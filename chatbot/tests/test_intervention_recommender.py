"""Exhaustive tests for the Intervention Recommender."""
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, CaseStage
)
from schemas.distress import DistressResult, RiskLevel
from schemas.escalation import EscalationResult, TrendDirection
from schemas.text_analysis import TextAnalysisResult
from schemas.intervention import (
    InterventionType, InterventionPriority,
)
from ai_service.intervention_recommender import get_intervention_recommender


recommender = get_intervention_recommender()


# ============================================================
# Helpers
# ============================================================

def make_pulse(victim_id="V001", wellbeing="neutral",
               factors=None, stage=None):
    return PulseInput(
        victim_id=victim_id,
        wellbeing_state=WellbeingState(wellbeing),
        affecting_factors=[AffectingFactor(f) for f in (factors or [])],
        case_stage=CaseStage(stage) if stage else None,
    )


def make_distress(victim_id="V001", score=50, risk="medium"):
    return DistressResult(
        victim_id=victim_id,
        distress_score=score,
        risk_level=RiskLevel(risk),
        risk_factors=[],
        reason_codes=[],
        explanation="test",
        rule_score=score,
        text_adjustment=0.0,
    )


def make_text_analysis(themes=None):
    if not themes:
        return None
    return TextAnalysisResult(
        text="test",
        detected_language="en",
        sentiment_label="negative",
        sentiment_score=0.9,
        emotion_label="fear",
        emotion_score=0.9,
        emotion_distribution={},
        critical_themes=themes,
        distress_intensity="high",
    )


def make_escalation(victim_id="V001", flag=True, trend="worsening"):
    return EscalationResult(
        victim_id=victim_id,
        escalation_flag=flag,
        trend_direction=TrendDirection(trend),
        window_size=3,
        recent_scores=[50.0, 60.0, 70.0],
        avg_delta=10.0,
        escalation_reasons=["monotonic_increase"],
        explanation="test",
    )


def show(result):
    print(f"   Interventions: {[i.value for i in result.recommended_interventions]}")
    print(f"   Priority:      {result.priority.value}")
    print(f"   Triggers:      {result.trigger_codes}")
    print(f"   Reasoning:     {result.reasoning}")
    print()


