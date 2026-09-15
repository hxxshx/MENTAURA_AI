"""
Intervention Recommender — Module 3
Rule-based expert system that maps distress signals → recommended interventions.

Fully explainable: every recommendation has a trigger code.
"""

from typing import Optional

from schemas.pulse import PulseInput
from schemas.distress import DistressResult
from schemas.escalation import EscalationResult
from schemas.text_analysis import TextAnalysisResult
from schemas.intervention import (
    InterventionResult,
    InterventionType,
    InterventionPriority,
)


class InterventionRecommender:
    """Stateless rule-based recommender."""

    # ----------------------------------------------------------
    # Core rule engine
    # ----------------------------------------------------------
    def _apply_rules(
        self,
        pulse: PulseInput,
        distress: DistressResult,
        escalation: Optional[EscalationResult],
        text_analysis: Optional[TextAnalysisResult],
    ) -> tuple[set[str], list[str]]:
        """Returns (intervention_set, trigger_codes)."""
        interventions: set[str] = set()
        triggers: list[str] = []

        risk = _level_str(distress.risk_level)
        themes = set(text_analysis.critical_themes) if text_analysis else set()
        factors = set(pulse.affecting_factors or [])
        stage = _level_str(pulse.case_stage) if pulse.case_stage else None

        # ---------------- RULE 1: High/Critical distress → counselling -------
        if risk in ("high", "critical"):
            interventions.add(InterventionType.COUNSELLING.value)
            triggers.append(f"HIGH_RISK_{risk.upper()}")

        # ---------------- RULE 2: Self-harm / suicidal → medical + counselling
        if themes & {"suicidal_ideation", "self_harm"}:
            interventions.add(InterventionType.COUNSELLING.value)
            interventions.add(InterventionType.MEDICAL.value)
            triggers.append("SELF_HARM_RISK")

        # ---------------- RULE 3: Threats / violence → protection ----------
        if themes & {"threats", "violence_fear"}:
            interventions.add(InterventionType.WITNESS_PROTECTION.value)
            triggers.append("THREAT_DETECTED")

        # ---------------- RULE 4: Displacement / unsafe home → relocation --
        if "displacement" in factors:
            interventions.add(InterventionType.RELOCATION.value)
            triggers.append("DISPLACEMENT_FLAGGED")

        # ---------------- RULE 5: Financial stress → financial assistance --
        if "financial_stress" in factors:
            interventions.add(InterventionType.FINANCIAL_ASSISTANCE.value)
            triggers.append("FINANCIAL_STRESS_FLAGGED")

        # ---------------- RULE 6: Legal stress OR court stage → legal aid --
        if "legal_stress" in factors or stage in ("investigation", "court"):
            interventions.add(InterventionType.LEGAL_AID.value)
            triggers.append("LEGAL_SUPPORT_NEEDED")

        # ---------------- RULE 7: Health issues → medical ------------------
        if "health_issues" in factors:
            interventions.add(InterventionType.MEDICAL.value)
            triggers.append("HEALTH_ISSUES_FLAGGED")

        # ---------------- RULE 8: Rehabilitation stage → rehabilitation ---
        if stage == "rehabilitation":
            interventions.add(InterventionType.REHABILITATION.value)
            triggers.append("REHABILITATION_STAGE")

        # ---------------- RULE 9: Escalation → add counselling + protection
        if escalation and escalation.escalation_flag:
            interventions.add(InterventionType.COUNSELLING.value)
            interventions.add(InterventionType.WITNESS_PROTECTION.value)
            triggers.append("ESCALATION_FLAGGED")

        # ---------------- RULE 10: Fallback (if nothing matched) ----------
        if not interventions:
            interventions.add(InterventionType.COUNSELLING.value)
            triggers.append("BASELINE_SUPPORT")

        return interventions, triggers

    # ----------------------------------------------------------
    # Priority logic
    # ----------------------------------------------------------
    def _compute_priority(
        self,
        distress: DistressResult,
        escalation: Optional[EscalationResult],
    ) -> InterventionPriority:
        risk = _level_str(distress.risk_level)
        escalating = escalation and escalation.escalation_flag

        if risk == "critical":
            return InterventionPriority.CRITICAL
        if risk == "high" and escalating:
            return InterventionPriority.HIGH
        if risk == "high":
            return InterventionPriority.HIGH
        if risk == "medium":
            return InterventionPriority.MEDIUM
        return InterventionPriority.LOW

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def recommend(
        self,
        pulse: PulseInput,
        distress: DistressResult,
        escalation: Optional[EscalationResult] = None,
        text_analysis: Optional[TextAnalysisResult] = None,
    ) -> InterventionResult:
        """Full intervention recommendation."""

        interventions, triggers = self._apply_rules(
            pulse, distress, escalation, text_analysis
        )
        priority = self._compute_priority(distress, escalation)

        reasoning = _build_reasoning(
            distress, escalation, text_analysis, interventions, triggers
        )

        return InterventionResult(
            victim_id=pulse.victim_id,
            recommended_interventions=[
                InterventionType(i) for i in sorted(interventions)
            ],
            priority=priority,
            reasoning=reasoning,
            trigger_codes=triggers,
        )


# ============================================================
# Helpers
# ============================================================

def _level_str(level) -> str:
    """Normalize enum or str → lowercase string."""
    if level is None:
        return ""
    if hasattr(level, "value"):
        return level.value
    s = str(level).lower()
    if "." in s:
        s = s.split(".")[-1]
    return s


def _build_reasoning(
    distress: DistressResult,
    escalation: Optional[EscalationResult],
    text_analysis: Optional[TextAnalysisResult],
    interventions: set[str],
    triggers: list[str],
) -> str:
    parts = [
        f"Risk level {_level_str(distress.risk_level)} "
        f"(score {distress.distress_score:.0f}/100)."
    ]

    if escalation and escalation.escalation_flag:
        parts.append(
            f"Distress is escalating ({escalation.trend_direction.value})."
        )

    if text_analysis and text_analysis.critical_themes:
        human = ", ".join(t.replace("_", " ") for t in text_analysis.critical_themes)
        parts.append(f"Critical signals: {human}.")

    parts.append(f"Recommended: {', '.join(sorted(interventions))}.")

    return " ".join(parts)


# Singleton accessor
_recommender_instance: Optional[InterventionRecommender] = None


def get_intervention_recommender() -> InterventionRecommender:
    """Return the global InterventionRecommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = InterventionRecommender()
    return _recommender_instance