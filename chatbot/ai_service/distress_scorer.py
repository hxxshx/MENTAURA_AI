"""
Distress Scorer — Module 1 (the heart of Mentaura)
Combines structured pulse data + text analysis → Dynamic Distress Score (0-100).

Hybrid design:
- Rule engine   → baseline score (fully explainable)
- Text analysis → bounded adjustment (±15, adds nuance)
- Critical themes → severity-differentiated handling with bands:
    * Self-harm / suicidal ideation  → force CRITICAL band [86, 100]
    * Threats / violence fear        → force HIGH band    [70, 84]
    * Hopelessness                   → force HIGH band    [61, 84]
"""

from typing import Optional

from config import get_settings
from schemas.pulse import PulseInput
from schemas.text_analysis import TextAnalysisResult
from schemas.distress import DistressResult, RiskLevel


# ============================================================
# RULE ENGINE TABLES
# ============================================================

WELLBEING_BASE_SCORE = {
    "very_unsafe": 80,
    "unsafe": 60,
    "neutral": 40,
    "safe": 20,
    "very_safe": 10,
}

FACTOR_BONUS = {
    "suicidal_thoughts": 20,
    "self_harm": 15,
    "threats": 15,
    "displacement": 10,
    "financial_stress": 5,
    "social_ostracism": 5,
    "legal_stress": 5,
    "health_issues": 5,
}

CASE_STAGE_BONUS = {
    "fir_filed": 0,
    "investigation": 5,
    "court": 10,
    "post_judgment": 5,
    "rehabilitation": 0,
}


# ============================================================
# CRITICAL THEME SEVERITY CLASSIFICATION
# ============================================================
# Self-harm themes → internal danger → force CRITICAL band [86, 100]
# Threats / violence → external danger → force HIGH band [70, 84]
# Hopelessness → pre-crisis → force HIGH band [61, 84]
# ============================================================

SELF_HARM_THEMES = {"suicidal_ideation", "self_harm"}
THREAT_THEMES = {"threats", "violence_fear"}
HOPELESS_THEMES = {"hopelessness"}

# Bands (floor, ceiling)
SELF_HARM_BAND = (86.0, 100.0)
THREAT_BAND = (70.0, 84.0)
HOPELESSNESS_BAND = (61.0, 84.0)


# ============================================================
# TEXT ADJUSTMENT (bounded ±15)
# ============================================================

def _compute_text_adjustment(
    text_analysis: Optional[TextAnalysisResult],
) -> tuple[float, list[str]]:
    """Bounded adjustment from NLP signals. Returns (adjustment, reason_codes)."""
    if text_analysis is None:
        return 0.0, []

    adjustment = 0.0
    reasons = []

    # Sentiment contribution (max ±8)
    if text_analysis.sentiment_label == "negative":
        adj = min(text_analysis.sentiment_score * 8, 8)
        adjustment += adj
        reasons.append(f"TEXT_NEGATIVE_SENTIMENT:+{adj:.1f}")
    elif text_analysis.sentiment_label == "positive":
        adj = -min(text_analysis.sentiment_score * 5, 5)
        adjustment += adj
        reasons.append(f"TEXT_POSITIVE_SENTIMENT:{adj:.1f}")

    # Emotion contribution (max ±7)
    if text_analysis.emotion_label in ("fear", "sadness", "disgust"):
        adj = min(text_analysis.emotion_score * 7, 7)
        adjustment += adj
        reasons.append(f"TEXT_{text_analysis.emotion_label.upper()}:+{adj:.1f}")
    elif text_analysis.emotion_label == "joy":
        adj = -min(text_analysis.emotion_score * 4, 4)
        adjustment += adj
        reasons.append(f"TEXT_JOY:{adj:.1f}")

    return round(adjustment, 2), reasons


# ============================================================
# SCORER
# ============================================================

