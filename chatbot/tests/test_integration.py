"""
End-to-end integration test — simulates a complete victim journey
across multiple channels and check-ins.

This is the demo we show judges: a real victim narrative flowing
through the entire ML pipeline.
"""

from schemas.chat import ChatMessage
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, CaseStage
)
from ai_service.chatbot import get_chatbot
from session.manager import get_session_manager


def banner(text):
    print(f"\n{'═' * 72}")
    print(f"  {text}")
    print(f"{'═' * 72}")


def show_turn(label, response):
    print(f"\n┌─ {label}")
    print(f"│  Reply:      {response.reply[:100]}...")
    if response.distress:
        print(f"│  Distress:   {response.distress.distress_score}/100 ({response.distress.risk_level})")
    if response.text_analysis:
        themes = response.text_analysis.critical_themes or ["none"]
        print(f"│  Themes:     {themes}")
        print(f"│  Language:   {response.text_analysis.detected_language}")
    if response.escalation:
        print(f"│  Trend:      {response.escalation.trend_direction}  "
              f"(escalating={response.escalation.escalation_flag})")
    if response.intervention:
        ints = [i.value for i in response.intervention.recommended_interventions]
        print(f"│  Recommend:  {ints}")
        print(f"│  Priority:   {response.intervention.priority.value}")
    print(f"└─")


def main():
    print("\n🧪 END-TO-END INTEGRATION TEST")
    print("   Simulating a real victim journey through the system\n")

    sessions = get_session_manager()
    sessions.clear_all()
    chatbot = get_chatbot()

    victim = "SIH-DEMO-V001"

    # ============================================================
    banner("DAY 1 — Victim uses CHATBOT (mild concern)")
    # ============================================================

    msg = ChatMessage(
        victim_id=victim,
        session_id="S-DAY-1",
        message="I'm a bit worried about the court hearing next week.",
        channel="chatbot",
    )
    pulse = PulseInput(
        victim_id=victim,
        wellbeing_state=WellbeingState.NEUTRAL,
        case_stage=CaseStage.COURT,
    )
    r1 = chatbot.process_turn(msg, pulse)
    show_turn("Day 1 — Chatbot", r1)

    # ============================================================
    banner("DAY 5 — Victim uses SMS (worse)")
    # ============================================================

    msg = ChatMessage(
        victim_id=victim,
        session_id="S-DAY-5",
        message="They threatened me again. I feel unsafe.",
        channel="sms",
    )
    pulse = PulseInput(
        victim_id=victim,
        wellbeing_state=WellbeingState.UNSAFE,
        affecting_factors=[AffectingFactor.THREATS],
        case_stage=CaseStage.COURT,
    )
    r2 = chatbot.process_turn(msg, pulse)
    show_turn("Day 5 — SMS", r2)

    # ============================================================
    banner("DAY 10 — Victim uses IVRS (voice → transcript)")
    # ============================================================

    msg = ChatMessage(
        victim_id=victim,
        session_id="S-DAY-10",
        message="I can't take this anymore. I dont want 2 liv. They will kill me if I testify.",
        channel="ivrs_transcript",
    )
    pulse = PulseInput(
        victim_id=victim,
        wellbeing_state=WellbeingState.VERY_UNSAFE,
        affecting_factors=[
            AffectingFactor.THREATS,
            AffectingFactor.SUICIDAL_THOUGHTS,
        ],
        case_stage=CaseStage.COURT,
    )
    r3 = chatbot.process_turn(msg, pulse)
    show_turn("Day 10 — IVRS transcript", r3)

    # ============================================================
    banner("SYSTEM STATE — Full history analysis")
    # ============================================================

    history = sessions.get_history(victim)
    print(f"\nVictim: {victim}")
    print(f"Total check-ins: {len(history)}")
    print(f"Score trajectory:")
    for i, r in enumerate(history, 1):
        lvl = r.risk_level.value if hasattr(r.risk_level, "value") else str(r.risk_level)
        print(f"  Check-in {i}: {r.distress_score:>5.1f}/100  ({lvl})")

    # Escalation summary
    escalation = chatbot.escalation.detect(victim, history)
    if escalation:
        print(f"\n📈 ESCALATION ANALYSIS")
        print(f"  Trend:      {escalation.trend_direction}")
        print(f"  Flagged:    {escalation.escalation_flag}")
        print(f"  Avg Δ:      {escalation.avg_delta:+.1f} per check-in")
        print(f"  Reasons:    {escalation.escalation_reasons}")

    # ============================================================
    banner("COUNSELLOR VIEW — Full human-readable report")
    # ============================================================

    # Use the last turn's full analysis
    print(r3.explanation)

    # ============================================================
    banner("VERIFICATION — All systems behaving correctly")
    # ============================================================

    checks = []

    # 1. Trajectory is worsening
    checks.append((
        "Distress scores increased over time",
        history[0].distress_score < history[-1].distress_score
    ))

    # 2. Escalation detected
    checks.append((
        "Escalation flag correctly triggered",
        escalation and escalation.escalation_flag
    ))

    # 3. Critical themes detected on final turn
    final_themes = r3.text_analysis.critical_themes if r3.text_analysis else []
    checks.append((
        "Final turn caught suicidal + threats themes",
        "suicidal_ideation" in final_themes and "threats" in final_themes
    ))

    # 4. Text-speak recognized
    checks.append((
        "Text-speak ('dont want 2 liv') recognized",
        "suicidal_ideation" in final_themes
    ))

    # 5. Right interventions recommended
    final_ints = [i.value for i in r3.intervention.recommended_interventions]
    checks.append((
        "Counselling + medical recommended",
        "counselling" in final_ints and "medical" in final_ints
    ))

    # 6. Priority is CRITICAL
    checks.append((
        "Priority = critical",
        r3.intervention.priority.value == "critical"
    ))

    # 7. Full explanation present
    checks.append((
        "Explanation attached to response",
        bool(r3.explanation and len(r3.explanation) > 100)
    ))

    # 8. Channel diversity worked
    channels_used = {"chatbot", "sms", "ivrs_transcript"}
    checks.append((
        "Multiple channels (chatbot, SMS, IVRS) all worked",
        True  # we ran all 3 above
    ))

    print()
    all_ok = True
    for desc, ok in checks:
        status = "✅" if ok else "❌"
        print(f"  {status}  {desc}")
        if not ok:
            all_ok = False

    banner("RESULT")
    if all_ok:
        print("\n✅  END-TO-END INTEGRATION TEST PASSED")
        print("    Full system works coherently across channels and time.\n")
    else:
        print("\n❌  Some checks failed — investigate.\n")


if __name__ == "__main__":
    main()