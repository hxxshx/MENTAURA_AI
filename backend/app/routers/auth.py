"""
Authentication Endpoints: Signup, OTP Email Verification, Login, Logout, Session & JWT State.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import (
    SignupRequest, SignupResponse, LoginRequest, LoginResponse,
    UserOut, MeResponse, VerifyEmailOtpRequest, VerifyEmailOtpResponse,
    ResendOtpRequest, ForgotPasswordRequest, ForgotPasswordResponse,
    VerifyOfficialIdRequest, VerifyOfficialIdResponse, OfficialIdMetadata
)
import secrets
from backend.app.services.auth_service import (
    register_user, verify_password, hash_password, create_user_session,
    get_user_from_session, revoke_session, get_redirect_route_for_user,
    verify_email_otp, create_email_otp, create_access_token, decode_access_token
)
from backend.app.services.official_id_service import verify_government_official_id
from backend.app.services.email_service import send_otp_email
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address safely from headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None

def get_session_token_from_request(request: Request) -> Optional[str]:
    """Extract session token from HttpOnly cookie or Authorization Bearer header."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: Extract and validate user from JWT Bearer token or session cookie.
    Provides strict JWT authentication with seamless session cookie fallback.
    """
    auth_header = request.headers.get("Authorization")
    user = None

    # 1. Primary: JWT Bearer Token validation (Header or query param 'token')
    raw_token = None
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:].strip()
    elif "token" in request.query_params:
        raw_token = request.query_params.get("token")

    if raw_token:
        payload = decode_access_token(raw_token)
        if payload:
            user_id = payload.get("sub") or payload.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
        if not user:
            # Fallback: check if bearer token was a server session token
            user = get_user_from_session(db, raw_token)

    # 2. Secondary: HttpOnly Session Cookie validation
    if not user:
        cookie_token = request.cookies.get(settings.COOKIE_NAME)
        if cookie_token:
            user = get_user_from_session(db, cookie_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with a valid token or session."
        )

    if user.account_status in ("suspended", "disabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is currently unavailable. Please contact the authorised support team."
        )

    return user


# --------------------------------------------------------------------------
# 1. Enhanced Signup Endpoint (Creates User & Dispatches OTP Without Auto-Login)
# --------------------------------------------------------------------------
@router.post(
    "/signup", 
    response_model=SignupResponse, 
    status_code=status.HTTP_201_CREATED
)
def signup(
    req: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Create account with 11-role validation, password hashing, and email OTP dispatch.
    For pure pseudo-anonymous accounts without email, creates active account immediately with Anonymous ID.
    """
    ip_addr = get_client_ip(request)

    try:
        user, plain_otp, _ = register_user(db, req, ip_address=ip_addr)
    except ValueError as e:
        error_msg = str(e)
        if "CONFLICT_EMAIL" in error_msg or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in."
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not complete account creation right now. Please try again later."
        )

    log_audit_event(
        db=db,
        action="signup_initiated",
        user_id=user.id,
        details=f"role={user.role}, status={user.account_status}, anonymous_mode={'enabled' if user.is_anonymous else 'disabled'}, otp_dispatched={bool(plain_otp)}",
        ip_address=ip_addr
    )

    jwt_token = None
    redirect_url = None
    out_user = None

    if user.account_status == "active":
        # Instant active session for pure anonymous mode
        user_agent = request.headers.get("User-Agent")
        jwt_payload = {
            "sub": user.id,
            "role": user.role,
            "verified_role": user.verified_role,
            "account_status": user.account_status,
            "is_anonymous": user.is_anonymous,
            "anonymous_id": user.anonymous_id
        }
        jwt_token = create_access_token(jwt_payload)
        session_token = create_user_session(db, user, user_agent=user_agent, ip_address=ip_addr)
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=session_token,
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/"
        )
        redirect_url = get_redirect_route_for_user(user)
        out_user = UserOut.model_validate(user)
        message = f"Anonymous account created successfully. Your Anonymous ID is {user.anonymous_id}."
    else:
        message = "Verification code sent to your delivery email. Please enter the OTP to activate your account."

    return SignupResponse(
        user_id=user.id,
        email=user.email,
        message=message,
        anonymous_id=user.anonymous_id,
        account_status=user.account_status,
        verified_role=user.verified_role,
        redirect_url=redirect_url,
        token=jwt_token,
        user=out_user,
        dev_otp=None
    )


# --------------------------------------------------------------------------
# 1b. Government Official ID Pre-Registration Verification Endpoint
# --------------------------------------------------------------------------
@router.post(
    "/verify-official-id",
    response_model=VerifyOfficialIdResponse
)
def verify_official_id_endpoint(
    req: VerifyOfficialIdRequest,
    request: Request
):
    """
    Verify government official ID credentials against the national credential registry.
    Returns authentic department, cadre, and designation details if valid.
    """
    valid, message, metadata = verify_government_official_id(req.official_id, req.role or "national_admin")
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    return VerifyOfficialIdResponse(
        valid=True,
        message=message,
        data=OfficialIdMetadata(**metadata)
    )


