import os

file_path = "/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Simplify greeting in REPLIES_DB
    if '"greeting": {' in line:
        new_lines.append('        "greeting": {\n')
        new_lines.append('            "EN": "Hello! How are you doing today? How can I help you?",\n')
        new_lines.append('            "HI": "नमस्ते! आप आज कैसा महसूस कर रहे हैं? मैं आपकी क्या मदद कर सकता हूँ?",\n')
        new_lines.append('            "TA": "வணக்கம்! இன்று நீங்கள் எப்படி இருக்கிறீர்கள்? நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",\n')
        new_lines.append('            "TE": "నమస్కారం! ఈరోజు మీరు ఎలా ఉన్నారు? నేను మీకు ఎలా సహాయపడగలను?",\n')
        new_lines.append('            "KN": "ನಮಸ್ಕಾರ! ಇಂದು ನೀವು ಹೇಗಿದ್ದೀರಿ? ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",\n')
        new_lines.append('            "MR": "नमस्ते! आज आपण कसे आहात? मी आपल्याला कशी मदत करू शकतो?",\n')
        new_lines.append('            "BN": "নমস্কার! আপনি আজ কেমন আছেন? আমি আপনাকে কীভাবে সাহায্য করতে পারি?"\n')
        new_lines.append('        },\n')
        # skip lines until closing bracket of greeting
        continue

    # Skip old greeting lines
    if i > 0 and any(k in lines[i-1] for k in ['"greeting": {', '"EN": "Namaste and welcome', '"HI": "नमस्ते और स्वागत', '"TA": "வணக்கம்! மென்டாரா', '"TE": "నమస్కారం! మెంటౌరా', '"KN": "ನಮಸ್ಕಾರ! ಮೆಂಟೌರಾ', '"MR": "नमस्ते! मेंटॉरा']) and '}' not in line:
        continue
    if i > 0 and '"BN": "নমস্কার! মেন্টরা' in lines[i-1] and '}' in line:
        continue

    # Simplify greeting chips
    if '"greeting": ["I want to share how I feel"' in line:
        new_lines.append('        "greeting": ["Tell me about my rights", "I want to share how I feel", "Help with my case"],\n')
        continue

    # Replace line where coping_techniques is returned
    if '"coping_techniques": TECHNIQUES_DATA.get(lang, TECHNIQUES_DATA["EN"]) if severity == "low" else None,' in line:
        new_lines.append('        "coping_techniques": TECHNIQUES_DATA.get(lang, TECHNIQUES_DATA["EN"]) if ((domain in ("grounding_calm", "anxiety_panic", "sleep_somatic") or any(w in message.lower() for w in ["calm", "relax", "breathe", "breathing", "exercise", "technique", "grounding", "coping"])) and domain not in ("greeting", "assistant_identity", "legal_process_inquiry", "compensation_welfare", "positive_resilience")) else [],\n')
        continue

    new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated conversation.py for simplified greeting and targeted coping techniques!")
