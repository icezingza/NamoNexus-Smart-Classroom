from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from namo_core.config.settings import get_settings
from namo_core.services.classroom.classroom_service import get_classroom_state
from namo_core.services.emotion.emotion_service import EmotionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

_emotion_svc: EmotionService | None = None


def _get_emotion_svc() -> EmotionService:
    global _emotion_svc
    if _emotion_svc is None:
        _emotion_svc = EmotionService()
    return _emotion_svc


async def _build_state_payload() -> dict:
    try:
        svc = _get_emotion_svc()
        emotion = svc.detect(
            perception={"attention_score": 0.75},
            transcript={"text": "", "confidence": 0.5},
        )
    except Exception as exc:
        logger.warning("emotion snapshot failed: %s", exc)
        emotion = {"emotion_state": "unknown", "composite_score": 0.0}

    try:
        classroom = await get_classroom_state()
    except Exception as exc:
        logger.warning("classroom snapshot failed: %s", exc)
        classroom = {}

    mic_ok = False
    cam_ok = False

    return {
        "type": "state",
        "emotion": emotion,
        "classroom": classroom,
        "devices": {"mic": mic_ok, "camera": cam_ok},
        "ts": time.time(),
    }


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            if raw.strip() == "ping":
                await websocket.send_text("pong")
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "invalid JSON"}))
                continue

            from namo_core.services.orchestrator import run_full_loop

            result = await run_full_loop(
                text=payload.get("text"),
                session_id=payload.get("session_id", "default"),
                voice=payload.get("voice", "th-TH-PremwadeeNeural"),
            )
            await websocket.send_text(json.dumps(result, ensure_ascii=False))
    except WebSocketDisconnect:
        pass


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    client = websocket.client
    logger.info("WS connected: %s", client)

    payload = await _build_state_payload()
    await websocket.send_text(json.dumps(payload))

    async def _receive_loop() -> None:
        while True:
            msg = await websocket.receive_text()
            if msg.strip() == "ping":
                await websocket.send_text("pong")

    async def _push_loop() -> None:
        settings = get_settings()
        if not settings.redis_url:
            while True:
                await asyncio.sleep(0.05)
                payload = await _build_state_payload()
                await websocket.send_text(json.dumps(payload))

        redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        try:
            await pubsub.subscribe("classroom_state")
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                payload = await _build_state_payload()
                await websocket.send_text(json.dumps(payload))
        finally:
            with suppress(Exception):
                await pubsub.unsubscribe("classroom_state")
            with suppress(Exception):
                await pubsub.close()
            with suppress(Exception):
                await redis_client.close()

    receive_task = asyncio.create_task(_receive_loop())
    push_task = asyncio.create_task(_push_loop())
    try:
        await asyncio.gather(receive_task, push_task)
    except Exception as exc:
        logger.debug("WS disconnected with error: %s", exc)
    finally:
        receive_task.cancel()
        push_task.cancel()
        with suppress(Exception):
            await receive_task
        with suppress(Exception):
            await push_task
        logger.info("WS disconnected: %s", client)
