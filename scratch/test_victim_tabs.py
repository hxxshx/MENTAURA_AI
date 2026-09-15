import requests

s = requests.Session()
login_res = s.post('http://127.0.0.1:8000/api/auth/login', json={'email': 'victim@mentaura.example', 'password': 'Mentaura@2026'})
assert login_res.status_code == 200, f'Login failed: {login_res.text}'
print('Logged in successfully, cookies:', s.cookies.get_dict())

# 1. Fetch requests
req_res = s.get('http://127.0.0.1:8000/api/victim/counsellor-requests')
assert req_res.status_code == 200, f'Fetch requests failed: {req_res.text}'
print('Counsellor requests fetched:', req_res.json()['total'])

# 2. Book a session
book_res = s.post('http://127.0.0.1:8000/api/victim/request-counsellor-session', json={
    'session_format': 'in_person',
    'support_need': 'Upcoming Court Hearing Anxiety',
    'time_slot': 'Today Afternoon (2:00 PM - 5:00 PM)',
    'notes': 'Section 15A safe court escort coordination'
})
assert book_res.status_code == 200, f'Booking failed: {book_res.text}'
book_data = book_res.json()
print('Session booked:', book_data['session_format'], 'Pass:', book_data.get('pass_code'))

# 3. Connect with any available counsellor
conn_res = s.post('http://127.0.0.1:8000/api/victim/connect-available-counsellor')
assert conn_res.status_code == 200, f'Connect failed: {conn_res.text}'
conn_data = conn_res.json()
print('Connect available counsellor:', conn_data['counsellor_name'], 'Room:', conn_data['room_id'])

# 4. Fetch HTML and check elements
html_res = s.get('http://127.0.0.1:8000/distress-trends.html')
assert html_res.status_code == 200
html_text = html_res.text
assert 'id="mobileMenuDrawer"' in html_text, 'Missing mobileMenuDrawer'
assert 'data-target-tab="messages"' in html_text, 'Missing messages tab'
assert 'data-target-tab="video"' in html_text, 'Missing video tab'
assert 'data-target-tab="requests"' in html_text, 'Missing requests tab'
assert 'id="panel-messages"' in html_text, 'Missing panel-messages'
assert 'id="panel-video"' in html_text, 'Missing panel-video'
assert 'id="panel-requests"' in html_text, 'Missing panel-requests'
assert 'btnConnectAnyCounsellor' in html_text, 'Missing btnConnectAnyCounsellor'
assert 'btnToggleRequestForm' in html_text, 'Missing btnToggleRequestForm'
print('ALL VICTIM UI & ENDPOINT CHECKS PASSED PERFECTLY!')
