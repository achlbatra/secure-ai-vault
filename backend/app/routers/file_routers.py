from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.auth import getCurrentUser
from app.core.database import get_db
from app.models.document import Document
import os, shutil, re
import spacy
import json

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_MIME = {
    "text/csv": "csv",
    "application/json": "json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}
MAX_FILE_SIZE_MB = 25

# Regex PII patterns + weights
PII_PATTERNS = {
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", 2),
    "phone": (r"\+?\d[\d -]{8,12}\d", 2),
    "ssn": (r"\d{3}-\d{2}-\d{4}", 5),
    "credit_card": (r"\b(?:\d[ -]*?){13,16}\b", 5),
    "passport": (r"[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]", 4),
    "ipv4": (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", 1),
    "ipv6": (r"([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}", 1),
    "dob": (r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", 3),
    "zip": (r"\b\d{5}(-\d{4})?\b", 1),
    "mac": (r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", 1),
    "url": (r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",1),
    "bank_account": (r"\b\d{9,18}\b", 4),
    "ifsc": (r"[A-Z]{4}0[A-Z0-9]{6}", 3),
    "pan": (r"[A-Z]{5}[0-9]{4}[A-Z]{1}", 3),
    "adhar": (r"\b\d{4}\s\d{4}\s\d{4}\b", 5)
}

# NLP NER weights
NER_WEIGHTS = {
    "PERSON": 1,
    "GPE": 2,
    "ORG": 2,
    "DATE": 3
}

nlp = spacy.load("en_core_web_sm")

from docx import Document as DocxDocument

def read_file_content(file_path, file_type):
    try:
        if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = DocxDocument(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        elif file_type in ["text/csv", "application/json", "text/plain"]:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""
    except Exception as e:
        print("Error reading file:", e)
        content = ""
    return content


def calculate_risk(file_content: str):
    total_weight = sum(weight for _, weight in PII_PATTERNS.values()) + sum(NER_WEIGHTS.values())
    detected_pii = []

    # Regex detection
    regex_score = 0
    for key, (pattern, weight) in PII_PATTERNS.items():
        if re.search(pattern, file_content):
            detected_pii.append(key)
            regex_score += weight

    # NLP NER detection
    doc = nlp(file_content)
    ner_score = 0
    for ent in doc.ents:
        if ent.label_ in NER_WEIGHTS:
            if ent.label_ not in detected_pii:
                detected_pii.append(ent.label_)
            ner_score += NER_WEIGHTS[ent.label_]

    risk_score = round((regex_score + ner_score) / total_weight * 100)
    return risk_score, detected_pii

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

    # Save initial record
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

    # Read file content
    try:
        content = read_file_content(file_path, file.content_type)
        print(content)
    except:
        content = ""

    # Calculate risk
    risk_score, detected_pii = calculate_risk(content)

    # Update document
    db_doc.risk_score = risk_score
    db_doc.detected_pii = json.dumps(detected_pii)
    db_doc.status = "completed"
    db.commit()

    return {"filename": file.filename, "risk_score": risk_score, "detected_pii": detected_pii}



@router.get("/list-recent-uploads")
def list_recent_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    user_id = current_user.id
    documents = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).limit(10).all()
    return documents

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(getCurrentUser)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    return [
        {
            "filename": d.file_name,
            "uploaded_at": d.created_at,
            "risk_score": d.risk_score,
            "status": d.status,
            "detected_pii": json.loads(d.detected_pii) if d.detected_pii else []
        }
        for d in docs
    ]
