"""
Transparent, Rule-Based Light Risk Scoring Service for Support Pulses.
SIH26094 — MENTAURA Secure Support Intelligence Platform.

Calculates an explainable risk score (0+) and risk level ("low" | "medium" | "high")
based on transparent, auditable rules without black-box clinical determinations.
"""
from typing import Dict, Any, List, Optional


def calculate_risk_score(
    wellbeing_state: Optional[str] = None,
    affecting_factors: Optional[List[str]] = None,
    support_needs: Optional[List[str]] = None,
    text_note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes a deterministic, explainable risk assessment for a Support Pulse.

    Scoring Breakdown:
    1. Wellbeing State:
       - "Very unsafe" / "very_unsafe" / "high_distress" -> +3
       - "Unsafe" / "unsafe" / "distressed"             -> +2
       - "Neutral" / "neutral" / "uneasy" / "overwhelmed" -> +1
       - "Safe" / "Very safe" / "steady" / "calm"         -> +0

    2. Affecting Factors:
       - Self-harm / Suicidal thoughts / Severe crisis   -> +3
       - Threats / Violence / Stalking / Intimidation     -> +2
       - Housing insecurity / Financial distress / Family -> +1

    3. Support Needs:
       - Emergency protection / Medical / Police aid     -> +2
       - Legal aid / Psychological Counselling / Rehab   -> +1

    4. Text Keyword Matches (Cap: +3):
       - +1 per distinct keyword: threat, hurt myself, kill, suicide,
         police, court, shelter, emergency, danger, weapon, stalking, violence

    Thresholds:
    - 0 – 2 : "low"
    - 3 – 5 : "medium"
    - 6+    : "high"
    """
    score = 0
    breakdown = {
        "wellbeing_score": 0,
        "factors_score": 0,
        "needs_score": 0,
        "text_score": 0
    }

    # 1. Wellbeing State Scoring
    if wellbeing_state:
        ws_norm = str(wellbeing_state).strip().lower().replace("_", " ")
        if any(k in ws_norm for k in ["very unsafe", "high distress", "critical", "severe danger", "emergency"]):
            breakdown["wellbeing_score"] = 3
        elif any(k in ws_norm for k in ["unsafe", "distressed", "fearful", "scared"]):
            breakdown["wellbeing_score"] = 2
        elif any(k in ws_norm for k in ["neutral", "uneasy", "struggling", "overwhelmed", "anxious"]):
            breakdown["wellbeing_score"] = 1
        else:
            breakdown["wellbeing_score"] = 0
        score += breakdown["wellbeing_score"]

    # 2. Affecting Factors Scoring
    if affecting_factors:
        factors_pts = 0
        for factor in affecting_factors:
            f_norm = str(factor).strip().lower()
            if any(k in f_norm for k in ["self-harm", "suicid", "kill myself", "end my life"]):
                factors_pts += 3
            elif any(k in f_norm for k in ["threat", "violenc", "stalk", "intimidat", "abus", "harass", "physical safety"]):
                factors_pts += 2
            elif any(k in f_norm for k in ["housing", "financial", "money", "employment", "family", "isolat"]):
                factors_pts += 1
            else:
                factors_pts += 1
        breakdown["factors_score"] = factors_pts
        score += factors_pts

    # 3. Support Needs Scoring
    if support_needs:
        needs_pts = 0
        for need in support_needs:
            n_norm = str(need).strip().lower()
            if any(k in n_norm for k in ["protection", "police", "shelter", "emergency", "medical", "hospital"]):
                needs_pts += 2
            elif any(k in n_norm for k in ["legal", "counselling", "psycholog", "compensation", "rehab"]):
                needs_pts += 1
            else:
                needs_pts += 1
        breakdown["needs_score"] = needs_pts
        score += needs_pts

    # 4. Text Keyword Matches (Cap at +3)
    if text_note:
        t_norm = str(text_note).strip().lower()
        keywords = [
            "threat", "hurt myself", "kill", "suicide", "police", "court",
            "shelter", "emergency", "danger", "weapon", "stalk", "violenc",
            "scared", "attack", "fear"
        ]
        matched_keywords = [kw for kw in keywords if kw in t_norm]
        text_pts = min(len(matched_keywords), 3)
        breakdown["text_score"] = text_pts
        score += text_pts

    # 5. Determine Qualitative Risk Level
    if score >= 6:
        risk_level = "high"
    elif score >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "breakdown": breakdown
    }
