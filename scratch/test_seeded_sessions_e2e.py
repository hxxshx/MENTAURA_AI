"""
End-to-end verification test for the 2 seeded sessions:
1. Direct Messaging Session
2. Encrypted Video Call Session
"""
from fastapi.testclient import TestClient
from backend.app.main import app

def test_counsellor_sessions_and_messaging():
    client = TestClient(app)
    
    # 1. Login as Counsellor
    login_res = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    cookies = login_res.cookies
    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 2. Check Support Requests Queue
    req_res = client.get("/api/counsellor/support-requests?include_inactive=false", cookies=cookies, headers=headers)
    assert req_res.status_code == 200, f"Failed to get requests: {req_res.text}"
    data = req_res.json()
    requests = data.get("support_requests", [])
    assert len(requests) >= 2, "Expected at least 2 support requests"

    # Find the seeded sessions
    direct_session = next((r for r in requests if r.get("session_format") == "direct_message"), None)
    video_session = next((r for r in requests if r.get("session_format") == "video"), None)

    assert direct_session is not None, "Direct messaging session not found in queue"
    assert video_session is not None, "Video call session not found in queue"

    print("FOUND SESSIONS:")
    print(f"  [Direct Message Session] ID: {direct_session['id']} | Status: {direct_session['status']} | Format: {direct_session['session_format']}")
    print(f"  [Video Call Session]     ID: {video_session['id']} | Status: {video_session['status']} | Format: {video_session['session_format']}")

    # 3. Test Direct Messaging Thread Retrieval
    victim_user_id = direct_session.get("user_id") or "74011797-0be6-434f-8bf8-0b22999c3af0"
    msg_res = client.get(f"/api/counsellor/messages/{victim_user_id}", cookies=cookies, headers=headers)
    assert msg_res.status_code == 200, f"Failed to load messages: {msg_res.text}"
    messages = msg_res.json().get("messages", [])
    print(f"Direct Messaging Thread: {len(messages)} messages found.")
    for m in messages[-2:]:
        print(f"  - [{m['sender_role'].upper()}] {m['sender_name']}: {m['message_text']}")

    # 4. Test Counsellor Replying in Direct Messaging
    reply_res = client.post(
        f"/api/counsellor/messages/{victim_user_id}/reply",
        json={"message_text": "I am reviewing your deposition anxiety notes. We will proceed with calm grounding techniques."},
        cookies=cookies,
        headers=headers
    )
    assert reply_res.status_code == 200, f"Failed to send reply: {reply_res.text}"
    print("Counsellor reply sent successfully.")

    # 5. Test Video Consultation Enclave Action
    video_id = video_session["id"]
    action_res = client.post(
        f"/api/counsellor/sessions/{video_id}/action",
        json={"action": "start_video", "notes": "Dr. Priya Nair entered WebRTC consultation enclave."},
        cookies=cookies,
        headers=headers
    )
    assert action_res.status_code == 200, f"Failed to start video session: {action_res.text}"
    print(f"Video session started successfully: {action_res.json()}")

    print("\nALL VERIFICATION TESTS PASSED (100%)!")

if __name__ == "__main__":
    test_counsellor_sessions_and_messaging()
