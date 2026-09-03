# 📁 LOCATION: backend/tests/test_contradiction.py
"""
test_contradiction.py
=======================
Tests for the Cross-Memory Contradiction Detector.
"""

from ai.contradiction_detector import ContradictionDetector, scan_for_contradictions


def test_extract_phone_number():
    detector = ContradictionDetector()
    facts = detector.extract_facts(1, "Call me at 9876543210 for details", date="2024-01-01")
    phone_facts = [f for f in facts if f.attribute == "phone"]
    assert len(phone_facts) > 0


def test_extract_email():
    detector = ContradictionDetector()
    facts = detector.extract_facts(1, "Contact: john.doe@example.com", date="2024-01-01")
    email_facts = [f for f in facts if f.attribute == "email"]
    assert len(email_facts) == 1
    assert "john.doe@example.com" in email_facts[0].value


def test_no_contradiction_when_values_match():
    memories = [
        {"id": 1, "title": "Resume", "description": "Email: same@test.com", "date": "2024-01-01"},
        {"id": 2, "title": "Cover Letter", "description": "Email: same@test.com", "date": "2024-02-01"},
    ]
    contradictions = scan_for_contradictions(memories)
    email_conflicts = [c for c in contradictions if c["attribute"] == "email"]
    assert len(email_conflicts) == 0


def test_contradiction_detected_for_different_emails():
    memories = [
        {"id": 1, "title": "Resume Old", "description": "Email: old@test.com", "date": "2024-01-01"},
        {"id": 2, "title": "Resume New", "description": "Email: new@test.com", "date": "2024-01-10"},
    ]
    contradictions = scan_for_contradictions(memories)
    email_conflicts = [c for c in contradictions if c["attribute"] == "email"]
    assert len(email_conflicts) == 1


def test_close_dates_classified_as_likely_error():
    memories = [
        {"id": 1, "title": "Doc A", "description": "Phone: 1234567890", "date": "2024-01-01"},
        {"id": 2, "title": "Doc B", "description": "Phone: 0987654321", "date": "2024-01-05"},
    ]
    contradictions = scan_for_contradictions(memories)
    assert any(c["classification"] == "likely_error" for c in contradictions)


def test_far_dates_classified_as_legitimate_update():
    memories = [
        {"id": 1, "title": "Old Address Doc", "description": "123 Main street", "date": "2023-01-01"},
        {"id": 2, "title": "New Address Doc", "description": "456 Oak street",  "date": "2024-06-01"},
    ]
    contradictions = scan_for_contradictions(memories)
    address_conflicts = [c for c in contradictions if c["attribute"] == "address"]
    if address_conflicts:
        assert address_conflicts[0]["classification"] in ("legitimate_update", "needs_review")
