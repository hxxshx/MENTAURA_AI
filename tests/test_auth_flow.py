import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db
from backend.app.models.user import User, EmailOTP
from backend.app.services.auth_service import hash_otp

client = TestClient(app)

def test_victim_signup_no_auto_login():
    """Test 1: Victim Signup (Must NOT auto-login before OTP)"""
    victim_email = f"victim_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/api/auth/signup", json={
        "full_name": "Test Victim",
        "email": victim_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "victim",
        "consent": True
    })
    assert res.status_code == 201, f"Victim signup failed: {res.text}"
    data = res.json()
    assert "mentaura_session" not in res.cookies, "Auto-login cookie was set on signup!"
    assert data.get("account_status") == "pending_otp", f"Expected pending_otp, got {data.get('account_status')}"
    assert data.get("token") is None, "JWT token returned on signup!"

def test_victim_otp_verification_auto_login():
    """Test 2: Victim OTP Verification (Logs in only after OTP)"""
    victim_email = f"victim_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/auth/signup", json={
        "full_name": "Test Victim 2",
        "email": victim_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "victim",
        "consent": True
    })
    db = next(get_db())
    u = db.query(User).filter(User.email == victim_email).first()
    otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == u.id, EmailOTP.consumed == False).first()
    assert otp_rec is not None

    # Wrong OTP
    res_wrong = client.post("/api/auth/verify-email-otp", json={"email": victim_email, "otp": "000000"})
    assert res_wrong.status_code == 400

    # Correct OTP
    known_otp = "123456"
    otp_rec.otp_hash = hash_otp(known_otp)
    db.commit()

    res_verify = client.post("/api/auth/verify-email-otp", json={"email": victim_email, "otp": known_otp})
    assert res_verify.status_code == 200, f"OTP verification failed: {res_verify.text}"
    v_data = res_verify.json()
    assert v_data.get("account_status") == "active"
    assert v_data.get("token") is not None
    assert "mentaura_session" in res_verify.cookies
    assert v_data.get("redirect_url") == "victim-home.html"

def test_official_id_mandatory_and_fraud_check():
    """Test 3: Official role without Official ID or with bogus ID (Must be rejected)"""
    official_email = f"counsellor_{uuid.uuid4().hex[:6]}@example.com"
    # Missing official ID
    res_bad = client.post("/api/auth/signup", json={
        "full_name": "Test Counsellor",
        "email": official_email,
        "password": "Password123!",
        "role": "counsellor",
        "consent": True
    })
    assert res_bad.status_code == 422

    # Bogus placeholder official ID
    res_bogus = client.post("/api/auth/signup", json={
        "full_name": "Test Counsellor",
        "email": official_email,
        "password": "Password123!",
        "role": "counsellor",
        "official_id": "test",
        "consent": True
    })
    assert res_bogus.status_code == 422

def test_official_signup_and_pending_status():
    """Test 4 & 5: Official role with valid Official ID & OTP verification remaining pending"""
    official_email = f"counsellor_{uuid.uuid4().hex[:6]}@example.com"
    res_good = client.post("/api/auth/signup", json={
        "full_name": "Dr. Test Counsellor",
        "email": official_email,
        "password": "Password123!",
        "role": "counsellor",
        "official_id": "MH-CNS-84920",
        "consent": True
    })
    assert res_good.status_code == 201
    off_data = res_good.json()
    assert off_data.get("account_status") == "pending_verification"
    assert "mentaura_session" not in res_good.cookies

    db = next(get_db())
    off_u = db.query(User).filter(User.email == official_email).first()
    assert off_u.official_id == "MH-CNS-84920"

    off_otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == off_u.id, EmailOTP.consumed == False).first()
    off_otp_rec.otp_hash = hash_otp("654321")
    db.commit()

    res_off_verify = client.post("/api/auth/verify-email-otp", json={"email": official_email, "otp": "654321"})
    assert res_off_verify.status_code == 200
    off_v_data = res_off_verify.json()
    assert off_v_data.get("account_status") == "active"
    assert off_v_data.get("redirect_url") == "counsellor-workspace.html"
    assert off_v_data.get("token") is not None
    assert "mentaura_session" in res_off_verify.cookies

def test_verify_official_id_endpoint():
    """Test verification endpoint for government official credentials"""
    # Valid government administrator ID
    res_valid_admin = client.post("/api/auth/verify-official-id", json={
        "official_id": "GOV-ADM-2026-01",
        "role": "national_admin"
    })
    assert res_valid_admin.status_code == 200
    data_admin = res_valid_admin.json()
    assert data_admin["valid"] is True
    assert "MWCD" in data_admin["data"]["department"] or "Central" in data_admin["data"]["department"]
    assert data_admin["data"]["official_id"] == "GOV-ADM-2026-01"

    # Valid state cadre counsellor ID
    res_valid_cns = client.post("/api/auth/verify-official-id", json={
        "official_id": "MH-CNS-84920",
        "role": "counsellor"
    })
    assert res_valid_cns.status_code == 200
    data_cns = res_valid_cns.json()
    assert data_cns["valid"] is True
    assert "Counsellor" in data_cns["data"]["designation"]

    # Invalid random string ID
    res_invalid = client.post("/api/auth/verify-official-id", json={
        "official_id": "random-invalid-id-123",
        "role": "national_admin"
    })
    assert res_invalid.status_code == 400

    # Bogus placeholder ID
    res_bogus = client.post("/api/auth/verify-official-id", json={
        "official_id": "12345",
        "role": "national_admin"
    })
    assert res_bogus.status_code == 400

