"""Alembic environment — NamoNexus.

Reads database_url from namo_core.config.settings so the same .env / GCP
Secret Manager setup used at runtime governs migrations too.

Usage (from backend/namo_core/):
    alembic upgrade head                     # apply all pending migrations
    alembic downgrade -1                     # roll back one step
    alembic revision --autogenerate -m "msg" # generate new migration from models
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make namo_core importable when running `alembic` from any CWD.
# The alembic.ini sits at backend/namo_core/ so adding its parent gives us
# `import namo_core.*` without installing the package.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Import settings FIRST so .env is loaded before any model import
# ---------------------------------------------------------------------------
from namo_core.config.settings import get_settings  # noqa: E402

# Import all models so autogenerate can diff against metadata
from namo_core.database.core import Base  # noqa: E402
import namo_core.database.models  # noqa: E402, F401  — registers all ORM classes

# ---------------------------------------------------------------------------
# Alembic Config object (wraps alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Forward alembic.ini logging section to Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Inject database URL from settings — overrides anything in alembic.ini
# ---------------------------------------------------------------------------
settings = get_settings()
_db_url: str = settings.database_url

# Swap sqlite+pysqlite for sqlite+pysqlite (no change) or postgres → psycopg2
# Cloud SQL socket path example:
#   postgresql+psycopg2://user:pass@/dbname?host=/cloudsql/project:region:instance
config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — generate SQL script without a live DB connection
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection required).

    Useful for reviewing migration SQL before applying it.
    Run with: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare server defaults so auto-generated migrations are accurate
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — apply migrations against a live connection
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """Run migrations in 'online' mode (requires a live DB connection)."""
    # migrate.py (Cloud SQL Connector path) injects a pre-built connection so
    # we skip engine_from_config entirely — avoids a second TCP dial to localhost.
    injected_conn = config.attributes.get("connection")
    if injected_conn is not None:
        context.configure(
            connection=injected_conn,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # Normal alembic CLI path — build engine from alembic.ini / settings URL.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
