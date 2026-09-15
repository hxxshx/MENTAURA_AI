"""
Automated Unit and Integration Tests for District & State Command Dashboards in Mentaura.
Tests authentication, role authorization, aggregate metrics, support breakdowns,
case stage distributions, priority escalations, and multi-district coordination summaries.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.review import ReviewAction

client = TestClient(app)


def get_session_cookie(email: str, password: str = "Mentaura@2026") -> str:
    """Helper to log in a user and retrieve their signed session cookie."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.cookies.get("mentaura_session")


# --------------------------------------------------------------------------
# 1. Access Control & Role Guard Tests
# --------------------------------------------------------------------------
def test_command_overview_unauthenticated():
    """Unauthenticated request must be rejected with 401 Unauthorized."""
    resp = client.get("/api/command/overview")
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()


def test_command_overview_forbidden_for_victim():
    """Victim role must NOT be permitted to view administrative command metrics."""
    cookie = get_session_cookie("victim@mentaura.example")
    resp = client.get("/api/command/overview", cookies={"mentaura_session": cookie})
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower()


def test_command_overview_forbidden_for_counsellor():
    """Counsellor role must NOT be permitted to view executive command dashboard."""
    cookie = get_session_cookie("counsellor@mentaura.example")
    resp = client.get("/api/command/overview", cookies={"mentaura_session": cookie})
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower()


