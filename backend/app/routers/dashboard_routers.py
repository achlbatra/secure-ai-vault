from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.dashboard import DashboardItem
from app.models.document import Document
from app.models.user import User
from app.core.database import get_db
from app.core.auth import getCurrentUser
from app.schemas.dashboard_schema import DashboardItemCreate
import json

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    """
    Returns live dashboard statistics for the logged-in user.
    Does NOT write to the database.
    """
    try:
        user_id = current_user.id

        docs = db.query(Document).filter(Document.user_id == user_id).all()
        total_docs = len(docs)
        avg_risk = round(sum(d.risk_score for d in docs if d.risk_score) / len(docs), 2) if docs else 0
        pii_count = 0
        for d in docs:
            try:
                pii_data = json.loads(d.detected_pii) if d.detected_pii else []
                pii_count += len(pii_data)
            except Exception:
                continue

        pending_reviews = len([d for d in docs if d.risk_score and d.risk_score > 60])
        security_score = max(0, 100 - int(avg_risk * 0.8))

        return {
            "documentsProcessed": total_docs,
            "securityScore": security_score,
            "piiItemsProtected": pii_count,
            "pendingReviews": pending_reviews,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/log")
def log_dashboard_item(
    item: DashboardItemCreate,  # ✅ use schema instead of ORM model
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    """
    Manually store a snapshot of dashboard stats in the database for audit purposes.
    """
    try:
        new_entry = DashboardItem(
            user_id=current_user.id,
            documents_processed=item.documents_processed,
            security_score=item.security_score,
            pii_items_protected=item.pii_items_protected,
            pending_reviews=item.pending_reviews,
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return {"message": "Dashboard snapshot stored", "id": new_entry.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
