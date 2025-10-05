from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(Text, nullable=False)
    risk_score = Column(Integer, nullable=True)
    status = Column(String, default="pending")  # e.g., 'uploaded', 'processing', 'completed'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    detected_pii = Column(Text, nullable=True)  # JSON string of detected PII types

