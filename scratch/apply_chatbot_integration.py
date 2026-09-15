"""
Safely replace lines in victim.py with ML Chatbot invocation.
"""
from pathlib import Path

victim_path = Path("/Users/Harshita/Desktop/sih 2026/backend/app/routers/victim.py")
content = victim_path.read_text(encoding="utf-8")

start_marker = "    history = payload.conversation_history or []"
end_marker = "    # 3. Persist Support Pulse Record into Database"

assert start_marker in content, "start_marker not found"
assert end_marker in content, "end_marker not found"

start_idx = content.find(start_marker) + len(start_marker)
end_idx = content.find(end_marker)

new_code = """

    # 1. Process turn through ML Trained Chatbot Orchestrator
    try:
        from schemas.chat import ChatMessage
        from ai_service.chatbot import get_chatbot

        chatbot = get_chatbot()
        chat_msg = ChatMessage(
            victim_id=str(current_user.id),
            session_id=f"session-{current_user.id}",
            message=user_msg,
            language=lang,
            channel="chatbot_web"
        )
        chat_turn = chatbot.process_turn(chat_msg)

        reply_text = chat_turn.reply
        severity_level = chat_turn.severity_level or "low"
        dynamic_score = int(chat_turn.distress.distress_score) if chat_turn.distress else 20
        primary_emotion = chat_turn.detected_emotion or (chat_turn.text_analysis.emotion_label if chat_turn.text_analysis else "neutral")
        suggested_actions = chat_turn.suggested_actions or ["Try 4-7-8 Breathing", "Explore Grounding Techniques", "Check Case Journey"]
        coping_techniques = chat_turn.coping_techniques or []
        escalation_contact = chat_turn.escalation_contact
        alert_details = chat_turn.alert_details
        alert_generated = (severity_level == "high")
        expl_text = chat_turn.explanation or f"MentAura ML Engine triaged input as '{severity_level.upper()}' severity (DDS: {dynamic_score}/100, Primary Emotion: {primary_emotion})."
        motivational_text = ""
    except Exception as e:
        print(f"[ML CHATBOT INTEGRATION ERROR]: {e}")
        reply_text = "I hear you, and what you're experiencing matters. You are in a safe, confidential space. How can I best support you right now?"
        severity_level = "low"
        dynamic_score = 20
        primary_emotion = "neutral"
        suggested_actions = ["Try 4-7-8 Breathing", "Explore Grounding Techniques", "Check Case Journey"]
        coping_techniques = []
        escalation_contact = None
        alert_details = None
        alert_generated = False
        expl_text = "Fallback assessment"
        motivational_text = ""

    wellbeing_state = "Heavy" if severity_level == "high" else ("Managing" if severity_level == "medium" else "Steady")

"""

updated_content = content[:start_idx] + new_code + content[end_idx:]
victim_path.write_text(updated_content, encoding="utf-8")
print("Successfully applied ML Chatbot integration in victim.py!")
