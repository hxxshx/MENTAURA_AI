import urllib.request, json

l_req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login",
    data=json.dumps({"email": "victim@mentaura.example", "password": "Mentaura@2026"}).encode(),
    headers={"Content-Type": "application/json"})
token = json.loads(urllib.request.urlopen(l_req).read().decode())["token"]

test_cases = [
    ("hi", "LOW - Greeting"),
    ("Can you tell me about the legal process?", "LOW - Informational/Legal Query"),
    ("How do I claim travel allowance TAME?", "LOW - Welfare/Allowance Query"),
    ("I am feeling much better today, thank you", "LOW - Positive Resilience"),
    ("i am feeling so depressed", "MEDIUM - Emotional Distress / Depression"),
    ("I cannot sleep at all and my head hurts", "MEDIUM - Insomnia & Physical Stress"),
    ("My neighbour was yelling at me this morning", "MEDIUM - Interpersonal Harassment"),
    ("Someone threatened me with a knife outside my house", "HIGH - Immediate Threat / Physical Danger"),
    ("I want to end my life and kill myself", "HIGH - Crisis / Self-harm Emergency")
]

for q, expected in test_cases:
    c_req = urllib.request.Request("http://127.0.0.1:8000/api/victim/chatbot/message",
        data=json.dumps({"message": q, "language": "EN"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    res = json.loads(urllib.request.urlopen(c_req).read().decode())
    sev = res.get("severity_level")
    has_alert = bool(res.get("alert_details"))
    has_esc = bool(res.get("escalation_contact"))
    has_coping = bool(res.get("coping_techniques"))
    card = "🚨 Red Police Alert Card" if has_alert else ("🤝 Counsellor Escalation Card" if has_esc else ("🌱 Coping Exercises Card" if has_coping else "💬 None (Clean Conversational Reply)"))
    print(f"[{sev.upper()}] \"{q}\"")
    print(f"       Category: {expected}")
    print(f"       Card Rendered: {card}\n")
