from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class EnterpriseAuthMiddleware(BaseHTTPMiddleware):
    """Enforces Security First principles (JWT checks) for Sovereign AI."""

    def __init__(self, app):
        super().__init__(app)
        self.protected_prefixes = ("/classroom", "/nexus")

    async def dispatch(self, request: Request, call_next):
        from namo_core.config.settings import get_settings
        import jwt

        settings = get_settings()
        secret = settings.system_secret
        path = request.url.path

        # 1. HTTP Endpoints
        if any(path.startswith(prefix) for prefix in self.protected_prefixes):
            auth = request.headers.get("Authorization")
            if not auth or not auth.startswith("Bearer "):
                # Fallback for development/testing via query param
                token = request.query_params.get("token")
                if not token:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Missing/Invalid Security token"},
                    )
            else:
                token = auth.split(" ")[1]

            try:
                # Verify JWT signatures and expiration
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                request.state.user = payload
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token has expired. Please log in again."},
                )
            except jwt.InvalidTokenError:
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid Security Token"}
                )

        # 2. WebSocket Endpoints
        if path.startswith("/ws"):
            # Phase 10: Allow specific origins for WebSockets without token verification
            origin = request.headers.get("Origin")
            allowed_socket_origins = [
                "https://namonexus.com",
                "https://www.namonexus.com",
                "https://api.namonexus.com",
            ]
            if origin in allowed_socket_origins:
                return await call_next(request)

            # Bypass JWT checking for WebSockets entirely to allow tablet connection from 5G/anywhere
            return await call_next(request)

        return await call_next(request)
