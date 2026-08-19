"""Synthetic PII enrichment (extended identity profile).

Demo datasets (e.g. Adult Census) carry no real identity fields, but the
privacy-audit workflow needs searchable identities across *many* field types
(name, email, phone, Aadhaar, PAN, passport, DOB, address, customer/employee
ids). This module synthesises **deterministic** values from each record's
content hash — the same record always maps to the same profile, so search and
deletion stay reproducible and auditable.

Real datasets provide identity columns which take precedence
(see :func:`synthesize_identity`). All values are synthetic demo data.
"""
from __future__ import annotations

import hashlib
import random

_FIRST_NAMES = [
    "Aarav", "Maya", "Liam", "Sofia", "Noah", "Zara", "Ethan", "Amara",
    "Lucas", "Priya", "Mateo", "Ingrid", "Kai", "Yuki", "Omar", "Nadia",
    "Felix", "Greta", "Ravi", "Chloe", "Hugo", "Leila", "Ivan", "Freya",
    "Diego", "Anika", "Jonas", "Mira", "Arjun", "Elena",
]
_LAST_NAMES = [
    "Sharma", "Nguyen", "Garcia", "Kowalski", "Okafor", "Silva", "Novak",
    "Haddad", "Meyer", "Tanaka", "Reyes", "Petrov", "Costa", "Ali", "Berg",
    "Dubois", "Khan", "Moreau", "Sato", "Fischer", "Ivanov", "Nakamura",
    "Rossi", "Bauer", "El-Sayed", "Larsen", "Verma", "Diallo", "Marin", "Cruz",
]
_DOMAINS = ["mail.com", "example.org", "proton.me", "outlook.com", "fastmail.com"]
_STREETS = ["MG Road", "Rose Avenue", "Lake View", "Park Street", "Hill Road", "Garden Lane"]
_CITIES = ["Mumbai", "Bengaluru", "Delhi", "Pune", "Hyderabad", "Chennai"]


def _seeded_random(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _gen_aadhaar(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(12))


def _gen_pan(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"  # PAN excludes I/O
    return "".join(rng.choice(letters) for _ in range(5)) + "".join(str(rng.randint(0, 9)) for _ in range(4)) + rng.choice(letters)


def _gen_passport(rng: random.Random) -> str:
    return rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") + "".join(str(rng.randint(0, 9)) for _ in range(7))


def _gen_phone(rng: random.Random) -> str:
    return "+91" + "".join(str(rng.randint(0, 9)) for _ in range(10))


def _gen_dob(rng: random.Random) -> str:
    return f"{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/{rng.randint(1955, 2005)}"


def _gen_address(rng: random.Random) -> str:
    return f"{rng.randint(1, 999)} {rng.choice(_STREETS)}, {rng.choice(_CITIES)} {rng.randint(100000, 999999)}"


def synthesize_identity(content_hash: str, existing: dict | None = None) -> dict[str, str]:
    """Deterministic identity profile for a record.

    Real identity columns (``full_name``/``name``, ``email``, ``phone``,
    ``aadhaar``, ``pan``, ``passport``, ``dob``, ``address``, ``customer_id``,
    ``employee_id``) take precedence; anything missing is synthesised from the
    content hash.
    """
    existing = existing or {}
    rng = _seeded_random(content_hash)

    full_name = existing.get("full_name") or existing.get("name") or f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
    email = existing.get("email") or f"{full_name.lower().replace(' ', '.')}{rng.randint(1, 999)}@{rng.choice(_DOMAINS)}"
    phone = existing.get("phone") or existing.get("mobile") or _gen_phone(rng)
    aadhaar = existing.get("aadhaar") or _gen_aadhaar(rng)
    pan = existing.get("pan") or _gen_pan(rng)
    passport = existing.get("passport") or _gen_passport(rng)
    dob = existing.get("dob") or existing.get("date_of_birth") or _gen_dob(rng)
    address = existing.get("address") or _gen_address(rng)
    customer_id = existing.get("customer_id") or f"CUST-{rng.randint(10000, 99999)}"
    employee_id = existing.get("employee_id") or f"EMP-{rng.randint(1000, 9999)}"

    return {
        "identity_key": _identity_key(full_name),
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "aadhaar": aadhaar,
        "pan": pan,
        "passport": passport,
        "dob": dob,
        "address": address,
        "customer_id": customer_id,
        "employee_id": employee_id,
    }


def _identity_key(full_name: str) -> str:
    """Stable identity key from a name (lowercased, ascii-folded)."""
    return "".join(c for c in full_name.lower().replace(" ", "") if c.isalnum())


def identity_key(full_name: str) -> str:
    return _identity_key(full_name)


def classify_sensitivity(features: dict) -> str:
    """Heuristic sensitivity classification of a record's feature payload."""
    sensitive_keys = {"health", "medical", "income", "salary", "credit", "ssn", "diagnosis"}
    if any(k in sensitive_keys for k in features):
        return "sensitive"
    return "personal"
