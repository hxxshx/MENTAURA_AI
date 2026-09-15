"""
SQLAlchemy Data Models for Support Pulse submissions, responses, and voice jobs.
Tables:
- support_pulses
- support_pulse_responses
- voice_processing_jobs
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)


class SupportPulse(Base):
    __tablename__ = "support_pulses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    authenticated_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(50), nullable=True, index=True)
    
    processing_mode = Column(String(30), nullable=False, default="ai_assisted") # ai_assisted | human_review_only
    consent_version = Column(String(20), nullable=False, default="1.0")
    consent_given_at = Column(DateTime, default=utc_now, nullable=False)
    
    channel = Column(String(30), nullable=False, default="web")
    language = Column(String(10), nullable=False, default="EN")
    
    wellbeing_state = Column(String(50), nullable=True)
    text_response = Column(Text, nullable=True) # Sanitized narrative text
    
    audio_storage_reference = Column(String(255), nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)
    audio_mime_type = Column(String(80), nullable=True)
    audio_file_size_bytes = Column(Integer, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, default=utc_now, nullable=False)
    completion_status = Column(String(30), nullable=False, default="submitted") # submitted | abandoned
    human_review_status = Column(String(30), nullable=False, default="pending") # pending | reviewed | escalated
    
    priority_review = Column(Boolean, default=False, nullable=False)
    risk_level = Column(String(20), nullable=True, default="low") # low | medium | high
    risk_score = Column(Integer, nullable=True, default=0)
    
    # Dynamic Distress & Emotion AI Fields (SIH 26094)
    dynamic_distress_score = Column(Integer, nullable=True, default=0)
    acoustic_score = Column(Integer, nullable=True, default=0)
    sentiment_score = Column(Integer, nullable=True, default=0)
    escalation_predicted = Column(Boolean, default=False, nullable=False)
    xai_explanation = Column(Text, nullable=True)
    interaction_channel = Column(String(40), default="web_form", nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
    responses = relationship("SupportPulseResponse", back_populates="pulse", cascade="all, delete-orphan")
    voice_job = relationship("VoiceProcessingJob", back_populates="pulse", uselist=False, cascade="all, delete-orphan")


class SupportPulseResponse(Base):
    __tablename__ = "support_pulse_responses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    support_pulse_id = Column(String(36), ForeignKey("support_pulses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    phase = Column(String(30), nullable=False) # pulse1 | pulse2 | pulse3 | safety | followup
    question_key = Column(String(80), nullable=False)
    response_value = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)

    pulse = relationship("SupportPulse", back_populates="responses")


class VoiceProcessingJob(Base):
    __tablename__ = "voice_processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    support_pulse_id = Column(String(36), ForeignKey("support_pulses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String(30), nullable=False, default="queued") # queued | processing | completed | failed | not_requested
    transcription_status = Column(String(30), nullable=False, default="queued") # queued | processing | completed | failed | not_requested
    analysis_status = Column(String(30), nullable=False, default="queued") # queued | processing | completed | failed | not_requested
    
    model_version = Column(String(50), nullable=True, default="mentaura-nlp-v1.0")
    error_message = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    pulse = relationship("SupportPulse", back_populates="voice_job")
