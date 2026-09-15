import requests
import json

BASE_URL = "http://127.0.0.1:8000"

s = requests.Session()
login_res = s.post(f"{BASE_URL}/api/auth/login", json={
    "email": "victim@mentaura.example",
    "password": "Mentaura@2026"
})
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
data = login_res.json()
token = data.get("access_token") or s.cookies.get("access_token") or ""
headers = {"Content-Type": "application/json"}
if token:
    headers["Authorization"] = f"Bearer {token}"

history = []

def send(msg):
    print(f"\n--- USER: '{msg}' ---")
    res = s.post(
        f"{BASE_URL}/api/victim/chatbot/message",
        headers=headers,
        json={"message": msg, "language": "EN", "conversation_history": history}
    )
    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    reply = data.get("reply") or data.get("bot_reply")
    sev = data.get("severity_level")
    esc = data.get("escalation_contact")
    print(f"BOT [{sev}]: {reply}")
    print(f"Escalation Contact: {esc}")
    history.append({"role": "user", "content": msg})
    history.append({"role": "bot", "content": reply})
    return data

# Turn 1: Greeting
d1 = send("hi")
assert d1["escalation_contact"] is None, "Greeting should not have escalation contact!"

# Turn 2: Medium distress ("I'm not feeling well.")
d2 = send("I'm not feeling well.")
assert d2["escalation_contact"] is None, "Standard distress must NOT have unsolicited counsellor card!"
print(">> PASSED: 'I'm not feeling well.' did NOT attach counsellor card!")

# Turn 3: Follow-up reason ("due to my family")
d3 = send("due to my family")
assert d3["escalation_contact"] is None, "Follow-up distress must NOT have unsolicited counsellor card!"
print(">> PASSED: 'due to my family' did NOT attach counsellor card!")

# Turn 4: Explicit request for counsellor
d4 = send("Can I please talk to a counsellor?")
assert d4["escalation_contact"] is not None, "Explicit request MUST return escalation contact!"
print(f">> PASSED: Counsellor returned on request: {d4['escalation_contact']['officer_name']}")

# Turn 5: User declines counsellor ("I'm okay for now, let's continue talking")
d5 = send("I am okay for now, thank you. Let us continue talking.")
assert d5["escalation_contact"] is None, "Declined counsellor must NOT return escalation contact!"
print(">> PASSED: User declined -> bot continues talking without card!")

# Turn 6: Severe crisis ("I'm going to commit suicide")
d6 = send("I'm going to commit suicide")
assert d6["severity_level"] == "high", "Suicide mention must be HIGH severity!"
assert d6["escalation_contact"] is not None, "High severity must have counsellor contact!"
assert d6["alert_details"] is not None, "High severity must have emergency alert details!"
print(">> PASSED: High crisis escalated automatically with alert details!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
