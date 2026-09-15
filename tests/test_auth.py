import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.user import User, UserSession, ConsentRecord, VerificationRequest, AuditLog

@pytest.fixture(autouse=True)
def cleanup_test_signups():
    db = SessionLocal()
    try:
        # Clean up any previously created test accounts
        test_emails = [
            "new_victim@mentaura.example",
            "new_witness@mentaura.example",
            "new_family@mentaura.example",
            "new_counsellor@mentaura.example",
            "new_district@mentaura.example",
            "test_victim_signup@mentaura.example"
        ]
        users = db.query(User).filter(User.email.in_(test_emails)).all()
        for u in users:
            db.query(UserSession).filter(UserSession.user_id == u.id).delete()
            db.query(ConsentRecord).filter(ConsentRecord.user_id == u.id).delete()
            db.query(VerificationRequest).filter(VerificationRequest.user_id == u.id).delete()
            db.query(AuditLog).filter(AuditLog.user_id == u.id).delete()
            db.delete(u)
        db.commit()
    finally:
        db.close()
    yield

client = TestClient(app)

# --------------------------------------------------------------------------
# 1. Signup Tests
# --------------------------------------------------------------------------
def test_valid_victim_signup():
    payload = {
        "full_name": "Test Victim User",
        "email": "new_victim@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "victim_complainant",
        "preferred_language": "EN",
        "preferred_channel": "web",
        "consent_version": "1.0",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["account_status"] == "pending_otp"
    assert data["verified_role"] == "victim"
    assert "mentaura_session" not in response.cookies


def test_valid_witness_signup():
    payload = {
        "full_name": "Test Witness User",
        "email": "new_witness@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "witness",
        "preferred_language": "HI",
        "preferred_channel": "sms",
        "consent_version": "1.0",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["account_status"] == "pending_otp"
    assert data["verified_role"] == "witness"
    assert "mentaura_session" not in response.cookies


def test_valid_affected_family_signup():
    payload = {
        "full_name": "Test Family Member",
        "email": "new_family@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "affected_family_member",
        "preferred_language": "TA",
        "preferred_channel": "web",
        "consent_version": "1.0",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["account_status"] == "pending_otp"
    assert data["verified_role"] == "affected_family_member"
    assert "mentaura_session" not in response.cookies


def test_counsellor_signup_is_pending_verification():
    payload = {
        "full_name": "Dr. New Counsellor",
        "email": "new_counsellor@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "counsellor",
        "official_id": "CNS-REG-7492",
        "preferred_language": "EN",
        "preferred_channel": "web",
        "consent_version": "1.0",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    # Must NOT be granted counsellor role immediately
    assert data["account_status"] == "pending_verification"
    assert data["verified_role"] == "pending_verification"
    assert "mentaura_session" not in response.cookies


def test_district_official_signup_is_pending_verification():
    payload = {
        "full_name": "New District Magistrate",
        "email": "new_district@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "district_authority",
        "official_id": "IAS-DM-10928",
        "preferred_language": "EN",
        "preferred_channel": "web",
        "consent_version": "1.0",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["account_status"] == "pending_verification"
    assert data["verified_role"] == "pending_verification"
    assert "mentaura_session" not in response.cookies


def test_signup_missing_fields():
    payload = {
        "full_name": "Incomplete User"
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_invalid_email():
    payload = {
        "full_name": "Invalid Email User",
        "email": "not-an-email",
        "password": "SecurePassword123!",
        "requested_category": "victim_complainant",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_weak_password():
    payload = {
        "full_name": "Short Password User",
        "email": "short_pwd@mentaura.example",
        "password": "short",
        "requested_category": "victim_complainant",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_consent_unchecked():
    payload = {
        "full_name": "No Consent User",
        "email": "no_consent@mentaura.example",
        "password": "SecurePassword123!",
        "requested_category": "victim_complainant",
        "consent_given": False
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_duplicate_email_safe_error():
    payload = {
        "full_name": "Duplicate User",
        "email": "victim@mentaura.example",  # already exists from seed
        "password": "SecurePassword123!",
        "requested_category": "victim_complainant",
        "consent_given": True
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


# --------------------------------------------------------------------------
# 2. Login Tests
# --------------------------------------------------------------------------
def test_valid_victim_login():
    payload = {
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["verified_role"] == "victim"
    assert data["redirect_url"] == "victim-home.html"
    assert "mentaura_session" in response.cookies


def test_valid_verified_counsellor_login():
    payload = {
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["verified_role"] == "counsellor"
    assert data["redirect_url"] == "counsellor-workspace.html"


def test_valid_verified_district_authority_login():
    payload = {
        "email": "district@mentaura.example",
        "password": "Mentaura@2026"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["verified_role"] == "district_authority"
    assert data["redirect_url"] == "command-dashboard.html"


def test_login_invalid_password():
    payload = {
        "email": "victim@mentaura.example",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_unknown_account():
    payload = {
        "email": "unknown_random_user@mentaura.example",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_pending_verification_user():
    payload = {
        "email": "pending@mentaura.example",
        "password": "Mentaura@2026"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["account_status"] == "pending_verification"
    assert data["redirect_url"] == "verification-pending.html"


def test_login_suspended_account():
    payload = {
        "email": "suspended@mentaura.example",
        "password": "Mentaura@2026"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 403
    assert "unavailable" in response.json()["detail"].lower()


# --------------------------------------------------------------------------
# 3. Session & Auth Guard Tests
# --------------------------------------------------------------------------
def test_get_current_user_me():
    c = TestClient(app)
    login_resp = c.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    me_resp = c.get("/api/auth/me", cookies={"mentaura_session": session_cookie})
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "victim@mentaura.example"
    assert data["verified_role"] == "victim"


def test_unauthenticated_me():
    c = TestClient(app)
    response = c.get("/api/auth/me")
    assert response.status_code == 401


def test_logout_invalidates_session():
    c = TestClient(app)
    # 1. Login
    login_resp = c.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    session_cookie = login_resp.cookies.get("mentaura_session")

    # 2. Logout
    logout_resp = c.post("/api/auth/logout", cookies={"mentaura_session": session_cookie})
    assert logout_resp.status_code == 200

    # 3. Verify session is revoked
    me_resp = c.get("/api/auth/me", cookies={"mentaura_session": session_cookie})
    assert me_resp.status_code == 401


# --------------------------------------------------------------------------
# 4. Password Recovery Placeholder Test
# --------------------------------------------------------------------------
def test_forgot_password():
    response = client.post("/api/auth/forgot-password", json={"email": "victim@mentaura.example"})
    assert response.status_code == 200
    data = response.json()
    assert "recovery will be available" in data["message"].lower()


# --------------------------------------------------------------------------
# 5. Password Hashing Security Check
# --------------------------------------------------------------------------
def test_passwords_are_argon2id():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "victim@mentaura.example").first()
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    db.close()
