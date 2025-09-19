from sqlalchemy import Integer, String, DateTime, func, Column
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # e.g., 'upload', 'delete', 'view'
    document_id = Column(Integer, nullable=False)  # e.g., 'document_id', 'user_id'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())