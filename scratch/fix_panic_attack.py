import os

file_path = "/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

old_threat = """    # 1. Threats / Danger / Section 15A
    if any(w in t for w in ["threat", "threatened", "intimidation", "knife", "gun", "accused", "kill", "attack", "stalk", "following me", "outside my", "unsafe", "in danger", "danger", "धमकी", "मार", "மிரட்டல்", "கொலை", "బెదిరింపు", "చంపే", "ಬೆದರಿಕೆ", "भीती", "হুমকি", "15a"]):
        return "safety_threats\""""

new_threat = """    # 1. Threats / Danger / Section 15A
    is_panic_or_anxiety_attack = any(p in t for p in ["panic attack", "anxiety attack", "heart attack"])
    has_threat_keyword = any(w in t for w in ["threat", "threatened", "intimidation", "knife", "gun", "accused", "kill", "stalk", "following me", "outside my", "unsafe", "in danger", "danger", "धमकी", "मार", "மிரட்டல்", "கொலை", "బెదిరింపు", "చంపే", "ಬೆದರಿಕೆ", "भीती", "হুমকি", "15a"]) or ("attack" in t and not is_panic_or_anxiety_attack)
    if has_threat_keyword:
        return "safety_threats\""""

assert old_threat in code, "old_threat not found"
code = code.replace(old_threat, new_threat, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated attack handling cleanly!")
