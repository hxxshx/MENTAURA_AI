import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

BASE_URL = "http://127.0.0.1:8000"

def make_req(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 0, str(e)

# 1. Login
status, data = make_req("/api/auth/login", "POST", {"email": "victim@mentaura.example", "password": "Mentaura@2026"})
print("Login status:", status)
token = data.get("token") or data.get("access_token")
assert token, f"Login failed: {data}"

# 2. Test Chatbot Message (Low / Greeting)
status, data = make_req("/api/victim/chatbot/message", "POST", {
    "message": "Hello, just checking in today.",
    "language": "EN"
}, token=token)
print("\n[Chatbot Message - Low]:", status, "Severity:", data.get("severity_level"))
print("Reply:", data.get("reply"))
assert status == 200

# 3. Test Chatbot Message (Medium with elevation prompt)
status, data = make_req("/api/victim/chatbot/message", "POST", {
    "message": "I am feeling very anxious about my court hearing date tomorrow.",
    "language": "EN"
}, token=token)
print("\n[Chatbot Message - Medium]:", status, "Severity:", data.get("severity_level"))
print("Reply:", data.get("reply"))
print("Elevation Prompt:", data.get("elevation_prompt"))
assert status == 200

# 4. Test Chatbot Elevate Endpoint
status, data = make_req("/api/victim/chatbot/elevate", "POST", {
    "message": "User confirmed counsellor connection via chatbot",
    "language": "EN"
}, token=token)
print("\n[Chatbot Elevate]:", status, "Success:", data.get("success"))
print("Message:", data.get("message"))
print("Counsellor Notified:", data.get("counsellor_notified"))
assert status == 200

print("\n=== ALL CHATBOT ENDPOINTS VERIFIED SUCCESSFULLY! ===")
