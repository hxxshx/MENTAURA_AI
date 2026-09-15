"""
SQLAlchemy Data Model for In-App Notifications & Alerts.
Table: notifications
"""
import uuid
import json
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


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification type: 'high_risk_pulse', 'case_escalated', 'system_alert'
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    
    # Optional JSON metadata (e.g. pulse_id, masked_identifier, case_id, escalation_level)
    meta_data = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")

    def to_dict(self):
        meta = {}
        if self.meta_data:
            try:
                meta = json.loads(self.meta_data)
            except Exception:
                meta = {}
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": meta
        }
