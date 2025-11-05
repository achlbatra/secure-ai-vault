from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.user import User
from app.core.database import get_db
from app.core.auth import getCurrentUser
import os, shutil, json, re, uuid
import pandas as pd
import spacy
from datetime import datetime
from pathlib import Path
from app.models.dashboard import DashboardItem
from app.models.document import Document
import json

def update_dashboard_summary(db, user_id: int):
    """
    Update or insert dashboard summary for a given user_id.
    """
    # Get all user's documents
    docs = db.query(Document).filter(Document.user_id == user_id).all()
    total_docs = len(docs)
    avg_risk = round(sum(d.risk_score for d in docs if d.risk_score) / len(docs), 2) if docs else 0

    pii_count = 0
    for d in docs:
        try:
            pii_data = json.loads(d.detected_pii) if d.detected_pii else []
            pii_count += len(pii_data)
        except Exception:
            continue

    pending_reviews = len([d for d in docs if d.risk_score and d.risk_score > 60])
    security_score = max(0, 100 - int(avg_risk * 0.8))

    # Fetch or create dashboard item for user
    dashboard_item = db.query(DashboardItem).filter(DashboardItem.user_id == user_id).first()

    if dashboard_item:
        # Update existing entry
        dashboard_item.documents_processed = total_docs
        dashboard_item.security_score = security_score
        dashboard_item.pii_items_protected = pii_count
        dashboard_item.pending_reviews = pending_reviews
    else:
        # Insert new entry
        dashboard_item = DashboardItem(
            user_id=user_id,
            documents_processed=total_docs,
            security_score=security_score,
            pii_items_protected=pii_count,
            pending_reviews=pending_reviews,
        )
        db.add(dashboard_item)

    db.commit()


router = APIRouter(prefix="/files", tags=["files"])

BACKEND_DIR = Path(__file__).resolve().parents[2]          # .../backend
UPLOAD_DIR = BACKEND_DIR / "uploads"                       # backend/uploads
SANITIZED_DIR = BACKEND_DIR / "sanitized"                  # backend/sanitized
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SANITIZED_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_MB = 25
ALLOWED_TYPES = {
    "text/plain": "txt",
    "text/csv": "csv",
    "application/json": "json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
}

_nlp = spacy.load("en_core_web_sm")

PII_PATTERNS = {
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", 3),
    "phone": (r"\+?\d[\d\s\-]{8,15}", 2),
    "ssn": (r"\d{3}-\d{2}-\d{4}", 4),
    "credit_card": (r"\b(?:\d[ -]*?){13,16}\b", 5),
}

# --- File Reader ---
def read_file_content(file_path: Path, mime: str) -> str:
    try:
        if mime == "text/plain":
            return file_path.read_text(encoding="utf-8", errors="ignore")
        if mime == "text/csv":
            return pd.read_csv(file_path).to_json(orient="records")
        if mime == "application/json":
            return json.dumps(json.load(file_path.open()))
        if mime.endswith("document"):
            from docx import Document as Docx
            return "\n".join(p.text for p in Docx(file_path).paragraphs)
        return ""
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to read file: {str(e)}")

"""
Enhanced Risk Scoring Engine with Improved PII Detection
"""
import re
import spacy
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    LOW = (0, 30)
    MEDIUM = (31, 60)
    HIGH = (61, 85)
    CRITICAL = (86, 100)

@dataclass
class PIIMatch:
    type: str
    value: str
    position: int
    confidence: float
    risk_weight: int

