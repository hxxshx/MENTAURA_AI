import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.notification import Notification
from backend.app.models.support_request import SupportRequest
from backend.app.models.pulse import SupportPulse
from backend.app.routers.victim import voice_chat_conversational_turn, voice_chat_elevate_to_counsellor, VoiceChatTurnRequest, VoiceChatElevateRequest

db = SessionLocal()
victim = db.query(User).filter(User.email == "victim@mentaura.example").first()
assert victim is not None, "Victim user not found!"

print(f"Testing with victim: {victim.full_name} ({victim.email})")

# 1. Test Low Distress
req_low = VoiceChatTurnRequest(
    transcript="I am feeling calm and holding steady today, just wanted to check in.",
    language="EN",
    pitch_tension_hz=165.0,
    jitter_percent=1.1,
    pause_ratio=0.18
)
res_low = voice_chat_conversational_turn(req_low, current_user=victim, db=db)
print("\n[LOW TEST RESULT]:")
print(f"Classification: {res_low['classification']}")
print(f"Score: {res_low['distress_score']}")
print(f"Spoken Reply: {res_low['ai_spoken_reply']}")
print(f"Actions: {[a['title'] for a in res_low['suggested_actions']]}")
assert res_low['classification'] == 'low'
assert len(res_low['suggested_actions']) >= 2

# 2. Test Medium Distress
req_med = VoiceChatTurnRequest(
    transcript="I am feeling very anxious, stressed, and overwhelmed about my upcoming court date next week.",
    language="EN",
    pitch_tension_hz=195.0,
    jitter_percent=1.7,
    pause_ratio=0.32
)
res_med = voice_chat_conversational_turn(req_med, current_user=victim, db=db)
print("\n[MEDIUM TEST RESULT]:")
print(f"Classification: {res_med['classification']}")
print(f"Score: {res_med['distress_score']}")
print(f"Spoken Reply: {res_med['ai_spoken_reply']}")
print(f"Elevation Prompt: {res_med['elevation_prompt']}")
assert res_med['classification'] == 'medium'
assert res_med['elevation_prompt'] is not None

# 3. Test High Distress
req_high = VoiceChatTurnRequest(
    transcript="I am terrified, someone threatened me outside and I can't take this anymore, please help me!",
    language="EN",
    pitch_tension_hz=225.0,
    jitter_percent=2.4,
    pause_ratio=0.45
)
notif_count_before = db.query(Notification).count()
res_high = voice_chat_conversational_turn(req_high, current_user=victim, db=db)
notif_count_after = db.query(Notification).count()
print("\n[HIGH TEST RESULT]:")
print(f"Classification: {res_high['classification']}")
print(f"Score: {res_high['distress_score']}")
print(f"Spoken Reply: {res_high['ai_spoken_reply']}")
print(f"Counsellor Notified: {res_high['counsellor_notified']}")
print(f"Notifications Before: {notif_count_before}, After: {notif_count_after}")
assert res_high['classification'] == 'high'
assert res_high['counsellor_notified'] is True
assert notif_count_after > notif_count_before

# 4. Test Elevation from Medium
req_elev = VoiceChatElevateRequest(
    transcript=req_med.transcript,
    notes="Victim accepted counsellor elevation from voice checkin"
)
res_elev = voice_chat_elevate_to_counsellor(req_elev, current_user=victim, db=db)
print("\n[ELEVATE TEST RESULT]:")
print(f"Status: {res_elev['status']}")
print(f"Message: {res_elev['message']}")
assert res_elev['status'] == 'elevated'

print("\nALL VOICE TESTS PASSED SUCCESSFULLY!")
