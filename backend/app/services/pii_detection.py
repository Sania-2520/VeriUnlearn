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
from typing import Any, Callable

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

# --- expanded sensitive-data patterns (all treated as sensitive, no exception) ---
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_IFSC = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
_SWIFT = re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b")
_UPI_ID = re.compile(r"(?i)\b[\w.-]+@[a-z0-9]+(?:\.[a-z0-9]+)?\b")
_BANK_ACCOUNT = re.compile(r"(?i)\b(?:bank[ -]?account|account[ -]?no|acc[ -]?no|a/c[ -]?no|iban)\b\s*[:=]?\s*[A-Z0-9-]{6,22}")
_CVV = re.compile(r"(?i)\b(?:cvv|cvc)\b\s*[:=]?\s*\d{3,4}")
_CRYPTO_KEY = re.compile(r"\b(?:0x[a-fA-F0-9]{64}|[1-9A-HJ-NP-Za-km-z]{51})\b")
_OTP = re.compile(r"(?i)\b(?:otp|one[ -]?time[ -]?pass(?:word)?|verification[ -]?code)\b\s*[:=]?\s*\d{4,8}")
_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_IMEI = re.compile(r"\b\d{15}\b")
_IP_ADDR = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)
_DRIVER_LICENSE = re.compile(r"(?i)\b(?:driver['’]?s[ -]?licen[cs]e|driving[ -]?licen[cs]e)\b\s*[:=]?\s*[A-Z0-9-]{4,}")
_VOTER_ID = re.compile(r"(?i)\b(?:voter[ -]?id|epic[ -]?id|election[ -]?card)\b\s*[:=]?\s*[A-Z0-9-]{3,}")

