from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import traceback
from typing import List, Dict, Optional, Tuple
import os
import re
import json
import hashlib
import secrets
from datetime import datetime
from faker import Faker
import spacy
from pathlib import Path

# Assuming these imports from your project structure
from app.core.database import get_db
from app.core.auth import getCurrentUser
from app.models.user import User
from app.models.document import Document

router = APIRouter(prefix="/sanitize", tags=["sanitize"])

BACKEND_DIR = Path(__file__).resolve().parents[2]          # .../backend
UPLOAD_DIR = BACKEND_DIR / "uploads"                       # backend/uploads
SANITIZED_DIR = BACKEND_DIR / "sanitized"                  # backend/sanitized
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SANITIZED_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SANITIZED_DIR.mkdir(parents=True, exist_ok=True)

# Initialize once at module level for performance
_fake = Faker()
_nlp = None  # Lazy load

def get_nlp():
    """Lazy load spaCy model."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# =====================================
# REQUEST/RESPONSE MODELS
# =====================================
class SanitizeRequest(BaseModel):
    file: str = Field(..., description="Filename to sanitize")
    method: str = Field(..., description="Sanitization method: mask, remove, encrypt, synthetic, tokenize")
    pii: Optional[List[str]] = Field(default=[], description="List of PII types to target")
    partial_mask: Optional[bool] = Field(default=True, description="Use partial masking")
    preserve_structure: Optional[bool] = Field(default=True, description="Preserve document structure")

class BatchSanitizeRequest(BaseModel):
    files: List[str] = Field(..., description="List of filenames to sanitize")
    method: str
    pii: List[str] = []
    partial_mask: bool = True

class DetokenizeRequest(BaseModel):
    file: str
    token_map_file: str

class SanitizationStats(BaseModel):
    total_pii_found: int
    unique_pii_types: int
    pii_types: List[str]
    method_used: str
    reversible: bool
    content_size_original: int
    content_size_sanitized: int
    reduction_ratio: float

class SanitizationResponse(BaseModel):
    message: str
    file: str
    pii_found: Dict[str, List[str]]
    statistics: SanitizationStats
    reversible: bool
    token_map_file: Optional[str] = None

# =====================================
# PII PATTERNS
# =====================================
PII_PATTERNS = {
    "EMAIL": [
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    ],
    "PHONE": [
        r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        r"\+?\d[\d\s\-]{8,15}"
    ],
    "ADDRESS": [
        r"\d{1,5}\s+[\w\s]{2,30}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)\b",
    ],
    "SSN": [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b\d{3}\s\d{2}\s\d{4}\b"
    ],
    "CREDIT_CARD": [
        r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
    ],
    "BANK_ACC": [
        r"\b(?:account|acct|acc)[\s#:]*\d{9,18}\b",
        r"\b\d{9,18}\b"
    ],
    "IP_ADDRESS": [
        r"\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ],
    "DOB": [
        r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b",
        r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b"
    ],
    "PASSPORT": [
        r"\b[A-Z]{1,2}\d{6,9}\b"
    ],
    "DRIVERS_LICENSE": [
        r"\b(?:DL|ID|LICENSE)[\s#:]*[A-Z0-9]{5,20}\b"
    ],
    "URL": [
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)"
    ],
    "MAC_ADDRESS": [
        r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"
    ]
}

# =====================================
# ENHANCED SANITIZER CLASS
# =====================================
class EnhancedSanitizer:
    """Advanced sanitization with multiple methods and reversibility support."""
    
    def __init__(self):
        self._fake = _fake
        self._token_store = {}
        self._salt = secrets.token_hex(16)
    
    # ==========================================
    # VALIDATION HELPERS
    # ==========================================
    
    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        try:
            digits = [int(d) for d in re.sub(r"\D", "", card_number)]
            checksum = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                checksum += digit
            return checksum % 10 == 0
        except:
            return False
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """Basic email validation."""
        return "@" in email and "." in email.split("@")[1] if "@" in email else False
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """Validate phone number has enough digits."""
        digits = re.sub(r"\D", "", phone)
        return 10 <= len(digits) <= 15
    
    @staticmethod
    def _validate_ssn(ssn: str) -> bool:
        """Validate SSN isn't obviously fake."""
        digits = re.sub(r"\D", "", ssn)
        return digits != "000000000" and not digits.startswith("666") and digits != "123456789"
    
    # ==========================================
    # PII DETECTION
    # ==========================================
    
    def find_pii(self, text: str, pii_types: Optional[List[str]] = None) -> Dict[str, List[Tuple[str, int, int]]]:
        """
        Enhanced PII detection with position tracking.
        
        Returns:
            Dict of {pii_type: [(value, start_pos, end_pos), ...]}
        """
        if not text:
            return {}
        
        if pii_types is None or len(pii_types) == 0:
            pii_types = list(PII_PATTERNS.keys()) + ["PERSON", "ORG", "GPE"]
        
        results = {}
        
        # Regex-based detection with positions and validation
        for pii_type in pii_types:
            if pii_type in PII_PATTERNS:
                for pattern in PII_PATTERNS[pii_type]:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        value = match.group(0)
                        
                        # Apply validation
                        is_valid = True
                        if pii_type == "CREDIT_CARD":
                            is_valid = self._luhn_check(value)
                        elif pii_type == "EMAIL":
                            is_valid = self._validate_email(value)
                        elif pii_type == "PHONE":
                            is_valid = self._validate_phone(value)
                        elif pii_type == "SSN":
                            is_valid = self._validate_ssn(value)
                        
                        if is_valid:
                            if pii_type not in results:
                                results[pii_type] = []
                            results[pii_type].append((
                                value,
                                match.start(),
                                match.end()
                            ))
        
        # NER-based detection for names, organizations, etc.
        nlp_types = {"PERSON", "ORG", "GPE", "DATE", "MONEY", "NORP"}
        nlp_requested = [t for t in pii_types if t in nlp_types]
        
        if nlp_requested:
            try:
                nlp = get_nlp()
                # Limit text size for performance
                doc = nlp(text[:100000])
                for ent in doc.ents:
                    if ent.label_ in nlp_requested:
                        if ent.label_ not in results:
                            results[ent.label_] = []
                        results[ent.label_].append((
                            ent.text,
                            ent.start_char,
                            ent.end_char
                        ))
            except Exception as e:
                print(f"NER detection warning: {e}")
        
        # Deduplicate and sort by position
        for pii_type in results:
            results[pii_type] = self._deduplicate_matches(results[pii_type])
        
        return results
    
    def _deduplicate_matches(self, matches: List[Tuple[str, int, int]]) -> List[Tuple[str, int, int]]:
        """Remove overlapping matches, keeping the longest."""
        if not matches:
            return []
        
        sorted_matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1])))
        deduplicated = [sorted_matches[0]]
        
        for match in sorted_matches[1:]:
            if match[1] >= deduplicated[-1][2]:  # No overlap
                deduplicated.append(match)
        
        return deduplicated
    
    # ==========================================
    # SANITIZATION METHODS
    # ==========================================
    
    def _mask_value(self, value: str, pii_type: str, partial: bool = True) -> str:
        """Advanced masking with partial reveal options."""
        if not value:
            return "[MASKED]"
        
        if pii_type == "EMAIL":
            if "@" in value:
                local, domain = value.split("@", 1)
                if partial and len(local) > 2:
                    return f"{local[0]}{'*' * (len(local)-2)}{local[-1]}@{domain}"
                return f"{'*' * len(local)}@{domain}"
        
        elif pii_type in ["PHONE"]:
            digits = re.sub(r"\D", "", value)
            if partial and len(digits) >= 4:
                masked = "*" * (len(digits) - 4) + digits[-4:]
                # Preserve original format if possible
                if "-" in value:
                    return f"***-***-{digits[-4:]}"
                return masked
            return "*" * len(digits)
        
        elif pii_type == "SSN":
            digits = re.sub(r"\D", "", value)
            if partial and len(digits) >= 4:
                return f"***-**-{digits[-4:]}"
            return "***-**-****"
        
        elif pii_type == "CREDIT_CARD":
            digits = re.sub(r"\D", "", value)
            if partial and len(digits) >= 4:
                masked = "*" * (len(digits) - 4) + digits[-4:]
                # Preserve format
                if " " in value or "-" in value:
                    sep = " " if " " in value else "-"
                    return f"****{sep}****{sep}****{sep}{digits[-4:]}"
                return masked
            return "****-****-****-****"
        
        elif pii_type == "BANK_ACC":
            digits = re.sub(r"\D", "", value)
            if partial and len(digits) >= 4:
                return f"***{digits[-4:]}"
            return "***"
        
        elif pii_type == "ADDRESS":
            if partial:
                parts = value.split()
                if len(parts) > 2:
                    return f"*** {parts[-2]} {parts[-1]}"
            return "[ADDRESS REDACTED]"
        
        elif pii_type in ["PERSON", "ORG", "GPE"]:
            if partial and len(value) > 1:
                return f"{value[0]}{'*' * min(len(value)-1, 5)}"
            return "[NAME REDACTED]"
        
        elif pii_type == "DOB":
            if partial:
                return "**/**/****"
            return "[DATE REDACTED]"
        
        elif pii_type == "IP_ADDRESS":
            parts = value.split(".")
            if partial and len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.***.***.***"
            return "***.***.***.***"
        
        elif pii_type == "PASSPORT":
            if partial and len(value) > 3:
                return f"{value[:2]}***{value[-2:]}"
            return "***"
        
        return "[REDACTED]"
    
    def _generate_synthetic(self, pii_type: str) -> str:
        """Generate realistic synthetic data."""
        generators = {
            "EMAIL": lambda: self._fake.email(),
            "PHONE": lambda: self._fake.phone_number(),
            "ADDRESS": lambda: self._fake.address().replace("\n", ", "),
            "PERSON": lambda: self._fake.name(),
            "ORG": lambda: self._fake.company(),
            "GPE": lambda: self._fake.city(),
            "DOB": lambda: self._fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%m/%d/%Y"),
            "SSN": lambda: f"{self._fake.random_int(100, 899)}-{self._fake.random_int(10, 99)}-{self._fake.random_int(1000, 9999)}",
            "CREDIT_CARD": lambda: self._fake.credit_card_number(),
            "BANK_ACC": lambda: str(self._fake.random_int(100000000, 999999999999)),
            "IP_ADDRESS": lambda: self._fake.ipv4(),
            "PASSPORT": lambda: f"{self._fake.random_letter().upper()}{self._fake.random_int(1000000, 9999999)}",
            "DRIVERS_LICENSE": lambda: f"DL{self._fake.random_int(10000000, 99999999)}",
            "MAC_ADDRESS": lambda: self._fake.mac_address(),
            "URL": lambda: self._fake.url(),
            "DATE": lambda: self._fake.date(),
            "MONEY": lambda: f"${self._fake.random_int(10, 10000)}"
        }
        
        return generators.get(pii_type, lambda: "[SYNTHETIC]")()
    
    def _encrypt_value(self, value: str, deterministic: bool = True) -> str:
        """Encrypt value using SHA-256."""
        if deterministic:
            return hashlib.sha256((self._salt + value).encode()).hexdigest()[:16]
        else:
            salt = secrets.token_hex(8)
            return hashlib.sha256((salt + value).encode()).hexdigest()[:16]
    
    def _tokenize_value(self, value: str, pii_type: str) -> str:
        """Create reversible token with secure storage."""
        token = f"TOK_{pii_type}_{secrets.token_hex(8)}"
        self._token_store[token] = value
        return token
    
    def _remove_value(self, value: str, pii_type: str) -> str:
        """Remove value with placeholder."""
        return f"[{pii_type}_REMOVED]"
    
    # ==========================================
    # MAIN SANITIZATION
    # ==========================================
    
    def sanitize(
        self, 
        content: str, 
        pii_types: Optional[List[str]] = None,
        method: str = "mask",
        preserve_structure: bool = True,
        partial_mask: bool = True
    ) -> Dict:
        """
        Comprehensive sanitization with multiple options.
        
        Args:
            content: Text to sanitize
            pii_types: List of PII types to target (None = all)
            method: Sanitization method to apply
            preserve_structure: Keep original text structure
            partial_mask: Show partial data when masking
        
        Returns:
            Dict with sanitized content and metadata
        """
        if not content:
            return {
                "original": "",
                "sanitized": "",
                "pii_found": {},
                "method_applied": method,
                "reversible": False,
                "statistics": self._get_empty_stats(method)
            }
        
        # Find all PII with positions
        pii_data = self.find_pii(content, pii_types)
        
        if not pii_data:
            return {
                "original": content,
                "sanitized": content,
                "pii_found": {},
                "method_applied": method,
                "reversible": False,
                "statistics": self._get_empty_stats(method)
            }
        
        # Prepare replacements
        replacements = []
        for pii_type, matches in pii_data.items():
            for value, start, end in matches:
                replacement = self._apply_method(value, pii_type, method, partial_mask)
                replacements.append((start, end, value, replacement))
        
        # Sort by position (reverse order to maintain positions)
        replacements.sort(key=lambda x: x[0], reverse=True)
        
        # Apply replacements
        sanitized = content
        for start, end, original, replacement in replacements:
            if preserve_structure and method in ["mask", "partial_mask"]:
                # Try to preserve original length for formatting
                if len(replacement) < len(original):
                    replacement += " " * (len(original) - len(replacement))
            sanitized = sanitized[:start] + replacement + sanitized[end:]
        
        # Format PII data for return
        pii_found = {
            pii_type: list(set([match[0] for match in matches]))
            for pii_type, matches in pii_data.items()
        }
        
        # Calculate statistics
        total_pii = sum(len(matches) for matches in pii_data.values())
        statistics = {
            "total_pii_found": total_pii,
            "unique_pii_types": len(pii_found),
            "pii_types": list(pii_found.keys()),
            "method_used": method,
            "reversible": (method == "tokenize"),
            "content_size_original": len(content),
            "content_size_sanitized": len(sanitized),
            "reduction_ratio": round(
                1 - (len(sanitized) / len(content)),
                2
            ) if content else 0
        }
        
        result = {
            "original": content,
            "sanitized": sanitized,
            "pii_found": pii_found,
            "method_applied": method,
            "reversible": (method == "tokenize"),
            "statistics": statistics
        }
        
        if method == "tokenize":
            result["token_map"] = self._token_store.copy()
        
        return result
    
    def _apply_method(self, value: str, pii_type: str, method: str, partial: bool) -> str:
        """Apply selected sanitization method."""
        if method == "mask" or method == "partial_mask":
            return self._mask_value(value, pii_type, partial)
        elif method == "remove":
            return self._remove_value(value, pii_type)
        elif method == "encrypt":
            return self._encrypt_value(value)
        elif method == "synthetic":
            return self._generate_synthetic(pii_type)
        elif method == "tokenize":
            return self._tokenize_value(value, pii_type)
        else:
            return "[SANITIZED]"
    
    def _get_empty_stats(self, method: str) -> Dict:
        """Return empty statistics."""
        return {
            "total_pii_found": 0,
            "unique_pii_types": 0,
            "pii_types": [],
            "method_used": method,
            "reversible": False,
            "content_size_original": 0,
            "content_size_sanitized": 0,
            "reduction_ratio": 0.0
        }
    
    def detokenize(self, content: str, token_map: Dict[str, str]) -> str:
        """Reverse tokenization to restore original values."""
        result = content
        for token, original in token_map.items():
            result = result.replace(token, original)
        return result