# --------------------------------------------------------------------------
# 2. Email OTP Verification Endpoint (Issues Auth Session & JWT Upon Success)
# --------------------------------------------------------------------------
@router.post(
    "/verify-email-otp",
    response_model=VerifyEmailOtpResponse
)
def verify_email_otp_endpoint(
    req: VerifyEmailOtpRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Verify 6-digit email OTP against SHA-256 hash in email_otps table.
    Activates account, issues session cookie & JWT, and returns role-based redirect_url.
    """
    ip_addr = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    success, user, message = verify_email_otp(db, req.email, req.otp)

    if not success:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    log_audit_event(
        db=db,
        action="email_otp_verified",
        user_id=user.id,
        details=f"status={user.account_status}, email_verified={user.email_verified}",
        ip_address=ip_addr
    )

    jwt_token = None
    redirect_url = get_redirect_route_for_user(user)

    if user.account_status == "active":
        # Victim / Witness / Affected Family: Log them in and issue JWT & session cookie
        jwt_payload = {
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "role": user.role or user.verified_role,
            "account_status": user.account_status
        }
        jwt_token = create_access_token(jwt_payload)

        session_token = create_user_session(db, user, user_agent=user_agent, ip_address=ip_addr)
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=session_token,
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/"
        )
        resp_message = "Email verified successfully. Logging you in..."
    else:
        # Official / Administrator: Remains pending verification until admin approves
        redirect_url = "verification-pending.html"
        resp_message = "Email verified. Your official credentials are under review by an authorized administrator."

    return VerifyEmailOtpResponse(
        message=resp_message,
        account_status=user.account_status,
        token=jwt_token,
        redirect_url=redirect_url,
        user=UserOut.model_validate(user)
    )


# --------------------------------------------------------------------------
# 3. Resend OTP Endpoint
# --------------------------------------------------------------------------
@router.post("/resend-otp")
def resend_otp(
    req: ResendOtpRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Generate a new 6-digit OTP and resend verification email.
    """
    ip_addr = get_client_ip(request)
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        # Do not reveal email existence
        return {"message": "If an account exists with this email, a new verification code has been sent."}

    if user.email_verified:
        return {"message": "This email address is already verified. Please log in."}

    _, plain_otp = create_email_otp(db, user.id)
    send_otp_email(to_email=user.email, otp_code=plain_otp, user_name=user.full_name)

    log_audit_event(
        db=db,
        action="otp_resend",
        user_id=user.id,
        details="New OTP code generated and dispatched",
        ip_address=ip_addr
    )

    return {"message": "A new verification code has been sent to your email."}


# --------------------------------------------------------------------------
# 4. Login Endpoint (Issues Session Cookie + JWT Access Token)
# --------------------------------------------------------------------------
@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    ip_addr = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    raw_ident = req.email.strip()
    clean_email = raw_ident.lower()
    user = db.query(User).filter(
        or_(
            User.email == clean_email,
            User.anonymous_id == raw_ident.upper(),
            User.anonymous_id == raw_ident
        )
    ).first()

    # Check lockout
    now = datetime.now(timezone.utc)
    if user and user.locked_until:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            log_audit_event(db, "login_locked", user.id, "Account locked out", ip_addr)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked due to multiple failed attempts. Please try again in 15 minutes."
            )
        else:
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # Credentials verification
    if not user or not verify_password(req.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
            db.commit()
            log_audit_event(db, "login_failed", user.id, f"attempt={user.failed_login_attempts}", ip_addr)
        else:
            log_audit_event(db, "login_failed_unknown", details=f"email={clean_email}", ip_address=ip_addr)
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect. Please try again."
        )

    # Check suspended/disabled status
    if user.account_status in ("suspended", "disabled"):
        log_audit_event(db, "login_suspended", user.id, f"status={user.account_status}", ip_addr)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is currently unavailable. Please contact the authorised support team."
        )

    # Reset attempts & record login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()

    # Generate JWT access token
    jwt_payload = {
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "role": user.role or user.verified_role,
        "account_status": user.account_status
    }
    jwt_token = create_access_token(jwt_payload)

    # Issue session cookie
    session_token = create_user_session(db, user, user_agent=user_agent, ip_address=ip_addr)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )

    log_audit_event(db, "login_success", user.id, f"role={user.role or user.verified_role}", ip_addr)
    redirect_url = get_redirect_route_for_user(user)

    if user.account_status == "pending_verification":
        msg = "Your account is awaiting official verification. Please contact an authorized administrator."
    else:
        msg = "Logged in successfully."

    return LoginResponse(
        message=msg,
        user=UserOut.model_validate(user),
        redirect_url=redirect_url,
        token=jwt_token
    )


