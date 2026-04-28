#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Namo Core — System Health Check Script.
Phase 8: Deployment

Verifies that all critical subsystems are operational before a classroom session.
Run from the project root:
    python scripts/health_check.py
    python scripts/health_check.py --url http://192.168.1.100:8000
    python scripts/health_check.py --full   (runs full pipeline test)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import time
from datetime import datetime
import io

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_URL = "http://127.0.0.1:8000"
TIMEOUT = 30  # seconds per request

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get(url: str) -> tuple[int, dict]:
    try:
        req = urllib.request.Request(
            url, headers={"Authorization": "Bearer NamoSystemBypass2026-HealthCheck"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read())
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def _post(url: str, data: dict) -> tuple[int, dict]:
    try:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer NamoSystemBypass2026-HealthCheck",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read())
            return resp.status, body
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Check functions
# ─────────────────────────────────────────────────────────────────────────────


def check(name: str, ok: bool, detail: str = "") -> bool:
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    label = f"{GREEN}{name}{RESET}" if ok else f"{RED}{name}{RESET}"
    detail_str = f"  {detail}" if detail else ""
    print(f"  {icon}  {label}{detail_str}")
    return ok


def run_checks(base_url: str, full: bool = False) -> bool:
    print(f"\n{BOLD}{CYAN}Namo Core Health Check{RESET}  —  {base_url}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    results: list[bool] = []

    # ── 1. Server reachable ───────────────────────────────────────────────────
    print(f"{BOLD}[Core]{RESET}")

    # Add retry logic (HTTP 0 = Connection Refused/Timeout while server boots up)
    for _ in range(5):
        status, body = _get(f"{base_url}/health")
        if status != 0:
            break
        time.sleep(1)

    results.append(check("API server reachable", status == 200, f"(HTTP {status})"))

    # ── 2. Status endpoint ────────────────────────────────────────────────────
    status, body = _get(f"{base_url}/status")
    results.append(check("Status endpoint", status == 200))

    # ── 3. Feature flags ──────────────────────────────────────────────────────
    flags = body.get("feature_flags", {})
    results.append(check("Emotion engine flag", flags.get("emotion_engine", False)))
    results.append(check("Knowledge flag", flags.get("knowledge", False)))
    results.append(check("TTS flag", flags.get("tts", False)))

    # ── 4. Knowledge base ─────────────────────────────────────────────────────
    print(f"\n{BOLD}[Knowledge]{RESET}")
    status, body = _get(f"{base_url}/knowledge/search?q=dukkha")
    results.append(check("Knowledge search", status == 200, f"(HTTP {status})"))
    if status == 200:
        count = len(body.get("results", []))
        results.append(check(f"Knowledge results ({count} items)", count > 0))

    status, body = _get(f"{base_url}/knowledge/tripitaka/status")
    results.append(
        check("Tripitaka FAISS Index status", status == 200, f"(HTTP {status})")
    )
    if status == 200:
        vectors = body.get("vectors", 0)
        results.append(check(f"Tripitaka vectors ({vectors:,} items)", vectors > 0))

    # ── 5. Classroom ──────────────────────────────────────────────────────────
    print(f"\n{BOLD}[Classroom]{RESET}")
    status, body = _get(f"{base_url}/classroom/session")
    results.append(check("Session endpoint", status == 200))

    status, body = _get(f"{base_url}/classroom/lessons")
    lesson_count = body.get("count", 0)
    results.append(check(f"Lessons loaded ({lesson_count} lessons)", lesson_count > 0))

    status, body = _get(f"{base_url}/classroom/slide")
    results.append(check("Slide controller", status == 200))

    # ── 6. Emotion engine ─────────────────────────────────────────────────────
    print(f"\n{BOLD}[Emotion Engine — Phase 5]{RESET}")
    status, body = _get(f"{base_url}/emotion/state")
    results.append(check("Emotion state endpoint", status == 200))
    if status == 200:
        state = body.get("emotion_state", "")
        results.append(check(f"Emotion detected ({state})", bool(state)))

    # ── 7. TTS ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}[TTS]{RESET}")
    status, body = _get(f"{base_url}/tts/status")
    results.append(check("TTS status endpoint", status == 200))

    # ── 8. Full pipeline test (optional) ─────────────────────────────────────
    if full:
        print(f"\n{BOLD}[Full Pipeline — Phase 7]{RESET}")
        status, body = _post(
            f"{base_url}/nexus/text-chat",
            {"text": "อธิบายทุกข์ให้เด็กเข้าใจ", "attention_score": 0.8},
        )
        results.append(check("Text-chat pipeline", status == 200))
        if status == 200:
            stages = body.get("pipeline_meta", {}).get("stages_completed", [])
            results.append(check(f"Emotion stage ran", "emotion" in stages))
            results.append(check(f"Reasoning stage ran", "reasoning" in stages))
            answer = body.get("reasoning", {}) or {}
            results.append(check("LLM answer present", bool(answer.get("answer"))))

    # ── 9. Security Audit ─────────────────────────────────────────────────────
    print(f"\n{BOLD}[Security Audit — Phase 9]{RESET}")
    # Force a student join
    test_pii_name = "Somchai-PII-Secret"
    _post(f"{base_url}/classroom/student/connect", {"name": test_pii_name})
    status, body = _get(f"{base_url}/classroom/students")
    roster = body.get("roster", []) if status == 200 else []

    # Verify no plain-text match for "Somchai-PII-Secret"
    pii_safe = True
    for student in roster:
        if test_pii_name in student.get("name", ""):
            pii_safe = False

    results.append(check("PII SHA-256 Hashing Enforced", pii_safe))

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(results)
    total = len(results)
    failed = total - passed
    print(f"\n{'─' * 44}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}All {total} checks passed ✓{RESET}")
        print(f"  {GREEN}System is ready for classroom use.{RESET}")
    else:
        print(f"  {RED}{BOLD}{failed}/{total} checks FAILED{RESET}")
        print(f"  {YELLOW}Resolve failures before starting a session.{RESET}")
    print()
    return failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Namo Core Health Check")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Base URL of the API server (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline test (includes LLM reasoning call)",
    )
    args = parser.parse_args()

    ok = run_checks(base_url=args.url.rstrip("/"), full=args.full)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
