import urllib.request
import json
import re

print("=== VERIFYING GOOGLE MEET FIXES ===")

# 1. Verify HTML badge updates and canvas removal
for fname in ["counsellor-workspace.html", "distress-trends.html"]:
    with open(fname, "r", encoding="utf-8") as f:
        content = f.read()

    has_protected = "Protected" in content
    has_secure = "Secure" in content
    has_1080p = "1080p Encrypted" in content
    has_sec15a = "Direct Sec. 15A" in content
    has_gmeet_canvas = "gmeetCanvas" in content

    print(f"[{fname}]")
    print(f"  Protected badge present: {has_protected}")
    print(f"  Secure badge present: {has_secure}")
    print(f"  1080p Encrypted removed: {not has_1080p}")
    print(f"  Direct Sec. 15A removed: {not has_sec15a}")
    print(f"  Canvas cartoon elements removed: {not has_gmeet_canvas}")

    assert has_protected and has_secure, f"Missing badges in {fname}"
    assert not has_1080p and not has_sec15a, f"Old badges still present in {fname}"
    assert not has_gmeet_canvas, f"Canvas element still present in {fname}"

# 2. Verify js/gmeet.js
with open("js/gmeet.js", "r", encoding="utf-8") as f:
    js_content = f.read()

assert "startLifelikePeerStream" not in js_content, "Cartoon peer stream still in js/gmeet.js!"
assert "mentaura_gmeet_active_call" in js_content, "Dual broadcast channel missing in js/gmeet.js!"
assert "RTCPeerConnection" in js_content, "WebRTC peer connection missing in js/gmeet.js!"
assert "loadInCallMessages" in js_content, "loadInCallMessages missing in js/gmeet.js!"
assert "_chatPollInterval" in js_content, "Chat polling missing in js/gmeet.js!"
print("[js/gmeet.js] All WebRTC, dual-channel broadcast, in-call chat polling & AI cartoon removal verified!")

# 3. Verify Backend Video Call Message Endpoints
# Login as victim
login_data = json.dumps({"email": "victim@mentaura.example", "password": "Mentaura@2026"}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    cookies = resp.headers.get("Set-Cookie")
    auth_resp = json.loads(resp.read().decode("utf-8"))
    token = auth_resp.get("access_token")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
    "Cookie": cookies
}

# Post a test message from victim
msg_payload = json.dumps({"room_id": "mentaura-priority-be1ed4", "message_text": "Hi doctor, I am ready for the consultation"}).encode("utf-8")
post_req = urllib.request.Request("http://127.0.0.1:8000/api/video-call/messages", data=msg_payload, headers=headers)
with urllib.request.urlopen(post_req) as resp:
    post_res = json.loads(resp.read().decode("utf-8"))
    assert post_res["success"] == True
    print(f"[Backend POST /api/video-call/messages] Success: {post_res['message']['message_text']}")

# Query messages with different room id to verify fallback query
get_req = urllib.request.Request("http://127.0.0.1:8000/api/video-call/messages?room_id=mentaura-priority-32b36c", headers=headers)
with urllib.request.urlopen(get_req) as resp:
    get_res = json.loads(resp.read().decode("utf-8"))
    assert get_res["success"] == True
    msgs = get_res["messages"]
    print(f"[Backend GET /api/video-call/messages (cross-room fallback)] Retrieved {len(msgs)} messages:")
    for m in msgs[-3:]:
        print(f"   -> [{m['sender_name']} ({m['sender_role']})]: {m['message_text']}")

print("\n=== ALL VIDEO CALL & IN-CALL CHAT TESTS PASSED SUCCESSFULLY! ===")
