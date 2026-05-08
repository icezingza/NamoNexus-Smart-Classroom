import json
import logging
import os
import time
import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ContextVar for async-safe request tracking
request_id_context: ContextVar[str] = ContextVar("request_id", default="N/A")


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract from header (for distributed tracing) or generate new
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        start_time = time.time()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{time.time() - start_time:.4f}s"
            return response
        finally:
            request_id_context.reset(token)


class HSTSMiddleware(BaseHTTPMiddleware):
    """Add Strict-Transport-Security header for production HTTPS enforcement."""

    _HSTS_VALUE = "max-age=31536000; includeSubDomains"

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = self._HSTS_VALUE
        return response


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()  # type: ignore[attr-defined]
        return True


class _JsonFormatter(logging.Formatter):
    """Structured JSON formatter for Cloud Run / Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", "N/A"),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_traced_logging() -> None:
    """Configure logging with request_id injection.

    In production (NAMO_ENV=production) emits JSON structured logs compatible
    with Cloud Run / Cloud Logging. In development uses a human-readable format.
    """
    is_production = os.environ.get("NAMO_ENV", "development") == "production"
    logger = logging.getLogger("namo_core")

    if not any(isinstance(f, _RequestIdFilter) for f in logger.filters):
        logger.addFilter(_RequestIdFilter())

    if is_production:
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
        )

    for handler in logger.handlers:
        handler.setFormatter(formatter)

    # Ensure at least one handler exists (uvicorn may not add one early enough)
    if not logger.handlers:
        _h = logging.StreamHandler()
        _h.setFormatter(formatter)
        logger.addHandler(_h)
        logger.setLevel(logging.INFO)