def test_admin_signup_and_direct_dashboard_login():
    """Verify administrator account creation with official ID and direct login after OTP"""
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    res_signup = client.post("/api/auth/signup", json={
        "full_name": "District Administrative Officer",
        "email": admin_email,
        "password": "Password123!",
        "role": "national_admin",
        "official_id": "GOV-ADM-2026-01",
        "consent": True
    })
    assert res_signup.status_code == 201
    assert res_signup.json().get("account_status") == "pending_verification"

    # Fetch OTP
    db = next(get_db())
    u = db.query(User).filter(User.email == admin_email).first()
    otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == u.id, EmailOTP.consumed == False).first()
    otp_rec.otp_hash = hash_otp("889900")
    db.commit()

    # Verify OTP -> Direct active login to command dashboard
    res_verify = client.post("/api/auth/verify-email-otp", json={
        "email": admin_email,
        "otp": "889900"
    })
    assert res_verify.status_code == 200
    v_data = res_verify.json()
    assert v_data["account_status"] == "active"
    assert v_data["redirect_url"] == "command-dashboard.html"
    assert v_data["token"] is not None
    assert "mentaura_session" in res_verify.cookies


def test_affected_individual_anonymous_signup_and_masking():
    """Test 6: Affected Individual Signup with Anonymity Mode Active and Backend Masking"""
    anon_email = f"anon_victim_{uuid.uuid4().hex[:6]}@example.com"
    full_name = "Priya Sharma"
    res = client.post("/api/auth/signup", json={
        "full_name": full_name,
        "email": anon_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "victim",
        "is_anonymous": True,
        "consent": True
    })
    assert res.status_code == 201, f"Signup failed: {res.text}"
    signup_data = res.json()
    anon_id = signup_data.get("anonymous_id")
    assert anon_id is not None
    assert anon_id.startswith("ANON-V-")
    
    db = next(get_db())
    # Retrieve user by anonymous_id - real email is NOT in users table!
    u = db.query(User).filter(User.anonymous_id == anon_id).first()
    assert u is not None
    assert u.is_anonymous is True
    assert u.anonymous_id == anon_id

    # PSEUDO-ANONYMISATION VERIFICATION:
    # 1. Real name "Priya Sharma" must NOT be stored in users table!
    assert u.full_name == "Anonymous Victim"
    assert u.full_name != full_name
    # 2. Real email must NOT be stored in users table!
    assert u.email == f"{anon_id.lower()}@mentaura.anonymous"
    assert u.email != anon_email
    # 3. Phone must NOT be stored!
    assert u.phone_number is None

    # Complete OTP verification to log in using anonymous_id
    otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == u.id, EmailOTP.consumed == False).first()
    known_otp = "889900"
    otp_rec.otp_hash = hash_otp(known_otp)
    db.commit()

    res_verify = client.post("/api/auth/verify-email-otp", json={"email": anon_id, "otp": known_otp})
    assert res_verify.status_code == 200
    token = res_verify.json()["token"]

    # Direct login using Anonymous ID + password
    res_login = client.post("/api/auth/login", json={"email": anon_id, "password": "Password123!"})
    assert res_login.status_code == 200
    assert res_login.json()["user"]["anonymous_id"] == anon_id
    assert res_login.json()["user"]["full_name"] == "Anonymous Victim"

    # Query /api/auth/me using token
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["is_anonymous"] is True
    assert me_data["anonymous_id"] == anon_id
    assert "Priya" not in me_data["full_name"]
    assert me_data["full_name"] == "Anonymous Victim"
    assert "@mentaura.anonymous" in me_data["email"]

    # Submit a Support Pulse for this anonymous victim
    from backend.app.models.pulse import SupportPulse
    pulse = SupportPulse(
        authenticated_user_id=u.id,
        channel="web",
        wellbeing_state="needs_support",
        text_response="Need assistance with safe housing",
        risk_level="high",
        risk_score=7,
        priority_review=True,
        human_review_status="pending"
    )
    db.add(pulse)
    db.commit()

    # Create an authorized counsellor to inspect the triage queue
    counsellor_email = f"counsellor_view_{uuid.uuid4().hex[:6]}@example.com"
    c_res = client.post("/api/auth/signup", json={
        "full_name": "Dr. Verification Counsellor",
        "email": counsellor_email,
        "password": "Password123!",
        "role": "counsellor",
        "official_id": "MH-CNS-84920",
        "consent": True
    })
    assert c_res.status_code == 201
    c_u = db.query(User).filter(User.email == counsellor_email).first()
    c_otp = db.query(EmailOTP).filter(EmailOTP.user_id == c_u.id, EmailOTP.consumed == False).first()
    c_otp.otp_hash = hash_otp("998877")
    db.commit()

    c_verify = client.post("/api/auth/verify-email-otp", json={"email": counsellor_email, "otp": "998877"})
    assert c_verify.status_code == 200
    c_token = c_verify.json()["token"]

    # Official checks the triage queue
    res_triage = client.get("/api/counsellor/triage-queue", headers={"Authorization": f"Bearer {c_token}"})
    assert res_triage.status_code == 200
    triage_items = res_triage.json()["triage_queue"]
    pulse_item = next((item for item in triage_items if item["id"] == pulse.id), None)
    assert pulse_item is not None
    # Real name must NOT appear in counsellor triage queue!
    assert "Priya" not in pulse_item["masked_identifier"]
    assert u.anonymous_id in pulse_item["masked_identifier"]
    assert pulse_item["masked_identifier"] == f"Anonymous Victim ({u.anonymous_id})"


