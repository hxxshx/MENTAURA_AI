"""Verify the Distress Scorer produces correct scores and explanations."""
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, CaseStage
)
from ai_service.text_analyzer import get_text_analyzer
from ai_service.distress_scorer import get_distress_scorer


def run_case(desc, pulse, text=None):
    print(f"\n{'─' * 60}")
    print(f"CASE: {desc}")
    print(f"{'─' * 60}")

    analyzer = get_text_analyzer()
    scorer = get_distress_scorer()

    ta = analyzer.analyze(text) if text else None
    if ta:
        print(f"Text: \"{text}\"")
        print(f"  → sentiment={ta.sentiment_label} emotion={ta.emotion_label}")
        print(f"  → themes={ta.critical_themes}")

    result = scorer.compute(pulse, ta)
    print(f"\nScore:       {result.distress_score}/100")
    print(f"Risk Level:  {result.risk_level}")
    print(f"Rule base:   {result.rule_score}")
    print(f"Text adj:    {result.text_adjustment:+}")
    print(f"Factors:     {result.risk_factors}")
    print(f"Explanation: {result.explanation}")
    print(f"Reason Codes:")
    for rc in result.reason_codes:
        print(f"   • {rc}")


def main():
    print("🧪 Testing Distress Scorer")

    # Case 1: Safe, happy
    run_case(
        "Safe and positive",
        PulseInput(
            victim_id="V001",
            wellbeing_state=WellbeingState.SAFE,
            case_stage=CaseStage.INVESTIGATION,
        ),
        text="I feel safe and supported today.",
    )

    # Case 2: Unsafe + threats during court
    run_case(
        "Unsafe + threats during court",
        PulseInput(
            victim_id="V002",
            wellbeing_state=WellbeingState.UNSAFE,
            affecting_factors=[AffectingFactor.THREATS],
            case_stage=CaseStage.COURT,
        ),
        text="They threatened me again before the hearing.",
    )

    # Case 3: CRITICAL — suicidal
    run_case(
        "Very unsafe + suicidal thoughts",
        PulseInput(
            victim_id="V003",
            wellbeing_state=WellbeingState.VERY_UNSAFE,
            affecting_factors=[
                AffectingFactor.SUICIDAL_THOUGHTS,
                AffectingFactor.THREATS,
            ],
            case_stage=CaseStage.COURT,
        ),
        text="I want to die, there's no point anymore.",
    )

    # Case 4: SILENT CRISIS — neutral selected, but text screams
    run_case(
        "Silent crisis — neutral state, critical text",
        PulseInput(
            victim_id="V004",
            wellbeing_state=WellbeingState.NEUTRAL,
        ),
        text="I've been cutting myself again, can't go on.",
    )

    # Case 5: Hindi silent crisis
    run_case(
        "Hindi — silent crisis",
        PulseInput(
            victim_id="V005",
            wellbeing_state=WellbeingState.NEUTRAL,
        ),
        text="मैं मरना चाहता हूँ।",
    )

    # Case 6: Text-speak silent crisis
    run_case(
        "Text-speak silent crisis",
        PulseInput(
            victim_id="V006",
            wellbeing_state=WellbeingState.NEUTRAL,
        ),
        text="I dont want 2 liv anymore",
    )

    print(f"\n{'━' * 60}")
    print("✅ Distress Scorer tests complete")


if __name__ == "__main__":
    main()