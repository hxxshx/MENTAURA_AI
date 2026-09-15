"""
Seed two test booking sessions for counsellor workspace:
1. Direct Messaging session (format: 'direct_message', status: 'scheduled')
2. Video Call session (format: 'video', status: 'scheduled')
Plus conversation messages so testing is immediate.
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.support_request import SupportRequest
from backend.app.models.counsellor_message import CounsellorMessage

def seed_test_sessions():
    db = SessionLocal()
    try:
        # Find victim and counsellor
        victim = db.query(User).filter(User.email == 'victim@mentaura.example').first()
        counsellor = db.query(User).filter(User.email == 'counsellor@mentaura.example').first()
        
        if not victim or not counsellor:
            print("Error: Could not find victim or counsellor user records.")
            return

        now = datetime.now(timezone.utc)

        # 1. Booking Session 1: Direct Messaging Session
        session1_id = str(uuid.uuid4())
        session1 = SupportRequest(
            id=session1_id,
            user_id=victim.id,
            case_id="CASE-2026-9041",
            support_type="counselling",
            status="scheduled",
            session_format="direct_message",
            session_metadata=json.dumps({
                "format": "direct_message",
                "mode": "direct_message",
                "notes": "Direct confidential chat session with Dr. Priya Nair under Section 15A.",
                "pass_code": f"OSC-TN-{session1_id[:6].upper()}"
            }),
            submitted_at=now - timedelta(minutes=15),
            last_updated_at=now - timedelta(minutes=5),
            assigned_role="Psychological Counsellor",
            assigned_user_reference="Dr. Priya Nair (Lead Counsellor)",
            appointment_at=now + timedelta(hours=1),
            next_step="Direct Messaging Care Session active with Dr. Priya Nair"
        )
        db.add(session1)

        # 2. Booking Session 2: Encrypted Video Call Consultation
        session2_id = str(uuid.uuid4())
        session2 = SupportRequest(
            id=session2_id,
            user_id=victim.id,
            case_id="CASE-2026-9041",
            support_type="counselling",
            status="scheduled",
            session_format="video",
            session_metadata=json.dumps({
                "format": "video",
                "mode": "video",
                "room_id": f"mentaura-room-{session2_id[:8]}",
                "pass_code": f"OSC-TN-{session2_id[:6].upper()}",
                "notes": "Encrypted WebRTC video consultation enclave scheduled by Dr. Priya Nair."
            }),
            submitted_at=now - timedelta(minutes=10),
            last_updated_at=now - timedelta(minutes=2),
            assigned_role="Psychological Counsellor",
            assigned_user_reference="Dr. Priya Nair (Lead Counsellor)",
            appointment_at=now + timedelta(hours=3),
            next_step="Encrypted Video Consultation scheduled with Dr. Priya Nair"
        )
        db.add(session2)

        # Seed sample chat messages between victim and counsellor
        convo_id = f"convo_{victim.id}_{counsellor.id}"
        msg1 = CounsellorMessage(
            id=str(uuid.uuid4()),
            conversation_id=convo_id,
            victim_id=victim.id,
            victim_name=victim.full_name or "Aanya Sharma",
            counsellor_id=counsellor.id,
            counsellor_name=counsellor.full_name or "Dr. Priya Nair",
            sender_id=victim.id,
            sender_name=victim.full_name or "Aanya Sharma",
            sender_role="victim",
            message_text="Hello Dr. Priya, I requested counselling support because I am feeling anxious about tomorrow's court deposition.",
            created_at=now - timedelta(minutes=20)
        )
        db.add(msg1)

        msg2 = CounsellorMessage(
            id=str(uuid.uuid4()),
            conversation_id=convo_id,
            victim_id=victim.id,
            victim_name=victim.full_name or "Aanya Sharma",
            counsellor_id=counsellor.id,
            counsellor_name=counsellor.full_name or "Dr. Priya Nair",
            sender_id=counsellor.id,
            sender_name="Dr. Priya Nair",
            sender_role="counsellor",
            message_text="Hello Aanya. I hear you and you are completely safe. We have Section 15A protection active and I will be guiding you through today's care session.",
            created_at=now - timedelta(minutes=18)
        )
        db.add(msg2)

        db.commit()

        print("SUCCESSFULLY SEEDED SESSIONS:")
        print(f"1. Direct Messaging Session: ID={session1_id}, Format={session1.session_format}, Status={session1.status}")
        print(f"2. Video Call Session:       ID={session2_id}, Format={session2.session_format}, Status={session2.status}")
        print("Seeded chat messages into the victim-counsellor thread.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_test_sessions()
