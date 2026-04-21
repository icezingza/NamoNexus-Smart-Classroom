from collections.abc import Callable


def run_with_fallback(primary: Callable[[], dict], fallback: Callable[[], dict]) -> dict:
    try:
        return primary()
    except Exception as exc:  # pragma: no cover - defensive demo path
        response = fallback()
        response["fallback_reason"] = str(exc)
        return response
