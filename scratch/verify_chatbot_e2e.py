import requests

session = requests.Session()
login_res = session.post("http://127.0.0.1:8000/api/auth/login", json={
    "email": "victim@mentaura.example",
    "password": "Mentaura@2026"
})
print("Login Status:", login_res.status_code)
assert login_res.status_code == 200, f"Login failed: {login_res.text}"

test_cases = [
    ("EN", "I felt so sad today because no one visited me"),
    ("EN", "Can you tell me about the legal process?"),
    ("EN", "My neighbour was yelling at me this morning"),
    ("EN", "Someone threatened me with a knife outside my house"),
    ("EN", "I have court hearing tomorrow and I am scared"),
    ("EN", "How do I claim travel allowance TAME?"),
    ("EN", "I cannot sleep at all, my head hurts and I feel exhausted"),
    ("EN", "I am feeling much better today, thank you"),
    ("HI", "मुझे अदालत जाने से बहुत डर लग रहा है"),
    ("TA", "எனக்கு தூக்கம் வரவில்லை, மிகவும் பயமாக இருக்கிறது")
]

replies_seen = set()

for i, (lang, prompt) in enumerate(test_cases, 1):
    res = session.post("http://127.0.0.1:8000/api/victim/chatbot/message", json={
        "message": prompt,
        "language": lang,
        "conversation_history": []
    })
    assert res.status_code == 200, f"Request {i} failed: {res.text}"
    data = res.json()
    reply = data.get("bot_response") or data.get("reply")
    severity = data.get("severity_level")
    score = data.get("dynamic_distress_indicator")
    chips = data.get("suggested_actions", [])
    has_coping = bool(data.get("coping_techniques"))
    has_escalation = bool(data.get("escalation_contact"))
    has_alert = bool(data.get("alert_details"))

    print(f"\n--- TEST {i}: [{lang}] \"{prompt}\" ---")
    print(f"Severity: {severity.upper()} | Score: {score}/100 | Tier Payload: (Coping: {has_coping}, Escalate: {has_escalation}, Alert: {has_alert})")
    print(f"Reply: {reply[:120]}...")
    print(f"Chips: {chips}")

    assert reply not in replies_seen, f"Duplicate reply detected on test {i}!"
    replies_seen.add(reply)

print("\n" + "=" * 65)
print("SUCCESS: ALL 10 TESTS PASSED! ZERO DUPLICATES! 100% WORKING!")
print("=" * 65)
