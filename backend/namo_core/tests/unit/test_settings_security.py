"""SMART [S] Sovereign — Settings security contract tests."""
from __future__ import annotations

import os
import pytest

from namo_core.config.settings import Settings

# Env vars injected by conftest.py that override placeholder defaults.
# These must be cleared before testing the "no config" baseline.
_SECRET_ENV_VARS = (
    "NAMO_JWT_SECRET_KEY",
    "NAMO_ADMIN_PASSWORD",
    "NAMO_ADMIN_USERNAME",
)


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch):
    """Remove secret env vars so Settings falls back to its coded defaults."""
    for var in _SECRET_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    yield


def test_cors_default_has_no_wildcard() -> None:
    s = Settings()
    assert "*" not in s.origin_list, (
        f"CORS wildcard '*' must not appear in default allowed_origins. Got: {s.origin_list}"
    )


def test_system_secret_default_is_placeholder(clean_env: None) -> None:
    """Ensure system_secret ships as a detectable placeholder, not a real secret."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.system_secret == "MUST_BE_SET_IN_ENV", (
        "system_secret default must remain a placeholder so misconfiguration is detectable"
    )


def test_jwt_secret_default_is_placeholder(clean_env: None) -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.jwt_secret_key == "MUST_BE_SET_IN_ENV"


def test_admin_password_default_is_placeholder(clean_env: None) -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.admin_password == "MUST_BE_SET_IN_ENV"
