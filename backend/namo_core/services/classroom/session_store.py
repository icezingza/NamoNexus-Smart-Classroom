import json
import logging
from pathlib import Path
import redis.asyncio as redis

from namo_core.config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SESSION_STATE = {
    "mode": "demo",
    "lesson": "Introduction to Buddhism",
    "students_connected": 0,
    "projector": "standby",
    "assistant_state": "ready",
}

REDIS_KEY_SESSION = "namo:classroom:session"
REDIS_CHANNEL_CLASSROOM_STATE = "classroom_state"


class ClassroomSessionStore:
    def __init__(self, file_path: Path | None = None) -> None:
        # file_path is kept for backward compatibility but ignored in Redis mode
        settings = get_settings()
        if settings.redis_url:
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.use_redis = True
        else:
            # Fallback for local testing if redis_url is not set
            self.use_redis = False
            self.file_path = file_path or settings.classroom_state_path

    async def load(self) -> dict:
        if self.use_redis:
            try:
                data = await self.redis.get(REDIS_KEY_SESSION)
                if data:
                    return json.loads(data)
                await self.save(dict(DEFAULT_SESSION_STATE))
                return dict(DEFAULT_SESSION_STATE)
            except Exception as e:
                logger.error(f"Redis load error: {e}. Falling back to default.")
                return dict(DEFAULT_SESSION_STATE)
        else:
            # Local fallback (async wrap of sync I/O for simplicity during local dev)
            import asyncio
            def _read():
                self._ensure_exists_sync()
                return json.loads(self.file_path.read_text(encoding="utf-8"))
            return await asyncio.to_thread(_read)

    async def save(self, payload: dict) -> dict:
        if self.use_redis:
            try:
                await self.redis.set(REDIS_KEY_SESSION, json.dumps(payload, ensure_ascii=True))
                await self.redis.publish(
                    REDIS_CHANNEL_CLASSROOM_STATE,
                    json.dumps(payload, ensure_ascii=True),
                )
            except Exception as e:
                logger.error(f"Redis save error: {e}")
        else:
            import asyncio
            def _write():
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                self.file_path.write_text(
                    json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
                    encoding="utf-8",
                )
            await asyncio.to_thread(_write)
        return payload

    def _ensure_exists_sync(self) -> None:
        if self.file_path.exists():
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(dict(DEFAULT_SESSION_STATE), ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
