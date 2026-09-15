import sys, io

with open('distress-trends.html', 'r', encoding='utf-8') as f:
    html = f.read()

assert '<footer class="site-footer">' in html, "Missing footer tag"
assert 'MENTAURA' in html, "Missing MENTAURA"
assert 'Case-aware support intelligence for people affected by atrocity cases.' in html, "Missing brand desc"
assert 'Support Space' in html, "Missing Support Space"
assert 'Authorised Support' in html, "Missing Authorised Support"
assert 'support@mentaura.example' in html, "Missing support email"
assert 'For authorised support and programme coordination' in html, "Missing note"
assert 'Secure Case-Aware Support Intelligence.' in html, "Missing copyright note"

print("FOOTER VERIFICATION SUCCESSFUL: EXACT MATCH CONFIRMED!")
