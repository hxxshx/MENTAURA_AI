"""
Comprehensive End-to-End Integration Tests for all 4 Psychological Counselling Session Interaction Modes:
1. Secure Telephonic Callback (telephonic)
2. Encrypted Video Consultation (video)
3. One-Stop Centre In-Person Visit (in_person)
4. Emergency Crisis Stabilization (emergency_crisis)
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.support_request import SupportRequest
from backend.app.models.user import User

client = TestClient(app)


def get_auth_cookies_and_victim():
    db = SessionLocal()
    try:
        victim = db.query(User).filter(User.email == "victim@mentaura.example").first()
        assert victim is not None, "victim@mentaura.example not found in DB"
        victim_id = victim.id

        # Ensure victim has a clinical counselling support request
        req = db.query(SupportRequest).filter(
            SupportRequest.user_id == victim_id,
            SupportRequest.support_type.in_(["counselling", "psychological", "clinical"])
        ).first()

        if not req:
            req = SupportRequest(
                user_id=victim_id,
                case_id="MUM-2026-9041",
                support_type="counselling",
                status="requested",
                submitted_at=datetime.now(timezone.utc)
            )
            db.add(req)
            db.commit()
            db.refresh(req)
        req_id = req.id
    finally:
        db.close()

    # Counsellor login
    c_login = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert c_login.status_code == 200, f"Counsellor login failed: {c_login.text}"
    c_cookie = c_login.cookies.get("mentaura_session")

    # Victim login
    v_login = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert v_login.status_code == 200, f"Victim login failed: {v_login.text}"
    v_cookie = v_login.cookies.get("mentaura_session")

    return c_cookie, v_cookie, req_id


def test_telephonic_callback_full_interaction():
    """Mode 1: Telephonic Callback scheduling, incoming ringing, answer, and completion."""
    c_cookie, v_cookie, req_id = get_auth_cookies_and_victim()

    # 1. Counsellor schedules Telephonic Callback
    sched_resp = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req_id,
        "action_type": "schedule_session",
        "session_format": "telephonic",
        "status": "scheduled",
        "appointment_date": "2026-09-18T10:00:00Z",
        "notes": "Telephonic triage callback on secure IVRS bridge."
    }, cookies={"mentaura_session": c_cookie})
    assert sched_resp.status_code == 200

    # 2. Victim fetches active counsellor session
    v_sess_resp = client.get("/api/victim/counsellor-session", cookies={"mentaura_session": v_cookie})
    assert v_sess_resp.status_code == 200
    v_data = v_sess_resp.json()
    assert v_data["has_session"] is True
    assert v_data["session"]["session_format"] == "telephonic"
    assert "pass_code" in v_data["session"]["metadata"]

    # 3. Counsellor initiates call
    c_act1 = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "start_call",
        "notes": "Dialing victim via encrypted IVRS gateway..."
    }, cookies={"mentaura_session": c_cookie})
    assert c_act1.status_code == 200
    assert c_act1.json()["metadata"]["call_status"] == "in_progress"

    # 4. Victim answers call
    v_act = client.post("/api/victim/counsellor-session/action", json={
        "session_id": req_id,
        "action": "answer_call"
    }, cookies={"mentaura_session": v_cookie})
    assert v_act.status_code == 200
    assert v_act.json()["metadata"]["victim_call_status"] == "connected"

    # 5. Counsellor completes call with clinical notes
    c_act2 = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "end_call",
        "notes": "Call completed successfully. Patient reported reduced anxiety."
    }, cookies={"mentaura_session": c_cookie})
    assert c_act2.status_code == 200
    assert c_act2.json()["status"] == "completed"
    assert c_act2.json()["metadata"]["call_status"] == "completed"


def test_video_consultation_full_interaction():
    """Mode 2: Encrypted Video Consultation room creation, joining, and concluding."""
    c_cookie, v_cookie, req_id = get_auth_cookies_and_victim()

    # 1. Counsellor schedules Video Consultation
    sched_resp = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req_id,
        "action_type": "schedule_session",
        "session_format": "video",
        "status": "scheduled",
        "appointment_date": "2026-09-18T11:00:00Z",
        "notes": "High security trauma video consultation."
    }, cookies={"mentaura_session": c_cookie})
    assert sched_resp.status_code == 200

    # 2. Victim queries session and retrieves room_id & encryption metadata
    v_sess_resp = client.get("/api/victim/counsellor-session", cookies={"mentaura_session": v_cookie})
    assert v_sess_resp.status_code == 200
    v_data = v_sess_resp.json()
    assert v_data["session"]["session_format"] == "video"
    room_id = v_data["session"]["metadata"].get("room_id")
    assert room_id is not None
    assert "mentaura-room-" in room_id

    # 3. Victim joins video room
    v_act = client.post("/api/victim/counsellor-session/action", json={
        "session_id": req_id,
        "action": "join_video"
    }, cookies={"mentaura_session": v_cookie})
    assert v_act.status_code == 200
    assert v_act.json()["metadata"]["victim_video_status"] == "joined"

    # 4. Counsellor starts & completes video session
    c_start = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "start_video",
        "notes": "Doctor joined consultation room."
    }, cookies={"mentaura_session": c_cookie})
    assert c_start.status_code == 200

    c_end = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "end_video",
        "notes": "Comprehensive psychiatric trauma assessment conducted. Victim calm."
    }, cookies={"mentaura_session": c_cookie})
    assert c_end.status_code == 200
    assert c_end.json()["status"] == "completed"


def test_in_person_osc_visit_full_interaction():
    """Mode 3: One-Stop Centre (OSC) In-Person Visit with Digital Pass, Security Checkin, and Clinical Vitals."""
    c_cookie, v_cookie, req_id = get_auth_cookies_and_victim()

    # 1. Counsellor schedules In-Person Visit at One-Stop Centre
    sched_resp = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req_id,
        "action_type": "schedule_session",
        "session_format": "in_person",
        "status": "scheduled",
        "appointment_date": "2026-09-19T09:30:00Z",
        "notes": "Face-to-face consultation at One-Stop Crisis Centre (OSC) District Hospital."
    }, cookies={"mentaura_session": c_cookie})
    assert sched_resp.status_code == 200

    # 2. Victim views Digital Pass details
    v_sess_resp = client.get("/api/victim/counsellor-session", cookies={"mentaura_session": v_cookie})
    assert v_sess_resp.status_code == 200
    v_data = v_sess_resp.json()
    assert v_data["session"]["session_format"] == "in_person"
    pass_num = v_data["session"]["metadata"].get("pass_number")
    assert pass_num is not None
    assert pass_num.startswith("OSC-TN-2026-")

    # 3. Victim requests escort & checks in at security gate
    v_escort = client.post("/api/victim/counsellor-session/action", json={
        "session_id": req_id,
        "action": "request_escort"
    }, cookies={"mentaura_session": v_cookie})
    assert v_escort.status_code == 200
    assert v_escort.json()["metadata"]["escort_requested"] is True

    v_gate = client.post("/api/victim/counsellor-session/action", json={
        "session_id": req_id,
        "action": "gate_checkin"
    }, cookies={"mentaura_session": v_cookie})
    assert v_gate.status_code == 200
    assert v_gate.json()["metadata"]["gate_checked_in"] is True

    # 4. Counsellor admits visitor and records vitals
    c_admit = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "admit_visitor"
    }, cookies={"mentaura_session": c_cookie})
    assert c_admit.status_code == 200
    assert c_admit.json()["metadata"]["visitor_arrived"] is True

    c_complete = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "complete_visit",
        "vitals": {
            "heart_rate_bpm": 76,
            "blood_pressure": "118/78",
            "clinical_state": "Stabilized",
            "mental_status_exam": "Oriented to time, place, and person."
        },
        "notes": "Beneficiary attended OSC consultation in person. Safe transit ensured."
    }, cookies={"mentaura_session": c_cookie})
    assert c_complete.status_code == 200
    assert c_complete.json()["status"] == "completed"
    assert "vitals" in c_complete.json()["metadata"]


def test_emergency_crisis_stabilization_full_interaction():
    """Mode 4: Emergency Crisis Stabilization protocol with SOS dispatch and clinical stabilization."""
    c_cookie, v_cookie, req_id = get_auth_cookies_and_victim()

    # 1. Counsellor schedules Emergency Crisis Stabilization
    sched_resp = client.post("/api/counsellor/review-action", json={
        "target_type": "support_request",
        "target_id": req_id,
        "action_type": "schedule_session",
        "session_format": "emergency_crisis",
        "status": "scheduled",
        "appointment_date": "2026-09-17T08:00:00Z",
        "notes": "Emergency 24/7 crisis stabilization protocol activated."
    }, cookies={"mentaura_session": c_cookie})
    assert sched_resp.status_code == 200

    # 2. Victim retrieves emergency crisis suite
    v_sess_resp = client.get("/api/victim/counsellor-session", cookies={"mentaura_session": v_cookie})
    assert v_sess_resp.status_code == 200
    v_data = v_sess_resp.json()
    assert v_data["session"]["session_format"] == "emergency_crisis"
    assert v_data["session"]["metadata"].get("priority") == "CRITICAL"

    # 3. Victim triggers SOS Beacon
    v_sos = client.post("/api/victim/counsellor-session/action", json={
        "session_id": req_id,
        "action": "crisis_sos",
        "notes": "Acute distress panic attack experienced."
    }, cookies={"mentaura_session": v_cookie})
    assert v_sos.status_code == 200
    assert v_sos.json()["metadata"]["sos_beacon_dispatched"] is True

    # 4. Counsellor stabilizes crisis
    c_stab = client.post(f"/api/counsellor/sessions/{req_id}/action", json={
        "action": "stabilize_crisis",
        "notes": "Crisis stabilization breathing protocols deployed. Grounding exercises completed with victim."
    }, cookies={"mentaura_session": c_cookie})
    assert c_stab.status_code == 200
    assert c_stab.json()["status"] == "completed"
    assert c_stab.json()["metadata"]["crisis_status"] == "stabilized"
