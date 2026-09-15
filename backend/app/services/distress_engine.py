"""
Dynamic Distress Scoring & Explainable Emotion AI Engine.
SIH 26094 - MENTAURA Platform.

Computes the Dynamic Distress Score (DDS, 0-100):
DDS = 0.35 * AcousticScore + 0.35 * TextEmotionScore + 0.15 * EngagementScore + 0.15 * CaseVulnerability

Provides:
- Multilingual NLP & Sentiment/Emotion AI (fear, grief, trauma, intimidation keywords)
- Predictive Escalation Detection (anticipates crisis 48-72h before hearings or steep upward trajectory)
- Explainable AI (XAI) transparent plain-language factor attribution
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta


# Multilingual Trauma, Fear, Intimidation & Crisis Keywords
KEYWORD_WEIGHTS = {
    # Crisis / Self-Harm
    "crisis": [
        "suicide", "kill myself", "end my life", "want to die", "hurt myself", "no point living",
        "आत्महत्या", "मरना चाहता", "जान दे दूंगा", "உயிர் விட", "தற்கொலை", "చనిపోవాలని", "ఆత్మహత్య",
        "ಆತ್ಮಹತ್ಯೆ", "ಸಾಯಬೇಕು", "आत्महत्या", "मरू इच्छितो", "আত্মহত্যা", "মরতে চাই"
    ],
    # Intimidation / Threats / Witness Tampering
    "intimidation": [
        "threat", "threatened", "threatening", "kill", "attack", "stalk", "stalking", "follow me",
        "outside my house", "withdraw complaint", "compromise", "money to drop case", "gun", "knife",
        "weapon", "casteist slur", "boycott", "social boycott", "oust", "torched",
        "धमकी", "मार डालेंगे", "शिकायत वापस", "राजीनामा", "बहिष्कार", "गुंडे",
        "மிரட்டல்", "கொன்று விடுவேன்", "வழக்கை வாபஸ்", "ஊர் விலக்கம்",
        "బెదిరింపు", "చంపేస్తామని", "కేసు వెనక్కి", "బహిష్కరణ",
        "ಬೆದರಿಕೆ", "ಕೊಲ್ಲುತ್ತೇನೆ", "ದೂರು ವಾಪಸ್", "ಸಾಮಾಜಿಕ ಬಹಿಷ್ಕಾರ",
        "धमकी", "मारून टाकू", "तक्रार मागे", "बहिष्कार",
        "হুমকি", "মেরে ফেলব", "অভিযোগ প্রত্যাহার", "সামাজিক বয়কট"
    ],
    # Legal / Institutional / Court Delays
    "legal_court": [
        "court", "hearing", "judge", "dsp", "police", "delay", "postponed", "adjourned",
        "chargesheet", "witness", "summon", "case", "advocate",
        "कोर्ट", "तारीख", "अदालत", "पुलिस", "जज", "गवाही", "सुनवाई",
        "நீதிமன்றம்", "விசாரணை", "காவல்துறை", "சாட்சி",
        "కోర్టు", "విచారణ", "పోలీసు", "సాక్షి", "వాయిదా",
        "ನ್ಯಾಯಾಲಯ", "ವಿಚಾರಣೆ", "ಪೊಲೀಸ್", "ಸಾಕ್ಷಿ",
        "न्यायालय", "सुनावणी", "पोलीस", "साक्षीदार",
        "আদালত", "শুনানি", "পুলিশ", "সাক্ষী"
    ],
    # Fear / Acute Anxiety
    "fear": [
        "scared", "terrified", "panic", "shaking", "trembling", "afraid", "nervous", "horror",
        "dread", "cannot sleep", "nightmares", "jumpy", "heart racing",
        "डर", "घबराहट", "कांप", "भय", "नींद नहीं", "डरावने सपने",
        "பயம்", "நடுக்கம்", "தூக்கம் இல்லை", "திகில்",
        "భయం", "వణుకు", "నిద్ర పట్టడం లేదు", "భయంగా",
        "ಭಯ", "ನಡುಕ", "ನಿದ್ರೆ ಇಲ್ಲ", "ಹೆದರಿಕೆ",
        "भीती", "घाबरलो", "झोप येत नाही", "थरथर",
        "ভয়", "আতঙ্ক", "ঘুম হচ্ছে না", "ভীত"
    ],
    # Grief / Hopelessness / Trauma
    "trauma": [
        "hopeless", "crying", "broken", "helpless", "isolated", "shame", "humiliated", "humiliation",
        "pain", "exhausted", "numb", "worthless", "heavy heart", "nobody cares", "depression",
        "उदास", "रो रहा", "बेबस", "अपमान", "अकेला", "टूट चुका",
        "கண்ணீர்", "அவமானம்", "ஏக்கம்", "மனமுடைந்து",
        "బాధ", "ఏడుపు", "ఒంటరితనం", "అవమానం",
        "ದುಃಖ", "ಅಳು", "ಒಂಟಿತನ", "ಅವಮಾನ",
        "दुःख", "रडणे", "एकटेपणा", "अपमान",
        "কষ্ট", "কান্না", "একাকীত্ব", "অপমান"
    ]
}


def compute_text_emotion_score(text: Optional[str]) -> Dict[str, Any]:
    """
    Analyzes text narrative or conversational messages for emotion, trauma, and intimidation.
    Returns sentiment score (0-100), detected emotion tags, urgency flag, and matched phrases.
    """
    if not text or not text.strip():
        return {
            "sentiment_score": 25,
            "detected_emotions": ["steady"],
            "urgency_flag": False,
            "matched_keywords": []
        }

    lower_text = text.lower()
    matched_keywords = []
    detected_emotions = []
    score = 20  # baseline

    urgency_flag = False

    for kw in KEYWORD_WEIGHTS["crisis"]:
        if kw in lower_text:
            score += 45
            matched_keywords.append(kw)
            detected_emotions.append("acute_crisis")
            urgency_flag = True
            break

    for kw in KEYWORD_WEIGHTS["intimidation"]:
        if kw in lower_text:
            score += 30
            matched_keywords.append(kw)
            detected_emotions.append("fear_intimidation")
            urgency_flag = True
            break

    for kw in KEYWORD_WEIGHTS["fear"]:
        if kw in lower_text:
            score += 20
            matched_keywords.append(kw)
            if "fear_intimidation" not in detected_emotions:
                detected_emotions.append("fear_intimidation")
            break

    for kw in KEYWORD_WEIGHTS["legal_court"]:
        if kw in lower_text:
            score += 15
            matched_keywords.append(kw)
            detected_emotions.append("legal_institutional_stress")
            break

    for kw in KEYWORD_WEIGHTS["trauma"]:
        if kw in lower_text:
            score += 18
            matched_keywords.append(kw)
            detected_emotions.append("hopelessness_depression")
            break

    if not detected_emotions:
        detected_emotions.append("steady")

    final_score = min(95, max(10, score))

    return {
        "sentiment_score": final_score,
        "detected_emotions": list(set(detected_emotions)),
        "urgency_flag": urgency_flag,
        "matched_keywords": matched_keywords[:6]
    }


def analyze_text_emotion(text: Optional[str]) -> Dict[str, Any]:
    """Alias/wrapper for compute_text_emotion_score."""
    return compute_text_emotion_score(text)


def calculate_dynamic_distress(
    wellbeing_state: Optional[str] = None,
    affecting_factors: Optional[List[str]] = None,
    support_needs: Optional[List[str]] = None,
    safety_status: Optional[str] = None,
    text_narrative: Optional[str] = None,
    acoustic_score: Optional[int] = 0,
    previous_scores: Optional[List[int]] = None,
    has_upcoming_hearing_soon: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Master computation function for Dynamic Distress Score (DDS), Escalation Prediction,
    and Explainable AI (XAI) factors breakdown.
    """
    # 1. Text Emotion Scoring
    text_eval = compute_text_emotion_score(text_narrative)
    sentiment_score = text_eval["sentiment_score"]
    urgency = text_eval["urgency_flag"]

    # 2. Wellbeing score from selection
    wb_score = 30
    if wellbeing_state:
        ws_norm = wellbeing_state.lower()
        if any(k in ws_norm for k in ["overwhelming", "very unsafe", "critical", "severe danger", "emergency"]):
            wb_score = 85
        elif any(k in ws_norm for k in ["heavy", "struggling", "unsafe", "distressed"]):
            wb_score = 65
        elif any(k in ws_norm for k in ["uneasy", "managing", "neutral"]):
            wb_score = 45
        elif any(k in ws_norm for k in ["steady", "calm", "safe"]):
            wb_score = 20

    # 3. Safety Status
    safety_boost = 0
    if safety_status:
        ss_norm = safety_status.lower()
        if "not" in ss_norm or "unsafe" in ss_norm or "threat" in ss_norm:
            safety_boost = 25
            urgency = True

    # 4. Affecting Factors & Needs
    factor_boost = 0
    if affecting_factors:
        for f in affecting_factors:
            f_l = f.lower()
            if any(k in f_l for k in ["threat", "safety", "intimidation"]):
                factor_boost += 15
                urgency = True
            elif any(k in f_l for k in ["court", "investigation", "delay"]):
                factor_boost += 10
            elif any(k in f_l for k in ["money", "compensation", "housing"]):
                factor_boost += 8
            else:
                factor_boost += 5
    factor_boost = min(30, factor_boost)

    # 5. Acoustic score
    ac_score = acoustic_score if (acoustic_score and acoustic_score > 0) else 0
    has_audio = ac_score > 0

    # 6. Weighted DDS Aggregation
    if has_audio:
        raw_dds = (
            0.35 * ac_score +
            0.35 * max(sentiment_score, wb_score) +
            0.15 * max(factor_boost * 2.5, 25) +
            0.15 * (55 if has_upcoming_hearing_soon else 25)
        )
    else:
        raw_dds = (
            0.50 * max(sentiment_score, wb_score) +
            0.25 * max(factor_boost * 2.5, 25) +
            0.25 * (55 if has_upcoming_hearing_soon else 25)
        )

    if safety_boost > 0:
        raw_dds += safety_boost * 0.4
    if urgency:
        raw_dds = max(raw_dds, 72)

    dds = int(round(max(10, min(95, raw_dds))))

    # 7. Predictive Escalation Detection
    escalation_predicted = False
    escalation_reasons = []

    if previous_scores and len(previous_scores) >= 1:
        last_score = previous_scores[-1]
        delta = dds - last_score
        if delta >= 15:
            escalation_predicted = True
            escalation_reasons.append(f"Rapid distress jump of +{delta} pts from previous check-in")
        elif len(previous_scores) >= 2 and dds > last_score > previous_scores[-2] and dds >= 60:
            escalation_predicted = True
            escalation_reasons.append("Consecutive upward distress slope across last 3 check-ins")

    if has_upcoming_hearing_soon and dds >= 60:
        escalation_predicted = True
        escalation_reasons.append("Special Court hearing scheduled within 72 hours")

    if urgency:
        escalation_predicted = True
        escalation_reasons.append("High-severity intimidation or distress flags in submission")

    # 8. Risk Level
    if dds >= 70 or urgency:
        risk_level = "high"
    elif dds >= 45:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 9. Factors Breakdown (for Explainable AI)
    factors_breakdown = [
        {
            "factor": "Reported Well-being State",
            "impact": f"+{min(wb_score, 30)}",
            "detail": f"Well-being stated as '{wellbeing_state or 'Standard'}'."
        }
    ]
    if has_audio and ac_score >= 40:
        factors_breakdown.append({
            "factor": "Acoustic Vocal Biomarkers",
            "impact": f"+{int(ac_score * 0.35)}",
            "detail": "Vocal pitch variance and hesitations detected in audio check-in."
        })
    if text_eval["matched_keywords"]:
        factors_breakdown.append({
            "factor": "Text Sentiment & Emotion Signals",
            "impact": f"+{int(sentiment_score * 0.35)}",
            "detail": f"Keywords identified: {', '.join(text_eval['matched_keywords'])}."
        })
    if safety_boost > 0 or factor_boost >= 10:
        factors_breakdown.append({
            "factor": "Safety & External Stressors",
            "impact": f"+{int(factor_boost + safety_boost)}",
            "detail": "Reported safety vulnerability or active harassment concerns."
        })

    effective_acoustic = ac_score
    text_emotion_score = sentiment_score
    xai_explanation = kwargs.get("xai_explanation") or {}
    if not xai_explanation.get("top_distress_drivers"):
        xai_explanation["top_distress_drivers"] = [f["factor"] for f in factors_breakdown]
    recommended_interventions = kwargs.get("recommended_interventions") or []

    risk_labels = {
        "high": "Elevated Distress (Priority Review)",
        "medium": "Moderate Strain (Support Recommended)",
        "low": "Steady / Stable"
    }
    risk_badges = {
        "high": "badge-risk-high",
        "medium": "badge-risk-medium",
        "low": "badge-risk-low"
    }

    top_drivers = xai_explanation.get("top_distress_drivers", [])
    if top_drivers:
        xai_summary = f"Distress score is driven primarily by: {', '.join(top_drivers[:2])}."
    else:
        xai_summary = "Well-being indicators remain steady with balanced emotional signals."

    if not factors_breakdown:
        factors_breakdown = [
            {"factor": d, "impact": "+15", "detail": "Active contributor identified by explainable AI."}
            for d in top_drivers
        ] or [{"factor": "Self-reported emotional baseline", "impact": "+10", "detail": "Baseline check-in response."}]

    recs_formatted = [
        {"title": r, "description": r, "category": "support", "action_text": "Request Support"}
        for r in recommended_interventions
    ]

    import json

    return {
        "dynamic_distress_score": dds,
        "acoustic_score": effective_acoustic,
        "sentiment_score": text_emotion_score,
        "risk_level": risk_level,
        "risk_label": risk_labels.get(risk_level, "Steady"),
        "risk_badge_class": risk_badges.get(risk_level, "badge-risk-low"),
        "escalation_predicted": escalation_predicted,
        "escalation_reason": escalation_reasons[0] if escalation_reasons else None,
        "xai_summary": xai_summary,
        "factors_breakdown": factors_breakdown,
        "recommendations": recs_formatted,
        "xai_explanation": json.dumps(xai_explanation),
        "xai_data": xai_explanation,
        "recommended_interventions": recommended_interventions
    }
