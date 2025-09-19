from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="user", nullable=False)  # e.g., 'user', 'admin', 'compliance'
    department = Column(String, nullable=True)  # e.g., 'HR', 'Finance', 'IT'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    hashed_password = Column(String, nullable=False)

