"""
Automated Test Suite for In-App Notifications & Alerts System (TASK 17).
Verifies database model, notification endpoints, automated triggers on high-risk pulses
and case escalations, unread counts, mark-as-read functionality, role security, and privacy protection.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.pulse import SupportPulse
from backend.app.models.notification import Notification

client = TestClient(app)


def get_cookie(email: str, password: str = "Mentaura@2026") -> str:
    """Helper to log in a user and retrieve their signed session cookie."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.cookies.get("mentaura_session")


# --------------------------------------------------------------------------
# 1. Access Control & Authorization Tests
# --------------------------------------------------------------------------
def test_notifications_unauthenticated():
    """Unauthenticated access must be rejected with 401."""
    resp = client.get("/api/notifications")
    assert resp.status_code == 401


def test_notifications_unread_count_unauthenticated():
    """Unauthenticated access to unread count must be rejected with 401."""
    resp = client.get("/api/notifications/unread-count")
    assert resp.status_code == 401


def test_notifications_mark_read_unauthenticated():
    """Unauthenticated access to mark-read must be rejected with 401."""
    resp = client.post("/api/notifications/mark-read", json={"mark_all": True})
    assert resp.status_code == 401


def test_notifications_forbidden_for_victim():
    """Victim role must NOT be permitted to access official notification endpoints."""
    cookie = get_cookie("victim@mentaura.example")
    resp = client.get("/api/notifications", cookies={"mentaura_session": cookie})
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower()


def test_notifications_allowed_for_officials():
    """Counsellor, District Admin, and State Admin must have access."""
    # Ensure state admin user exists
    db = SessionLocal()
    state_user = db.query(User).filter(User.email == "state_admin@mentaura.example").first()
    if not state_user:
        from backend.app.services.auth_service import hash_password
        state_user = User(
            full_name="Dr. Jayant Patil",
            email="state_admin@mentaura.example",
            password_hash=hash_password("Mentaura@2026"),
            requested_category="state_administrator",
            verified_role="state_administrator",
            account_status="active",
            email_verified=True
        )
        db.add(state_user)
        db.commit()
    db.close()

    for role_email in ["counsellor@mentaura.example", "district@mentaura.example", "state_admin@mentaura.example"]:
        cookie = get_cookie(role_email)
        resp = client.get("/api/notifications", cookies={"mentaura_session": cookie})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "notifications" in data
        assert "unread_count" in data


# --------------------------------------------------------------------------
# 2. Automated Notification on High-Risk Pulse Submission
# --------------------------------------------------------------------------
def test_high_risk_pulse_creates_notification():
    """Submitting a high-risk pulse must trigger in-app notifications for officials."""
    db = SessionLocal()
    try:
        counsellor = db.query(User).filter(User.email == "counsellor@mentaura.example").first()
        initial_count = db.query(Notification).filter(
            Notification.user_id == counsellor.id,
            Notification.type == "high_risk_pulse"
        ).count()
    finally:
        db.close()

    # Submit a high-risk pulse as victim
    victim_cookie = get_cookie("victim@mentaura.example")
    pulse_payload = {
        "case_id": "CASE-NOTIF-TEST-01",
        "wellbeing_state": "Crisis",
        "affecting_factors": ["Physical threats", "No shelter"],
        "support_needs": ["Immediate protection", "Emergency shelter"],
        "safety_status": "No, I do not feel safe.",
        "follow_up_requests": ["Urgent safety contact"],
        "private_note": "Immediate danger and fear for safety.",
        "ai_processing_consent": True,
        "processing_mode": "ai_assisted"
    }
    resp = client.post("/api/victim/pulse", json=pulse_payload, cookies={"mentaura_session": victim_cookie})
    assert resp.status_code == 200

    # Verify notification created for counsellor
    db = SessionLocal()
    try:
        new_count = db.query(Notification).filter(
            Notification.user_id == counsellor.id,
            Notification.type == "high_risk_pulse"
        ).count()
        assert new_count > initial_count

        # Fetch latest notification
        latest = db.query(Notification).filter(
            Notification.user_id == counsellor.id,
            Notification.type == "high_risk_pulse"
        ).order_by(Notification.created_at.desc()).first()

        assert latest is not None
        assert "High-risk" in latest.title
        assert latest.is_read is False
        # Privacy check: raw note must NOT be in message or title
        assert "Immediate danger and fear for safety" not in latest.message
        assert "Immediate danger and fear for safety" not in latest.title
    finally:
        db.close()