class EnhancedRiskCalculator:
    """Improved risk calculation with confidence scoring and context awareness."""
    
    # Enhanced PII patterns with capture groups and validation
    PII_PATTERNS = {
        "EMAIL": {
            "pattern": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
            "weight": 5,
            "validation": lambda x: "@" in x and "." in x.split("@")[1]
        },
        "PHONE": {
            "pattern": r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            "weight": 4,
            "validation": lambda x: len(re.sub(r"\D", "", x)) >= 10
        },
        "SSN": {
            "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
            "weight": 10,
            "validation": lambda x: x != "000-00-0000" and not x.startswith("666")
        },
        "CREDIT_CARD": {
            "pattern": r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            "weight": 10,
            "validation": lambda x: EnhancedRiskCalculator._luhn_check(x)
        },
        "PASSPORT": {
            "pattern": r"\b[A-Z]{1,2}\d{6,9}\b",
            "weight": 9,
            "validation": lambda x: len(x) >= 7
        },
        "DRIVERS_LICENSE": {
            "pattern": r"\b[A-Z]{1,2}\d{6,8}\b",
            "weight": 7,
            "validation": lambda x: len(x) >= 7
        },
        "BANK_ACCOUNT": {
            "pattern": r"\b\d{9,18}\b",
            "weight": 8,
            "validation": lambda x: 9 <= len(x) <= 18
        },
        "IP_ADDRESS": {
            "pattern": r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
            "weight": 3,
            "validation": lambda x: all(0 <= int(p) <= 255 for p in x.split("."))
        },
        "DOB": {
            "pattern": r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
            "weight": 6,
            "validation": lambda x: True
        },
        "URL": {
            "pattern": r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)",
            "weight": 2,
            "validation": lambda x: True
        }
    }
    
    # NER entity weights with contextual importance
    NER_WEIGHTS = {
        "PERSON": 6,
        "ORG": 3,
        "GPE": 2,
        "DATE": 2,
        "NORP": 2,
        "FAC": 2,
        "MONEY": 3,
        "CARDINAL": 1
    }
    
    # Context-based risk modifiers
    RISK_CONTEXTS = {
        "medical": ["diagnosis", "patient", "prescription", "treatment", "health", "medical"],
        "financial": ["account", "balance", "payment", "transaction", "invoice", "credit"],
        "legal": ["confidential", "attorney", "legal", "lawsuit", "contract"],
        "personal": ["private", "personal", "confidential", "sensitive"]
    }
    
    def __init__(self):
        self._nlp = spacy.load("en_core_web_sm")
        self._pii_cache = {}
    
    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        digits = [int(d) for d in re.sub(r"\D", "", card_number)]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0
    
    def _detect_regex_pii(self, content: str) -> List[PIIMatch]:
        """Enhanced regex-based PII detection with validation."""
        matches = []
        
        for pii_type, config in self.PII_PATTERNS.items():
            pattern = config["pattern"]
            weight = config["weight"]
            validator = config["validation"]
            
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = match.group(0)
                
                # Validate match
                try:
                    if validator(value):
                        matches.append(PIIMatch(
                            type=pii_type,
                            value=value,
                            position=match.start(),
                            confidence=0.9,
                            risk_weight=weight
                        ))
                except Exception:
                    continue
        
        return matches
    
    def _detect_ner_pii(self, content: str) -> List[PIIMatch]:
        """NER-based contextual PII detection."""
        matches = []
        doc = self._nlp(content[:100000])  # Limit for performance
        
        for ent in doc.ents:
            if ent.label_ in self.NER_WEIGHTS:
                # Calculate confidence based on context
                confidence = self._calculate_ner_confidence(ent, doc)
                
                matches.append(PIIMatch(
                    type=ent.label_,
                    value=ent.text,
                    position=ent.start_char,
                    confidence=confidence,
                    risk_weight=self.NER_WEIGHTS[ent.label_]
                ))
        
        return matches
    
    def _calculate_ner_confidence(self, entity, doc) -> float:
        """Calculate confidence score based on entity context."""
        base_confidence = 0.7
        
        # Check surrounding context
        start_token = entity.start - 5 if entity.start >= 5 else 0
        end_token = entity.end + 5 if entity.end + 5 < len(doc) else len(doc)
        context = doc[start_token:end_token].text.lower()
        
        # Boost confidence if in sensitive context
        for context_type, keywords in self.RISK_CONTEXTS.items():
            if any(kw in context for kw in keywords):
                base_confidence += 0.1
                break
        
        return min(base_confidence, 1.0)
    
    def _calculate_context_multiplier(self, content: str) -> float:
        """Calculate risk multiplier based on document context."""
        content_lower = content.lower()
        multiplier = 1.0
        
        for context_type, keywords in self.RISK_CONTEXTS.items():
            matched = sum(1 for kw in keywords if kw in content_lower)
            if matched >= 2:
                multiplier += 0.2
        
        return min(multiplier, 2.0)
    
    def _calculate_density_factor(self, matches: List[PIIMatch], content_length: int) -> float:
        """Calculate PII density factor."""
        if content_length == 0:
            return 1.0
        
        pii_density = len(matches) / (content_length / 1000)  # Per 1000 chars
        
        if pii_density > 10:
            return 1.5
        elif pii_density > 5:
            return 1.3
        elif pii_density > 2:
            return 1.1
        return 1.0
    
    def calculate_risk(self, content: str) -> Tuple[int, Dict[str, List[str]], Dict]:
        """
        Calculate comprehensive risk score with detailed breakdown.
        
        Returns:
            (risk_score, detected_pii, risk_details)
        """
        if not content or len(content.strip()) == 0:
            return 0, {}, {}
        
        # Detect PII from both sources
        regex_matches = self._detect_regex_pii(content)
        ner_matches = self._detect_ner_pii(content)
        
        # Deduplicate matches by position
        all_matches = self._deduplicate_matches(regex_matches + ner_matches)
        
        # Calculate base score
        base_score = sum(
            match.risk_weight * match.confidence 
            for match in all_matches
        )
        
        # Apply context multiplier
        context_multiplier = self._calculate_context_multiplier(content)
        
        # Apply density factor
        density_factor = self._calculate_density_factor(all_matches, len(content))
        
        # Calculate final risk score
        final_score = base_score * context_multiplier * density_factor
        risk_score = int(min(final_score, 100))
        
        # Organize detected PII by type
        detected_pii = {}
        for match in all_matches:
            if match.type not in detected_pii:
                detected_pii[match.type] = []
            detected_pii[match.type].append(match.value)
        
        # Remove duplicates
        detected_pii = {k: list(set(v)) for k, v in detected_pii.items()}
        
        # Build risk details
        risk_details = {
            "risk_level": self._get_risk_level(risk_score),
            "pii_count": len(all_matches),
            "unique_pii_types": len(detected_pii),
            "base_score": round(base_score, 2),
            "context_multiplier": round(context_multiplier, 2),
            "density_factor": round(density_factor, 2),
            "high_risk_items": [
                match.type for match in all_matches 
                if match.risk_weight >= 8
            ],
            "recommendations": self._generate_recommendations(risk_score, detected_pii)
        }
        
        return risk_score, detected_pii, risk_details
    
    def _deduplicate_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove duplicate matches based on position overlap."""
        if not matches:
            return []
        
        sorted_matches = sorted(matches, key=lambda x: (x.position, -x.risk_weight))
        deduplicated = [sorted_matches[0]]
        
        for match in sorted_matches[1:]:
            # Check if overlaps with previous match
            if match.position > deduplicated[-1].position + len(deduplicated[-1].value):
                deduplicated.append(match)
        
        return deduplicated
    
    def _get_risk_level(self, score: int) -> str:
        """Get risk level category."""
        for level in RiskLevel:
            min_score, max_score = level.value
            if min_score <= score <= max_score:
                return level.name
        return "UNKNOWN"
    
    def _generate_recommendations(self, score: int, detected_pii: Dict) -> List[str]:
        """Generate context-aware recommendations."""
        recommendations = []
        
        if score >= 86:
            recommendations.extend([
                "🔴 CRITICAL: Implement full anonymization immediately",
                "Conduct manual security review before sharing",
                "Use encryption for data at rest and in transit",
                "Consider data minimization - remove unnecessary PII"
            ])
        elif score >= 61:
            recommendations.extend([
                "🟠 HIGH RISK: Apply strong sanitization techniques",
                "Use synthetic data replacement for sensitive fields",
                "Implement access controls and audit logging",
                "Review data retention policies"
            ])
        elif score >= 31:
            recommendations.extend([
                "🟡 MODERATE: Apply targeted masking to identified PII",
                "Consider tokenization for reversible protection",
                "Implement role-based access controls"
            ])
        else:
            recommendations.extend([
                "🟢 LOW RISK: Apply selective masking where needed",
                "Maintain standard security practices"
            ])
        
        # Add specific recommendations based on PII types
        if "SSN" in detected_pii or "CREDIT_CARD" in detected_pii:
            recommendations.append("⚠️ High-value PII detected - prioritize encryption")
        
        if "EMAIL" in detected_pii and len(detected_pii["EMAIL"]) > 10:
            recommendations.append("📧 Multiple emails detected - consider bulk anonymization")
        
        return recommendations


# Usage in FastAPI endpoint
def calculate_risk(content: str):
    """Wrapper function for backward compatibility."""
    calculator = EnhancedRiskCalculator()
    risk_score, detected_pii, details = calculator.calculate_risk(content)
    
    # Convert to format expected by existing code
    detected_pii_list = sorted(detected_pii.keys())
    
    return risk_score, detected_pii_list, details


# --- File Validation ---
def validate_file(upload: UploadFile):
    ext = Path(upload.filename).suffix.lower()
    if upload.content_type not in ALLOWED_TYPES or ext.strip(".") not in ALLOWED_TYPES.values():
        raise HTTPException(400, detail="Invalid or unsupported file type")
    upload.file.seek(0, os.SEEK_END)
    size_mb = upload.file.tell() / (1024 * 1024)
    if size_mb > MAX_FILE_MB:
        raise HTTPException(400, detail=f"File too large ({size_mb:.2f} MB). Limit: {MAX_FILE_MB} MB")
    upload.file.seek(0)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    validate_file(file)
    user_id = current_user.id

    unique_name = f"{user_id}_{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / unique_name

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(500, detail=f"Error saving file: {str(e)}")

    content = read_file_content(file_path, file.content_type)
    risk_score, detected, details = calculate_risk(content)  # Now returns 3 values

    # Save to DB
    documents = Document(
        file_name=file.filename,
        file_path=str(file_path),
        file_type=file.content_type,
        user_id=user_id,
        status="uploaded",
        risk_score=risk_score,
        detected_pii=json.dumps(detected),
        recommendations=json.dumps(details["recommendations"]),
        risk_level=details["risk_level"],
        pii_count=details["pii_count"],
        context_multiplier=details["context_multiplier"],
        density_factor=details["density_factor"]
    )
    db.add(documents)
    db.commit()
    db.refresh(documents)

    update_dashboard_summary(db, current_user.id)

    return {
        "filename": file.filename,
        "stored_as": unique_name,
        "risk_score": risk_score,
        "risk_level": details["risk_level"],
        "detected_pii": detected,
        "pii_count": details["pii_count"],
        "recommendations": details["recommendations"],
        "high_risk_items": details.get("high_risk_items", []),
        "risk_breakdown": {
            "base_score": details["base_score"],
            "context_multiplier": details["context_multiplier"],
            "density_factor": details["density_factor"]
        }
    }


# --- Recent Uploads ---
@router.get("/list-recent-uploads")
def list_recent_uploads(db: Session = Depends(get_db), current_user: User = Depends(getCurrentUser)):
    user_id = current_user.id
    recent_docs = (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    )
    return recent_docs


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db), current_user = Depends(getCurrentUser)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    result = []
    for d in docs:
        result.append({
            "id": getattr(d, "id", None),
            "filename": getattr(d, "file_name", None),  # Fixed: use file_name from model
            # stored_as is the on-disk filename (basename of file_path)
            "stored_as": Path(getattr(d, "file_path", "")).name if getattr(d, "file_path", None) else None,
            "file_path": getattr(d, "file_path", None),
            "file_type": ALLOWED_TYPES.get(getattr(d, "file_type", None), "unknown"),
            "uploaded_at": getattr(d, "created_at", None),
            "created_at": getattr(d, "created_at", None),  # Add this for frontend compatibility
            "risk_score": getattr(d, "risk_score", None),
            "status": getattr(d, "status", None),
            "detected_pii": json.loads(d.detected_pii) if getattr(d, "detected_pii", None) and isinstance(d.detected_pii, str) else (d.detected_pii or []),
            "recommendations": json.loads(d.recommendations) if getattr(d, "recommendations", None) and isinstance(d.recommendations, str) else (d.recommendations or [])
        })
    return result

@router.get("/files")
def list_files(name: str = None, db: Session = Depends(get_db), current_user = Depends(getCurrentUser)):
    try:
        q = db.query(Document).filter(Document.user_id == current_user.id)
        if name:
            q = q.filter(Document.file_name == name)
        docs = q.all()
        out = []
        for d in docs:
            out.append({
                "id": getattr(d, "id", None),
                "file_name": getattr(d, "file_name", None),
                "stored_as": Path(getattr(d, "file_path", "")).name if getattr(d, "file_path", None) else None,
                "file_path": getattr(d, "file_path", None)
            })
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))