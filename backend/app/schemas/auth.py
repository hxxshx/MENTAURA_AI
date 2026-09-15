"""
Pydantic Schemas for Authentication, Registration, and Session State.
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict
from typing import Optional
from datetime import datetime

# Standard 11 Roles
VALID_ROLES = {
    "victim",
    "witness",
    "affected_family",
    "counsellor",
    "case_officer",
    "district_authority",
    "legal_aid_officer",
    "protection_officer",
    "medical_rehab_officer",
    "state_admin",
    "national_admin",
    "anonymous",
}

# Roles that require verified Official / Government / Employee ID
OFFICIAL_ROLES = {
    "counsellor",
    "case_officer",
    "district_authority",
    "legal_aid_officer",
    "protection_officer",
    "medical_rehab_officer",
    "state_admin",
    "national_admin",
}

# Roles representing Affected Individuals & Families eligible for anonymity protection
AFFECTED_ROLES = {
    "victim",
    "witness",
    "affected_family",
}

# Role normalizer for backward compatibility with older labels/enums
ROLE_ALIASES = {
    "anonymous": "anonymous",
    "guest": "anonymous",
    "victim_complainant": "victim",
    "victim": "victim",
    "witness": "witness",
    "affected_family_member": "affected_family",
    "affected_family": "affected_family",
    "counsellor": "counsellor",
    "case_officer": "case_officer",
    "district_authority": "district_authority",
    "district_admin": "district_authority",
    "legal_aid_officer": "legal_aid_officer",
    "protection_officer": "protection_officer",
    "medical_rehabilitation_officer": "medical_rehab_officer",
    "medical_rehab_officer": "medical_rehab_officer",
    "administrator": "national_admin",
    "admin": "national_admin",
    "state_administrator": "state_admin",
    "state_admin": "state_admin",
    "national_administrator": "national_admin",
    "national_admin": "national_admin",
}

class VerifyOfficialIdRequest(BaseModel):
    official_id: str = Field(..., min_length=4, max_length=100, description="Government Official / Cadre ID")
    role: Optional[str] = Field("national_admin", max_length=50)

class OfficialIdMetadata(BaseModel):
    official_id: str
    department: str
    designation: str
    cadre: str
    status: str
    verification_agency: str

class VerifyOfficialIdResponse(BaseModel):
    valid: bool
    message: str
    data: Optional[OfficialIdMetadata] = None

# Controlled Preferred Channels
VALID_CHANNELS = {
    "web_portal",
    "mobile_app",
    "sms",
    "ivrs",
    "helpline",
}

CHANNEL_ALIASES = {
    "web": "web_portal",
    "web_portal": "web_portal",
    "mobile_app": "mobile_app",
    "sms": "sms",
    "ivrs": "ivrs",
    "ivrs_voice": "ivrs",
    "helpline": "helpline",
    "helpline_followup": "helpline",
}

# Controlled Languages
VALID_LANGUAGES = {
    "EN", "HI", "TA", "TE", "KN", "ML", "MR", "BN"
}


class SignupRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: Optional[str] = Field(None, min_length=8, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=30)
    
    role: Optional[str] = Field(None, description="Selected role at registration")
    requested_category: Optional[str] = Field(None, description="Backward compatible role/category")
    official_id: Optional[str] = Field(None, max_length=100, description="Mandatory for official/admin roles")

    preferred_language: str = Field("en", max_length=10)
    preferred_channel: str = Field("web_portal", max_length=30)
    
    is_anonymous: Optional[bool] = Field(default=False, description="True if affected individual requested anonymous mode")
    
    consent: Optional[bool] = Field(None, description="Explicit agreement to consent notice")
    consent_given: Optional[bool] = Field(None, description="Backward compatible consent flag")
    consent_version: str = Field("1.0", max_length=20)

    @model_validator(mode="before")
    def validate_and_normalize(cls, values: dict):
        if not isinstance(values, dict):
            return values

        # 1. Resolve role from role or requested_category
        has_explicit_role = "role" in values and values["role"] is not None
        raw_role = values.get("role") or values.get("requested_category")
        if not raw_role:
            raise ValueError("Please select how you will use Mentaura (role is required).")
        clean_role = str(raw_role).strip().lower()
        resolved_role = ROLE_ALIASES.get(clean_role, clean_role)
        if resolved_role not in VALID_ROLES:
            raise ValueError(f"Invalid role selected. Must be one of: {', '.join(sorted(VALID_ROLES))}")
        values["role"] = resolved_role
        values["requested_category"] = clean_role

        # Anonymity is ONLY available for affected individuals and families
        affected_roles = {"victim", "witness", "affected_family"}
        if resolved_role in affected_roles:
            raw_anon = values.get("is_anonymous")
            if isinstance(raw_anon, str):
                values["is_anonymous"] = raw_anon.strip().lower() in ("true", "1", "yes")
            elif raw_anon is not None:
                values["is_anonymous"] = bool(raw_anon)
            else:
                values["is_anonymous"] = False
        else:
            values["is_anonymous"] = False

        # Validate full_name and email depending on anonymity choice
        if values.get("is_anonymous"):
            # Anonymous Mode: Real name and email are NOT collected or stored
            raw_fn = values.get("full_name")
            if not raw_fn or not str(raw_fn).strip():
                values["full_name"] = f"Anonymous {resolved_role.replace('_', ' ').title()}"
            else:
                # If passed, will be replaced with pseudonymous label during registration
                values["full_name"] = str(raw_fn).strip()

            raw_em = values.get("email")
            if raw_em and str(raw_em).strip():
                clean_em = str(raw_em).strip().lower()
                if "@" not in clean_em or "." not in clean_em:
                    raise ValueError("Please enter a valid delivery email format or leave blank.")
                values["email"] = clean_em
            else:
                values["email"] = None
        else:
            # Standard Non-Anonymous Mode: full_name and email are strictly mandatory
            raw_fn = values.get("full_name")
            if not raw_fn or len(str(raw_fn).strip()) < 2:
                raise ValueError("Full name is required (minimum 2 characters).")
            values["full_name"] = str(raw_fn).strip()

            raw_em = values.get("email")
            if not raw_em or "@" not in str(raw_em) or "." not in str(raw_em):
                raise ValueError("A valid email address is required.")
            values["email"] = str(raw_em).strip().lower()

        # 2. Validate official_id for official roles (strictly mandatory and verified against registry)
        raw_official_id = values.get("official_id")
        if resolved_role in OFFICIAL_ROLES:
            if not raw_official_id or not str(raw_official_id).strip():
                raise ValueError(
                    f"Official ID / Employee ID / Government ID is mandatory for role: {resolved_role.replace('_', ' ').title()}"
                )
            clean_id = str(raw_official_id).strip()
            try:
                from backend.app.services.official_id_service import verify_government_official_id
            except ImportError:
                from app.services.official_id_service import verify_government_official_id
            is_valid, err_msg, meta = verify_government_official_id(clean_id, resolved_role)
            if not is_valid:
                raise ValueError(err_msg)
            values["official_id"] = meta.get("official_id", clean_id.upper())
        else:
            values["official_id"] = str(raw_official_id).strip() if raw_official_id else None

        # 3. Validate password strength
        pwd = values.get("password") or ""
        if len(pwd) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", pwd):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", pwd):
            raise ValueError("Password must contain at least one digit.")

        # 4. Validate password confirmation if supplied
        confirm_pwd = values.get("confirm_password")
        if confirm_pwd is not None and pwd != confirm_pwd:
            raise ValueError("Passwords do not match. Please re-enter.")

        # 5. Resolve and validate consent
        consent_flag = values.get("consent")
        if consent_flag is None:
            consent_flag = values.get("consent_given")
        if not consent_flag:
            raise ValueError("Consent notice agreement is required to create a Mentaura account.")
        values["consent"] = True
        values["consent_given"] = True

        # 6. Normalize channel
        raw_channel = str(values.get("preferred_channel", "web_portal")).strip().lower()
        values["preferred_channel"] = CHANNEL_ALIASES.get(raw_channel, "web_portal")

        # 7. Normalize language
        raw_lang = str(values.get("preferred_language", "en")).strip().upper()
        values["preferred_language"] = raw_lang if raw_lang in VALID_LANGUAGES else "EN"

        return values


class VerifyEmailOtpRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="Email address or Anonymous ID")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        clean = v.strip()
        if not clean.isdigit() or len(clean) != 6:
            raise ValueError("Verification code must be a 6-digit number.")
        return clean


class VerifyEmailOtpResponse(BaseModel):
    message: str
    account_status: str
    token: Optional[str] = None
    redirect_url: Optional[str] = None
    user: Optional["UserOut"] = None


class ResendOtpRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    full_name: str
    email: str
    role: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_language: str
    preferred_channel: str
    requested_category: Optional[str] = None
    verified_role: Optional[str] = None
    account_status: str
    email_verified: bool = False
    is_anonymous: bool = False
    anonymous_id: Optional[str] = None
    masked_name: Optional[str] = None
    masked_email: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    @model_validator(mode="after")
    def populate_aliases(self):
        if not self.user_id:
            self.user_id = self.id
        if not self.role:
            self.role = self.verified_role or self.requested_category or "victim"
        if self.is_anonymous:
            if self.full_name and self.full_name.startswith("Anonymous"):
                self.masked_name = self.full_name
            else:
                from backend.app.utils.anonymity import mask_identifier
                self.masked_name = mask_identifier(self.full_name, self.id)
            self.masked_email = self.email
        return self


class MeResponse(BaseModel):
    user_id: str
    id: Optional[str] = None
    email: str
    full_name: str
    role: str
    verified_role: Optional[str] = None
    preferred_language: str
    preferred_channel: str
    account_status: str
    email_verified: bool
    is_anonymous: bool = False
    anonymous_id: Optional[str] = None
    masked_name: Optional[str] = None
    masked_email: Optional[str] = None


class SignupResponse(BaseModel):
    user_id: str
    email: str
    message: str
    anonymous_id: Optional[str] = None
    account_status: Optional[str] = None
    verified_role: Optional[str] = None
    redirect_url: Optional[str] = None
    user: Optional[UserOut] = None
    token: Optional[str] = None
    dev_otp: Optional[str] = None


class LoginResponse(BaseModel):
    message: str
    user: UserOut
    redirect_url: str
    token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str
    status: str
