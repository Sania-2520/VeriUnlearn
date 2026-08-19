"""Privacy risk analysis engine (Phase 3).

Detects PII categories in record text/metadata with regex + heuristics and
assigns a severity per finding:

- **critical**: government IDs (Aadhaar/PAN/passport), financial (card
  numbers, Luhn-checked), credentials (passwords/API keys)
- **high**: email, phone, date of birth, medical information
- **medium**: address, customer/employee ids
- **low**: name, generic personal data

Every finding carries ``category``, ``severity``, a ``snippet`` and a
confidence score so reports are auditable, not just "PII detected".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_IN = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")
_PHONE_GENERIC = re.compile(r"(?<!\d)(?:\+?\d{1,3}[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}(?!\d)")
_AADHAAR = re.compile(r"\b[2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4}\b")
_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_PASSPORT = re.compile(r"\b[A-Z][0-9]{7}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PIN_INDIA = re.compile(r"\b[1-9][0-9]{5}\b")
_DOB = re.compile(
    r"\b(?:0[1-9]|[12]\d|3[01])[/-](?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}\b"
)
_CREDENTIAL = re.compile(
    r"(?i)\b(password|passwd|api[_-]?key|secret|token|client[_-]?secret)\b\s*[:=]\s*\S+"
)
_MEDICAL = re.compile(
    r"(?i)\b(patient|diagnosis|prescription|blood[ -]?group|medical|symptom|treatment|"
    r"insurance[ -]?id|ssn|social[ -]?security)\b"
)
_ADDRESS = re.compile(
    r"(?i)\b(street|road|rd|avenue|ave|lane|colony|society|layout|city|"
    r"pincode|pin[ -]?code|postal)\b"
)
_ID_PREFIX = re.compile(r"(?i)\b(cust|emp|member|account|policy|ref|order)[-_]?id\b\s*[:=]?\s*[A-Z0-9-]{4,}")
_NAME_KEY = re.compile(r"(?i)\b(name|full[ -]?name|first[ -]?name|last[ -]?name)\b")

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Finding:
    category: str
    severity: str
    snippet: str
    confidence: float = 0.9
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "snippet": self.snippet,
            "confidence": round(self.confidence, 3),
            "field": self.field,
        }


@dataclass
class AnalysisResult:
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "counts_by_severity": {
                s: sum(1 for f in self.findings if f.severity == s)
                for s in ("critical", "high", "medium", "low")
            },
            "counts_by_category": _count_by(self.findings, "category"),
            "risk_score": self.risk_score(),
        }

    def risk_score(self) -> float:
        """0–100 aggregate risk of the analysed content."""
        if not self.findings:
            return 0.0
        total = sum(_SEVERITY_ORDER[f.severity] for f in self.findings)
        return round(min(100.0, total * 12.0), 1)

    @property
    def max_severity(self) -> str:
        if not self.findings:
            return "low"
        return max(self.findings, key=lambda f: _SEVERITY_ORDER[f.severity]).severity


def _count_by(findings: list[Finding], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.category] = counts.get(f.category, 0) + 1
    return counts


def _luhn_valid(digits: str) -> bool:
    try:
        total = 0
        for i, ch in enumerate(reversed(digits)):
            d = int(ch)
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return total % 10 == 0
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PIIDetectionEngine:
    """Category + severity PII detection over text and structured metadata."""

    def analyze(self, text: str, metadata: dict[str, Any] | None = None) -> AnalysisResult:
        metadata = metadata or {}
        result = AnalysisResult()
        self._detect_text(text, result)
        self._detect_metadata(metadata, result)
        # Deduplicate identical (category, snippet) pairs.
        seen: set[tuple[str, str]] = set()
        unique: list[Finding] = []
        for f in result.findings:
            key = (f.category, f.snippet)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        result.findings = unique
        return result

    # -------------------------------------------------------------- text

    def _detect_text(self, text: str, result: AnalysisResult) -> None:
        if not text:
            return
        for match in _EMAIL.findall(text):
            result.findings.append(Finding("email", "high", match[:64], 0.95))
        for match in _AADHAAR.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:32], 0.97, "aadhaar"))
        for match in _PAN.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:16], 0.97, "pan"))
        for match in _PASSPORT.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:16], 0.95, "passport"))
        for match in _PHONE_IN.findall(text):
            result.findings.append(Finding("phone", "high", match[:24], 0.93))
        for match in _PHONE_GENERIC.findall(text):
            result.findings.append(Finding("phone", "high", match[:24], 0.7))
        for match in _DOB.findall(text):
            result.findings.append(Finding("dob", "high", match[:16], 0.9))
        for match in _MEDICAL.findall(text):
            result.findings.append(Finding("medical", "high", match[:40], 0.85))
        for match in _CREDENTIAL.findall(text):
            result.findings.append(Finding("credentials", "critical", match[:48], 0.9))
        for match in _ADDRESS.findall(text):
            result.findings.append(Finding("address", "medium", match[:48], 0.75))
        for match in _ID_PREFIX.findall(text):
            result.findings.append(Finding("identifier", "medium", match[:40], 0.7))
        for match in _CARD.findall(text):
            digits = re.sub(r"\D", "", match)
            if _luhn_valid(digits):
                result.findings.append(Finding("financial", "critical", match[:24], 0.96, "card"))
        for match in _PIN_INDIA.findall(text):
            result.findings.append(Finding("address", "medium", match[:16], 0.6, "pincode"))
        for match in _NAME_KEY.findall(text):
            result.findings.append(Finding("pii", "low", match[:40], 0.6))

    # ---------------------------------------------------------- metadata

    def _detect_metadata(self, metadata: dict[str, Any], result: AnalysisResult) -> None:
        for key, value in metadata.items():
            if value is None:
                continue
            key_l = str(key).lower()
            value_s = str(value)
            if key_l in {"phone", "mobile", "phone_number"} and value_s.strip():
                result.findings.append(Finding("phone", "high", value_s[:24], 0.98, key))
            elif key_l in {"aadhaar", "uid", "aadhar"} and value_s.strip():
                result.findings.append(Finding("government_id", "critical", value_s[:24], 0.99, key))
            elif key_l == "pan" and value_s.strip():
                result.findings.append(Finding("government_id", "critical", value_s[:16], 0.99, key))
            elif key_l in {"passport", "passport_no", "passport_number"} and value_s.strip():
                result.findings.append(Finding("government_id", "critical", value_s[:16], 0.98, key))
            elif key_l in {"dob", "date_of_birth", "birth_date"} and value_s.strip():
                result.findings.append(Finding("dob", "high", value_s[:16], 0.98, key))
            elif key_l in {"email", "email_id"} and value_s.strip():
                result.findings.append(Finding("email", "high", value_s[:48], 0.98, key))
            elif key_l in {"address", "street", "city"} and value_s.strip():
                result.findings.append(Finding("address", "medium", value_s[:48], 0.9, key))
            elif key_l in {"customer_id", "cust_id"} and value_s.strip() or key_l in {"employee_id", "emp_id"} and value_s.strip():
                result.findings.append(Finding("identifier", "medium", value_s[:24], 0.95, key))
            elif key_l in {"card_number", "credit_card", "debit_card"} and value_s.strip():
                result.findings.append(Finding("financial", "critical", value_s[:24], 0.97, key))
            elif key_l in {"password", "api_key", "secret", "token"} and value_s.strip():
                result.findings.append(Finding("credentials", "critical", value_s[:24], 0.95, key))
            elif key_l in {"income", "salary", "credit_score", "balance"} and value_s.strip():
                result.findings.append(Finding("financial", "high", value_s[:24], 0.85, key))
            elif key_l in {"medical", "diagnosis", "health", "blood_group"} and value_s.strip():
                result.findings.append(Finding("medical", "high", value_s[:32], 0.9, key))