class DistressScorer:
    """Stateless scorer. Feed it a pulse + optional text analysis."""

    def __init__(self):
        self.settings = get_settings()

    def _compute_rule_score(
        self, pulse: PulseInput, text_analysis: Optional[TextAnalysisResult] = None
    ) -> tuple[float, list[str], list[str]]:
        """Returns (rule_score, reason_codes, risk_factors)."""
        reasons: list[str] = []
        factors: list[str] = []

        # Wellbeing baseline
        if pulse.wellbeing_state:
            base = WELLBEING_BASE_SCORE.get(pulse.wellbeing_state, 40)
            reasons.append(f"WELLBEING_{pulse.wellbeing_state.upper()}:+{base}")
            factors.append(f"{pulse.wellbeing_state}_state")
        elif text_analysis:
            if text_analysis.critical_themes:
                base = 75
                reasons.append("TEXT_CRITICAL_THEME_BASE:+75")
            elif text_analysis.sentiment_label == "positive":
                base = 15
                reasons.append("TEXT_POSITIVE_BASE:+15")
            elif text_analysis.distress_intensity == "high":
                base = 65
                reasons.append("TEXT_HIGH_DISTRESS_BASE:+65")
            elif text_analysis.distress_intensity == "medium":
                base = 45
                reasons.append("TEXT_MEDIUM_DISTRESS_BASE:+45")
            elif text_analysis.sentiment_label == "neutral" and text_analysis.emotion_label == "neutral":
                base = 25
                reasons.append("TEXT_NEUTRAL_BASE:+25")
            else:
                base = 35
                reasons.append("TEXT_DEFAULT_BASE:+35")
        else:
            base = 40
            reasons.append("WELLBEING_UNKNOWN:+40")

        score = float(base)

        # Affecting factors
        for factor in pulse.affecting_factors or []:
            bonus = FACTOR_BONUS.get(factor, 0)
            if bonus:
                score += bonus
                reasons.append(f"FACTOR_{factor.upper()}:+{bonus}")
                factors.append(factor)

        # Case stage
        if pulse.case_stage:
            bonus = CASE_STAGE_BONUS.get(pulse.case_stage, 0)
            if bonus:
                score += bonus
                reasons.append(f"CASESTAGE_{pulse.case_stage.upper()}:+{bonus}")
                factors.append(f"case_stage_{pulse.case_stage}")

        score = max(0.0, min(100.0, score))
        return score, reasons, factors

    def _map_risk_level(self, score: float) -> RiskLevel:
        s = self.settings
        if score <= s.RISK_LOW_MAX:
            return RiskLevel.LOW
        elif score <= s.RISK_MEDIUM_MAX:
            return RiskLevel.MEDIUM
        elif score <= s.RISK_HIGH_MAX:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _build_explanation(
        self,
        score: float,
        risk_level: RiskLevel,
        risk_factors: list[str],
        critical_themes: list[str],
    ) -> str:
        parts = [f"Distress score {score:.0f}/100 ({risk_level.value})."]

        if critical_themes:
            human = ", ".join(t.replace("_", " ") for t in critical_themes)
            parts.append(f"Critical signals detected: {human}.")

        if risk_factors:
            top = risk_factors[:3]
            human = ", ".join(f.replace("_", " ") for f in top)
            parts.append(f"Key contributing factors: {human}.")

        return " ".join(parts)

    # ----------------------------------------------------------
    # Critical theme handling — severity-differentiated bands
    # ----------------------------------------------------------
    def _apply_critical_themes(
        self,
        combined: float,
        themes: list[str],
        reason_codes: list[str],
        risk_factors: list[str],
    ) -> float:
        """
        Differentiated handling by severity:
        - Self-harm / suicidal → force CRITICAL band [86, 100]
        - Threats / violence   → force HIGH band    [70, 84]
        - Hopelessness         → force HIGH band    [61, 84]
        """
        if not themes:
            return combined

        theme_set = set(themes)

        for theme in themes:
            reason_codes.append(f"CRITICAL_THEME_{theme.upper()}")
            risk_factors.append(theme)

        # Priority 1: self-harm / suicidal (most severe)
        if theme_set & SELF_HARM_THEMES:
            lo, hi = SELF_HARM_BAND
            if combined < lo:
                reason_codes.append(f"SELF_HARM_FLOOR:+{int(lo)}")
                combined = lo
            elif combined > hi:
                combined = hi
            return combined

        # Priority 2: threats / violence (HIGH band)
        if theme_set & THREAT_THEMES:
            lo, hi = THREAT_BAND
            if combined < lo:
                reason_codes.append(f"THREAT_FLOOR:+{int(lo)}")
                combined = lo
            if combined > hi:
                reason_codes.append(f"THREAT_CAP:{int(hi)}")
                combined = hi
            return combined

        # Priority 3: hopelessness (pre-crisis → HIGH band)
        if theme_set & HOPELESS_THEMES:
            lo, hi = HOPELESSNESS_BAND
            if combined < lo:
                reason_codes.append(f"HOPELESSNESS_FLOOR:+{int(lo)}")
                combined = lo
            if combined > hi:
                reason_codes.append(f"HOPELESSNESS_CAP:{int(hi)}")
                combined = hi
            return combined

        return combined

    def compute(
        self,
        pulse: PulseInput,
        text_analysis: Optional[TextAnalysisResult] = None,
    ) -> DistressResult:
        """Full distress assessment for one pulse."""

        # 1. Rule baseline
        rule_score, reason_codes, risk_factors = self._compute_rule_score(pulse, text_analysis)

        # 2. Text adjustment
        text_adjustment, text_reasons = _compute_text_adjustment(text_analysis)
        reason_codes.extend(text_reasons)

        # 3. Combined score
        combined = rule_score + text_adjustment

        # 4. Critical theme handling (differentiated)
        if text_analysis and text_analysis.critical_themes:
            combined = self._apply_critical_themes(
                combined,
                text_analysis.critical_themes,
                reason_codes,
                risk_factors,
            )

        # 5. Clamp
        final_score = round(max(0.0, min(100.0, combined)), 1)

        # 6. Risk level
        risk_level = self._map_risk_level(final_score)

        # 7. Explanation
        explanation = self._build_explanation(
            final_score,
            risk_level,
            risk_factors,
            text_analysis.critical_themes if text_analysis else [],
        )

        return DistressResult(
            victim_id=pulse.victim_id,
            distress_score=final_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            reason_codes=reason_codes,
            explanation=explanation,
            rule_score=round(rule_score, 1),
            text_adjustment=round(text_adjustment, 2),
        )


# Singleton accessor
_scorer_instance: Optional[DistressScorer] = None


def get_distress_scorer() -> DistressScorer:
    """Return the global DistressScorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = DistressScorer()
    return _scorer_instance