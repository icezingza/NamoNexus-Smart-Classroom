"""
models.py - SQLAlchemy Models for Persistent Data Analytics (Phase 12)
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from namo_core.database.core import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    sessions = relationship("ClassroomSession", back_populates="teacher")


class ClassroomSession(Base):
    __tablename__ = "classroom_sessions"

    id = Column(String, primary_key=True, index=True)  # UUID for session ID
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    topic = Column(String, nullable=True)

    teacher = relationship("Teacher", back_populates="sessions")
    events = relationship("EventLog", back_populates="session")


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("classroom_sessions.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String)  # e.g., "question", "emotion", "rag_search"
    content = Column(Text)  # The transcript or prompt
    response = Column(Text, nullable=True)  # AI answer
    emotion_state = Column(String, nullable=True)  # "focused", "wandering", etc.
    latency_ms = Column(Float, nullable=True)

    session = relationship("ClassroomSession", back_populates="events")


class SemanticCacheEntry(Base):
    """Persistent storage for semantic cache — enables cache reload on restart."""
    __tablename__ = "semantic_cache_entries"

    id = Column(Integer, primary_key=True, index=True)
    query_normalized = Column(String, unique=True, index=True)  # lowercase, stripped query
    response_json = Column(Text)  # Serialized LLM response
    embedding_vector = Column(Text, nullable=True)  # Serialized numpy array as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), onupdate=func.now())
    access_count = Column(Integer, default=0)  # Track popularity


class AIFeedback(Base):
    """Thumbs-up / thumbs-down feedback from Tablet Dashboard (Phase 12)."""
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_query = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    is_positive = Column(Integer, nullable=False)  # 1 = thumbs-up, 0 = thumbs-down
    feedback_note = Column(Text, nullable=True)  # Optional teacher comment