# =====================================
# HELPER FUNCTIONS
# =====================================
def read_file_content(file_path: Path) -> str:
    print(f"Reading file content from: {file_path}")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if file_path.suffix.lower() == ".docx":
        try:
            from docx import Document as Docx
            doc = Docx(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read docx: {str(e)}")


    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return file_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    raise HTTPException(status_code=500, detail="Unable to read file with supported encodings")



def resolve_file_path(db: Session, filename: str, user_id: int) -> Path:
    candidate = UPLOAD_DIR / filename
    if candidate.exists():
        return candidate
    try:
        doc = db.query(Document).filter(
            (Document.file_name == filename) | (Document.stored_as == filename),
            Document.user_id == user_id
        ).first()
        if doc and getattr(doc, "file_path", None):
            p = Path(doc.file_path)
            if p.exists():
                return p
    except Exception:
        pass
    return candidate


def save_token_map(token_map: Dict, filename: str) -> str:
    """Save token map to file for later detokenization."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    token_file = f"tokens_{timestamp}_{filename}.json"
    token_path = UPLOAD_DIR / token_file
    
    with open(token_path, 'w') as f:
        json.dump(token_map, f, indent=2)
    
    return token_file

def update_document_sanitization(db: Session, filename: str, method: str, user_id: int):
    """Update document record with sanitization info."""
    doc = db.query(Document).filter(
        Document.file_name == filename,
        Document.user_id == user_id
    ).first()
    
    if doc:
        doc.is_sanitized = True
        doc.sanitization_method = method
        db.commit()

# =====================================
# API ROUTES
# =====================================


@router.post("/preview")
async def preview_sanitization(request: SanitizeRequest, db: Session = Depends(get_db), current_user = Depends(getCurrentUser)):
    try:
        file_path = resolve_file_path(db, request.file, current_user.id)
        print(f"Previewing sanitization for file: {file_path}")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file}")


        content = read_file_content(file_path)
        sanitizer = EnhancedSanitizer()
        result = sanitizer.sanitize(content=content, pii_types=request.pii, method=request.method, preserve_structure=request.preserve_structure, partial_mask=request.partial_mask)

        return {
        "original_snippet": content[:1500],
        "sanitized_snippet": result.get("sanitized", "")[:1500],
        "pii_found": result.get("pii_found", []),
        "statistics": result.get("statistics", {}),
        "method_applied": request.method,
        "reversible": result.get("reversible", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print("Preview sanitization traceback:\n", tb)
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/save")
async def sanitize_and_save(request: SanitizeRequest, db: Session = Depends(get_db), current_user = Depends(getCurrentUser)):
    try:
        file_path = resolve_file_path(db, request.file, current_user.id)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file}")

        content = read_file_content(file_path)
        sanitizer = EnhancedSanitizer()
        result = sanitizer.sanitize(
            content=content,
            pii_types=request.pii,
            method=request.method,
            preserve_structure=request.preserve_structure,
            partial_mask=request.partial_mask
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"sanitized_{request.method}_{timestamp}_{Path(file_path).name}"
        output_path = UPLOAD_DIR / output_file
        output_path.write_text(result.get("sanitized", ""), encoding="utf-8")

        token_map_file = None
        if result.get("reversible") and result.get("token_map"):
            token_map_file = save_token_map(result["token_map"], Path(file_path).name)

        try:
            update_document_sanitization(db, Path(file_path).name, request.method, current_user.id)
        except Exception:
            pass

        return {
            "message": "Sanitization successful",
            "file": output_file,
            "pii_found": result.get("pii_found", {}),
            "statistics": result.get("statistics", {}),
            "reversible": result.get("reversible", False),
            "token_map_file": token_map_file
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        print("Sanitization error traceback:\n", tb)
        raise HTTPException(status_code=500, detail=f"Sanitization failed: {str(e)}")



@router.post("/batch")
async def batch_sanitize(
    request: BatchSanitizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(getCurrentUser)
):
    """
    Sanitize multiple files at once.
    """
    results = []
    errors = []
    
    for filename in request.files:
        try:
            file_path = UPLOAD_DIR / filename
            if not file_path.exists():
                errors.append({"file": filename, "error": "File not found"})
                continue
            
            content = read_file_content(file_path)
            
            sanitizer = EnhancedSanitizer()
            result = sanitizer.sanitize(
                content=content,
                pii_types=request.pii if request.pii else None,
                method=request.method,
                partial_mask=request.partial_mask
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"sanitized_{request.method}_{timestamp}_{filename}"
            output_path = UPLOAD_DIR / output_file
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["sanitized"])
            
            # Save token map if needed
            token_map_file = None
            if result["reversible"] and "token_map" in result:
                token_map_file = save_token_map(result["token_map"], filename)
            
            update_document_sanitization(db, filename, request.method, current_user.id)
            
            results.append({
                "original": filename,
                "sanitized": output_file,
                "statistics": result["statistics"],
                "token_map_file": token_map_file
            })
        
        except Exception as e:
            errors.append({"file": filename, "error": str(e)})
    
    return {
        "results": results,
        "total_processed": len(results),
        "total_failed": len(errors),
        "errors": errors
    }


@router.post("/detokenize")
async def detokenize_file(
    request: DetokenizeRequest,
    current_user: User = Depends(getCurrentUser)
):
    """
    Reverse tokenization to restore original values.
    """
    try:
        file_path = UPLOAD_DIR / request.file
        token_map_path = UPLOAD_DIR / request.token_map_file
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Sanitized file not found")
        if not token_map_path.exists():
            raise HTTPException(status_code=404, detail="Token map file not found")
        
        content = read_file_content(file_path)
        
        with open(token_map_path, 'r') as f:
            token_map = json.load(f)
        
        sanitizer = EnhancedSanitizer()
        detokenized = sanitizer.detokenize(content, token_map)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"detokenized_{timestamp}_{request.file}"
        output_path = UPLOAD_DIR / output_file
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(detokenized)
        
        return {
            "message": "Detokenization successful",
            "file": output_file,
            "original_file": request.file
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detokenization failed: {str(e)}")



@router.get("/methods")
async def get_sanitization_methods():
    """Return available sanitization methods and their descriptions."""
    return {
        "methods": [
            {
                "name": "mask",
                "description": "Partially mask sensitive data (e.g., j***@example.com)",
                "reversible": False,
                "use_case": "Sharing data while maintaining readability"
            },
            {
                "name": "partial_mask",
                "description": "Smart masking with visible hints (e.g., ***-1234)",
                "reversible": False,
                "use_case": "Customer service, debugging"
            },
            {
                "name": "remove",
                "description": "Completely remove PII with placeholders",
                "reversible": False,
                "use_case": "Maximum privacy, public sharing"
            },
            {
                "name": "encrypt",
                "description": "Hash PII values (deterministic SHA-256)",
                "reversible": False,
                "use_case": "Analytics, deduplication"
            },
            {
                "name": "synthetic",
                "description": "Replace with realistic fake data",
                "reversible": False,
                "use_case": "Testing, demonstrations, ML training"
            },
            {
                "name": "tokenize",
                "description": "Replace with reversible tokens",
                "reversible": True,
                "use_case": "Secure processing, authorized re-identification"
            }
        ]
    }
