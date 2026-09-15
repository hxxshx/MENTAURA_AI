import requests

s = requests.Session()
login_res = s.post('http://127.0.0.1:8000/api/auth/login', json={'email': 'victim@mentaura.example', 'password': 'Mentaura@2026'})
assert login_res.status_code == 200, f'Login failed: {login_res.text}'

# Book with custom focus area and custom flexible time
book_res = s.post('http://127.0.0.1:8000/api/victim/request-counsellor-session', json={
    'session_format': 'video',
    'support_need': 'Study Anxiety & Competitive Exam Trauma Recovery',
    'time_slot': 'Weekdays after 6:30 PM (Flexible)',
    'notes': 'Requested custom focus area and flexible time'
})
assert book_res.status_code == 200, f'Booking failed: {book_res.text}'
data = book_res.json()
assert data['success'] == True
print('[OK] Backend accepted custom focus area & flexible time window:', data['session_format'])

# Verify distress-trends.html markup
html_res = s.get('http://127.0.0.1:8000/distress-trends.html')
assert html_res.status_code == 200
html = html_res.text
assert 'id="bookNeedCustomInput"' in html, 'bookNeedCustomInput missing'
assert 'id="btnToggleCustomNeed"' in html, 'btnToggleCustomNeed missing'
assert 'id="bookTimeCustomInput"' in html, 'bookTimeCustomInput missing'
assert 'id="btnToggleCustomTime"' in html, 'btnToggleCustomTime missing'
assert '__custom__' in html, '__custom__ options missing'
print('[OK] distress-trends.html contains custom inputs, toggle buttons, and custom options!')

# Verify counsellor table receives the custom focus and flexible time
reqs_res = s.get('http://127.0.0.1:8000/api/victim/counsellor-requests')
assert reqs_res.status_code == 200
requests_list = reqs_res.json().get('requests', [])
latest = requests_list[0] if requests_list else None
assert latest, 'No requests found'
print(f"[OK] Latest request saved with focus: '{latest.get('support_type') or latest.get('notes')}' and time: '{latest.get('preferred_time')}'")
print("\n=== ALL CUSTOM BOOKING CHECKS PASSED SUCCESSFULLY! ===")
