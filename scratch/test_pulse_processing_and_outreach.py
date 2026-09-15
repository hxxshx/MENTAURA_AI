import json
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://127.0.0.1:8000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def req(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with opener.open(r) as response:
        content = response.read().decode("utf-8")
        return response.status, json.loads(content)

print("=== 1. Logging in as Victim ===")
status, login_data = req("/api/auth/login", method="POST", data={
    "email": "victim@mentaura.example",
    "password": "Mentaura@2026"
})
assert status == 200
token = login_data.get("token") or login_data.get("access_token")
auth_h = {"Authorization": f"Bearer {token}"}
print("Victim login successful!")

print("\n=== 2. Submitting Support Pulse with Safety Concern & Follow-up Requests ===")
pulse_payload = {
    "wellbeing_state": "I feel very overwhelmed and stressed",
    "affecting_factors": ["Safety concerns outside my home", "Upcoming court hearing"],
    "safety_status": "No, I do not feel safe.",
    "follow_up_requests": ["Request Support Team Call", "Legal aid advice"],
    "support_needs": ["Counselling support", "Protection assistance"],
    "processing_mode": "ai_assisted",
    "ai_processing_consent": True,
    "private_note": "Someone came by and warned me about the court hearing. I need advice on protection and legal assistance."
}

status, pulse_res = req("/api/victim/pulse", method="POST", data=pulse_payload, headers=auth_h)
print(f"Status Code: {status}")
print(f"Analysis Status: {pulse_res.get('analysis_status')}")
print(f"Risk Level: {pulse_res.get('risk_level')}")
print(f"Priority Review: {pulse_res.get('priority_review')}")
print(f"Timeline: {pulse_res.get('care_team_outreach', {}).get('contact_timeline')}")
print(f"Badge Text: {pulse_res.get('care_team_outreach', {}).get('badge_text')}")
print(f"Team Message: {pulse_res.get('care_team_outreach', {}).get('team_contact_message')}")
print(f"Next Steps: {json.dumps(pulse_res.get('care_team_outreach', {}).get('next_steps'), indent=2)}")

assert pulse_res.get("analysis_status") == "completed", "Expected analysis_status to be 'completed' instead of 'queued'!"
assert pulse_res.get("status") == "completed", "Expected status to be 'completed'!"
assert "care_team_outreach" in pulse_res, "Expected care_team_outreach in response!"
assert "contact" in pulse_res["care_team_outreach"]["team_contact_message"].lower()

print("\n=== 3. Logging in as Counsellor & Verifying Triage Queue & Notifications ===")
c_cj = http.cookiejar.CookieJar()
c_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(c_cj))

def c_req(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with c_opener.open(r) as response:
        content = response.read().decode("utf-8")
        return response.status, json.loads(content)

c_status, c_login = c_req("/api/auth/login", method="POST", data={
    "email": "counsellor@mentaura.example",
    "password": "Mentaura@2026"
})
assert c_status == 200
c_token = c_login.get("token") or c_login.get("access_token")
c_auth_h = {"Authorization": f"Bearer {c_token}"}

# Check triage queue
t_status, triage_data = c_req("/api/counsellor/triage-queue", headers=c_auth_h)
assert t_status == 200
items = triage_data.get("triage_queue", [])
print(f"Triage queue has {len(items)} items. Top item risk: {items[0].get('risk_level') if items else 'None'}")
assert any(i.get("id") == pulse_res.get("pulse_id") for i in items), "Submitted pulse must appear in counsellor triage queue!"

# Check notifications
n_status, notifs = c_req("/api/notifications", headers=c_auth_h)
assert n_status == 200
notif_list = notifs.get("notifications", [])
print(f"Counsellor has {len(notif_list)} notifications. Top: {notif_list[0].get('title')} - {notif_list[0].get('message')}")

print("\n=== ALL REAL-TIME PROCESSING AND TEAM OUTREACH VERIFICATIONS PASSED! ===")
