import requests

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    # 1. Login
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    token = token_data.get("token") or token_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("1. Login successful")

    # 2. Test High Crisis: 'I am going to commit suicide'
    history = []
    crisis_res = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json={
        "message": "I feel completely hopeless and I am going to commit suicide",
        "language": "EN",
        "conversation_history": history
    }, headers=headers)
    assert crisis_res.status_code == 200
    c_data = crisis_res.json()
    print(f"2. Crisis Turn -> Score: {c_data['dynamic_distress_indicator']}, Severity: {c_data['severity_level']}")
    assert c_data['severity_level'] == 'high'
    assert c_data['dynamic_distress_indicator'] >= 80

    # Record into history
    history.append({"role": "user", "content": "I am going to commit suicide", "distress_score": 85})
    history.append({"role": "bot", "content": c_data['bot_reply']})

    # 3. Test Follow-up 'hi' (Cumulative Distress & Context-Aware Greeting Follow-up)
    followup_res = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json={
        "message": "hi",
        "language": "EN",
        "conversation_history": history
    }, headers=headers)
    assert followup_res.status_code == 200
    f_data = followup_res.json()
    print(f"3. Followup 'hi' Turn -> Score: {f_data['dynamic_distress_indicator']}, Severity: {f_data['severity_level']}")
    print(f"   Bot Reply: {f_data['bot_reply']}")
    assert f_data['severity_level'] == 'high', f"Expected high severity, got {f_data['severity_level']}"
    assert f_data['dynamic_distress_indicator'] >= 80, f"Expected score >= 80, got {f_data['dynamic_distress_indicator']}"

    # 4. Test Medium Distress Referral Offer
    med_res = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json={
        "message": "I am not feeling well due to my family and court pressure",
        "language": "EN",
        "conversation_history": []
    }, headers=headers)
    assert med_res.status_code == 200
    m_data = med_res.json()
    print(f"4. Medium Turn -> Severity: {m_data['severity_level']}, Has Offer: {m_data['elevation_prompt'] is not None}")
    assert m_data['severity_level'] == 'medium'
    assert m_data['escalation_contact'] is not None

    # 5. Test History Endpoint (Audio 1)
    hist_res = requests.get(f"{BASE_URL}/api/victim/chatbot/history", headers=headers)
    assert hist_res.status_code == 200
    h_data = hist_res.json()
    print(f"5. History Endpoint -> Total records returned: {h_data['count']}")
    assert h_data['count'] > 0

    # 6. Test Proactive Check-In Endpoint (30s Monitoring - Audio 4)
    proactive_res = requests.post(f"{BASE_URL}/api/victim/chatbot/proactive-checkin", json={
        "language": "EN",
        "conversation_history": history
    }, headers=headers)
    assert proactive_res.status_code == 200
    p_data = proactive_res.json()
    print(f"6. Proactive Check-In (30s) -> Mode: {p_data['mode']}")
    print(f"   Message: {p_data['proactive_message']}")
    assert p_data['is_proactive'] is True

    print("\n*** ALL 5 BACKEND ENHANCEMENTS PASSED! ***")

if __name__ == "__main__":
    run_tests()
