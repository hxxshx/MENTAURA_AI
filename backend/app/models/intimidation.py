"""
SQLAlchemy Data Model for Section 15A Witness Protection & Threat/Intimidation Reports.
Under Scheduled Castes & Scheduled Tribes (Prevention of Atrocities) Act, 1989.
Table: intimidation_reports
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


class IntimidationReport(Base):
    __tablename__ = "intimidation_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(50), nullable=True, index=True)

    incident_type = Column(String(80), nullable=False)  # direct_threat, stalking, social_boycott, bribe_pressure, property_damage
    threat_source = Column(String(120), nullable=True)  # accused_associates, village_members, unknown
    incident_location = Column(String(255), nullable=True)
    incident_time = Column(DateTime, nullable=True)
    
    narrative = Column(Text, nullable=False)
    evidence_file_reference = Column(String(255), nullable=True)
    
    urgency_level = Column(String(30), nullable=False, default="high")  # emergency | high | moderate
    status = Column(String(40), nullable=False, default="dispatched_to_dsp")  # dispatched_to_dsp | under_investigation | protection_provided | reviewed
    
    protection_officer_reference = Column(String(100), nullable=True)
    protection_measures_taken = Column(Text, nullable=True)
    
    is_sos_panic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
