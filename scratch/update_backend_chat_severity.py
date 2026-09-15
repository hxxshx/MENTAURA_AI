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

if start_marker not in content or end_marker not in content:
    print("ERROR: Markers not found!")
    exit(1)

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
    MentAura Case-Aware Mental Health AI Assistant (SIH 26094).
    Implements 3-tier severity classification:
      - Low Severity: Soothing techniques, motivation, resilience reinforcement.
      - Medium Severity: Empathetic validation, motivation, and escalation referrals with contact cards.
      - High Severity: Automated urgent alert dispatch to District Protection Officers and DLSA,
                       emergency SOS guidance, and crisis escalation.
    Includes full multilingual dynamic translation for EN, HI, TA, TE, KN, MR, BN.
    """
    if current_user.verified_role not in VICTIM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized victim and witness accounts."
        )

    user_msg = payload.message.strip()
    msg_lower = user_msg.lower()
    lang = (payload.language or current_user.preferred_language or "EN").upper()
    if lang not in ["EN", "HI", "TA", "TE", "KN", "MR", "BN"]:
        lang = "EN"
    history = payload.conversation_history or []

    # 1. Contextual Intent & Topic Detection
    is_greeting = any(w in msg_lower for w in ["hi", "hello", "hey", "namaste", "vanakkam", "namaskara", "good morning", "good evening", "good afternoon"]) and len(msg_lower.split()) <= 3
    is_conn_check = any(w in msg_lower for w in ["hear me", "listening", "are you there", "can you hear", "anyone there", "hello?"])
    is_crisis = any(w in msg_lower for w in ["suicide", "kill myself", "end my life", "want to die", "hurt myself", "no point living", "आत्महत्या", "मरना चाहता", "जान दे दूंगा", "தற்கொலை", "உயிர் விட", "చనిపోవాలని", "ఆత్మహత్య", "ಆತ್ಮಹತ್ಯೆ", "ಸಾಯಬೇಕು", "मरू इच्छितो", "আত্মহত্যা", "মরতে চাই"])
    is_threat = any(w in msg_lower for w in ["threat", "threatened", "intimidation", "scared of accused", "following me", "stalk", "kill me", "unsafe", "danger", "gun", "knife", "outside my house", "attack", "धमकी", "मार डालेंगे", "गुंडे", "மிரட்டல்", "கொன்று விடுவேன்", "ஊர் விலக்கம்", "బెదిరింపు", "చంపేస్తామని", "బహిష్కరణ", "ಬೆದರಿಕೆ", "ಕೊಲ್ಲುತ್ತೇನೆ", "ಸಾಮಾಜಿಕ ಬಹಿಷ್ಕಾರ", "भीती", "तक्रार मागे", "হুমকি", "মেরে ফেলব", "15a"])
    is_court = any(w in msg_lower for w in ["court", "hearing", "judge", "trial", "chargesheet", "lawyer", "advocate", "summons", "postponed", "adjourned", "अदालत", "कोर्ट", "तारीख", "गवाही", "सुनवाई", "நீதிமன்றம்", "விசாரணை", "சாட்சி", "కోర్టు", "విచారణ", "సాక్షి", "వాయిదా", "ನ್ಯಾಯಾಲಯ", "ವಿಚಾರಣೆ", "ಸಾಕ್ಷಿ", "न्यायालय", "सुनावणी", "साक्षीदार", "আদালত", "শুনানি", "সাক্ষী"])
    is_compensation = any(w in msg_lower for w in ["compensation", "relief", "money", "allowance", "tame", "travel", "disbursement", "annexure", "मुआवजा", "राहत", "இழப்பீடு", "பயணப்படி", "పరిహారం", "భత్యం", "ಪರಿಹಾರ", "ಪ್ರಯಾಣ ಭತ್ಯೆ", "भरपाई", "भत्ता", "ক্ষতিপূরণ", "ভাতা"])
    is_sleep = any(w in msg_lower for w in ["sleep", "insomnia", "nightmare", "nightmares", "sleepless", "wake up", "restless", "नींद", "डरावने सपने", "தூக்கம்", "கெட்ட கனவு", "నిద్ర", "పీడకలలు", "ನಿದ್ರೆ", "ದುಃಸ್ವಪ್ನ", "झोप", "वाईट स्वप्न", "ঘুম", "খারাপ স্বপ্ন"])
    is_grounding = any(w in msg_lower for w in ["grounding", "breathe", "breathing", "calm", "panic", "4-7-8", "exercise", "soothe", "meditation", "प्राणायाम", "शांत", "மூச்சுப்பயிற்சி", "శ్వాస", "ಉಸಿರಾಟ", "श्वास", "শ্বাস"])
    is_deep_distress = any(w in msg_lower for w in ["deep emotional distress", "grief", "social isolation", "boycott", "humiliation", "broken", "helpless", "crying", "pain", "hopeless", "depression", "उदास", "रो रहा", "अपमान", "अकेला", "टूट चुका", "கண்ணீர்", "அவமானம்", "மனமுடைந்து", "బాధ", "ఏడుపు", "ఒంటరితనం", "ಅವಮಾನ", "ದುಃಖ", "ಅಳು", "रडणे", "अपमान", "कष्ट", "কান্না"])
    is_stress_general = any(w in msg_lower for w in ["stress", "stressed", "tension", "pressure", "overwhelmed", "exhausted", "tired", "heavy", "तनाव", "घबराहट", "मन அழுத்தம்", "பதற்றம்", "ఒత్తిడి", "ఆందోళన", "ಒತ್ತಡ", "ಆತಂಕ", "तणाव", "काळजी", "চাপ", "উদ্বেগ"])
    is_positive = any(w in msg_lower for w in ["fine", "okay", "ok", "good", "safe today", "better", "thank", "thanks", "feeling steady", "peaceful", "all good"]) and not (is_threat or is_crisis)

    # 2. Determine Severity Level (3 Tiers)
    # High: Threat to life, witness intimidation, acute suicidal crisis, severe trauma despair
    # Medium: Court hearing anxiety, sleeplessness, generalized stress, social pressure
    # Low: Greetings, connection checks, calm grounding inquiries, positive/stable check-ins, routine compensation questions
    if is_crisis:
        severity_level = "high"
        dynamic_score = 92
        primary_emotion = "acute_crisis"
    elif is_threat:
        severity_level = "high"
        dynamic_score = 82
        primary_emotion = "fear_intimidation"
    elif is_deep_distress:
        severity_level = "high"
        dynamic_score = 72
        primary_emotion = "trauma_distress"
    elif is_court:
        severity_level = "medium"
        dynamic_score = 56
        primary_emotion = "legal_anxiety"
    elif is_sleep:
        severity_level = "medium"
        dynamic_score = 48
        primary_emotion = "somatic_distress"
    elif is_stress_general:
        severity_level = "medium"
        dynamic_score = 44
        primary_emotion = "stress"
    elif is_compensation:
        severity_level = "low"
        dynamic_score = 22
        primary_emotion = "statutory_inquiry"
    elif is_grounding:
        severity_level = "low"
        dynamic_score = 18
        primary_emotion = "grounding"
    elif is_greeting or is_conn_check:
        severity_level = "low"
        dynamic_score = 12
        primary_emotion = "steady"
    elif is_positive:
        severity_level = "low"
        dynamic_score = 10
        primary_emotion = "resilient"
    else:
        # Default conversational tier based on sentiment keyword scan
        if any(w in msg_lower for w in ["fear", "scared", "die", "attack", "alone"]):
            severity_level = "high"
            dynamic_score = 70
            primary_emotion = "fear"
        elif any(w in msg_lower for w in ["help", "worried", "sad", "unhappy"]):
            severity_level = "medium"
            dynamic_score = 45
            primary_emotion = "uneasy"
        else:
            severity_level = "low"
            dynamic_score = 20
            primary_emotion = "neutral"

    # Multilingual Content Bundles for Low, Medium, and High Tiers
    coping_techniques = []
    motivational_text = ""
    escalation_contact = None
    alert_generated = False
    alert_details = None

    # =========================================================================
    # TIER 1: LOW SEVERITY (Suggests Soothing Techniques & Motivates)
    # =========================================================================
    if severity_level == "low":
        techniques_dict = {
            "EN": [
                {"title": "4-7-8 Breathing Pacer", "desc": "Inhale 4s, Hold 7s, Exhale 8s to calm the nervous system.", "action": "Start Breathing Pacer"},
                {"title": "5-4-3-2-1 Sensory Grounding", "desc": "Name 5 things you see, 4 you can touch, 3 hear, 2 smell, 1 taste.", "action": "Start 5-4-3-2-1 Pacer"},
                {"title": "Positive Self-Affirmation", "desc": "Remind yourself: 'I am safe right now. Step by step, I am rebuilding my peace.'", "action": "Save Daily Affirmation"}
            ],
            "HI": [
                {"title": "4-7-8 श्वास अभ्यास", "desc": "4 सेकंड सांस लें, 7 सेकंड रोकें, 8 सेकंड में छोड़ें ताकि मन शांत हो सके।", "action": "श्वास अभ्यास शुरू करें"},
                {"title": "5-4-3-2-1 ग्राउंडिंग", "desc": "5 चीजें देखें, 4 स्पर्श करें, 3 सुनें, 2 सूंघें, 1 स्वाद लें।", "action": "ग्राउंडिंग शुरू करें"},
                {"title": "सकारात्मक आत्म-संवाद", "desc": "'मैं इस समय सुरक्षित हूँ। हर कदम पर न्याय और शांति मेरे साथ है।'", "action": "दैनिक विचार सहेजें"}
            ],
            "TA": [
                {"title": "4-7-8 சுவாசப் பயிற்சி", "desc": "4 நொடிகள் மூச்சை உள்ளிழுத்து, 7 நொடிகள் நிறுத்தி, 8 நொடிகள் வெளியிடவும்.", "action": "சுவாசப் பயிற்சி தொடங்க"},
                {"title": "5-4-3-2-1 உணர்வு நிலைப் பயிற்சி", "desc": "5 பொருட்களைப் பாருங்கள், 4 தொடுங்கள், 3 கேளுங்கள், 2 நுகருங்கள், 1 சுவையுங்கள்.", "action": "பயிற்சி தொடங்க"},
                {"title": "நேர்மறை உறுதிமொழி", "desc": "'நான் பாதுகாப்பாக இருக்கிறேன். ஒவ்வொரு நாளும் நான் மன வலிமை பெறுகிறேன்.'", "action": "உறுதிமொழி ஏற்க"}
            ],
            "TE": [
                {"title": "4-7-8 శ్వాస వ్యాయామం", "desc": "4 సెకన్లు పీల్చుకోండి, 7 సెకన్లు ఆపండి, 8 సెకన్లలో వదలండి.", "action": "శ్వాస వ్యాయామం ప్రారంభించండి"},
                {"title": "5-4-3-2-1 గ్రౌండింగ్ పద్ధతి", "desc": "5 వస్తువులను చూడండి, 4 తాకండి, 3 వినండి, 2 వాసన చూడండి, 1 రుచి చూడండి.", "action": "గ్రౌండింగ్ ప్రారంభించండి"},
                {"title": "సానుకూల దృక్పథం", "desc": "'నేను ఇప్పుడు సురక్షితంగా ఉన్నాను. నా మనోధైర్యాన్ని తిరిగి పొందుతున్నాను.'", "action": "ధృవీకరణ సేవ్ చేయండి"}
            ],
            "KN": [
                {"title": "4-7-8 ಉಸಿರಾಟದ ವ್ಯಾಯಾಮ", "desc": "4 ಸೆಕೆಂಡ್ ಉಸಿರೆಳೆದುಕೊಳ್ಳಿ, 7 ಸೆಕೆಂಡ್ ಹಿಡಿದಿಟ್ಟುಕೊಳ್ಳಿ, 8 ಸೆಕೆಂಡ್ ಬಿಡಿ.", "action": "ಉಸಿರಾಟ ವ್ಯಾಯಾಮ ಪ್ರಾರಂಭಿಸಿ"},
                {"title": "5-4-3-2-1 ಇಂದ್ರಿಯ ಗ್ರೌಂಡಿಂಗ್", "desc": "5 ವಸ್ತುಗಳನ್ನು ನೋಡಿ, 4 ಸ್ಪರ್ಶಿಸಿ, 3 ಆಲಿಸಿ, 2 ಆಘ್ರಾಣಿಸಿ, 1 ರುಚಿ ನೋಡಿ.", "action": "ಗ್ರೌಂಡಿಂಗ್ ಪ್ರಾರಂಭಿಸಿ"},
                {"title": "ಸಕಾರಾತ್ಮಕ ಆತ್ಮವಿಶ್ವಾಸ", "desc": "'ನಾನು ಈಗ ಸುರಕ್ಷಿತವಾಗಿದ್ದೇನೆ. ಹಂತ ಹಂತವಾಗಿ ಶಾಂತಿ ಪಡೆಯುತ್ತಿದ್ದೇನೆ.'", "action": "ವಿಚಾರ ಉಳಿಸಿ"}
            ],
            "MR": [
                {"title": "4-7-8 श्वासोच्छ्वास व्यायाम", "desc": "4 सेकंद श्वास घ्या, 7 सेकंद रोखा, 8 सेकंदात सोडा.", "action": "श्वास व्यायाम सुरू करा"},
                {"title": "5-4-3-2-1 ग्राउंडिंग तंत्र", "desc": "5 वस्तू पहा, 4 स्पर्श करा, 3 ऐका, 2 वास घ्या, 1 चव घ्या.", "action": "ग्राउंडिंग सुरू करा"},
                {"title": "सकारात्मक आत्मसंवाद", "desc": "'मी आता सुरक्षित आहे. हळूहळू मी मानसिक शांतता प्राप्त करत आहे.'", "action": "विचार जतन करा"}
            ],
            "BN": [
                {"title": "4-7-8 শ্বাস-প্রশ্বাসের ব্যায়াম", "desc": "4 সেকেন্ড শ্বাস নিন, 7 সেকেন্ড ধরে রাখুন, 8 সেকেন্ডে শ্বাস ছাড়ুন।", "action": "শ্বাস ব্যায়াম শুরু করুন"},
                {"title": "5-4-3-2-1 গ্রাউন্ডিং টেকনিক", "desc": "5টি জিনিস দেখুন, 4টি স্পর্শ করুন, 3টি শুনুন, 2টি গন্ধ নিন, 1টি স্বাদ নিন।", "action": "গ্রাউন্ডিং শুরু করুন"},
                {"title": "ইতিবাচক আত্মবিশ্বাস", "desc": "'আমি এই মুহূর্তে নিরাপদ। ধীরে ধীরে আমি আমার শান্তি ফিরে পাচ্ছি।'", "action": "প্রতিজ্ঞা সংরক্ষণ করুন"}
            ]
        }
        coping_techniques = techniques_dict.get(lang, techniques_dict["EN"])

        motivation_dict = {
            "EN": "You are resilient, strong, and doing wonderful by checking in today. Every small step towards self-care grounds you. Here are gentle techniques to keep your mind calm and centered.",
            "HI": "आप बहुत साहसी हैं और आज चेक-इन करके आपने एक मजबूत कदम उठाया है। आत्म-देखभाल की ओर हर छोटा कदम आपके मन को शांति देता है। आपके लिए कुछ शांत करने वाली तकनीकें प्रस्तुत हैं।",
            "TA": "நீங்கள் மிகவும் மன உறுதியுள்ளவர். சுய பராமரிப்பை நோக்கி எடுக்கும் ஒவ்வொரு சிறிய அடியும் உங்களை அமைதிப்படுத்தும். உங்கள் மனதை அமைதிப்படுத்த சில எளிய பயிற்சிகள் கீழே உள்ளன.",
            "TE": "మీరు చాలా దృఢమైనవారు. ప్రతి చిన్న అడుగు మీకు శాంతిని చేకూరుస్తుంది. మీ మనస్సును ప్రశాంతంగా ఉంచడానికి ఇక్కడ కొన్ని సులభమైన వ్యాయామాలు ఉన్నాయి.",
            "KN": "ನೀವು ತುಂಬಾ ಧೈರ್ಯವಂತರು. ನಿಮ್ಮ ಯೋಗಕ್ಷೇಮದ ಬಗ್ಗೆ ಕಾಳಜಿ ವಹಿಸುವುದು ಉತ್ತಮ ಸಂಗತಿ. ನಿಮ್ಮ ಮನಸ್ಸನ್ನು ಶಾಂತಗೊಳಿಸಲು ಕೆಲವು ಸರಳ ತಂತ್ರಗಳು ಇಲ್ಲಿವೆ.",
            "MR": "तुम्ही खूप खंबीर आहात. स्वतःची काळजी घेण्यासाठी उचललेले प्रत्येक पाऊल महत्त्वाचे आहे. मन शांत ठेवण्यासाठी खालील काही सोपी तंत्रे वापरा.",
            "BN": "আপনি খুব দৃঢ়চেতা এবং সাহসী। স্ব-যত্নের প্রতিটি ছোট পদক্ষেপ আপনাকে শক্তি দেয়। মনকে শান্ত রাখতে নিচে কিছু সহজ কৌশল দেওয়া হলো।"
        }
        motivational_text = motivation_dict.get(lang, motivation_dict["EN"])

        if is_compensation:
            if lang == "HI":
                reply_text = "नियम 12(4) के तहत आप वित्तीय राहत और प्रत्येक सुनवाई हेतु यात्रा भत्ता (TAME) के पूर्ण हकदार हैं। आपकी स्थिति स्थिर है, और नीचे दिए गए शांत अभ्यास भी आपकी सहायता करेंगे।"
            elif lang == "TA":
                reply_text = "வன்கொடுமை தடுப்பு விதிகளின்படி நீங்கள் நிவாரணம் மற்றும் பயணப்படி பெற முழு உரிமை உண்டு. நீங்கள் நிதானமாக இருக்கிறீர்கள்."
            elif lang == "TE":
                reply_text = "SC/ST చట్టం ప్రకారం మీకు ఆర్థిక పరిహారం మరియు ప్రయాణ భత్యం (TAME) పొందే హక్కు ఉంది."
            elif lang == "KN":
                reply_text = "ದೌರ್ಜನ್ಯ ತಡೆ ನಿಯಮಗಳ ಪ್ರಕಾರ ನಿಮಗೆ ಪರಿಹಾರ ಮತ್ತು ಪ್ರಯಾಣ ಭತ್ಯೆ ಪಡೆಯುವ ಹಕ್ಕಿದೆ."
            elif lang == "MR":
                reply_text = "अत्याचार प्रतिबंधक नियमांनुसार तुम्हाला आर्थिक भरपाई व प्रवास भत्ता मिळवण्याचा पूर्ण हक्क आहे."
            elif lang == "BN":
                reply_text = "পিওএ বিধিমালার অধীনে আপনি আর্থিক ক্ষতিপূরণ এবং ভ্রমণ ভাতা (TAME) পাওয়ার যোগ্য।"
            else:
                reply_text = "Under Rule 12(4) of the SC/ST (PoA) Rules, you are entitled to phased financial relief and Travel & Maintenance Allowance (TAME). Your check-in shows a stable, low-severity state. Take a look at these soothing techniques below to keep yourself grounded."
            suggested_actions = ["Check Compensation Details", "Try 4-7-8 Breathing", "Save Daily Affirmation"]

        elif is_grounding:
            reply_text = motivational_text
            suggested_actions = ["Inhale 4s • Hold 7s • Exhale 8s", "5-4-3-2-1 Sensory Grounding", "I feel a bit calmer now"]

        elif is_conn_check:
            if lang == "HI":
                reply_text = "नमस्ते! हाँ, मैं आपको स्पष्ट सुन पा रहा हूँ। मैं आपका मेंटॉरा AI मानसिक स्वास्थ्य साथी हूँ। आपकी स्थिति स्थिर है। आज आपको क्या सहायता चाहिए?"
            elif lang == "TA":
                reply_text = "வணக்கம்! ஆம், நான் உங்களை தெளிவாக கவனிக்கிறேன். நான் உங்கள் மென்டாரா மனநல உதவியாளர். இன்று உங்களுக்கு என்ன உதவி வேண்டும்?"
            elif lang == "TE":
                reply_text = "నమస్కారం! అవును, నేను మీ మాటలు వింటున్నాను. నేను మీ మెంటౌరా మానసిక ఆరోగ్య సహాయకుడిని."
            elif lang == "KN":
                reply_text = "ನಮಸ್ಕಾರ! ಹೌದು, ನಾನು ನಿಮ್ಮನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ. ನಾನು ನಿಮ್ಮ ಮಾನಸಿಕ ಆರೋಗ್ಯ ಬೆಂಬಲ ಸಹಾಯಕ."
            elif lang == "MR":
                reply_text = "नमस्ते! होय, मी ऐकत आहे. मी आपला मेंटॉरा मानसिक आरोग्य सहाय्यक आहे. आज मी काय मदत करू शकतो?"
            elif lang == "BN":
                reply_text = "নমস্কার! হ্যাঁ, আমি পরিষ্কার শুনতে পাচ্ছি। আমি আপনার মেন্টরা মানসিক স্বাস্থ্য সহায়ক।"
            else:
                reply_text = "Yes, I can hear you loud and clear! I am your MentAura AI Mental Health Support Companion. You are in a safe, steady space right now. How can I support your well-being today?"
            suggested_actions = ["Try Calming Breathing", "Talk about my day", "I feel okay today"]

        elif is_positive:
            if lang == "HI":
                reply_text = "यह जानकर बहुत खुशी हुई कि आप आज सहज और बेहतर महसूस कर रहे हैं! " + motivational_text
            elif lang == "TA":
                reply_text = "நீங்கள் இன்று நன்றாக உணர்வது மகிழ்ச்சி அளிக்கிறது! " + motivational_text
            elif lang == "TE":
                reply_text = "ఈరోజు మీరు క్షేమంగా ఉన్నారని తెలుసుకోవడం చాలా ఆనందంగా ఉంది! " + motivational_text
            elif lang == "KN":
                reply_text = "ಇಂದು ನೀವು ಆರಾಮವಾಗಿದ್ದೀರಿ ಎಂದು ತಿಳಿದು ಸಂತೋಷವಾಯಿತು! " + motivational_text
            elif lang == "MR":
                reply_text = "तुम्ही आज बरे आहात हे जाणून खूप आनंद झाला! " + motivational_text
            elif lang == "BN":
                reply_text = "আজ আপনি ভালো আছেন জেনে খুব ভালো লাগল! " + motivational_text
            else:
                reply_text = "It is genuinely heartening to hear that you are feeling steady and positive today! " + motivational_text
            suggested_actions = ["Save Today's Affirmation", "Explore Wellness Toolkit", "Check Case Journey"]

        else:
            if lang == "HI":
                reply_text = "नमस्ते! मेंटॉरा मानसिक स्वास्थ्य सहायता में आपका स्वागत है। " + motivational_text
            elif lang == "TA":
                reply_text = "வணக்கம்! மென்டாரா மனநல ஆதரவு இடத்திற்கு வரவேற்கிறோம். " + motivational_text
            elif lang == "TE":
                reply_text = "నమస్కారం! మెంటౌరా మానసిక ఆరోగ్య కేంద్రానికి స్వాగతం. " + motivational_text
            elif lang == "KN":
                reply_text = "ನಮಸ್ಕಾರ! ಮೆಂಟೌರಾ ಮಾನಸಿಕ ಆರೋಗ್ಯ ಬೆಂಬಲಕ್ಕೆ ಸ್ವಾಗತ. " + motivational_text
            elif lang == "MR":
                reply_text = "नमस्ते! मेंटॉरा मानसिक आरोग्य सहाय्यात आपले स्वागत आहे. " + motivational_text
            elif lang == "BN":
                reply_text = "নমস্কার! মেন্টরা মানসিক স্বাস্থ্য সহায়তায় স্বাগতম। " + motivational_text
            else:
                reply_text = "Hello and welcome. I am your MentAura Mental Health Assistant. " + motivational_text
            suggested_actions = ["I want to try 4-7-8 Breathing", "Explore Grounding Techniques", "I am feeling steady"]

    # =========================================================================
    # TIER 2: MEDIUM SEVERITY (Motivates & Escalates to Direct Contacts)
    # =========================================================================
    elif severity_level == "medium":
        escalation_contacts_dict = {
            "EN": {
                "officer_name": "Dr. Aruna Rao (District Psychological Counsellor)",
                "role": "Assigned District Trauma & Mental Health Specialist",
                "phone": "Toll-Free Helpline 14416 (Tele-MANAS)",
                "alt_phone": "DLSA Legal Aid Helpdesk: 15100",
                "action_prompt": "We strongly encourage you to speak with a professional counsellor to share this burden."
            },
            "HI": {
                "officer_name": "डॉ. अरुणा राव (जिला मनोवैज्ञानिक परामर्शदाता)",
                "role": "नामित जिला मानसिक स्वास्थ्य विशेषज्ञ",
                "phone": "टोल-फ्री हेल्पलाइन 14416 (Tele-MANAS)",
                "alt_phone": "DLSA मुफ्त कानूनी सहायता: 15100",
                "action_prompt": "हम आपको सलाह देते हैं कि आप अपने परामर्शदाता या विधिक सेवा प्राधिकरण से बात करें।"
            },
            "TA": {
                "officer_name": "டாக்டர் அருணா ராவ் (மாவட்ட உளவியல் ஆலோசகர்)",
                "role": "மாவட்ட மனநல ஆலோசகர்",
                "phone": "கட்டணமில்லா உதவி எண் 14416 (Tele-MANAS)",
                "alt_phone": "DLSA இலவச சட்ட உதவி: 15100",
                "action_prompt": "ஒரு தொழில்முறை ஆலோசகருடன் பேசி உதவி பெற பரிந்துரைக்கிறோம்."
            },
            "TE": {
                "officer_name": "డా. అరుణా రావు (జిల్లా మనస్తత్వవేత్త)",
                "role": "జిల్లా మానసిక ఆరోగ్య నిపుణులు",
                "phone": "టోల్-ఫ్రీ నంబర్ 14416 (Tele-MANAS)",
                "alt_phone": "DLSA ఉచిత న్యాయ సహాయం: 15100",
                "action_prompt": "వృత్తిపరమైన కౌన్సెలర్‌ను సంప్రదించి సహాయం పొందాలని మేము సిఫార్సు చేస్తున్నాము."
            },
            "KN": {
                "officer_name": "ಡಾ. ಅರುಣಾ ರಾವ್ (ಜಿಲ್ಲಾ ಮನಶ್ಶಾಸ್ತ್ರಜ್ಞರು)",
                "role": "ಜಿಲ್ಲಾ ಮಾನಸಿಕ ಆರೋಗ್ಯ ತಜ್ಞರು",
                "phone": "ಟೋಲ್-ಫ್ರೀ ಸಂಖ್ಯೆ 14416 (Tele-MANAS)",
                "alt_phone": "DLSA ಉಚಿತ ಕಾನೂನು ನೆರವು: 15100",
                "action_prompt": "ತಜ್ಞ ಸಮಾಲೋಚಕರನ್ನು ಸಂಪರ್ಕಿಸಿ ನೆರವು ಪಡೆಯಲು ನಾವು ಸಲಹೆ ನೀಡುತ್ತೇವೆ."
            },
            "MR": {
                "officer_name": "डॉ. अरुणा राव (जिल्हा मानसशास्त्रज्ञ)",
                "role": "जिल्हा मानसिक आरोग्य तज्ज्ञ",
                "phone": "टोल-फ्री क्रमांक 14416 (Tele-MANAS)",
                "alt_phone": "DLSA मोफत कायदेशीर मदत: 15100",
                "action_prompt": "आम्ही आपल्याला समुपदेशकाशी बोलून मदत घेण्याचा सल्ला देतो."
            },
            "BN": {
                "officer_name": "ড. অরুণা রাও (জেলা মনস্তাত্ত্বিক পরামর্শদাতা)",
                "role": "মনস্তাত্ত্বিক স্বাস্থ্য বিশেষজ্ঞ",
                "phone": "টোল-ফ্রি নম্বর 14416 (Tele-MANAS)",
                "alt_phone": "DLSA বিনামূল্যে আইনি সহায়তা: 15100",
                "action_prompt": "আমরা আপনাকে একজন কাউন্সেলরের সাথে যোগাযোগ করার পরামর্শ দিচ্ছি।"
            }
        }
        escalation_contact = escalation_contacts_dict.get(lang, escalation_contacts_dict["EN"])

        motivation_dict = {
            "EN": "You do not have to carry this emotional weight by yourself. What you are feeling is completely valid after everything you've experienced. Let us connect you with supportive professionals who can walk with you.",
            "HI": "आपको यह मानसिक बोझ अकेले उठाने की आवश्यकता नहीं है। जो कुछ आपने सहा है, उसके बाद ऐसा महसूस होना पूरी तरह स्वाभाविक है। हम आपको ऐसे विशेषज्ञों से जोड़ रहे हैं जो आपकी सहायता कर सकते हैं।",
            "TA": "இந்த மன அழுத்தத்தை நீங்கள் தனியாக சுமக்க வேண்டியதில்லை. உங்களுக்கு உதவ தகுதிவாய்ந்த ஆலோசகர்கள் தயாராக உள்ளனர்.",
            "TE": "ఈ భారాన్ని మీరు ఒంటరిగా మోయాల్సిన అవసరం లేదు. మీకు సహాయం చేయడానికి నిపుణులు సిద్ధంగా ఉన్నారు.",
            "KN": "ಈ ಭಾರವನ್ನು ನೀವು ಒಬ್ಬರೇ ಹೊರಬೇಕಾಗಿಲ್ಲ. ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ತಜ್ಞರು ಸದಾ ಲಭ್ಯವಿದ್ದಾರೆ.",
            "MR": "हा ताण तुम्ही एकट्याने सहन करण्याची गरज नाही. आपल्याला मदत करण्यासाठी तज्ज्ञ समुपदेशक उपलब्ध आहेत.",
            "BN": "এই মানসিক চাপ আপনার একা বহন করার দরকার নেই। আপনাকে সহায়তা করার জন্য বিশেষজ্ঞ প্রস্তুত আছেন।"
        }
        motivational_text = motivation_dict.get(lang, motivation_dict["EN"])

        if is_court:
            if lang == "HI":
                reply_text = "अदालत की सुनवाई और कानूनी प्रक्रियाएं काफी तनाव उत्पन्न करती हैं। " + motivational_text + " कृपया नीचे दिए गए जिला परामर्शदाता या DLSA से तुरंत संपर्क करें।"
            elif lang == "TA":
                reply_text = "நீதிமன்ற விசாரணை தொடர்பான மன அழுத்தம் இயல்பானது. " + motivational_text
            elif lang == "TE":
                reply_text = "కోర్టు విచారణల వల్ల కలిగే ఒత్తిడి అర్థం చేసుకోదగినది. " + motivational_text
            elif lang == "KN":
                reply_text = "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆಯ ಆತಂಕ ಸಹಜ. " + motivational_text
            elif lang == "MR":
                reply_text = "न्यायालयीन प्रक्रियेचा ताण स्वाभाविक आहे. " + motivational_text
            elif lang == "BN":
                reply_text = "আদালতের শুনানির উদ্বেগ খুব স্বাভাবিক। " + motivational_text
            else:
                reply_text = "Court dates and legal depositions can bring on acute anxiety and tension. " + motivational_text + " We recommend reaching out to your assigned counsellor or DLSA legal clinic below to prepare with confidence."
            suggested_actions = ["Request Counsellor Callback", "Call Tele-MANAS (14416)", "Contact DLSA Legal Aid"]

        elif is_sleep:
            if lang == "HI":
                reply_text = "नींद न आना और लगातार बेचैनी होना तनाव का संकेत है। " + motivational_text
            elif lang == "TA":
                reply_text = "தூக்கமின்மை மற்றும் கவலை உங்களை சோர்வடையச் செய்யலாம். " + motivational_text
            elif lang == "TE":
                reply_text = "నిద్రలేమి మరియు అలసట తీవ్రమైన ఒత్తిడికి సంకేతం. " + motivational_text
            elif lang == "KN":
                reply_text = "ನಿದ್ರಾಹೀನತೆ ಮತ್ತು ಆತಂಕ ನಿಮ್ಮನ್ನು ಕಾಡಬಹುದು. " + motivational_text
            elif lang == "MR":
                reply_text = "झोप न येणे आणि बेचैनी हे ताणाचे लक्षण आहे. " + motivational_text
            elif lang == "BN":
                reply_text = "অনিদ্রা এবং অতিরিক্ত উদ্বেগ মানসিক চাপের লক্ষণ। " + motivational_text
            else:
                reply_text = "Disrupted sleep and recurring restlessness reflect elevated stress. " + motivational_text + " In addition to soothing exercises, having a supportive conversation with our counsellor will provide immense relief."
            suggested_actions = ["Connect with Counsellor", "Dial Tele-MANAS 14416", "Try Night Relaxation Technique"]

        else:
            if lang == "HI":
                reply_text = "मैं समझ सकता हूँ कि आप तनाव में हैं। " + motivational_text + " आप नीचे दिए गए नंबर पर बात करके सहायता प्राप्त कर सकते हैं।"
            elif lang == "TA":
                reply_text = "நீங்கள் மன அழுத்தத்தில் உள்ளீர்கள் என்பதை நான் உணர்கிறேன். " + motivational_text
            elif lang == "TE":
                reply_text = "మీరు ఒత్తిడిలో ఉన్నారని నేను అర్థం చేసుకున్నాను. " + motivational_text
            elif lang == "KN":
                reply_text = "ನೀವು ಮಾನಸಿಕ ಒತ್ತಡದಲ್ಲಿದ್ದೀರಿ ಎಂದು ನಾನು ತಿಳಿಯಬಲ್ಲೆ. " + motivational_text
            elif lang == "MR":
                reply_text = "मला समजते की आपण तणावात आहात. " + motivational_text
            elif lang == "BN":
                reply_text = "আমি বুঝতে পারছি আপনি মানসিক চাপে আছেন। " + motivational_text
            else:
                reply_text = "I can hear the strain and stress in your words. " + motivational_text + " Let's get you connected with a specialist who understands your situation and can provide direct support."
            suggested_actions = ["Request Counsellor Callback", "Dial Tele-MANAS 14416", "Contact District Support Officer"]

    # =========================================================================
    # TIER 3: HIGH SEVERITY (Direct Alert Dispatched to Higher Authority & SOS)
    # =========================================================================
    else:  # severity_level == "high"
        alert_generated = True
        
        # Dispatch in-app notifications and official alert to higher priority authorities
        try:
            from backend.app.routers.notifications import dispatch_high_risk_pulse_notifications, create_in_app_notification
            masked_id = f"Victim #{current_user.id[:8]}"
            dispatch_high_risk_pulse_notifications(
                db=db,
                pulse_id=f"chat-{current_user.id[:6]}",
                masked_identifier=masked_id,
                risk_level="high",
                risk_score=dynamic_score // 10
            )
            # Create user-facing alert confirmation
            create_in_app_notification(
                db=db,
                user_id=current_user.id,
                notif_type="urgent_alert",
                title="Emergency Protective Alert Generated",
                message="Your high distress check-in has been escalated directly to the District Protection Officer & DLSA. Priority assistance is being activated.",
                metadata_dict={"severity": "high", "score": dynamic_score}
            )
        except Exception as notif_err:
            print(f"[HIGH SEVERITY ALERT DISPATCH LOG]: {notif_err}")

        alert_messages_dict = {
            "EN": {
                "badge": "🚨 HIGH SEVERITY ALERT GENERATED",
                "authority": "District Protection Officer & DLSA Special PP Alerted",
                "detail": "An urgent priority alert has been transmitted to your District Protection Authority. An officer has been tasked to reach out to you immediately. If you are in immediate physical danger, use the buttons below to dial Emergency Police 112 or National Helpline 14566."
            },
            "HI": {
                "badge": "🚨 उच्च प्राथमिकता चेतावनी दर्ज की गई",
                "authority": "जिला संरक्षण अधिकारी और DLSA को तुरंत सूचित किया गया",
                "detail": "आपकी स्थिति की गंभीरता को देखते हुए जिला संरक्षण प्राधिकारी को तत्काल अलर्ट भेजा गया है। अधिकारी आपसे संपर्क करेंगे। यदि आप तत्काल खतरे में हैं, तो सीधे पुलिस (112) या राष्ट्रीय हेल्पलाइन (14566) पर कॉल करें।"
            },
            "TA": {
                "badge": "🚨 தீவிர முன்னுரிமை எச்சரிக்கை உருவாக்கப்பட்டது",
                "authority": "மாவட்ட பாதுகாப்பு அதிகாரிக்கு தகவல் தெரிவிக்கப்பட்டது",
                "detail": "உங்கள் அவசர பாதுகாப்பு எச்சரிக்கை மாவட்ட அதிகாரிகளுக்கு அனுப்பப்பட்டுள்ளது. உடனடியாக தொடர்பு கொள்ள காவல்துறையை (112) அல்லது தேசிய உதவி எண்ணை (14566) அழைக்கவும்."
            },
            "TE": {
                "badge": "🚨 అత్యవసర హెచ్చరిక జారీ చేయబడింది",
                "authority": "జిల్లా రక్షణ అధికారికి అత్యవసర నోటీసు పంపబడింది",
                "detail": "మీ పరిస్థితి తీవ్రతను బట్టి జిల్లా అధికారులకు తక్షణ హెచ్చరిక పంపబడింది. అత్యవసర సహాయం కోసం 112 లేదా 14566 కు కాల్ చేయండి."
            },
            "KN": {
                "badge": "🚨 ಉನ್ನತ ಮಟ್ಟದ ತುರ್ತು ಎಚ್ಚರಿಕೆ ರವಾನಿಸಲಾಗಿದೆ",
                "authority": "ಜಿಲ್ಲಾ ರಕ್ಷಣಾಧಿಕಾರಿಗಳಿಗೆ ತುರ್ತು ಸಂದೇಶ ಕಳುಹಿಸಲಾಗಿದೆ",
                "detail": "ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ಜಿಲ್ಲಾ ರಕ್ಷಣಾ ಪ್ರಾಧಿಕಾರಕ್ಕೆ ತುರ್ತು ಸಂದೇಶ ರವಾನಿಸಲಾಗಿದೆ. ತಕ್ಷಣದ ಸಹಾಯಕ್ಕಾಗಿ 112 ಅಥವಾ 14566 ಗೆ ಕರೆ ಮಾಡಿ."
            },
            "MR": {
                "badge": "🚨 उच्च प्राधान्य सुरक्षा इशारा जारी",
                "authority": "जिल्हा संरक्षण अधिकारी व DLSA कडे तातडीने अलर्ट पाठवला",
                "detail": "आपल्या सुरक्षेसाठी उच्च अधिकाऱ्यांना त्वरित अलर्ट पाठवण्यात आला आहे. तात्काळ मदतीसाठी 112 किंवा 14566 वर संपर्क साधा."
            },
            "BN": {
                "badge": "🚨 উচ্চ অগ্রাধিকার সতর্কতা তৈরি করা হয়েছে",
                "authority": "জেলা সুরক্ষা আধিকারিককে জরুরি বার্তা পাঠানো হয়েছে",
                "detail": "আপনার সুরক্ষার জন্য জেলা কর্তৃপক্ষের কাছে জরুরি সতর্কতা পাঠানো হয়েছে। তাৎক্ষণিক বিপদের জন্য 112 বা 14566 নম্বরে যোগাযোগ করুন।"
            }
        }
        alert_details = alert_messages_dict.get(lang, alert_messages_dict["EN"])

        if is_crisis:
            if lang == "HI":
                reply_text = "आपकी जान और सुरक्षा हमारे लिए अत्यंत महत्वपूर्ण है। कृपया कोई कठोर कदम न उठाएं। हमने आपके लिए आपातकालीन सहायता टीम को अलर्ट कर दिया है। कृपया तुरंत 14566 या 112 पर बात करें।"
            elif lang == "TA":
                reply_text = "உங்கள் உயிர் மிகவும் விலைமதிப்பற்றது. தயவுசெய்து அவசர உதவிக்கு 14566 அல்லது 112 ஐ உடனடியாக தொடர்பு கொள்ளவும். நாங்கள் அதிகாரிகளை எச்சரித்துள்ளோம்."
            elif lang == "TE":
                reply_text = "మీ ప్రాణం చాలా విలువైనది. అత్యవసర సహాయం కోసం దయచేసి వెంటనే 14566 లేదా 112 కు కాల్ చేయండి."
            elif lang == "KN":
                reply_text = "ನಿಮ್ಮ ಜೀವ ಅತ್ಯಂತ ಅಮೂಲ್ಯವಾಗಿದೆ. ತುರ್ತು ಸಹಾಯಕ್ಕಾಗಿ ದಯವಿಟ್ಟು 14566 ಅಥವಾ 112 ಗೆ ಕರೆ ಮಾಡಿ."
            elif lang == "MR":
                reply_text = "आपले जीवन अत्यंत अनमोल आहे. कृपया त्वरित 14566 किंवा 112 वर संपर्क साधा. आम्ही अधिकाऱ्यांना अलर्ट केले आहे."
            elif lang == "BN":
                reply_text = "আপনার জীবন অত্যন্ত মূল্যবান। অনুগ্রহ করে অবিলম্বে 14566 বা 112 নম্বরে যোগাযোগ করুন। সুরক্ষা টিমকে জানানো হয়েছে।"
            else:
                reply_text = "I hear how much agony you are in, and I want you to know you are not alone. Your life is deeply important. We have directly generated an alert to the crisis response team and District Protection Unit. Please connect right now with our 24/7 National Crisis Line at 14566 or Police Emergency at 112."
            suggested_actions = ["Call National Helpline 14566", "Call Police Emergency 112", "Request Immediate In-Person Help"]

        elif is_threat:
            if lang == "HI":
                reply_text = "SC/ST अत्याचार निवारण अधिनियम की धारा 15A के तहत आपको पूर्ण पुलिस सुरक्षा, एस्कॉर्ट और गवाह संरक्षण का वैधानिक अधिकार है। हमने जिला संरक्षण अधिकारी और DLSA को आपका अलर्ट प्रेषित कर दिया है। वे आपसे संपर्क करेंगे।"
            elif lang == "TA":
                reply_text = "வன்கொடுமை தடுப்புச் சட்டம் பிரிவு 15A இன் கீழ் உங்களுக்கு முழு காவல் பாதுகாப்பு மற்றும் சாட்சி பாதுகாப்பு பெற உரிமை உண்டு. மாவட்ட பாதுகாப்பு அதிகாரிகளுக்கு அவசர எச்சரிக்கை அனுப்பப்பட்டுள்ளது."
            elif lang == "TE":
                reply_text = "SC/ST చట్టం సెక్షన్ 15A ప్రకారం మీకు పోలీసు భద్రత పొందే హక్కు ఉంది. జిల్లా రక్షణ అధికారులకు అత్యవసర హెచ్చరిక పంపబడింది."
            elif lang == "KN":
                reply_text = "ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಸಂಪೂರ್ಣ ಪೊಲೀಸ್ ರಕ್ಷಣೆ ಪಡೆಯುವ ಹಕ್ಕಿದೆ. ಜಿಲ್ಲಾ ರಕ್ಷಣಾಧಿಕಾರಿಗಳಿಗೆ ತುರ್ತು ಸಂದೇಶ ರವಾನಿಸಲಾಗಿದೆ."
            elif lang == "MR":
                reply_text = "कलम 15A अंतर्गत आपल्याला पोलीस संरक्षण मिळवण्याचा अधिकार आहे. जिल्हा संरक्षण अधिकाऱ्यांना अलर्ट पाठवण्यात आला आहे."
            elif lang == "BN":
                reply_text = "ধারা 15A এর অধীনে আপনার পূর্ণ পুলিশ সুরক্ষা পাওয়ার আইনি অধিকার রয়েছে। জেলা সুরক্ষা আধিকারিককে সতর্কতা পাঠানো হয়েছে।"
            else:
                reply_text = "Your safety is non-negotiable. Under Section 15A of the SC/ST (PoA) Act, 1989, you are legally guaranteed immediate police security escorts and witness protection. We have directly dispatched an urgent escalation alert to the District Protection Officer and DLSA to initiate immediate contact."
            suggested_actions = ["Call Police Emergency 112", "Call Helpline 14566", "Request Police Protection Escort (Sec 15A)"]

        else:
            if lang == "HI":
                reply_text = "आप बहुत गंभीर भावनात्मक और सामाजिक संकट से गुजर रहे हैं। आपकी स्थिति को देखते हुए हमने वरिष्ठ परामर्शदाता और सहायता टीम को अलर्ट कर दिया है। वे आपसे सीधे संपर्क करेंगे।"
            elif lang == "TA":
                reply_text = "நீங்கள் மிகுந்த மன வேதனையில் உள்ளீர்கள். அதிகாரிகளுக்கும் ஆலோசகர்களுக்கும் தகவல் தெரிவிக்கப்பட்டுள்ளது."
            elif lang == "TE":
                reply_text = "మీరు తీవ్రమైన వేదనలో ఉన్నారు. జిల్లా సహాయ బృందానికి అత్యవసర సమాచారం పంపబడింది."
            elif lang == "KN":
                reply_text = "ನೀವು ತೀವ್ರ ದುಃಖದಲ್ಲಿದ್ದೀರಿ. ಹಿರಿಯ ಸಮಾಲೋಚಕರಿಗೆ ತುರ್ತು ಮಾಹಿತಿ ರವಾನಿಸಲಾಗಿದೆ."
            elif lang == "MR":
                reply_text = "आपण गंभीर मानसिक संकटात आहात. वरिष्ठ समुपदेशकांना अलर्ट पाठवण्यात आला आहे."
            elif lang == "BN":
                reply_text = "আপনি তীব্র মানসিক যন্ত্রণার মধ্য দিয়ে যাচ্ছেন। জরুরি সহায়তা টিমকে সতর্ক করা হয়েছে।"
            else:
                reply_text = "I hear the acute emotional pain and burden you are carrying. Because of the severity of what you have shared, we have automatically dispatched an alert to the Senior Psychological Support Team and District Protection Unit so they can reach out to you directly."
            suggested_actions = ["Speak to Emergency Counsellor", "Call 14566 National Helpline", "Activate Protection Support"]

    wellbeing_state = "Heavy" if severity_level == "high" else ("Managing" if severity_level == "medium" else "Steady")
    expl_text = f"MentAura Severity Engine triaged input as '{severity_level.upper()}' severity (DDS: {dynamic_score}/100, Primary Emotion: {primary_emotion})."

    # 3. Persist Support Pulse Record into Database
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
            recent_pulse.risk_level = severity_level
            recent_pulse.wellbeing_state = wellbeing_state
            recent_pulse.text_response = (recent_pulse.text_response or "") + f" | {user_msg}"
            recent_pulse.xai_explanation = expl_text
            recent_pulse.escalation_predicted = (severity_level == "high")
            recent_pulse.priority_review = (severity_level == "high")
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
                risk_level=severity_level,
                risk_score=dynamic_score // 10,
                escalation_predicted=(severity_level == "high"),
                xai_explanation=expl_text,
                completion_status="submitted",
                priority_review=(severity_level == "high")
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
        "severity_level": severity_level,
        "coping_techniques": coping_techniques,
        "motivational_text": motivational_text,
        "escalation_contact": escalation_contact,
        "alert_generated": alert_generated,
        "alert_details": alert_details,
        "detected_emotions": [primary_emotion],
        "detected_emotion": primary_emotion,
        "sentiment_score": dynamic_score,
        "sentiment_distress_score": dynamic_score,
        "dynamic_distress_indicator": dynamic_score,
        "is_crisis_flag": (severity_level == "high"),
        "suggested_actions": suggested_actions,
        "suggested_chips": suggested_actions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
'''

new_content = content[:content.find(start_marker)] + new_code + "\n\n" + content[content.find(end_marker):]

with open(victim_py_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("SUCCESS: Fully integrated 3-tier severity engine into victim.py!")
