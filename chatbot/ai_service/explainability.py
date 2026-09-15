"""
Explainability Layer — Module 5
Produces human-readable explanations for any AI output.
Used by counsellor dashboards, alerts, and audit trails.
"""

from typing import Optional

from schemas.distress import DistressResult
from schemas.escalation import EscalationResult
from schemas.intervention import InterventionResult


# ============================================================
# Reason code → human phrase
# ============================================================

REASON_CODE_HUMAN = {
    # Wellbeing
    "WELLBEING_VERY_UNSAFE": "felt very unsafe",
    "WELLBEING_UNSAFE": "felt unsafe",
    "WELLBEING_NEUTRAL": "felt neutral",
    "WELLBEING_SAFE": "felt safe",
    "WELLBEING_VERY_SAFE": "felt very safe",
    "WELLBEING_UNKNOWN": "wellbeing not stated",

    # Factors
    "FACTOR_SUICIDAL_THOUGHTS": "reported suicidal thoughts",
    "FACTOR_SELF_HARM": "reported self-harm",
    "FACTOR_THREATS": "reported threats",
    "FACTOR_DISPLACEMENT": "reported displacement",
    "FACTOR_FINANCIAL_STRESS": "reported financial stress",
    "FACTOR_SOCIAL_OSTRACISM": "reported social ostracism",
    "FACTOR_LEGAL_STRESS": "reported legal stress",
    "FACTOR_HEALTH_ISSUES": "reported health issues",

    # Case stage
    "CASESTAGE_FIR_FILED": "case at FIR stage",
    "CASESTAGE_INVESTIGATION": "case under investigation",
    "CASESTAGE_COURT": "case at court stage",
    "CASESTAGE_POST_JUDGMENT": "case post-judgment",
    "CASESTAGE_REHABILITATION": "case in rehabilitation",

    # Text
    "TEXT_NEGATIVE_SENTIMENT": "text showed negative sentiment",
    "TEXT_POSITIVE_SENTIMENT": "text showed positive sentiment",
    "TEXT_FEAR": "text showed fear",
    "TEXT_SADNESS": "text showed sadness",
    "TEXT_ANGER": "text showed anger",
    "TEXT_DISGUST": "text showed disgust",
    "TEXT_JOY": "text showed joy",

    # Overrides
    "SELF_HARM_FLOOR": "self-harm signal → forced to critical",
    "THREAT_FLOOR": "threat detected → elevated to high",
    "THREAT_CAP": "threat ceiling applied",
    "HOPELESSNESS_FLOOR": "hopelessness detected → elevated to high",
    "HOPELESSNESS_CAP": "hopelessness ceiling applied",
}


def _humanize_reason(code: str) -> str:
    """Translate a reason code to human-readable text."""
    # Direct match
    if code in REASON_CODE_HUMAN:
        return REASON_CODE_HUMAN[code]

    # Prefix matches (e.g. CRITICAL_THEME_SUICIDAL_IDEATION)
    if code.startswith("CRITICAL_THEME_"):
        theme = code.replace("CRITICAL_THEME_", "").replace("_", " ").lower()
        return f"critical theme detected: {theme}"
    if code.startswith("FACTOR_"):
        factor = code.replace("FACTOR_", "").split(":")[0].replace("_", " ").lower()
        return f"factor: {factor}"
    if code.startswith("WELLBEING_"):
        wb = code.replace("WELLBEING_", "").split(":")[0].replace("_", " ").lower()
        return f"wellbeing: {wb}"

    # Fallback: just prettify
    return code.replace("_", " ").lower()


# ============================================================
# Public API
# ============================================================

def explain_distress(result: DistressResult) -> str:
    """Human-readable explanation of a distress result."""
    lines = []
    lines.append(f"RISK ASSESSMENT — Victim {result.victim_id}")
    lines.append("─" * 40)
    lines.append(
        f"Score: {result.distress_score:.0f}/100  |  "
        f"Level: {_level_str(result.risk_level).upper()}"
    )
    lines.append("")

    # Why this score
    lines.append("Why this score:")
    if result.reason_codes:
        for code in result.reason_codes:
            lines.append(f"  • {_humanize_reason(code)}")
    else:
        lines.append("  • no specific signals")

    lines.append("")

    # Risk factors
    if result.risk_factors:
        human = ", ".join(f.replace("_", " ") for f in result.risk_factors)
        lines.append(f"Key factors: {human}")

    return "\n".join(lines)


def explain_escalation(result: EscalationResult) -> str:
    """Human-readable explanation of an escalation result."""
    lines = []
    lines.append(f"ESCALATION ANALYSIS — Victim {result.victim_id}")
    lines.append("─" * 40)
    lines.append(
        f"Trend: {_level_str(result.trend_direction).upper()}  |  "
        f"Escalation flagged: {'YES' if result.escalation_flag else 'no'}"
    )
    lines.append("")

    scores_str = " → ".join(f"{s:.0f}" for s in result.recent_scores)
    lines.append(f"Recent scores: {scores_str}")
    lines.append(f"Avg change: {result.avg_delta:+.1f} per check-in")
    lines.append("")

    if result.escalation_reasons:
        lines.append("Escalation reasons:")
        for reason in result.escalation_reasons:
            lines.append(f"  • {reason.replace('_', ' ')}")

    return "\n".join(lines)


def explain_intervention(result: InterventionResult) -> str:
    """Human-readable explanation of an intervention recommendation."""
    lines = []
    lines.append(f"INTERVENTION PLAN — Victim {result.victim_id}")
    lines.append("─" * 40)
    lines.append(f"Priority: {_level_str(result.priority).upper()}")
    lines.append("")

    if result.recommended_interventions:
        lines.append("Recommended actions:")
        for i in result.recommended_interventions:
            lines.append(f"  → {_level_str(i).replace('_', ' ')}")
    else:
        lines.append("No specific interventions.")

    lines.append("")
    lines.append(f"Reasoning: {result.reasoning}")

    return "\n".join(lines)


def explain_full_turn(
    distress: DistressResult,
    escalation: Optional[EscalationResult] = None,
    intervention: Optional[InterventionResult] = None,
) -> str:
    """Complete report combining all three modules."""
    parts = ["", "=" * 60, explain_distress(distress), "=" * 60]

    if escalation:
        parts.extend(["", explain_escalation(escalation), "=" * 60])

    if intervention:
        parts.extend(["", explain_intervention(intervention), "=" * 60])

    return "\n".join(parts)


# ============================================================
# Helpers
# ============================================================

def _level_str(val) -> str:
    """Normalize enum or str → string."""
    if val is None:
        return ""
    if hasattr(val, "value"):
        return val.value
    s = str(val)
    if "." in s:
        s = s.split(".")[-1]
    return s