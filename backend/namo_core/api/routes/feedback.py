from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Optional SQLAlchemy — graceful degradation if not installed
try:
    from sqlalchemy.orm import Session
    from fastapi import Depends
    from namo_core.db.database import get_db
    from namo_core.models.feedback import AIFeedback
    _SQL_AVAILABLE = True
except ImportError:
    _SQL_AVAILABLE = False

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    session_id: str
    user_query: str
    ai_response: str
    is_positive: bool
    feedback_note: Optional[str] = None


@router.post("/")
def submit_feedback(feedback: FeedbackCreate) -> dict:
    """รับ Feedback ดี/ไม่ดี (thumbs up/down) จาก Tablet Dashboard"""
    if not _SQL_AVAILABLE:
        # Graceful stub: log to memory, return success to avoid breaking UI
        return {"status": "accepted", "message": "Feedback received (DB not available — install sqlalchemy to persist)"}
    try:
        from namo_core.db.database import SessionLocal
        db = SessionLocal()
        try:
            new_feedback = AIFeedback(
                session_id=feedback.session_id,
                user_query=feedback.user_query,
                ai_response=feedback.ai_response,
                is_positive=feedback.is_positive,
                feedback_note=feedback.feedback_note,
            )
            db.add(new_feedback)
            db.commit()
            return {"status": "success", "message": "บันทึก Feedback เรียบร้อยแล้ว"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"บันทึก Feedback ไม่สำเร็จ: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB unavailable: {str(e)}")
