"""WebSocket route — Phase 10: Real-time Tablet Dashboard.

เปิด WebSocket endpoint ที่ /ws เพื่อ stream ข้อมูล classroom + emotion
ไปยัง Tablet Dashboard แบบ real-time

Protocol:
  Server → Client: JSON payload ทุก 5 วินาที
    {
      "type": "state",
      "emotion": { state, smoothed_state, composite_score, ... },
      "classroom": { assistant_state, projector, students_connected, ... },
      "ts": <unix timestamp>
    }

  Client → Server: "ping" → Server ตอบ "pong" (ป้องกัน Cloudflare timeout 100s)

Payload เพิ่มเติม:
  "devices": { "mic": bool, "camera": bool }
  — ใช้แสดงไฟสถานะ Mic / Camera บน Tablet Dashboard
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from namo_core.services.classroom.classroom_service import get_classroom_state
from namo_core.services.emotion.emotion_service import EmotionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# ── /ws/chat — Full-Loop Real-time Chat ──────────────────────────────
# Protocol (JSON over WebSocket):
#   Client→Server: {"text":"คำถาม","session_id":"abc","voice":"th-TH-PremwadeeNeural"}
#   Server→Client: {"stt_text":…,"emotion":…,"answer":…,"audio_base64":…,"latency_ms":…}
#   Client→Server: "ping" → Server: "pong"


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """Full-Loop WebSocket: Text → Emotion → RAG → Reasoning → TTS (real-time)."""
    await websocket.accept()
    logger.info("WS/chat connected: %s", websocket.client)
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

            from namo_core.services.orchestrator import run_full_loop  # noqa: PLC0415
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda p=payload: run_full_loop(
                    text=p.get("text"),
                    session_id=p.get("session_id", "default"),
                    voice=p.get("voice", "th-TH-PremwadeeNeural"),
                ),
            )
            await websocket.send_text(json.dumps(result, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WS/chat error: %s", exc)
    finally:
        logger.info("WS/chat disconnected: %s", websocket.client)


# singleton emotion service (ใช้ร่วมกับ /emotion/state)
_emotion_svc: EmotionService | None = None


def _get_emotion_svc() -> EmotionService:
    """Lazy-load EmotionService singleton."""
    global _emotion_svc
    if _emotion_svc is None:
        _emotion_svc = EmotionService()
    return _emotion_svc


async def _build_state_payload() -> dict:
    """รวบรวม emotion + classroom + device state เป็น payload เดียว."""
    # --- emotion ---
    try:
        svc = _get_emotion_svc()
        emotion = svc.detect(
            perception={"attention_score": 0.75},
            transcript={"text": "", "confidence": 0.5},
        )
    except Exception as exc:
        logger.warning("emotion snapshot failed: %s", exc)
        emotion = {"emotion_state": "unknown", "composite_score": 0.0}

    # --- classroom ---
    try:
        classroom = await get_classroom_state()
    except Exception as exc:
        logger.warning("classroom snapshot failed: %s", exc)
        classroom = {}

    # --- devices (mic / camera) ---
    try:
        from namo_core.modules.perception.perception_module import PerceptionModule
        perception = PerceptionModule()
        snapshot = perception.snapshot()
        mic_ok    = snapshot.get("device", {}).get("status") == "ready" if "device" in snapshot else False
        cam_ok    = snapshot.get("attention_score", 0) > 0
    except Exception:
        mic_ok = False
        cam_ok = False

    return {
        "type": "state",
        "emotion": emotion,
        "classroom": classroom,
        "devices": {
            "mic":    mic_ok,
            "camera": cam_ok,
        },
        "ts": time.time(),
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint สำหรับ Tablet Dashboard.

    - ส่ง state ทุก 5 วินาที
    - รับ "ping" แล้วตอบ "pong" เพื่อป้องกัน Cloudflare timeout
    """
    await websocket.accept()
    client = websocket.client
    logger.info("WS connected: %s", client)

    # ส่ง state แรกทันทีที่เชื่อมต่อ
    try:
        payload = await _build_state_payload()
        await websocket.send_text(json.dumps(payload))
    except Exception:
        return

    async def _receive_loop() -> None:
        """รับ message จาก client (ping/pong)."""
        try:
            while True:
                msg = await websocket.receive_text()
                if msg.strip() == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("WS receive error: %s", exc)

    async def _push_loop() -> None:
        """ส่ง state ทุก 5 วินาที."""
        try:
            while True:
                await asyncio.sleep(5)
                payload = await _build_state_payload()
                await websocket.send_text(json.dumps(payload))
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("WS push error: %s", exc)

    # รัน receive + push พร้อมกัน
    receive_task = asyncio.create_task(_receive_loop())
    push_task = asyncio.create_task(_push_loop())

    try:
        await asyncio.gather(receive_task, push_task)
    except Exception:
        pass
    finally:
        receive_task.cancel()
        push_task.cancel()
        logger.info("WS disconnected: %s", client)
