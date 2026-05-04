from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt

from namo_core.config.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    settings = get_settings()

    # TODO: ใน Phase 12 สามารถปรับให้เชื่อมกับ Database เพื่อเช็ค Hash ของรหัสผ่านได้
    # เบื้องต้นใช้ค่าที่กำหนดไว้สำหรับให้ครูใช้งานก่อน
    valid_username = settings.admin_username
    valid_password = settings.admin_password

    if credentials.username != valid_username or credentials.password != valid_password:
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    # สร้าง JWT Token ให้มีอายุการใช้งาน 12 ชั่วโมง
    expiration = datetime.utcnow() + timedelta(hours=12)
    payload = {"sub": credentials.username, "role": "teacher", "exp": expiration}

    token = jwt.encode(payload, settings.system_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}
