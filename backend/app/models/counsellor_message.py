"""
Data model for Direct 1-to-1 Messages between Victims and Assigned Counsellors.
Supports real-time trauma-informed dialogue, status notifications, and Section 15A confidentiality.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class CounsellorMessage(Base):
    __tablename__ = "counsellor_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    conversation_id = Column(String(100), nullable=False, index=True)
    
    # Victim details
    victim_id = Column(String(36), nullable=False, index=True)
    victim_name = Column(String(120), nullable=False)
    
    # Counsellor details
    counsellor_id = Column(String(36), nullable=False, index=True)
    counsellor_name = Column(String(120), nullable=False)
    
    # Message sender
    sender_id = Column(String(36), nullable=False, index=True)
    sender_name = Column(String(120), nullable=False)
    sender_role = Column(String(30), nullable=False)  # "victim" or "counsellor"
    
    # Content & Status
    message_text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "victim_id": self.victim_id,
            "victim_name": self.victim_name,
            "counsellor_id": self.counsellor_id,
            "counsellor_name": self.counsellor_name,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "sender_role": self.sender_role,
            "message_text": self.message_text,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
