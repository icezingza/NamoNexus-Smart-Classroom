from fastapi import APIRouter

from namo_core.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "namo-core",
        "environment": settings.env,
        "version": "0.1.0-recovered",
    }
