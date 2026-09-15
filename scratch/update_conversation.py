"""
Update conversation.py to include legal_process_inquiry and court_anxiety templates.
"""
from pathlib import Path

conv_path = Path("/Users/Harshita/Desktop/sih 2026/chatbot/ai_service/conversation.py")
text = conv_path.read_text(encoding="utf-8")

# 1. Update detect_message_domain
old_court_detect = '''    # 3. Court / Legal Hearings / Depositions
    if any(w in t for w in ["court", "hearing", "judge", "trial", "chargesheet", "lawyer", "advocate", "summons", "deposition", "witness box", "legal process", "testimony", "bail", "अदालत", "कोर्ट", "तारीख", "गवाही", "நீதிமன்றம்", "விசாரணை", "కోర్టు", "విచారణ", "ನ್ಯಾಯಾಲಯ", "न्यायालय", "सुनावणी", "আদালত", "শুনানি"]):
        return "court_legal"'''

new_court_detect = '''    # 3. Court / Legal Hearings / Depositions
    if any(w in t for w in ["legal process", "court process", "how court works", "stages of trial", "procedure", "tell me about the legal"]):
        return "legal_process_inquiry"
    if any(w in t for w in ["court", "hearing", "judge", "trial", "chargesheet", "lawyer", "advocate", "summons", "deposition", "witness box", "testimony", "bail", "अदालत", "कोर्ट", "तारीख", "गवाही", "நீதிமன்றம்", "விசாரணை", "కోర్టు", "విచారణ", "ನ್ಯಾಯಾಲಯ", "न्यायालय", "सुनावणी", "আদালত", "শুনানি"]):
        if any(w in t for w in ["scared", "fear", "anxious", "nervous", "tomorrow", "worried", "डर", "பயம்", "భయం", "ಹೆದರಿಕೆ"]):
            return "court_anxiety"
        return "court_legal"'''

assert old_court_detect in text, "old_court_detect not found"
text = text.replace(old_court_detect, new_court_detect)

# 2. Add legal_process_inquiry and court_anxiety into REPLIES_DB
old_court_entry = '''        "court_legal": {
            "EN": "Court hearings, legal depositions, and trial procedures naturally create intense anxiety and nervousness. Under Section 15A of the PoA Act, you have explicit rights: protection during transit, in-camera examination, DLSA legal counsel, and daily travel allowance (TAME). What part of the court date is worrying you the most?",
            "HI": "न्यायालय की सुनवाई, गवाही और कानूनी प्रक्रियाएं स्वाभाविक रूप से गहरा तनाव और घबराहट पैदा करती हैं। अधिनियम की धारा 15A के तहत आपको अदालत आते-जाते समय सुरक्षा, बंद कमरे (इन-कैमरा) में गवाही और DLSA से निःशुल्क कानूनी सहायता का पूरा अधिकार है। अदालत को लेकर आपके मन में सबसे बड़ी चिंता क्या है?",
            "TA": "நீதிமன்ற விசாரணை மற்றும் வாக்குமூலம் அளிப்பது இயல்பாகவே அதிக மன அழுத்தத்தை தரும். பிரிவு 15A இன் கீழ் உங்களுக்கு நீதிமன்றத்திற்கு பாதுகாப்பான பயணம் மற்றும் இலவச சட்ட உதவி பெற உரிமை உள்ளது. உங்கள் வழக்கில் உங்களுக்கு என்ன தயக்கம் உள்ளது?",
            "TE": "కోర్టు విచారణలు మరియు సాక్ష్యం చెప్పే ప్రక్రియ తీవ్ర ఆందోళన కలిగిస్తుంది. సెక్షన్ 15A కింద మీకు ఉచిత న్యాయ సహాయం మరియు భద్రత పొందే హక్కు ఉంది. కోర్టు విషయంలో మీకు ఏది ఎక్కువ భయంగా ఉంది?",
            "KN": "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆ ಮತ್ತು ಸಾಕ್ಷಿ ಹೇಳುವುದು ಸಹಜವಾಗಿಯೇ ಆತಂಕ ಉಂಟುಮಾಡುತ್ತದೆ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಉಚಿತ ಕಾನೂನು ನೆರವು ಮತ್ತು ರಕ್ಷಣೆಯ ಹಕ್ಕಿದೆ. ನ್ಯಾಯಾಲಯದ ಬಗ್ಗೆ ನಿಮಗೆ ಯಾವ ವಿಷಯ ಆತಂಕ ತಂದಿದೆ?",
            "MR": "न्यायालयातील सुनावणी आणि साक्ष देण्याची प्रक्रिया तणाव निर्माण करणारी असते. कलम 15A अन्वये आपल्याला न्यायालयापर्यंत सुरक्षा आणि विधी सेवा प्राधिकरणाकडून मोफत वकील मिळण्याचा अधिकार आहे. आपल्याला नक्की कशाची भीती वाटते?",
            "BN": "আদালতের শুনানি এবং সাক্ষ্য দেওয়ার প্রক্রিয়া স্বাভাবিকভাবেই উদ্বেগ সৃষ্টি করে। ধারা ১৫A এর অধীনে আপনার নিরাপত্তা এবং বিনামূল্যে আইনি সহায়তা পাওয়ার অধিকার রয়েছে। আদালতের ব্যাপারে আপনার প্রধান চিন্তা কী?"
        },'''

