import sys
sys.path.insert(0, "/Users/Harshita/Desktop/sih 2026/chatbot")

from schemas.chat import ChatMessage
from ai_service.chatbot import get_chatbot

bot = get_chatbot()

test_prompts = [
    ("EN", "I felt so sad today because no one visited me"),
    ("EN", "Can you tell me about the legal process?"),
    ("EN", "My neighbour was yelling at me this morning"),
    ("EN", "Someone threatened me with a knife outside my house"),
    ("EN", "I have court hearing tomorrow and I am scared"),
    ("EN", "How do I claim travel allowance TAME?"),
    ("EN", "I can't sleep at all, my head hurts and I feel exhausted"),
    ("EN", "I am feeling much better today, thank you"),
    ("HI", "मुझे अदालत जाने से बहुत डर लग रहा है"),
    ("TA", "எனக்கு தூக்கம் வரவில்லை, மிகவும் பயமாக இருக்கிறது")
]

for i, (lang, prompt) in enumerate(test_prompts, 1):
    msg = ChatMessage(
        victim_id=f"user-{i}",
        session_id=f"session-{i}",
        message=prompt,
        language=lang
    )
    res = bot.process_turn(msg)
    print(f"\n--- PROMPT {i} ({lang}) ---")
    print(f"USER: {prompt}")
    print(f"BOT : {res.reply[:120]}...")
    print(f"TIER: {res.severity_level} | DISTRESS: {res.distress.distress_score if res.distress else None} | CHIPS: {res.suggested_actions}")
