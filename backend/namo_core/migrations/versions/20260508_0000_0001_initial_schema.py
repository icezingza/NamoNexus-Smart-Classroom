"""initial_schema

Creates all NamoNexus tables from scratch.
Compatible with both SQLite (dev) and PostgreSQL (production / Cloud SQL).

Revision ID: 0001
Revises:
Create Date: 2026-05-08 00:00:00.000000 UTC

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # teachers
    # ------------------------------------------------------------------
    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teachers_id", "teachers", ["id"], unique=False)
    op.create_index("ix_teachers_username", "teachers", ["username"], unique=True)

    # ------------------------------------------------------------------
    # classroom_sessions
    # ------------------------------------------------------------------
    op.create_table(
        "classroom_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column(
            "start_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_classroom_sessions_id", "classroom_sessions", ["id"], unique=False
    )

    # ------------------------------------------------------------------
    # event_logs
    # ------------------------------------------------------------------
    op.create_table(
        "event_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("emotion_state", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["classroom_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_logs_id", "event_logs", ["id"], unique=False)

    # ------------------------------------------------------------------
    # notebooks
    # ------------------------------------------------------------------
    op.create_table(
        "notebooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notebooks_id", "notebooks", ["id"], unique=False)
    op.create_index("ix_notebooks_title", "notebooks", ["title"], unique=False)

    # ------------------------------------------------------------------
    # notebook_sources
    # ------------------------------------------------------------------
    op.create_table(
        "notebook_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notebook_sources_id", "notebook_sources", ["id"], unique=False
    )

    # ------------------------------------------------------------------
    # notebook_contents
    # ------------------------------------------------------------------
    op.create_table(
        "notebook_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("instruction_used", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notebook_contents_id", "notebook_contents", ["id"], unique=False
    )

    # ------------------------------------------------------------------
    # notebook_jobs
    # ------------------------------------------------------------------
    op.create_table(
        "notebook_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("result_content_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"]),
        sa.ForeignKeyConstraint(["result_content_id"], ["notebook_contents.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notebook_jobs_id", "notebook_jobs", ["id"], unique=False)

    # ------------------------------------------------------------------
    # notebook_audit_logs
    # ------------------------------------------------------------------
    op.create_table(
        "notebook_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("notebook_id", sa.Integer(), nullable=True),
        sa.Column("instruction_sanitized", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notebook_audit_logs_id", "notebook_audit_logs", ["id"], unique=False
    )

    # ------------------------------------------------------------------
    # semantic_cache_entries
    # ------------------------------------------------------------------
    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query_normalized", sa.String(), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("embedding_vector", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("last_accessed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_semantic_cache_entries_id", "semantic_cache_entries", ["id"], unique=False
    )
    op.create_index(
        "ix_semantic_cache_entries_query_normalized",
        "semantic_cache_entries",
        ["query_normalized"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # ai_feedback
    # ------------------------------------------------------------------
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("ai_response", sa.Text(), nullable=False),
        sa.Column("is_positive", sa.Integer(), nullable=False),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_feedback_id", "ai_feedback", ["id"], unique=False)
    op.create_index(
        "ix_ai_feedback_session_id", "ai_feedback", ["session_id"], unique=False
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_ai_feedback_session_id", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_id", table_name="ai_feedback")
    op.drop_table("ai_feedback")

    op.drop_index(
        "ix_semantic_cache_entries_query_normalized",
        table_name="semantic_cache_entries",
    )
    op.drop_index(
        "ix_semantic_cache_entries_id", table_name="semantic_cache_entries"
    )
    op.drop_table("semantic_cache_entries")

    op.drop_index(
        "ix_notebook_audit_logs_id", table_name="notebook_audit_logs"
    )
    op.drop_table("notebook_audit_logs")

    op.drop_index("ix_notebook_jobs_id", table_name="notebook_jobs")
    op.drop_table("notebook_jobs")

    op.drop_index("ix_notebook_contents_id", table_name="notebook_contents")
    op.drop_table("notebook_contents")

    op.drop_index("ix_notebook_sources_id", table_name="notebook_sources")
    op.drop_table("notebook_sources")

    op.drop_index("ix_notebooks_title", table_name="notebooks")
    op.drop_index("ix_notebooks_id", table_name="notebooks")
    op.drop_table("notebooks")

    op.drop_index("ix_event_logs_id", table_name="event_logs")
    op.drop_table("event_logs")

    op.drop_index("ix_classroom_sessions_id", table_name="classroom_sessions")
    op.drop_table("classroom_sessions")

    op.drop_index("ix_teachers_username", table_name="teachers")
    op.drop_index("ix_teachers_id", table_name="teachers")
    op.drop_table("teachers")
