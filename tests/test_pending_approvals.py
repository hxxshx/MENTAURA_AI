"""
Automated Test Suite for Admin Pending Approvals UI & Endpoints (TASK 15).
Verifies role authorization, pending queue retrieval, approval and rejection actions,
audit logging, and static asset serving.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.user import User, AuditLog
from backend.app.models.review import ReviewAction
from backend.app.services.auth_service import hash_password

client = TestClient(app)


def get_cookie(email: str, password: str = "Mentaura@2026") -> str:
    """Helper to log in a user and retrieve their signed session cookie."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.cookies.get("mentaura_session")


# --------------------------------------------------------------------------
# 1. Role Guard & Access Control Tests
# --------------------------------------------------------------------------
def test_pending_approvals_unauthenticated():
    """Unauthenticated requests must be rejected with 401."""
    resp = client.get("/api/admin/pending-officials")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_pending_approvals_forbidden_for_victim():
    """Victim role must receive 403 Forbidden from admin endpoints."""
    cookie = get_cookie("victim@mentaura.example")
    resp = client.get("/api/admin/pending-officials", cookies={"mentaura_session": cookie})
    assert resp.status_code == 403
    assert "Access restricted" in resp.json()["detail"]


def test_pending_approvals_forbidden_for_counsellor():
    """Counsellor role must receive 403 Forbidden from admin endpoints."""
    cookie = get_cookie("counsellor@mentaura.example")
    resp = client.get("/api/admin/pending-officials", cookies={"mentaura_session": cookie})
    assert resp.status_code == 403
    assert "Access restricted" in resp.json()["detail"]


def test_pending_approvals_authorized_state_admin():
    """State administrator can access pending officials queue."""
    cookie = get_cookie("stateadmin@mentaura.example")
    resp = client.get("/api/admin/pending-officials", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "pending_officials" in data
    assert "admin_reviewer" in data
    assert data["admin_reviewer"]["role"] in ("state_administrator", "state_admin")


# --------------------------------------------------------------------------
# 2. Approve Official Action Test
# --------------------------------------------------------------------------
def test_approve_official_action():
    """
    Verifies that an administrator can approve a pending official,
    which activates the account, assigns the verified role, and records audit logs.
    """
    db = SessionLocal()
    unique_email = f"counsellor.test.{uuid.uuid4().hex[:6]}@mentaura.example"
    test_user = User(
        full_name="Dr. Ananya Murthy",
        email=unique_email,
        password_hash=hash_password("Mentaura@2026"),
        requested_category="counsellor",
        verified_role="pending_verification",
        account_status="pending_verification",
        preferred_language="EN",
        preferred_channel="web",
        email_verified=False
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    test_user_id = test_user.id
    db.close()

    admin_cookie = get_cookie("stateadmin@mentaura.example")

    # 1. Verify user is in pending list
    list_resp = client.get("/api/admin/pending-officials", cookies={"mentaura_session": admin_cookie})
    assert list_resp.status_code == 200
    pending_list = list_resp.json()["pending_officials"]
    assert any(u["id"] == test_user_id for u in pending_list)

    # 2. Post approve official action
    approve_resp = client.post(
        "/api/admin/approve-official",
        json={
            "user_id": test_user_id,
            "verified_role": "counsellor",
            "district": "Chennai District",
            "notes": "Verified psychological credentials via Tamil Nadu council registry."
        },
        cookies={"mentaura_session": admin_cookie}
    )
    assert approve_resp.status_code == 200
    res_data = approve_resp.json()
    assert res_data["success"] is True
    assert res_data["verified_role"] == "counsellor"
    assert res_data["account_status"] == "active"

    # 3. Verify user record in database
    db = SessionLocal()
    updated_user = db.query(User).filter(User.id == test_user_id).first()
    assert updated_user is not None
    assert updated_user.verified_role == "counsellor"
    assert updated_user.account_status == "active"
    assert updated_user.email_verified is True

    # 4. Verify Review Action Record
    action = db.query(ReviewAction).filter(
        ReviewAction.target_id == test_user_id,
        ReviewAction.action_type == "approve_official"
    ).first()
    assert action is not None
    assert action.status == "approved"

    # 5. Verify Audit Log
    audit = db.query(AuditLog).filter(
        AuditLog.action == "official_approved",
        AuditLog.details.like(f"%{unique_email}%")
    ).first()
    assert audit is not None
    db.close()


# --------------------------------------------------------------------------
# 3. Reject Official Action Test
# --------------------------------------------------------------------------
def test_reject_official_action():
    """
    Verifies that an administrator can reject a pending official registration.
    """
    db = SessionLocal()
    unique_email = f"unverified.{uuid.uuid4().hex[:6]}@mentaura.example"
    test_user = User(
        full_name="Duplicate Registration User",
        email=unique_email,
        password_hash=hash_password("Mentaura@2026"),
        requested_category="protection_officer",
        verified_role="pending_verification",
        account_status="pending_verification",
        email_verified=False
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    test_user_id = test_user.id
    db.close()

    admin_cookie = get_cookie("stateadmin@mentaura.example")

    # Post reject official action
    reject_resp = client.post(
        "/api/admin/reject-official",
        json={
            "user_id": test_user_id,
            "reason": "Duplicate registration without matching district authority credential."
        },
        cookies={"mentaura_session": admin_cookie}
    )
    assert reject_resp.status_code == 200
    res_data = reject_resp.json()
    assert res_data["success"] is True
    assert res_data["account_status"] == "rejected"

    # Verify user in database
    db = SessionLocal()
    updated_user = db.query(User).filter(User.id == test_user_id).first()
    assert updated_user.account_status == "rejected"

    action = db.query(ReviewAction).filter(
        ReviewAction.target_id == test_user_id,
        ReviewAction.action_type == "reject_official"
    ).first()
    assert action is not None
    assert action.status == "rejected"
    assert "Duplicate registration" in action.notes
    db.close()


# --------------------------------------------------------------------------
# 4. Static Asset Accessibility Test
# --------------------------------------------------------------------------
def test_static_pending_approvals_pages():
    """Verifies that pending-approvals.html and its CSS/JS are cleanly served."""
    resp_html = client.get("/pending-approvals.html")
    assert resp_html.status_code == 200
    assert "Pending Approvals" in resp_html.text
    assert "MENTAURA" in resp_html.text

    resp_css = client.get("/css/pending-approvals.css")
    assert resp_css.status_code == 200
    assert "admin-app-wrapper" in resp_css.text

    resp_js = client.get("/js/pending-approvals.js")
    assert resp_js.status_code == 200
    assert "loadPendingOfficials" in resp_js.text
