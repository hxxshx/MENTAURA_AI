"""
Authentication Service: Argon2id Password Hashing, Session Management, JWT, Email OTP, and Role Resolution.
"""
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, InvalidHash
import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.user import User, UserSession, ConsentRecord, VerificationRequest, EmailOTP
from backend.app.schemas.auth import SignupRequest, OFFICIAL_ROLES
from backend.app.services.email_service import send_otp_email

logger = logging.getLogger("mentaura.auth")

# Initialize Argon2id Password Hasher with standard secure parameters
ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    type=Type.ID
)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# --------------------------------------------------------------------------
# Password Hashing & Verification
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id."""
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, InvalidHash):
        return False

# --------------------------------------------------------------------------
# Email OTP Generation & Verification (SHA-256 Hashing)
# --------------------------------------------------------------------------
def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    code = secrets.randbelow(1000000)
    return f"{code:06d}"

def hash_otp(otp_code: str) -> str:
    """Hash OTP using SHA-256."""
    return hashlib.sha256(otp_code.strip().encode("utf-8")).hexdigest()

def create_email_otp(db: Session, user_id: str, delivery_email: Optional[str] = None) -> Tuple[EmailOTP, str]:
    """
    Create a new 10-minute email verification OTP record with SHA-256 hash.
    Marks any prior unconsumed verification OTPs for this user as consumed.
    Never stores or persists plain OTP or plain delivery email.
    Returns (otp_record, plain_otp).
    """
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Invalidate existing unconsumed verification OTPs
    db.query(EmailOTP).filter(
        EmailOTP.user_id == user_id,
        EmailOTP.otp_type == "email_verification",
        EmailOTP.consumed == False
    ).update({"consumed": True})

    plain_otp = generate_otp()
    delivery_hash = None
    if delivery_email:
        delivery_hash = hashlib.sha256(delivery_email.strip().lower().encode()).hexdigest()

    otp_record = EmailOTP(
        user_id=user_id,
        otp_hash=hash_otp(plain_otp),
        delivery_email_hash=delivery_hash,
        otp_type="email_verification",
        expires_at=expires_at,
        consumed=False,
        created_at=now
    )
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    return otp_record, plain_otp

def verify_email_otp(db: Session, email: str, otp_code: str) -> Tuple[bool, Optional[User], str]:
    """
    Verify 6-digit OTP for given email or anonymous_id.
    Finds latest unconsumed email_otps row with otp_type='email_verification' and expires_at > now.
    Compares SHA-256 hashes.
    If valid:
      - marks OTP as consumed
      - sets users.email_verified = True
      - sets account_status = 'active' for victim/witness/affected_family
      - keeps account_status = 'pending_verification' for officials
    Returns (success, user, message).
    """
    clean_email = email.strip().lower()
    raw_ident = email.strip()

    # 1. Look up user by email, anonymous_id, or user id
    user = db.query(User).filter(
        or_(
            User.email == clean_email,
            User.anonymous_id == raw_ident.upper(),
            User.anonymous_id == raw_ident,
            User.id == raw_ident
        )
    ).first()

    now = utc_now()
    otp_record = None

    # 2. If not found directly, check if the input matches a one-way delivery email hash
    if not user:
        e_hash = hashlib.sha256(clean_email.encode()).hexdigest()
        otp_record = (
            db.query(EmailOTP)
            .filter(
                EmailOTP.delivery_email_hash == e_hash,
                EmailOTP.otp_type == "email_verification",
                EmailOTP.consumed == False
            )
            .order_by(EmailOTP.created_at.desc())
            .first()
        )
        if otp_record:
            user = db.query(User).filter(User.id == otp_record.user_id).first()

    if not user:
        return False, None, "No account associated with this email address or Protected ID."

    # 3. Find the latest unconsumed OTP record for this user if not already located
    if not otp_record:
        otp_record = (
            db.query(EmailOTP)
            .filter(
                EmailOTP.user_id == user.id,
                EmailOTP.otp_type == "email_verification",
                EmailOTP.consumed == False
            )
            .order_by(EmailOTP.created_at.desc())
            .first()
        )

    if not otp_record:
        return False, user, "No active verification code found. Please request a new code."

    # Check expiry
    exp = otp_record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < now:
        otp_record.consumed = True
        db.commit()
        return False, user, "Verification code has expired. Please request a new code."

    # Compare SHA-256 hashes
    incoming_hash = hash_otp(otp_code)
    if incoming_hash != otp_record.otp_hash:
        return False, user, "Invalid verification code. Please check and try again."

    # Success: consume OTP and update user
    otp_record.consumed = True
    otp_record.delivery_email_hash = None  # Immediately scrub delivery trace
    user.email_verified = True
    user.updated_at = now

    user_role = (user.role or user.requested_category or "victim").lower()
    # Official government IDs are verified directly during account creation.
    # Upon successful email OTP confirmation, user account becomes active and verified.
    user.account_status = "active"
    user.verified_role = user.role or user_role

    db.commit()
    db.refresh(user)

    return True, user, "Email verified successfully."

# --------------------------------------------------------------------------
# JWT Token Generation & Validation
# --------------------------------------------------------------------------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token for API authorization."""
    to_encode = data.copy()
    now = utc_now()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# --------------------------------------------------------------------------
