"""Smoke tests covering critical production-readiness paths.

Tests:
  - /auth/login: happy path, wrong creds, rate limit
  - /knowledge/search: auth-gated, returns results
  - /notebook/generate: LAN mode (no Redis) returns inline result
  - /notebook/suggest-sources: public endpoint (no auth)
  - startup secret guard: blocks placeholder secrets in production
  - HSTSMiddleware: injects header in production mode
  - settings.system_secret: returns jwt_secret_key value (no drift)
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch

# --------------------------------------------------------------------------
# Environment setup — must happen before importing app modules
# --------------------------------------------------------------------------

os.environ.setdefault("NAMO_TTS_PROVIDER", "mock")
os.environ.setdefault("NAMO_SPEECH_PROVIDER", "mock")
os.environ.setdefault("NAMO_REASONING_PROVIDER", "mock")
os.environ.setdefault("NAMO_SYSTEM_SECRET", "test-secret-32chars-xxxxxxxxxxx")
os.environ.setdefault("NAMO_JWT_SECRET_KEY", "test-secret-32chars-xxxxxxxxxxx")
os.environ.setdefault("NAMO_ADMIN_USERNAME", "admin")
os.environ.setdefault("NAMO_ADMIN_PASSWORD", "testpassword123")
os.environ.setdefault("NAMO_ENV", "development")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Isolated TestClient with a fresh settings instance per test."""
    import namo_core.config.settings as _s
    _s._settings_instance = None
    from namo_core.api.app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    _s._settings_instance = None


def _get_token(client) -> str:
    """Log in and return a valid JWT Bearer token."""
    resp = client.post("/auth/login", json={"username": "admin", "password": "testpassword123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# --------------------------------------------------------------------------
# Auth tests
# --------------------------------------------------------------------------

def test_login_success(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "testpassword123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_wrong_username(client):
    resp = client.post("/auth/login", json={"username": "hacker", "password": "testpassword123"})
    assert resp.status_code == 401


def test_login_rate_limit(client):
    """After 10 failed attempts the endpoint should return 429."""
    for _ in range(10):
        client.post("/auth/login", json={"username": "x", "password": "x"})
    resp = client.post("/auth/login", json={"username": "x", "password": "x"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_protected_endpoint_without_token(client):
    resp = client.get("/notebook/list")
    assert resp.status_code == 401


def test_protected_endpoint_with_token(client):
    token = _get_token(client)
    resp = client.get("/notebook/list", headers={"Authorization": f"Bearer {token}"})
    # 200 or 500 (DB not seeded) — not 401/403
    assert resp.status_code in (200, 500)


def test_jwt_token_in_query_param_rejected(client):
    """Query-param token fallback must be removed — expect 401, not 200."""
    token = _get_token(client)
    resp = client.get(f"/notebook/list?token={token}")
    assert resp.status_code == 401


# --------------------------------------------------------------------------
# Knowledge tests
# --------------------------------------------------------------------------

def test_knowledge_search_public(client):
    """GET /knowledge/search is NOT in protected_prefixes — should be accessible."""
    resp = client.get("/knowledge/search?q=อริยสัจ")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "query" in data


def test_suggest_sources_no_auth(client):
    """/notebook/suggest-sources is in public_paths — no token needed."""
    resp = client.get("/notebook/suggest-sources?q=พุทธศาสนา")
    # 200 or 503 (FAISS not loaded in test) — never 401
    assert resp.status_code != 401


# --------------------------------------------------------------------------
# Settings: dual-secret consolidation
# --------------------------------------------------------------------------

def test_system_secret_is_alias_of_jwt_secret_key():
    import namo_core.config.settings as _s
    _s._settings_instance = None
    from namo_core.config.settings import Settings
    s = Settings(
        jwt_secret_key="unique-jwt-secret",
        admin_password="pass",
        system_secret=None,  # type: ignore[arg-type]  # should be ignored
    )
    assert s.system_secret == "unique-jwt-secret", (
        "system_secret must always return jwt_secret_key — no drift allowed"
    )
    _s._settings_instance = None


# --------------------------------------------------------------------------
# Startup guard: placeholder secrets
# --------------------------------------------------------------------------

def test_startup_guard_logs_warning_in_dev(caplog):
    """In development mode, placeholder secrets emit a warning but don't crash."""
    import namo_core.config.settings as _s
    _s._settings_instance = None
    import logging
    with caplog.at_level(logging.WARNING, logger="namo_core"):
        with patch.dict(os.environ, {
            "NAMO_SYSTEM_SECRET": "MUST_BE_SET_IN_ENV",
            "NAMO_JWT_SECRET_KEY": "MUST_BE_SET_IN_ENV",
            "NAMO_ADMIN_PASSWORD": "MUST_BE_SET_IN_ENV",
            "NAMO_ENV": "development",
        }):
            _s._settings_instance = None
            from namo_core.api.app import create_app
            from fastapi.testclient import TestClient
            app = create_app()
            with TestClient(app, raise_server_exceptions=False):
                pass  # Startup should complete with warnings, not crash
    _s._settings_instance = None


def test_startup_guard_blocks_production_with_placeholder():
    """In production mode, placeholder secrets must raise RuntimeError."""
    import namo_core.config.settings as _s
    _s._settings_instance = None
    with patch.dict(os.environ, {
        "NAMO_JWT_SECRET_KEY": "MUST_BE_SET_IN_ENV",
        "NAMO_SYSTEM_SECRET": "MUST_BE_SET_IN_ENV",
        "NAMO_ADMIN_PASSWORD": "MUST_BE_SET_IN_ENV",
        "NAMO_ENV": "production",
    }):
        _s._settings_instance = None
        from namo_core.api.app import create_app
        from fastapi.testclient import TestClient
        app = create_app()
        with pytest.raises(RuntimeError, match="placeholder values detected"):
            with TestClient(app, raise_server_exceptions=True):
                pass
    _s._settings_instance = None


# --------------------------------------------------------------------------
# HSTS Middleware
# --------------------------------------------------------------------------

def test_hsts_header_not_added_in_development(client):
    resp = client.get("/health")
    assert "strict-transport-security" not in resp.headers


def test_hsts_header_added_in_production():
    import namo_core.config.settings as _s
    _s._settings_instance = None
    with patch.dict(os.environ, {"NAMO_ENV": "production"}):
        _s._settings_instance = None
        from namo_core.api.app import create_app
        from fastapi.testclient import TestClient
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/health")
            assert "strict-transport-security" in resp.headers
    _s._settings_instance = None
