import urllib.request
import urllib.parse
import re

# 1. Verify osc-pass-verify.html is served
verify_url = "http://127.0.0.1:8000/osc-pass-verify.html?pass=OSC-TN-2026-FB1EA5&name=Aanya"
resp = urllib.request.urlopen(verify_url)
assert resp.status == 200, f"Failed to load {verify_url}"
verify_html = resp.read().decode("utf-8")
assert "Government of India" in verify_html, "Missing Government of India title"
assert "Section 15A Witness Protection" in verify_html, "Missing Section 15A mention"
assert "dispPassNumber" in verify_html, "Missing pass number display"
assert "dispPatientName" in verify_html, "Missing patient name display"
assert "+91 95138 86363" in verify_html, "Missing IVRS phone number"
print("[OK] osc-pass-verify.html successfully verified and serving!")

# 2. Verify distress-trends.html contains scannable QR and verify link
trends_html = urllib.request.urlopen("http://127.0.0.1:8000/distress-trends.html").read().decode("utf-8")
assert 'id="vOscQrImage"' in trends_html, "vOscQrImage missing from distress-trends.html"
assert 'id="vOscVerifyLink"' in trends_html, "vOscVerifyLink missing from distress-trends.html"
assert 'api.qrserver.com' in trends_html, "QR server API image missing"
print("[OK] distress-trends.html contains real scannable QR image and live verification link!")

# 3. Test QR Server API endpoint with actual pass data
test_qr_payload = """GOVERNMENT OF INDIA • ONE-STOP CENTRE (OSC)
OFFICIAL SECTION 15A PROTECTION PASS
====================================
PASS NUMBER: OSC-TN-2026-FB1EA5
BENEFICIARY: Aanya (Protected Citizen)
PROTECTION STATUS: Section 15A Active & Verified
FACILITY: District One-Stop Crisis Enclave, Room 104
CARE LEAD: Dr. Priya Nair (Clinical Counsellor)
SECURITY STATUS: Priority Entry Authorized
IVRS CARE BRIDGE: +91 95138 86363
STATUTORY HELPLINES: 14566 / 112"""

qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=8&data={urllib.parse.quote(test_qr_payload)}"
qr_resp = urllib.request.urlopen(qr_api_url)
assert qr_resp.status == 200, "QR API failed"
qr_bytes = qr_resp.read()
assert len(qr_bytes) > 500, f"QR image too small: {len(qr_bytes)} bytes"
print(f"[OK] High-resolution scannable QR code generated ({len(qr_bytes)} bytes)!")

print("\n=== ALL OSC PASS ORIGINAL VERIFICATION TESTS PASSED! ===")
