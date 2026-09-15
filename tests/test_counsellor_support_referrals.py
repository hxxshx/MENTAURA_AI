"""
Unit & Integration tests for Counsellor Support & Referrals Restructuring.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.support_request import SupportRequest

client = TestClient(app)

def test_counsellor_support_requests_categorized():
    """Verify counsellor receives domain breakdown and categorized requests."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/counsellor/support-requests", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "total_count" in data
    assert "clinical_count" in data
    assert "statutory_count" in data
    assert data["clinical_count"] > 0
    assert data["statutory_count"] > 0
    assert data["total_count"] == data["clinical_count"] + data["statutory_count"]


def test_counsellor_support_requests_filtering():
    """Verify filtering by clinical and statutory domains."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    cookie = login_resp.cookies.get("mentaura_session")

    # Clinical
    res_clin = client.get("/api/counsellor/support-requests?domain=clinical", cookies={"mentaura_session": cookie})
    assert res_clin.status_code == 200
    data_clin = res_clin.json()
    assert data_clin["filtered_count"] == data_clin["clinical_count"]
    for r in data_clin["support_requests"]:
        assert r["domain"] == "clinical"
        assert r["action_mode"] == "clinical_care"

    # Statutory
    res_stat = client.get("/api/counsellor/support-requests?domain=statutory", cookies={"mentaura_session": cookie})
    assert res_stat.status_code == 200
    data_stat = res_stat.json()
    assert data_stat["filtered_count"] == data_stat["statutory_count"]
    for r in data_stat["support_requests"]:
        assert r["domain"] == "statutory"
        assert r["action_mode"] == "statutory_referral"
        assert r["target_agency"] is not None


def test_counsellor_schedule_and_refer_actions():
    """Verify session scheduling and cross-agency statutory referral review actions."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    cookie = login_resp.cookies.get("mentaura_session")

    # Fetch one clinical and one statutory
    clin_items = client.get("/api/counsellor/support-requests?domain=clinical&limit=1", cookies={"mentaura_session": cookie}).json()["support_requests"]
    stat_items = client.get("/api/counsellor/support-requests?domain=statutory&limit=1", cookies={"mentaura_session": cookie}).json()["support_requests"]

    # 1. Schedule Clinical Care
    req1_id = clin_items[0]["id"]
    act1 = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req1_id,
        "action_type": "schedule_session",
        "status": "scheduled",
        "appointment_date": "2026-09-17T14:00:00Z",
        "notes": "Format: VIDEO | Clinical Assessment: Trauma debriefing and stabilization."
    }, cookies={"mentaura_session": cookie})
    assert act1.status_code == 200

    # 2. Statutory Referral
    req2_id = stat_items[0]["id"]
    act2 = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req2_id,
        "action_type": "refer_to_agency",
        "status": "referred",
        "target_agency": "SP Witness Protection Cell",
        "urgency": "critical_threat",
        "notes": "Urgency: CRITICAL THREAT | Clinical Reason: Severe distress induced by accused intimidations."
    }, cookies={"mentaura_session": cookie})
    assert act2.status_code == 200

    # Verify DB updates
    db = SessionLocal()
    try:
        r1 = db.query(SupportRequest).filter(SupportRequest.id == req1_id).first()
        assert r1.status == "scheduled"
        assert "scheduled with" in r1.next_step

        r2 = db.query(SupportRequest).filter(SupportRequest.id == req2_id).first()
        assert r2.status == "referred"
        assert r2.assigned_role == "SP Witness Protection Cell"
    finally:
        db.close()
