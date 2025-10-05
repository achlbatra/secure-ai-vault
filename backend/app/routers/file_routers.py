from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.auth import getCurrentUser
from app.core.database import get_db
from app.models.document import Document
import os, shutil, re, json, csv
import spacy
import pandas as pd

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

PII_PATTERNS = {
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", 2),
    "phone": (r"\\+?\\d[\\d -]{8,12}\\d", 2),
    "ssn": (r"\\d{3}-\\d{2}-\\d{4}", 5),
    "credit_card": (r"\\b(?:\\d[ -]*?){13,16}\\b", 5),
    "passport": (r"[A-PR-WYa-pr-wy][1-9]\\d\\s?\\d{4}[1-9]", 4),
    "ipv4": (r"\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b", 1),
    "ipv6": (r"([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}", 1),
    "dob": (r"\\b\\d{2}[/-]\\d{2}[/-]\\d{4}\\b", 3),
    "zip": (r"\\b\\d{5}(-\\d{4})?\\b", 1),
    "mac": (r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", 1),
    "url": (r"https?://(?:[-\\w.]|(?:%[\\da-fA-F]{2}))+", 1),
    "bank_account": (r"\\b\\d{9,18}\\b", 4),
    "ifsc": (r"[A-Z]{4}0[A-Z0-9]{6}", 3),
    "pan": (r"[A-Z]{5}[0-9]{4}[A-Z]{1}", 3),
    "adhar": (r"\\b\\d{4}\\s\\d{4}\\s\\d{4}\\b", 5)
}

NER_WEIGHTS = {
    "PERSON": 1,
    "GPE": 2,
    "ORG": 2,
    "DATE": 3
}

PII_KEYWORDS = {
    "phone": ["phone", "mobile", "contact"],
    "bank_account": ["account", "iban", "acct"],
    "ssn": ["ssn", "social security"],
    "credit_card": ["card", "cc", "credit"],
    "email": ["email", "mail"],
    "dob": ["dob", "birth", "date"]
}

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


from docx import Document as DocxDocument

nlp = spacy.load("en_core_web_sm")

def is_credit_card(num: str) -> bool:
    num = re.sub(r"\\D", "", num)
    if not 13 <= len(num) <= 16:
        return False
    total = 0
    reverse_digits = num[::-1]
    for i, d in enumerate(reverse_digits):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def read_file_content(file_path, file_type):
    try:
        if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = DocxDocument(file_path)
            content = "\\n".join([para.text for para in doc.paragraphs])
        elif file_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        elif file_type == "text/csv":
            df = pd.read_csv(file_path)
            content = df.to_json()  
        elif file_type == "application/json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            content = json.dumps(data)
        else:
            content = ""
    except Exception as e:
        print("Error reading file:", e)
        content = ""
    return content
def calculate_risk(file_content: str, file_type: str, file_path: str):
    detected_pii = []
    regex_score = 0
    ner_score = 0
    nlp_model = get_nlp()
    doc = nlp_model(file_content)

    # --- Regex-based PII detection ---
    for key, (pattern, weight) in PII_PATTERNS.items():
        matches = re.findall(pattern, file_content)
        count = len(matches)
        if count > 0:
            detected_pii.append(key)
            # Weight severity × occurrence factor
            regex_score += min(weight * count * 1.5, 15)  # cap each type’s impact to avoid skew

    # --- NER-based detection (names, locations, etc.) ---
    for ent in doc.ents:
        if ent.label_ in NER_WEIGHTS:
            detected_pii.append(ent.label_)
            ner_score += NER_WEIGHTS[ent.label_] * 0.5  # reduced weight for NER noise

    # --- Structured file boost ---
    structure_boost = 0
    if file_type in ["text/csv", "application/json"]:
        structure_boost = 10  # structured formats are riskier for PII leaks

    # --- Category Severity Boost ---
    critical_pii = {"ssn", "credit_card", "adhar", "bank_account"}
    if any(p in detected_pii for p in critical_pii):
        regex_score *= 1.5  # critical data = higher risk

    # --- Final Risk Score ---
    raw_score = regex_score + ner_score + structure_boost
    risk_score = min(100, int(raw_score))

    # --- Adjust scale for realism ---
    if risk_score == 0 and len(detected_pii) > 0:
        risk_score = 10  # minimum 10% if any PII detected
    elif risk_score > 0 and risk_score < 20 and any(p in critical_pii for p in detected_pii):
        risk_score += 20  # bump low scores for high-severity PII

    return risk_score, sorted(set(detected_pii))


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

    try:
        content = read_file_content(file_path, file.content_type)
    except:
        content = ""

    risk_score, detected_pii = calculate_risk(content, file.content_type, file_path)

    db_doc.risk_score = risk_score
    detected_pii = list(sorted(set(filter(None, detected_pii))))
    db_doc.detected_pii = json.dumps(detected_pii)
    db_doc.status = "completed"
    db.commit()

    recommendations = []
    if risk_score <= 30:
        recommendations = [
            "Low risk: minimal sanitization needed.",
            "Mask emails and identifiers before sharing."
        ]
    elif risk_score <= 60:
        recommendations = [
            "Moderate risk: mask contact and ID fields.",
            "Consider anonymization for structured data."
        ]
    else:
        recommendations = [
            "High risk: perform full sanitization.",
            "Review file manually before sharing externally."
        ]


    return {"filename": file.filename, "risk_score": risk_score, "detected_pii": detected_pii, "recommendations": recommendations}


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
            "file_type": ALLOWED_MIME.get(d.file_type),
            "uploaded_at": d.created_at,
            "risk_score": d.risk_score,
            "status": d.status,
            "detected_pii": json.loads(d.detected_pii) if d.detected_pii else []
        }
        for d in docs
    ]
