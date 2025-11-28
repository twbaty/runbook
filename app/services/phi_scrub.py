# app/services/phi_scrub.py
import re

# Basic PHI/PII detection patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DOB_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
MRN_RE = re.compile(r"\b(?:MRN[:\s]*\d+|\d{7,10})\b", re.IGNORECASE)

# VERY conservative "looks like a name" pattern
NAME_LIKE_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


def scrub_text(text: str) -> str:
    """Redact obvious PHI/PII before sending to the model."""
    if not text:
        return text

    text = EMAIL_RE.sub("<REDACTED_EMAIL>", text)
    text = PHONE_RE.sub("<REDACTED_PHONE>", text)
    text = SSN_RE.sub("<REDACTED_SSN>", text)
    text = DOB_RE.sub("<REDACTED_DOB>", text)
    text = MRN_RE.sub("<REDACTED_MRN>", text)
    text = NAME_LIKE_RE.sub("<REDACTED_NAME>", text)

    return text
