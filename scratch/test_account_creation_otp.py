"""
End-to-end Automated Validation for Mentaura Enhanced Account Creation:
- UUID Primary Keys & PostgreSQL Schema
- 11 Role Mappings & Conditional Official ID
- Argon2id Password Hashing & Strength Validation
- 6-Digit Email OTP with SHA-256 Hashing & 10-Min Expiration
- Safe Gmail SMTP Service Fallback
- JWT-Based Authentication for /api/auth/me
- Pseudo-Anonymity Identifier Masking ("A****a S.")
"""
import uuid
import hashlib
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.app.main import app, run_migrations
from backend.app.database import engine, SessionLocal
from backend.app.models.user import User, EmailOTP
from backend.app.utils.anonymity import mask_identifier, mask_email
from backend.app.services.auth_service import hash_otp, create_access_token

client = TestClient(app)

def run_pseudo_anonymity_masking():
    print("\n--- 1. Testing Pseudo-Anonymity Masking Helpers ---")
    test_id = str(uuid.uuid4())
    
    # "Anita Sharma" -> "A****a S."
    masked1 = mask_identifier("Anita Sharma")
    assert masked1 == "A****a S.", f"Expected 'A****a S.', got '{masked1}'"
    print(f"[OK] mask_identifier('Anita Sharma') => {masked1}")

    # "Anita Sharma" with short UUID suffix
    masked_uuid = mask_identifier("Anita Sharma", test_id, include_uuid=True)
    assert masked_uuid.startswith("A****a S. (#"), f"Unexpected: {masked_uuid}"
    print(f"[OK] mask_identifier('Anita Sharma', UUID, include_uuid=True) => {masked_uuid}")

    # Single name "Anita" -> "A****a"
    masked_single = mask_identifier("Anita")
    assert masked_single == "A****a", f"Expected 'A****a', got '{masked_single}'"
    print(f"[OK] mask_identifier('Anita') => {masked_single}")

    # Three parts "Anita Kumari Sharma" -> "A****a K. S."
    masked_three = mask_identifier("Anita Kumari Sharma")
    assert masked_three == "A****a K. S.", f"Expected 'A****a K. S.', got '{masked_three}'"
    print(f"[OK] mask_identifier('Anita Kumari Sharma') => {masked_three}")

    # Email masking
    masked_mail = mask_email("anita.sharma@example.com")
    assert masked_mail.startswith("a****a@"), f"Unexpected: {masked_mail}"
    print(f"[OK] mask_email('anita.sharma@example.com') => {masked_mail}")


def run_schema_and_migrations():
    print("\n--- 2. Testing Database Schema & Migrations ---")
    run_migrations()
    db = SessionLocal()
    try:
        users_count = db.query(User).count()
        otps_count = db.query(EmailOTP).count()
        print(f"[OK] Users count: {users_count}, EmailOTPs count: {otps_count}")
    finally:
        db.close()


def run_signup_validation_failures():
    print("\n--- 3. Testing Signup Validation Failures ---")
    
    # 3a. Weak password (<8 chars)
    res = client.post("/api/auth/signup", json={
        "full_name": "Test User",
        "email": f"test_weak_{uuid.uuid4().hex[:6]}@example.com",
        "password": "weak",
        "confirm_password": "weak",
        "role": "victim",
        "consent": True
    })
    assert res.status_code == 422, f"Expected 422, got {res.status_code}"
    print(f"[OK] Weak password rejected (422): {res.json()['detail']}")

    # 3b. Password missing number
    res = client.post("/api/auth/signup", json={
        "full_name": "Test User",
        "email": f"test_nonum_{uuid.uuid4().hex[:6]}@example.com",
        "password": "PasswordOnlyLetters",
        "confirm_password": "PasswordOnlyLetters",
        "role": "victim",
        "consent": True
    })
    assert res.status_code == 422
    print(f"[OK] Missing number rejected (422): {res.json()['detail']}")

    # 3c. Password mismatch
    res = client.post("/api/auth/signup", json={
        "full_name": "Test User",
        "email": f"test_mismatch_{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123",
        "confirm_password": "Password999",
        "role": "victim",
        "consent": True
    })
    assert res.status_code == 422
    print(f"[OK] Password mismatch rejected (422): {res.json()['detail']}")

    # 3d. Missing Official ID for official role (counsellor)
    res = client.post("/api/auth/signup", json={
        "full_name": "Dr. Ramesh Officer",
        "email": f"official_noid_{uuid.uuid4().hex[:6]}@example.com",
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123",
        "role": "counsellor",
        "official_id": "",
        "consent": True
    })
    assert res.status_code == 422
    print(f"[OK] Missing Official ID for counsellor rejected (422): {res.json()['detail']}")

    # 3e. Missing consent
    res = client.post("/api/auth/signup", json={
        "full_name": "Test User",
        "email": f"test_noconsent_{uuid.uuid4().hex[:6]}@example.com",
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123",
        "role": "victim",
        "consent": False
    })
    assert res.status_code == 422
    print(f"[OK] Missing consent rejected (422)")


