"""
Chatbot Orchestration — Module 6
Ties all 5 ML modules into a single pipeline.

Input:  ChatMessage (victim text + metadata)
Output: ChatResponse (empathetic reply + full AI analysis + explanation)
"""

from typing import Optional

from schemas.chat import ChatMessage, ChatResponse
from schemas.pulse import PulseInput
from ai_service.text_analyzer import get_text_analyzer
from ai_service.distress_scorer import get_distress_scorer
from ai_service.escalation_detector import get_escalation_detector
from ai_service.intervention_recommender import get_intervention_recommender
from ai_service.explainability import explain_full_turn
from session.manager import get_session_manager
from ai_service.conversation import (
    Intent, classify_intent, extract_topic, build_reply, should_shift_to_crisis,
    generate_contextual_turn
)
from ai_service.reply_generator import generate_reply


# ============================================================
# Empathetic reply templates (rule-based, no LLM needed)
# ============================================================

REPLIES = {
    "low": {
        "positive": "That's good to hear. We're glad you're doing well. We're here whenever you need us.",
        "neutral":  "Thanks for checking in. We're always here if you need support.",
        "help":     "Thanks for reaching out. If anything changes or you'd like to talk, we're here to listen.",
    },
    "medium": {
        "concerned": "Thank you for sharing that with me. It sounds like things have been a bit tough. Would you like to talk about what's going on?",
        "neutral":   "I hear you. It's okay to have hard days. We're here to listen — would you like to tell me more?",
        "help":      "Thanks for telling me this. Let's see how we can help. Would you like to talk about it?",
    },
    "high": {
        "concerned": "Thank you for telling me this. What you're going through sounds really difficult. A counsellor will reach out to support you soon, and I'm here if you want to keep talking.",
        "help":      "I hear how hard things are right now. You're not alone in this. A counsellor will be notified and will contact you shortly.",
    },
    "critical": {
        "default": "I hear you, and I'm really glad you reached out. What you're feeling is serious, and help is available right now. A counsellor will be notified immediately. You are not alone in this.",
    },
}


def _pick_reply(risk_level, message: str = "") -> str:
    """
    Pick an empathetic reply based on risk level AND message content.
    """
    if hasattr(risk_level, "value"):
        risk_level = risk_level.value
    risk = str(risk_level).lower().split(".")[-1]

    text = (message or "").lower()

    help_words = [
        "help", "counsel", "counselling", "support", "advice",
        "talk to someone", "need someone", "please help",
    ]
    positive_words = [
        "fine", "okay", "ok", "good", "safe", "well", "better",
        "happy", "great", "thank",
    ]

    wants_help = any(w in text for w in help_words)
    sounds_positive = any(w in text for w in positive_words)

    if risk == "critical":
        return REPLIES["critical"]["default"]

    if risk == "high":
        if wants_help:
            return REPLIES["high"]["help"]
        return REPLIES["high"]["concerned"]

    if risk == "medium":
        if wants_help:
            return REPLIES["medium"]["help"]
        if sounds_positive:
            return REPLIES["medium"]["neutral"]
        return REPLIES["medium"]["concerned"]

    # LOW risk
    if wants_help:
        return REPLIES["low"]["help"]
    if sounds_positive:
        return REPLIES["low"]["positive"]
    return REPLIES["low"]["neutral"]


# ============================================================
# Chatbot pipeline
# ============================================================

