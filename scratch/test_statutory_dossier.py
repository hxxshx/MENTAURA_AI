import sys
import io

# Force utf-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

print("=== 1. TESTING BACKEND STATUTORY RELIEF ENDPOINTS ===")
session = requests.Session()
login_res = session.post('http://localhost:8000/api/auth/login', json={
    'email': 'victim@mentaura.example',
    'password': 'Mentaura@2026'
})
assert login_res.status_code == 200, f"Login failed: {login_res.status_code}"
print("[OK] Victim login successful")

# Test GET statutory relief
get_res = session.get('http://localhost:8000/api/victim/statutory-relief')
assert get_res.status_code == 200, f"GET statutory-relief failed: {get_res.status_code}"
data = get_res.json()

print(f"[OK] Total Sanctioned: {data['total_relief_sanctioned_display']}")
print(f"[OK] Total Disbursed: {data['total_disbursed_display']}")
print(f"[OK] Pending Balance: {data['balance_pending_display']}")
print(f"[OK] Stages count: {len(data['stages'])}")
assert len(data['stages']) == 3, f"Expected 3 stages, got {len(data['stages'])}"

tracker = data['dsp_investigation_tracker']
print(f"[OK] Rule 7(2) DSP Clock: {tracker['days_remaining']} days remaining (elapsed: {tracker['days_elapsed']} of {tracker['statutory_limit_days']} days)")
assert tracker['statutory_limit_days'] == 60

tame = data['tame_allowance']
print(f"[OK] Rule 11 TAME Allowance: {tame['total_tame_reimbursed']} reimbursed (rate: {tame['rate_per_day']})")

charter = data['rights_charter']
print(f"[OK] Section 15A Rights Charter: {len(charter)} statutory rights returned")
assert len(charter) >= 5

# Test POST action: court_escort
escort_res = session.post('http://localhost:8000/api/victim/statutory-relief/action', json={
    'action_type': 'court_escort',
    'pickup_location': 'Village East Panchayat Hall',
    'hearing_date': '2026-09-22T10:30',
    'details': 'Need escort van due to intimidation from accused associates'
})
assert escort_res.status_code == 200, f"Escort action failed: {escort_res.status_code}"
escort_data = escort_res.json()
print(f"[OK] Escort Action Invocation: {escort_data['title']} (Ref: {escort_data['reference_id']})")

# Test POST action: dlsa legal aid
legal_res = session.post('http://localhost:8000/api/victim/statutory-relief/action', json={
    'action_type': 'legal_aid',
    'details': 'Requesting senior advocate for special court bail objection'
})
assert legal_res.status_code == 200, f"Legal aid action failed: {legal_res.status_code}"
legal_data = legal_res.json()
print(f"[OK] Legal Aid Invocation: {legal_data['title']} (Ref: {legal_data['reference_id']})")

# Test POST action: tame claim
tame_res = session.post('http://localhost:8000/api/victim/statutory-relief/action', json={
    'action_type': 'tame_claim',
    'details': 'Attended Special Court hearing on 10 Sep. Bus ticket fare Rs 240.'
})
assert tame_res.status_code == 200, f"TAME claim failed: {tame_res.status_code}"
tame_action_data = tame_res.json()
print(f"[OK] TAME Claim Invocation: {tame_action_data['title']} (Ref: {tame_action_data['reference_id']})")


print("\n=== 2. TESTING FRONTEND HTML MARKUP & IDS ===")
with open("distress-trends.html", "r", encoding="utf-8") as f:
    html = f.read()

required_html_ids = [
    "openSection15AModalBtn",
    "mandateCategory",
    "mandateDisbursedAmount",
    "mandateStageBadge",
    "mandateStageBadgeText",
    "mandateNarrative",
    "btnReviewSection15A",
    "section15AModal",
    "section15AModalTitle",
    "closeSection15AModalBtn",
    "statActionAlert",
    "btnTabCompensation",
    "btnTabDspClock",
    "btnTabRights",
    "btnTabActions",
    "tabCompensation",
    "tabDspClock",
    "tabRights",
    "tabActions",
    "statDisbursedVal",
    "statPendingVal",
    "statSanctionedVal",
    "statStagesList",
    "dspDaysRemaining",
    "dspDaysElapsed",
    "dspProgressBarFill",
    "dspOfficerName",
    "dspComplianceStatus",
    "statRightsGrid",
    "statActionForm"
]

for hid in required_html_ids:
    assert f'id="{hid}"' in html, f"Missing HTML ID: {hid}"
print(f"[OK] All {len(required_html_ids)} required Section 15A HTML elements verified in distress-trends.html")

print("\n=== 3. TESTING FRONTEND JAVASCRIPT LOGIC ===")
with open("js/trends.js", "r", encoding="utf-8") as f:
    js = f.read()

assert "fetchStatutoryReliefData" in js
assert "initSection15AModal" in js
assert "renderStatutoryCardAndModal" in js
assert "/api/victim/statutory-relief" in js
assert "/api/victim/statutory-relief/action" in js
print("[OK] All Section 15A frontend handlers and async bindings verified in js/trends.js")

print("\n=== ALL AUDITS & TESTS PASSED! ===")
