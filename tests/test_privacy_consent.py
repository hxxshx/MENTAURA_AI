"""
Test Suite for Authenticated Victim Privacy & Consent Endpoint and Static Assets (TASK 11).
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_privacy_consent_unauthenticated():
    """Unauthenticated requests must be rejected with 401."""
    resp = client.get("/api/victim/privacy-consent")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_privacy_consent_forbidden_for_counsellor():
    """Official/counsellor roles must not access victim privacy records."""
    login_resp = client.post("/api/auth/login", json={
        "email": "counsellor@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/victim/privacy-consent", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 403
    assert "Access restricted" in resp.json()["detail"]


def test_privacy_consent_authorized_victim():
    """Victim role must receive authentic privacy data with masked identifiers and truthful capabilities."""
    login_resp = client.post("/api/auth/login", json={
        "email": "victim@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/victim/privacy-consent", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "account" in data
    assert "processing_choice" in data
    assert "consent_records" in data
    assert "capabilities" in data
    assert "contact" in data

    # Verify account fields
    acc = data["account"]
    assert acc["role"] == "victim"
    assert acc["account_status"] == "active"
    assert "v****m@mentaura.example" in acc["email_masked"]

    # Verify capabilities truthfulness
    caps = data["capabilities"]
    assert caps["role_based_access"] is True
    assert caps["authenticated_sessions"] is True
    assert caps["support_pulse_consent"] is True
    assert caps["processing_choice"] is True
    assert caps["consent_withdrawal"] is False
    assert caps["data_export"] is False
    assert caps["data_deletion_request"] is False

    # Verify consent records
    assert len(data["consent_records"]) >= 1
    consent0 = data["consent_records"][0]
    assert consent0["consent_given"] is True
    assert consent0["status"] == "Active"


def test_privacy_consent_authorized_witness():
    """Witness role must receive authentic privacy data."""
    login_resp = client.post("/api/auth/login", json={
        "email": "witness@mentaura.example",
        "password": "Mentaura@2026"
    })
    assert login_resp.status_code == 200
    session_cookie = login_resp.cookies.get("mentaura_session")

    resp = client.get("/api/victim/privacy-consent", cookies={"mentaura_session": session_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["account"]["role"] == "witness"


def test_static_privacy_pages_accessible():
    """Verify that frontend HTML and CSS files are properly served."""
    resp_html = client.get("/privacy-consent.html")
    assert resp_html.status_code == 200
    assert "Privacy &amp; Consent" in resp_html.text or "Privacy & Consent" in resp_html.text

    resp_policy = client.get("/privacy-policy.html")
    assert resp_policy.status_code == 200
    assert "Privacy Policy" in resp_policy.text

    resp_terms = client.get("/terms-of-service.html")
    assert resp_terms.status_code == 200
    assert "Terms of Service" in resp_terms.text

    resp_css = client.get("/css/privacy.css")
    assert resp_css.status_code == 200
    assert "privacy-app-wrapper" in resp_css.text

    resp_js = client.get("/js/privacy.js")
    assert resp_js.status_code == 200
    assert "loadPrivacyConsentData" in resp_js.text
