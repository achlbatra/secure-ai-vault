from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.core import auth
from app.core.database import get_db
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from app.core.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: str
    role: str = "user"
    department: str | None = None
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(user_id=user.id, user_email=user.email)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register", response_model=dict)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email=user.email,
        role=user.role,
        department=user.department,
        hashed_password=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}
