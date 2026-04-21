"""
manager.py — Session Memory (Hippocampus) for Namo Core
Sliding window chat history per session_id, in-process dict store.
"""
from __future__ import annotations
from collections import deque
from threading import Lock

_WINDOW = 10          # จำนวน turn สูงสุด (1 turn = 1 user + 1 assistant)
_store: dict[str, deque] = {}
_lock = Lock()


def _get(session_id: str) -> deque:
    with _lock:
        if session_id not in _store:
            _store[session_id] = deque(maxlen=_WINDOW * 2)  # *2: user+assistant
        return _store[session_id]


def add_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    """เพิ่ม 1 turn (user + assistant) เข้า sliding window"""
    q = _get(session_id)
    with _lock:
        q.append({"role": "user",      "content": user_text})
        q.append({"role": "assistant", "content": assistant_text})


def get_history(session_id: str) -> list[dict]:
    """คืน chat history เป็น list[{role, content}] พร้อมส่งให้ LLM"""
    return list(_get(session_id))


def clear(session_id: str) -> None:
    """ล้าง session"""
    with _lock:
        _store.pop(session_id, None)
