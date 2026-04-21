from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

os.environ["NAMO_TTS_PROVIDER"] = "mock"
os.environ["NAMO_TTS_VOICE"] = "demo-th"
os.environ["NAMO_ENABLE_TTS"] = "true"
os.environ["NAMO_SPEECH_PROVIDER"] = "mock"

from namo_core.config.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