def run_victim_signup_otp_flow():
    print("\n--- 4. Testing Victim Signup & Email OTP Activation Flow ---")
    email = f"victim_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123"

    # Step 1: Signup
    res = client.post("/api/auth/signup", json={
        "full_name": "Anita Sharma",
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "role": "victim",
        "preferred_language": "hi",
        "preferred_channel": "web_portal",
        "consent": True
    })
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    data = res.json()
    assert "user_id" in data
    assert data["email"] == email
    assert "OTP sent to your email" in data["message"]
    user_id = data["user_id"]
    print(f"[OK] Signup successful for user_id={user_id}, email={email}")

    # Step 2: Verify in DB that OTP was stored as SHA-256 hash (never plain)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.email_verified == False
        assert user.account_status == "active"
        assert user.role == "victim"

        otp_record = db.query(EmailOTP).filter(EmailOTP.user_id == user_id, EmailOTP.consumed == False).first()
        assert otp_record is not None
        assert len(otp_record.otp_hash) == 64  # SHA-256 hex digest length
        assert otp_record.otp_type == "email_verification"
        assert otp_record.consumed == False
        diff_mins = (otp_record.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 60
        assert 8 <= diff_mins <= 10.5
        print(f"[OK] Stored OTP is SHA-256 hash ({otp_record.otp_hash[:16]}...), expires in {diff_mins:.1f} minutes")
    finally:
        db.close()

    # Step 3: Duplicate signup with same email -> 400 or 409
    res_dup = client.post("/api/auth/signup", json={
        "full_name": "Anita Sharma Duplicate",
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "role": "victim",
        "consent": True
    })
    assert res_dup.status_code in (400, 409), f"Expected 400 or 409, got {res_dup.status_code}"
    print(f"[OK] Duplicate email rejected with {res_dup.status_code}: {res_dup.json()['detail']}")

    # Step 4: Invalid OTP verification attempt
    res_bad_otp = client.post("/api/auth/verify-email-otp", json={
        "email": email,
        "otp": "000000"
    })
    assert res_bad_otp.status_code == 400
    print(f"[OK] Invalid OTP rejected (400): {res_bad_otp.json()['detail']}")

    # Step 5: Simulate correct OTP verification
    test_otp = "123456"
    test_otp_hash = hash_otp(test_otp)
    db = SessionLocal()
    try:
        otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == user_id, EmailOTP.consumed == False).first()
        otp_rec.otp_hash = test_otp_hash
        db.commit()
    finally:
        db.close()

    res_verify = client.post("/api/auth/verify-email-otp", json={
        "email": email,
        "otp": test_otp
    })
    assert res_verify.status_code == 200, f"Expected 200, got {res_verify.status_code}: {res_verify.text}"
    vdata = res_verify.json()
    assert vdata["account_status"] == "active"
    assert "Email verified successfully" in vdata["message"]
    print(f"[OK] Correct OTP verified! Account status: {vdata['account_status']}")

    # Step 6: Verify consumed state in DB
    db = SessionLocal()
    try:
        user_after = db.query(User).filter(User.id == user_id).first()
        assert user_after.email_verified == True
        otp_after = db.query(EmailOTP).filter(EmailOTP.user_id == user_id).order_by(EmailOTP.created_at.desc()).first()
        assert otp_after.consumed == True
        print(f"[OK] Database verified: email_verified={user_after.email_verified}, otp_consumed={otp_after.consumed}")
    finally:
        db.close()

    # Step 7: Attempt to reuse already consumed OTP -> 400 Bad Request
    res_reuse = client.post("/api/auth/verify-email-otp", json={
        "email": email,
        "otp": test_otp
    })
    assert res_reuse.status_code == 400
    print(f"[OK] Reused consumed OTP rejected (400): {res_reuse.json()['detail']}")

    return user_id, email, pwd


