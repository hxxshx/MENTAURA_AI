import urllib.request
import urllib.parse
import json
import re

print("=== 1. VERIFYING HTML STRUCTURE & 3 TABS IN counsellor-workspace.html ===")
with open("counsellor-workspace.html", "r", encoding="utf-8") as f:
    html = f.read()

# Verify the 3 Caseload summary counters in the compact hero banner
counters = re.findall(r'id="(cntDirectMessages|cntScheduledVideo|cntPendingRequests)"', html)
print(f"Caseload Counters Found in Hero ({len(counters)}):", counters)
assert set(counters) == {"cntDirectMessages", "cntScheduledVideo", "cntPendingRequests"}, "Missing counters!"

# Verify hero-counters-strip contains exactly 3 pills
hero_strip_match = re.search(r'<div class="hero-counters-strip"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
assert hero_strip_match, "Could not locate hero-counters-strip in hero banner"
hero_pills = re.findall(r'data-target-tab="([^"]+)"', hero_strip_match.group(1))
print(f"Hero Counter Pills Found ({len(hero_pills)}):", hero_pills)
assert hero_pills == ["messages", "video", "requests"], f"Expected hero pills ['messages', 'video', 'requests'], got {hero_pills}"

# Verify that inner workspace-tabs-bar and bulky counsellor-summary-card are completely removed
assert '<div class="workspace-tabs-bar"' not in html, "workspace-tabs-bar should not be present inside the tab section"
assert 'counsellor-summary-card' not in html, "counsellor-summary-card should not be present"
print("[OK] Redundant inner tabs bar and bulky summary card successfully removed from page body.")

# Verify exactly the 3 tabs in the header navigation pill (replacing single Review Workspace)
header_nav_match = re.search(r'<nav class="nav-pill" id="mainNavPill"[^>]*>(.*?)</nav>', html, re.DOTALL)
assert header_nav_match, "Could not locate #mainNavPill"
header_tabs = re.findall(r'class="[^"]*header-nav-tab[^"]*"[^>]*data-tab="([^"]+)"', header_nav_match.group(1))
print(f"Header Navigation Tabs Found ({len(header_tabs)}):", header_tabs)
assert header_tabs == ["messages", "video", "requests"], f"Expected header tabs ['messages', 'video', 'requests'], got {header_tabs}"
assert 'id="headerBadgeMessages"' in html, "Missing #headerBadgeMessages in header nav"
assert 'id="headerBadgeVideo"' in html, "Missing #headerBadgeVideo in header nav"
assert 'id="headerBadgeRequests"' in html, "Missing #headerBadgeRequests in header nav"
print("[OK] Header navigation pill contains strictly the 3 tabs with badges.")

# Verify exactly the 3 panels
panels = re.findall(r'id="(panel-[a-z]+)"', html)
print(f"Queue Panels Found ({len(panels)}):", panels)
assert set(panels) == {"panel-messages", "panel-video", "panel-requests"}, f"Unexpected panels: {panels}"

# Verify WhatsApp-style message layout elements in Panel 1
assert 'id="counsellorConvosList"' in html, "Missing #counsellorConvosList in Panel 1"
assert 'id="counsellorThreadMessages"' in html, "Missing #counsellorThreadMessages in Panel 1"
assert 'id="counsellorReplyForm"' in html, "Missing #counsellorReplyForm in Panel 1"
print("[OK] WhatsApp-style direct messaging layout verified.")

# Verify Video Consultation elements in Panel 2
assert 'id="videoScheduleTableBody"' in html, "Missing #videoScheduleTableBody in Panel 2"
assert 'id="counsellorVideoModal"' in html, "Missing #counsellorVideoModal"
print("[OK] Google Meet video consultation enclave verified.")

# Verify Counselling Requests and In-Person Slip in Panel 3
assert 'id="requestsTableBody"' in html, "Missing #requestsTableBody in Panel 3"
assert 'id="inPersonVerificationSlipModal"' in html, "Missing #inPersonVerificationSlipModal"
assert 'id="slipPassNumber"' in html, "Missing #slipPassNumber"
assert 'id="slipBeneficiaryName"' in html, "Missing #slipBeneficiaryName"
assert 'id="slipCaseId"' in html, "Missing #slipCaseId"
assert 'id="slipAppointmentTime"' in html, "Missing #slipAppointmentTime"
print("[OK] Counselling requests table and In-Person OSC Verification Pass Slip verified.")

print("\n=== 2. VERIFYING LIVE BACKEND APIS WITH AUTHENTICATED COUNSELLOR ===")
# Login as Dr. Priya Nair (Counsellor)
login_req = urllib.request.Request(
    'http://127.0.0.1:8000/api/auth/login',
    data=json.dumps({'email': 'counsellor@mentaura.example', 'password': 'Mentaura@2026'}).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(login_req) as resp:
    login_data = json.loads(resp.read().decode())
    token = login_data['token']
    user = login_data['user']
    print(f"Logged in as: {user['full_name']} ({user['verified_role']})")

headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

# 1. Overview
overview_req = urllib.request.Request('http://127.0.0.1:8000/api/counsellor/overview', headers=headers)
with urllib.request.urlopen(overview_req) as resp:
    ov = json.loads(resp.read().decode())
    print("Overview API 200 OK. Summary:", ov.get("summary"))

# 2. Conversations (Tab 1)
convos_req = urllib.request.Request('http://127.0.0.1:8000/api/counsellor/messages/conversations', headers=headers)
with urllib.request.urlopen(convos_req) as resp:
    convos_data = json.loads(resp.read().decode())
    convos = convos_data.get('conversations', [])
    print(f"Tab 1: Message Consultations Found: {len(convos)}")
    for c in convos:
        print(f"  - Convo with {c['victim_name']}: {c['last_message']} ({c.get('unread_count', 0)} unread)")

# 3. Support Requests (Tab 2 & 3)
reqs_req = urllib.request.Request('http://127.0.0.1:8000/api/counsellor/support-requests', headers=headers)
with urllib.request.urlopen(reqs_req) as resp:
    reqs_data = json.loads(resp.read().decode())
    reqs = reqs_data.get('support_requests', [])
    print(f"Tab 3: Support Requests Found: {len(reqs)}")
    video_reqs = [r for r in reqs if r.get('session_format') == 'video' or (r.get('session_metadata') and r['session_metadata'].get('format') == 'video')]
    print(f"Tab 2: Scheduled Video Consultations Found: {len(video_reqs)}")

# 4. Test Scheduling an In-Person Consultation with Verification Pass Slip Generation
if reqs:
    test_req = reqs[0]
    print(f"\nTesting scheduling In-Person consultation for request {test_req['id']} ({test_req['masked_requester']})...")
    action_payload = {
        "target_type": "support_request",
        "target_id": test_req['id'],
        "action_type": "schedule_session",
        "status": "scheduled",
        "notes": "Format: IN PERSON | Clinical Assessment: OSC Chamber 104 intake scheduled",
        "appointment_date": "2026-09-15T10:00:00Z",
        "assigned_role": "Psychological Counsellor",
        "session_format": "in_person"
    }
    action_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/counsellor/review-action',
        data=json.dumps(action_payload).encode(),
        headers={'Content-Type': 'application/json', **headers}
    )
    with urllib.request.urlopen(action_req) as resp:
        res = json.loads(resp.read().decode())
        print("Schedule session action response:", res)

    # Re-fetch requests to verify generated pass slip details
    with urllib.request.urlopen(reqs_req) as resp:
        updated_reqs = json.loads(resp.read().decode()).get('support_requests', [])
        updated = next(r for r in updated_reqs if r['id'] == test_req['id'])
        meta = updated.get('session_metadata') or {}
        print("Generated Pass Details:")
        print(f"  - Session Format: {updated.get('session_format')}")
        print(f"  - Pass Number: {meta.get('pass_number')}")
        print(f"  - Location: {meta.get('location')}")
        print(f"  - Transit Escort: {meta.get('transit_escort')}")
        assert meta.get('pass_number'), "Pass number was not generated!"
        assert meta.get('pass_number').startswith("OSC-TN-2026-"), f"Unexpected pass number format: {meta.get('pass_number')}"

print("\n>>> ALL 3 TABS, WHATSAPP MESSAGING, VIDEO MEET, & OSC VERIFICATION SLIP VERIFIED SUCCESSFULLY! <<<")