# Keyword-driven sensitive-data terms — every one of these is treated as
# sensitive with no exception, grouped by category and severity.
_KEYWORD_TERMS: list[tuple[str, str, "re.Pattern[str]"]] = [
    ("government_id", "critical", re.compile(r"(?i)\b(ssn|social[ -]?security[ -]?number|aadhaar|aadhar|pan[ -]?card|passport[ -]?number|government[ -]?id)\b")),
    ("financial", "critical", re.compile(r"(?i)\b(ifsc|swift[ -]?code|bank[ -]?account|account[ -]?number|cvv|cvc|upi[ -]?id|debit[ -]?card|credit[ -]?card|card[ -]?number|pin[ -]?number|tax[ -]?record|income[ -]?tax|netbanking|crypto[ -]?wallet|seed[ -]?phrase|private[ -]?key|wallet[ -]?address)\b")),
    ("credentials", "critical", re.compile(r"(?i)\b(password|passwd|api[ -]?key|oauth[ -]?token|session[ -]?cookie|ssh[ -]?key|private[ -]?certificate|recovery[ -]?code|secret[ -]?key|token|otp|one[ -]?time[ -]?password|security[ -]?question|login[ -]?credential)\b")),
    ("biometric", "critical", re.compile(r"(?i)\b(fingerprint|facial[ -]?recognition|face[ -]?id|iris[ -]?scan|voiceprint|retina[ -]?scan|dna[ -]?data|biometric)\b")),
    ("medical", "high", re.compile(r"(?i)\b(medical[ -]?record|diagnosis|prescription|lab[ -]?report|mental[ -]?health|genetic[ -]?data|insurance[ -]?detail|health[ -]?record|patient|blood[ -]?group|symptom|treatment|doctor|hospital)\b")),
    ("employment", "high", re.compile(r"(?i)\b(employee[ -]?id|salary|performance[ -]?review|hr[ -]?record|internal[ -]?company[ -]?document|payslip|ctc|designation|offer[ -]?letter|payroll)\b")),
    ("education", "medium", re.compile(r"(?i)\b(student[ -]?id|transcript|marksheet|grade[ -]?sheet|exam[ -]?roll[ -]?number|admission[ -]?number|report[ -]?card|certificate[ -]?number)\b")),
    ("legal", "high", re.compile(r"(?i)\b(court[ -]?record|lawsuit|litigation|attorney|lawyer|attorney[ -]?client|confidential[ -]?agreement|non[ -]?disclosure|contract|legal[ -]?notice)\b")),
    ("business_confidential", "high", re.compile(r"(?i)\b(trade[ -]?secret|proprietary[ -]?algorithm|product[ -]?roadmap|unreleased[ -]?financials|customer[ -]?list|pricing[ -]?strategy|internal[ -]?document|business[ -]?secret|confidential[ -]?data)\b")),
    ("government_military", "critical", re.compile(r"(?i)\b(classified[ -]?document|restricted[ -]?government[ -]?data|defense[ -]?information|military|top[ -]?secret|state[ -]?secret)\b")),
    ("intellectual_property", "high", re.compile(r"(?i)\b(patent[ -]?draft|unpublished[ -]?research|copyrighted[ -]?manuscript|confidential[ -]?design|trademark|intellectual[ -]?property)\b")),
    ("security_info", "high", re.compile(r"(?i)\b(network[ -]?architecture|firewall[ -]?configuration|vulnerability[ -]?report|penetration[ -]?test|exploit|security[ -]?audit|zero[ -]?day)\b")),
    ("personal_comms", "medium", re.compile(r"(?i)\b(private[ -]?email|private[ -]?chat|private[ -]?message|sms|diary|personal[ -]?correspondence|confidential[ -]?message)\b")),
    ("location", "high", re.compile(r"(?i)\b(live[ -]?gps|gps[ -]?location|home[ -]?address|work[ -]?address|travel[ -]?history|current[ -]?location|latitude|longitude|coordinates)\b")),
    ("children", "high", re.compile(r"(?i)\b(minor['’]?s[ -]?data|child['’]?s[ -]?data|guardian[ -]?detail|school[ -]?record|minor|kindergarten)\b")),
    ("media", "high", re.compile(r"(?i)\b(identity[ -]?document|medical[ -]?image|x[- ]?ray|confidential[ -]?photo|signature[ -]?scan|id[ -]?photo|pan[ -]?image)\b")),
    ("source_code_secret", "critical", re.compile(r"(?i)\b(\.env|database[ -]?credential|cloud[ -]?access[ -]?key|signing[ -]?certificate|connection[ -]?string|db[ -]?password|deployment[ -]?key)\b")),
    ("customer_client", "high", re.compile(r"(?i)\b(crm[ -]?export|invoice[ -]?number|customer[ -]?list|purchase[ -]?history|support[ -]?ticket|client[ -]?data|billing[ -]?detail)\b")),
    ("research", "high", re.compile(r"(?i)\b(unpublished[ -]?dataset|experiment[ -]?result|participant[ -]?information|research[ -]?data|confidential[ -]?study|clinical[ -]?trial)\b")),
    ("corporate_creds", "critical", re.compile(r"(?i)\b(vpn[ -]?credential|vpn[ -]?password|wifi[ -]?password|internal[ -]?dashboard|admin[ -]?account|corporate[ -]?login|company[ -]?portal)\b")),
    ("sensitive_attribute", "high", re.compile(r"(?i)\b(religion|political[ -]?opinion|sexual[ -]?orientation|ethnicity|caste|union[ -]?membership|gender[ -]?identity)\b")),
    ("recovery", "critical", re.compile(r"(?i)\b(backup[ -]?code|recovery[ -]?code|recovery[ -]?email|account[ -]?recovery|security[ -]?code|2fa[ -]?code)\b")),
    ("payment_docs", "high", re.compile(r"(?i)\b(payslip|tax[ -]?return|salary[ -]?slip|payment[ -]?invoice|bank[ -]?statement|salary[ -]?statement)\b")),
    ("device", "medium", re.compile(r"(?i)\b(imei[ -]?number|mac[ -]?address|serial[ -]?number|device[ -]?id|hardware[ -]?id)\b")),
    ("access_logs", "medium", re.compile(r"(?i)\b(audit[ -]?log|access[ -]?log|ip[ -]?address|username|authentication[ -]?event|login[ -]?record|session[ -]?log|user[ -]?agent)\b")),
    ("meeting", "medium", re.compile(r"(?i)\b(meeting[ -]?recording|meeting[ -]?transcript|strategic[ -]?discussion|board[ -]?meeting|executive[ -]?meeting)\b")),
    ("regulatory", "high", re.compile(r"(?i)\b(gdpr|hipaa|pci[ -]?dss|ferpa|protected[ -]?data|regulated[ -]?data|privacy[ -]?regulation)\b")),
]

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Deterministic redaction labels per category (used by ``redact_sensitive``).
_REDACT_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    ("email", _EMAIL),
    ("aadhaar", _AADHAAR),
    ("PAN", _PAN),
    ("passport", _PASSPORT),
    ("SSN", _SSN),
    ("driver's license", _DRIVER_LICENSE),
    ("voter ID", _VOTER_ID),
    ("phone", _PHONE_IN),
    ("phone", _PHONE_GENERIC),
    ("date of birth", _DOB),
    ("IFSC", _IFSC),
    ("SWIFT", _SWIFT),
    ("UPI ID", _UPI_ID),
    ("bank account", _BANK_ACCOUNT),
    ("CVV", _CVV),
    ("crypto key", _CRYPTO_KEY),
    ("OTP", _OTP),
    ("private key", _PRIVATE_KEY),
    ("MAC address", _MAC),
    ("IMEI", _IMEI),
    ("IP address", _IP_ADDR),
    ("medical info", _MEDICAL),
    ("credentials", _CREDENTIAL),
    ("address", _ADDRESS),
    ("identifier", _ID_PREFIX),
    ("card", _CARD),
    ("pincode", _PIN_INDIA),
    ("personal name", _NAME_KEY),
]


