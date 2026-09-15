"""
SQLAlchemy Data Model for Official Review Actions & Auditing.
Table: review_actions
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    target_type = Column(String(50), nullable=False, index=True) # support_pulse | support_request | case_milestone | intervention
    target_id = Column(String(50), nullable=False, index=True)
    
    action_type = Column(String(50), nullable=False, index=True) # mark_reviewed | assign | update_status | escalate
    status = Column(String(50), nullable=True) # reviewed | in_review | assigned | scheduled | completed
    
    notes = Column(Text, nullable=True) # Internal official notes (strictly excluded from victim-facing portal)
    performed_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationship to performing official
    user = relationship("User")