# --------------------------------------------------------------------------
# 3. Automated Notification on Case Escalation
# --------------------------------------------------------------------------
def test_case_escalation_creates_notification():
    """Escalating a case from Command Dashboard must create case_escalated notifications."""
    admin_cookie = get_cookie("district@mentaura.example")
    counsellor_cookie = get_cookie("counsellor@mentaura.example")

    # Initial counsellor unread count
    resp_init = client.get("/api/notifications/unread-count", cookies={"mentaura_session": counsellor_cookie})
    assert resp_init.status_code == 200
    initial_unread = resp_init.json()["unread_count"]

    # Escalate a case
    escalation_payload = {
        "case_id": "CASE-NOTIF-ESC-99",
        "escalation_level": "critical",
        "reason": "Rapid escalation required due to high vulnerability.",
        "assigned_officer": "Senior Officer R. Kumar",
        "notes": "Coordinating with district rapid response unit."
    }
    resp_esc = client.post("/api/command/escalate-case", json=escalation_payload, cookies={"mentaura_session": admin_cookie})
    assert resp_esc.status_code == 200
    assert resp_esc.json()["success"] is True

    # Check counsellor notifications
    resp_notifs = client.get("/api/notifications", cookies={"mentaura_session": counsellor_cookie})
    assert resp_notifs.status_code == 200
    notifs = resp_notifs.json()["notifications"]

    esc_notif = next((n for n in notifs if n["type"] == "case_escalated" and "CASE-NOTIF-ESC-99" in str(n.get("metadata", {}))), None)
    assert esc_notif is not None
    assert "Case escalated" in esc_notif["title"]
    assert esc_notif["is_read"] is False


# --------------------------------------------------------------------------
# 4. Mark Read Functionality & Unread Count Tracking
# --------------------------------------------------------------------------
def test_mark_notifications_read_individual_and_all():
    """Test marking single notification as read and marking all as read."""
    cookie = get_cookie("counsellor@mentaura.example")

    # Get notifications
    resp = client.get("/api/notifications", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    notifs = resp.json()["notifications"]
    assert len(notifs) > 0

    target_id = notifs[0]["id"]

    # Mark individual notification as read
    resp_mark_one = client.post(
        "/api/notifications/mark-read",
        json={"notification_ids": [target_id]},
        cookies={"mentaura_session": cookie}
    )
    assert resp_mark_one.status_code == 200
    assert resp_mark_one.json()["success"] is True

    # Verify that targeted notification is now read
    resp_after = client.get("/api/notifications", cookies={"mentaura_session": cookie})
    updated_notifs = resp_after.json()["notifications"]
    marked_item = next(n for n in updated_notifs if n["id"] == target_id)
    assert marked_item["is_read"] is True

    # Mark all as read
    resp_mark_all = client.post(
        "/api/notifications/mark-read",
        json={"mark_all": True},
        cookies={"mentaura_session": cookie}
    )
    assert resp_mark_all.status_code == 200
    assert resp_mark_all.json()["unread_count"] == 0

    # Verify unread-count endpoint returns 0
    resp_count = client.get("/api/notifications/unread-count", cookies={"mentaura_session": cookie})
    assert resp_count.status_code == 200
    assert resp_count.json()["unread_count"] == 0


# --------------------------------------------------------------------------
# 5. User Isolation & Privacy Protection
# --------------------------------------------------------------------------
def test_notification_user_isolation():
    """Users must only receive and manipulate their own notifications."""
    db = SessionLocal()
    try:
        user_a = db.query(User).filter(User.email == "counsellor@mentaura.example").first()
        user_b = db.query(User).filter(User.email == "state_admin@mentaura.example").first()

        # Create private notification for user_b
        notif_b = Notification(
            user_id=user_b.id,
            type="system_alert",
            title="State Administrative Digest",
            message="Private state level summary.",
            is_read=False
        )
        db.add(notif_b)
        db.commit()
        db.refresh(notif_b)
        notif_b_id = notif_b.id
    finally:
        db.close()

    # User A accesses notifications - should NOT see user B's private notification
    cookie_a = get_cookie("counsellor@mentaura.example")
    resp_a = client.get("/api/notifications", cookies={"mentaura_session": cookie_a})
    notif_ids_a = [n["id"] for n in resp_a.json()["notifications"]]
    assert notif_b_id not in notif_ids_a

    # User A attempts to mark user B's notification as read - must not modify it
    resp_mark = client.post(
        "/api/notifications/mark-read",
        json={"notification_ids": [notif_b_id]},
        cookies={"mentaura_session": cookie_a}
    )
    assert resp_mark.status_code == 200
    assert resp_mark.json()["updated_count"] == 0

    db = SessionLocal()
    try:
        check_b = db.query(Notification).filter(Notification.id == notif_b_id).first()
        assert check_b.is_read is False  # Remained unread
    finally:
        db.close()
