"""Tests for the FastAPI REST + WebSocket endpoints."""
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def main():
    print("\n🧪 API Test Suite\n")

    section("1. ROOT + HEALTH")
    r = client.get("/")
    print(f"GET / → {r.status_code}")
    print(f"  {r.json()}\n")

    r = client.get("/api/health")
    print(f"GET /api/health → {r.status_code}")
    print(f"  {r.json()}\n")

    section("2. CHAT — SAFE")
    r = client.post("/api/chat", json={
        "victim_id": "API_TEST_1",
        "session_id": "S1",
        "message": "I feel safe and supported today.",
    })
    print(f"POST /api/chat → {r.status_code}")
    data = r.json()
    print(f"  reply: {data['reply'][:80]}...")
    print(f"  distress: {data['distress']['distress_score']} ({data['distress']['risk_level']})")
    print(f"  turn: {data['turn_number']}\n")

    section("3. CHAT — CRITICAL")
    r = client.post("/api/chat", json={
        "victim_id": "API_TEST_2",
        "session_id": "S2",
        "message": "I want to die, there's no point anymore.",
    })
    print(f"POST /api/chat → {r.status_code}")
    data = r.json()
    print(f"  reply: {data['reply'][:80]}...")
    print(f"  distress: {data['distress']['distress_score']} ({data['distress']['risk_level']})")
    print(f"  themes: {data['text_analysis']['critical_themes']}")
    print(f"  intervention: {data['intervention']['recommended_interventions']}\n")

    section("4. HINDI CRITICAL")
    r = client.post("/api/chat", json={
        "victim_id": "API_TEST_3",
        "session_id": "S3",
        "message": "मैं मरना चाहता हूँ।",
    })
    print(f"POST /api/chat (Hindi) → {r.status_code}")
    data = r.json()
    print(f"  distress: {data['distress']['distress_score']} ({data['distress']['risk_level']})")
    print(f"  themes: {data['text_analysis']['critical_themes']}\n")

    section("5. VOICE TRANSCRIPT")
    r = client.post("/api/voice-transcript", json={
        "victim_id": "API_TEST_4",
        "session_id": "S4",
        "message": "I am scared for my life, they threatened me.",
    })
    print(f"POST /api/voice-transcript → {r.status_code}")
    data = r.json()
    print(f"  distress: {data['distress']['distress_score']} ({data['distress']['risk_level']})")
    print(f"  themes: {data['text_analysis']['critical_themes']}\n")

    section("6. DISTRESS SCORE (pulse only)")
    r = client.post("/api/distress-score", json={
        "victim_id": "API_TEST_5",
        "wellbeing_state": "very_unsafe",
        "affecting_factors": ["suicidal_thoughts", "threats"],
        "case_stage": "court",
    })
    print(f"POST /api/distress-score → {r.status_code}")
    data = r.json()
    print(f"  score: {data['distress_score']}")
    print(f"  risk: {data['risk_level']}")
    print(f"  reason codes: {data['reason_codes']}\n")

    section("7. VICTIM HISTORY")
    for i in range(1, 4):
        client.post("/api/chat", json={
            "victim_id": "API_TEST_HISTORY",
            "session_id": "SH",
            "message": f"Turn {i} message — I feel unsafe.",
        })

    r = client.get("/api/victim/API_TEST_HISTORY/history")
    print(f"GET /api/victim/.../history → {r.status_code}")
    print(f"  {r.json()}\n")

    section("8. WEBSOCKET")
    with client.websocket_connect("/ws/chat/WS_TEST") as ws:
        ws.send_json({
            "session_id": "WSS",
            "message": "I'm scared and alone.",
        })
        data = ws.receive_json()
        print(f"WS reply: {data['reply'][:80]}...")
        print(f"WS distress: {data['distress']['score']} ({data['distress']['risk_level']})")
        print(f"WS themes: {data['text_analysis']['critical_themes']}\n")

    print(f"\n{'━' * 70}")
    print("  ✅ API test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()