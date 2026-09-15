"""
Development Seed Script: Populate initial test accounts with Argon2id hashed passwords.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.user import User, ConsentRecord, VerificationRequest
from backend.app.services.auth_service import hash_password

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    common_pwd = hash_password("Mentaura@2026")

    test_users = [
        {
            "full_name": "Aanya Sharma",
            "email": "victim@mentaura.example",
            "requested_category": "victim_complainant",
            "verified_role": "victim",
            "account_status": "active"
        },
        {
            "full_name": "Rohan Deshmukh",
            "email": "witness@mentaura.example",
            "requested_category": "witness",
            "verified_role": "witness",
            "account_status": "active"
        },
        {
            "full_name": "Sunita Devi",
            "email": "family@mentaura.example",
            "requested_category": "affected_family_member",
            "verified_role": "affected_family_member",
            "account_status": "active"
        },
        {
            "full_name": "Dr. Priya Nair",
            "email": "counsellor@mentaura.example",
            "requested_category": "counsellor",
            "verified_role": "counsellor",
            "account_status": "active"
        },
        {
            "full_name": "Rajesh Varma, IAS",
            "email": "district@mentaura.example",
            "requested_category": "district_authority",
            "verified_role": "district_authority",
            "account_status": "active"
        },
        {
            "full_name": "Inspector Anand Rao",
            "email": "caseofficer@mentaura.example",
            "requested_category": "case_officer",
            "verified_role": "case_officer",
            "account_status": "active"
        },
        {
            "full_name": "Advocate Meera Sen",
            "email": "legalaid@mentaura.example",
            "requested_category": "legal_aid_officer",
            "verified_role": "legal_aid_officer",
            "account_status": "active"
        },
        {
            "full_name": "State Director S. Mukherjee",
            "email": "stateadmin@mentaura.example",
            "requested_category": "state_administrator",
            "verified_role": "state_administrator",
            "account_status": "active"
        },
        {
            "full_name": "National Coordinator Dr. V. Patel",
            "email": "nationaladmin@mentaura.example",
            "requested_category": "national_administrator",
            "verified_role": "national_administrator",
            "account_status": "active"
        },
        {
            "full_name": "Pending Official User",
            "email": "pending@mentaura.example",
            "requested_category": "protection_officer",
            "verified_role": "pending_verification",
            "account_status": "pending_verification"
        },
        {
            "full_name": "Suspended Test User",
            "email": "suspended@mentaura.example",
            "requested_category": "victim_complainant",
            "verified_role": "victim",
            "account_status": "suspended"
        }
    ]

    count = 0
    for u_data in test_users:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if not existing:
            user = User(
                full_name=u_data["full_name"],
                email=u_data["email"],
                password_hash=common_pwd,
                requested_category=u_data["requested_category"],
                verified_role=u_data["verified_role"],
                account_status=u_data["account_status"],
                preferred_language="EN",
                preferred_channel="web",
                email_verified=True,
                consent_version="1.0",
                consent_given_at=now,
                created_at=now,
                updated_at=now
            )
            db.add(user)
            db.flush()

            # Record consent
            consent = ConsentRecord(
                user_id=user.id,
                consent_type="account_creation_and_support_processing",
                consent_version="1.0",
                notice_version="1.0",
                consent_given=True,
                given_at=now
            )
            db.add(consent)

            if u_data["account_status"] == "pending_verification":
                v_req = VerificationRequest(
                    user_id=user.id,
                    requested_role=u_data["requested_category"],
                    status="pending",
                    submitted_at=now
                )
                db.add(v_req)

            count += 1

    db.commit()
    db.close()
    print(f"Successfully seeded {count} test user(s) into database. Common password: Mentaura@2026")

if __name__ == "__main__":
    seed_database()
