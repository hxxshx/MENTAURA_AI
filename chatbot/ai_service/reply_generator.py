"""
Mentora Reply Generator — Powered by Google Gemini 1.5 Flash
Replaces the reply-generation layer with real-time empathetic text.
Decision logic (distress scoring, escalation, risk tiers, interventions)
remains 100% inside the ML pipeline. Gemini receives decisions as locked facts.
"""

import os
import re
import concurrent.futures
from typing import Optional, List, Dict, Any

try:
    import google.generativeai as legacy_genai
except ImportError:
    legacy_genai = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


FALLBACK_REPLIES: Dict[str, str] = {
    "low": "Thank you for sharing that with me. I'm here whenever you need to talk.",
    "medium": "I hear you, and what you're feeling matters. I'm here with you — would you like to tell me a bit more?",
    "high": "Thank you for trusting me with this. You're not alone — a counsellor has been notified and will reach out to you soon.",
    "critical": "I hear you. Your safety matters most right now. A counsellor has been alerted and will reach out to you immediately. Are you somewhere safe?",
}

SYSTEM_PROMPT_TEMPLATE = """You are Mentora, an empathetic, warm, and calm AI companion for
victims of atrocities in India under the SC/ST (Prevention of
Atrocities) Act, 1989. You speak in a caring, human tone — never
robotic, never clinical, never preachy.

The system has ALREADY analyzed this conversation. The following
facts are LOCKED — you must NOT contradict them:

- Risk level: {risk_level}
- Distress score: {distress_score}/100
- Detected concerns: {critical_themes}
- Escalation flag: {escalation_flag}
- Recommended actions: {recommended_interventions}

Rules for your reply:
- If risk is LOW: respond warmly, gently acknowledge what the user
  said, and offer a small, practical, kind suggestion. Do NOT
  mention counsellors or emergency numbers.
- If risk is MEDIUM: validate their feelings with real empathy,
  then offer one or two comforting or grounding suggestions. You
  MAY gently mention a counsellor is available.
- If risk is HIGH: acknowledge their courage in sharing, reassure
  them they are not alone, and clearly state that a counsellor
  and/or protective support has been notified. Keep the tone calm
  and steady — never alarming.
- If risk is CRITICAL: prioritize safety. Speak with deep care.
  Ask ONE gentle safety question (e.g. whether they are somewhere
  safe right now). Let them know immediate help is on the way.

Voice and style:
- Speak like a caring human, not a manual.
- 2-4 short sentences MAX. No bullet points, no lists, no emojis.
- Do not repeat the user's exact words back verbatim.
- Reference ONE specific detail from the user's message. If they
  mention court, say "court". If they mention sleep, say "sleep".
  If they mention a person, name the person. Do not paraphrase
  into vague terms like "this" or "what you're going through".
  Specificity is how a real listener shows they heard you.
- Do NOT use the same opening phrase ("It is completely natural...")
  for every reply. Vary your first sentence based on what the user
  actually said. Speak specifically to their situation.
- If the user is writing in Hindi, Tamil, Kannada, Telugu, Marathi,
  or Bengali, respond ENTIRELY in that language. Reference the
  specific detail in that language (e.g. "अदालत", "தூக்கம்").
- Do not use phrases like "As an AI" or "I understand that".
- Do not add disclaimers about being an AI.
- Match the language of the user's message (support English,
  Hindi, Tamil, Telugu, Kannada, Marathi, Bengali).
- End with one short, gentle question OR one calm reassurance."""


