from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey, Boolean, Float
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
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    pii_count = Column(Integer, default=0)
    context_multiplier = Column(Float, default=1.0)
    density_factor = Column(Float, default=1.0)
    sanitization_method = Column(String(50))
    is_sanitized = Column(Boolean, default=False)
    recommendations = Column(Text, nullable=True)  # JSON string of recommendations

