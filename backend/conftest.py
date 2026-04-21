"""Root conftest.py — ensures namo_core is discoverable regardless of pytest CWD,
and configures the event loop backend to avoid Windows anyio/trio teardown deadlocks."""
from __future__ import annotations

import sys
from pathlib import Path

# Make sure 'namo_core' package is always importable when running pytest from the project root.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
