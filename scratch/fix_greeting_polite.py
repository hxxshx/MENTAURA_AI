import os

file_path = "/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 1. Update greeting detector in detect_message_domain
    if '# 12. Greeting' in line:
        new_lines.append("    # 12. Greeting & Introductions\n")
        new_lines.append('    if any(w in t for w in ["hi", "hello", "hey", "nice to meet", "good to meet", "pleased to meet", "namaste", "vanakkam", "namaskara", "good morning", "good afternoon", "good evening", "how are you"]):\n')
        new_lines.append('        return "greeting"\n')
        continue

    # skip old greeting check line
    if 'if any(w in t for w in ["hi", "hello", "hey", "namaste"' in line:
        continue
    if 'and len(t.split()) <= 4:' in line:
        continue
    if 'return "greeting"' in line and len(new_lines) > 0 and 'return "greeting"' in new_lines[-1]:
        continue

    # 2. Update general_sharing template to be conversational and not overly melodramatic
    if '"general_sharing": {' in line:
        new_lines.append('        "general_sharing": {\n')
        new_lines.append('            "EN": "I am here to support you. How are you feeling today, or is there something specific about your case or well-being you would like to talk about?",\n')
        new_lines.append('            "HI": "मैं आपकी सहायता के लिए यहाँ हूँ। आज आप कैसा महसूस कर रहे हैं, या अपने मामले और मानसिक स्वास्थ्य को लेकर कुछ पूछना चाहते हैं?",\n')
        new_lines.append('            "TA": "நான் உங்களுக்கு உதவ தயாராக உள்ளேன். இன்று நீங்கள் எப்படி உணர்கிறீர்கள்? உங்கள் வழக்கு குறித்து ஏதேனும் பேச விரும்புகிறீர்களா?",\n')
        new_lines.append('            "TE": "నేను మీకు సహాయం చేయడానికి సిద్ధంగా ఉన్నాను. ఈరోజు మీరు ఎలా ఉన్నారు? మీ కేసు లేదా సంక్షేమం గురించి ఏమైనా మాట్లాడాలనుకుంటున్నారా?",\n')
        new_lines.append('            "KN": "ನಾನು ನಿಮಗೆ ಬೆಂಬಲ ನೀಡಲು ಇಲ್ಲಿದ್ದೇನೆ. ಇಂದು ನೀವು ಹೇಗಿದ್ದೀರಿ? ನಿಮ್ಮ ಪ್ರಕರಣ ಅಥವಾ ಆರೋಗ್ಯದ ಬಗ್ಗೆ ಏನಾದರೂ ಮಾತನಾಡಲು ಬಯಸುವಿರಾ?",\n')
        new_lines.append('            "MR": "मी आपल्याला मदत करण्यासाठी उपस्थित आहे. आज आपण कसे आहात? आपल्या प्रकरणाविषयी काही बोलायचे आहे का?",\n')
        new_lines.append('            "BN": "আমি আপনার সহায়তায় আছি। আজ আপনি কেমন আছেন? আপনার মামলা বা মানসিক স্বাস্থ্য সম্পর্কে কিছু বলতে চান?"\n')
        new_lines.append('        },\n')
        continue

    if any(k in line for k in ['"EN": "Thank you for sharing that with me. What you\'re experiencing is important', '"HI": "अपनी बात साझा करने के लिए धन्यवाद', '"TA": "உங்கள் அனுபவத்தை பகிர்ந்ததற்கு நன்றி', '"TE": "నాతో పంచుకున్నందుకు ధన్యవాదాలు', '"KN": "ನಿಮ್ಮ ಅನುಭವ ಹಂಚಿಕೊಂಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು', '"MR": "आपल्या भावना व्यक्त केल्याबद्दल धन्यवाद', '"BN": "আপনার কথা জানানোর জন্য ধন্যবাদ']):
        continue

    # 3. Update general_sharing chips
    if '"general_sharing": ["Share more details", "Connect with Counsellor", "Try 4-7-8 Breathing"]' in line:
        new_lines.append('        "general_sharing": ["Tell me about my rights", "I want to share how I feel", "Help with my case"]\n')
        continue

    new_lines.append(line)

code = "".join(new_lines)

# 4. In generate_contextual_turn, if user says "nice to meet you" or "good to meet you", give a tailored intro reply
old_reply_assign = 'reply_text = REPLIES_DB.get(domain, {}).get(lang, REPLIES_DB["general_sharing"]["EN"])'
new_reply_assign = '''    if domain == "greeting" and any(w in t for w in ["nice to meet", "good to meet", "pleased to meet"]):
        intro_replies = {
            "EN": "Hello! Nice to meet you too. How are you doing today? How can I help you?",
            "HI": "नमस्ते! आपसे मिलकर बहुत अच्छा लगा। आप आज कैसा महसूस कर रहे हैं? मैं आपकी क्या मदद कर सकता हूँ?",
            "TA": "வணக்கம்! உங்களை சந்தித்ததில் மிக்க மகிழ்ச்சி. இன்று உங்களுக்கு நான் எவ்வாறு உதவ முடியும்?",
            "TE": "నమస్కారం! మిమ్మల్ని కలవడం చాలా సంతోషంగా ఉంది. ఈరోజు నేను మీకు ఎలా సహాయపడగలను?",
            "KN": "ನಮಸ್ಕಾರ! ನಿಮ್ಮನ್ನು ಭೇಟಿಯಾಗಿದ್ದಕ್ಕೆ ಸಂತೋಷವಾಯಿತು. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
            "MR": "नमस्ते! आपल्याला भेटून खूप आनंद झाला. आज मी आपल्याला कशी मदत करू शकतो?",
            "BN": "নমস্কার! আপনার সাথে পরিচিত হয়ে ভালো লাগল। আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
        }
        reply_text = intro_replies.get(lang, intro_replies["EN"])
    else:
        reply_text = REPLIES_DB.get(domain, {}).get(lang, REPLIES_DB["general_sharing"]["EN"])'''

assert old_reply_assign in code, "old_reply_assign not found"
code = code.replace(old_reply_assign, new_reply_assign, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated conversation.py for greetings and polite introductions successfully!")
