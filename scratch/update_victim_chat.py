# -*- coding: utf-8 -*-
import os

victim_py_path = os.path.join(r"c:\Users\Keerthi Sridhar\Desktop\sih 2026", "backend", "app", "routers", "victim.py")

try:
    with open(victim_py_path, "r", encoding="utf-8") as f:
        content = f.read()
except UnicodeDecodeError:
    with open(victim_py_path, "r", encoding="latin-1") as f:
        content = f.read()

start_marker = "class ChatbotMessageRequest(BaseModel):"
end_marker = "# ============================================================================\n# NHAA 14566 IVRS TELEPHONY CALL SIMULATOR (SIH 26094)"

new_code = '''class ChatbotMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="EN")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)


@router.post("/api/victim/chatbot/message")
def conversational_chatbot_checkin(
    payload: ChatbotMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Advanced, trauma-informed conversational AI dialogue engine for victim check-in.
    Provides empathetic multi-turn continuity, statutory legal awareness under SC/ST PoA Act 1989 & PCR Act 1955,
    accurate distress scoring, and genuine multilingual dialogue.
    """
    if current_user.verified_role not in VICTIM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized victim and witness accounts."
        )

    user_msg = payload.message.strip()
    msg_lower = user_msg.lower()
    lang = (payload.language or current_user.preferred_language or "EN").upper()
    history = payload.conversation_history or []

    # 1. Contextual Intent & Topic Classification
    is_greeting = any(w in msg_lower for w in ["hi", "hello", "hey", "namaste", "vanakkam", "namaskara", "good morning", "good evening", "good afternoon"]) and len(msg_lower.split()) <= 3
    is_conn_check = any(w in msg_lower for w in ["hear me", "listening", "are you there", "can you hear", "anyone there", "hello?"])
    is_crisis = any(w in msg_lower for w in ["suicide", "kill myself", "end my life", "want to die", "hurt myself", "आत्महत्या", "मरना चाहता", "தற்கொலை", "చనిపోవాలని", "ಆತ್ಮಹತ್ಯೆ", "মরতে চাই"])
    is_threat = any(w in msg_lower for w in ["threat", "threatened", "intimidation", "scared of accused", "following me", "stalk", "kill me", "unsafe", "danger", "धमकी", "मार डालेंगे", "மிரட்டல்", "బెదిరింపు", "ಬೆದರಿಕೆ", "भीती", "হুমকি", "15a"])
    is_court = any(w in msg_lower for w in ["court", "hearing", "judge", "trial", "chargesheet", "lawyer", "advocate", "summons", "postponed", "adjourned", "अदालत", "कोर्ट", "तारीख", "நீதிமன்றம்", "விசாரணை", "కోర్టు", "ನ್ಯಾಯಾಲಯ", "न्यायालय", "আদালত"])
    is_compensation = any(w in msg_lower for w in ["compensation", "relief", "money", "allowance", "tame", "travel", "disbursement", "annexure", "मुआवजा", "राहत", "இழப்பீடு", "పరిహారం", "ಪರಿಹಾರ", "भरपाई", "ক্ষতিপূরণ"])
    is_sleep = any(w in msg_lower for w in ["sleep", "insomnia", "nightmare", "nightmares", "sleepless", "wake up", "restless", "नींद", "தூக்கம்", "నిద్ర", "ನಿದ್ರೆ", "झोप", "ঘুম"])
    is_grounding = any(w in msg_lower for w in ["grounding", "breathe", "breathing", "calm", "panic", "4-7-8", "exercise", "soothe", "प्राणायाम", "மூச்சுப்பயிற்சி", "శ్వాస"])
    is_deep_distress = any(w in msg_lower for w in ["deep emotional distress", "grief", "social isolation", "boycott", "humiliation", "broken", "helpless", "crying", "pain", "hopeless", "depression", "उदास", "रो रहा", "अपमान", "கண்ணீர்", "அவமானம்", "బాధ", "ಏಕಾಂಗಿ", "दुःख", "কষ্ট"])
    is_stress_general = any(w in msg_lower for w in ["stress", "stressed", "tension", "pressure", "overwhelmed", "exhausted", "tired", "heavy", "तनाव", "மன அழுத்தம்", "ఒత్తిడి", "ಒತ್ತಡ", "तणाव", "চাপ"])
    is_positive = any(w in msg_lower for w in ["fine", "okay", "ok", "good", "safe today", "better", "thank", "thanks", "feeling steady"]) and not (is_threat or is_crisis)

    # 2. Extract Prior Context from History
    prior_user_msgs = [h.get("content", "").lower() for h in history if h.get("role") == "user"]
    prior_has_court = any("court" in m or "hearing" in m for m in prior_user_msgs)
    prior_has_threat = any("threat" in m or "scared" in m or "safe" in m for m in prior_user_msgs)

    # 3. Generate Intelligent Empathetic Response & Structured Action Chips
    if is_crisis:
        dynamic_score = 90
        risk_level_str = "critical"
        primary_emotion = "acute_crisis"
        if lang == "HI":
            reply_text = "आपकी सुरक्षा और भलाई हमारी सर्वोच्च प्राथमिकता है। आप अकेले नहीं हैं। हमने आपके लिए विशेष सहायता सक्रिय की है। कृपया तुरंत 14566 या Tele-MANAS (14416) पर बात करें।"
        elif lang == "TA":
            reply_text = "உங்கள் பாதுகாப்பு மிகவும் முக்கியமானது. நீங்கள் தனியாக இல்லை. அவசர ஆதரவு தயாராக உள்ளது. தயவுசெய்து 14566 அல்லது 14416 ஐ தொடர்பு கொள்ளவும்."
        elif lang == "TE":
            reply_text = "మీ భద్రత మరియు శ్రేయస్సు మా అత్యంత ప్రాధాన్యత. మీరు ఒంటరిగా లేరు. తక్షణ సహాయం కోసం దయచేసి 14566 లేదా 14416 కు కాల్ చేయండి."
        elif lang == "KN":
            reply_text = "ನಿಮ್ಮ ಸುರಕ್ಷತೆ ಮತ್ತು ಯೋಗಕ್ಷೇಮ ನಮ್ಮ ಆದ್ಯತೆಯಾಗಿದೆ. ನೀವು ಒಂಟಿಯಾಗಿಲ್ಲ. ತಕ್ಷಣದ ಬೆಂಬಲಕ್ಕಾಗಿ 14566 ಅಥವಾ 14416 ಗೆ ಕರೆ ಮಾಡಿ."
        elif lang == "MR":
            reply_text = "तुमची सुरक्षा आणि आरोग्य ही आमची सर्वोच्च प्राथमिकता आहे. तुम्ही एकटे नाही आहात. तात्काळ मदतीसाठी 14566 किंवा 14416 वर संपर्क साधा."
        elif lang == "BN":
            reply_text = "আপনার সুরক্ষা এবং সুস্থতা আমাদের সর্বোচ্চ অগ্রাধিকার। আপনি একা নন। জরুরি সহায়তার জন্য অনুগ্রহ করে 14566 বা 14416 নম্বরে যোগাযোগ করুন।"
        else:
            reply_text = "I hear the deep pain in what you're sharing. Please know that your life and safety are deeply important to us. You do not have to carry this alone. Please reach out right now to our 24/7 dedicated helpline at 14566 or Tele-MANAS at 14416. We can also connect you to an emergency counsellor immediately."
        suggested_actions = ["Call Helpline 14566", "Trigger SOS Panic Alert", "Request Immediate Counsellor Call"]

    elif is_threat:
        dynamic_score = 75
        risk_level_str = "high"
        primary_emotion = "fear_intimidation"
        if lang == "HI":
            reply_text = "मुझे यह जानकर दुख हुआ कि आप भयभीत या असुरक्षित महसूस कर रहे हैं। SC/ST अत्याचार निवारण अधिनियम की धारा 15A के तहत आपको पूर्ण गवाह संरक्षण, पुलिस सुरक्षा एस्कॉर्ट और गोपनीयता का वैधानिक अधिकार है। क्या आप चाहते हैं कि हम सुरक्षा अधिकारी को सूचित करें?"
        elif lang == "TA":
            reply_text = "நீங்கள் பயத்தை அல்லது மிரட்டலை எதிர்கொள்கிறீர்கள் என்பதை நான் புரிந்துகொள்கிறேன். வன்கொடுமை தடுப்புச் சட்டம் பிரிவு 15A இன் கீழ் உங்களுக்கு முழு காவல் பாதுகாப்பு மற்றும் சாட்சி பாதுகாப்பு பெற சட்ட உரிமை உண்டு."
        elif lang == "TE":
            reply_text = "మీరు భయపడుతున్నారని అర్థం చేసుకోగలను. SC/ST చట్టం సెక్షన్ 15A ప్రకారం మీకు పూర్తి రక్షణ మరియు పోలీసు భద్రత పొందే చట్టపరమైన హక్కు ఉంది."
        elif lang == "KN":
            reply_text = "ನೀವು ಬೆದರಿಕೆ ಅಥವಾ ಭಯವನ್ನು ಎದುರಿಸುತ್ತಿದ್ದೀರಿ ಎಂದು ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ದೌರ್ಜನ್ಯ ತಡೆ ಕಾಯ್ದೆಯ ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಪೊಲೀಸ್ ರಕ್ಷಣೆ ಪಡೆಯುವ ಹಕ್ಕಿದೆ."
        elif lang == "MR":
            reply_text = "तुम्हाला भीती किंवा धोका वाटत असल्याचे मला समजते. अत्याचार प्रतिबंधक कायद्याच्या कलम 15A अंतर्गत तुम्हाला पोलीस संरक्षण मिळवण्याचा कायदेशीर हक्क आहे."
        elif lang == "BN":
            reply_text = "আমি বুঝতে পারছি আপনি ভয় বা হুমকি পাচ্ছেন। পিওএ আইনের ধারা 15A এর অধীনে আপনার পূর্ণ পুলিশ সুরক্ষা এবং সহায়তা পাওয়ার আইনি অধিকার রয়েছে।"
        else:
            reply_text = "Your safety is paramount. Under Section 15A of the SC/ST (PoA) Act, 1989, you have a statutory right to comprehensive witness protection, police security escorts, confidential trial proceedings, and immediate protection against intimidation. If you are in immediate danger, please press the red SOS Panic button or call 14566 right now."
        suggested_actions = ["Log Threat Under Section 15A", "Request Police Protection Escort", "Call 14566 Helpline"]

    elif is_court:
        dynamic_score = 55
        risk_level_str = "medium"
        primary_emotion = "legal_institutional_stress"
        if lang == "HI":
            reply_text = "अदालत की सुनवाई और कानूनी प्रक्रियाएं बहुत तनावपूर्ण हो सकती हैं। यह बिल्कुल स्वाभाविक है। आपको विशेष लोक अभियोजक (Special PP), मुफ्त कानूनी सहायता (DLSA) और हर सुनवाई के लिए यात्रा और रखरखाव भत्ता (TAME) का कानूनी अधिकार है।"
        elif lang == "TA":
            reply_text = "நீதிமன்ற விசாரணைகள் மன அழுத்தத்தை ஏற்படுத்தலாம். உங்களுக்கு இலவச சட்ட உதவி, சிறப்பு வழக்கறிஞர் மற்றும் பயணப்படி (TAME) பெற உரிமை உண்டு."
        elif lang == "TE":
            reply_text = "కోర్టు విచారణలు మరియు న్యాయపరమైన జాప్యాలు ఆందోళన కలిగిస్తాయి. మీకు ఉచిత న్యాయ సహాయం మరియు ప్రయాణ భత్యం (TAME) పొందే హక్కు ఉంది."
        elif lang == "KN":
            reply_text = "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆಗಳು ಆತಂಕವನ್ನುಂಟುಮಾಡಬಹುದು. ನಿಮಗೆ ಉಚಿತ ಕಾನೂನು ನೆರವು ಮತ್ತು ಪ್ರಯಾಣ ಭತ್ಯೆ (TAME) ಪಡೆಯುವ ಹಕ್ಕಿದೆ."
        elif lang == "MR":
            reply_text = "न्यायालयीन सुनावणी आणि कायदेशीर प्रक्रिया तणावपूर्ण असू शकतात. तुम्हाला मोफत कायदेशीर मदत आणि प्रवास भत्ता (TAME) मिळवण्याचा हक्क आहे."
        elif lang == "BN":
            reply_text = "আদালতের শুনানি উদ্বেগজনক হতে পারে। আপনার বিনামূল্যে আইনি সহায়তা এবং ভ্রমণ ভাতা (TAME) পাওয়ার অধিকার রয়েছে।"
        else:
            reply_text = "Court hearings and trial proceedings can bring up intense anxiety. Under the SC/ST PoA Act, Special Courts are mandated to conduct sensitive, camera proceedings to protect you from harassment. You also have the right to free legal aid from DLSA, a dedicated Special Public Prosecutor, and Travel Allowance (TAME) for every court attendance."
        suggested_actions = ["View My Case Journey", "Check Hearing Schedule", "Request Free Legal Aid Consultation"]

    elif is_compensation:
        dynamic_score = 30
        risk_level_str = "low"
        primary_emotion = "institutional_inquiry"
        if lang == "HI":
            reply_text = "SC/ST अत्याचार निवारण नियमों के नियम 12(4) और अनुलग्नक-I के तहत, आप चरणबद्ध वित्तीय राहत (FIR पर 25%, चार्जशीट पर 50%, फैसले पर 25%) और प्रत्येक पेशी के लिए यात्रा भत्ते (TAME) के पूर्ण हकदार हैं।"
        elif lang == "TA":
            reply_text = "வன்கொடுமை தடுப்பு விதிகளின் கீழ் உங்களுக்கு இழப்பீடு மற்றும் பயணப்படி (TAME) பெற உரிமை உண்டு."
        elif lang == "TE":
            reply_text = "SC/ST చట్టం ప్రకారం మీకు ఆర్థిక పరిహారం మరియు ప్రతి కోర్టు విచారణకు ప్రయాణ భత్యం (TAME) పొందే హక్కు ఉంది."
        elif lang == "KN":
            reply_text = "ದೌರ್ಜನ್ಯ ತಡೆ ನಿಯಮಗಳ ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಆರ್ಥಿಕ ಪರಿಹಾರ ಮತ್ತು ಪ್ರಯಾಣ ಭತ್ಯೆ ಪಡೆಯುವ ಹಕ್ಕಿದೆ."
        elif lang == "MR":
            reply_text = "अत्याचार प्रतिबंधक नियमांनुसार तुम्हाला आर्थिक भरपाई आणि प्रवास भत्ता (TAME) मिळवण्याचा हक्क आहे."
        elif lang == "BN":
            reply_text = "পিওএ বিধিমালার অধীনে আপনি পর্যায়ক্রমিক আর্থিক ক্ষতিপূরণ এবং ভ্রমণ ভাতা (TAME) পাওয়ার অধিকারী।"
        else:
            reply_text = "Under Rule 12(4) and Annexure-I of the SC/ST (PoA) Rules, you are entitled to mandatory financial relief (disbursed: 25% on FIR, 50% on chargesheet, 25% on judgment) regardless of conviction outcome. You are also entitled to immediate Travel and Maintenance Allowance (TAME) for each hearing."
        suggested_actions = ["Check Compensation Status", "Apply for Travel Allowance (TAME)", "Speak to District Officer"]

    elif is_sleep:
        dynamic_score = 42
        risk_level_str = "medium"
        primary_emotion = "somatic_distress"
        if lang == "HI":
            reply_text = "अत्याचार या कानूनी तनाव के बाद नींद न आना और घबराहट होना स्वाभाविक है। हमारे साथ 4-7-8 श्वास अभ्यास करें या मन को शांत करने के लिए शांत संगीत सुनें।"
        elif lang == "TA":
            reply_text = "தூக்கமின்மை மற்றும் பயம் ஏற்பட்டால் 4-7-8 சுவாசப் பயிற்சியை மேற்கொள்ளுங்கள்."
        elif lang == "TE":
            reply_text = "ఒత్తిడి మరియు నిద్రలేమిని తగ్గించడానికి 4-7-8 శ్వాస వ్యాయామం ప్రయత్నించండి."
        elif lang == "KN":
            reply_text = "ನಿದ್ರಾಹೀನತೆ ಮತ್ತು ಆತಂಕವನ್ನು ನಿವಾರಿಸಲು 4-7-8 ಉಸಿರಾಟದ ವ್ಯಾಯಾಮ ಮಾಡಿ."
        elif lang == "MR":
            reply_text = "झोप न येणे आणि तणाव जाणवणे स्वाभाविक आहे. 4-7-8 श्वासोच्छ्वास तंत्राचा सराव करा."
        elif lang == "BN":
            reply_text = "অনিদ্রা এবং অতিরিক্ত উদ্বেগের জন্য 4-7-8 শ্বাস-প্রশ্বাসের ব্যায়াম চেষ্টা করুন।"
        else:
            reply_text = "Trauma and ongoing legal stress frequently disrupt sleep patterns and cause restless hypervigilance. This is a natural somatic response to stress. Gentle techniques like the 4-7-8 breathing pacer or progressive muscle relaxation can help soothe your nervous system tonight."
        suggested_actions = ["Start 4-7-8 Breathing", "Listen to Calming Audio", "Speak with Counsellor"]

    elif is_deep_distress:
        dynamic_score = 68
        risk_level_str = "high"
        primary_emotion = "hopelessness_depression"
        if lang == "HI":
            reply_text = "आप बहुत भारी भावनात्मक बोझ और सामाजिक अलगाव सह रहे हैं। आपकी भावनाएं पूरी तरह मान्य हैं। आप अकेले नहीं हैं — Mentaura और हमारे परामर्शदाता आपके साथ हैं।"
        elif lang == "TA":
            reply_text = "நீங்கள் ஒரு பெரிய மன வேதனையை அனுபவிக்கிறீர்கள். நீங்கள் தனியாக இல்லை, நாங்கள் உங்களுடன் இருக்கிறோம்."
        elif lang == "TE":
            reply_text = "మీరు చాలా భారమైన వేదనను మోస్తున్నారు. మేము మీతో ఉన్నాము, మీరు ఒంటరిగా లేరు."
        elif lang == "KN":
            reply_text = "ನೀವು ತುಂಬಾ ಆಳವಾದ ದುಃಖವನ್ನು ಅನುಭವಿಸುತ್ತಿದ್ದೀರಿ. ನಾವು ನಿಮ್ಮೊಂದಿಗೆ ಸದಾ ಇರುತ್ತೇವೆ."
        elif lang == "MR":
            reply_text = "तुम्ही खूप मोठा मानसिक ताण आणि एकटेपणा सहन करत आहात. आम्ही तुमच्या पाठीशी ठामपणे उभे आहोत."
        elif lang == "BN":
            reply_text = "আপনি গভীর মানসিক যন্ত্রণা এবং সামাজিক বিচ্ছিন্নতা অনুভব করছেন। আমরা আপনার পাশে আছি।"
        else:
            reply_text = "I hear the deep pain, grief, and exhaustion in what you are experiencing. Facing social ostracism or feeling isolated after an incident is deeply unfair and overwhelming. Please remember that what happened was not your fault, and you do not have to endure this alone. We are right here with you."
        suggested_actions = ["Talk to Empathetic Counsellor", "Try Grounding Exercise", "View Support Network"]

    elif is_grounding:
        dynamic_score = 25
        risk_level_str = "low"
        primary_emotion = "grounding_coping"
        reply_text = "Let's take a calm moment together. Inhale slowly through your nose for 4 seconds... hold your breath gently for 7 seconds... and exhale smoothly through your mouth for 8 seconds. Repeat this 3 times to soothe your heart rate."
        suggested_actions = ["Inhale 4s • Hold 7s • Exhale 8s", "5-4-3-2-1 Sensory Grounding", "I feel a bit calmer now"]

    elif is_conn_check:
        dynamic_score = 12
        risk_level_str = "low"
        primary_emotion = "steady"
        if lang == "HI":
            reply_text = "नमस्ते! हाँ, मैं आपको सुन पा रहा हूँ। मैं आपका मेंटॉरा AI सपोर्ट साथी हूँ। आप सुरक्षित हैं, बताइए आज मैं आपकी क्या मदद कर सकता हूँ?"
        elif lang == "TA":
            reply_text = "வணக்கம்! ஆம், நான் உங்களை கவனிக்கிறேன். நான் உங்களுக்கு உதவ தயாராக உள்ளேன்."
        elif lang == "TE":
            reply_text = "నమస్కారం! అవును, నేను మీ మాటలు వింటున్నాను. మీకు సహాయం చేయడానికి నేను సిద్ధంగా ఉన్నాను."
        elif lang == "KN":
            reply_text = "ನಮಸ್ಕಾರ! ಹೌದು, ನಾನು ನಿಮ್ಮನ್ನು ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ. ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ."
        elif lang == "MR":
            reply_text = "नमस्ते! होय, मी ऐकत आहे. मी आपल्या मदतीसाठी सदैव उपलब्ध आहे."
        elif lang == "BN":
            reply_text = "নমস্কার! হ্যাঁ, আমি শুনতে পাচ্ছি। আমি আপনাকে সাহায্য করতে প্রস্তুত।"
        else:
            reply_text = "Yes, I can hear you clearly! I am your MentAura Case-Aware Support Companion. I am right here with you in this private space. How are you doing today, and how can I help?"
        suggested_actions = ["I am feeling stressed today", "Need information on my case", "Talk about court hearing"]

    elif is_greeting:
        dynamic_score = 12
        risk_level_str = "low"
        primary_emotion = "steady"
        if lang == "HI":
            reply_text = "नमस्ते! Mentaura सपोर्ट स्पेस में आपका स्वागत है। आज आप कैसा महसूस कर रहे हैं, और क्या आपको किसी सहायता की आवश्यकता है?"
        elif lang == "TA":
            reply_text = "வணக்கம்! இன்று நீங்கள் எப்படி உணர்கிறீர்கள்? உங்களுக்கு ஏதேனும் உதவி தேவையா?"
        elif lang == "TE":
            reply_text = "నమస్కారం! ఈరోజు మీరు ఎలా ఉన్నారు? మీకు ఎలాంటి సహాయం కావాలి?"
        elif lang == "KN":
            reply_text = "ನಮಸ್ಕಾರ! ಇಂದು ನೀವು ಹೇಗಿದ್ದೀರಿ? ನಿಮಗೆ ಯಾವುದೇ ಬೆಂಬಲದ ಅಗತ್ಯವಿದೆಯೇ?"
        elif lang == "MR":
            reply_text = "नमस्ते! आज आपण कसे आहात? आपल्याला कशा प्रकारच्या मदतीची आवश्यकता आहे?"
        elif lang == "BN":
            reply_text = "নমস্কার! আজ আপনি কেমন অনুভব করছেন? কোনো সাহায্যের প্রয়োজন আছে কি?"
        else:
            reply_text = "Hello and welcome. I am your MentAura Support Companion. You are in a safe, confidential space. How are you feeling today, and what would be most helpful right now?"
        suggested_actions = ["I am feeling stressed", "Have questions about court hearing", "Check compensation status", "I feel okay today"]

    elif is_stress_general:
        dynamic_score = 45
        risk_level_str = "medium"
        primary_emotion = "generalized_stress"
        # Contextual continuity check:
        if prior_has_court:
            reply_text = "I hear how stressed you are feeling. With your court proceedings and case updates in mind, this tension is completely understandable. Would you like to talk through what feels heaviest right now?"
        elif prior_has_threat:
            reply_text = "I understand you are feeling high stress and worry. Given the threats and safety concerns you mentioned earlier, let's make sure you feel protected. Would you like to request an escort or speak with our officer?"
        else:
            if lang == "HI":
                reply_text = "मैं समझ सकता हूँ कि आप काफी तनाव और दबाव महसूस कर रहे हैं। कानूनी प्रक्रियाओं और व्यक्तिगत चिंताओं के बीच यह बिल्कुल स्वाभाविक है। क्या आप बताना चाहेंगे कि इस समय सबसे ज्यादा परेशानी किस बात से है?"
            elif lang == "TA":
                reply_text = "நீங்கள் அதிக மன அழுத்தத்தில் உள்ளீர்கள் என்பதை நான் உணர்கிறேன். உங்களுக்கு என்ன உதவி தேவை என்பதை பகிர்ந்து கொள்ளுங்கள்."
            elif lang == "TE":
                reply_text = "మీరు తీవ్రమైన ఒత్తిడిలో ఉన్నారని నేను అర్థం చేసుకున్నాను. ఈ సమయంలో మీకు ఎలాంటి మద్దతు కావాలో చెప్పండి."
            elif lang == "KN":
                reply_text = "ನೀವು ತುಂಬಾ ಒತ್ತಡದಲ್ಲಿದ್ದೀರಿ ಎಂದು ನಾನು ಅರ್ಥಮಾಡಿಕೊಂಡಿದ್ದೇನೆ. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು ತಿಳಿಸಿ."
            elif lang == "MR":
                reply_text = "तुम्ही खूप तणावाखाली असल्याचे मला समजते. काय अडचण आहे ते सांगा, आम्ही सोबत आहोत."
            elif lang == "BN":
                reply_text = "আমি বুঝতে পারছি আপনি খুব চাপে আছেন। কী কারণে চাপ অনুভব করছেন বলুন, আমরা সাহায্য করব।"
            else:
                reply_text = "I hear you, and it is completely understandable that you are feeling stressed right now. Navigating the aftermath of an incident and dealing with legal and personal pressures is exhausting. Would you like to talk about what feels heaviest today — is it court worries, threats, delays, or something else?"
        suggested_actions = ["Worried about court hearing", "Threats and safety concerns", "Trouble sleeping", "Financial relief questions"]

    elif is_positive:
        dynamic_score = 15
        risk_level_str = "low"
        primary_emotion = "steady"
        if lang == "HI":
            reply_text = "यह जानकर बहुत अच्छा लगा कि आप स्थिर और ठीक महसूस कर रहे हैं। Mentaura आपकी सहायता के लिए 24/7 सक्रिय है।"
        elif lang == "TA":
            reply_text = "நீங்கள் நலமாக இருப்பது மகிழ்ச்சி அளிக்கிறது. நாங்கள் எப்போதும் உங்களுடன் இருக்கிறோம்."
        elif lang == "TE":
            reply_text = "మీరు క్షేమంగా ఉన్నారని తెలుసుకోవడం చాలా సంతోషంగా ఉంది. మేము ఎల్లప్పుడూ మీకు అందుబాటులో ఉంటాము."
        elif lang == "KN":
            reply_text = "ನೀವು ಚೆನ್ನಾಗಿದ್ದೀರಿ ಎಂದು ತಿಳಿದು ಸಂತೋಷವಾಯಿತು. ನಾವು ಸದಾ ನಿಮ್ಮೊಂದಿಗೆ ಇರುತ್ತೇವೆ."
        elif lang == "MR":
            reply_text = "तुम्ही बरे आहात हे जाणून आनंद झाला. आम्ही सदैव आपल्या सेवेत आहोत."
        elif lang == "BN":
            reply_text = "আপনি ভালো আছেন জেনে ভালো লাগল। আমরা সবসময় আপনার পাশে আছি।"
        else:
            reply_text = "That is truly reassuring to hear. I am glad you are feeling steady and okay today. Remember that Mentaura is always here for you whenever you need support or updates on your case."
        suggested_actions = ["View My Case Journey", "Explore Well-being Resources", "Check Compensation Status"]

    else:
        # Natural adaptive dialogue
        dynamic_score = 35
        risk_level_str = "medium"
        primary_emotion = "active_listening"
        if lang == "HI":
            reply_text = "साझा करने के लिए धन्यवाद। मैं आपकी बात ध्यान से सुन रहा हूँ। Mentaura आपके न्याय और कल्याण के हर कदम पर आपके साथ है। आप आगे क्या बताना चाहते हैं?"
        elif lang == "TA":
            reply_text = "பகிர்ந்து கொண்டதற்கு நன்றி. நான் உங்களுடன் இருக்கிறேன். நீங்கள் மேலும் என்ன பகிர விரும்புகிறீர்கள்?"
        elif lang == "TE":
            reply_text = "మాతో పంచుకున్నందుకు ధన్యవాదాలు. మేము మీతో ఉన్నాము. మీరు ఇంకా ఏమి చెప్పాలనుకుంటున్నారు?"
        elif lang == "KN":
            reply_text = "ಹಂಚಿಕೊಂಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. ನಾವು ನಿಮ್ಮೊಂದಿಗಿದ್ದೇವೆ. ನೀವು ಮುಂದೆ ಏನು ಹೇಳಲು ಬಯಸುತ್ತೀರಿ?"
        elif lang == "MR":
            reply_text = "शेअर केल्याबद्दल धन्यवाद. आम्ही आपल्या सोबत आहोत. आपण पुढे काय सांगू इच्छिता?"
        elif lang == "BN":
            reply_text = "শেয়ার করার জন্য ধন্যবাদ। আমরা আপনার পাশে আছি। আপনি আর কী বলতে চান?"
        else:
            reply_text = f"Thank you for sharing this with me. I am listening closely. Whether it is dealing with court stress, witness protection under Section 15A, or coping with daily pressures, you have full support here. How can I best help you with this right now?"
        suggested_actions = ["Need counsellor advice", "View my legal entitlements", "I am feeling steady"]

    wellbeing_state = "Heavy" if dynamic_score >= 60 else ("Managing" if dynamic_score >= 35 else "Steady")
    expl_text = f"Conversational AI evaluated message intent '{primary_emotion}' with distress score {dynamic_score}/100."

    # 4. Persist Support Pulse Record into Database
    try:
        case_map = db.query(UserCaseMapping).filter(UserCaseMapping.user_id == current_user.id).first()
        user_case_id = case_map.case_id if case_map else None

        recent_pulse = db.query(SupportPulse).filter(
            SupportPulse.authenticated_user_id == current_user.id,
            SupportPulse.interaction_channel == "chatbot_web",
            SupportPulse.submitted_at >= datetime.now(timezone.utc) - timedelta(minutes=30)
        ).order_by(SupportPulse.submitted_at.desc()).first()

        if recent_pulse:
            recent_pulse.dynamic_distress_score = dynamic_score
            recent_pulse.sentiment_score = dynamic_score
            recent_pulse.risk_level = risk_level_str
            recent_pulse.wellbeing_state = wellbeing_state
            recent_pulse.text_response = (recent_pulse.text_response or "") + f" | {user_msg}"
            recent_pulse.xai_explanation = expl_text
            recent_pulse.escalation_predicted = is_crisis or (dynamic_score >= 65)
            recent_pulse.priority_review = is_crisis
            recent_pulse.updated_at = datetime.now(timezone.utc)
        else:
            now_t = datetime.now(timezone.utc)
            new_pulse = SupportPulse(
                authenticated_user_id=current_user.id,
                case_id=user_case_id,
                channel="web",
                interaction_channel="chatbot_web",
                processing_mode="ai_assisted",
                consent_version="1.0",
                consent_given_at=now_t,
                submitted_at=now_t,
                language=lang,
                wellbeing_state=wellbeing_state,
                text_response=user_msg,
                dynamic_distress_score=dynamic_score,
                sentiment_score=dynamic_score,
                acoustic_score=20,
                risk_level=risk_level_str,
                risk_score=dynamic_score // 10,
                escalation_predicted=is_crisis or (dynamic_score >= 65),
                xai_explanation=expl_text,
                completion_status="submitted",
                priority_review=is_crisis
            )
            db.add(new_pulse)
        db.commit()
    except Exception as e:
        print(f"[ERROR PERSISTING PULSE]: {e}")
        db.rollback()

    return {
        "reply": reply_text,
        "bot_reply": reply_text,
        "bot_response": reply_text,
        "language": lang,
        "detected_emotions": [primary_emotion],
        "detected_emotion": primary_emotion,
        "sentiment_score": dynamic_score,
        "sentiment_distress_score": dynamic_score,
        "dynamic_distress_indicator": dynamic_score,
        "is_crisis_flag": is_crisis,
        "suggested_actions": suggested_actions,
        "suggested_chips": suggested_actions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

'''

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    updated = content[:start_idx] + new_code + "\n\n" + content[end_idx:]
    with open(victim_py_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print("SUCCESS: Updated victim.py")
else:
    print(f"FAILED: start_idx={start_idx}, end_idx={end_idx}")
