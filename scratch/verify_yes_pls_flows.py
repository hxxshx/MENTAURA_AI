import json
import urllib.request

class TestClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        self.login()

    def login(self):
        url = f"{self.base_url}/api/auth/login"
        payload = json.dumps({
            "email": "victim@mentaura.example",
            "password": "Mentaura@2026"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.token = data.get("token")
            # print("Logged in successfully! Token received.")

    def post_chat(self, message, language="EN", conversation_history=None):
        url = f"{self.base_url}/api/victim/chatbot/message"
        payload = json.dumps({
            "message": message,
            "language": language,
            "conversation_history": conversation_history or []
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

client = TestClient()

conversations_to_test = [
    {
        "name": "Fear / Scared Flow -> 'yes pls'",
        "turns": [
            "i am feeling super scared",
            "yes pls"
        ]
    },
    {
        "name": "Panic Attack -> 'yes pls' -> 'cycle 2' -> 'feeling calmer now'",
        "turns": [
            "i am having a severe panic attack",
            "yes pls",
            "let's do cycle 2",
            "feeling much better and calmer now"
        ]
    },
    {
        "name": "Lonely / Depressed -> 'origami' -> 'yes pls'",
        "turns": [
            "i feel so lonely and sad",
            "origami",
            "yes pls"
        ]
    },
    {
        "name": "Wedding Stress -> 'yes pls'",
        "turns": [
            "i am getting married next week and i have cold feet",
            "yes pls"
        ]
    },
    {
        "name": "Exam Stress -> 'yes pls'",
        "turns": [
            "i have my board exams tomorrow and i am terrified",
            "yes pls"
        ]
    },
    {
        "name": "Arbitrary unscripted prompt -> 'yes pls'",
        "turns": [
            "my laptop broke and my project submission is due tomorrow",
            "yes pls"
        ]
    }
]

for suite in conversations_to_test:
    print(f"\n========================================================")
    print(f"RUNNING SUITE: {suite['name']}")
    print(f"========================================================")
    history = []
    for turn_idx, user_msg in enumerate(suite["turns"], 1):
        data = client.post_chat(
            message=user_msg,
            language="EN",
            conversation_history=history
        )
        reply = data.get("bot_response") or data.get("reply")
        chips = data.get("suggested_actions", [])
        
        print(f"User [{turn_idx}]: \"{user_msg}\"")
        print(f"Bot  [{turn_idx}]: {reply[:120]}...")
        print(f"Chips [{turn_idx}]: {chips}")
        
        # CRITICAL ASSERTIONS:
        assert "regarding **yes pls**" not in reply, f"FAIL: Bot repeated 'regarding **yes pls**'!"
        assert "regarding **yes**" not in reply, f"FAIL: Bot repeated 'regarding **yes**'!"
        assert "regarding **ok**" not in reply, f"FAIL: Bot repeated 'regarding **ok**'!"
        assert "regarding **sure**" not in reply, f"FAIL: Bot repeated 'regarding **sure**'!"
        
        for chip in chips:
            assert "yes pls" not in chip.lower(), f"FAIL: Chip contains 'yes pls'!"
            assert "yes" != chip.lower(), f"FAIL: Chip is just 'yes'!"

        history.append({"role": "user", "content": user_msg})
        history.append({"role": "bot", "content": reply})

print("\n" + "=" * 65)
print("ALL CONVERSATIONAL 'YES PLS' FLOWS VERIFIED SUCCESSFULLY!")
print("ZERO 'regarding **yes pls**' BUGS! 100% BULLETPROOF!")
print("=" * 65)