new_court_entry = '''        "legal_process_inquiry": {
            "EN": "The legal journey under the SC/ST (Prevention of Atrocities) Act follows structured statutory milestones: 1) Immediate FIR registration, 2) Investigation completed by a DSP-level officer within 60 days, 3) Chargesheet submission to a Special Designated Court, 4) Free legal aid provided by DLSA under Section 15A, and 5) Day-to-day trial hearings with Travel & Maintenance Allowance (TAME). What stage is your case currently at?",
            "HI": "अत्याचार निवारण अधिनियम के तहत कानूनी प्रक्रिया सुनियोजित चरणों में चलती है: 1) तत्काल FIR, 2) पुलिस उपाधीक्षक (DSP) द्वारा 60 दिनों में जांच पूरी करना, 3) विशेष अदालत में आरोप पत्र दाखिल करना, 4) धारा 15A के तहत DLSA द्वारा मुफ्त वकील, और 5) त्वरित सुनवाई के साथ प्रत्येक तारीख पर यात्रा भत्ता (TAME)। आपका मामला वर्तमान में किस चरण में है?",
            "TA": "வன்கொடுமை தடுப்பு சட்டத்தின் கீழ் சட்ட நடைமுறை: 1) உடனடி முதல் தகவல் அறிக்கை (FIR), 2) டிஎஸ்பி அதிகாரியால் 60 நாட்களில் விசாரணை, 3) சிறப்பு நீதிமன்றத்தில் குற்றப்பத்திரிகை, 4) இலவச சட்ட உதவி, 5) தினசரி விசாரணை மற்றும் பயணப்படி (TAME). உங்கள் வழக்கு தற்போது எந்த நிலையில் உள்ளது?",
            "TE": "SC/ST చట్టం కింద న్యాయ ప్రక్రియ: 1) తక్షణ ఎఫ్ఐఆర్ నమోదు, 2) డీఎస్పీ స్థాయి అధికారితో 60 రోజుల్లో దర్యాప్తు, 3) ప్రత్యేక కోర్టులో ఛార్జిషీట్ దాఖలు, 4) ఉచిత న్యాయ సహాయం, 5) ప్రతి వాయిదాకు ప్రయాణ భత్యం (TAME). మీ కేసు ప్రస్తుతం ఏ దశలో ఉంది?",
            "KN": "ದೌರ್ಜನ್ಯ ತಡೆ ಕಾಯ್ದೆಯಡಿ ಕಾನೂನು ಹಂತಗಳು: 1) ತಕ್ಷಣದ ಎಫ್‌ಐಆರ್, 2) ಡಿಎಸ್‌ಪಿ ಅಧಿಕಾರಿಯಿಂದ 60 ದಿನಗಳಲ್ಲಿ ತನಿಖೆ, 3) ವಿಶೇಷ ನ್ಯಾಯಾಲಯದಲ್ಲಿ ದೋಷಾರೋಪಣೆ ಪಟ್ಟಿ, 4) ಉಚಿತ ಕಾನೂನು ನೆರವು, 5) ಪ್ರಯಾಣ ಭತ್ಯೆ (TAME). ನಿಮ್ಮ ಪ್ರಕರಣ ಪ್ರಸ್ತುತ ಯಾವ ಹಂತದಲ್ಲಿದೆ?",
            "MR": "अत्याचार प्रतिबंधक कायद्यान्वये कायदेशीर टप्पे: 1) तात्काळ एफआयआर, 2) डीवायएसपी अधिकाऱ्यांकडून 60 दिवसांत तपास, 3) विशेष न्यायालयात दोषारोपपत्र, 4) मोफत वकील, 5) प्रवास भत्ता (TAME). आपले प्रकरण सध्या कोणत्या टप्प्यावर आहे?",
            "BN": "পিওএ আইনের অধীনে আইনি প্রক্রিয়া: ১) অবিলম্বে এফআইআর, ২) ডিএসপি স্তরের আধিকারিক দ্বারা ৬০ দিনে তদন্ত, ৩) বিশেষ আদালতে চার্জশিট, ৪) বিনামূল্যে আইনি সহায়তা, ৫) ভ্রমণ ভাতা (TAME)। আপনার মামলা বর্তমানে কোন পর্যায়ে রয়েছে?"
        },
        "court_anxiety": {
            "EN": "Feeling scared and anxious about an upcoming court date is completely understandable. Walking into a courtroom can feel overwhelming, but you have vital rights under Section 15A: secure police escort during transit, in-camera testimony away from the public, and DLSA legal representation. Our assigned counsellor can also guide you through pre-hearing grounding. What part of tomorrow feels most frightening?",
            "HI": "अदालत की तारीख को लेकर घबराहट और डर महसूस होना पूरी तरह स्वाभाविक है। अदालत में जाना कठिन लग सकता है, लेकिन धारा 15A के तहत आपको अदालत तक सुरक्षित पुलिस एस्कॉर्ट, बंद कमरे (इन-कैमरा) में गवाही और सुरक्षा का पूरा कानूनी अधिकार है। हमारे परामर्शदाता सुनवाई से पहले आपको मानसिक संबल भी दे सकते हैं। कल के बारे में सबसे ज्यादा क्या सता रहा है?",
            "TA": "நீதிமன்ற விசாரணைக்கு முன் பயமும் பதற்றமும் ஏற்படுவது மிகவும் இயல்பானது. பிரிவு 15A இன் கீழ் உங்களுக்கு பாதுகாப்பான போலீஸ் பாதுகாப்பு மற்றும் ரகசிய வாக்குமூல உரிமை உண்டு. நாளைய விசாரணையில் உங்களுக்கு என்ன பயமாக இருக்கிறது?",
            "TE": "కోర్టు వాయిదా గురించి భయం మరియు ఆందోళన కలగడం చాలా సహజం. సెక్షన్ 15A కింద మీకు పూర్తి రక్షణ మరియు ఉచిత న్యాయవాది సేవలు లభిస్తాయి. రేపటి కోర్టు గురించి మీకు ఏది ఎక్కువ భయంగా ఉంది?",
            "KN": "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆಯ ಬಗ್ಗೆ ಭಯ ಮತ್ತು ಆತಂಕ ಉಂಟಾಗುವುದು ಸಹಜ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಪೊಲೀಸ್ ರಕ್ಷಣೆ ಮತ್ತು ಕಾನೂನು ನೆರವು ಸಿಗುತ್ತದೆ. ನಾಳಿನ ಬಗ್ಗೆ ನಿಮಗೆ ಯಾವ ಆತಂಕವಿದೆ?",
            "MR": "न्यायालयातील सुनावणीबद्दल भीती वाटणे अगदी स्वाभाविक आहे. कलम 15A नुसार आपल्याला पोलीस संरक्षण आणि मोफत कायदेशीर मदत मिळते. उद्याच्या सुनावणीबद्दल आपल्याला नक्की कशाची भीती वाटते?",
            "BN": "আদালতের তারিখ নিয়ে ভয় ও উদ্বেগ হওয়া খুবই স্বাভাবিক। ধারা ১৫A এর অধীনে আপনার পুলিশ এসকর্ট এবং গোপনীয় সাক্ষ্য দেওয়ার অধিকার রয়েছে। আগামীকালের ব্যাপারে আপনার প্রধান ভয় কী?"
        },
        "court_legal": {
            "EN": "Court hearings, legal depositions, and trial procedures naturally create intense anxiety and nervousness. Under Section 15A of the PoA Act, you have explicit rights: protection during transit, in-camera examination, DLSA legal counsel, and daily travel allowance (TAME). What part of the court date is worrying you the most?",
            "HI": "न्यायालय की सुनवाई, गवाही और कानूनी प्रक्रियाएं स्वाभाविक रूप से गहरा तनाव और घबराहट पैदा करती हैं। अधिनियम की धारा 15A के तहत आपको अदालत आते-जाते समय सुरक्षा, बंद कमरे (इन-कैमरा) में गवाही और DLSA से निःशुल्क कानूनी सहायता का पूरा अधिकार है। अदालत को लेकर आपके मन में सबसे बड़ी चिंता क्या है?",
            "TA": "நீதிமன்ற விசாரணை மற்றும் வாக்குமூலம் அளிப்பது இயல்பாகவே அதிக மன அழுத்தத்தை தரும். பிரிவு 15A இன் கீழ் உங்களுக்கு நீதிமன்றத்திற்கு பாதுகாப்பான பயணம் மற்றும் இலவச சட்ட உதவி பெற உரிமை உள்ளது. உங்கள் வழக்கில் உங்களுக்கு என்ன தயக்கம் உள்ளது?",
            "TE": "కోర్టు విచారణలు మరియు సాక్ష్యం చెప్పే ప్రక్రియ తీవ్ర ఆందోళన కలిగిస్తుంది. సెక్షన్ 15A కింద మీకు ఉచిత న్యాయ సహాయం మరియు భద్రత పొందే హక్కు ఉంది. కోర్టు విషయంలో మీకు ఏది ఎక్కువ భయంగా ఉంది?",
            "KN": "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆ ಮತ್ತು ಸಾಕ್ಷಿ ಹೇಳುವುದು ಸಹಜವಾಗಿಯೇ ಆತಂಕ ಉಂಟುಮಾಡುತ್ತದೆ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಉಚಿತ ಕಾನೂನು ನೆರವು ಮತ್ತು ರಕ್ಷಣೆಯ ಹಕ್ಕಿದೆ. ನ್ಯಾಯಾಲಯದ ಬಗ್ಗೆ ನಿಮಗೆ ಯಾವ ವಿಷಯ ಆತಂಕ ತಂದಿದೆ?",
            "MR": "न्यायालयातील सुनावणी आणि साक्ष देण्याची प्रक्रिया तणाव निर्माण करणारी असते. कलम 15A अन्वये आपल्याला न्यायालयापर्यंत सुरक्षा आणि विधी सेवा प्राधिकरणाकडून मोफत वकील मिळण्याचा अधिकार आहे. आपल्याला नक्की कशाची भीती वाटते?",
            "BN": "আদালতের শুনানি এবং সাক্ষ্য দেওয়ার প্রক্রিয়া স্বাভাবিকভাবেই উদ্বেগ সৃষ্টি করে। ধারা ১৫A এর অধীনে আপনার নিরাপত্তা এবং বিনামূল্যে আইনি সহায়তা পাওয়ার অধিকার রয়েছে। আদালতের ব্যাপারে আপনার প্রধান চিন্তা কী?"
        },'''

assert old_court_entry in text, "old_court_entry not found"
text = text.replace(old_court_entry, new_court_entry)

# 3. Add to ACTION_CHIPS_DB
old_chips = '''        "court_legal": ["Request Pre-Trial Counsellor Session", "Know Section 15A Rights", "Try 4-7-8 Breathing"],'''
new_chips = '''        "legal_process_inquiry": ["Learn Trial Milestones", "DLSA Legal Aid Guide", "Section 15A Rights Summary"],
        "court_anxiety": ["Pre-Hearing Grounding Session", "Request Court Police Escort", "Try 4-7-8 Breathing"],
        "court_legal": ["Request Pre-Trial Counsellor Session", "Know Section 15A Rights", "Try 4-7-8 Breathing"],'''

assert old_chips in text, "old_chips not found"
text = text.replace(old_chips, new_chips)

conv_path.write_text(text, encoding="utf-8")
print("conversation.py updated with distinct legal process inquiry and court anxiety!")