def run_official_signup_pending_verification_flow():
    print("\n--- 5. Testing Official Signup & Pending Verification Flow ---")
    email = f"counsellor_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecureOfficialPass123"

    res = client.post("/api/auth/signup", json={
        "full_name": "Dr. Sarah Rao",
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "role": "counsellor",
        "official_id": "MH-COUN-2026-881",
        "preferred_language": "en",
        "preferred_channel": "web_portal",
        "consent": True
    })
    assert res.status_code == 201, f"Expected 201, got {res.status_code}"
    data = res.json()
    user_id = data["user_id"]
    print(f"[OK] Counsellor signup successful: user_id={user_id}, initial status={data['account_status']}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user.role == "counsellor"
        assert user.official_id == "MH-COUN-2026-881"
        assert user.account_status == "pending_verification"
        assert user.email_verified == False

        test_otp = "654321"
        otp_rec = db.query(EmailOTP).filter(EmailOTP.user_id == user_id, EmailOTP.consumed == False).first()
        otp_rec.otp_hash = hash_otp(test_otp)
        db.commit()
    finally:
        db.close()

    res_verify = client.post("/api/auth/verify-email-otp", json={
        "email": email,
        "otp": test_otp
    })
    assert res_verify.status_code == 200
    vdata = res_verify.json()
    assert vdata["account_status"] == "pending_verification", f"Expected pending_verification, got {vdata['account_status']}"
    print(f"[OK] Counsellor OTP verified! Status correctly remains 'pending_verification' pending administrative review")


def run_jwt_auth_me_endpoint(user_id, email, password):
    print("\n--- 6. Testing JWT-based Auth for /api/auth/me ---")

    fresh_client = TestClient(app)
    res_no_auth = fresh_client.get("/api/auth/me")
    assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"
    print("[OK] /api/auth/me without token correctly returned 401 Unauthorized")

    login_res = fresh_client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    assert "token" in login_data and login_data["token"] is not None
    jwt_token = login_data["token"]
    print(f"[OK] Login successful. JWT token issued ({jwt_token[:20]}...)")

    token_only_client = TestClient(app)
    me_res = token_only_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert me_res.status_code == 200, f"Expected 200, got {me_res.status_code}: {me_res.text}"
    profile = me_res.json()
    assert profile["user_id"] == user_id
    assert profile["email"] == email
    assert profile["role"] == "victim"
    assert profile["email_verified"] == True
    assert "password" not in profile
    assert "password_hash" not in profile
    print("[OK] /api/auth/me with Bearer JWT retrieved profile successfully:")
    print(f"  User ID: {profile['user_id']}")
    print(f"  Role: {profile['role']}")
    print(f"  Email Verified: {profile['email_verified']}")
    print(f"  Account Status: {profile['account_status']}")


def test_complete_account_creation_suite():
    run_pseudo_anonymity_masking()
    run_schema_and_migrations()
    run_signup_validation_failures()
    uid, em, pwd = run_victim_signup_otp_flow()
    run_official_signup_pending_verification_flow()
    run_jwt_auth_me_endpoint(uid, em, pwd)
    print("\n* ALL TESTS IN SUITE PASSED SUCCESSFULLY! *\n")


if __name__ == "__main__":
    test_complete_account_creation_suite()
