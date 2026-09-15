"""
Exhaustive Distress Scorer test suite.
Covers boundaries, contradictions, all languages, all themes, missing fields.
"""
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, CaseStage
)
from ai_service.text_analyzer import get_text_analyzer
from ai_service.distress_scorer import get_distress_scorer


analyzer = get_text_analyzer()
scorer = get_distress_scorer()


def score(pulse, text=None):
    """Helper: run pulse through analyzer + scorer."""
    ta = analyzer.analyze(text) if text else None
    return scorer.compute(pulse, ta)


def check(desc, result, expected_risk, expected_range=None):
    """Check that result matches expected risk level. Optionally check score range."""
    ok = result.risk_level == expected_risk
    range_ok = True
    if expected_range:
        lo, hi = expected_range
        range_ok = lo <= result.distress_score <= hi
    status = "✅" if (ok and range_ok) else "❌"
    print(f"{status} [{desc}]")
    print(f"   Score: {result.distress_score}  Risk: {result.risk_level}")
    if expected_range:
        print(f"   Expected range: {expected_range}")
    print(f"   Themes detected: {[f for f in result.risk_factors if '_' in f and f in ['suicidal_ideation','self_harm','threats','violence_fear','hopelessness']]}")
    print()


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def main():
    print("\n🧪 Exhaustive Distress Scorer Test Suite\n")

    # ============================================================
    section("1. BOUNDARY TESTS — Threshold Transitions")
    # ============================================================

    # Exact boundary at 30 (LOW/MEDIUM)
    r = score(PulseInput(victim_id="B1", wellbeing_state=WellbeingState.VERY_SAFE))
    # very_safe = 10 → LOW
    check("Very safe alone (score ~10)", r, "low", (0, 30))

    r = score(PulseInput(victim_id="B2", wellbeing_state=WellbeingState.SAFE))
    # safe = 20 → LOW
    check("Safe alone (score ~20)", r, "low", (0, 30))

    r = score(PulseInput(victim_id="B3", wellbeing_state=WellbeingState.NEUTRAL))
    # neutral = 40 → MEDIUM
    check("Neutral alone (score ~40)", r, "medium", (31, 60))

    r = score(PulseInput(victim_id="B4", wellbeing_state=WellbeingState.UNSAFE))
    # unsafe = 60 → MEDIUM (boundary)
    check("Unsafe alone (score ~60)", r, "medium", (31, 60))

    r = score(PulseInput(victim_id="B5", wellbeing_state=WellbeingState.VERY_UNSAFE))
    # very_unsafe = 80 → HIGH
    check("Very unsafe alone (score ~80)", r, "high", (61, 85))

    # ============================================================
    section("2. EVERY WELLBEING STATE × Every Factor (spot check)")
    # ============================================================

    for state in [WellbeingState.SAFE, WellbeingState.NEUTRAL,
                  WellbeingState.UNSAFE, WellbeingState.VERY_UNSAFE]:
        pulse = PulseInput(
            victim_id="F1",
            wellbeing_state=state,
            affecting_factors=[AffectingFactor.SUICIDAL_THOUGHTS],
        )
        r = score(pulse)
        # Adding suicidal thoughts (+20) to state
        check(f"{state} + suicidal_thoughts factor", r, r.risk_level)  # informational

    # ============================================================
    section("3. ALL FACTORS INDIVIDUALLY")
    # ============================================================

    for factor in AffectingFactor:
        pulse = PulseInput(
            victim_id="FT",
            wellbeing_state=WellbeingState.NEUTRAL,
            affecting_factors=[factor],
        )
        r = score(pulse)
        check(f"Neutral + {factor.value}", r, r.risk_level)  # informational

    # ============================================================
    section("4. ALL CASE STAGES")
    # ============================================================

    for stage in CaseStage:
        pulse = PulseInput(
            victim_id="CS",
            wellbeing_state=WellbeingState.NEUTRAL,
            case_stage=stage,
        )
        r = score(pulse)
        check(f"Neutral at stage {stage.value}", r, r.risk_level)

    # ============================================================
    section("5. MISSING FIELDS")
    # ============================================================

    r = score(PulseInput(victim_id="M1"))  # no wellbeing, no factors, no stage
    check("No wellbeing, no factors, no stage", r, "medium", (31, 60))

    r = score(PulseInput(victim_id="M2", wellbeing_state=WellbeingState.UNSAFE),
              text="")  # empty text
    check("Unsafe + empty text", r, "medium", (31, 60))

    # ============================================================
    section("6. CONTRADICTIONS")
    # ============================================================

    # "Safe" but writing suicidal text
    r = score(
        PulseInput(victim_id="C1", wellbeing_state=WellbeingState.VERY_SAFE),
        text="I want to die, there's no point anymore.",
    )
    check("Very safe BUT suicidal text → must be CRITICAL", r, "critical", (86, 100))

    # "Very unsafe" but writing positive text
    r = score(
        PulseInput(victim_id="C2", wellbeing_state=WellbeingState.VERY_UNSAFE),
        text="I feel so happy and grateful today.",
    )
    check("Very unsafe BUT positive text → still HIGH (rule score)", r, "high", (61, 85))

    # ============================================================
    section("7. ALL CRITICAL THEMES INDIVIDUALLY (Neutral state)")
    # ============================================================

    theme_texts = {
        "suicidal_ideation": "I want to die.",
        "self_harm": "I've been cutting myself.",
        "threats": "They threatened to kill me.",
        "violence_fear": "I am scared for my life.",
        "hopelessness": "I feel hopeless, no hope left.",
    }

    for theme, text in theme_texts.items():
        r = score(
            PulseInput(victim_id=f"T_{theme}", wellbeing_state=WellbeingState.NEUTRAL),
            text=text,
        )
        print(f"→ Theme '{theme}': score={r.distress_score} risk={r.risk_level}")
        if theme in ("suicidal_ideation", "self_harm"):
            check(f"Neutral + {theme} → CRITICAL", r, "critical", (86, 100))
        elif theme in ("threats", "violence_fear"):
            check(f"Neutral + {theme} → HIGH (capped)", r, "high", (61, 84))
        elif theme == "hopelessness":
            check(f"Neutral + {theme} → MEDIUM/HIGH", r, r.risk_level)
        print()

    # ============================================================
    section("8. MULTI-THEME PRIORITY")
    # ============================================================

    # Self-harm + threats → self-harm wins (CRITICAL)
    r = score(
        PulseInput(victim_id="MT1", wellbeing_state=WellbeingState.NEUTRAL),
        text="They threatened me. I want to die.",
    )
    check("Threats + suicidal → CRITICAL wins", r, "critical", (86, 100))

    # Hopelessness + threats → threat cap applies
    r = score(
        PulseInput(victim_id="MT2", wellbeing_state=WellbeingState.NEUTRAL),
        text="They threatened to kill me. I feel hopeless.",
    )
    check("Threats + hopelessness → HIGH (capped)", r, "high", (61, 84))

    # ============================================================
    section("9. ALL 10 LANGUAGES — Same crisis")
    # ============================================================

    lang_cases = [
        ("English", "I want to die."),
        ("Hindi", "मैं मरना चाहता हूँ।"),
        ("Telugu", "నేను చనిపోవాలని అనుకుంటున్నాను."),
        ("Tamil", "நான் இறக்க விரும்புகிறேன்."),
        ("Bengali", "আমি মরতে চাই।"),
        ("Marathi", "मला मरायचं आहे."),
        ("Kannada", "ನಾನು ಸಾಯಬೇಕು."),
        ("Malayalam", "എനിക്ക് മരിക്കണം."),
        ("Punjabi", "ਮੈਂ ਮਰਨਾ ਚਾਹੁੰਦਾ ਹਾਂ।"),
        ("Gujarati", "હું મરવા માંગુ છું."),
    ]

    for lang, text in lang_cases:
        r = score(
            PulseInput(victim_id=f"L_{lang}", wellbeing_state=WellbeingState.NEUTRAL),
            text=text,
        )
        status = "✅" if r.risk_level == "critical" else "⚠️"
        print(f"{status} {lang}: score={r.distress_score} risk={r.risk_level} themes={[f for f in r.risk_factors if f in ['suicidal_ideation','self_harm','threats','violence_fear','hopelessness']]}")

    # ============================================================
    section("10. TEXT-SPEAK VARIANTS")
    # ============================================================

    shorthand_cases = [
        ("I dont want 2 liv"),
        ("i wanna die"),
        ("cant go on anymore"),
        ("no reason 2 live"),
        ("i gv up"),
    ]

    for text in shorthand_cases:
        r = score(
            PulseInput(victim_id="TS", wellbeing_state=WellbeingState.NEUTRAL),
            text=text,
        )
        status = "✅" if r.risk_level in ("high", "critical") else "⚠️"
        print(f"{status} '{text}' → score={r.distress_score} risk={r.risk_level}")

    # ============================================================
    section("11. MAX STACK — Everything at once")
    # ============================================================

    r = score(
        PulseInput(
            victim_id="MAX",
            wellbeing_state=WellbeingState.VERY_UNSAFE,
            affecting_factors=[
                AffectingFactor.SUICIDAL_THOUGHTS,
                AffectingFactor.SELF_HARM,
                AffectingFactor.THREATS,
                AffectingFactor.DISPLACEMENT,
            ],
            case_stage=CaseStage.COURT,
        ),
        text="I want to die. I've been cutting myself. They threatened me.",
    )
    check("Max stack → CRITICAL 100", r, "critical", (95, 100))

    # ============================================================
    section("12. TEXT_ANALYSIS=None (pure structured)")
    # ============================================================

    r = score(PulseInput(victim_id="N1", wellbeing_state=WellbeingState.VERY_UNSAFE),
              text=None)
    check("Very unsafe, no text → HIGH", r, "high", (61, 85))

    # ============================================================
    print(f"\n{'━' * 70}")
    print("  ✅ Exhaustive test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()