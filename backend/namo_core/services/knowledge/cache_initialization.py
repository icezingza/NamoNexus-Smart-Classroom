"""Initialize semantic cache with database persistence on application startup."""

import logging
from sqlalchemy.orm import Session

from namo_core.services.knowledge.semantic_cache import query_cache, set_db_save_callback
from namo_core.services.knowledge.semantic_cache_repository import SemanticCacheRepository

logger = logging.getLogger(__name__)


def initialize_semantic_cache(db: Session) -> None:
    """
    Initialize semantic cache system:
    1. Register database persistence callback
    2. Load cached entries from database into memory cache

    Should be called during application startup.

    Args:
        db: SQLAlchemy database session
    """
    # Define callback for database persistence
    def save_to_db(query_normalized: str, response: dict, embedding) -> None:
        """Callback to save cache entries to database."""
        try:
            SemanticCacheRepository.save_cache_entry(db, query_normalized, response, embedding)
        except Exception as exc:
            logger.error(f"Failed to save cache entry to DB: {exc}")

    # Register the callback
    set_db_save_callback(save_to_db)
    logger.info("[Semantic Cache] Database persistence callback registered")

    # Load existing cache from database
    try:
        entries = SemanticCacheRepository.load_cache_entries(db, limit=query_cache.max_size)

        for entry in entries:
            query_cache.cache.append({
                "question": entry["question"],
                "response": entry["response"],
                "timestamp": entry["timestamp"],
            })
            query_cache.embeddings.append(entry["embedding"])

        logger.info(
            f"[Semantic Cache] Loaded {len(entries)} entries from database "
            f"(memory cache now has {len(query_cache.cache)} entries)"
        )
    except Exception as exc:
        logger.warning(f"Failed to load cache from database on startup: {exc}")


def get_cache_initialization_function():
    """
    Return a function that can be used as a FastAPI lifespan event.

    Usage in main.py:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            db = SessionLocal()
            initialize_semantic_cache(db)
            db.close()
            yield
            # Shutdown

        app = FastAPI(lifespan=lifespan)
    """
    return initialize_semantic_cache
