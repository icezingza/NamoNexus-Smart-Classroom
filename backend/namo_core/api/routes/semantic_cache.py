"""REST API endpoints for semantic cache management and monitoring."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from namo_core.database.core import get_db
from namo_core.database.models import SemanticCacheEntry
from namo_core.services.knowledge.semantic_cache import query_cache
from namo_core.services.knowledge.semantic_cache_repository import SemanticCacheRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/semantic-cache", tags=["cache"])


@router.get("/stats")
def get_cache_stats(db: Session = Depends(get_db)) -> dict:
    """Get semantic cache statistics — hit rate, entry count, most accessed queries."""
    db_stats = SemanticCacheRepository.get_cache_stats(db)

    return {
        "memory_cache": {
            "total_entries": len(query_cache.cache),
            "max_size": query_cache.max_size,
            "similarity_threshold": query_cache.similarity_threshold,
            "model_loaded": query_cache.model_loaded,
        },
        "database_cache": db_stats,
        "status": "operational",
    }


@router.get("/entries")
def list_cache_entries(
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
    db: Session = Depends(get_db),
) -> dict:
    """List recent semantic cache entries from database."""
    entries = SemanticCacheRepository.load_cache_entries(db, limit=limit)

    return {
        "count": len(entries),
        "limit": limit,
        "entries": [
            {
                "query": e["question"],
                "access_count": e["access_count"],
                "created_at": e["timestamp"],
            }
            for e in entries
        ],
    }


@router.post("/clear")
def clear_cache(
    older_than_days: int = Query(
        30, ge=1, le=365, description="Clear entries older than N days"
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Delete old semantic cache entries to free up database space."""
    deleted_count = SemanticCacheRepository.clear_old_entries(db, days=older_than_days)

    return {
        "deleted_entries": deleted_count,
        "older_than_days": older_than_days,
        "message": f"Cleared {deleted_count} cache entries older than {older_than_days} days",
    }


@router.get("/threshold")
def get_threshold() -> dict:
    """Get current similarity threshold for cache matching."""
    return {
        "current_threshold": query_cache.similarity_threshold,
        "min": 0.0,
        "max": 1.0,
        "description": "Higher threshold = stricter matching (fewer false positives)",
    }


@router.post("/threshold")
def set_threshold(
    threshold: float = Query(..., ge=0.0, le=1.0, description="New similarity threshold"),
) -> dict:
    """
    Adjust semantic similarity threshold.

    - 0.7: More permissive (accepts lower similarity matches)
    - 0.85: Default (balanced)
    - 0.95: Very strict (only very similar queries match)
    """
    query_cache.set_similarity_threshold(threshold)

    return {
        "new_threshold": threshold,
        "message": f"Similarity threshold updated to {threshold}",
    }


@router.post("/reload")
def reload_cache_from_db(db: Session = Depends(get_db)) -> dict:
    """
    Reload semantic cache from database.

    Useful when restarting the service to restore previous cache entries.
    """
    try:
        entries = SemanticCacheRepository.load_cache_entries(db, limit=query_cache.max_size)

        # Clear in-memory cache and reload from DB
        query_cache.cache.clear()
        query_cache.embeddings.clear()

        for entry in entries:
            query_cache.cache.append({
                "question": entry["question"],
                "response": entry["response"],
                "timestamp": entry["timestamp"],
            })
            query_cache.embeddings.append(entry["embedding"])

        logger.info(f"Reloaded {len(entries)} cache entries from database")

        return {
            "loaded_entries": len(entries),
            "message": f"Successfully reloaded {len(entries)} cache entries",
        }
    except Exception as exc:
        logger.error(f"Failed to reload cache from database: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload cache: {exc}",
        )


@router.delete("/all")
def delete_all_cache(db: Session = Depends(get_db)) -> dict:
    """⚠️ WARNING: Delete ALL semantic cache entries (both memory and database)."""
    try:
        # Clear in-memory cache
        mem_count = len(query_cache.cache)
        query_cache.cache.clear()
        query_cache.embeddings.clear()

        # Clear database cache
        db.query(SemanticCacheEntry).delete()
        db.commit()

        logger.warning("All semantic cache entries cleared by user")

        return {
            "memory_cleared": mem_count,
            "message": "All semantic cache entries have been deleted",
        }
    except Exception as exc:
        logger.error(f"Failed to clear cache: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
