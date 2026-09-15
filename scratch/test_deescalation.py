import os
import sys
from pathlib import Path

# Ensure paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.routers.victim import conversational_chatbot_checkin, ChatbotMessageRequest

db = SessionLocal()
try:
    u = db.query(User).filter(User.verified_role == 'victim').first()
    if not u:
        u = db.query(User).first()
    print(f"Testing User: {u.full_name} ({u.verified_role})")

    history = []

    # Turn 1: Threat
    r1 = conversational_chatbot_checkin(
        ChatbotMessageRequest(message="someone threatened me and I am terrified", conversation_history=history),
        u, db
    )
    print(f"Turn 1 (Threat)        -> Severity: {r1.get('severity_level'):<6} | Alert: {bool(r1.get('alert_details'))}")
    history.append({'role': 'user', 'content': 'someone threatened me and I am terrified', 'distress_score': 85})
    history.append({'role': 'bot', 'content': r1.get('reply')})

    # Turn 2: im fine now
    r2 = conversational_chatbot_checkin(
        ChatbotMessageRequest(message="im fine now", conversation_history=history),
        u, db
    )
    print(f"Turn 2 (im fine now)   -> Severity: {r2.get('severity_level'):<6} | Alert: {bool(r2.get('alert_details'))}")
    history.append({'role': 'user', 'content': 'im fine now', 'distress_score': 25})
    history.append({'role': 'bot', 'content': r2.get('reply')})

    # Turn 3: suggest a song
    r3 = conversational_chatbot_checkin(
        ChatbotMessageRequest(message="suggest a song to listen in this situation", conversation_history=history),
        u, db
    )
    print(f"Turn 3 (suggest a song)-> Severity: {r3.get('severity_level'):<6} | Alert: {bool(r3.get('alert_details'))}")
    print(f"         Reply: {r3.get('reply')[:80]}...")
    history.append({'role': 'user', 'content': 'suggest a song to listen in this situation', 'distress_score': 20})
    history.append({'role': 'bot', 'content': r3.get('reply')})

    # Turn 4: safe place
    r4 = conversational_chatbot_checkin(
        ChatbotMessageRequest(message="yes i am in a safe place", conversation_history=history),
        u, db
    )
    print(f"Turn 4 (safe place)    -> Severity: {r4.get('severity_level'):<6} | Alert: {bool(r4.get('alert_details'))}")
    history.append({'role': 'user', 'content': 'yes i am in a safe place', 'distress_score': 20})
    history.append({'role': 'bot', 'content': r4.get('reply')})

    # Turn 5: yes
    r5 = conversational_chatbot_checkin(
        ChatbotMessageRequest(message="yes", conversation_history=history),
        u, db
    )
    print(f"Turn 5 (yes)           -> Severity: {r5.get('severity_level'):<6} | Alert: {bool(r5.get('alert_details'))}")

finally:
    db.close()
