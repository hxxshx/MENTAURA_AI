"""
Automated Test Suite for Light Explainable Risk Scoring (TASK 16).
Verifies rule-based scoring logic, database persistence, and API exposure
in Counsellor Triage Queue and Admin Command Priority Cases.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.pulse import SupportPulse
from backend.app.services.risk_scorer import calculate_risk_score

client = TestClient(app)


def get_cookie(email: str, password: str = "Mentaura@2026") -> str:
    """Helper to log in a user and retrieve their signed session cookie."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.cookies.get("mentaura_session")


# --------------------------------------------------------------------------
# 1. Unit Tests for Rule-Based Risk Scorer Function
# --------------------------------------------------------------------------
def test_risk_scorer_low_score():
    """Scores 0-2 must produce 'low' risk level."""
    res1 = calculate_risk_score(
        wellbeing_state="Safe",
        affecting_factors=[],
        support_needs=[],
        text_note="I am feeling okay today."
    )
    assert res1["risk_score"] == 0
    assert res1["risk_level"] == "low"

    res2 = calculate_risk_score(
        wellbeing_state="Neutral",  # +1
        affecting_factors=["Housing insecurity"],  # +1
        support_needs=[],
        text_note=""
    )
    assert res2["risk_score"] == 2
    assert res2["risk_level"] == "low"


def test_risk_scorer_medium_score():
    """Scores 3-5 must produce 'medium' risk level."""
    res = calculate_risk_score(
        wellbeing_state="Unsafe",  # +2
        affecting_factors=["Financial stress"],  # +1
        support_needs=["Legal aid"],  # +1
        text_note="Looking for information on legal defense."
    )
    assert res["risk_score"] == 4
    assert res["risk_level"] == "medium"
    assert res["breakdown"]["wellbeing_score"] == 2
    assert res["breakdown"]["factors_score"] == 1
    assert res["breakdown"]["needs_score"] == 1


def test_risk_scorer_high_score():
    """Scores 6+ must produce 'high' risk level."""
    res1 = calculate_risk_score(
        wellbeing_state="Very unsafe",  # +3
        affecting_factors=["Threats & Intimidation"],  # +2
        support_needs=["Emergency Protection"],  # +2
        text_note="Someone is following me outside my house."
    )
    assert res1["risk_score"] >= 7
    assert res1["risk_level"] == "high"

    res2 = calculate_risk_score(
        wellbeing_state="Unsafe",  # +2
        affecting_factors=["Self-harm"],  # +3
        support_needs=["Psychological Counselling"],  # +1
        text_note="I feel in danger."  # +1 ("danger")
    )
    assert res2["risk_score"] == 7
    assert res2["risk_level"] == "high"


def test_risk_scorer_text_keyword_cap():
    """Text matching should contribute at most +3 even if multiple keywords appear."""
    res = calculate_risk_score(
        wellbeing_state="Safe",  # +0
        affecting_factors=[],
        support_needs=[],
        text_note="threat danger weapon police court shelter emergency violence attack"
    )
    assert res["breakdown"]["text_score"] == 3
    assert res["risk_score"] == 3
    assert res["risk_level"] == "medium"


# --------------------------------------------------------------------------
# 2. Integration Tests: Pulse Submission Persistence
# --------------------------------------------------------------------------
def test_pulse_submission_stores_risk_level():
    """Submitting a Support Pulse calculates and stores risk_level and risk_score in the database."""
    victim_cookie = get_cookie("victim@mentaura.example")

    pulse_payload = {
        "wellbeing_state": "Very unsafe",
        "affecting_factors": ["Threats", "Domestic violence"],
        "support_needs": ["Emergency Protection", "Legal aid"],
        "private_note": "I received serious threats from the perpetrator.",
        "ai_processing_consent": True,
        "consent_version": "1.0",
        "channel": "web",
        "language": "EN"
    }

    resp = client.post(
        "/api/victim/pulse",
        json=pulse_payload,
        cookies={"mentaura_session": victim_cookie}
    )
    assert resp.status_code == 200, f"Pulse submission failed: {resp.text}"
    pulse_id = resp.json()["pulse_id"]

    # Verify database record
    db = SessionLocal()
    pulse = db.query(SupportPulse).filter(SupportPulse.id == pulse_id).first()
    assert pulse is not None
    assert pulse.risk_level == "high"
    assert pulse.risk_score >= 6
    db.close()


# --------------------------------------------------------------------------
# 3. Integration Tests: API Serialization in Triage & Command Views
# --------------------------------------------------------------------------
def test_counsellor_triage_queue_includes_risk_level():
    """Counsellor triage queue returns risk_level and risk_score for each item."""
    counsellor_cookie = get_cookie("counsellor@mentaura.example")

    resp = client.get(
        "/api/counsellor/triage-queue",
        cookies={"mentaura_session": counsellor_cookie}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "triage_queue" in data
    triage_list = data["triage_queue"]
    assert len(triage_list) > 0

    for item in triage_list:
        assert "risk_level" in item
        assert item["risk_level"] in ("low", "medium", "high")
        assert "risk_score" in item
        assert isinstance(item["risk_score"], int)


def test_command_priority_cases_includes_risk_level():
    """Command Dashboard priority cases return risk_level and risk_score."""
    admin_cookie = get_cookie("stateadmin@mentaura.example")

    resp = client.get(
        "/api/command/priority-cases",
        cookies={"mentaura_session": admin_cookie}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "priority_cases" in data
    cases = data["priority_cases"]
    assert len(cases) > 0

    for c in cases:
        assert "risk_level" in c
        assert c["risk_level"] in ("low", "medium", "high")
        assert "risk_score" in c
        assert isinstance(c["risk_score"], int)