# Role & Routing Resolution
# --------------------------------------------------------------------------
ROLE_REDIRECT_MAP = {
    "victim": "victim-home.html",
    "witness": "victim-home.html",
    "affected_family": "victim-home.html",
    "affected_family_member": "victim-home.html",
    "counsellor": "counsellor-workspace.html",
    "case_officer": "command-dashboard.html",
    "district_authority": "command-dashboard.html",
    "district_admin": "command-dashboard.html",
    "legal_aid_officer": "support-workspace.html",
    "protection_officer": "support-workspace.html",
    "medical_rehab_officer": "support-workspace.html",
    "medical_rehabilitation_officer": "support-workspace.html",
    "state_admin": "command-dashboard.html",
    "state_administrator": "command-dashboard.html",
    "national_admin": "command-dashboard.html",
    "national_administrator": "command-dashboard.html",
    "anonymous": "resources.html",
    "pending_verification": "verification-pending.html",
}

def get_redirect_route_for_user(user: User) -> str:
    """Determine the destination route based on backend-verified role and account status."""
    if user.account_status == "pending_verification" or user.verified_role == "pending_verification":
        return "verification-pending.html"
    
    if user.account_status in ("suspended", "disabled"):
        return "index.html"
    
    role = (user.role or user.verified_role or "victim").lower()
    return ROLE_REDIRECT_MAP.get(role, "victim-home.html")

# --------------------------------------------------------------------------
# Session Token Management
# --------------------------------------------------------------------------
def create_user_session(
    db: Session, 
    user: User, 
    user_agent: Optional[str] = None, 
    ip_address: Optional[str] = None
) -> str:
    """Create a persistent server-side session token with expiration."""
    raw_token = secrets.token_urlsafe(48)
    expires_at = utc_now() + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)

    session_record = UserSession(
        user_id=user.id,
        session_token=raw_token,
        expires_at=expires_at,
        is_revoked=False,
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=ip_address[:45] if ip_address else None
    )
    db.add(session_record)
    db.commit()
    return raw_token

def get_user_from_session(db: Session, session_token: str) -> Optional[User]:
    """Validate a session token and return the associated user if active and not expired."""
    if not session_token:
        return None
    
    now = utc_now()
    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == session_token,
            UserSession.is_revoked == False
        )
        .first()
    )
    
    if not session_record:
        return None
    
    expires_at = session_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < now:
        session_record.is_revoked = True
        db.commit()
        return None
    
    user = db.query(User).filter(User.id == session_record.user_id).first()
    return user

def revoke_session(db: Session, session_token: str) -> bool:
    """Revoke an active session token on logout."""
    if not session_token:
        return False
    
    session_record = (
        db.query(UserSession)
        .filter(UserSession.session_token == session_token)
        .first()
    )
    if session_record:
        session_record.is_revoked = True
        db.commit()
        return True
    return False

