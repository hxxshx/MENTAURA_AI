"""Verify all schemas instantiate and validate correctly."""
from schemas.pulse import (
    PulseInput, WellbeingState, AffectingFactor, SupportNeed, CaseStage
)
from schemas.text_analysis import TextAnalysisResult
from schemas.distress import DistressResult, RiskLevel
from schemas.escalation import EscalationResult, TrendDirection
from schemas.intervention import (
    InterventionResult, InterventionType, InterventionPriority
)
from schemas.chat import ChatMessage, ChatResponse


def main():
    print("🧪 Testing schemas\n")

    # ---- PulseInput ----
    pulse = PulseInput(
        victim_id="V001",
        wellbeing_state=WellbeingState.UNSAFE,
        affecting_factors=[AffectingFactor.THREATS, AffectingFactor.SUICIDAL_THOUGHTS],
        support_needs=[SupportNeed.COUNSELLING, SupportNeed.PROTECTION],
        case_stage=CaseStage.COURT,
        feeling_text="I'm scared and no one is helping.",
    )
    print(f"✅ PulseInput:  victim={pulse.victim_id}  factors={pulse.affecting_factors}")

    # ---- TextAnalysisResult ----
    ta = TextAnalysisResult(
        text="I feel so alone",
        detected_language="en",
        sentiment_label="negative",
        sentiment_score=0.94,
        emotion_label="sadness",
        emotion_score=0.98,
        critical_themes=["hopelessness"],
        distress_intensity="high",
    )
    print(f"✅ TextAnalysis: sentiment={ta.sentiment_label} emotion={ta.emotion_label}")

    # ---- DistressResult ----
    dr = DistressResult(
        victim_id="V001",
        distress_score=78.0,
        risk_level=RiskLevel.HIGH,
        risk_factors=["very_unsafe_state"],
        reason_codes=["WELLBEING_VERY_UNSAFE:+50"],
        explanation="Test explanation.",
        rule_score=70.0,
        text_adjustment=8.0,
    )
    print(f"✅ DistressResult: score={dr.distress_score} risk={dr.risk_level}")

    # ---- EscalationResult ----
    er = EscalationResult(
        victim_id="V001",
        escalation_flag=True,
        trend_direction=TrendDirection.WORSENING,
        window_size=3,
        recent_scores=[55.0, 65.0, 78.0],
        avg_delta=11.5,
        escalation_reasons=["monotonic_increase"],
        explanation="Distress is rising.",
    )
    print(f"✅ Escalation: flag={er.escalation_flag} trend={er.trend_direction}")

    # ---- InterventionResult ----
    ir = InterventionResult(
        victim_id="V001",
        recommended_interventions=[
            InterventionType.COUNSELLING,
            InterventionType.WITNESS_PROTECTION,
        ],
        priority=InterventionPriority.CRITICAL,
        reasoning="High distress + threats.",
        trigger_codes=["HIGH_RISK"],
    )
    print(f"✅ Intervention: priority={ir.priority} count={len(ir.recommended_interventions)}")

    # ---- Chat ----
    msg = ChatMessage(victim_id="V001", session_id="S001", message="I'm scared")
    resp = ChatResponse(
        session_id="S001",
        reply="I hear you. Can you tell me more?",
        turn_number=1,
    )
    print(f"✅ Chat: msg='{msg.message}' → reply='{resp.reply}'")

    print("\n✅ All schemas validated successfully")


if __name__ == "__main__":
    main()