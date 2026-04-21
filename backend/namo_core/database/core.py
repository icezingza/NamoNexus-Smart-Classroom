"""
core.py - Database engine and session factory (Phase 12)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from namo_core.config.settings import get_settings

settings = get_settings()

# Create Database Engine
# (check_same_thread=False is required for SQLite in FastAPI)
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class for Models
Base = declarative_base()

def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
