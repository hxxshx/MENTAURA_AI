import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.routers.victim import voice_chat_conversational_turn, VoiceChatTurnRequest

db = SessionLocal()
victim = db.query(User).filter(User.email == "victim@mentaura.example").first()
assert victim is not None, "Victim not found!"

for greeting in ["Hello", "Hello.", "Hi there!", "Namaste", "Good morning"]:
    req = VoiceChatTurnRequest(
        transcript=greeting,
        language="EN",
        pitch_tension_hz=175.0,
        jitter_percent=1.2,
        pause_ratio=0.22
    )
    res = voice_chat_conversational_turn(req, current_user=victim, db=db)
    print(f"\nUser: '{greeting}'")
    print(f"Classification: {res['classification']}, Score: {res['distress_score']}")
    print(f"Elevation Prompt: {res['elevation_prompt']}")
    print(f"AI Reply: {res['ai_spoken_reply']}")
    assert res['classification'] == 'low', f"Greeting '{greeting}' should be low distress!"
    assert res['elevation_prompt'] is None, f"Greeting '{greeting}' should not have elevation prompt!"

print("\nALL GREETING TESTS PASSED PERFECTLY!")
