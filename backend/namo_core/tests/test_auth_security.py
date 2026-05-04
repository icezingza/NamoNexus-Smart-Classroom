"""Security tests for auth middleware.

TDD: tests written BEFORE code fixes.
Expected failures before fix, passing after.
"""
from __future__ import annotations

import pytest
import jwt as pyjwt
from fastapi.testclient import TestClient

from namo_core.api.app import app

client = TestClient(app, raise_server_exceptions=False)


# ── Bypass token tests ─────────────────────────────────────────────────────


def test_hardcoded_health_check_bypass_token_is_rejected():
    """NamoSystemBypass2026-HealthCheck must not grant access — it is a leaked secret."""
    response = client.get(
        "/classroom/session",
        headers={"Authorization": "Bearer NamoSystemBypass2026-HealthCheck"},
    )
    assert response.status_code == 401


def test_hardcoded_sovereign_bypass_token_is_rejected():
    """NamoSovereignToken2026 must not grant access — hardcoded tokens are not auth."""
    response = client.get(
        "/classroom/session",
        headers={"Authorization": "Bearer NamoSovereignToken2026"},
    )
    assert response.status_code == 401


def test_valid_jwt_still_grants_access():
    """A properly signed JWT must still be accepted after bypass tokens are removed."""
    from namo_core.config.settings import get_settings

    secret = get_settings().system_secret
    token = pyjwt.encode({"sub": "test-teacher"}, secret, algorithm="HS256")

    response = client.get(
        "/classroom/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Must NOT be 401 — actual route may return other codes, that is fine
    assert response.status_code != 401


# ── WebSocket auth tests ───────────────────────────────────────────────────


def test_ws_chat_without_token_is_rejected():
    """WebSocket /ws/chat must reject connections that carry no JWT."""
    rejected = False
    try:
        with client.websocket_connect("/ws/chat") as ws:
            # If we reach here the server accepted an unauthenticated WS — failure
            ws.receive_text()
    except Exception:
        rejected = True

    assert rejected, "WS connection without token must be rejected (got accepted)"


def test_ws_chat_with_valid_token_is_accepted():
    """WebSocket /ws/chat must accept connections carrying a valid JWT via ?token=."""
    from namo_core.config.settings import get_settings

    secret = get_settings().system_secret
    token = pyjwt.encode({"sub": "test-teacher"}, secret, algorithm="HS256")

    connected = False
    try:
        with client.websocket_connect(f"/ws/chat?token={token}") as ws:
            connected = True
            # Send ping to keep exchange clean
            ws.send_text("ping")
    except Exception:
        pass  # Any error after accept still counted below

    assert connected, "WS connection with valid token must be accepted"
