import urllib.request
import json
import time

def api_post(url, data, token=None):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def api_get(url, token=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

print("=== 1. AUTHENTICATING COUNSELLOR & VICTIM ===")
c_login = api_post("http://127.0.0.1:8000/api/auth/login", {"email": "counsellor@mentaura.example", "password": "Mentaura@2026"})
c_token = c_login["token"]
print(f"Counsellor logged in: {c_login['user']['full_name']}")

v_login = api_post("http://127.0.0.1:8000/api/auth/login", {"email": "victim@mentaura.example", "password": "Mentaura@2026"})
v_token = v_login["token"]
victim_id = v_login["user"]["id"]
print(f"Victim logged in: {v_login['user']['full_name']} (ID: {victim_id})")

ts = int(time.time())
c_msg = f"hi hi ({ts})"
print(f"\n=== 2. COUNSELLOR SENDS TO VICTIM: '{c_msg}' ===")
c_send = api_post(f"http://127.0.0.1:8000/api/counsellor/messages/{victim_id}/reply", {"message_text": c_msg}, token=c_token)
print(f"Counsellor send result: {c_send.get('status')}")

print("\n=== 3. VICTIM INBOX RECEIVES MESSAGE ===")
v_inbox = api_get("http://127.0.0.1:8000/api/victim/counsellor-chat/messages", token=v_token)
received_texts = [m["message_text"] for m in v_inbox.get("messages", [])]
assert c_msg in received_texts, f"Victim did not receive {c_msg}!"
print(f"SUCCESS: Victim received '{c_msg}' from Dr. Priya Nair!")

v_msg = f"im not ok ({ts})"
print(f"\n=== 4. VICTIM SENDS TO COUNSELLOR: '{v_msg}' ===")
v_send = api_post("http://127.0.0.1:8000/api/victim/counsellor-chat/send", {"message_text": v_msg}, token=v_token)
print(f"Victim send result: {v_send.get('status')}")

print("\n=== 5. COUNSELLOR RECEIVES VICTIM MESSAGE IN THREAD ===")
c_thread = api_get(f"http://127.0.0.1:8000/api/counsellor/messages/{victim_id}", token=c_token)
c_received_texts = [m["message_text"] for m in c_thread.get("messages", [])]
assert v_msg in c_received_texts, f"Counsellor did not receive {v_msg}!"
print(f"SUCCESS: Counsellor received '{v_msg}' from Aanya Sharma!")

print("\n>>> DYNAMIC TWO-WAY REAL-TIME MESSAGING VERIFIED 100% FUNCTIONAL! <<<")