def check(desc, result, must_include=None, must_not_include=None,
          priority=None):
    """Verify result has expected interventions + priority."""
    got = {i.value for i in result.recommended_interventions}
    ok = True

    if must_include:
        missing = set(must_include) - got
        if missing:
            ok = False

    if must_not_include:
        unexpected = set(must_not_include) & got
        if unexpected:
            ok = False

    if priority and result.priority.value != priority:
        ok = False

    status = "✅" if ok else "❌"
    print(f"{status} [{desc}]")
    show(result)


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def main():
    print("\n🧪 Intervention Recommender — Test Suite\n")

    # ============================================================
    section("1. LOW RISK — BASELINE")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="safe"),
        make_distress(score=15, risk="low"),
    )
    check("Low risk, no signals → baseline counselling only",
          r, priority="low")

    # ============================================================
    section("2. MEDIUM RISK")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="neutral"),
        make_distress(score=50, risk="medium"),
    )
    check("Medium risk → baseline support, medium priority",
          r, priority="medium")

    # ============================================================
    section("3. HIGH RISK — counselling required")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="unsafe"),
        make_distress(score=75, risk="high"),
    )
    check("High risk → counselling, high priority",
          r, must_include=["counselling"], priority="high")

    # ============================================================
    section("4. CRITICAL RISK")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="very_unsafe"),
        make_distress(score=95, risk="critical"),
    )
    check("Critical risk → counselling, critical priority",
          r, must_include=["counselling"], priority="critical")

    # ============================================================
    section("5. SELF-HARM / SUICIDAL → counselling + medical")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="neutral"),
        make_distress(score=86, risk="critical"),
        text_analysis=make_text_analysis(["suicidal_ideation"]),
    )
    check("Suicidal ideation → counselling + medical",
          r,
          must_include=["counselling", "medical"],
          priority="critical")

    r = recommender.recommend(
        make_pulse(wellbeing="neutral"),
        make_distress(score=86, risk="critical"),
        text_analysis=make_text_analysis(["self_harm"]),
    )
    check("Self-harm → counselling + medical",
          r,
          must_include=["counselling", "medical"],
          priority="critical")

    # ============================================================
    section("6. THREATS → witness protection")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="unsafe", factors=["threats"]),
        make_distress(score=75, risk="high"),
        text_analysis=make_text_analysis(["threats"]),
    )
    check("Threats detected → witness protection",
          r,
          must_include=["counselling", "witness_protection"],
          priority="high")

    r = recommender.recommend(
        make_pulse(wellbeing="neutral"),
        make_distress(score=70, risk="high"),
        text_analysis=make_text_analysis(["violence_fear"]),
    )
    check("Violence fear → witness protection",
          r, must_include=["witness_protection"])

    # ============================================================
    section("7. DISPLACEMENT → relocation")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="unsafe", factors=["displacement"]),
        make_distress(score=65, risk="high"),
    )
    check("Displacement → relocation",
          r, must_include=["relocation"])

    # ============================================================
    section("8. FINANCIAL STRESS → financial assistance")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="neutral", factors=["financial_stress"]),
        make_distress(score=50, risk="medium"),
    )
    check("Financial stress → financial assistance",
          r, must_include=["financial_assistance"])

    # ============================================================
    section("9. LEGAL STRESS / COURT → legal aid")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="neutral", factors=["legal_stress"]),
        make_distress(score=50, risk="medium"),
    )
    check("Legal stress → legal aid",
          r, must_include=["legal_aid"])

    r = recommender.recommend(
        make_pulse(wellbeing="neutral", stage="court"),
        make_distress(score=50, risk="medium"),
    )
    check("Court stage → legal aid",
          r, must_include=["legal_aid"])

    r = recommender.recommend(
        make_pulse(wellbeing="neutral", stage="investigation"),
        make_distress(score=45, risk="medium"),
    )
    check("Investigation stage → legal aid",
          r, must_include=["legal_aid"])

    # ============================================================
    section("10. HEALTH ISSUES → medical")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="neutral", factors=["health_issues"]),
        make_distress(score=45, risk="medium"),
    )
    check("Health issues → medical",
          r, must_include=["medical"])

    # ============================================================
    section("11. REHABILITATION STAGE → rehabilitation")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="safe", stage="rehabilitation"),
        make_distress(score=20, risk="low"),
    )
    check("Rehabilitation stage → rehabilitation",
          r, must_include=["rehabilitation"], priority="low")

    # ============================================================
    section("12. ESCALATION BOOST")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="unsafe"),
        make_distress(score=75, risk="high"),
        escalation=make_escalation(flag=True),
    )
    check("High risk + escalating → counselling + witness protection",
          r,
          must_include=["counselling", "witness_protection"],
          priority="high")

    r = recommender.recommend(
        make_pulse(wellbeing="neutral"),
        make_distress(score=45, risk="medium"),
        escalation=make_escalation(flag=False, trend="stable"),
    )
    check("Medium risk, not escalating → baseline only",
          r, priority="medium")

    # ============================================================
    section("13. MULTIPLE SIGNALS STACK")
    # ============================================================

    r = recommender.recommend(
        make_pulse(
            wellbeing="very_unsafe",
            factors=["threats", "financial_stress", "legal_stress"],
            stage="court",
        ),
        make_distress(score=95, risk="critical"),
        escalation=make_escalation(flag=True),
        text_analysis=make_text_analysis(["threats", "violence_fear"]),
    )
    check("Critical multi-signal → all relevant interventions",
          r,
          must_include=[
              "counselling",
              "witness_protection",
              "financial_assistance",
              "legal_aid",
          ],
          priority="critical")

    # ============================================================
    section("14. SUICIDAL + THREATS → highest urgency")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="very_unsafe", factors=["threats"]),
        make_distress(score=100, risk="critical"),
        escalation=make_escalation(flag=True),
        text_analysis=make_text_analysis(["suicidal_ideation", "threats"]),
    )
    check("Suicidal + threats → counselling, medical, protection",
          r,
          must_include=["counselling", "medical", "witness_protection"],
          priority="critical")

    # ============================================================
    section("15. FALLBACK (no signals, low risk)")
    # ============================================================

    r = recommender.recommend(
        make_pulse(wellbeing="very_safe"),
        make_distress(score=10, risk="low"),
    )
    check("No signals at all → baseline counselling",
          r, must_include=["counselling"], priority="low")

    # ============================================================
    section("16. IDEMPOTENCE (same input → same output)")
    # ============================================================

    pulse = make_pulse(wellbeing="unsafe", factors=["threats"])
    distress = make_distress(score=75, risk="high")
    ta = make_text_analysis(["threats"])

    r1 = recommender.recommend(pulse, distress, text_analysis=ta)
    r2 = recommender.recommend(pulse, distress, text_analysis=ta)

    ok = (
        {i.value for i in r1.recommended_interventions}
        == {i.value for i in r2.recommended_interventions}
        and r1.priority == r2.priority
    )
    status = "✅" if ok else "❌"
    print(f"{status} [Idempotence: same input → same output]")
    print(f"   Run 1: {[i.value for i in r1.recommended_interventions]} ({r1.priority.value})")
    print(f"   Run 2: {[i.value for i in r2.recommended_interventions]} ({r2.priority.value})")
    print()

    print(f"\n{'━' * 70}")
    print("  ✅ Intervention Recommender test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()
    