"""
SQLAlchemy Data Model for Victim Support Requests in Mentaura.
Table: support_requests
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class SupportRequest(Base):
    __tablename__ = "support_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(50), nullable=True, index=True)
    support_type = Column(String(100), nullable=False)  # counselling, legal_aid, protection, medical, compensation, rehabilitation, etc.
    source_pulse_id = Column(String(36), ForeignKey("support_pulses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Status options: requested | under_review | assigned | scheduled | completed | follow_up_required | closed | unable_to_proceed
    status = Column(String(40), nullable=False, default="under_review")
    submitted_at = Column(DateTime, default=utc_now, nullable=False)
    last_updated_at = Column(DateTime, nullable=True)
    next_step = Column(String(255), nullable=True, default="Awaiting authorised review")
    
    assigned_role = Column(String(80), nullable=True)
    assigned_user_reference = Column(String(80), nullable=True)
    appointment_at = Column(DateTime, nullable=True)
    completion_at = Column(DateTime, nullable=True)
    session_format = Column(String(50), nullable=True, default="telephonic")  # telephonic | video | in_person | emergency_crisis
    session_metadata = Column(Text, nullable=True)  # JSON metadata: room_id, pass_code, call_status, vitals, etc.
    
    visible_to_victim = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
    source_pulse = relationship("SupportPulse")