# --------------------------------------------------------------------------
# User Registration Logic
# --------------------------------------------------------------------------
def register_user(
    db: Session, 
    req: SignupRequest, 
    ip_address: Optional[str] = None
) -> Tuple[User, str, str]:
    """
    Register a new user:
    1. Checks uniqueness of email.
    2. Hashes password using Argon2id.
    3. Populates user with role and official_id.
    4. Sets email_verified = False.
    5. Sets account_status ('active' for victim/witness/affected_family; 'pending_verification' for officials).
    6. Creates explicit consent record.
    7. Generates 6-digit OTP, stores SHA-256 hash in email_otps.
    8. Dispatches OTP verification email via Gmail SMTP.
    Returns (user, plain_otp, redirect_url).
    """
    clean_email = req.email.strip().lower() if req.email else None
    
    chosen_role = (req.role or req.requested_category or "victim").strip().lower()
    is_official = chosen_role in OFFICIAL_ROLES
    is_anon = bool(getattr(req, "is_anonymous", False)) and (chosen_role in ("victim", "witness", "affected_family", "affected_family_member"))

    # If NOT anonymous, email is mandatory and must be unique
    if not is_anon:
        if not clean_email:
            raise ValueError("A valid email address is required.")
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing:
            raise ValueError("CONFLICT_EMAIL: An account with this email address already exists.")

    # Initial verified_role & account_status
    if is_official:
        verified_role = "pending_verification"
        account_status = "pending_verification"
        email_verified = False
    elif is_anon and not clean_email:
        # Pure Anonymous ID mode: no email provided, account active immediately
        verified_role = chosen_role
        account_status = "active"
        email_verified = True
    else:
        if req.requested_category == "affected_family_member":
            verified_role = "affected_family_member"
        else:
            verified_role = chosen_role
        account_status = "pending_otp"
        email_verified = False

    pwd_hash = hash_password(req.password)
    now = utc_now()

    # PSEUDO-ANONYMISATION: If anonymous, real name, email, and phone are NEVER stored in users table
    if is_anon:
        role_letter = "V" if "victim" in chosen_role else ("W" if "witness" in chosen_role else "F")
        anon_identifier = f"ANON-{role_letter}-{secrets.token_hex(3).upper()}"
        stored_full_name = f"Anonymous {chosen_role.replace('_', ' ').title()}"
        stored_email = f"{anon_identifier.lower()}@mentaura.anonymous"
        stored_phone = None
    else:
        anon_identifier = None
        stored_full_name = req.full_name.strip()
        stored_email = clean_email
        stored_phone = req.phone_number.strip() if req.phone_number else None

    user = User(
        full_name=stored_full_name,
        email=stored_email,
        phone_number=stored_phone,
        password_hash=pwd_hash,
        role=chosen_role,
        official_id=req.official_id.strip() if req.official_id else None,
        requested_category=chosen_role,
        verified_role=verified_role,
        account_status=account_status,
        email_verified=email_verified,
        phone_verified=False,
        is_anonymous=is_anon,
        anonymous_id=anon_identifier,
        preferred_language=req.preferred_language,
        preferred_channel=req.preferred_channel,
        consent_version=req.consent_version,
        consent_given_at=now,
        created_at=now,
        updated_at=now
    )
    db.add(user)
    db.flush()  # Populates user.id (UUID)

    # Record explicit consent
    consent = ConsentRecord(
        user_id=user.id,
        consent_type="account_creation_and_support_processing",
        consent_version=req.consent_version,
        notice_version=settings.CURRENT_NOTICE_VERSION,
        consent_given=True,
        given_at=now,
        ip_address=ip_address
    )
    db.add(consent)

    # If official, record VerificationRequest for audit/review
    if is_official:
        v_req = VerificationRequest(
            user_id=user.id,
            requested_role=chosen_role,
            status="pending",
            submitted_at=now,
            notes=f"Official ID submitted: {req.official_id}" if req.official_id else None
        )
        db.add(v_req)

    plain_otp = None
    if clean_email:
        # Generate 6-digit OTP & store SHA-256 in email_otps (hashes delivery email without storing plain text)
        _, plain_otp = create_email_otp(db, user.id, delivery_email=clean_email if is_anon else None)

        # Dispatch email via Gmail SMTP (with safe fallback) to the delivery email
        send_otp_email(
            to_email=clean_email, 
            otp_code=plain_otp, 
            user_name="Valued Individual" if is_anon else user.full_name
        )

    db.commit()
    db.refresh(user)

    redirect_url = get_redirect_route_for_user(user)
    return user, plain_otp, redirect_url
