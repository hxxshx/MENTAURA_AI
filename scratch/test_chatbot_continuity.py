import requests
import json

def test_chatbot():
    s = requests.Session()
    login_res = s.post(
        'http://127.0.0.1:8000/api/auth/login',
        json={'email': 'victim@mentaura.example', 'password': 'Mentaura@2026'}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    data = login_res.json()
    token = data.get('access_token') or s.cookies.get('access_token') or ''
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    print('=== TEST 1: Greeting "hi" ===')
    r1 = s.post(
        'http://127.0.0.1:8000/api/victim/chatbot/message',
        json={'message': 'hi', 'language': 'EN', 'conversation_history': []},
        headers=headers
    ).json()
    print('Bot reply:', r1.get('bot_reply'))
    print('Severity:', r1.get('severity_level'))
    print('Distress score:', r1.get('distress_score'))
    print('Coping techniques count:', len(r1.get('coping_techniques', [])))
    print('Suggested actions count:', len(r1.get('suggested_actions', [])))
    assert len(r1.get('coping_techniques', [])) == 0, "Greeting should not return coping techniques!"
    assert len(r1.get('suggested_actions', [])) == 0, "Greeting should not return suggested action pills!"

    print('\n=== TEST 2: Multi-Turn Conversational Continuity ===')
    # Turn 1: "I am not feeling well"
    r2_1 = s.post(
        'http://127.0.0.1:8000/api/victim/chatbot/message',
        json={'message': 'I am not feeling well', 'language': 'EN', 'conversation_history': []},
        headers=headers
    ).json()
    print('Turn 1 User: "I am not feeling well"')
    print('Turn 1 Bot reply:', r2_1.get('bot_reply'))
    print('Turn 1 Severity:', r2_1.get('severity_level'))

    # Turn 2: "due to my family" with history
    hist = [
        {'role': 'user', 'content': 'I am not feeling well'},
        {'role': 'bot', 'content': r2_1.get('bot_reply')}
    ]
    r2_2 = s.post(
        'http://127.0.0.1:8000/api/victim/chatbot/message',
        json={'message': 'due to my family', 'language': 'EN', 'conversation_history': hist},
        headers=headers
    ).json()
    print('\nTurn 2 User: "due to my family"')
    print('Turn 2 Bot reply:', r2_2.get('bot_reply'))
    print('Turn 2 Severity:', r2_2.get('severity_level'))
    print('Turn 2 Elevation prompt:', r2_2.get('elevation_prompt'))
    print('Turn 2 Counsellor Contact:', r2_2.get('escalation_contact', {}).get('officer_name'))
    assert r2_2.get('severity_level') == 'medium', f"Expected medium severity for continuity, got {r2_2.get('severity_level')}"

    print('\n=== TEST 3: Explicit Exercise Request ===')
    r3 = s.post(
        'http://127.0.0.1:8000/api/victim/chatbot/message',
        json={'message': 'Guide me through quick 4-7-8 calm breathing exercises', 'language': 'EN', 'conversation_history': []},
        headers=headers
    ).json()
    print('Exercise Bot reply:', r3.get('bot_reply'))
    print('Exercise Coping count:', len(r3.get('coping_techniques', [])))
    assert len(r3.get('coping_techniques', [])) > 0, "Explicit request should return exercises!"

    print('\n=== ALL TESTS PASSED SUCCESSFULLY! ===')

if __name__ == '__main__':
    test_chatbot()