def test_affected_individual_non_anonymous_signup():
    """Test 7: Affected Individual Signup without Anonymity (Standard Identity)"""
    std_email = f"std_victim_{uuid.uuid4().hex[:6]}@example.com"
    full_name = "Rajesh Kumar"
    res = client.post("/api/auth/signup", json={
        "full_name": full_name,
        "email": std_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "victim",
        "is_anonymous": False,
        "consent": True
    })
    assert res.status_code == 201

    db = next(get_db())
    u = db.query(User).filter(User.email == std_email).first()
    assert u is not None
    assert u.is_anonymous is False
    assert u.anonymous_id is None

    # Complete OTP verification
    otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == u.id, EmailOTP.consumed == False).first()
    known_otp = "112233"
    otp_rec.otp_hash = hash_otp(known_otp)
    db.commit()

    res_verify = client.post("/api/auth/verify-email-otp", json={"email": std_email, "otp": known_otp})
    assert res_verify.status_code == 200
    token = res_verify.json()["token"]

    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["is_anonymous"] is False
    assert me_data["anonymous_id"] is None
    assert me_data["full_name"] == full_name


def test_official_role_cannot_be_anonymous():
    """Test 8: Official roles cannot activate anonymous mode"""
    admin_email = f"admin_anon_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/api/auth/signup", json={
        "full_name": "Official Officer",
        "email": admin_email,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "case_officer",
        "official_id": "MH-ADM-84920",
        "is_anonymous": True,  # Attempting anonymity
        "consent": True
    })
    assert res.status_code == 201
    db = next(get_db())
    u = db.query(User).filter(User.email == admin_email).first()
    assert u is not None
    # Official must not be anonymous
    assert u.is_anonymous is False
    assert u.anonymous_id is None


def test_pure_pseudoanonymous_signup_zero_name_zero_email():
    """Test 10: Affected Individual Pure Pseudo-Anonymisation with Zero Name and Zero Email"""
    res = client.post("/api/auth/signup", json={
        "role": "witness",
        "is_anonymous": True,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "consent": True
    })
    assert res.status_code == 201, f"Signup failed: {res.text}"
    signup_data = res.json()
    anon_id = signup_data.get("anonymous_id")
    assert anon_id is not None
    assert anon_id.startswith("ANON-W-")
    assert signup_data["account_status"] == "active"
    assert signup_data["token"] is not None
    assert signup_data["redirect_url"] == "victim-home.html"

    db = next(get_db())
    # Retrieve user from database strictly by anonymous_id
    u = db.query(User).filter(User.anonymous_id == anon_id).first()
    assert u is not None
    assert u.is_anonymous is True
    assert u.anonymous_id == anon_id

    # ZERO PII STORAGE:
    # 1. full_name is system pseudonymous label
    assert u.full_name == "Anonymous Witness"
    # 2. email is synthetic pseudonymous URI
    assert u.email == f"{anon_id.lower()}@mentaura.anonymous"
    # 3. phone_number is completely None
    assert u.phone_number is None

    # All platform access happens using anonymous_id + password
    res_login = client.post("/api/auth/login", json={"email": anon_id, "password": "Password123!"})
    assert res_login.status_code == 200
    login_user = res_login.json()["user"]
    assert login_user["anonymous_id"] == anon_id
    assert login_user["full_name"] == "Anonymous Witness"
    assert login_user["is_anonymous"] is True

    # Validate /api/auth/me output
    token = res_login.json().get("token") or signup_data["token"]
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["is_anonymous"] is True
    assert me_data["anonymous_id"] == anon_id
    assert me_data["full_name"] == "Anonymous Witness"
    assert "@mentaura.anonymous" in me_data["email"]

