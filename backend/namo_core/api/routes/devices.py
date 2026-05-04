from fastapi import APIRouter

from namo_core.services.devices.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def devices() -> dict:
    return DeviceService().snapshot()
