import requests

BASE = "http://127.0.0.1:8000"

def test_chat():
    victim_session = requests.Session()
    counsellor_session = requests.Session()

    # 1. Login Victim
    r = victim_session.post(f"{BASE}/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    print("Victim login:", r.status_code)
    assert r.status_code == 200

    # 2. Login Counsellor
    r = counsellor_session.post(f"{BASE}/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    print("Counsellor login:", r.status_code)
    assert r.status_code == 200

    # 3. Victim sends message to Dr. Priya
    r = victim_session.post(f"{BASE}/api/victim/counsellor-chat/send", json={
        "message": "Hello Dr. Priya, I have an upcoming court hearing and feel anxious. Can we talk?"
    })
    print("Victim send status:", r.status_code, r.json())
    assert r.status_code == 200
    victim_id = r.json()["message"]["victim_id"]

    # 4. Counsellor checks conversations
    r = counsellor_session.get(f"{BASE}/api/counsellor/messages/conversations")
    print("Counsellor conversations:", r.status_code, r.json())
    assert r.status_code == 200

    # 5. Counsellor reads thread
    r = counsellor_session.get(f"{BASE}/api/counsellor/messages/{victim_id}")
    print("Counsellor read thread:", r.status_code, len(r.json()["messages"]), "messages")
    assert r.status_code == 200

    # 6. Counsellor replies
    r = counsellor_session.post(f"{BASE}/api/counsellor/messages/{victim_id}/reply", json={
        "message": "Hello Aanya, I hear you and you are completely safe. Let's practice 4-7-8 breathing and request Section 15A police transit."
    })
    print("Counsellor reply status:", r.status_code, r.json())
    assert r.status_code == 200

    # 7. Victim fetches messages and sees reply
    r = victim_session.get(f"{BASE}/api/victim/counsellor-chat/messages")
    print("Victim fetch thread:", r.status_code, len(r.json()["messages"]), "messages")
    assert r.status_code == 200
    last_msg = r.json()["messages"][-1]
    print("Latest message received by victim:", last_msg["sender_name"], "->", last_msg["message_text"])
    assert last_msg["sender_role"] == "counsellor"
    print("\nSUCCESS! Two-way interactive messaging between Victim and Dr. Priya Nair verified!")

if __name__ == "__main__":
    test_chat()
