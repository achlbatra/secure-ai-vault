from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.auth import getCurrentUser
from app.core.database import get_db
import os, shutil
from app.models.document import Document

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_MIME = {"text/csv": "csv", "application/json": "json", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}
MAX_FILE_SIZE_MB = 25

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    user_id = current_user.id

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="File type not allowed")

    file.file.seek(0, os.SEEK_END)
    size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="File too large")

    unique_filename = f"{user_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    db_doc = Document(
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        user_id=user_id,
        status="uploaded",
        risk_score=None
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    return {"message": "File uploaded successfully", "filename": file.filename}


@router.get("/list-recent-uploads")
def list_recent_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    user_id = current_user.id
    documents = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).limit(10).all()
    return documents