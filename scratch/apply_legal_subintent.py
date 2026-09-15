import os

file_path = "/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "# 3. Court / Legal Hearings / Depositions" in line:
        new_lines.append("    # 2.5 Legal Process Inquiry\n")
        new_lines.append('    if any(w in t for w in ["legal process", "steps are involved", "how the case works", "what are the steps", "stages of case", "legal procedure", "procedure", "what happens next in court", "fir to trial"]):\n')
        new_lines.append('        return "legal_process_inquiry"\n\n')
    
    if '"court_legal": ["Request Pre-Trial Counsellor Session"' in line:
        new_lines.append('        "legal_process_inquiry": ["Check Case Stages on Portal", "Know Free DLSA Legal Aid", "Claim TAME Travel Allowance"],\n')

    if 'elif domain in ("court_legal", "neighbor_harassment"' in line:
        new_lines.append('    elif domain in ("court_legal", "legal_process_inquiry", "neighbor_harassment", "sleep_somatic", "sadness_isolation", "anxiety_panic"):\n')
        continue

    if 'default_score = 52' in line and len(new_lines) > 0 and 'legal_process_inquiry' in new_lines[-1]:
        new_lines.append('        default_score = 42 if domain == "legal_process_inquiry" else 52\n')
        continue

    if 'primary_emotion = "anxiety" if domain in ("court_legal", "anxiety_panic") else "sadness"' in line:
        new_lines.append('        primary_emotion = "trust" if domain == "legal_process_inquiry" else ("anxiety" if domain in ("court_legal", "anxiety_panic") else "sadness")\n')
        continue

    if '        "court_legal": {' in line:
        new_lines.append('        "legal_process_inquiry": {\n')
        new_lines.append('            "EN": "The legal journey under the SC/ST (PoA) Act follows structured statutory stages: 1) FIR registration and preliminary protection, 2) DSP-level investigation mandated within 60 days, 3) Filing of the chargesheet in the Special Court, 4) Appointment of free legal aid via DLSA, and 5) Trial with Section 15A rights (separate witness room, police escort, daily travel allowance, and in-camera deposition). Which stage is your case currently at?",\n')
        new_lines.append('            "HI": "अनुसूचित जाति/जनजाति अत्याचार निवारण अधिनियम के तहत कानूनी प्रक्रिया के मुख्य वैधानिक चरण हैं: 1) एफआईआर दर्ज होना और सुरक्षा, 2) डीएसपी स्तर के अधिकारी द्वारा 60 दिनों के भीतर जांच, 3) विशेष अदालत में आरोप पत्र (चार्जशीट) दाखिल होना, 4) DLSA से निःशुल्क वकील मिलना, और 5) धारा 15A के तहत सुरक्षित गवाही, बंद कमरे में सुनवाई व यात्रा भत्ता (TAME)। आपका मामला वर्तमान में किस चरण में है?",\n')
        new_lines.append('            "TA": "வன்கொடுமை தடுப்பு சட்டத்தின் கீழ் சட்ட நடைமுறைகள்: 1) முதல் தகவல் அறிக்கை (FIR) மற்றும் பாதுகாப்பு, 2) 60 நாட்களுக்குள் டிஎஸ்பி விசாரணை, 3) சிறப்பு நீதிமன்றத்தில் குற்றப்பத்திரிகை, 4) இலவச DLSA வழக்கறிஞர், மற்றும் 5) பிரிவு 15A இன் கீழ் சாட்சி பாதுகாப்புடன் கூடிய விசாரணை. உங்கள் வழக்கு இப்போது எந்த கட்டத்தில் உள்ளது?",\n')
        new_lines.append('            "TE": "SC/ST చట్టం కింద న్యాయ ప్రక్రియ దశలు: 1) ఎఫ్‌ఐఆర్ నమోదు మరియు రక్షణ, 2) 60 రోజుల్లో డీఎస్పీ విచారణ, 3) ప్రత్యేక కోర్టులో చార్జిషీటు దాఖలు, 4) ఉచిత న్యాయ సహాయం (DLSA), మరియు 5) సెక్షన్ 15A కింద సాక్షి రక్షణతో కోర్టు విచారణ. మీ కేసు ప్రస్తుతం ఏ దశలో ఉంది?",\n')
        new_lines.append('            "KN": "ದೌರ್ಜನ್ಯ ತಡೆ ಕಾಯ್ದೆಯಡಿ ಕಾನೂನು ಪ್ರಕ್ರಿಯೆಯ ಹಂತಗಳು: 1) ಎಫ್‌ಐಆರ್ ಮತ್ತು ರಕ್ಷಣೆ, 2) 60 ದಿನಗಳಲ್ಲಿ ಡಿಎಸ್‌ಪಿ ತನಿಖೆ, 3) ವಿಶೇಷ ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಚಾರ್ಜ್‌ಶೀಟ್, 4) ಉಚಿತ ಕಾನೂನು ನೆರವು (DLSA), ಮತ್ತು 5) ಸೆಕ್ಷನ್ 15A ಸಾಕ್ಷಿ ರಕ್ಷಣೆಯೊಂದಿಗೆ ವಿಚಾರಣೆ. ನಿಮ್ಮ ಪ್ರಕರಣ ಈಗ ಯಾವ ಹಂತದಲ್ಲಿದೆ?",\n')
        new_lines.append('            "MR": "अत्याचार प्रतिबंधक कायद्यांतर्गत कायदेशीर प्रक्रिया: 1) एफआयआर आणि सुरक्षा, 2) 60 दिवसांत डीएसपी स्तरावर तपास, 3) विशेष न्यायालयात दोषारोपपत्र (चार्जशीट), 4) विधी सेवा प्राधिकरणाकडून मोफत वकील, आणि 5) कलम 15A अन्वये साक्ष नोंदणी व प्रवास भत्ता. आपले प्रकरण सध्या कोणत्या टप्प्यावर आहे?",\n')
        new_lines.append('            "BN": "পিওএ আইনের অধীনে আইনি ধাপগুলি হল: ১) এফআইআর ও সুরক্ষা, ২) ৬০ দিনের মধ্যে ডিএসপি তদন্ত, ৩) বিশেষ আদালতে চার্জশিট, ৪) ডিএলএসএ বিনামূল্যে আইনজীবী, এবং ৫) ধারা ১৫A এর অধীনে সাক্ষ্য সুরক্ষা। আপনার মামলাটি বর্তমানে কোন পর্যায়ে রয়েছে?"\n')
        new_lines.append('        },\n')

    new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Applied legal_process_inquiry cleanly!")
