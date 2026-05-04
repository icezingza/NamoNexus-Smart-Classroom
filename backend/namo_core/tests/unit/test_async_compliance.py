"""
SMART [A] Async Compliance Tests

Verify that critical pipeline functions are coroutines (non-blocking).
Each test watches the function fail *before* the fix, then passes after.
"""
from __future__ import annotations

import asyncio
import inspect


def test_orchestrator_run_full_loop_is_coroutine() -> None:
    from namo_core.services.orchestrator import run_full_loop
    assert inspect.iscoroutinefunction(run_full_loop), (
        "run_full_loop must be async def — sync version blocks the event loop"
    )


def test_orchestrator_singleton_run_full_loop_is_coroutine() -> None:
    from namo_core.services.orchestrator import OrchestratorSingleton
    assert inspect.iscoroutinefunction(OrchestratorSingleton.run_full_loop)


def test_knowledge_search_route_is_coroutine() -> None:
    from namo_core.api.routes.knowledge import search_knowledge
    assert inspect.iscoroutinefunction(search_knowledge), (
        "search_knowledge route must be async def — calls FAISS (CPU-bound)"
    )


def test_knowledge_tripitaka_search_route_is_coroutine() -> None:
    from namo_core.api.routes.knowledge import search_tripitaka_endpoint
    assert inspect.iscoroutinefunction(search_tripitaka_endpoint)


def test_knowledge_tripitaka_status_route_is_coroutine() -> None:
    from namo_core.api.routes.knowledge import tripitaka_index_status
    assert inspect.iscoroutinefunction(tripitaka_index_status)


def test_ws_chat_handler_is_coroutine() -> None:
    from namo_core.api.routes.ws import websocket_chat
    assert inspect.iscoroutinefunction(websocket_chat)


def test_ws_endpoint_is_coroutine() -> None:
    from namo_core.api.routes.ws import websocket_endpoint
    assert inspect.iscoroutinefunction(websocket_endpoint)


def test_orchestrator_run_full_loop_returns_coroutine_when_called() -> None:
    from namo_core.services.orchestrator import run_full_loop
    coro = run_full_loop(text="test")
    assert asyncio.iscoroutine(coro), "run_full_loop() must return a coroutine"
    coro.close()


def test_ws_push_loop_fallback_interval_under_200ms() -> None:
    """
    [R] Resonance gate: fallback poll interval ต้อง < 200ms
    ตรวจจาก source — asyncio.sleep value ใน _push_loop fallback
    """
    import ast
    import pathlib

    ws_path = pathlib.Path(__file__).parents[2] / "api" / "routes" / "ws.py"
    source = ws_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    sleep_values: list[float] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "sleep"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            sleep_values.append(float(node.args[0].value))

    assert sleep_values, "No asyncio.sleep found in ws.py — expected fallback poll"
    assert all(v <= 0.2 for v in sleep_values), (
        f"WebSocket fallback sleep must be ≤ 0.2s (200ms), found: {sleep_values}"
    )
