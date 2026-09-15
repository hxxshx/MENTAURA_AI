# -*- coding: utf-8 -*-
import requests

BASE_URL = "http://127.0.0.1:8000"

# 1. Login as victim to get auth token
login_data = {
    "username": "victim.user@mentaura.gov.in",
    "password": "Password123!"
}

login_res = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
if login_res.status_code != 200:
    # Try alternate test victim or query DB
    print(f"Login failed ({login_res.status_code}): {login_res.text}")
    # Let's inspect users in DB
    from backend.app.database import SessionLocal
    from backend.app.models.user import User
    db = SessionLocal()
    victim = db.query(User).filter(User.verified_role.in_(["victim", "witness"])).first()
    print("Victim user in DB:", victim.email if victim else "None")
    db.close()
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("=== TEST 1: LOW SEVERITY CHECK-IN ===")
low_payload = {"message": "Hello, I am feeling steady today and doing well.", "language": "EN"}
res_low = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json=low_payload, headers=headers)
print("Status:", res_low.status_code)
data_low = res_low.json()
print("Severity:", data_low.get("severity_level"))
print("Techniques count:", len(data_low.get("coping_techniques", [])))
print("Alert generated:", data_low.get("alert_generated"))
assert data_low.get("severity_level") == "low"
assert len(data_low.get("coping_techniques", [])) > 0
assert not data_low.get("alert_generated")

print("\n=== TEST 2: MEDIUM SEVERITY (COURT ANXIETY & COUNSELLOR ESCALATION) ===")
med_payload = {"message": "I am feeling deep dread and stress about my upcoming court hearing date.", "language": "EN"}
res_med = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json=med_payload, headers=headers)
print("Status:", res_med.status_code)
data_med = res_med.json()
print("Severity:", data_med.get("severity_level"))
print("Escalation contact:", data_med.get("escalation_contact", {}).get("officer_name"))
print("Alert generated:", data_med.get("alert_generated"))
assert data_med.get("severity_level") == "medium"
assert data_med.get("escalation_contact") is not None
assert not data_med.get("alert_generated")

print("\n=== TEST 3: HIGH SEVERITY (THREAT TO LIFE & AUTOMATED ALERT DISPATCH) ===")
high_payload = {"message": "Someone came outside my house with weapons and threatened to kill me if I go to court!", "language": "EN"}
res_high = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json=high_payload, headers=headers)
print("Status:", res_high.status_code)
data_high = res_high.json()
print("Severity:", data_high.get("severity_level"))
print("Alert generated:", data_high.get("alert_generated"))
print("Alert details badge:", data_high.get("alert_details", {}).get("badge"))
assert data_high.get("severity_level") == "high"
assert data_high.get("alert_generated") is True

print("\n=== TEST 4: MULTILINGUAL HINDI CHECK-IN (THREAT & SECTION 15A) ===")
hi_payload = {"message": "आरोपी ने मुझे धमकी दी है और मुझे अपनी जान का डर है", "language": "HI"}
res_hi = requests.post(f"{BASE_URL}/api/victim/chatbot/message", json=hi_payload, headers=headers)
print("Status:", res_hi.status_code)
data_hi = res_hi.json()
print("Severity:", data_hi.get("severity_level"))
print("Bot response (HI):", data_hi.get("bot_response")[:120], "...")
print("Alert badge (HI):", data_hi.get("alert_details", {}).get("badge"))
assert data_hi.get("severity_level") == "high"
assert data_hi.get("alert_generated") is True

print("\nALL 4 TESTS PASSED FLAWLESSLY! 3-Tier Severity Triaging & Multilingual Alerts Verified!")
