"""
SQLAlchemy Data Models for Mentaura Platform.
Tables:
- users
- consent_records
- verification_requests
- user_sessions
- audit_logs
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(30), nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    preferred_language = Column(String(10), default="EN", nullable=False)
    preferred_channel = Column(String(30), default="web", nullable=False)
    
    role = Column(String(50), nullable=True, index=True)
    official_id = Column(String(100), nullable=True)
    
    requested_category = Column(String(50), nullable=False)
    verified_role = Column(String(50), nullable=False, default="pending_verification", index=True)
    account_status = Column(String(30), nullable=False, default="pending_verification", index=True)
    
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    
    is_anonymous = Column(Boolean, default=False, nullable=False)
    anonymous_id = Column(String(50), nullable=True, index=True)
    
    consent_version = Column(String(20), nullable=False, default="1.0")
    consent_given_at = Column(DateTime, default=utc_now, nullable=False)
    
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    consents = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    verification_requests = relationship("VerificationRequest", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    email_otps = relationship("EmailOTP", back_populates="user", cascade="all, delete-orphan")


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    otp_hash = Column(String(64), nullable=False)
    delivery_email_hash = Column(String(64), nullable=True, index=True)
    otp_type = Column(String(50), nullable=False, default="email_verification")
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="email_otps")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    consent_type = Column(String(80), nullable=False, default="account_creation_and_support_processing")
    consent_version = Column(String(20), nullable=False, default="1.0")
    notice_version = Column(String(20), nullable=False, default="1.0")
    consent_given = Column(Boolean, nullable=False, default=True)
    
    given_at = Column(DateTime, default=utc_now, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="consents")


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    requested_role = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="pending", index=True)  # pending, approved, rejected
    
    submitted_at = Column(DateTime, default=utc_now, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="verification_requests")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(128), unique=True, index=True, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    action = Column(String(80), nullable=False, index=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
