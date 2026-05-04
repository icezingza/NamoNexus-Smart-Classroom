from urllib.parse import parse_qs

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class EnterpriseAuthMiddleware(BaseHTTPMiddleware):
    """Enforces Security First principles (JWT checks) for Sovereign AI."""

    def __init__(self, app):
        super().__init__(app)
        self.protected_prefixes = ("/classroom", "/nexus", "/notebook")
        # Public paths that bypass auth (read-only, no personal data)
        self.public_paths = ("/notebook/suggest-sources",)
        self._ws_prefixes = ("/ws", "/notebook/ws")

    async def __call__(self, scope, receive, send):
        # BaseHTTPMiddleware skips dispatch() for WebSocket scopes entirely.
        # We intercept here before that bypass can happen.
        if scope["type"] == "websocket":
            path = scope.get("path", "")
            if any(path.startswith(p) for p in self._ws_prefixes):
                import jwt

                from namo_core.config.settings import get_settings

                settings = get_settings()
                qs = scope.get("query_string", b"").decode()
                token = (parse_qs(qs).get("token") or [None])[0]

                if not token:
                    await receive()  # consume websocket.connect
                    await send({"type": "websocket.close", "code": 1008, "reason": "Missing auth token"})
                    return

                try:
                    payload = jwt.decode(token, settings.system_secret, algorithms=["HS256"])
                    scope.setdefault("state", {})["user"] = payload
                except jwt.InvalidTokenError:
                    await receive()  # consume websocket.connect
                    await send({"type": "websocket.close", "code": 1008, "reason": "Invalid token"})
                    return

        await super().__call__(scope, receive, send)

    async def dispatch(self, request: Request, call_next):
        from namo_core.config.settings import get_settings
        import jwt

        settings = get_settings()
        secret = settings.system_secret
        path = request.url.path

        # 0. Public paths bypass — no auth needed
        if any(path.startswith(pub) for pub in self.public_paths):
            return await call_next(request)

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

        return await call_next(request)
