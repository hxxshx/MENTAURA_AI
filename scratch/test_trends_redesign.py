import re

with open("distress-trends.html", "r", encoding="utf-8") as f:
    html = f.read()

with open("js/trends.js", "r", encoding="utf-8") as f:
    js = f.read()

# Check key IDs and classes in HTML
required_ids = [
    "sentinelCard",
    "sentinelBadge",
    "sentinelBadgeText",
    "sentinelIconWrap",
    "sentinelIcon",
    "sentinelHeadline",
    "sentinelNarrative",
    "kpiRecoveryTitle",
    "kpiRecoveryBadge",
    "kpiRecoveryDesc",
    "kpiStreakVal",
    "stressTriggersList",
    "reliefAnchorsList",
    "distressChart",
    "toggleChartBtn",
    "chartCanvasContainer",
    "protectionModal",
    "closeProtectionModalBtn",
    "protectionActionForm",
    "camouflageOverlay",
    "sosModal"
]

missing = []
for req_id in required_ids:
    if f'id="{req_id}"' not in html and f"id='{req_id}'" not in html:
        missing.append(req_id)

print(f"Total checked: {len(required_ids)}")
if missing:
    print(f"MISSING IDs: {missing}")
else:
    print("ALL REQUIRED IDs PRESENT IN HTML!")

# Check tabs in nav
assert 'href="victim-home.html"' in html
assert 'href="checkin.html"' in html
assert 'href="distress-trends.html"' in html

# Check tab count
nav_links = re.findall(r'<a[^>]+class="nav-link[^"]*"[^>]*>([^<]+)</a>', html)
print(f"Universal Navigation links ({len(nav_links)}): {nav_links}")
assert len(nav_links) == 3, f"Expected 3 tabs, found {len(nav_links)}"
print("NAVIGATION TAB COUNT CONFIRMED: EXACTLY 3 TABS")
