"""
Automated Test Suite for Counsellor & Official Review Workspace (TASK 12).
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.pulse import SupportPulse
from backend.app.models.support_request import SupportRequest
from backend.app.models.review import ReviewAction

client = TestClient(app)

def test_counsellor_overview_unauthenticated():
    """Unauthenticated requests must be rejected with 401."""
    resp = client.get("/api/counsellor/overview")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_counsellor_overview_forbidden_for_victim():
    """Victim role must be rejected with 403 from official review workspace."""
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/counsellor/overview", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 403
    assert "Access restricted" in resp.json()["detail"]


def test_counsellor_overview_authorized_counsellor():
    """Authorized counsellor receives overview summary counts and reviewer info."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/counsellor/overview", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "summary" in data
    assert "reviewer" in data
    assert "new_pulses_count" in data["summary"]
    assert "pending_requests_count" in data["summary"]
    assert data["reviewer"]["role"] == "counsellor"
    assert data["reviewer"]["full_name"] == "Dr. Priya Nair"


def test_triage_queue_authorized():
    """Triage queue returns pulses with masked identifiers and processing choices."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/counsellor/triage-queue", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "triage_queue" in data
    assert isinstance(data["triage_queue"], list)
    if len(data["triage_queue"]) > 0:
        first = data["triage_queue"][0]
        assert "masked_identifier" in first
        assert "processing_mode" in first
        assert first["processing_mode"] in ("ai_assisted", "human_review_only")
        assert "wellbeing_state" in first


def test_support_requests_authorized():
    """Support requests queue returns structured requests."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/counsellor/support-requests", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "support_requests" in data
    assert isinstance(data["support_requests"], list)


def test_case_milestones_and_interventions_authorized():
    """Case milestones and interventions endpoints return structured items."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp_m = client.get("/api/counsellor/case-milestones", cookies={"mentaura_session": session_cookie})
    assert resp_m.status_code == 200
    data_m = resp_m.json()
    assert "case_milestones" in data_m
    assert len(data_m["case_milestones"]) >= 1

    resp_i = client.get("/api/counsellor/interventions", cookies={"mentaura_session": session_cookie})
    assert resp_i.status_code == 200
    data_i = resp_i.json()
    assert "interventions" in data_i
    assert len(data_i["interventions"]) >= 1


def test_review_action_recording():
    """Posting a review action updates target status and persists ReviewAction."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    # Get a real pulse to review
    queue_resp = client.get("/api/counsellor/triage-queue", cookies={"mentaura_session": session_cookie})
    pulses = queue_resp.json()["triage_queue"]
    assert len(pulses) > 0
    target_pulse_id = pulses[0]["id"]

    # Post review action
    action_resp = client.post(
        "/api/counsellor/review-action",
        json={
            "target_type": "support_pulse",
            "target_id": target_pulse_id,
            "action_type": "mark_reviewed",
            "status": "reviewed",
            "notes": "Verified initial emotional stabilization check-in."
        },
        cookies={"mentaura_session": session_cookie}
    )
    assert action_resp.status_code == 200
    res_data = action_resp.json()
    assert res_data["success"] is True
    assert res_data["new_status"] == "reviewed"

    # Verify DB update
    db = SessionLocal()
    pulse = db.query(SupportPulse).filter(SupportPulse.id == target_pulse_id).first()
    assert pulse.human_review_status == "reviewed"

    action_record = db.query(ReviewAction).filter(ReviewAction.id == res_data["action_id"]).first()
    assert action_record is not None
    assert action_record.action_type == "mark_reviewed"
    assert action_record.notes == "Verified initial emotional stabilization check-in."
    db.close()


def test_static_counsellor_pages_accessible():
    """Verify that counsellor workspace static HTML, CSS, and JS are served properly."""
    resp_html = client.get("/counsellor-workspace.html")
    assert resp_html.status_code == 200
    assert "Review Workspace" in resp_html.text

    resp_css = client.get("/css/counsellor.css")
    assert resp_css.status_code == 200
    assert "counsellor-app-wrapper" in resp_css.text

    resp_js = client.get("/js/counsellor.js")
    assert resp_js.status_code == 200
    assert "loadTriageQueue" in resp_js.text


def test_new_pulse_appears_in_counsellor_triage_queue():
    """
    PART C Verification:
    1. Create/login victim account.
    2. Submit a brand new Support Pulse.
    3. Login as counsellor and call triage-queue endpoint.
    4. Verify the newly submitted pulse appears immediately with masked identifier and correct fields.
    """
    # 1. Login as victim
    victim_login = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert victim_login.status_code == 200
    victim_cookie = victim_login.cookies.get("mentaura_session")

    # 2. Submit Support Pulse
    pulse_payload = {
        "case_id": "CASE-2026-DL-08942",
        "wellbeing_state": "Steady",
        "private_note": "Self-test verifying triage queue sync.",
        "processing_mode": "human_review_only",
        "affecting_factors": ["Legal proceedings", "Housing"],
        "safety_status": "Yes, I feel safe right now.",
        "support_needs": ["Legal advice support"]
    }
    submit_resp = client.post("/api/victim/pulse", json=pulse_payload, cookies={"mentaura_session": victim_cookie})
    assert submit_resp.status_code == 200
    pulse_data = submit_resp.json()
    new_pulse_id = pulse_data["pulse_id"]
    assert new_pulse_id is not None

    # 3. Login as Counsellor
    counsellor_login = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert counsellor_login.status_code == 200
    counsellor_cookie = counsellor_login.cookies.get("mentaura_session")

    # 4. Call triage-queue endpoint as Counsellor
    triage_resp = client.get("/api/counsellor/triage-queue", cookies={"mentaura_session": counsellor_cookie})
    assert triage_resp.status_code == 200
    triage_json = triage_resp.json()
    queue = triage_json.get("triage_queue", [])

    # 5. Assert newly created pulse is present in triage queue
    matched_pulse = next((item for item in queue if item["id"] == new_pulse_id), None)
    assert matched_pulse is not None, f"Pulse {new_pulse_id} should appear in counsellor triage queue"
    assert "Victim" in matched_pulse["masked_identifier"] or "Aanya" in matched_pulse["masked_identifier"]
    assert matched_pulse["wellbeing_state"] == "Steady"
    assert matched_pulse["processing_mode"] == "human_review_only"
    assert matched_pulse["human_review_status"] in ("pending", "new")
    assert matched_pulse["submission_date"] is not None

    # 6. Teardown: Clean up test pulse immediately so it never clutters the UI
    db = SessionLocal()
    try:
        db.query(SupportPulse).filter(SupportPulse.id == new_pulse_id).delete()
        db.commit()
    finally:
        db.close()