def _clean_reply(raw_text: str) -> str:
    """Removes bullet points, emojis, or markdown code fences from generated text."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    # Strip wrapping quotes or markdown backticks
    if text.startswith(("```", "'''")):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    if text.startswith(('"', "'")) and text.endswith(('"', "'")) and len(text) > 2:
        text = text[1:-1].strip()

    # Remove emojis (Unicode symbols and emoticons)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)

    # Remove bullet point leaders like "* ", "- ", "1. "
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r"^[\*\-\•\d+\.]\s*", "", line).strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    text = " ".join(cleaned_lines)
    # Remove excessive spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _call_gemini_api(
    user_message: str,
    system_instruction: str,
    conversation_history: List[Dict[str, str]],
    model_name: str,
    api_key: str
) -> str:
    """Invokes Google Gemini via google.generativeai or google-genai SDK."""
    if legacy_genai:
        legacy_genai.configure(api_key=api_key)
        models_to_try = [model_name]
        for m in ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]:
            if m not in models_to_try:
                models_to_try.append(m)

        last_err = None
        for m in models_to_try:
            try:
                model = legacy_genai.GenerativeModel(
                    model_name=m,
                    system_instruction=system_instruction
                )
                chat_history = []
                if conversation_history:
                    for turn in conversation_history[-6:]:
                        role = "user" if turn.get("role") in ("user", "human") else "model"
                        content = turn.get("content", "")
                        if content:
                            chat_history.append({"role": role, "parts": [content]})
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(user_message)
                if response and response.text:
                    return response.text
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err

    if genai:
        http_opts = types.HttpOptions(timeout=10000) if types else None
        client = genai.Client(api_key=api_key, http_options=http_opts)

        contents = []
        if conversation_history:
            for turn in conversation_history[-6:]:
                role = "user" if turn.get("role") in ("user", "human") else "model"
                content = turn.get("content", "")
                if content:
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
            max_output_tokens=600,
        ) if types else None

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            return response.text or ""
        except Exception as e:
            err_msg = str(e).lower()
            if any(c in err_msg for c in ["404", "429", "not found", "resource_exhausted", "quota", "no longer available"]):
                for alt_model in ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-flash-latest"]:
                    if alt_model != model_name:
                        try:
                            response = client.models.generate_content(
                                model=alt_model,
                                contents=contents,
                                config=config
                            )
                            return response.text or ""
                        except Exception:
                            pass
            raise e

    raise RuntimeError("No Google Gemini SDK available.")


def generate_reply(
    user_message: str,
    risk_level: str,               # "low" | "medium" | "high" | "critical"
    distress_score: float,         # 0-100
    critical_themes: List[str],    # e.g. ["suicidal_ideation"]
    conversation_history: List[Dict[str, str]],  # [{"role": "user"|"assistant", "content": str}]
    language: str = "en",          # ISO code
    escalation_flag: bool = False,
    recommended_interventions: Optional[List[str]] = None,
) -> str:
    """
    Returns the reply string Gemini generated.
    Raises no exception — falls back to a safe template on failure.
    """
    # Normalize risk level
    norm_risk = str(risk_level).lower().split(".")[-1]
    if norm_risk not in FALLBACK_REPLIES:
        norm_risk = "medium"

    fallback_str = FALLBACK_REPLIES[norm_risk]

    # Check API key
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()

    if not api_key:
        try:
            import dotenv
            env_file = dotenv.find_dotenv(usecwd=True)
            if not env_file:
                # Check workspace root
                root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
                if os.path.exists(root_env):
                    env_file = root_env
            if env_file:
                env_dict = dotenv.dotenv_values(env_file)
                api_key = (env_dict.get("GEMINI_API_KEY") or env_dict.get("GOOGLE_API_KEY") or "").strip()
        except Exception:
            pass

    if not api_key or (not genai and not legacy_genai):
        return fallback_str

    model_name = (
        os.getenv("GEMINI_MODEL")
        or (env_dict.get("GEMINI_MODEL") if "env_dict" in locals() and env_dict else None)
        or "gemini-3.6-flash"
    ).strip()
    themes_str = ", ".join(critical_themes) if critical_themes else "none"
    interventions_str = ", ".join(recommended_interventions) if recommended_interventions else "none"

    system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
        risk_level=norm_risk,
        distress_score=round(float(distress_score), 1),
        critical_themes=themes_str,
        escalation_flag=bool(escalation_flag),
        recommended_interventions=interventions_str,
    )

    is_goodbye = bool(re.search(r"\b(bye|goodbye|see you|good night|take care)\b", user_message.lower()))
    if is_goodbye:
        system_instruction += "\n\nThe user is saying goodbye. Respond with a short, warm farewell. Do not treat this as a crisis."
        fallback_str = "Take care of yourself. I'm here whenever you need to talk."

    try:
        # Enforce timeout via ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _call_gemini_api,
                user_message=user_message,
                system_instruction=system_instruction,
                conversation_history=conversation_history or [],
                model_name=model_name,
                api_key=api_key,
            )
            raw_result = future.result(timeout=12.0)

        cleaned = _clean_reply(raw_result)
        if cleaned:
            return cleaned
        return fallback_str

    except Exception as e:
        # Fall back cleanly without raising exception
        return fallback_str