class ChatbotOrchestrator:
    """Coordinates all ML modules for one chat turn."""

    def __init__(self):
        self.analyzer = get_text_analyzer()
        self.scorer = get_distress_scorer()
        self.escalation = get_escalation_detector()
        self.recommender = get_intervention_recommender()
        self.sessions = get_session_manager()
        self._conversation_log: dict[str, list[str]] = {}
        self._last_reply: dict[str, str] = {}
        self._chat_history: dict[str, list[dict]] = {}

    def process_turn(
        self,
        message: ChatMessage,
        pulse: Optional[PulseInput] = None,
    ) -> ChatResponse:
        """
        Process one chat turn end-to-end.

        Args:
            message: incoming chat message with victim text
            pulse: optional structured pulse data (wellbeing, factors, stage).
                   If not provided, we synthesize a minimal pulse from the message.

        Returns:
            ChatResponse with reply + full AI analysis + explanation.
        """
        # 1. Text analysis
        text_analysis = self.analyzer.analyze(message.message)

        # 2. Build pulse if not provided
        if pulse is None:
            pulse = PulseInput(
                victim_id=message.victim_id,
                feeling_text=message.message,
            )
        else:
            if not pulse.feeling_text:
                pulse.feeling_text = message.message

        # 3. Distress scoring
        distress = self.scorer.compute(pulse, text_analysis)

        # 4. Escalation detection — uses FULL history including this turn
        prior = self.sessions.get_history(message.victim_id)
        sequence = prior + [distress]
        escalation = self.escalation.detect(message.victim_id, sequence)

        # 5. Store this result for future turns
        self.sessions.add_distress_result(message.victim_id, distress)

        # 6. Intervention recommendation
        intervention = self.recommender.recommend(
            pulse, distress, escalation, text_analysis
        )

        # 7. Conversation-aware empathetic reply
        prior_history = self.sessions.get_history(message.victim_id)
        turn_count = len(prior_history)

        msg_log = self._conversation_log.setdefault(message.victim_id, [])
        if turn_count <= 1:
            msg_log.clear()
            self._last_reply.pop(message.victim_id, None)
            self._chat_history.pop(message.victim_id, None)
        prev_messages = list(msg_log)              # messages BEFORE this one
        msg_log.append(message.message)            # add current

        risk_str = distress.risk_level.value if hasattr(distress.risk_level, "value") else str(distress.risk_level)
        escalation_flag = bool(escalation and escalation.escalation_flag)

        intent = classify_intent(
            current_message=message.message,
            history=prev_messages,
            risk_level=risk_str,
            escalation_flag=escalation_flag,
        )

        # Extract topic from CURRENT message (what victim just said).
        # Fall back to previous message's topic if current has none.
        last_topic = extract_topic(message.message)
        if not last_topic and prev_messages:
            last_topic = extract_topic(prev_messages[-1])

        last_rep = None
        if getattr(message, "conversation_history", None):
            for item in reversed(message.conversation_history):
                if isinstance(item, dict) and item.get("role") in ("bot", "assistant"):
                    last_rep = item.get("content")
                    break
        if not last_rep:
            last_rep = self._last_reply.get(message.victim_id)

        msg_lang = getattr(message, "language", "EN") or "EN"
        turn_number = len(self.sessions.get_history(message.victim_id))

        # Generate contextual, multi-domain, multilingual response
        turn_data = generate_contextual_turn(
            message=message.message,
            language=msg_lang,
            turn_number=turn_number,
            prev_messages=getattr(message, "conversation_history", None) or prev_messages,
            distress=distress,
            escalation=escalation,
            text_analysis=text_analysis,
            last_reply=last_rep
        )

        # Gemini-generated reply with conversation context
        conv_hist = getattr(message, "conversation_history", None)
        if not conv_hist:
            conv_hist = self._chat_history.get(message.victim_id, [])

        rec_interventions = (
            [i.value if hasattr(i, "value") else str(i) for i in getattr(intervention, "recommended_interventions", [])]
            if intervention and hasattr(intervention, "recommended_interventions")
            else []
        )
        crit_themes = list(text_analysis.critical_themes) if text_analysis and getattr(text_analysis, "critical_themes", None) else []

        reply = generate_reply(
            user_message=message.message,
            risk_level=risk_str,
            distress_score=float(distress.distress_score) if distress else 20.0,
            critical_themes=crit_themes,
            conversation_history=conv_hist,
            language=msg_lang.lower(),
            escalation_flag=escalation_flag,
            recommended_interventions=rec_interventions,
        )
        self._last_reply[message.victim_id] = reply
        self._chat_history.setdefault(message.victim_id, []).extend([
            {"role": "user", "content": message.message},
            {"role": "assistant", "content": reply},
        ])

        # 8. Full human-readable explanation
        explanation = explain_full_turn(distress, escalation, intervention)

        # Card selection derived strictly from CURRENT turn's distress result and domain
        curr_risk = risk_str.lower()
        curr_domain = turn_data.get("domain", "general_conversational") if turn_data else "general_conversational"
        is_suicide = (curr_domain in ("suicide_crisis", "self_harm")) or ("suicidal_ideation" in crit_themes)
        is_threat = (curr_domain in ("safety_threats", "physical_threat")) or any(t in crit_themes for t in ["threats", "violence", "violence_fear"])

        try:
            from ai_service.dynamic_engine import ALERT_DETAILS_CRISIS, ALERT_DETAILS_THREAT
        except ImportError:
            from chatbot.ai_service.dynamic_engine import ALERT_DETAILS_CRISIS, ALERT_DETAILS_THREAT

        if curr_risk == "low":
            final_severity = "low"
            final_alert = None
            final_escalation = None
            final_coping = []
        elif curr_risk == "medium":
            final_severity = "medium"
            final_alert = None
            if curr_domain in ("sadness_depression", "sleep_somatic", "court_legal", "anxiety_panic"):
                final_escalation = turn_data.get("escalation_contact") if turn_data else None
            else:
                final_escalation = None
            final_coping = (turn_data.get("coping_techniques") or []) if turn_data else []
        elif curr_risk in ("high", "critical"):
            final_severity = "high"
            if is_suicide:
                final_alert = ALERT_DETAILS_CRISIS.get(msg_lang, ALERT_DETAILS_CRISIS["EN"])
                final_escalation = None
            elif is_threat:
                final_alert = ALERT_DETAILS_THREAT.get(msg_lang, ALERT_DETAILS_THREAT["EN"])
                final_escalation = None
            else:
                final_alert = None
                final_escalation = turn_data.get("escalation_contact") if turn_data else None
            final_coping = []
        else:
            final_severity = "low"
            final_alert = None
            final_escalation = None
            final_coping = []

        return ChatResponse(
            session_id=message.session_id,
            reply=reply,
            severity_level=final_severity,
            suggested_actions=turn_data.get("suggested_actions", []) if turn_data else [],
            coping_techniques=final_coping,
            escalation_contact=final_escalation,
            alert_details=final_alert,
            detected_emotion=turn_data.get("primary_emotion", "neutral") if turn_data else "neutral",
            text_analysis=text_analysis,
            distress=distress,
            escalation=escalation,
            intervention=intervention,
            explanation=explanation,
            turn_number=turn_number,
        )


# Singleton accessor
_orchestrator_instance: Optional[ChatbotOrchestrator] = None


def get_chatbot() -> ChatbotOrchestrator:
    """Return the global ChatbotOrchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ChatbotOrchestrator()
    return _orchestrator_instance