def redact_sensitive(text: str) -> str:
    """Replace detected PII with deterministic ``[REDACTED <label>]`` markers.

    Applied in category priority order so overlapping matches (e.g. a phone
    number inside an address line) are masked once. The result is still human
    readable and can be stored as the "after" state of a chat transcript.

    Matches are first replaced with numeric sentinels so a marker can never be
    re-matched by a later pattern (e.g. ``[REDACTED SSN]`` containing uppercase
    letters that a SWIFT/word pattern would otherwise consume).
    """
    if not text:
        return text

    sentinels: list[str] = []

    def _repl(label: str) -> Callable[[re.Match[str]], str]:
        def _apply(_m: re.Match[str]) -> str:
            sentinels.append(f"[REDACTED {label}]")
            return f"\x00{len(sentinels) - 1}\x00"

        return _apply

    for label, pattern in _REDACT_PATTERNS:
        text = pattern.sub(_repl(label), text)
    for i, marker in enumerate(sentinels):
        text = text.replace(f"\x00{i}\x00", marker)
    return text


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

        # ---- expanded sensitive-data detection (no exception) ----
        for match in _SSN.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:16], 0.97, "ssn"))
        for match in _DRIVER_LICENSE.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:32], 0.9, "driver_license"))
        for match in _VOTER_ID.findall(text):
            result.findings.append(Finding("government_id", "critical", match[:32], 0.9, "voter_id"))
        for match in _IFSC.findall(text):
            result.findings.append(Finding("financial", "critical", match[:16], 0.97, "ifsc"))
        for match in _SWIFT.findall(text):
            result.findings.append(Finding("financial", "critical", match[:16], 0.85, "swift"))
        for match in _UPI_ID.findall(text):
            result.findings.append(Finding("financial", "critical", match[:32], 0.85, "upi"))
        for match in _BANK_ACCOUNT.findall(text):
            result.findings.append(Finding("financial", "critical", match[:40], 0.93, "bank_account"))
        for match in _CVV.findall(text):
            result.findings.append(Finding("financial", "critical", match[:16], 0.95, "cvv"))
        for match in _CRYPTO_KEY.findall(text):
            result.findings.append(Finding("financial", "critical", match[:32], 0.95, "crypto_wallet"))
        for match in _OTP.findall(text):
            result.findings.append(Finding("credentials", "critical", match[:24], 0.93, "otp"))
        for match in _PRIVATE_KEY.findall(text):
            result.findings.append(Finding("credentials", "critical", match[:48], 0.99, "private_key"))
        for match in _MAC.findall(text):
            result.findings.append(Finding("device", "medium", match[:24], 0.95, "mac_address"))
        for match in _IMEI.findall(text):
            result.findings.append(Finding("device", "medium", match[:16], 0.93, "imei"))
        for match in _IP_ADDR.findall(text):
            result.findings.append(Finding("access_logs", "medium", match[:20], 0.85, "ip_address"))

        for category, severity, pattern in _KEYWORD_TERMS:
            for match in pattern.findall(text):
                snippet = match if isinstance(match, str) else str(match[0])
                result.findings.append(Finding(category, severity, snippet[:40], 0.8))

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
