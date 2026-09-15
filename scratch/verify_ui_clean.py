import urllib.request
import re

html = urllib.request.urlopen("http://127.0.0.1:8000/distress-trends.html").read().decode("utf-8")

# 1. Verify nav bar Counsellor Consultation has no icon
assert '<i class="fa-solid fa-comments"></i> Counsellor Consultation' not in html, "Found message icon in nav bar!"
assert 'Counsellor Consultation</a>' in html, "Counsellor Consultation link missing!"
print("[OK] Verified nav bar has Counsellor Consultation with NO message icon")

# 2. Verify hero counters strip has NO number badges
m = re.search(r'<div class="hero-counters-strip".*?</div>', html, re.DOTALL)
assert m, "hero-counters-strip not found"
strip_html = m.group(0)
assert "hero-counter-badge" not in strip_html, f"Found badge in hero-counters-strip: {strip_html}"
assert "cntVictim" not in strip_html, f"Found cntVictim in hero-counters-strip: {strip_html}"
assert "Message Consultation" in strip_html and "Video Consultation" in strip_html and "Counselling Requests" in strip_html
print("[OK] Verified hero-counters-strip has all 3 consultation options with NO number badges")

# 3. Verify counsellor workspace still has its badges
c_html = urllib.request.urlopen("http://127.0.0.1:8000/counsellor-workspace.html").read().decode("utf-8")
assert "cntDirectMessages" in c_html, "cntDirectMessages missing from counsellor workspace"
assert "cntScheduledVideo" in c_html, "cntScheduledVideo missing from counsellor workspace"
assert "cntPendingRequests" in c_html, "cntPendingRequests missing from counsellor workspace"
print("[OK] Verified counsellor workspace badges are intact and untouched")

# 3b. Verify IVRS button is a <button> with oval pill styling
assert '<button type="button" class="btn btn-ivrs-call"' in html, "Button element missing"
assert "border-radius: 9999px" in html, "Oval border-radius missing"
assert "IVRS Call: +91 95138 86363" in html, "IVRS Call text missing"
assert "tel:+919513886363" in html, "tel dial action missing"
print("[OK] Verified IVRS button is a <button> with oval pill styling around +91 95138 86363")

# 4. Verify all victim pages header nav bar
victim_pages = [
    "victim-home.html",
    "case-journey.html",
    "checkin.html",
    "my-support.html",
    "privacy-consent.html",
    "resources.html"
]

for page in victim_pages:
    page_html = urllib.request.urlopen(f"http://127.0.0.1:8000/{page}").read().decode("utf-8")
    # Check desktop navbar link
    m_nav = re.search(r'id="nav-victim-trends"[^>]*>([^<]*)<', page_html)
    if not m_nav:
        m_nav = re.search(r'>([^<]*)</a>\s*</li>\s*</ul>\s*</nav>', page_html)
    assert "Counsellor Consultation" in m_nav.group(0), f"Desktop nav mismatch in {page}"
    assert "<i" not in m_nav.group(0), f"Found icon in desktop nav of {page}"

    # Check mobile navbar link
    m_mob = re.search(r'class="mobile-nav-link[^"]*"[^>]*>([^<]*)<', page_html)
    # Ensure any mobile link to distress-trends has no icon
    m_mob_dt = re.search(r'<a href="distress-trends\.html" class="mobile-nav-link[^"]*">([^<]*)</a>', page_html)
    assert m_mob_dt, f"Mobile nav link missing in {page}"
    assert m_mob_dt.group(1).strip() == "Counsellor Consultation", f"Mobile nav link contains icon in {page}: {m_mob_dt.group(0)}"
    print(f"[OK] Verified {page} navbar has clean Counsellor Consultation link (no icon)")

print("\n=== ALL UI VERIFICATIONS PASSED CLEANLY! ===")
