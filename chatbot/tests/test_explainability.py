"""Tests for the Explainability Layer."""
from schemas.distress import DistressResult, RiskLevel
from schemas.escalation import EscalationResult, TrendDirection
from schemas.intervention import (
    InterventionResult, InterventionType, InterventionPriority
)
from ai_service.explainability import (
    explain_distress,
    explain_escalation,
    explain_intervention,
    explain_full_turn,
)


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def main():
    print("\n🧪 Explainability Layer — Test Suite\n")

    # ============================================================
    section("1. DISTRESS EXPLANATION")
    # ============================================================

    d = DistressResult(
        victim_id="V001",
        distress_score=86.0,
        risk_level=RiskLevel.CRITICAL,
        risk_factors=["neutral_state", "suicidal_ideation", "self_harm"],
        reason_codes=[
            "WELLBEING_NEUTRAL:+40",
            "TEXT_NEGATIVE_SENTIMENT:+7.2",
            "TEXT_SADNESS:+3.8",
            "CRITICAL_THEME_SUICIDAL_IDEATION",
            "CRITICAL_THEME_SELF_HARM",
            "SELF_HARM_FLOOR:+86",
        ],
        explanation="test",
        rule_score=40.0,
        text_adjustment=11.0,
    )

    print(explain_distress(d))

    # ============================================================
    section("2. ESCALATION EXPLANATION")
    # ============================================================

    e = EscalationResult(
        victim_id="V001",
        escalation_flag=True,
        trend_direction=TrendDirection.WORSENING,
        window_size=3,
        recent_scores=[40.0, 60.0, 86.0],
        avg_delta=23.0,
        escalation_reasons=[
            "monotonic_increase",
            "risk_jump_medium_to_critical",
            "crossed_into_critical",
        ],
        explanation="test",
    )

    print(explain_escalation(e))

    # ============================================================
    section("3. INTERVENTION EXPLANATION")
    # ============================================================

    i = InterventionResult(
        victim_id="V001",
        recommended_interventions=[
            InterventionType.COUNSELLING,
            InterventionType.MEDICAL,
            InterventionType.WITNESS_PROTECTION,
        ],
        priority=InterventionPriority.CRITICAL,
        reasoning="Critical risk with self-harm and threats.",
        trigger_codes=["HIGH_RISK_CRITICAL", "SELF_HARM_RISK", "THREAT_DETECTED"],
    )

    print(explain_intervention(i))

    # ============================================================
    section("4. FULL TURN REPORT")
    # ============================================================

    print(explain_full_turn(d, e, i))

    # ============================================================
    section("5. EMPTY / FALLBACK CASES")
    # ============================================================

    d2 = DistressResult(
        victim_id="V002",
        distress_score=15.0,
        risk_level=RiskLevel.LOW,
        risk_factors=[],
        reason_codes=["WELLBEING_SAFE:+20", "TEXT_POSITIVE_SENTIMENT:-4.6"],
        explanation="test",
        rule_score=20.0,
        text_adjustment=-4.6,
    )
    print("Low-risk distress:")
    print(explain_distress(d2))

    print()
    print("Distress with no reason codes (fallback):")
    d3 = DistressResult(
        victim_id="V003",
        distress_score=40.0,
        risk_level=RiskLevel.MEDIUM,
        risk_factors=[],
        reason_codes=[],
        explanation="test",
        rule_score=40.0,
        text_adjustment=0.0,
    )
    print(explain_distress(d3))

    print(f"\n{'━' * 70}")
    print("  ✅ Explainability test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()