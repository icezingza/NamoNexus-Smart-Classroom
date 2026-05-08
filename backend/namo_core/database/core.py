"""
core.py - Database engine and session factory (Phase 12 / PostgreSQL-ready)

SQLite  → used in local dev / LAN demo (no extra config needed)
PostgreSQL → used in production / Cloud SQL (pool tuning applied automatically)

Connection URL is read from settings.database_url (NAMO_DATABASE_URL env var).
Cloud SQL socket example:
  NAMO_DATABASE_URL=postgresql+psycopg2://user:pass@/dbname?host=/cloudsql/project:region:instance
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from namo_core.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
_db_url: str = settings.database_url

_is_sqlite = _db_url.startswith("sqlite")

# ---------------------------------------------------------------------------
# Engine kwargs — differ between SQLite and PostgreSQL
# ---------------------------------------------------------------------------
if _is_sqlite:
    # SQLite: disable thread check (FastAPI uses a thread pool for sync deps)
    _engine_kwargs: dict = {
        "connect_args": {"check_same_thread": False},
    }
else:
    # PostgreSQL / Cloud SQL: production-grade pool settings
    #   pool_size         — connections kept alive in the pool (default 5)
    #   max_overflow      — extra connections allowed above pool_size (default 10)
    #   pool_pre_ping     — issues a lightweight SELECT 1 before each checkout
    #                       to automatically drop stale/closed connections
    #   pool_recycle      — recycle connections older than N seconds to avoid
    #                       hitting Cloud SQL's idle-connection timeout (~600s)
    _engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,  # 5 minutes — well within Cloud SQL's 10-min idle limit
    }

engine = create_engine(_db_url, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Optional: log slow queries in development
# ---------------------------------------------------------------------------
if _is_sqlite and settings.env == "development":
    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[misc]
        import time
        conn.info.setdefault("query_start_time", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[misc]
        import time
        elapsed = time.monotonic() - conn.info["query_start_time"].pop()
        if elapsed > 0.1:  # warn if query takes > 100ms
            logger.warning("Slow query (%.3fs): %.120s", elapsed, statement.strip())

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Declarative base — imported by all model files
# ---------------------------------------------------------------------------
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a scoped DB session, always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
