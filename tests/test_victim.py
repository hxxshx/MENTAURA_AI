"""
Automated Test Suite for Victim Home, Access Control, and Support Pulse Submissions.
"""
import json
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.pulse import SupportPulse, VoiceProcessingJob

client = TestClient(app)

def test_victim_overview_authorized_victim():
    # 1. Login as victim
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # 2. Access /api/victim/overview
    overview_resp = client.get("/api/victim/overview", cookies={"mentaura_session": session_cookie})
    assert overview_resp.status_code == 200
    data = overview_resp.json()
    assert data["verified_role"] == "victim"
    assert "support_pulse" in data
    assert "case_overview" in data
    assert "support_requests" in data
    assert data["case_overview"]["stage_display"] == "Support monitoring"


def test_victim_overview_authorized_witness():
    login_resp = client.post("/api/auth/login", json={
        "email": "witness@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    overview_resp = client.get("/api/victim/overview", cookies={"mentaura_session": session_cookie})
    assert overview_resp.status_code == 200
    data = overview_resp.json()
    assert data["verified_role"] == "witness"


def test_victim_overview_forbidden_for_counsellor():
    # Login as counsellor
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # Counsellor should be forbidden from /api/victim/overview
    overview_resp = client.get("/api/victim/overview", cookies={"mentaura_session": session_cookie})
    assert overview_resp.status_code == 403


def test_victim_overview_unauthenticated():
    c = TestClient(app)
    response = c.get("/api/victim/overview")
    assert response.status_code == 401


def test_victim_pulse_submission_authorized():
    # Login as victim
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    pulse_data = {
        "channel": "web",
        "language": "EN",
        "ai_processing_consent": True,
        "processing_mode": "ai_assisted",
        "wellbeing_state": "Managing",
        "private_note": "Feeling a bit stressed about the upcoming hearing.",
        "voice_response_status": "not_added",
        "affecting_factors": ["Court or investigation", "Sleep or daily life"],
        "safety_status": "Yes, I feel safe.",
        "follow_up_requests": [],
        "support_needs": ["Counselling", "Legal or case-status support"]
    }

    pulse_resp = client.post("/api/victim/pulse", json=pulse_data, cookies={"mentaura_session": session_cookie})
    assert pulse_resp.status_code == 200
    res = pulse_resp.json()
    assert res["status"] == "submitted"
    assert "pulse_id" in res
    assert res["processing_mode"] == "ai_assisted"
    assert res["ai_processing_consent"] is True
    assert res["analysis_status"] == "queued"
    assert res["human_review_status"] == "pending"


def test_victim_pulse_submission_human_only():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    pulse_data = {
        "channel": "web",
        "language": "EN",
        "ai_processing_consent": False,
        "processing_mode": "human_review_only",
        "wellbeing_state": "Steady",
        "private_note": "Taking it one day at a time.",
        "voice_response_status": "not_added",
        "affecting_factors": ["Prefer not to say"],
        "safety_status": None,
        "follow_up_requests": [],
        "support_needs": ["I am okay for now"]
    }

    pulse_resp = client.post("/api/victim/pulse", json=pulse_data, cookies={"mentaura_session": session_cookie})
    assert pulse_resp.status_code == 200
    res = pulse_resp.json()
    assert res["status"] == "submitted"
    assert res["processing_mode"] == "human_review_only"
    assert res["ai_processing_consent"] is False
    assert res["transcription_status"] == "not_requested"
    assert res["analysis_status"] == "not_requested"

    # Verify no AI job was created in DB
    db = SessionLocal()
    try:
        pulse_id = res["pulse_id"]
        job = db.query(VoiceProcessingJob).filter(VoiceProcessingJob.support_pulse_id == pulse_id).first()
        assert job is None
    finally:
        db.close()


def test_victim_pulse_multipart_with_audio():
    # Login as victim
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    metadata = {
        "channel": "web",
        "language": "EN",
        "ai_processing_consent": True,
        "processing_mode": "ai_assisted",
        "wellbeing_state": "Heavy",
        "private_note": "Voice note attached with updates.",
        "voice_response_status": "recorded",
        "audio_duration_seconds": 18.5,
        "affecting_factors": ["Safety or threats"],
        "safety_status": "I do not feel completely safe.",
        "follow_up_requests": ["Request a support call."],
        "support_needs": ["Safety or protection support"]
    }

    fake_audio_content = b"RIFF....WAVEfmt ....data...."
    files = {
        "audio_file": ("test_recording.webm", io.BytesIO(fake_audio_content), "audio/webm")
    }
    data = {
        "metadata": json.dumps(metadata)
    }

    pulse_resp = client.post(
        "/api/support-pulses",
        data=data,
        files=files,
        cookies={"mentaura_session": session_cookie}
    )
    assert pulse_resp.status_code == 200
    res = pulse_resp.json()
    assert res["status"] == "submitted"
    assert res["audio_received"] is True
    assert res["processing_mode"] == "ai_assisted"
    assert res["transcription_status"] == "queued"
    assert res["analysis_status"] == "queued"
    assert res["priority_review"] is True


def test_victim_pulse_submission_forbidden_for_counsellor():
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    pulse_resp = client.post("/api/victim/pulse", json={"channel": "web"}, cookies={"mentaura_session": session_cookie})
    assert pulse_resp.status_code == 403


def test_victim_pulse_submission_unauthenticated():
    c = TestClient(app)
    pulse_resp = c.post("/api/victim/pulse", json={"channel": "web"})
    assert pulse_resp.status_code == 401


def test_victim_pulse_submission_with_adaptive_factors_and_followups():
    # Login as victim
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    pulse_data = {
        "channel": "web",
        "language": "EN",
        "ai_processing_consent": True,
        "processing_mode": "ai_assisted",
        "wellbeing_state": "Overwhelming",
        "private_note": "Need assistance with compensation forms.",
        "voice_response_status": "written_note",
        "affecting_factors": [
            "Money or compensation",
            "Sleep or daily life",
            "Feeling unsupported"
        ],
        "safety_status": "I do not feel completely safe.",
        "follow_up_requests": [
            "Compensation: Yes, request follow-up.",
            "Request Support Team Call"
        ],
        "support_needs": [
            "Financial or compensation support",
            "A call from my support team"
        ]
    }

    pulse_resp = client.post("/api/victim/pulse", json=pulse_data, cookies={"mentaura_session": session_cookie})
    assert pulse_resp.status_code == 200
    res = pulse_resp.json()
    assert res["status"] == "submitted"
    assert res["priority_review"] is True
    assert res["processing_mode"] == "ai_assisted"


def test_victim_pulse_sanitization():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    pulse_data = {
        "channel": "web",
        "language": "EN",
        "ai_processing_consent": False,
        "processing_mode": "human_review_only",
        "wellbeing_state": "Steady",
        "private_note": "<script>alert('xss')</script> Safe text note.",
        "voice_response_status": "written_note",
        "affecting_factors": ["Something else"],
        "support_needs": ["I am okay for now"]
    }

    pulse_resp = client.post("/api/victim/pulse", json=pulse_data, cookies={"mentaura_session": session_cookie})
    assert pulse_resp.status_code == 200
    res = pulse_resp.json()
    assert res["status"] == "submitted"

    # Check DB stored sanitized version
    db = SessionLocal()
    try:
        pulse_id = res["pulse_id"]
        pulse_record = db.query(SupportPulse).filter(SupportPulse.id == pulse_id).first()
        assert pulse_record is not None
        assert "<script>" not in pulse_record.text_response
        assert "&lt;script&gt;" in pulse_record.text_response
    finally:
        db.close()


def test_victim_chatbot_threat_and_hindi():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # 1. Threat query
    resp = client.post("/api/victim/chatbot/message", json={
        "message": "Someone came to my house and threatened me about the court date.",
        "language": "EN"
    }, cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert "bot_reply" in data
    assert "Section 15A" in data["bot_reply"]
    assert "suggested_chips" in data
    assert any("SOS" in c or "Protection" in c for c in data["suggested_chips"])

    # 2. Hindi query
    resp_hi = client.post("/api/victim/chatbot/message", json={
        "message": "मुझे डर लग रहा है और घबराहट हो रही है",
        "language": "HI"
    }, cookies={"mentaura_session": session_cookie})
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert "bot_reply" in data_hi
    assert len(data_hi["bot_reply"]) > 10


def test_victim_simulate_ivrs():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # Step 1
    s1_resp = client.post("/api/victim/simulate-ivrs", json={"step": 1}, cookies={"mentaura_session": session_cookie})
    assert s1_resp.status_code == 200
    s1 = s1_resp.json()
    assert s1["step"] == 1
    assert "14566" in s1["prompt_text"]

    # Step 2
    s2_resp = client.post("/api/victim/simulate-ivrs", json={"step": 2, "key_pressed": "2"}, cookies={"mentaura_session": session_cookie})
    assert s2_resp.status_code == 200
    s2 = s2_resp.json()
    assert s2["recorded_state"] == "Managing"

    # Step 4 (Concluded)
    s4_resp = client.post("/api/victim/simulate-ivrs", json={"step": 4, "key_pressed": "1"}, cookies={"mentaura_session": session_cookie})
    assert s4_resp.status_code == 200
    s4 = s4_resp.json()
    assert s4["is_call_ended"] is True
    assert s4["summary"]["callback_requested"] is True


def test_victim_sos_alert():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.post("/api/victim/sos-alert", json={"latitude": 28.6139, "longitude": 77.2090}, cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sos_dispatched"
    assert "alert_id" in data
    assert any(h["number"] == "14566" for h in data["emergency_helplines"])


def test_victim_report_and_get_intimidation():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # Create threat report
    post_resp = client.post("/api/victim/report-intimidation", json={
        "incident_type": "direct_threat",
        "threat_source": "Associates of accused party",
        "incident_location": "Outside district court complex",
        "narrative": "Approached and warned not to give testimony at next hearing.",
        "urgency_level": "high"
    }, cookies={"mentaura_session": session_cookie})
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["status"] == "submitted"

    # Fetch threat reports
    get_resp = client.get("/api/victim/intimidation-reports", cookies={"mentaura_session": session_cookie})
    assert get_resp.status_code == 200
    reports = get_resp.json()
    assert len(reports) >= 1
    assert any(r["incident_type"] == "direct_threat" for r in reports)


def test_victim_distress_trends_and_statutory_relief():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # 1. Distress trends
    trends_resp = client.get("/api/victim/distress-trends", cookies={"mentaura_session": session_cookie})
    assert trends_resp.status_code == 200
    trends_data = trends_resp.json()
    assert "current_dds" in trends_data
    assert "trajectory" in trends_data
    assert "milestones" in trends_data
    assert "xai_factors" in trends_data

    # 2. Statutory relief
    relief_resp = client.get("/api/victim/statutory-relief", cookies={"mentaura_session": session_cookie})
    assert relief_resp.status_code == 200
    relief_data = relief_resp.json()
    assert "stages" in relief_data
    assert len(relief_data["stages"]) == 3
    assert relief_data["stages"][0]["percentage"] == "25%"
    assert relief_data["stages"][1]["percentage"] == "50%"
    assert relief_data["stages"][2]["percentage"] == "25%"
    assert "dsp_investigation_tracker" in relief_data
    assert relief_data["dsp_investigation_tracker"]["statutory_limit_days"] == 60


def test_victim_chatbot_message():
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    # English message
    resp_en = client.post("/api/victim/chatbot/message", json={
        "message": "I am feeling anxious and dreading the next court hearing",
        "language": "EN"
    }, cookies={"mentaura_session": session_cookie})
    assert resp_en.status_code == 200
    data_en = resp_en.json()
    assert "bot_response" in data_en
    assert "sentiment_distress_score" in data_en
    assert data_en["sentiment_distress_score"] > 20

    # Hindi message
    resp_hi = client.post("/api/victim/chatbot/message", json={
        "message": "मुझे बहुत डर और चिंता लग रही है कोर्ट की तारीख को लेकर",
        "language": "HI"
    }, cookies={"mentaura_session": session_cookie})
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert "bot_response" in data_hi
    assert "sentiment_distress_score" in data_hi



