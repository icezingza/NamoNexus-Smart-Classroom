"""
cache_seed_loader.py — Load semantic cache seed data on startup.

Injects pre-curated Dhamma Q&A into SemanticCache so common questions
get <100ms responses without hitting the LLM.

Usage:
    from namo_core.services.knowledge.cache_seed_loader import load_seed_cache
    load_seed_cache()  # call once at startup, after SemanticCache is ready
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SEED_FILE = Path(__file__).parent.parent.parent / "data" / "semantic_cache_seed.json"


def load_seed_cache(cache_instance=None) -> int:
    """
    Load seed Q&A into the SemanticCache singleton.

    Args:
        cache_instance: optional SemanticCache instance; uses singleton if None.

    Returns:
        Number of entries loaded successfully.
    """
    if not _SEED_FILE.exists():
        logger.warning("Seed file not found: %s", _SEED_FILE)
        return 0

    try:
        with open(_SEED_FILE, encoding="utf-8") as f:
            seed_data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load seed file: %s", exc)
        return 0

    entries = seed_data.get("entries", [])
    if not entries:
        logger.warning("No entries found in seed file.")
        return 0

    # Resolve cache instance
    if cache_instance is None:
        try:
            from namo_core.services.knowledge.semantic_cache import SemanticCache
            cache_instance = SemanticCache()
        except ImportError as exc:
            logger.error("SemanticCache not available: %s", exc)
            return 0

    loaded = 0
    for entry in entries:
        question = entry.get("question", "").strip()
        answer   = entry.get("answer", "").strip()
        if not question or not answer:
            continue
        try:
            cache_instance.put(question, answer)
            loaded += 1
        except Exception as exc:
            logger.warning("Failed to cache entry '%s': %s", question[:40], exc)

    logger.info("[CacheSeed] Loaded %d/%d entries into SemanticCache", loaded, len(entries))
    return loaded
