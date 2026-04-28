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
    notebooks = relationship("Notebook", back_populates="teacher")


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


class Notebook(Base):
    """Personal notebook for teachers to store sources and generated content."""
    __tablename__ = "notebooks"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    title = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    teacher = relationship("Teacher", back_populates="notebooks")
    sources = relationship("NotebookSource", back_populates="notebook", cascade="all, delete-orphan")
    contents = relationship("NotebookContent", back_populates="notebook", cascade="all, delete-orphan")


class NotebookSource(Base):
    """Sources stored within a notebook."""
    __tablename__ = "notebook_sources"

    id = Column(Integer, primary_key=True, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"))
    title = Column(String)
    text = Column(Text)
    source_type = Column(String)  # e.g., "tripitaka", "notes", "pdf"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notebook = relationship("Notebook", back_populates="sources")


class NotebookContent(Base):
    """Generated content (Briefing, Quiz, Flashcards) stored within a notebook."""
    __tablename__ = "notebook_contents"

    id = Column(Integer, primary_key=True, index=True)
    notebook_id = Column(Integer, ForeignKey("notebooks.id"))
    mode = Column(String)  # briefing, faq, audio, flashcard, quiz
    title = Column(String)
    content = Column(Text)
    instruction_used = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notebook = relationship("Notebook", back_populates="contents")


class NotebookJob(Base):
    """Tracks asynchronous generation jobs for notebooks."""
    __tablename__ = "notebook_jobs"

    id = Column(String, primary_key=True, index=True) # Job UUID
    notebook_id = Column(Integer, ForeignKey("notebooks.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    mode = Column(String)
    status = Column(String, default="pending") # pending, completed, failed
    result_content_id = Column(Integer, ForeignKey("notebook_contents.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotebookAuditLog(Base):
    """Security audit trail for notebook activities."""
    __tablename__ = "notebook_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    action = Column(String) # e.g., "list", "view", "generate", "save"
    notebook_id = Column(Integer, nullable=True)
    instruction_sanitized = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


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
