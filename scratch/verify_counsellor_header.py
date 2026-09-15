import re

with open("counsellor-workspace.html", "r", encoding="utf-8") as f:
    c_html = f.read()

with open("victim-home.html", "r", encoding="utf-8") as f:
    v_html = f.read()

with open("css/counsellor.css", "r", encoding="utf-8") as f:
    c_css = f.read()

# 1. Check header in counsellor-workspace.html
header_match = re.search(r'<header[^>]*>(.*?)</header>', c_html, re.DOTALL)
assert header_match, "Header not found in counsellor-workspace.html"
header_content = header_match.group(1)

# Check tabs inside header
assert "Review Workspace" in header_content, "Review Workspace must be in header"
assert "district-command-centre.html" not in header_content, "district-command-centre should not be in header"
assert "Command Centre" not in header_content, "Command Centre text should not be in header"
assert "state-overview.html" not in header_content, "state-overview should not be in header"
assert "State Overview" not in header_content, "State Overview text should not be in header"
assert "resources.html" not in header_content, "resources.html should not be in header"

# Check nav-link count in header
nav_links = re.findall(r'<a[^>]+class="nav-link[^"]*"[^>]*>([^<]+)</a>', header_content)
print(f"Counsellor Header Nav Links ({len(nav_links)}):", nav_links)
assert len(nav_links) == 1, f"Expected exactly 1 nav-link, got {len(nav_links)}"
assert nav_links[0].strip() == "Review Workspace"

# Check mobile drawer links
mobile_drawer_match = re.search(r'<div[^>]+id="mobileMenuDrawer"[^>]*>(.*?)</div>\s*</header>', c_html, re.DOTALL)
assert mobile_drawer_match, "Mobile drawer not found"
mobile_links = re.findall(r'<a[^>]+class="mobile-nav-link[^"]*"[^>]*>([^<]+)</a>', mobile_drawer_match.group(1))
print(f"Counsellor Mobile Nav Links ({len(mobile_links)}):", mobile_links)
assert len(mobile_links) == 1, f"Expected exactly 1 mobile nav-link, got {len(mobile_links)}"
assert mobile_links[0].strip() == "Review Workspace"

# 2. Check hero banner in counsellor-workspace.html
hero_match = re.search(r'<section[^>]+class="counsellor-hero-banner"[^>]*>(.*?)</section>', c_html, re.DOTALL)
assert hero_match, "Hero banner not found"
hero_content = hero_match.group(1)
assert "counsellor-greeting-title" in hero_content
assert "counsellor-greeting-sub" in hero_content
assert "counsellor-trust-badge" in hero_content
assert "Review Workspace" in hero_content
assert "Role-authorized oversight and privacy-governed case coordination." in hero_content

# 3. Check CSS
assert "var(--gradient-hero" in c_css, "Counsellor CSS must use var(--gradient-hero)"
assert ".counsellor-hero-banner" in c_css
assert ".counsellor-greeting-title" in c_css

print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