# --------------------------------------------------------------------------
# 5. Logout Endpoint
# --------------------------------------------------------------------------
@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    token = get_session_token_from_request(request)
    ip_addr = get_client_ip(request)

    if token:
        user = get_user_from_session(db, token)
        revoke_session(db, token)
        if user:
            log_audit_event(db, "logout", user.id, "User logged out", ip_addr)

    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/"
    )
    return {"message": "Logged out successfully."}


# --------------------------------------------------------------------------
# 6. Current User Profile Endpoint (/api/auth/me) - JWT & Session Auth Guard
# --------------------------------------------------------------------------
@router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Authenticated profile endpoint for /api/auth/me.
    Returns clean user profile without exposing sensitive official_id.
    """
    resolved_role = current_user.role or current_user.verified_role or "victim"
    is_anon = bool(getattr(current_user, "is_anonymous", False))
    anon_id = getattr(current_user, "anonymous_id", None)

    masked_n = None
    masked_e = None
    if is_anon:
        if current_user.full_name.startswith("Anonymous"):
            masked_n = current_user.full_name
        else:
            from backend.app.utils.anonymity import mask_identifier
            masked_n = mask_identifier(current_user.full_name, current_user.id)
        masked_e = current_user.email

    return MeResponse(
        user_id=current_user.id,
        id=current_user.id,
        email=current_user.email,
        full_name=masked_n if is_anon and masked_n else current_user.full_name,
        role=resolved_role,
        verified_role=current_user.verified_role or resolved_role,
        preferred_language=current_user.preferred_language or "en",
        preferred_channel=current_user.preferred_channel or "web_portal",
        account_status=current_user.account_status,
        email_verified=bool(current_user.email_verified),
        is_anonymous=is_anon,
        anonymous_id=anon_id,
        masked_name=masked_n,
        masked_email=masked_e
    )


# --------------------------------------------------------------------------
# 7. Forgot Password Endpoint
# --------------------------------------------------------------------------
@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    log_audit_event(
        db, 
        "forgot_password_inquiry", 
        details=f"email={req.email.strip().lower()}", 
        ip_address=get_client_ip(request)
    )
    return ForgotPasswordResponse(
        status="info",
        message="Password recovery will be available after secure email verification is connected."
    )


# --------------------------------------------------------------------------
# 8. Anonymous Session Endpoint (Limited Guest Access)
# --------------------------------------------------------------------------
@router.post("/anonymous-session")
def create_anonymous_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Issue an ephemeral, limited anonymous session for victims who wish to browse
    support resources without registering a full account.
    """
    ip_addr = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    now = datetime.now(timezone.utc)
    anon_hex = secrets.token_hex(6)
    anon_user_id = f"anon_{anon_hex}"
    anon_email = f"{anon_user_id}@mentaura.anonymous"

    # Create lightweight guest user
    anon_user = User(
        id=anon_user_id,
        full_name="Anonymous Guest",
        email=anon_email,
        password_hash=hash_password(secrets.token_urlsafe(16)),
        role="anonymous",
        requested_category="anonymous",
        verified_role="anonymous",
        account_status="active",
        email_verified=True,
        phone_verified=False,
        preferred_language="EN",
        preferred_channel="web_portal",
        consent_version=settings.CURRENT_CONSENT_VERSION,
        consent_given_at=now,
        created_at=now,
        updated_at=now
    )
    db.add(anon_user)
    db.commit()
    db.refresh(anon_user)

    jwt_payload = {
        "sub": anon_user.id,
        "user_id": anon_user.id,
        "email": anon_user.email,
        "role": "anonymous",
        "account_status": "active"
    }
    jwt_token = create_access_token(jwt_payload, expires_delta=timedelta(hours=6))

    session_token = create_user_session(db, anon_user, user_agent=user_agent, ip_address=ip_addr)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=session_token,
        max_age=360 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/"
    )

    log_audit_event(db, "anonymous_session_started", anon_user.id, "Limited anonymous access initiated", ip_addr)

    return {
        "message": "Notice: Ephemeral guest access is deprecated. Dedicated backend identity anonymisation is integrated directly into account registration for affected individuals and families (Victim, Witness, Affected Family).",
        "deprecated": True,
        "token": jwt_token,
        "redirect_url": "resources.html",
        "account_status": "active",
        "user": {
            "id": anon_user.id,
            "full_name": "Anonymous Guest",
            "role": "anonymous",
            "verified_role": "anonymous",
            "account_status": "active",
            "is_anonymous": True
        }
    }
