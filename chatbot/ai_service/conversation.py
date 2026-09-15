"""
Conversation Manager — decides reply intent + builds context-aware replies.
Supports multi-domain intent detection, multi-turn dialogue memory,
and native multilingual responses across EN, HI, TA, TE, KN, MR, BN.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional, List, Dict, Any


class Intent(str, Enum):
    OPENING = "opening"                      # first turn of a conversation
    FOLLOW_UP = "follow_up"                  # continuing from prior context
    EMPATHIZE = "empathize"                  # victim shared something painful
    PROBE_SAFETY = "probe_safety"            # check if they are physically safe
    NOTIFY_COUNSELLOR = "notify_counsellor"  # crisis: counsellor is coming
    STAY_WITH = "stay_with"                  # crisis: keep victim engaged until help


@dataclass
class ConversationState:
    intent: Intent
    last_topic: Optional[str] = None
    turn_count: int = 0
    risk_history: list = None


# Topic keywords for simple topic extraction
TOPIC_KEYWORDS = [
    "court", "hearing", "police", "family", "money", "sleep", "health",
    "children", "job", "threats", "threat", "case", "trial", "listening",
    "knife", "gun", "accused", "neighbour", "neighbor", "shouting", "yelling",
    "lawyer", "advocate", "judge", "sad", "sadness", "cry", "lonely", "alone",
    "anxiety", "panic", "nightmare", "nightmares", "relief", "compensation",
    "tame", "safe", "breathing", "protection", "intimidation"
]

# Phrases that indicate safety probe is needed
SAFETY_PHRASES = [
    "not safe", "unsafe", "in danger", "danger", "nowhere to go",
    "being followed", "following me", "at my door", "trapped", "hiding",
    "safe place", "break in", "broken in", "threatened", "knife", "gun",
    "kill me", "hurt me", "attack",
]

# Emotional / painful content words for empathy
EMPATHIZE_WORDS = [
    "hurt", "scared", "alone", "can't take", "cant take", "afraid",
    "tired", "pain", "exhausting", "exhausted", "can't sleep", "cant sleep",
    "sleepless", "sad", "crying", "cry", "hopeless", "lonely", "broken",
    "nobody visited", "no one visited", "डर", "दर्द", "अकेला", "रो",
]

# Core templates specified for each intent (fallback)
REPLY_TEMPLATES = {
    Intent.OPENING: {
        "low": "Hello. Thank you for reaching out. How are you feeling today?",
        "medium": "Thank you for reaching out. I'm here to listen. What's been on your mind lately?",
        "high": "Thank you for reaching out. I'm here with you. Can you tell me what's happening right now?",
        "critical": "I'm here with you. What you're going through matters. Can you tell me where you are right now?",
    },
    Intent.FOLLOW_UP: {
        "low": "I'm glad you're checking in. How have things been with the {topic}?",
        "medium": "Thanks for continuing. You mentioned the {topic} — how are you coping with that?",
        "high": "I hear you. Let's stay with this — how are things with the {topic} right now?",
        "critical": "I'm still here with you. What's happening right now?",
    },
    Intent.EMPATHIZE: {
        "low": "That sounds difficult. Thank you for sharing it with me. Would you like to tell me more?",
        "medium": "That sounds really hard. I hear you. Can you tell me how long you've been feeling this way?",
        "high": "I hear you, and what you're feeling is real. You're not alone. Can you tell me a bit more?",
        "critical": "I hear you. What you're feeling is serious and I'm staying with you. Help is on the way.",
    },
    Intent.PROBE_SAFETY: {
        "any": "I want to make sure you're okay right now. Are you somewhere safe?",
    },
    Intent.NOTIFY_COUNSELLOR: {
        "high": "Thank you for telling me this. A counsellor has been notified and will reach out to you very soon. I'm here with you until then.",
        "critical": "I've alerted a counsellor right now. They will reach out to you immediately. I'm staying with you. Are you somewhere safe?",
    },
    Intent.STAY_WITH: {
        "high": "I'm here. Take your time. Is there anything you want to tell me while we wait for the counsellor?",
        "critical": "I'm not going anywhere. You're not alone. Can you tell me if someone is with you right now?",
    },
}

# Generic replies for FOLLOW_UP when topic is None
FOLLOW_UP_GENERIC = {
    "low": "I'm glad you're checking in. How have things been going?",
    "medium": "Thanks for continuing. I'm here to listen — how are you coping right now?",
    "high": "I hear you. Let's stay with this — how are things right now?",
    "critical": "I'm still here with you. What's happening right now?",
}

# Alternative replies to prevent consecutive identical responses
EMPATHIZE_ALT = {
    "low": "I hear you. Thank you for opening up to me. We're here whenever you want to share more.",
    "medium": "I hear how difficult and exhausting this has been for you. You don't have to carry this alone — I'm right here listening.",
    "high": "Thank you for trusting me with this. What you're experiencing is heavy, and I'm right here with you.",
    "critical": "I hear how much pain you're in. You're not alone right now — help is on the way, and I'm staying right here with you.",
}

FOLLOW_UP_GENERIC_ALT = {
    "low": "Thanks for checking in today. We're right here whenever you need us.",
    "medium": "I appreciate you staying in touch. How can I best support you today?",
    "high": "I'm listening closely. Please take your time and tell me what you need.",
    "critical": "I'm still here with you. What's happening right now?",
}

_conversation_risk_history: dict[tuple, list[str]] = {}


def extract_topic(current_message: str) -> Optional[str]:
    """Extract first matched topic keyword from text."""
    if not current_message:
        return None
    text = current_message.lower()
    first_topic = None
    first_idx = float("inf")
    for kw in TOPIC_KEYWORDS:
        idx = text.find(kw)
        if idx != -1 and idx < first_idx:
            first_idx = idx
            first_topic = kw
    return first_topic


def classify_intent(
    current_message: str,
    history: list,
    risk_level,
    escalation_flag: bool = False,
    risk_history: Optional[list] = None,
) -> Intent:
    """Classify reply intent based on current message, history, and risk level."""
    turn_count = len(history) if history is not None else 0

    if hasattr(risk_level, "value"):
        risk_level = risk_level.value
    risk = str(risk_level).lower().split(".")[-1]

    history_tuple = tuple(history) if history else ()
    if risk_history is not None:
        prior_risks = [
            (r.value if hasattr(r, "value") else str(r)).lower().split(".")[-1]
            for r in risk_history
        ]
    else:
        prior_risks = _conversation_risk_history.get(history_tuple, [])

    next_key = history_tuple + (current_message,)
    _conversation_risk_history[next_key] = prior_risks + [risk]

    # Crisis check FIRST
    if risk in ("high", "critical"):
        had_prior_crisis = any(r in ("high", "critical") for r in prior_risks)
        if turn_count == 0 or not had_prior_crisis:
            return Intent.NOTIFY_COUNSELLOR
        return Intent.STAY_WITH

    if turn_count == 0:
        history_key = (current_message,)
        _conversation_risk_history[history_key] = [risk]
        return Intent.OPENING

    text = (current_message or "").lower()
    if any(phrase in text for phrase in SAFETY_PHRASES):
        return Intent.PROBE_SAFETY

    if any(word in text for word in EMPATHIZE_WORDS):
        return Intent.EMPATHIZE

    return Intent.FOLLOW_UP


def build_reply(
    intent: Intent,
    current_message: str = "",
    last_topic: Optional[str] = None,
    risk_level="medium",
    last_reply: Optional[str] = None,
) -> str:
    """Return a reply string matched to the intent, current message, topic, and risk level."""
    if hasattr(risk_level, "value"):
        risk_level = risk_level.value
    risk = str(risk_level).lower().split(".")[-1]
    if risk not in ("low", "medium", "high", "critical"):
        risk = "medium"

    msg_clean = (current_message or "").strip().lower()
    if msg_clean == "help":
        return "I'm here to help. You can talk to me about what you're going through, and counselling support is available whenever you need it."

    if intent == Intent.PROBE_SAFETY:
        return REPLY_TEMPLATES[Intent.PROBE_SAFETY]["any"]

    if intent == Intent.NOTIFY_COUNSELLOR:
        if risk == "critical":
            return REPLY_TEMPLATES[Intent.NOTIFY_COUNSELLOR]["critical"]
        return REPLY_TEMPLATES[Intent.NOTIFY_COUNSELLOR]["high"]

    if intent == Intent.STAY_WITH:
        if risk == "critical":
            return REPLY_TEMPLATES[Intent.STAY_WITH]["critical"]
        return REPLY_TEMPLATES[Intent.STAY_WITH]["high"]

    if intent == Intent.OPENING:
        return REPLY_TEMPLATES[Intent.OPENING][risk]

    if intent == Intent.FOLLOW_UP:
        topic = last_topic or extract_topic(current_message)
        if topic:
            return REPLY_TEMPLATES[Intent.FOLLOW_UP][risk].format(topic=topic)
        candidate = FOLLOW_UP_GENERIC[risk]
        if last_reply and candidate == last_reply:
            return FOLLOW_UP_GENERIC_ALT[risk]
        return candidate

    if intent == Intent.EMPATHIZE:
        candidate = REPLY_TEMPLATES[Intent.EMPATHIZE][risk]
        if last_reply and candidate == last_reply:
            return EMPATHIZE_ALT[risk]
        return candidate

    return REPLY_TEMPLATES[Intent.OPENING][risk]


def should_shift_to_crisis(history, current_risk) -> bool:
    """Return True if current risk is high/critical or rising in last 2 turns."""
    if hasattr(current_risk, "value"):
        current_risk = current_risk.value
    cur = str(current_risk).lower().split(".")[-1]
    if cur in ("high", "critical"):
        return True

    if not history:
        return False

    recent = history[-2:]
    for item in recent:
        if hasattr(item, "risk_level"):
            r = item.risk_level
            if hasattr(r, "value"):
                r = r.value
            if str(r).lower().split(".")[-1] in ("high", "critical"):
                return True
        elif isinstance(item, str):
            r = item.lower().split(".")[-1]
            if r in ("high", "critical"):
                return True
            if any(w in r for w in ["die", "suicid", "kill", "threat", "end it all"]):
                return True
        elif isinstance(item, dict) and "risk_level" in item:
            r = str(item["risk_level"]).lower().split(".")[-1]
            if r in ("high", "critical"):
                return True
    return False


# ============================================================================
# MULTILINGUAL DOMAIN KNOWLEDGE & CONVERSATIONAL ENGINE
# ============================================================================

TECHNIQUES_DATA = {
    "EN": [
        {"title": "4-7-8 Breathing Pacer", "desc": "Inhale 4s, Hold 7s, Exhale 8s to calm your nervous system.", "action": "Start Breathing Pacer"},
        {"title": "5-4-3-2-1 Sensory Grounding", "desc": "Identify 5 things you see, 4 touch, 3 hear, 2 smell, 1 taste.", "action": "Start 5-4-3-2-1 Grounding"},
        {"title": "Positive Daily Affirmation", "desc": "'I am safe in this moment. Step by step, I am rebuilding my peace.'", "action": "Save Daily Affirmation"}
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

ESCALATION_CONTACTS_DATA = {
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

ALERT_DETAILS_DATA = {
    "EN": {
        "badge": "🚨 HIGH SEVERITY ALERT GENERATED",
        "authority": "District Protection Officer & DLSA Notified",
        "detail": "An urgent alert has been dispatched to your District Protection Unit. Authorities have been requested to reach out immediately under Section 15A. If in immediate danger, dial 112 right now."
    },
    "HI": {
        "badge": "🚨 उच्च गंभीरता चेतावनी जारी",
        "authority": "जिला संरक्षण अधिकारी एवं DLSA को सूचित किया गया",
        "detail": "धारा 15A के तहत आपकी सुरक्षा हेतु जिला संरक्षण इकाई को त्वरित संदेश भेजा गया है। यदि आप तत्काल खतरे में हैं, तो अभी 112 डायल करें।"
    },
    "TA": {
        "badge": "🚨 அவசர பாதுகாப்பு எச்சரிக்கை",
        "authority": "மாவட்ட பாதுகாப்பு அதிகாரி & DLSA எச்சரிக்கப்பட்டனர்",
        "detail": "பிரிவு 15A இன் கீழ் உடனடி பாதுகாப்பு கோரப்பட்டுள்ளது. நீங்கள் ஆபத்தில் இருந்தால் உடனடியாக 112 ஐ அழைக்கவும்."
    },
    "TE": {
        "badge": "🚨 అత్యవసర రక్షణ హెచ్చరిక",
        "authority": "జిల్లా రక్షణ అధికారి & DLSA కు సమాచారం అందించబడింది",
        "detail": "సెక్షన్ 15A కింద రక్షణ చర్యలు ప్రారంభించబడ్డాయి. ప్రమాదం ఉంటే వెంటనే 112 కు కాల్ చేయండి."
    },
    "KN": {
        "badge": "🚨 ತುರ್ತು ಭದ್ರತಾ ಎಚ್ಚರಿಕೆ",
        "authority": "ಜಿಲ್ಲಾ ರಕ್ಷಣಾ ಅಧಿಕಾರಿ & DLSA ಗೆ ಮಾಹಿತಿ ರವಾನಿಸಲಾಗಿದೆ",
        "detail": "ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ತುರ್ತು ರಕ್ಷಣಾ ಕ್ರಮ ಕೈಗೊಳ್ಳಲಾಗಿದೆ. ಅಪಾಯವಿದ್ದರೆ ತಕ್ಷಣ 112 ಗೆ ಕರೆ ಮಾಡಿ."
    },
    "MR": {
        "badge": "🚨 तातडीचा सुरक्षा इशारा",
        "authority": "जिल्हा संरक्षण अधिकारी व DLSA यांना सूचित केले",
        "detail": "कलम 15A अंतर्गत तात्काळ संरक्षण संदेश पाठवला आहे. तात्काळ धोक्यात असल्यास 112 डायल करा."
    },
    "BN": {
        "badge": "🚨 জরুরি নিরাপত্তা সতর্কতা",
        "authority": "জেলা সুরক্ষা আধিকারিক ও DLSA অবহিত",
        "detail": "ধারা ১৫A এর অধীনে অবিলম্বে সুরক্ষা সতর্কতা জারি করা হয়েছে। কোনো বিপদ থাকলে এখনই ১১২ ডায়াল করুন।"
    }
}


def detect_message_domain(message: str) -> str:
    """Identify the core subject area of the user's message."""
    t = message.lower()

    # 1. Threats / Danger / Section 15A
    is_panic_or_anxiety_attack = any(p in t for p in ["panic attack", "anxiety attack", "heart attack"])
    has_threat_keyword = any(w in t for w in ["threat", "threatened", "intimidation", "knife", "gun", "accused", "kill", "stalk", "following me", "outside my", "unsafe", "in danger", "danger", "धमकी", "मार", "மிரட்டல்", "கொலை", "బెదిరింపు", "చంపే", "ಬೆದರಿಕೆ", "भीती", "হুমকি", "15a"]) or ("attack" in t and not is_panic_or_anxiety_attack)
    if has_threat_keyword:
        return "safety_threats"

    # 2. Suicide / Self-harm
    if any(w in t for w in ["suicide", "kill myself", "end my life", "want to die", "hurt myself", "आत्महत्या", "मरना चाहता", "தற்கொலை", "ఆత్మహత్య", "ಆತ್ಮಹತ್ಯೆ", "মরতে চাই"]):
        return "suicide_crisis"

    # 2.5 Legal Process Inquiry
    if any(w in t for w in ["legal process", "steps are involved", "how the case works", "what are the steps", "stages of case", "legal procedure", "procedure", "what happens next in court", "fir to trial"]):
        return "legal_process_inquiry"

    # 3. Court / Legal Hearings / Depositions
    if any(w in t for w in ["court", "hearing", "judge", "trial", "chargesheet", "lawyer", "advocate", "summons", "deposition", "witness box", "legal process", "testimony", "bail", "अदालत", "कोर्ट", "तारीख", "गवाही", "நீதிமன்றம்", "விசாரணை", "కోర్టు", "విచారణ", "ನ್ಯಾಯಾಲಯ", "न्यायालय", "সুनावणी", "আদালত", "শুনানি"]):
        return "court_legal"

    # 4. Compensation / Financial Relief / TAME
    if any(w in t for w in ["compensation", "relief", "money", "allowance", "tame", "travel", "disbursement", "annexure", "financial", "fund", "मुआवजा", "राहत", "இழப்பீடு", "பயணப்படி", "పరిహారం", "భత్యం", "ಪರಿಹಾರ", "भरपाई", "ক্ষতিপূরণ"]):
        return "compensation_welfare"

    # 5. Interpersonal / Neighbour Harassment / Boycott
    if any(w in t for w in ["neighbour", "neighbor", "shouting", "yelling", "abusing", "abused", "harass", "harassment", "fight", "fighting", "dispute", "boycott", "ostracism", "slur", "humiliate", "colony", "हल्ला", "गाली", "पड़ोसी", "சண்டை", "தகராறு", "பக்கத்து", "గొడవ", "ఇరుగుపొరుగు", "ಜಗಳ", "ನೆರೆಹೊರೆ", "भांडण", "शेजारी", "ঝগড়া", "প্রতিবেশী"]):
        return "neighbor_harassment"

    # 6. Sleep / Nightmares / Somatic distress
    if any(w in t for w in ["sleep", "insomnia", "nightmare", "nightmares", "sleepless", "wake up", "restless", "headache", "exhausted", "tired", "head hurts", "body pain", "नींद", "डरावने सपने", "தூக்கம்", "நிద్ర", "పీడకలలు", "ನಿದ್ರೆ", "झोप", "ঘুম"]):
        return "sleep_somatic"

    # 7. Sadness, Grief, Loneliness & Isolation (e.g. "no one visited me")
    if any(w in t for w in ["depressed", "depression", "feeling down", "unhappy", "no one visited", "nobody visited", "visited", "alone", "lonely", "nobody cares", "crying", "cry", "broken", "empty", "hopeless", "sad", "sadness", "grief", "pain", "heavy heart", "उदासीन", "अकेला", "रो रहा", "डिप्रेशन", "उदासी", "கண்ணீர்", "தனிமை", "బాధ", "ఒంటరి", "ಅಳು", "ಏಕಾಂಗಿ", "रडणे", "एकटेपणा", "কান্না", "নিঃসঙ্গ"]):
        return "sadness_isolation"

    # 8. Anxiety, Panic & Dread
    if any(w in t for w in ["anxiety", "anxious", "panic", "trembling", "shaking", "nervous", "tension", "stress", "stressed", "overwhelmed", "dread", "घबराहट", "तनाव", "பதற்றம்", "ஆందోళన", "ಒತ್ತಡ", "तणाव", "উদ্বেগ"]):
        return "anxiety_panic"

    # 9. Grounding & Calming exercises
    if any(w in t for w in ["grounding", "breathe", "breathing", "calm", "soothe", "4-7-8", "exercise", "meditation", "प्राणायाम", "மூச்சு", "శ్వాస", "ಉಸಿರಾಟ", "श्वास", "শ্বাস"]):
        return "grounding_calm"

    # 10. Positive check-in / Resilience
    if any(w in t for w in ["fine", "okay", "ok", "good", "safe today", "better", "thank", "thanks", "feeling steady", "peaceful", "happy", "great", "अच्छा", "நன்றி", "ధన్యవాదాలు"]):
        return "positive_resilience"

    # 11. Assistant Identity & Capabilities
    if any(w in t for w in ["who are you", "what can you do", "what do you do", "help me", "how does this work", "mentaura", "features", "options"]):
        return "assistant_identity"

    # 12. Greeting & Introductions
    if any(w in t for w in ["hi", "hello", "hey", "nice to meet", "good to meet", "pleased to meet", "namaste", "vanakkam", "namaskara", "good morning", "good afternoon", "good evening", "how are you"]):
        return "greeting"

    return "general_sharing"


