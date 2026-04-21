"""
feedback.py - Thumbs-up/thumbs-down feedback endpoint (Phase 12).

Persists AI response feedback to SQLite via SQLAlchemy.
Graceful fallback to in-memory stub when DB is unavailable (e.g., CI env).

Endpoints:
    POST /feedback/          - Submit thumbs-up/down for an AI response
    GET  /feedback/summary   - Aggregate stats (total, positive rate) per session
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

# ---------------------------------------------------------------------------
# SQLAlchemy bootstrap — graceful degradation when not installed
# ---------------------------------------------------------------------------
try:
    from namo_core.database.core import SessionLocal
    from namo_core.database.models import AIFeedback
    _DB_AVAILABLE = True
except ImportError as _err:
    logger.warning("SQLAlchemy/DB not available — feedback will not be persisted: %s", _err)
    _DB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    session_id: str
    user_query: str
    ai_response: str
    is_positive: bool
    feedback_note: Optional[str] = None


class FeedbackSummaryResponse(BaseModel):
    session_id: str
    total: int
    positive: int
    negative: int
    positive_rate: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", summary="Submit AI response feedback")
def submit_feedback(feedback: FeedbackCreate) -> dict:
    """รับ Feedback ดี/ไม่ดี (👍/👎) จาก Tablet Dashboard และบันทึกลง SQLite.

    Args:
        feedback: session_id, user_query, ai_response, is_positive, feedback_note

    Returns:
        {"status": "success", "id": <new row id>}

    Raises:
        HTTPException 500: DB write error
        HTTPException 503: DB not available
    """
    if not _DB_AVAILABLE:
        logger.info(
            "Feedback stub: session=%s positive=%s", feedback.session_id, feedback.is_positive
        )
        return {
            "status": "accepted",
            "message": "Feedback received (DB not available — install sqlalchemy to persist)",
        }

    db = SessionLocal()
    try:
        row = AIFeedback(
            session_id=feedback.session_id,
            user_query=feedback.user_query,
            ai_response=feedback.ai_response,
            is_positive=int(feedback.is_positive),  # bool → 1/0
            feedback_note=feedback.feedback_note,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info(
            "[Feedback] id=%d session=%s positive=%s",
            row.id, feedback.session_id, feedback.is_positive,
        )
        return {"status": "success", "id": row.id, "message": "บันทึก Feedback เรียบร้อยแล้ว"}
    except Exception as exc:
        db.rollback()
        logger.error("Failed to write feedback to DB: %s", exc)
        raise HTTPException(status_code=500, detail=f"บันทึก Feedback ไม่สำเร็จ: {exc}") from exc
    finally:
        db.close()


@router.get("/summary", response_model=FeedbackSummaryResponse, summary="Feedback stats per session")
def get_feedback_summary(session_id: str) -> FeedbackSummaryResponse:
    """ดึงสถิติ feedback รวมของ session (ใช้ใน Analytics Dashboard).

    Args:
        session_id: classroom session UUID

    Returns:
        FeedbackSummaryResponse with total/positive/negative/positive_rate
    """
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="DB not available")

    db = SessionLocal()
    try:
        rows = db.query(AIFeedback).filter(AIFeedback.session_id == session_id).all()
        total = len(rows)
        positive = sum(1 for r in rows if r.is_positive)
        negative = total - positive
        return FeedbackSummaryResponse(
            session_id=session_id,
            total=total,
            positive=positive,
            negative=negative,
            positive_rate=round(positive / total, 4) if total > 0 else 0.0,
        )
    except Exception as exc:
        logger.error("Failed to query feedback summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Query error: {exc}") from exc
    finally:
        db.close()
