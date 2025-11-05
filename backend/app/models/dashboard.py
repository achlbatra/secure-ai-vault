from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class DashboardItem(Base):
    __tablename__ = "dashboard_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    documents_processed = Column(Integer, default=0)
    security_score = Column(Float, default=0.0)
    pii_items_protected = Column(Integer, default=0)
    pending_reviews = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
