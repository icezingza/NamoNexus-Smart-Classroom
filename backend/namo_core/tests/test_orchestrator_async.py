"""Async integrity tests for the orchestrator pipeline.

TDD: tests written BEFORE the async refactor.
These fail on sync run_full_loop and pass after async refactor.
"""
from __future__ import annotations

import inspect


def test_run_full_loop_is_a_coroutine_function():
    """run_full_loop must be async — blocking sync I/O in event loop violates CLAUDE.md §7."""
    from namo_core.services.orchestrator import run_full_loop

    assert inspect.iscoroutinefunction(run_full_loop), (
        "run_full_loop is a plain sync function. "
        "Refactor to async def with asyncio.to_thread() around FAISS/model.encode."
    )


def test_orchestrator_method_is_a_coroutine_function():
    """OrchestratorSingleton.run_full_loop must also be async — it is the actual executor."""
    from namo_core.services.orchestrator import OrchestratorSingleton

    assert inspect.iscoroutinefunction(OrchestratorSingleton.run_full_loop), (
        "OrchestratorSingleton.run_full_loop is sync. "
        "The module-level wrapper cannot be async if the method it calls is not."
    )


def test_ws_handler_does_not_use_deprecated_get_event_loop():
    """ws.py must not call asyncio.get_event_loop() — deprecated in 3.10+, broken in 3.12+."""
    from namo_core.api.routes import ws as ws_module

    source = inspect.getsource(ws_module)
    assert "get_event_loop()" not in source, (
        "ws.py still calls asyncio.get_event_loop(). "
        "Replace with direct `await run_full_loop(...)` after async refactor."
    )


def test_ws_handler_does_not_use_run_in_executor():
    """After async refactor ws.py must not need run_in_executor wrapper."""
    from namo_core.api.routes import ws as ws_module

    source = inspect.getsource(ws_module)
    assert "run_in_executor" not in source, (
        "ws.py still wraps run_full_loop in run_in_executor. "
        "Once run_full_loop is async, call it directly with await."
    )
