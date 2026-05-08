import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import jwt

from namo_core.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 60

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _lock:
        _attempts[ip] = [t for t in _attempts[ip] if now - t < _WINDOW_SECONDS]
        if len(_attempts[ip]) >= _MAX_ATTEMPTS:
            logger.warning("Login rate limit hit for IP %s (%d attempts)", ip, len(_attempts[ip]))
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts. Try again in {_WINDOW_SECONDS}s.",
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )
        _attempts[ip].append(now)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, request: Request) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    settings = get_settings()
    valid_username = settings.admin_username
    stored_password = settings.admin_password

    username_ok = secrets.compare_digest(credentials.username, valid_username)

    if stored_password.startswith("$2b$"):
        try:
            import bcrypt as _bcrypt
            password_ok = _bcrypt.checkpw(credentials.password.encode(), stored_password.encode())
        except ImportError:
            logger.error("bcrypt not installed but bcrypt hash detected")
            password_ok = False
    else:
        if settings.env == "production":
            logger.warning("admin_password is stored as plaintext — use bcrypt in production")
        password_ok = secrets.compare_digest(credentials.password, stored_password)

    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    expiration = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": credentials.username, "role": "teacher", "exp": expiration}
    token = jwt.encode(payload, settings.system_secret, algorithm="HS256")
    return TokenResponse(access_token=token, token_type="bearer")
