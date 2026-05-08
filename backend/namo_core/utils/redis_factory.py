"""Shared Redis client factory.

All code that needs a Redis connection MUST use make_redis() instead of
calling redis.Redis.from_url() directly.  This ensures the password from
settings is always injected, even when it is not embedded in the URL.
"""
from __future__ import annotations

import redis.asyncio as aioredis
import redis as syncredis

from namo_core.config.settings import get_settings


def make_redis(decode_responses: bool = True) -> aioredis.Redis:
    """Return an async Redis client configured from settings.

    Password precedence:
    1. Already embedded in NAMO_REDIS_URL (redis://:pass@host/db)
    2. NAMO_REDIS_PASSWORD env var (injected here if not already in URL)
    """
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("NAMO_REDIS_URL is not configured")

    kwargs: dict = {"decode_responses": decode_responses}

    # Only inject password if the URL does not already carry one.
    # from_url parses the URL; password kwarg overrides the URL password field.
    if settings.redis_password and "@" not in settings.redis_url.split("://", 1)[-1].split("/")[0]:
        kwargs["password"] = settings.redis_password

    return aioredis.Redis.from_url(settings.redis_url, **kwargs)


def make_redis_sync(decode_responses: bool = True) -> syncredis.Redis:
    """Return a synchronous Redis client configured from settings."""
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("NAMO_REDIS_URL is not configured")

    kwargs: dict = {"decode_responses": decode_responses}
    if settings.redis_password and "@" not in settings.redis_url.split("://", 1)[-1].split("/")[0]:
        kwargs["password"] = settings.redis_password

    return syncredis.Redis.from_url(settings.redis_url, **kwargs)
