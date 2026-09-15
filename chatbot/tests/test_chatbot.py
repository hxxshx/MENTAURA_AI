"""Tests for the Chatbot Orchestrator — full pipeline."""
from schemas.chat import ChatMessage
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, CaseStage
)
from ai_service.chatbot import get_chatbot
from session.manager import get_session_manager


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def run(message, pulse=None, show_explanation=False):
    chatbot = get_chatbot()
    response = chatbot.process_turn(message, pulse)

    print(f"Victim: {message.victim_id}")
    print(f"Message: \"{message.message}\"")
    if pulse and pulse.wellbeing_state:
        print(f"State: {pulse.wellbeing_state}, Factors: {pulse.affecting_factors or []}")
    print()
    print(f"🤖 Reply: {response.reply}")
    print()
    if response.distress:
        print(f"📊 Distress: {response.distress.distress_score}/100 ({response.distress.risk_level})")
    if response.text_analysis:
        print(f"🧠 Themes: {response.text_analysis.critical_themes}")
    if response.escalation:
        print(f"📈 Trend: {response.escalation.trend_direction}, escalating={response.escalation.escalation_flag}")
    if response.intervention:
        ints = [i.value for i in response.intervention.recommended_interventions]
        print(f"💊 Recommended: {ints} (priority={response.intervention.priority.value})")
    print(f"Turn: {response.turn_number}")
    print()

    if show_explanation and response.explanation:
        print(response.explanation)

    return response


def main():
    print("\n🧪 Chatbot Orchestrator — Test Suite\n")
    sessions = get_session_manager()
    sessions.clear_all()

    # ============================================================
    section("1. SAFE MESSAGE")
    # ============================================================
    run(
        ChatMessage(
            victim_id="V001",
            session_id="S001",
            message="I feel safe and supported today.",
        ),
        pulse=PulseInput(
            victim_id="V001",
            wellbeing_state=WellbeingState.SAFE,
        ),
    )

    # ============================================================
    section("2. UNSAFE + THREATS")
    # ============================================================
    run(
        ChatMessage(
            victim_id="V002",
            session_id="S002",
            message="They threatened me again before the hearing.",
        ),
        pulse=PulseInput(
            victim_id="V002",
            wellbeing_state=WellbeingState.UNSAFE,
            affecting_factors=[AffectingFactor.THREATS],
            case_stage=CaseStage.COURT,
        ),
    )

    # ============================================================
    section("3. CRITICAL — SUICIDAL (with full explanation)")
    # ============================================================
    sessions.clear("V003")
    run(
        ChatMessage(
            victim_id="V003",
            session_id="S003",
            message="I want to die, there's no point anymore.",
        ),
        pulse=PulseInput(
            victim_id="V003",
            wellbeing_state=WellbeingState.VERY_UNSAFE,
            affecting_factors=[
                AffectingFactor.SUICIDAL_THOUGHTS,
                AffectingFactor.THREATS,
            ],
        ),
        show_explanation=True,
    )

    # ============================================================
    section("4. HINDI SUICIDAL")
    # ============================================================
    sessions.clear("V004")
    run(
        ChatMessage(
            victim_id="V004",
            session_id="S004",
            message="मैं मरना चाहता हूँ।",
        ),
    )

    # ============================================================
    section("5. TEXT-SPEAK SUICIDAL")
    # ============================================================
    sessions.clear("V005")
    run(
        ChatMessage(
            victim_id="V005",
            session_id="S005",
            message="I dont want 2 liv anymore",
        ),
    )

    # ============================================================
    section("6. MULTI-TURN ESCALATION (same victim, 3 turns)")
    # ============================================================
    sessions.clear("V006")
    chatbot = get_chatbot()

    turns = [
        (WellbeingState.NEUTRAL, "I'm okay I guess."),
        (WellbeingState.UNSAFE, "Things have been getting harder."),
        (WellbeingState.VERY_UNSAFE, "They threatened me and I don't know what to do."),
    ]

    for i, (state, text) in enumerate(turns, 1):
        msg = ChatMessage(
            victim_id="V006",
            session_id="S006",
            message=text,
        )
        pulse = PulseInput(victim_id="V006", wellbeing_state=state)
        response = chatbot.process_turn(msg, pulse)

        print(f"─── Turn {i} ───")
        print(f"  Message:  \"{text}\"")
        print(f"  Score:    {response.distress.distress_score}/100 ({response.distress.risk_level})")
        if response.escalation:
            print(f"  Trend:    {response.escalation.trend_direction}")
            print(f"  Escalate: {response.escalation.escalation_flag}")
        print()

    # ============================================================
    section("7. SESSION ISOLATION (different victims don't mix)")
    # ============================================================
    sessions.clear_all()

    chatbot.process_turn(
        ChatMessage(victim_id="VA", session_id="SA", message="I'm scared."),
    )
    chatbot.process_turn(
        ChatMessage(victim_id="VB", session_id="SB", message="I feel fine."),
    )

    hist_a = sessions.get_history("VA")
    hist_b = sessions.get_history("VB")

    ok = len(hist_a) == 1 and len(hist_b) == 1
    status = "✅" if ok else "❌"
    print(f"{status} Victim A has {len(hist_a)} pulses, Victim B has {len(hist_b)}")
    print()

    print(f"\n{'━' * 70}")
    print("  ✅ Chatbot Orchestrator test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()