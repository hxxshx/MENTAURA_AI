import requests
import json
import re

BASE_URL = "http://127.0.0.1:8000"

# 1. Verify HTML element IDs and structure
with open("counsellor-workspace.html", "r", encoding="utf-8") as f:
    html = f.read()

required_ids = [
    "notificationBellBtn",
    "notificationBadge",
    "notificationDropdown",
    "notificationHeaderCount",
    "markAllReadBtn",
    "notificationList"
]

for rid in required_ids:
    assert f'id="{rid}"' in html, f"Missing {rid} in counsellor-workspace.html"

print("All notification HTML elements present!")

# 2. Login as Counsellor
session = requests.Session()
login_res = session.post(f"{BASE_URL}/api/auth/login", json={
    "email": "counsellor@mentaura.example",
    "password": "Mentaura@2026"
})
assert login_res.status_code == 200, f"Counsellor login failed: {login_res.text}"
c_data = login_res.json()
token = c_data.get("token") or c_data.get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 3. Test unread count endpoint
unread_res = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers)
assert unread_res.status_code == 200, f"Unread count failed: {unread_res.text}"
initial_unread = unread_res.json().get("unread_count", 0)
print(f"Initial unread notifications count: {initial_unread}")

# 4. Test fetch notifications list
list_res = requests.get(f"{BASE_URL}/api/notifications?limit=20", headers=headers)
assert list_res.status_code == 200, f"Fetch notifications failed: {list_res.text}"
notifs = list_res.json().get("notifications", [])
print(f"Fetched {len(notifs)} notifications from API.")

# 5. Test mark single as read
if notifs:
    target_notif = notifs[0]
    notif_id = target_notif["id"]
    mark_res = requests.post(f"{BASE_URL}/api/notifications/mark-read", headers=headers, json={
        "notification_ids": [notif_id]
    })
    assert mark_res.status_code == 200, f"Mark single read failed: {mark_res.text}"
    print(f"Successfully marked notification {notif_id} as read.")

# 6. Test sending a new victim message to trigger a fresh notification
victim_session = requests.Session()
v_login = victim_session.post(f"{BASE_URL}/api/auth/login", json={
    "email": "victim@mentaura.example",
    "password": "Mentaura@2026"
})
assert v_login.status_code == 200, f"Victim login failed: {v_login.text}"

send_res = victim_session.post(f"{BASE_URL}/api/victim/counsellor-chat/send", json={
    "message_text": "Hello Dr. Priya, checking in on my court date notification."
})
assert send_res.status_code == 200, f"Victim send failed: {send_res.text}"

# Verify counsellor received the notification
latest_notifs_res = requests.get(f"{BASE_URL}/api/notifications?limit=5", headers=headers)
assert latest_notifs_res.status_code == 200
latest_notifs = latest_notifs_res.json().get("notifications", [])
chat_notifs = [n for n in latest_notifs if n.get("type") == "counsellor_message"]
assert len(chat_notifs) > 0, "Expected at least one counsellor_message notification!"
first_chat_notif = chat_notifs[0]
assert first_chat_notif.get("metadata", {}).get("victim_id"), "Metadata missing victim_id!"

print("Notification dispatch and metadata verification passed!")
print("ALL NOTIFICATION SYSTEM CHECKS COMPLETED SUCCESSFULLY!")
