from __future__ import annotations

from app.services.pii_detection import PIIDetectionEngine

engine = PIIDetectionEngine()


def test_email_detection():
    result = engine.analyze("Contact maya.ali@mail.com for support.")
    cats = {f.category for f in result.findings}
    assert "email" in cats
    assert any(f.snippet == "maya.ali@mail.com" for f in result.findings)


def test_indian_government_ids_detected_as_critical():
    text = "Aadhaar 2345 6789 0123, PAN ABCDE1234F, passport M9876543"
    result = engine.analyze(text)
    gov = [f for f in result.findings if f.category == "government_id"]
    assert len(gov) == 3
    assert all(f.severity == "critical" for f in gov)


def test_phone_detection():
    result = engine.analyze("Call +91 9876543210 today")
    assert any(f.category == "phone" for f in result.findings)


def test_credentials_critical():
    result = engine.analyze("api_key=sk-abcdef1234567890")
    assert any(f.severity == "critical" and f.category == "credentials" for f in result.findings)


def test_card_luhn_detection():
    # A valid Luhn card number (Visa test card 4111 1111 1111 1111).
    result = engine.analyze("card 4111 1111 1111 1111")
    assert any(f.category == "financial" for f in result.findings)
    assert any(f.severity == "critical" for f in result.findings)


def test_invalid_card_rejected():
    # Luhn-invalid number must not be flagged as a card.
    result = engine.analyze("card 4532 0112 3456 7891")
    assert not any(f.category == "financial" and f.field == "card" for f in result.findings)


def test_metadata_field_detection():
    result = engine.analyze("", {"aadhaar": "234567890123", "income": 150000})
    cats = {f.category for f in result.findings}
    assert "government_id" in cats
    assert "financial" in cats


def test_severity_ordering_and_risk():
    result = engine.analyze("aadhaar 2345 6789 0123 and email a@b.com")
    assert result.max_severity == "critical"
    assert result.risk_score() > 0
    counts = result.to_dict()["counts_by_severity"]
    assert counts["critical"] >= 1


def test_clean_text_no_findings():
    result = engine.analyze("the quick brown fox jumps over the lazy dog")
    assert result.findings == []
    assert result.risk_score() == 0.0