def generate_contextual_turn(
    message: str,
    language: str = "EN",
    turn_number: int = 1,
    prev_messages: Optional[List[str]] = None,
    distress=None,
    escalation=None,
    text_analysis=None,
    last_reply: Optional[str] = None
) -> Dict[str, Any]:
    """
    Formulate a dynamic, intelligent, context-aware reply reflecting the
    user's actual statement across all domains and 7 languages.
    """
    try:
        from ai_service.dynamic_engine import generate_dynamic_turn
    except ImportError:
        try:
            from chatbot.ai_service.dynamic_engine import generate_dynamic_turn
        except ImportError:
            generate_dynamic_turn = None

    if generate_dynamic_turn:
        history_dicts = []
        if prev_messages:
            for pm in prev_messages:
                history_dicts.append({"role": "user", "content": pm} if isinstance(pm, str) else pm)
        return generate_dynamic_turn(
            message=message,
            language=language,
            turn_number=turn_number,
            history=history_dicts,
            last_reply=last_reply
        )

    lang = (language or "EN").upper()
    if lang not in ["EN", "HI", "TA", "TE", "KN", "MR", "BN"]:
        lang = "EN"

    domain = detect_message_domain(message)

    # Determine severity
    if domain in ("suicide_crisis", "safety_threats"):
        severity = "high"
        default_score = 88 if domain == "suicide_crisis" else 78
        primary_emotion = "fear"
    elif domain in ("court_legal", "legal_process_inquiry", "neighbor_harassment", "sleep_somatic", "sadness_isolation", "anxiety_panic"):
        severity = "medium"
        default_score = 52
        primary_emotion = "trust" if domain == "legal_process_inquiry" else ("anxiety" if domain in ("court_legal", "anxiety_panic") else "sadness")
    else:
        severity = "low"
        default_score = 18
        primary_emotion = "steady"

    # Synchronize score with ML distress calculator if available
    if distress and hasattr(distress, "distress_score"):
        final_score = int(distress.distress_score)
        if hasattr(distress, "risk_level"):
            r_str = str(distress.risk_level.value if hasattr(distress.risk_level, "value") else distress.risk_level).lower()
            if ("high" in r_str or "critical" in r_str) and domain in ("suicide_crisis", "safety_threats"):
                severity = "high"
            elif "medium" in r_str or domain in ("court_legal", "neighbor_harassment", "sleep_somatic", "sadness_isolation", "anxiety_panic"):
                severity = "medium"
            else:
                severity = "low"
    else:
        final_score = default_score

    # Domain response templates by language
    REPLIES_DB = {
        "safety_threats": {
            "EN": "Your safety is our absolute priority. Any threat, weapon, or intimidation from the accused or their associates is a serious violation under Section 15A of the SC/ST (PoA) Act. You are entitled to immediate police protection and escort. Are you in a physically secure place right now?",
            "HI": "आपकी सुरक्षा हमारी सर्वोच्च प्राथमिकता है। आरोपी या उसके साथियों द्वारा किसी भी प्रकार की धमकी, हथियार दिखाना या डराना अनुसूचित जाति/जनजाति अधिनियम की धारा 15A के तहत गंभीर अपराध है। आपको तत्काल पुलिस सुरक्षा और एस्कॉर्ट का वैधानिक अधिकार है। क्या आप इस समय किसी सुरक्षित स्थान पर हैं?",
            "TA": "உங்கள் பாதுகாப்பு எங்களின் முதல் முன்னுரிமை. பிரிவு 15A இன் கீழ் மிரட்டல்கள் மற்றும் அச்சுறுத்தல்களுக்கு எதிராக உங்களுக்கு உடனடி போலீஸ் பாதுகாப்பு பெற முழு உரிமை உண்டு. நீங்கள் இப்போது பாதுகாப்பான இடத்தில் இருக்கிறீர்களா?",
            "TE": "మీ భద్రత మా అత్యున్నత ప్రాధాన్యత. SC/ST చట్టం సెక్షన్ 15A ప్రకారం ఎవరైనా బెదిరిస్తే మీకు తక్షణ పోలీసు రక్షణ పొందే హక్కు ఉంది. మీరు ఇప్పుడు సురక్షితమైన ప్రదేశంలో ఉన్నారా?",
            "KN": "ನಿಮ್ಮ ಸುರಕ್ಷತೆ ನಮ್ಮ ಪ್ರಮುಖ ಆದ್ಯತೆ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ಬೆದರಿಕೆಗಳ ವಿರುದ್ಧ ತಕ್ಷಣದ ಪೊಲೀಸ್ ರಕ್ಷಣೆ ಪಡೆಯಲು ನಿಮಗೆ ಸಂಪೂರ್ಣ ಹಕ್ಕಿದೆ. ನೀವು ಈಗ ಸುರಕ್ಷಿತ ಸ್ಥಳದಲ್ಲಿದ್ದೀರಾ?",
            "MR": "आपली सुरक्षा आमची सर्वोच्च प्राथमिकता आहे. अनुसूचित जाती/जमाती कायद्याच्या कलम 15A अंतर्गत धमकी देणे हा गंभीर गुन्हा आहे. आपल्याला तात्काळ पोलीस संरक्षणाचा हक्क आहे. आपण आता सुरक्षित ठिकाणी आहात का?",
            "BN": "আপনার নিরাপত্তা আমাদের সর্বোচ্চ অগ্রাধিকার। ধারা ১৫A এর অধীনে কোনো হুমকি বা ভীতি প্রদর্শনের বিরুদ্ধে আপনার অবিলম্বে পুলিশ সুরক্ষা পাওয়ার আইনি অধিকার রয়েছে। আপনি কি এখন কোনো নিরাপদ স্থানে আছেন?"
        },
        "suicide_crisis": {
            "EN": "I hear you, and I want you to know that your life has immense value. You are carrying an unimaginable burden, but you do not have to face this dark moment alone. I am staying right here with you, and help is available immediately. Please connect with our emergency crisis support right away.",
            "HI": "मैं आपकी पीड़ा को समझ रहा हूँ। आपका जीवन अत्यंत मूल्यवान है। आप बहुत भारी मानसिक कष्ट से गुजर रहे हैं, लेकिन आपको यह दर्द अकेले नहीं सहना है। मैं आपके साथ हूँ और तत्काल सहायता उपलब्ध है। कृपया संकटकालीन हेल्पलाइन 14416 पर तुरंत संपर्क करें।",
            "TA": "உங்கள் வலியை நான் உணர்கிறேன். உங்கள் வாழ்க்கை மிகவும் மதிப்புமிக்கது. நீங்கள் தனியாக இல்லை, நாங்கள் உங்களுடன் இருக்கிறோம். தயவுசெய்து உடனடி உதவி எண் 14416 ஐ அழைக்கவும்.",
            "TE": "నేను మీ బాధను అర్థం చేసుకోగలను. మీ ప్రాణం చాలా విలువైంది. మీరు ఒంటరిగా లేరు, మీకు సహాయం చేయడానికి మేము ఉన్నాము. దయచేసి వెంటనే 14416 కి కాల్ చేయండి.",
            "KN": "ನಿಮ್ಮ ನೋವು ನನಗೆ ಅರ್ಥವಾಗುತ್ತದೆ. ನಿಮ್ಮ ಜೀವ ಅತ್ಯಮೂಲ್ಯವಾದುದು. ನೀವು ಒಬ್ಬರೇ ಇಲ್ಲ, ನಾವು ನಿಮ್ಮೊಂದಿಗೆ ಇದ್ದೇವೆ. ದಯವಿಟ್ಟು ತಕ್ಷಣ 14416 ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ.",
            "MR": "मी आपले दुःख समजू शकतो. आपले जीवन खूप मोलाचे आहे. आपण एकटे नाही आहात, आम्ही आपल्या सोबत आहोत. कृपया तात्काळ 14416 या हेल्पलाइनवर संपर्क साधा.",
            "BN": "আমি আপনার যন্ত্রণা বুঝতে পারছি। আপনার জীবন অত্যন্ত মূল্যবান। আপনি একা নন, আমরা আপনার পাশে আছি। অবিলম্বে 14416 নম্বরে যোগাযোগ করুন।"
        },
        "legal_process_inquiry": {
            "EN": "The legal journey under the SC/ST (PoA) Act follows structured statutory stages: 1) FIR registration and preliminary protection, 2) DSP-level investigation mandated within 60 days, 3) Filing of the chargesheet in the Special Court, 4) Appointment of free legal aid via DLSA, and 5) Trial with Section 15A rights (separate witness room, police escort, daily travel allowance, and in-camera deposition). Which stage is your case currently at?",
            "HI": "अनुसूचित जाति/जनजाति अत्याचार निवारण अधिनियम के तहत कानूनी प्रक्रिया के मुख्य वैधानिक चरण हैं: 1) एफआईआर दर्ज होना और सुरक्षा, 2) डीएसपी स्तर के अधिकारी द्वारा 60 दिनों के भीतर जांच, 3) विशेष अदालत में आरोप पत्र (चार्जशीट) दाखिल होना, 4) DLSA से निःशुल्क वकील मिलना, और 5) धारा 15A के तहत सुरक्षित गवाही, बंद कमरे में सुनवाई व यात्रा भत्ता (TAME)। आपका मामला वर्तमान में किस चरण में है?",
            "TA": "வன்கொடுமை தடுப்பு சட்டத்தின் கீழ் சட்ட நடைமுறைகள்: 1) முதல் தகவல் அறிக்கை (FIR) மற்றும் பாதுகாப்பு, 2) 60 நாட்களுக்குள் டிஎஸ்பி விசாரணை, 3) சிறப்பு நீதிமன்றத்தில் குற்றப்பத்திரிகை, 4) இலவச DLSA வழக்கறிஞர், மற்றும் 5) பிரிவு 15A இன் கீழ் சாட்சி பாதுகாப்புடன் கூடிய விசாரணை. உங்கள் வழக்கு இப்போது எந்த கட்டத்தில் உள்ளது?",
            "TE": "SC/ST చట్టం కింద న్యాయ ప్రక్రియ దశలు: 1) ఎఫ్‌ఐఆర్ నమోదు మరియు రక్షణ, 2) 60 రోజుల్లో డీఎస్పీ విచారణ, 3) ప్రత్యేక కోర్టులో చార్జిషీటు దాఖలు, 4) ఉచిత న్యాయ సహాయం (DLSA), మరియు 5) సెక్షన్ 15A కింద సాక్షి రక్షణతో కోర్టు విచారణ. మీ కేసు ప్రస్తుతం ఏ దశలో ఉంది?",
            "KN": "ದೌರ್ಜನ್ಯ ತಡೆ ಕಾಯ್ದೆಯಡಿ ಕಾನೂನು ಪ್ರಕ್ರಿಯೆಯ ಹಂತಗಳು: 1) ಎಫ್‌ಐಆರ್ ಮತ್ತು ರಕ್ಷಣೆ, 2) 60 ದಿನಗಳಲ್ಲಿ ಡಿಎಸ್‌ಪಿ ತನಿಖೆ, 3) ವಿಶೇಷ ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಚಾರ್ಜ್‌ಶೀಟ್, 4) ಉಚಿತ ಕಾನೂನು ನೆರವು (DLSA), ಮತ್ತು 5) ಸೆಕ್ಷನ್ 15A ಸಾಕ್ಷಿ ರಕ್ಷಣೆಯೊಂದಿಗೆ ವಿಚಾರಣೆ. ನಿಮ್ಮ ಪ್ರಕರಣ ಈಗ ಯಾವ ಹಂತದಲ್ಲಿದೆ?",
            "MR": "अत्याचार प्रतिबंधक कायद्यांतर्गत कायदेशीर प्रक्रिया: 1) एफआयआर आणि सुरक्षा, 2) 60 दिवसांत डीएसपी स्तरावर तपास, 3) विशेष न्यायालयात दोषारोपपत्र (चार्जशीट), 4) विधी सेवा प्राधिकरणाकडून मोफत वकील, आणि 5) कलम 15A अन्वये साक्ष नोंदणी व प्रवास भत्ता. आपले प्रकरण सध्या कोणत्या टप्प्यावर आहे?",
            "BN": "পিওএ আইনের অধীনে আইনি ধাপগুলি হল: ১) এফআইআর ও সুরক্ষা, ২) ৬০ দিনের মধ্যে ডিএসপি তদন্ত, ৩) বিশেষ আদালতে চার্জশিট, ৪) ডিএলএসএ বিনামূল্যে আইনজীবী, এবং ৫) ধারা ১৫A এর অধীনে সাক্ষ্য সুরক্ষা। আপনার মামলাটি বর্তমানে কোন পর্যায়ে রয়েছে?"
        },
        "court_legal": {
            "EN": "Court hearings, legal depositions, and trial procedures naturally create intense anxiety and nervousness. Under Section 15A of the PoA Act, you have explicit rights: protection during transit, in-camera examination, DLSA legal counsel, and daily travel allowance (TAME). What part of the court date is worrying you the most?",
            "HI": "न्यायालय की सुनवाई, गवाही और कानूनी प्रक्रियाएं स्वाभाविक रूप से गहरा तनाव और घबराहट पैदा करती हैं। अधिनियम की धारा 15A के तहत आपको अदालत आते-जाते समय सुरक्षा, बंद कमरे (इन-कैमरा) में गवाही और DLSA से निःशुल्क कानूनी सहायता का पूरा अधिकार है। अदालत को लेकर आपके मन में सबसे बड़ी चिंता क्या है?",
            "TA": "நீதிமன்ற விசாரணை மற்றும் வாக்குமூலம் அளிப்பது இயல்பாகவே அதிக மன அழுத்தத்தை தரும். பிரிவு 15A இன் கீழ் உங்களுக்கு நீதிமன்றத்திற்கு பாதுகாப்பான பயணம் மற்றும் இலவச சட்ட உதவி பெற உரிமை உள்ளது. உங்கள் வழக்கில் உங்களுக்கு என்ன தயக்கம் உள்ளது?",
            "TE": "కోర్టు విచారణలు మరియు సాక్ష్యం చెప్పే ప్రక్రియ తీవ్ర ఆందోళన కలిగిస్తుంది. సెక్షన్ 15A కింద మీకు ఉచిత న్యాయ సహాయం మరియు భద్రత పొందే హక్కు ఉంది. కోర్టు విషయంలో మీకు ఏది ఎక్కువ భయంగా ఉంది?",
            "KN": "ನ್ಯಾಯಾಲಯದ ವಿಚಾರಣೆ ಮತ್ತು ಸಾಕ್ಷಿ ಹೇಳುವುದು ಸಹಜವಾಗಿಯೇ ಆತಂಕ ಉಂಟುಮಾಡುತ್ತದೆ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ನಿಮಗೆ ಉಚಿತ ಕಾನೂನು ನೆರವು ಮತ್ತು ರಕ್ಷಣೆಯ ಹಕ್ಕಿದೆ. ನ್ಯಾಯಾಲಯದ ಬಗ್ಗೆ ನಿಮಗೆ ಯಾವ ವಿಷಯ ಆತಂಕ ತಂದಿದೆ?",
            "MR": "न्यायालयातील सुनावणी आणि साक्ष देण्याची प्रक्रिया तणाव निर्माण करणारी असते. कलम 15A अन्वये आपल्याला न्यायालयापर्यंत सुरक्षा आणि विधी सेवा प्राधिकरणाकडून मोफत वकील मिळण्याचा अधिकार आहे. आपल्याला नक्की कशाची भीती वाटते?",
            "BN": "আদালতের শুনানি এবং সাক্ষ্য দেওয়ার প্রক্রিয়া স্বাভাবিকভাবেই উদ্বেগ সৃষ্টি করে। ধারা ১৫A এর অধীনে আপনার নিরাপত্তা এবং বিনামূল্যে আইনি সহায়তা পাওয়ার অধিকার রয়েছে। আদালতের ব্যাপারে আপনার প্রধান চিন্তা কী?"
        },
        "compensation_welfare": {
            "EN": "Under Rule 12(4) of the SC/ST (PoA) Rules, you are legally entitled to statutory financial relief and Travel & Maintenance Allowance (TAME) for every court attendance. Relief is disbursed in stages: 25% at FIR, 50% on chargesheet filing, and 25% on case conclusion. Have your relief papers been submitted to the District Welfare Officer?",
            "HI": "अधिनियम के नियम 12(4) के तहत आप वित्तीय राहत और प्रत्येक अदालती तारीख हेतु यात्रा एवं भरण-पोषण भत्ता (TAME) पाने के पूर्ण हकदार हैं। यह राहत तीन चरणों में मिलती है: 25% FIR पर, 50% आरोप पत्र (चार्जशीट) दाखिल होने पर, और 25% फैसला होने पर। क्या आपके कागजात जिला समाज कल्याण अधिकारी के पास जमा हैं?",
            "TA": "வன்கொடுமை தடுப்பு விதிகளின்படி உங்களுக்கு அரசு இழப்பீடு மற்றும் ஒவ்வொரு நீதிமன்ற அமர்வுக்கும் பயணப்படி (TAME) பெற முழு உரிமை உண்டு. உங்கள் நிவாரண ஆவணங்கள் சமர்ப்பிக்கப்பட்டுவிட்டதா?",
            "TE": "SC/ST నిబంధనల ప్రకారం మీకు ప్రభుత్వ పరిహారం మరియు ప్రతి కోర్టు విచారణకు ప్రయాణ భత్యం (TAME) పొందే చట్టబద్ధమైన హక్కు ఉంది. మీ పరిహార పత్రాలు సమర్పించబడ్డాయా?",
            "KN": "ದೌರ್ಜನ್ಯ ತಡೆ ನಿಯಮಗಳ ಪ್ರಕಾರ ಪರಿಹಾರ ಮತ್ತು ಪ್ರತಿ ವಿಚಾರಣೆಗೆ ಪ್ರಯಾಣ ಭತ್ಯೆ (TAME) ಪಡೆಯಲು ನಿಮಗೆ ಹಕ್ಕಿದೆ. ನಿಮ್ಮ ಪರಿಹಾರದ ದಾಖಲೆಗಳನ್ನು ಸಲ್ಲಿಸಲಾಗಿದೆಯೇ?",
            "MR": "अत्याचार प्रतिबंधक नियमांनुसार आपल्याला शासकीय भरपाई आणि प्रत्येक सुनावणीसाठी प्रवास भत्ता (TAME) मिळण्याचा कायदेशीर हक्क आहे. आपले कागदपत्रे समाज कल्याण कार्यालयात जमा झाली आहेत का?",
            "BN": "পিওএ বিধিমালার অধীনে আপনি আর্থিক ক্ষতিপূরণ এবং প্রতিটি শুনানির জন্য ভ্রমণ ভাতা (TAME) পাওয়ার অধিকারী। আপনার ক্ষতিপূরণের নথি কি জমা দেওয়া হয়েছে?"
        },
        "neighbor_harassment": {
            "EN": "Facing hostility, shouting, or harassment from neighbours is deeply stressful and painful. Please remember: social boycott, verbal humiliation, or intimidation against protected persons is strictly prohibited under the law. You do not have to accept this hostility. Have you been able to safely record the dates and times of these incidents?",
            "HI": "पड़ोसियों द्वारा चिल्लाना, दुर्व्यवहार या सामाजिक बहिष्कार अत्यंत तनावपूर्ण और पीड़ादायक होता है। कानून के तहत किसी भी पीड़ित को अपमानित करना या सामाजिक रूप से अलग-थलग करना दंडनीय अपराध है। आपको यह सब अकेले नहीं सहना है। क्या आपने इन घटनाओं की तारीख और समय सुरक्षित रूप से नोट किया है?",
            "TA": "அக்கம்பக்கத்தினரால் ஏற்படும் சண்டை, கூச்சல்கள் அல்லது சமூக புறக்கணிப்பு மிகுந்த மன உளைச்சலை ஏற்படுத்தும். சட்டப்படி இது தண்டனைக்குரிய குற்றம். இந்த சம்பவங்களை நீங்கள் தேதி மற்றும் நேரத்துடன் குறித்து வைத்துள்ளீர்களா?",
            "TE": "ఇరుగుపొరుగు వారి నుండి వేధింపులు లేదా గొడవలు తీవ్ర మానసిక క్షోభను కలిగిస్తాయి. చట్ట ప్రకారం ఇలాంటి చర్యలు నేరం. ఈ ఘటనల సమయం మరియు తేదీలను మీరు రాసి పెట్టుకున్నారా?",
            "KN": "ನೆರೆಹೊರೆಯವರಿಂದ ನಿಂದನೆ ಅಥವಾ ಗಲಾಟೆ ತೀವ್ರ ಮಾನಸಿಕ ನೋವು ಉಂಟುಮಾಡುತ್ತದೆ. ಕಾನೂನಿನ ಪ್ರಕಾರ ಇದು ಶಿಕ್ಷಾರ್ಹ ಅಪರಾಧ. ಈ ಘಟನೆಗಳ ದಿನಾಂಕ ಮತ್ತು ಸಮಯವನ್ನು ನೀವು ಬರೆದಿಟ್ಟುಕೊಂಡಿದ್ದೀರಾ?",
            "MR": "शेजाऱ्यांकडून होणारा त्रास, शिवीगाळ किंवा अपमान खूप मानसिक त्रास देणारा असतो. कायद्यानुसार असा त्रास देणे गुन्हा आहे. आपण या घटनांची तारीख व वेळ नोंदवून ठेवली आहे का?",
            "BN": "প্রতিবেশীদের হুমকি বা দুর্ব্যবহার অত্যন্ত কষ্টদায়ক। আইনের চোখে এটি শাস্তিযোগ্য অপরাধ। আপনি কি এই ঘটনার তারিখ ও সময় লিপিবদ্ধ করেছেন?"
        },
        "sleep_somatic": {
            "EN": "Severe sleep disturbances, nightmares, and physical exhaustion often happen when trauma keeps your nervous system in constant high alert. Your body is physically carrying this emotional strain. In addition to gentle progressive relaxation techniques, our clinical counsellor can guide you through restorative trauma recovery. Would you like a gentle night relaxation guide?",
            "HI": "नींद न आना, डरावने सपने और लगातार सिरदर्द होना इस बात का संकेत है कि आपका शरीर और मन भारी तनाव में हैं। आघात के बाद दिमाग लगातार सतर्क मुद्रा में रहता है। गहरी विश्राम तकनीकों के साथ-साथ हमारे मनोवैज्ञानिक परामर्शदाता आपको शांति पाने में मदद कर सकते हैं। क्या आप एक शांत विश्राम तकनीक आजमाना चाहेंगे?",
            "TA": "தூக்கமின்மை மற்றும் கெட்ட கனவுகள் உங்கள் உடல் மற்றும் மனதின் அதிகப்படியான அழுத்தத்தை காட்டுகின்றன. எங்களின் மனநல ஆலோசகர் உங்களுக்கு தூக்கத்தை சீராக்க வழிகாட்ட முடியும். எளிய தளர்வு பயிற்சியை முயற்சிக்கலாமா?",
            "TE": "నిద్రలేమి మరియు పీడకలలు మీ మనస్సు తీవ్ర ఆందోళనలో ఉందనడానికి సంకేతం. మా కౌన్సెలర్ మీకు ఉపశమనం పొందడానికి మార్గదర్శనం చేయగలరు. సులభమైన రిలాక్సేషన్ పద్ధతిని ప్రయత్నిస్తారా?",
            "KN": "ನಿದ್ರಾಹೀನತೆ ಮತ್ತು ದುಃಸ್ವಪ್ನಗಳು ನಿಮ್ಮ ಅತಿಯಾದ ಮಾನಸಿಕ ಒತ್ತಡವನ್ನು ತೋರಿಸುತ್ತವೆ. ನಮ್ಮ ತಜ್ಞ ಸಮಾಲೋಚಕರು ನಿಮಗೆ ವಿಶ್ರಾಂತಿ ಪಡೆಯಲು ನೆರವಾಗಬಹುದು. ಸರಳ ವಿಶ್ರಾಂತಿ ತಂತ್ರವನ್ನು ಪ್ರಯತ್ನಿಸಲು ಬಯಸುವಿರಾ?",
            "MR": "झोप न लागणे आणि वाईट स्वप्ने पडणे हे तीव्र मानसिक ताणाचे लक्षण आहे. आमचे समुपदेशक आपल्याला मानसिक शांतता मिळवून देण्यासाठी मदत करू शकतात. आपण काही शांतता व्यायाम करू इच्छिता?",
            "BN": "অনিদ্রা এবং দুঃস্বপ্ন অতিরিক্ত মানসিক চাপের লক্ষণ। আমাদের কাউন্সেলর আপনাকে মানসিক শান্তি পুনরুদ্ধারে সহায়তা করতে পারেন। আপনি কি একটি সহজ রিলাক্সেশন ব্যায়াম চেষ্টা করতে চান?"
        },
        "sadness_isolation": {
            "EN": "I hear how heavy and heartbreaking this feels. When no one visits or reaches out, the loneliness and grief can feel overwhelming. Please know that your pain is real, but you are not forgotten. I am right here listening to every word you say, and we genuinely care about your well-being. Would you like to tell me more about what your day felt like?",
            "HI": "मैं समझ सकता हूँ कि यह कितना दर्दनाक और भारी महसूस होता है। जब कोई मिलने नहीं आता और अकेलापन घेर लेता है, तो दिल टूट सा जाता है। कृपया जानिए कि आपकी भावनाएं सच्ची हैं और आप अकेले नहीं हैं। मैं आपकी हर बात ध्यान से सुन रहा हूँ। क्या आप मुझे अपने मन की बात और बताना चाहेंगे?",
            "TA": "யாரும் பார்க்க வராதபோது ஏற்படும் தனிமையும் சோகமும் மிகவும் வேதனையானது என்பதை நான் உணர்கிறேன். நீங்கள் தனியாக இல்லை, நான் உங்களுடன் இருக்கிறேன். உங்கள் மனதை பாரமாக்கும் விஷயங்களை என்னிடம் இன்னும் பகிர்ந்துகொள்ள விருப்பமா?",
            "TE": "ఎవరూ రానప్పుడు కలిగే ఒంటరితనం మరియు బాధ ఎంత భారంగా ఉంటాయో నేను గ్రహించగలను. మీరు ఒంటరిగా లేరు, నేను మీ మాటలు వింటున్నాను. మీ మనస్సులో ఉన్న భావాలను నాతో పంచుకోవాలనుకుంటున్నారా?",
            "KN": "ಯಾರೂ ಭೇಟಿ ನೀಡದಿದ್ದಾಗ ಕಾಡುವ ಏಕಾಂಗಿತನ ಮತ್ತು ದುಃಖ ತುಂಬಾ ಭಾರವಾಗಿರುತ್ತದೆ. ನೀವು ಒಬ್ಬರೇ ಇಲ್ಲ, ನಾನು ನಿಮ್ಮೊಂದಿಗೆ ಇದ್ದೇನೆ. ನಿಮ್ಮ ಮನಸ್ಸಿನ ಮಾತನ್ನು ಇನ್ನಷ್ಟು ಹಂಚಿಕೊಳ್ಳಲು ಬಯಸುವಿರಾ?",
            "MR": "कोणीही न आल्यावर येणारा एकटेपणा आणि दुःख मनाला खूप वेदना देणारे असते. आपण एकटे नाही आहात, मी आपले प्रत्येक शब्द ऐकत आहे. आपण आपल्या भावना अजून सांगू इच्छिता का?",
            "BN": "কেউ দেখা করতে না আসলে একাকীত্ব ও কষ্ট খুব ভারী মনে হয়। আপনি একা নন, আমি আপনার সব কথা শুনছি। আপনার মনের কথা কি আরও বলতে চান?"
        },
        "anxiety_panic": {
            "EN": "Take a slow, gentle breath right now. When panic and racing thoughts take over, your body feels like it is in immediate danger. Let's ground ourselves together: feel both feet firmly planted on the floor, drop your shoulders, and breathe in for 4 seconds, hold for 4, and exhale slowly for 6. You are safe in this present moment.",
            "HI": "अभी एक गहरी और धीमी सांस लीजिए। जब अत्यधिक घबराहट और बेचैनी होती है, तो दिल तेजी से धड़कने लगता है। आइए मिलकर मन को शांत करें: अपने पैरों को जमीन पर महसूस करें, कंधों को ढीला छोड़ें, 4 सेकंड सांस लें और धीरे-धीरे 6 सेकंड में बाहर छोड़ें। आप इस पल में सुरक्षित हैं।",
            "TA": "இப்போது ஒரு ஆழமான மூச்சை உள்ளிழுக்கவும். பயம் ஏற்படும் போது உடல் பதற்றமடைவது இயல்பு. உங்கள் கால்களை தரையில் ஊன்றி, மெதுவாக மூச்சை இழுத்து வெளியிடவும். நீங்கள் இப்போது பாதுகாப்பாக இருக்கிறீர்கள்.",
            "TE": "ఇప్పుడు ఒక దీర్ఘ శ్వాస తీసుకోండి. ఆందోళన పెరిగినప్పుడు శరీరం వణుకుతుంది. ప్రశాంతంగా కూర్చుని, 4 సెకన్లు శ్వాస పీల్చి నెమ్మదిగా వదలండి. మీరు ప్రస్తుతం క్షేమంగా ఉన్నారు.",
            "KN": "ಈಗ ನಿಧಾನವಾಗಿ ದೀರ್ಘ ಉಸಿರು ತೆಗೆದುಕೊಳ್ಳಿ. ಆತಂಕ ಹೆಚ್ಚಾದಾಗ ದೇಹ ನಡುಗುವುದು ಸಹಜ. ನಿರಾಳವಾಗಿ ಕುಳಿತು, ಉಸಿರಾಟದ ಮೇಲೆ ಗಮನ ಕೇಂದ್ರೀಕರಿಸಿ. ನೀವು ಪ್ರಸ್ತುತ ಸುರಕ್ಷಿತವಾಗಿದ್ದೀರಿ.",
            "MR": "आत्ता एक दीर्घ आणि शांत श्वास घ्या. भीती आणि धडधड वाढणे स्वाभाविक आहे. आपले खांदे सैल सोडा आणि हळूवारपणे श्वासोच्छ्वास करा. आपण या क्षणी सुरक्षित आहात.",
            "BN": "এখনই একটি গভীর এবং ধীর শ্বাস নিন। অতিরিক্ত উদ্বেগের সময় শান্ত থাকা জরুরি। পায়ের পাতা মাটিতে রেখে ধীরে ধীরে শ্বাস নিন ও ছাড়ুন। আপনি এই মুহূর্তে নিরাপদ।"
        },
        "grounding_calm": {
            "EN": "Focusing on calming exercises is a powerful way to reset your nervous system. Try the 4-7-8 breathing method: inhale gently through your nose for 4 counts, hold for 7, and exhale with a soft whoosh for 8 counts. Repeat this 3 times to soothe tension.",
            "HI": "मन को शांत करने के अभ्यास आपके तंत्रिका तंत्र को संतुलित करने का सर्वोत्तम उपाय हैं। 4-7-8 श्वास विधि अपनाएं: 4 सेकंड नाक से सांस लें, 7 सेकंड रोकें, और 8 सेकंड में धीरे-धीरे मुंह से छोड़ें। इसे 3 बार दोहराएं।",
            "TA": "4-7-8 சுவாச முறை உங்கள் மன அழுத்தத்தை உடனடியாகக் குறைக்கும்: 4 நொடிகள் மூச்சை உள்ளிழுத்து, 7 நொடிகள் நிறுத்தி, 8 நொடிகள் மெதுவாக வெளியிடவும். இதை 3 முறை செய்யவும்.",
            "TE": "4-7-8 శ్వాస పద్ధతి ఒత్తిడిని తగ్గిస్తుంది: 4 సెకన్లు ముక్కు ద్వారా పీల్చుకోండి, 7 సెకన్లు ఆపండి, 8 సెకన్లలో నోటి ద్వారా వదలండి. దీన్ని 3 సార్లు చేయండి.",
            "KN": "4-7-8 ಉಸಿರಾಟದ ವಿಧಾನವು ತಕ್ಷಣವೇ ಮನಸ್ಸನ್ನು ಶಾಂತಗೊಳಿಸುತ್ತದೆ: 4 ಸೆಕೆಂಡ್ ಉಸಿರೆಳೆದುಕೊಳ್ಳಿ, 7 ಸೆಕೆಂಡ್ ಹಿಡಿದಿಟ್ಟುಕೊಳ್ಳಿ, 8 ಸೆಕೆಂಡ್ ನಿಧಾನವಾಗಿ ಬಿಡಿ.",
            "MR": "4-7-8 श्वास तंत्र मानसिक शांततेसाठी अत्यंत उपयुक्त आहे: 4 सेकंद श्वास घ्या, 7 सेकंद रोखून धरा, 8 सेकंदात हळूहळू सोडा. हे 3 वेळा करा.",
            "BN": "4-7-8 শ্বাস পদ্ধতি আপনার উদ্বেগ দূর করতে সাহায্য করবে: 4 সেকেন্ড শ্বাস নিন, 7 সেকেন্ড ধরে রাখুন এবং 8 সেকেন্ডে ধীরে ধীরে শ্বাস ছাড়ুন।"
        },
        "positive_resilience": {
            "EN": "It is truly wonderful to hear that you are feeling steady, supported, and better today! Celebrating these moments of calm and resilience is a crucial part of your healing journey. How can we continue supporting your well-being today?",
            "HI": "यह जानकर बहुत खुशी और संतोष हुआ कि आप आज सहज, सुरक्षित और बेहतर महसूस कर रहे हैं! आत्म-विश्वास और शांति के ऐसे पलों का सम्मान करना आपके उपचार की यात्रा का महत्वपूर्ण हिस्सा है। आज हम आपकी और क्या सहायता कर सकते हैं?",
            "TA": "நீங்கள் இன்று நன்றாக உணர்வது மிகுந்த மகிழ்ச்சி அளிக்கிறது! மன அமைதி உங்கள் மீட்சியின் முக்கிய அடையாளம். இன்று உங்களுக்கு வேறு ஏதேனும் தகவல் தேவையா?",
            "TE": "ఈరోజు మీరు క్షేమంగా ఉన్నారని తెలుసుకోవడం చాలా ఆనందంగా ఉంది! మీ మనోధైర్యమే మీ బలం. ఈరోజు మేము మీకు ఇంకేమైనా సహాయం చేయగలమా?",
            "KN": "ಇಂದು ನೀವು ಸಮಾಧಾನವಾಗಿದ್ದೀರಿ ಎಂದು ತಿಳಿದು ಸಂತೋಷವಾಯಿತು! ನಿಮ್ಮ ಧೈರ್ಯವೇ ನಿಮ್ಮ ಶಕ್ತಿ. ಇಂದು ನಿಮಗೆ ಇನ್ನೇನು ಸಹಾಯ ಬೇಕು?",
            "MR": "तुम्ही आज बरे आणि सुरक्षित आहात हे जाणून खूप समाधान वाटले! मन शांत राहणे हे तुमच्या प्रगतीचे लक्षण आहे. आज आपण अजून काही बोलू इच्छिता?",
            "BN": "আজ আপনি ভালো এবং নিরাপদ আছেন জেনে খুব ভালো লাগল! নিজের যত্ন নেওয়া অত্যন্ত জরুরি। আজ আমরা আপনাকে আর কীভাবে সাহায্য করতে পারি?"
        },
        "assistant_identity": {
            "EN": "I am your MentAura Case-Aware Support Assistant, built under Section 15A of the SC/ST (Prevention of Atrocities) Act. I provide 24/7 confidential emotional support, real-time distress monitoring, witness protection guidance, legal aid navigation, and direct escalation to your assigned district counsellors.",
            "HI": "मैं आपका मेंटॉरा केस-जागरूक मानसिक स्वास्थ्य साथी हूँ, जिसे अनुसूचित जाति/जनजाति अत्याचार निवारण अधिनियम की धारा 15A के तहत विकसित किया गया है। मैं 24/7 गोपनीय भावनात्मक समर्थन, तनाव मूल्यांकन, सुरक्षा अधिकार मार्गदर्शन और परामर्शदाताओं से सीधा संपर्क प्रदान करता हूँ।",
            "TA": "நான் உங்கள் மென்டாரா மனநல உதவியாளர். பிரிவு 15A இன் கீழ் ரகசிய ஆதரவு, மன அழுத்த கண்காணிப்பு, சட்ட உதவி மற்றும் ஆலோசகர் இணைப்பை நான் வழங்குகிறேன்.",
            "TE": "నేను మీ మెంటౌరా మానసిక ఆరోగ్య సహాయకుడిని. సెక్షన్ 15A కింద పూర్తి గోప్యమైన సహాయం, భద్రతా మార్గదర్శనం మరియు కౌన్సెలర్ సంప్రదింపులను అందిస్తాను.",
            "KN": "ನಾನು ನಿಮ್ಮ ಮೆಂಟೌರಾ ಮಾನಸಿಕ ಆರೋಗ್ಯ ಸಹಾಯಕ. ಸೆಕ್ಷನ್ 15A ಅಡಿಯಲ್ಲಿ ಸಂಪೂರ್ಣ ರಹಸ್ಯ ಬೆಂಬಲ, ಕಾನೂನು ನೆರವು ಮತ್ತು ತಜ್ಞರ ಸಂಪರ್ಕವನ್ನು ಒದಗಿಸುತ್ತೇನೆ.",
            "MR": "मी आपला मेंटॉरा मानसिक आरोग्य सहाय्यक आहे. कलम 15A अन्वये गोपनीय मदत, ताणतणाव निरीक्षण, कायदेशीर माहिती आणि समुपदेशकांशी संवाद उपलब्ध करून देतो.",
            "BN": "আমি আপনার মেন্টরা সহায়তা সহকারী। ধারা ১৫A এর অধীনে গোপনীয় সহায়তা, মানসিক স্বাস্থ্য পর্যবেক্ষণ এবং আইনি দিকনির্দেশনা প্রদান করাই আমার কাজ।"
        },
        "greeting": {
            "EN": "Hello! How are you doing today? How can I help you?",
            "HI": "नमस्ते! आप आज कैसा महसूस कर रहे हैं? मैं आपकी क्या मदद कर सकता हूँ?",
            "TA": "வணக்கம்! இன்று நீங்கள் எப்படி இருக்கிறீர்கள்? நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
            "TE": "నమస్కారం! ఈరోజు మీరు ఎలా ఉన్నారు? నేను మీకు ఎలా సహాయపడగలను?",
            "KN": "ನಮಸ್ಕಾರ! ಇಂದು ನೀವು ಹೇಗಿದ್ದೀರಿ? ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
            "MR": "नमस्ते! आज आपण कसे आहात? मी आपल्याला कशी मदत करू शकतो?",
            "BN": "নমস্কার! আপনি আজ কেমন আছেন? আমি আপনাকে কীভাবে সাহায্য করতে পারি?"
        },
        "general_sharing": {
            "EN": "I am here to support you. How are you feeling today, or is there something specific about your case or well-being you would like to talk about?",
            "HI": "मैं आपकी सहायता के लिए यहाँ हूँ। आज आप कैसा महसूस कर रहे हैं, या अपने मामले और मानसिक स्वास्थ्य को लेकर कुछ पूछना चाहते हैं?",
            "TA": "நான் உங்களுக்கு உதவ தயாராக உள்ளேன். இன்று நீங்கள் எப்படி உணர்கிறீர்கள்? உங்கள் வழக்கு குறித்து ஏதேனும் பேச விரும்புகிறீர்களா?",
            "TE": "నేను మీకు సహాయం చేయడానికి సిద్ధంగా ఉన్నాను. ఈరోజు మీరు ఎలా ఉన్నారు? మీ కేసు లేదా సంక్షేమం గురించి ఏమైనా మాట్లాడాలనుకుంటున్నారా?",
            "KN": "ನಾನು ನಿಮಗೆ ಬೆಂಬಲ ನೀಡಲು ಇಲ್ಲಿದ್ದೇನೆ. ಇಂದು ನೀವು ಹೇಗಿದ್ದೀರಿ? ನಿಮ್ಮ ಪ್ರಕರಣ ಅಥವಾ ಆರೋಗ್ಯದ ಬಗ್ಗೆ ಏನಾದರೂ ಮಾತನಾಡಲು ಬಯಸುವಿರಾ?",
            "MR": "मी आपल्याला मदत करण्यासाठी उपस्थित आहे. आज आपण कसे आहात? आपल्या प्रकरणाविषयी काही बोलायचे आहे का?",
            "BN": "আমি আপনার সহায়তায় আছি। আজ আপনি কেমন আছেন? আপনার মামলা বা মানসিক স্বাস্থ্য সম্পর্কে কিছু বলতে চান?"
        }
    }

    # Action chip recommendations by domain
    ACTION_CHIPS_DB = {
        "greeting": ["Tell me about my rights", "I want to share how I feel", "Help with my case"],
        "opening": ["Tell me about my rights", "I want to share how I feel", "Help with my case"],
        "safety_threats": ["Immediate safety steps", "How to reach police", "Request protection"],
        "suicide_crisis": ["You are not alone", "Calm my racing thoughts", "Request counsellor now"],
        "court_hearing": ["How to prepare for court", "Calm before the hearing", "Know my rights in court"],
        "court_legal": ["How to prepare for court", "Calm before the hearing", "Know my rights in court"],
        "legal_process_inquiry": ["Steps in my case", "Legal aid options", "What happens next"],
        "compensation_welfare": ["How to claim", "Documents I need", "Talk to a legal advisor"],
        "neighbour_harassment": ["Document what happened", "Know my rights", "Talk to a counsellor"],
        "neighbor_harassment": ["Document what happened", "Know my rights", "Talk to a counsellor"],
        "sleep_somatic": ["Calming tips", "Try 4-7-8 Breathing", "Grounding exercise"],
        "sadness_isolation": ["Talk it out", "Calm my racing thoughts", "Request counsellor support"],
        "anxiety_panic": ["Try 4-7-8 Breathing", "5-4-3-2-1 Grounding", "Calm my racing thoughts"],
        "creative_cheerful": ["Show me more ideas", "Try Origami", "Cheerful playlist"],
        "interpersonal_family": ["Set boundaries", "Talk it out", "Request counsellor support"],
        "exam_academic": ["Exam preparation tips", "Calm before exam", "Rest tonight"],
        "career_workplace": ["Interview prep", "Calm my nerves", "Confidence boost"],
        "assistant_identity": ["What can you do?", "How does this help?", "My privacy"],
        "grounding_calm": ["Try 4-7-8 Breathing", "5-4-3-2-1 Grounding", "Calm my racing thoughts"],
        "positive_resilience": ["Tell me more", "Calm my thoughts", "Get support"],
        "general_sharing": ["Tell me about my rights", "I want to share how I feel", "Help with my case"],
        "default": ["Tell me more", "Calm my thoughts", "Get support"]
    }

    if domain == "greeting" and any(w in message.lower() for w in ["nice to meet", "good to meet", "pleased to meet"]):
        intro_replies = {
            "EN": "Hello! Nice to meet you too. How are you doing today? How can I help you?",
            "HI": "नमस्ते! आपसे मिलकर बहुत अच्छा लगा। आप आज कैसा महसूस कर रहे हैं? मैं आपकी क्या मदद कर सकता हूँ?",
            "TA": "வணக்கம்! உங்களை சந்தித்ததில் மிக்க மகிழ்ச்சி. இன்று உங்களுக்கு நான் எவ்வாறு உதவ முடியும்?",
            "TE": "నమస్కారం! మిమ్మల్ని కలవడం చాలా సంతోషంగా ఉంది. ఈరోజు నేను మీకు ఎలా సహాయపडగలను?",
            "KN": "ನಮಸ್ಕಾರ! ನಿಮ್ಮನ್ನು ಭೇಟಿಯಾಗಿದ್ದಕ್ಕೆ ಸಂತೋಷವಾಯಿತು. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
            "MR": "नमस्ते! आपल्याला भेटून खूप आनंद झाला. आज मी आपल्याला कशी मदत करू शकतो?",
            "BN": "নমস্কার! আপনার সাথে পরিচিত হয়ে ভালো লাগল। আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
        }
        reply_text = intro_replies.get(lang, intro_replies["EN"])
    else:
        reply_text = REPLIES_DB.get(domain, {}).get(lang, REPLIES_DB["general_sharing"]["EN"])
    suggested_actions = ACTION_CHIPS_DB.get(domain, ACTION_CHIPS_DB["default"])

    # Multi-turn context adaptation: if user repeats or continues, enrich response
    if prev_messages and len(prev_messages) > 0 and turn_number > 1:
        prev_domain = detect_message_domain(prev_messages[-1])
        if prev_domain == domain and domain not in ("greeting", "safety_threats", "suicide_crisis"):
            continuation_prefixes = {
                "EN": "I hear you continuing on this. It shows great courage to unpack these feelings step by step. ",
                "HI": "मैं समझ रहा हूँ कि आप इस विषय पर आगे बात कर रहे हैं। अपनी भावनाओं को व्यक्त करना एक बड़ा साहसी कदम है। ",
                "TA": "இதைப் பற்றி நீங்கள் தொடர்ந்து பேசுவது உங்கள் மன வலிமையைக் காட்டுகிறது. ",
                "TE": "దీనిపై మీరు వివరంగా మాట్లాడుతున్నందుకు అభినందనలు. మీ భావాలను వ్యక్తపరచడం చాలా ముఖ్యం. ",
                "KN": "ಈ ವಿಷಯದ ಬಗ್ಗೆ ನೀವು ಮುಕ್ತವಾಗಿ ಮಾತನಾಡುತ್ತಿರುವುದು ನಿಮ್ಮ ಧೈರ್ಯವನ್ನು ತೋರಿಸುತ್ತದೆ. ",
                "MR": "आपण या विषयावर पुढे बोलत आहात हे आपले धैर्य दर्शवते. ",
                "BN": "এই বিষয়ে আপনার কথা চালিয়ে যাওয়া মানসিক সাহসের পরিচায়ক। "
            }
            reply_text = continuation_prefixes.get(lang, continuation_prefixes["EN"]) + reply_text

    # Avoid exact consecutive duplicate responses
    if last_reply and reply_text == last_reply:
        if domain == "greeting":
            alt_greeting = {
                "EN": "Hello again! How can I help you today?",
                "HI": "नमस्ते पुनः! आज मैं आपकी क्या मदद कर सकता हूँ?",
                "TA": "மீண்டும் வணக்கம்! இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
                "TE": "మరోసారి నమస్కారం! ఈరోజు నేను మీకు ఎలా సహాయపడగలను?",
                "KN": "ಮತ್ತೊಮ್ಮೆ ನಮಸ್ಕಾರ! ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
                "MR": "पुन्हा एकदा नमस्ते! आज मी आपल्याला कशी मदत करू शकतो?",
                "BN": "আবারো নমস্কার! আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
            }
            reply_text = alt_greeting.get(lang, alt_greeting["EN"])
        else:
            alt_follow = {
                "EN": "I am listening closely to everything you're sharing. Please take all the time you need — what else has been weighing on you?",
                "HI": "मैं आपकी हर बात बहुत ध्यान से सुन रहा हूँ। आप जितना समय चाहें ले सकते हैं — क्या कोई और बात भी आपको परेशान कर रही है?",
                "TA": "நான் உங்கள் ஒவ்வொரு வார்த்தையையும் கவனிக்கிறேன். நிதானமாக சொல்லுங்கள் — வேறு என்ன உங்கள் மனதில் உள்ளது?",
                "TE": "నేను మీ ప్రతి మాటను శ్రద్ధగా వింటున్నాను. ఇంకేమైనా మీకు బాధ కలిగిస్తోందా?",
                "KN": "ನಾನು ನಿಮ್ಮ ಪ್ರತಿಯೊಂದು ಮಾತನ್ನು ಗಮನವಿಟ್ಟು ಕೇಳುತ್ತಿದ್ದೇನೆ. ಇನ್ನೂ ಏನಾದರೂ ನಿಮಗೆ ನೋವು ತರುತ್ತಿದೆಯೇ?",
                "MR": "मी आपले प्रत्येक शब्द लक्षपूर्वक ऐकत आहे. आपल्याला अजून काही सांगायचे आहे का?",
                "BN": "আমি আপনার প্রতিটি কথা মন দিয়ে শুনছি। আর কোনো বিষয় কি আপনাকে কষ্ট দিচ্ছে?"
            }
            reply_text = alt_follow.get(lang, alt_follow["EN"])

    return {
        "reply": reply_text,
        "severity_level": severity,
        "dynamic_score": final_score,
        "primary_emotion": primary_emotion,
        "domain": domain,
        "coping_techniques": TECHNIQUES_DATA.get(lang, TECHNIQUES_DATA["EN"]) if ((domain in ("grounding_calm", "anxiety_panic", "sleep_somatic") or any(w in message.lower() for w in ["calm", "relax", "breathe", "breathing", "exercise", "technique", "grounding", "coping"])) and domain not in ("greeting", "assistant_identity", "legal_process_inquiry", "compensation_welfare", "positive_resilience")) else [],
        "escalation_contact": ESCALATION_CONTACTS_DATA.get(lang, ESCALATION_CONTACTS_DATA["EN"]) if severity == "medium" else None,
        "alert_details": ALERT_DETAILS_DATA.get(lang, ALERT_DETAILS_DATA["EN"]) if (severity == "high" and domain in ("suicide_crisis", "safety_threats")) else None,
        "suggested_actions": suggested_actions
    }
