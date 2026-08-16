"""Synthetic PII enrichment.

The Adult Census benchmark contains no names or emails, but the privacy-audit
workflow needs searchable identities. This module synthesises *deterministic*
names/emails from each record's content hash — the same record always maps to
the same identity, so search/deletion remain reproducible and auditable.

Synthesis is a documented demo affordance; production datasets provide real
identity columns, which take precedence (see :func:`synthesize_identity`).
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


def _seeded_random(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def synthesize_identity(content_hash: str, existing: dict | None = None) -> dict[str, str]:
    """Deterministic identity for a record.

    If the record carries real identity columns (``full_name``/``email``), they
    win. Otherwise synthesize from the content hash.
    """
    if existing:
        full_name = existing.get("full_name") or existing.get("name")
        email = existing.get("email")
        if full_name and email:
            return {"identity_key": _identity_key(full_name), "full_name": full_name, "email": email}

    rng = _seeded_random(content_hash)
    full_name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
    email = f"{full_name.lower().replace(' ', '.')}{rng.randint(1, 999)}@{rng.choice(_DOMAINS)}"
    return {"identity_key": _identity_key(full_name), "full_name": full_name, "email": email}


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
