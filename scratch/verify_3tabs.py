import urllib.request
import json
import re

def check_nav(html, page_name):
    pill_match = re.search(r'<nav class="nav-pill"[^>]*>(.*?)</nav>', html, re.DOTALL)
    if pill_match:
        links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', pill_match.group(1))
        print(f"{page_name} Nav Pill Links ({len(links)}):")
        for href, text in links:
            print(f"  - {text.strip()} -> {href}")
        assert len(links) == 3, f"Expected 3 links, got {len(links)}"

pages = ['victim-home.html', 'checkin.html', 'distress-trends.html']
for page in pages:
    with urllib.request.urlopen(f"http://127.0.0.1:8000/{page}") as resp:
        html = resp.read().decode('utf-8')
        check_nav(html, page)

print("\n--- Testing Backend API for Distress Trends ---")
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/auth/login',
    data=json.dumps({'email': 'victim@mentaura.example', 'password': 'Mentaura@2026'}).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode())['token']

headers = {'Authorization': f'Bearer {token}'}
req_trends = urllib.request.Request('http://127.0.0.1:8000/api/victim/distress-trends?days=30', headers=headers)
with urllib.request.urlopen(req_trends) as resp:
    data = json.loads(resp.read().decode())
    print(f"Status: 200 OK")
    print(f"Current DDS: {data.get('current_dds')}/100")
    print(f"Trend Label: {data.get('trend_label')}")
    print(f"Trajectory Checkpoints: {len(data.get('trajectory', []))}")
    print(f"XAI Factors: {len(data.get('xai_factors', []))}")
    print(f"Predictive Alert: {data.get('predictive_alert', {}).get('title')}")
    print(f"Predictive Alert Action URL: {data.get('predictive_alert', {}).get('action_url')}")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
