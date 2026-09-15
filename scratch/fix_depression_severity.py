import os

file_path = "/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '# 7. Sadness, Grief, Loneliness & Isolation' in line:
        new_lines.append(line)
        continue
    
    if len(new_lines) > 0 and '# 7. Sadness, Grief, Loneliness & Isolation' in new_lines[-1] and 'if any(w in t for w in [' in line:
        new_lines.append('    if any(w in t for w in ["depressed", "depression", "feeling down", "unhappy", "no one visited", "nobody visited", "visited", "alone", "lonely", "nobody cares", "crying", "cry", "broken", "empty", "hopeless", "sad", "sadness", "grief", "pain", "heavy heart", "उदासीन", "अकेला", "रो रहा", "डिप्रेशन", "उदासी", "கண்ணீர்", "தனிமை", "బాధ", "ఒంటరి", "ಅಳು", "ಏಕಾಂಗಿ", "रडणे", "एकटेपणा", "কান্না", "নিঃসঙ্গ"]):\n')
        continue

    if 'if "high" in r_str or "critical" in r_str:' in line:
        new_lines.append('            if ("high" in r_str or "critical" in r_str) and domain in ("suicide_crisis", "safety_threats"):\n')
        continue

    if 'elif "medium" in r_str:' in line:
        new_lines.append('            elif "medium" in r_str or domain in ("court_legal", "neighbor_harassment", "sleep_somatic", "sadness_isolation", "anxiety_panic"):\n')
        continue

    if '"alert_details": ALERT_DETAILS_DATA.get(lang, ALERT_DETAILS_DATA["EN"]) if severity == "high" else None,' in line:
        new_lines.append('        "alert_details": ALERT_DETAILS_DATA.get(lang, ALERT_DETAILS_DATA["EN"]) if (severity == "high" and domain in ("suicide_crisis", "safety_threats")) else None,\n')
        continue

    new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated conversation.py line-by-line successfully!")
