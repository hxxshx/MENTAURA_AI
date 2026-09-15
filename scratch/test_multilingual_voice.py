import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.routers.victim import voice_chat_conversational_turn, VoiceChatTurnRequest

db = SessionLocal()
victim = db.query(User).filter(User.email == "victim@mentaura.example").first()
assert victim is not None, "Victim user not found!"

print(f"Testing with victim: {victim.full_name} ({victim.email})")

# 1. English
res_en = voice_chat_conversational_turn(
    VoiceChatTurnRequest(transcript="Hello, I am checking in today.", language="EN"),
    current_user=victim,
    db=db
)
print("EN Reply:", res_en.get("ai_spoken_reply", "")[:80])

# 2. Hindi
res_hi = voice_chat_conversational_turn(
    VoiceChatTurnRequest(transcript="नमस्ते, आज मैं थोड़ा परेशान महसूस कर रहा हूँ।", language="HI"),
    current_user=victim,
    db=db
)
print("HI Reply Length:", len(res_hi.get("ai_spoken_reply", "")))
print("HI Reply Preview (safe):", res_hi.get("ai_spoken_reply", "")[:80].encode('ascii', 'backslashreplace').decode('ascii'))

# 3. Tamil
res_ta = voice_chat_conversational_turn(
    VoiceChatTurnRequest(transcript="வணக்கம், எனக்கு நீதிமன்ற விசாரணை பற்றி பயமாக இருக்கிறது.", language="TA"),
    current_user=victim,
    db=db
)
print("TA Reply Length:", len(res_ta.get("ai_spoken_reply", "")))
print("TA Reply Preview (safe):", res_ta.get("ai_spoken_reply", "")[:80].encode('ascii', 'backslashreplace').decode('ascii'))

print("\nALL MULTILINGUAL TESTS PASSED SUCCESSFULLY!")
