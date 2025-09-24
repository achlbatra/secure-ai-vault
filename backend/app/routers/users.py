from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.auth import getCurrentUser
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

class UserResponse(BaseModel):
    id: int
    email: str
    class Config:
        orm_mode = True

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(getCurrentUser)):
    return current_user