def test_command_overview_authorized_district_authority():
    """District authority receives district-scoped overview metrics."""
    cookie = get_session_cookie("district@mentaura.example")
    resp = client.get("/api/command/overview?time_range=7d", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()
    
    assert "jurisdiction" in data
    assert data["jurisdiction"]["type"] == "district"
    assert "Chennai" in data["jurisdiction"]["name"]
    assert "overview" in data
    assert data["overview"]["new_pulses_7d"] >= 0
    assert data["overview"]["pending_requests"] >= 0
    assert data["overview"]["active_cases"] >= 0
    assert data["overview"]["active_interventions"] >= 0
    assert "administrator" in data
    assert data["administrator"]["verified_role"] == "district_authority"


def test_command_overview_authorized_state_admin():
    """State administrator receives state-scoped overview metrics."""
    # Ensure state admin user exists or create fixture
    db = SessionLocal()
    state_user = db.query(User).filter(User.email == "state_admin@mentaura.example").first()
    if not state_user:
        from backend.app.services.auth_service import hash_password
        state_user = User(
            full_name="Dr. Jayant Patil",
            email="state_admin@mentaura.example",
            password_hash=hash_password("Mentaura@2026"),
            requested_category="state_administrator",
            verified_role="state_administrator",
            account_status="active",
            email_verified=True
        )
        db.add(state_user)
        db.commit()
    db.close()

    cookie = get_session_cookie("state_admin@mentaura.example")
    resp = client.get("/api/command/overview?time_range=30d", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["jurisdiction"]["type"] == "state"
    assert "Tamil Nadu" in data["jurisdiction"]["name"]
    assert data["overview"]["active_cases"] > 50


# --------------------------------------------------------------------------
# 2. Support Type Breakdown & Case Stages Tests
# --------------------------------------------------------------------------
def test_metrics_by_support_type_authorized():
    """Verifies that 6 aid categories are reported with breakdowns."""
    cookie = get_session_cookie("district@mentaura.example")
    resp = client.get("/api/command/metrics-by-support-type", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "categories" in data
    assert len(data["categories"]) == 6
    categories = {c["category"] for c in data["categories"]}
    expected_categories = {"counselling", "legal_aid", "protection", "medical", "compensation", "rehabilitation"}
    assert expected_categories == categories

    for cat in data["categories"]:
        assert "total_30d" in cat
        assert "pending_count" in cat
        assert "in_progress_count" in cat
        assert "completed_count" in cat
        assert cat["total_30d"] == cat["pending_count"] + cat["in_progress_count"] + cat["completed_count"]


def test_cases_by_stage_authorized():
    """Verifies that active case distribution is categorized across procedural stages."""
    cookie = get_session_cookie("district@mentaura.example")
    resp = client.get("/api/command/cases-by-stage", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "stages" in data
    assert len(data["stages"]) >= 6
    for stage in data["stages"]:
        assert "stage_key" in stage
        assert "stage_name" in stage
        assert "case_count" in stage
        assert "status_color" in stage


# --------------------------------------------------------------------------
# 3. Priority Cases & Escalation Action Tests
# --------------------------------------------------------------------------
def test_priority_cases_authorized():
    """Verifies priority queue returns cases with masked identifiers."""
    cookie = get_session_cookie("district@mentaura.example")
    resp = client.get("/api/command/priority-cases?priority_only=true", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "priority_cases" in data
    assert len(data["priority_cases"]) > 0
    for case in data["priority_cases"]:
        assert "***" in case["case_id_masked"]
        assert "****" in case["victim_masked"]
        assert case["urgency"] in ("critical", "urgent", "standard")
        assert "priority_reason" in case
        assert "assigned_officer" in case


def test_post_escalate_case_authorized():
    """District authority can escalate a priority case and log it in review_actions."""
    cookie = get_session_cookie("district@mentaura.example")
    payload = {
        "case_id": "case-mh-08942",
        "escalation_level": "critical",
        "reason": "Immediate security detail required for scheduled court deposition",
        "assigned_officer": "Deputy Commissioner of Police",
        "notes": "Fast-tracked under Section 195A IPC witness protection mandate"
    }
    resp = client.post("/api/command/escalate-case", json=payload, cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["case_id"] == "case-mh-08942"
    assert data["escalation_level"] == "critical"
    assert "action_id" in data

    # Verify logged in database
    db = SessionLocal()
    action = db.query(ReviewAction).filter(ReviewAction.id == data["action_id"]).first()
    assert action is not None
    assert action.action_type == "escalate"
    assert "critical" in action.status
    db.close()


# --------------------------------------------------------------------------
# 4. District Summary & Static File Tests
# --------------------------------------------------------------------------
def test_district_summary_authorized():
    """Verifies multi-district comparison statistics."""
    cookie = get_session_cookie("district@mentaura.example")
    resp = client.get("/api/command/district-summary", cookies={"mentaura_session": cookie})
    assert resp.status_code == 200
    data = resp.json()

    assert "districts" in data
    assert len(data["districts"]) >= 4
    district_names = [d["district_name"] for d in data["districts"]]
    assert "Chennai District" in district_names
    assert "Coimbatore District" in district_names


def test_static_command_pages_accessible():
    """Ensures command-dashboard.html and associated assets are cleanly servable."""
    resp = client.get("/command-dashboard.html")
    assert resp.status_code == 200
    assert "Command Dashboard" in resp.text
    assert "MENTAURA" in resp.text


def test_state_admin_can_access_command_dashboard_and_district_summary():
    """
    TASK 14 Automated Verification:
    1. Ensure state admin user exists and is active.
    2. Log in as state admin.
    3. Call GET /api/command/overview and GET /api/command/district-summary.
    4. Assert HTTP 200 and state-level aggregated metrics and district summary table.
    5. Assert that unauthorized roles (victim, counsellor) receive HTTP 403.
    """
    # 1. Ensure state admin user exists
    db = SessionLocal()
    from backend.app.services.auth_service import hash_password
    state_user = db.query(User).filter(User.email == "stateadmin@mentaura.example").first()
    if not state_user:
        state_user = User(
            full_name="State Director S. Mukherjee",
            email="stateadmin@mentaura.example",
            password_hash=hash_password("Mentaura@2026"),
            requested_category="state_administrator",
            verified_role="state_administrator",
            account_status="active",
            email_verified=True
        )
        db.add(state_user)
        db.commit()
    db.close()

    # 2. Login as State Admin
    login_resp = client.post("/api/auth/login", json={
        "email": "stateadmin@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["redirect_url"] == "command-dashboard.html"
    state_cookie = login_resp.cookies.get("mentaura_session")

    # 3. Call Overview as State Admin
    overview_resp = client.get("/api/command/overview", cookies={"mentaura_session": state_cookie})
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert ov_data["jurisdiction"]["type"] == "state"
    assert "Tamil Nadu" in ov_data["jurisdiction"]["name"]
    assert "overview" in ov_data
    assert "new_pulses_7d" in ov_data["overview"]
    assert "pending_requests" in ov_data["overview"]
    assert "active_cases" in ov_data["overview"]
    assert "active_interventions" in ov_data["overview"]
    assert ov_data["overview"]["active_cases"] >= 50

    # 4. Call District Summary as State Admin
    dist_resp = client.get("/api/command/district-summary", cookies={"mentaura_session": state_cookie})
    assert dist_resp.status_code == 200
    dist_data = dist_resp.json()
    assert dist_data["is_state_view"] is True
    assert len(dist_data["districts"]) >= 5
    for d in dist_data["districts"]:
        assert "district_name" in d
        assert "new_pulses_30d" in d
        assert "pending_requests" in d
        assert "active_cases" in d
        assert "active_interventions" in d
        assert "status" in d

    # 5. Assert Non-Admin Roles Receive 403 Forbidden
    victim_cookie = get_session_cookie("victim@mentaura.example")
    counsellor_cookie = get_session_cookie("counsellor@mentaura.example")

    assert client.get("/api/command/district-summary", cookies={"mentaura_session": victim_cookie}).status_code == 403
    assert client.get("/api/command/district-summary", cookies={"mentaura_session": counsellor_cookie}).status_code == 403


def test_state_admin_demo_flow_sanity():
    """
    TASK 14-POLISH Sanity Verification:
    Full state admin interactive demonstration flow:
    1. Login as State Admin
    2. Retrieve overview metrics (state scope, non-zero cases/interventions)
    3. Retrieve district summary (multiple districts with comparative indicators)
    4. Retrieve priority cases
    5. Perform case escalation and assert ReviewAction record creation
    """
    cookie = get_session_cookie("stateadmin@mentaura.example")

    # 1. Overview
    ov_resp = client.get("/api/command/overview?time_range=7d", cookies={"mentaura_session": cookie})
    assert ov_resp.status_code == 200
    ov_data = ov_resp.json()
    assert ov_data["jurisdiction"]["type"] == "state"
    assert ov_data["overview"]["active_cases"] > 0
    assert ov_data["overview"]["active_interventions"] > 0

    # 2. District Summary
    dist_resp = client.get("/api/command/district-summary", cookies={"mentaura_session": cookie})
    assert dist_resp.status_code == 200
    dist_data = dist_resp.json()
    assert len(dist_data["districts"]) >= 4

    # 3. Priority Cases
    priority_resp = client.get("/api/command/priority-cases", cookies={"mentaura_session": cookie})
    assert priority_resp.status_code == 200
    cases_data = priority_resp.json()
    cases = cases_data["priority_cases"]
    assert len(cases) > 0
    test_case_id = cases[0]["id"]

    # 4. Escalate Case Action
    escalate_payload = {
        "case_id": test_case_id,
        "escalation_level": "inter_district",
        "reason": "Cross-district victim relocation and witness protection requisition",
        "assigned_officer": "State Director S. Mukherjee",
        "notes": "Coordinating between Nagpur and Pune District Magistrates"
    }
    esc_resp = client.post("/api/command/escalate-case", json=escalate_payload, cookies={"mentaura_session": cookie})
    assert esc_resp.status_code == 200
    esc_data = esc_resp.json()
    assert esc_data["success"] is True
    assert esc_data["escalation_level"] == "inter_district"

    # Verify Action in Database
    db = SessionLocal()
    action = db.query(ReviewAction).filter(ReviewAction.id == esc_data["action_id"]).first()
    assert action is not None
    assert action.target_type == "case_escalation"
    assert "INTER_DISTRICT" in action.notes
    db.close()


