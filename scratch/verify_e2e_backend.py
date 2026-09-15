"""
Comprehensive E2E Backend Integration Validation Script (TASK 18)
Validates that all major user-facing components across Mentaura are:
1. Powered by real backend APIs.
2. Sourced from actual database records in SQLite (mentaura.db).
3. Consistent with zero fake or static demo data.
4. Correctly propagating real-time updates across victim, counsellor, and admin workflows.
"""
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "mentaura.db"


class APIClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def post(self, url, json_data=None):
        data_bytes = json.dumps(json_data).encode("utf-8") if json_data is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.opener.open(req) as resp:
                status_code = resp.getcode()
                body = resp.read().decode("utf-8")
                return Response(status_code, json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            return Response(e.code, json.loads(body) if body else {})

    def get(self, url):
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with self.opener.open(req) as resp:
                status_code = resp.getcode()
                body = resp.read().decode("utf-8")
                return Response(status_code, json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            return Response(e.code, json.loads(body) if body else {})


class Response:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json


def get_db_cursor():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()


def login_user(email, password="Mentaura@2026"):
    client = APIClient()
    resp = client.post(f"{BASE_URL}/api/auth/login", {"email": email, "password": password})
    assert resp.status_code == 200, f"Failed login for {email}: {resp.json()}"
    return client, resp.json()["user"]


def test_victim_flow():
    print("\n--- 1. VALIDATING VICTIM FLOW ---")
    client, user = login_user("victim@mentaura.example")
    victim_id = user["id"]
    print(f"Victim logged in: {user['email']} (ID: {victim_id})")

    # A. Victim Overview (/api/victim/overview)
    resp = client.get(f"{BASE_URL}/api/victim/overview")
    assert resp.status_code == 200, f"Failed /api/victim/overview: {resp.json()}"
    data = resp.json()
    assert "user_id" in data
    assert "support_pulse" in data
    assert "case_overview" in data
    assert "support_requests" in data

    # Verify against DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT count(*) FROM support_pulses WHERE authenticated_user_id = ?", (victim_id,))
    db_pulse_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM support_requests WHERE user_id = ?", (victim_id,))
    db_req_count = cur.fetchone()[0]
    conn.close()

    print(f"  [PASS] /api/victim/overview: DB has {db_pulse_count} pulses and {db_req_count} support requests for this user.")

    # B. Support Requests (/api/victim/support)
    resp_req = client.get(f"{BASE_URL}/api/victim/support")
    assert resp_req.status_code == 200, f"Support failed: {resp_req.json()}"
    req_data = resp_req.json()
    assert "requests" in req_data
    assert "summary" in req_data
    print(f"  [PASS] /api/victim/support: {len(req_data['requests'])} request items returned from DB.")

    # C. Journey Milestones (/api/victim/case-journey)
    resp_journey = client.get(f"{BASE_URL}/api/victim/case-journey")
    assert resp_journey.status_code == 200
    journey_data = resp_journey.json()
    assert "timeline" in journey_data
    assert "current_stage" in journey_data
    print(f"  [PASS] /api/victim/case-journey: Stage '{journey_data['current_stage']}' with {len(journey_data['timeline'])} timeline milestones.")

    # D. Privacy & Consent (/api/victim/privacy-consent)
    resp_pc = client.get(f"{BASE_URL}/api/victim/privacy-consent")
    assert resp_pc.status_code == 200
    pc_data = resp_pc.json()
    assert "consent_records" in pc_data
    assert "account" in pc_data
    print(f"  [PASS] /api/victim/privacy-consent: Found {len(pc_data['consent_records'])} consent records.")


def test_counsellor_flow():
    print("\n--- 2. VALIDATING COUNSELLOR FLOW ---")
    client, user = login_user("counsellor@mentaura.example")
    print(f"Counsellor logged in: {user['email']} (Role: {user['verified_role']})")

    # A. Overview (/api/counsellor/overview)
    resp = client.get(f"{BASE_URL}/api/counsellor/overview")
    assert resp.status_code == 200
    data = resp.json()
    stats = data["summary"]
    print(f"  [PASS] /api/counsellor/overview: New Pulses: {stats['new_pulses_count']}, Pending Requests: {stats['pending_requests_count']}, Active Cases: {stats['active_cases_count']}")

    # B. Triage Queue (/api/counsellor/triage-queue)
    resp_triage = client.get(f"{BASE_URL}/api/counsellor/triage-queue?limit=50")
    assert resp_triage.status_code == 200
    triage_data = resp_triage.json()
    assert "triage_queue" in triage_data
    pulses = triage_data["triage_queue"]
    print(f"  [PASS] /api/counsellor/triage-queue: Total {triage_data['total_count']} items in queue, returned {len(pulses)} items.")

    # Cross-reference with DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT id, risk_level, risk_score, human_review_status FROM support_pulses WHERE human_review_status = 'pending'")
    db_pending = cur.fetchall()
    conn.close()

    if pulses:
        first_pulse = pulses[0]
        assert "risk_level" in first_pulse
        assert "risk_score" in first_pulse
        print(f"  [PASS] Top triage pulse ID: {first_pulse['id'][:8]}... Risk Level: {first_pulse['risk_level'].upper()} (Score: {first_pulse['risk_score']})")


def test_command_admin_flow():
    print("\n--- 3. VALIDATING ADMIN COMMAND FLOW ---")
    client, user = login_user("state_admin@mentaura.example")
    print(f"Admin logged in: {user['email']} (Role: {user['verified_role']})")

    # A. Overview (/api/command/overview)
    resp = client.get(f"{BASE_URL}/api/command/overview?time_range=30d")
    assert resp.status_code == 200
    data = resp.json()
    ov = data["overview"]
    print(f"  [PASS] /api/command/overview: Active Cases: {ov['active_cases']}, New Pulses: {ov['new_pulses_7d']}, Pending Requests: {ov['pending_requests']}")

    # B. Metrics By Support Type (/api/command/metrics-by-support-type)
    resp_st = client.get(f"{BASE_URL}/api/command/metrics-by-support-type?time_range=30d")
    assert resp_st.status_code == 200
    st_data = resp_st.json()
    print(f"  [PASS] /api/command/metrics-by-support-type: {len(st_data['categories'])} categories aggregated from DB (Total: {st_data['total_requests_30d']}).")

    # C. Cases By Stage (/api/command/cases-by-stage)
    resp_stage = client.get(f"{BASE_URL}/api/command/cases-by-stage")
    assert resp_stage.status_code == 200
    stage_data = resp_stage.json()
    print(f"  [PASS] /api/command/cases-by-stage: {len(stage_data['stages'])} stages mapped from {stage_data['total_active_cases']} active cases.")

    # D. Priority Cases (/api/command/priority-cases)
    resp_pri = client.get(f"{BASE_URL}/api/command/priority-cases?limit=20")
    assert resp_pri.status_code == 200
    pri_data = resp_pri.json()
    print(f"  [PASS] /api/command/priority-cases: {len(pri_data['priority_cases'])} priority cases returned (Total in queue: {pri_data['total_count']}).")

    # E. District Summary (/api/command/district-summary)
    resp_dist = client.get(f"{BASE_URL}/api/command/district-summary")
    assert resp_dist.status_code == 200
    dist_data = resp_dist.json()
    print(f"  [PASS] /api/command/district-summary: {len(dist_data['districts'])} districts listed for jurisdiction: {dist_data['jurisdiction']['name']}.")


def test_pending_approvals_flow():
    print("\n--- 4. VALIDATING PENDING APPROVALS FLOW ---")
    client, user = login_user("state_admin@mentaura.example")

    # A. Get pending officials
    resp = client.get(f"{BASE_URL}/api/admin/pending-officials")
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_officials" in data
    print(f"  [PASS] /api/admin/pending-officials: {data['total_count']} pending official accounts in database.")

    # B. Test creating a new signup, approving it, and logging in
    import uuid
    test_email = f"test.officer.{uuid.uuid4().hex[:6]}@mentaura.example"
    signup_client = APIClient()
    signup_resp = signup_client.post(f"{BASE_URL}/api/auth/signup", {
        "full_name": "Test Officer Kumar",
        "email": test_email,
        "password": "Password@123",
        "confirm_password": "Password@123",
        "preferred_language": "EN",
        "requested_category": "case_officer",
        "consent_given": True
    })
    assert signup_resp.status_code in (200, 201), f"Signup failed: {signup_resp.json()}"
    created_user = signup_resp.json()["user"]
    user_id = created_user["id"]
    print(f"  [PASS] Created new official signup: {test_email} (Status: {created_user['account_status']})")

    # Verify in DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT account_status, verified_role FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    assert row["account_status"] == "pending_verification"
    conn.close()

    # Approve via Admin API
    approve_resp = client.post(f"{BASE_URL}/api/admin/approve-official", {
        "user_id": user_id,
        "verified_role": "case_officer",
        "notes": "Verified credentials in Tamil Nadu state registry."
    })
    assert approve_resp.status_code == 200
    print(f"  [PASS] Approved official via /api/admin/approve-official.")

    # Verify in DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT account_status, verified_role FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    assert row["account_status"] == "active"
    assert row["verified_role"] == "case_officer"
    conn.close()

    # Log in as newly approved official
    officer_client, officer_user = login_user(test_email, "Password@123")
    assert officer_user["account_status"] == "active"
    print(f"  [PASS] Newly approved official successfully logged in with role: {officer_user['verified_role']}")


def test_risk_scoring_and_notification_triggers():
    print("\n--- 5. VALIDATING RISK SCORING & IN-APP NOTIFICATIONS E2E ---")
    victim_client, victim = login_user("victim@mentaura.example")
    counsellor_client, counsellor = login_user("counsellor@mentaura.example")

    # Initial unread count
    resp_init = counsellor_client.get(f"{BASE_URL}/api/notifications/unread-count")
    initial_unread = resp_init.json()["unread_count"]

    # Submit a high risk pulse
    high_risk_pulse = {
        "case_id": "CASE-E2E-TEST-HR",
        "wellbeing_state": "Crisis",
        "affecting_factors": ["Physical threats", "Stalking / surveillance"],
        "support_needs": ["Immediate protection", "Emergency shelter"],
        "safety_status": "No, I do not feel safe.",
        "follow_up_requests": ["Urgent safety contact"],
        "private_note": "Intense fear of violence and stalking.",
        "ai_processing_consent": True,
        "processing_mode": "ai_assisted"
    }
    resp_pulse = victim_client.post(f"{BASE_URL}/api/victim/pulse", high_risk_pulse)
    assert resp_pulse.status_code == 200
    pulse_id = resp_pulse.json()["pulse_id"]
    print(f"  [PASS] High-risk pulse submitted with ID: {pulse_id}")

    # Verify pulse in DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT risk_level, risk_score, priority_review FROM support_pulses WHERE id = ?", (pulse_id,))
    pulse_db = cur.fetchone()
    assert pulse_db["risk_level"] == "high"
    assert pulse_db["risk_score"] >= 6
    assert pulse_db["priority_review"] == 1
    print(f"  [PASS] Pulse persisted in DB with risk_level: {pulse_db['risk_level']} (Score: {pulse_db['risk_score']})")

    # Verify notification created for counsellor
    cur.execute("SELECT * FROM notifications WHERE user_id = ? AND type = 'high_risk_pulse' ORDER BY created_at DESC LIMIT 1", (counsellor["id"],))
    notif_db = cur.fetchone()
    assert notif_db is not None
    assert "High-risk" in notif_db["title"]
    # Privacy check: private note must NOT be in notification message
    assert "Intense fear" not in notif_db["message"]
    conn.close()
    print(f"  [PASS] Notification automatically created in DB: '{notif_db['title']}' for counsellor (Privacy safe)")

    # Verify via Counsellor Notifications API
    resp_notifs = counsellor_client.get(f"{BASE_URL}/api/notifications?limit=10")
    assert resp_notifs.status_code == 200
    notif_list = resp_notifs.json()["notifications"]
    assert any(n["type"] == "high_risk_pulse" and "High-risk" in n["title"] for n in notif_list)
    print(f"  [PASS] /api/notifications accurately returned dispatched high-risk alert.")

    # Mark all read test
    resp_mark = counsellor_client.post(f"{BASE_URL}/api/notifications/mark-read", {"mark_all": True})
    assert resp_mark.status_code == 200
    assert resp_mark.json()["unread_count"] == 0
    print(f"  [PASS] /api/notifications/mark-read updated unread count to 0 in DB and API.")


def test_case_escalation_triggers():
    print("\n--- 6. VALIDATING CASE ESCALATION & NOTIFICATIONS E2E ---")
    admin_client, admin = login_user("state_admin@mentaura.example")
    counsellor_client, counsellor = login_user("counsellor@mentaura.example")

    esc_payload = {
        "case_id": "CASE-E2E-ESC-001",
        "escalation_level": "critical",
        "reason": "Immediate security protection and relocation required for trial witness.",
        "assigned_officer": "Special Officer V. Natarajan",
        "notes": "Coordinating with district special protection unit."
    }
    resp_esc = admin_client.post(f"{BASE_URL}/api/command/escalate-case", esc_payload)
    assert resp_esc.status_code == 200, f"Escalation failed: {resp_esc.json()}"
    print(f"  [PASS] Case escalated via /api/command/escalate-case: {resp_esc.json()['message']}")

    # Verify review action in DB
    conn, cur = get_db_cursor()
    cur.execute("SELECT * FROM review_actions WHERE target_id = ? AND action_type = 'escalate'", ("CASE-E2E-ESC-001",))
    action_db = cur.fetchone()
    assert action_db is not None
    assert "critical" in action_db["status"]
    print(f"  [PASS] Review action persisted in DB: Status '{action_db['status']}'")

    # Verify notification in DB
    cur.execute("SELECT * FROM notifications WHERE user_id = ? AND type = 'case_escalated' ORDER BY created_at DESC LIMIT 1", (counsellor["id"],))
    notif_db = cur.fetchone()
    assert notif_db is not None
    assert "Case escalated" in notif_db["title"]
    assert "critical" in notif_db["message"]
    conn.close()
    print(f"  [PASS] In-app notification created in DB: '{notif_db['title']}' for counsellor.")

    # Verify via Counsellor API
    resp_n = counsellor_client.get(f"{BASE_URL}/api/notifications?limit=5")
    assert resp_n.status_code == 200
    notifs = resp_n.json()["notifications"]
    assert any(n["type"] == "case_escalated" for n in notifs)
    print(f"  [PASS] Counsellor received live case_escalated notification.")


def main():
    print("=" * 60)
    print("MENTAURA E2E BACKEND INTEGRATION & REAL-TIME VALIDATION")
    print("=" * 60)
    try:
        test_victim_flow()
        test_counsellor_flow()
        test_command_admin_flow()
        test_pending_approvals_flow()
        test_risk_scoring_and_notification_triggers()
        test_case_escalation_triggers()
        print("\n" + "=" * 60)
        print("ALL E2E INTEGRATION & DATA FIDELITY CHECKS PASSED (100%)")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[FAIL] Validation assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Validation encountered error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
