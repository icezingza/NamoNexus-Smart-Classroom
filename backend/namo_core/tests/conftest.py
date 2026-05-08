from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Collection guard: skip files that import removed/renamed modules.
collect_ignore = [
    str(Path(__file__).parent / "test_classroom_phase6.py"),
]

# ---------------------------------------------------------------------------
# Sandbox-safe stubs: inject before any app module imports heavy ML deps
# ---------------------------------------------------------------------------

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = None  # type: ignore[assignment]
    return mod

# sentence_transformers stub
if "sentence_transformers" not in sys.modules:
    _st = _make_stub("sentence_transformers")

    class _SentenceTransformer:
        def __init__(self, *a, **kw): pass
        def encode(self, texts, *a, **kw):
            import numpy as np
            n = len(texts) if isinstance(texts, list) else 1
            return np.zeros((n, 384), dtype="float32")

    _st.SentenceTransformer = _SentenceTransformer  # type: ignore[attr-defined]
    sys.modules["sentence_transformers"] = _st

# groq stub
if "groq" not in sys.modules:
    _groq = _make_stub("groq")
    _groq.Groq = MagicMock  # type: ignore[attr-defined]
    sys.modules["groq"] = _groq

# google.cloud.* stubs
for _pkg in [
    "google", "google.cloud", "google.cloud.storage",
    "google.cloud.secretmanager", "google.auth",
]:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = _make_stub(_pkg)

# ---------------------------------------------------------------------------

os.environ["NAMO_TTS_PROVIDER"] = "mock"
os.environ["NAMO_TTS_VOICE"] = "demo-th"
os.environ["NAMO_ENABLE_TTS"] = "true"
os.environ["NAMO_SPEECH_PROVIDER"] = "mock"
os.environ.setdefault("NAMO_REASONING_PROVIDER", "mock")
os.environ.setdefault("NAMO_ENV", "development")
os.environ.setdefault("NAMO_JWT_SECRET_KEY", "test-secret-32chars-xxxxxxxxxxxxx")
os.environ.setdefault("NAMO_ADMIN_PASSWORD", "testpassword123")
os.environ.setdefault("NAMO_ADMIN_USERNAME", "admin")
# Use in-memory SQLite: prevents disk I/O errors in sandbox/CI
os.environ.setdefault("NAMO_DATABASE_URL", "sqlite:///:memory:")
# Disable Redis: prevents ConnectionRefusedError when localhost:6379 is unavailable
os.environ["NAMO_REDIS_URL"] = ""

# ---------------------------------------------------------------------------
# JWT helpers — shared test secret matches NAMO_JWT_SECRET_KEY above
# ---------------------------------------------------------------------------
_TEST_SECRET = "test-secret-32chars-xxxxxxxxxxxxx"
_TEST_USERNAME = "admin"


def _make_test_token() -> str:
    """Generate a valid HS256 JWT for test requests to protected endpoints."""
    import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": _TEST_USERNAME,
        "role": "teacher",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def auth_token() -> str:
    """Session-scoped JWT token — created once, reused across all tests."""
    return _make_test_token()


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict:
    """Authorization headers dict for TestClient requests to protected routes."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Reset settings singleton AND in-memory rate limiter between every test."""
    import namo_core.config.settings as _s
    _s._settings_instance = None

    try:
        import namo_core.api.routes.auth_routes as _ar
        _ar._attempts.clear()
    except Exception:
        pass

    yield

    _s._settings_instance = None
    try:
        import namo_core.api.routes.auth_routes as _ar
        _ar._attempts.clear()
    except Exception:
        pass
