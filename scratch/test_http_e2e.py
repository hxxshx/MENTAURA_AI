import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://127.0.0.1:8000"

# Set up cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Helper function
def make_request(path, method="GET", data=None, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method=method)
    try:
        with opener.open(req) as resp:
            content = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(content)
            except Exception:
                return resp.status, content
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_content)
        except Exception:
            return e.code, err_content

print("=== 1. Testing Health Endpoint ===")
status, res = make_request("/health")
print(f"Health: status={status}, app={res.get('app')}")
assert status == 200

print("\n=== 2. Logging in as Victim User ===")
login_payload = {
    "email": "victim@mentaura.example",
    "password": "Mentaura@2026"
}
status, login_res = make_request("/api/auth/login", method="POST", data=login_payload)
print(f"Login: status={status}, role={login_res.get('user', {}).get('verified_role')}")
assert status == 200
access_token = login_res.get("access_token")
auth_headers = {"Authorization": f"Bearer {access_token}"}

print("\n=== 3. Testing Voice Turn: Low Distress ===")
turn_low = {
    "transcript": "I am doing okay and holding steady today, just checking in.",
    "language": "EN",
    "audio_duration_seconds": 5.0,
    "pitch_tension_hz": 165.0,
    "jitter_percent": 1.1,
    "pause_ratio": 0.18
}
status, res_low = make_request("/api/victim/voice-chat/turn", method="POST", data=turn_low, headers=auth_headers)
print(f"Low Turn: status={status}, class={res_low['classification']}, score={res_low['distress_score']}")
print(f"Low AI Spoken Reply: {res_low['ai_spoken_reply']}")
print(f"Low Suggested Actions: {[a['title'] for a in res_low['suggested_actions']]}")
assert status == 200
assert res_low['classification'] == "low"

print("\n=== 4. Testing Voice Turn: Medium Distress ===")
turn_med = {
    "transcript": "I am feeling very anxious, stressed, and overwhelmed about my upcoming court hearing date.",
    "language": "EN",
    "audio_duration_seconds": 6.0,
    "pitch_tension_hz": 192.0,
    "jitter_percent": 1.65,
    "pause_ratio": 0.32
}
status, res_med = make_request("/api/victim/voice-chat/turn", method="POST", data=turn_med, headers=auth_headers)
print(f"Med Turn: status={status}, class={res_med['classification']}, score={res_med['distress_score']}")
print(f"Med AI Spoken Reply: {res_med['ai_spoken_reply']}")
print(f"Elevation Prompt: {res_med['elevation_prompt']}")
assert status == 200
assert res_med['classification'] == "medium"
assert res_med['elevation_prompt'] is not None

print("\n=== 5. Testing Voice Turn: High Distress ===")
turn_high = {
    "transcript": "I feel terrified and unsafe, someone threatened me outside and I cannot take this anymore, please help me!",
    "language": "EN",
    "audio_duration_seconds": 7.0,
    "pitch_tension_hz": 228.0,
    "jitter_percent": 2.4,
    "pause_ratio": 0.46
}
status, res_high = make_request("/api/victim/voice-chat/turn", method="POST", data=turn_high, headers=auth_headers)
print(f"High Turn: status={status}, class={res_high['classification']}, score={res_high['distress_score']}")
print(f"High AI Spoken Reply: {res_high['ai_spoken_reply']}")
print(f"Counsellor Notified: {res_high['counsellor_notified']}")
print(f"Notification ID: {res_high['notification_id']}")
assert status == 200
assert res_high['classification'] == "high"
assert res_high['counsellor_notified'] is True

print("\n=== 6. Testing Counsellor Elevation from Voice AI ===")
elev_payload = {
    "transcript": turn_med["transcript"],
    "notes": "Victim requested elevation from AI Voice Mode"
}
status, res_elev = make_request("/api/victim/voice-chat/elevate", method="POST", data=elev_payload, headers=auth_headers)
print(f"Elevate: status={status}, msg={res_elev['message']}")
assert status == 200
assert res_elev['status'] == "elevated"

print("\n=== 7. Logging in as Counsellor & Verifying Notifications ===")
counsellor_cj = http.cookiejar.CookieJar()
counsellor_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(counsellor_cj))

login_counsellor = {
    "email": "counsellor@mentaura.example",
    "password": "Mentaura@2026"
}
req_c = urllib.request.Request(
    f"{BASE_URL}/api/auth/login",
    data=json.dumps(login_counsellor).encode("utf-8"),
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST"
)
with counsellor_opener.open(req_c) as r:
    c_login = json.loads(r.read().decode("utf-8"))
    c_token = c_login.get("access_token")

req_notifs = urllib.request.Request(
    f"{BASE_URL}/api/notifications",
    headers={"Authorization": f"Bearer {c_token}", "Accept": "application/json"}
)
with counsellor_opener.open(req_notifs) as r:
    res = json.loads(r.read().decode("utf-8"))
    notif_list = res.get("notifications", [])
    print(f"Counsellor received {len(notif_list)} notifications total (unread: {res.get('unread_count')}).")
    for n in notif_list[:3]:
        print(f"  - [{n.get('severity', 'info').upper()}] {n.get('title')}: {n.get('message')}")
        
    assert any("Voice Check-In" in n.get("title", "") for n in notif_list), "Expected Voice Check-In notification"

print("\n=== ALL VOICE CHAT E2E SCENARIOS VERIFIED SUCCESSFULLY! ===")

print("\n=== 8. Checking Frontend Assets on Localhost ===")
req_page = urllib.request.Request(f"{BASE_URL}/checkin.html")
with opener.open(req_page) as r:
    html_data = r.read().decode("utf-8")
    assert "Interactive Voice Check-In" in html_data
    assert "voice-studio-container" in html_data
    assert "ChatGPT-Style" not in html_data
    print("checkin.html contains clean, user-friendly Voice Check-In UI without technical clutter or ChatGPT labels!")

print("\nALL HTTP & E2E ENDPOINTS VALIDATED SUCCESSFULLY!")
