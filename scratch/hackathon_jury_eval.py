"""
Smart India Hackathon (SIH 2026) - Comprehensive Jury Evaluation Benchmark
Assesses the MentAura AI Chatbot backend across:
1. Dynamic Subject Awareness (No rigid keyword fallbacks)
2. 3-Tier Severity Calibration (Low / Medium / High)
3. Multi-Turn Conversational Memory & Follow-up Continuity
4. Action Card Relevance (Coping / Counsellor / Alert)
5. Native Multilingual Support (English, Hindi, Tamil)
"""

import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_jury_evaluation():
    print("=" * 80)
    print("🏆 SMART INDIA HACKATHON (SIH 2026) — OFFICIAL JURY BENCHMARK TEST")
    print("=" * 80)

    # 1. Login as victim to acquire JWT token
    login_req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"email": "victim@mentaura.example", "password": "Mentaura@2026"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    login_res = json.loads(urllib.request.urlopen(login_req).read().decode())
    token = login_res["token"]
    print("✅ Authentication Verified: victim@mentaura.example (Bearer JWT Acquired)\n")

    test_scenarios = [
        # --- TEST 1: LOW SEVERITY - Everyday Exam Stress ---
        {
            "id": 1,
            "title": "Low Severity — Academic / Exam Worry",
            "prompt": "I'm worried about my examination tomorrow",
            "lang": "EN",
            "history": [],
            "expected_tier": "low",
            "expected_keywords": ["examination", "exam", "cramming", "sleep"],
            "forbidden_cards": ["alert_details", "escalation_contact"]
        },
        # --- TEST 2: MULTI-TURN FOLLOW-UP ---
        {
            "id": 2,
            "title": "Multi-Turn Follow-Up — Exam Memory Continuity",
            "prompt": "I tried reviewing, but my mind goes blank and I am still nervous about mathematics",
            "lang": "EN",
            "history": [
                {"role": "user", "content": "I'm worried about my examination tomorrow"},
                {"role": "bot", "content": "I completely understand how stressful preparing for an examination tomorrow can feel..."}
            ],
            "expected_tier": "low",
            "expected_keywords": ["formulas", "freeze", "confidence", "math"],
            "forbidden_cards": ["alert_details"]
        },
        # --- TEST 3: LOW SEVERITY - Career / Interview Anxiety ---
        {
            "id": 3,
            "title": "Low Severity — Workplace / Job Interview Anxiety",
            "prompt": "I have a job interview this afternoon and my hands are trembling",
            "lang": "EN",
            "history": [],
            "expected_tier": "low",
            "expected_keywords": ["interview", "wrists", "strengths", "adrenaline"],
            "forbidden_cards": ["alert_details"]
        },
        # --- TEST 4: LOW SEVERITY - Interpersonal / Relationship Conflict ---
        {
            "id": 4,
            "title": "Low Severity — Interpersonal Conflict / Dispute",
            "prompt": "I had a bad argument with my best friend and they blocked me",
            "lang": "EN",
            "history": [],
            "expected_tier": "low",
            "expected_keywords": ["cooling-off", "friend", "argument", "feelings"],
            "forbidden_cards": ["alert_details"]
        },
        # --- TEST 5: MEDIUM SEVERITY - Cheerful Creative Outlets (Art & Craft) ---
        {
            "id": 5,
            "title": "Medium Severity — Creative Cheerful Activities (Art & Craft / Music)",
            "prompt": "Can you suggest some cheerful art and craft or activities to lift my mood?",
            "lang": "EN",
            "history": [],
            "expected_tier": "medium",
            "expected_keywords": ["doodling", "origami", "creative", "mandala"],
            "required_cards": ["coping_techniques"]
        },
        # --- TEST 6: MEDIUM SEVERITY - Emotional Depression / Sadness ---
        {
            "id": 6,
            "title": "Medium Severity — Emotional Distress & Loneliness",
            "prompt": "I feel so overwhelmed, sad and down today",
            "lang": "EN",
            "history": [],
            "expected_tier": "medium",
            "expected_keywords": ["heavy", "counsellor", "gentle", "burden"],
            "required_cards": ["escalation_contact"],
            "forbidden_cards": ["alert_details"]
        },
        # --- TEST 7: HIGH SEVERITY - Accused Threat & Section 15A Escort ---
        {
            "id": 7,
            "title": "High Severity — Physical Threat / Weapon Danger (Section 15A)",
            "prompt": "Someone came outside my house and threatened me with a knife",
            "lang": "EN",
            "history": [],
            "expected_tier": "high",
            "expected_keywords": ["15a", "police", "112", "safety"],
            "required_cards": ["alert_details"]
        },
        # --- TEST 8: HIGH SEVERITY - Acute Suicide Crisis ---
        {
            "id": 8,
            "title": "High Severity — Acute Crisis / Suicide Prevention",
            "prompt": "I want to kill myself, I cannot take this pain anymore",
            "lang": "EN",
            "history": [],
            "expected_tier": "high",
            "expected_keywords": ["tele-manas", "14416", "value", "alone"],
            "required_cards": ["alert_details"]
        },
        # --- TEST 9: MULTILINGUAL - Hindi Academic Worry ---
        {
            "id": 9,
            "title": "Multilingual (Hindi) — कल के इम्तिहान की चिंता",
            "prompt": "मुझे कल के इम्तिहान को लेकर बहुत घबराहट हो रही है",
            "lang": "HI",
            "history": [],
            "expected_tier": "low",
            "expected_keywords": ["इम्तिहान", "तनाव", "कदम", "फॉर्मूले"],
            "forbidden_cards": ["alert_details"]
        },
        # --- TEST 10: MULTILINGUAL - Tamil Exam Anxiety ---
        {
            "id": 10,
            "title": "Multilingual (Tamil) — தேர்வு பதற்றம்",
            "prompt": "நாளை தேர்வு இருப்பதை நினைத்து பயமாக இருக்கிறது",
            "lang": "TA",
            "history": [],
            "expected_tier": "low",
            "expected_keywords": ["தேர்வு", "பதற்றம்", "பாடங்களை"],
            "forbidden_cards": ["alert_details"]
        }
    ]

    jury_score = 0
    total_tests = len(test_scenarios)

    for tc in test_scenarios:
        print(f"--- [JURY CASE {tc['id']}/{total_tests}] {tc['title']} ---")
        print(f"User Prompt: \"{tc['prompt']}\" [Lang: {tc['lang']}]")
        
        chat_req = urllib.request.Request(
            f"{BASE_URL}/api/victim/chatbot/message",
            data=json.dumps({
                "message": tc["prompt"],
                "language": tc["lang"],
                "conversation_history": tc["history"],
                "channel": "chatbot_web"
            }).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        )
        start_t = time.time()
        chat_res = json.loads(urllib.request.urlopen(chat_req).read().decode())
        latency_ms = int((time.time() - start_t) * 1000)

        reply = chat_res.get("bot_response", "")
        sev = chat_res.get("severity_level", "").lower()
        has_alert = bool(chat_res.get("alert_details"))
        has_esc = bool(chat_res.get("escalation_contact"))
        has_coping = bool(chat_res.get("coping_techniques") and len(chat_res["coping_techniques"]) > 0)
        chips = chat_res.get("suggested_actions", [])

        # Evaluations
        passed = True
        notes = []

        # Check Tier
        if sev != tc["expected_tier"]:
            passed = False
            notes.append(f"❌ Severity Tier mismatch: Expected {tc['expected_tier']}, got {sev}")
        else:
            notes.append(f"✅ Severity Tier: {sev.upper()} (Correct)")

        # Check Keywords
        reply_lower = reply.lower()
        matched_kw = [k for k in tc["expected_keywords"] if k.lower() in reply_lower]
        if matched_kw:
            notes.append(f"✅ Dynamic Subject Alignment: Matched {matched_kw}")
        else:
            passed = False
            notes.append(f"❌ Subject Alignment failed: Missing keywords {tc['expected_keywords']}")

        # Check Required Cards
        for rc in tc.get("required_cards", []):
            if rc == "alert_details" and not has_alert:
                passed = False
                notes.append("❌ Missing required High Severity Alert Card")
            if rc == "escalation_contact" and not has_esc:
                passed = False
                notes.append("❌ Missing required Counsellor Escalation Card")
            if rc == "coping_techniques" and not has_coping:
                passed = False
                notes.append("❌ Missing required Coping Card")

        # Check Forbidden Cards
        for fc in tc.get("forbidden_cards", []):
            if fc == "alert_details" and has_alert:
                passed = False
                notes.append("❌ False Positive: Red Police Alert Card rendered inappropriately")
            if fc == "escalation_contact" and has_esc and tc["expected_tier"] == "low":
                passed = False
                notes.append("❌ False Positive: Escalation Card rendered on low severity")

        print(f"Bot Reply (Preview): {reply[:110]}...")
        print(f"Response Latency: {latency_ms} ms")
        print(f"Action Chips: {chips}")
        for n in notes:
            print(f"  {n}")

        if passed:
            jury_score += 1
            print("Verdict: 🟢 APPROVED BY JURY\n")
        else:
            print("Verdict: 🔴 FAILED JURY BENCHMARK\n")

    print("=" * 80)
    print(f"🏁 FINAL HACKATHON JURY SCORE: {jury_score} / {total_tests} ({int(jury_score/total_tests * 100)}%)")
    if jury_score == total_tests:
        print("🌟 STATUS: 100% PRODUCTION READY FOR SIH 2026 FINALS!")
    else:
        print("⚠️ STATUS: NEEDS REFINEMENT")
    print("=" * 80)

if __name__ == "__main__":
    run_jury_evaluation()
