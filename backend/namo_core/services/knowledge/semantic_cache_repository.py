"""Database repository for semantic cache persistence."""

import json
import logging
from typing import Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime

from namo_core.database.models import SemanticCacheEntry

logger = logging.getLogger(__name__)


class SemanticCacheRepository:
    """Handle persistent storage of semantic cache entries in database."""

    @staticmethod
    def save_cache_entry(
        db: Session,
        query_normalized: str,
        response: Dict[str, Any],
        embedding: Optional[np.ndarray] = None,
    ) -> SemanticCacheEntry:
        """
        Save or update a cache entry in the database.

        Args:
            db: SQLAlchemy session
            query_normalized: Normalized (lowercase, stripped) query
            response: LLM response dict
            embedding: Optional embedding vector

        Returns:
            Created or updated SemanticCacheEntry
        """
        try:
            # Serialize response to JSON
            response_json = json.dumps(response, ensure_ascii=False, default=str)

            # Serialize embedding if provided
            embedding_json = None
            if embedding is not None:
                embedding_json = json.dumps(embedding.tolist())

            # Check if entry exists
            entry = db.query(SemanticCacheEntry).filter(
                SemanticCacheEntry.query_normalized == query_normalized
            ).first()

            if entry:
                # Update existing entry
                entry.response_json = response_json
                entry.embedding_vector = embedding_json
                entry.last_accessed = datetime.utcnow()
                entry.access_count += 1
            else:
                # Create new entry
                entry = SemanticCacheEntry(
                    query_normalized=query_normalized,
                    response_json=response_json,
                    embedding_vector=embedding_json,
                    access_count=1,
                )
                db.add(entry)

            db.commit()
            logger.debug(f"[SemanticCacheDB] Saved cache entry for: '{query_normalized[:80]}'")
            return entry

        except Exception as exc:
            logger.error(f"Failed to save cache entry: {exc}")
            db.rollback()
            raise

    @staticmethod
    def load_cache_entries(db: Session, limit: int = 50) -> list[Dict[str, Any]]:
        """
        Load all cache entries from database, ordered by recency.

        Args:
            db: SQLAlchemy session
            limit: Maximum number of entries to load

        Returns:
            List of cache entries with deserialized response and embedding
        """
        try:
            entries = db.query(SemanticCacheEntry).order_by(
                SemanticCacheEntry.last_accessed.desc()
            ).limit(limit).all()

            cache_data = []
            for entry in entries:
                try:
                    response = json.loads(entry.response_json)
                    embedding = None
                    if entry.embedding_vector:
                        embedding = np.array(json.loads(entry.embedding_vector))

                    cache_data.append({
                        "question": entry.query_normalized,
                        "response": response,
                        "embedding": embedding,
                        "timestamp": entry.created_at.timestamp() if entry.created_at else 0,
                        "access_count": entry.access_count,
                    })
                except json.JSONDecodeError as jexc:
                    logger.warning(f"Failed to deserialize cache entry {entry.id}: {jexc}")
                    continue

            logger.info(f"[SemanticCacheDB] Loaded {len(cache_data)} cache entries from database")
            return cache_data

        except Exception as exc:
            logger.error(f"Failed to load cache entries: {exc}")
            return []

    @staticmethod
    def get_cache_stats(db: Session) -> Dict[str, Any]:
        """Get cache statistics from database."""
        try:
            count = db.query(SemanticCacheEntry).count()
            most_accessed = db.query(SemanticCacheEntry).order_by(
                SemanticCacheEntry.access_count.desc()
            ).first()

            return {
                "total_entries": count,
                "most_accessed_query": most_accessed.query_normalized if most_accessed else None,
                "most_accessed_count": most_accessed.access_count if most_accessed else 0,
            }
        except Exception as exc:
            logger.error(f"Failed to get cache stats: {exc}")
            return {"error": str(exc)}

    @staticmethod
    def clear_old_entries(db: Session, days: int = 30) -> int:
        """Delete cache entries older than N days."""
        from datetime import timedelta, datetime as dt

        try:
            cutoff_date = dt.utcnow() - timedelta(days=days)
            deleted = db.query(SemanticCacheEntry).filter(
                SemanticCacheEntry.last_accessed < cutoff_date
            ).delete()
            db.commit()
            logger.info(f"[SemanticCacheDB] Deleted {deleted} old cache entries")
            return deleted
        except Exception as exc:
            logger.error(f"Failed to clear old entries: {exc}")
            db.rollback()
            return 0
