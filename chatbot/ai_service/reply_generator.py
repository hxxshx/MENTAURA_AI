"""
Mentora Reply Generator — Optimised for low-latency responses via Google Gemini Flash.
Decision logic (distress scoring, escalation, risk tiers) stays 100% in the ML pipeline.
Gemini only handles natural-language reply generation.
"""

import os
import re
import concurrent.futures
from typing import Optional, List, Dict, Any

# ── SDK imports ────────────────────────────────────────────────────────────────
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

# ── Cache API key + model at module-load time to avoid re-reading .env each call ──
def _load_env_once() -> Dict[str, str]:
    """Read .env once at import time."""
    try:
        import dotenv
        env_file = dotenv.find_dotenv(usecwd=True)
        if not env_file:
            root_env = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", ".env")
            )
            if os.path.exists(root_env):
                env_file = root_env
        if env_file:
            return dict(dotenv.dotenv_values(env_file))
    except Exception:
        pass
    return {}

_ENV_CACHE: Dict[str, str] = _load_env_once()

def _get_api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or _ENV_CACHE.get("GEMINI_API_KEY")
        or _ENV_CACHE.get("GOOGLE_API_KEY")
        or ""
    ).strip()

def _get_model_name() -> str:
    return (
        os.getenv("GEMINI_MODEL")
        or _ENV_CACHE.get("GEMINI_MODEL")
        or "gemini-3.5-flash-lite"   # fastest available Gemini model
    ).strip()


# ── Fallback replies (used when API is unavailable) ───────────────────────────
FALLBACK_REPLIES: Dict[str, str] = {
    "low": "Thank you for sharing that with me. I'm here whenever you need to talk.",
    "medium": "I hear you, and what you're feeling matters. I'm here with you — would you like to tell me a bit more?",
    "high": "Thank you for trusting me with this. You're not alone — a counsellor has been notified and will reach out to you soon.",
    "critical": "I hear you. Your safety matters most right now. A counsellor has been alerted and will reach out to you immediately. Are you somewhere safe?",
}

# ── Concise system prompt (shorter = faster inference) ────────────────────────
SYSTEM_PROMPT_TEMPLATE = """You are Mentora, a warm AI companion for atrocity victims in India.
Facts (do NOT contradict): Risk={risk_level}, Distress={distress_score}/100, Themes={critical_themes}, Escalated={escalation_flag}.
Rules:
- LOW risk: warm acknowledgement, gentle suggestion. No crisis language.
- MEDIUM risk: validate feelings, offer comfort, may mention counsellor.
- HIGH risk: reassure they are not alone, state counsellor notified, stay calm.
- CRITICAL risk: ask one gentle safety question, confirm immediate help is coming.
Style: 2-3 sentences max. No bullets, no emojis. Name one specific detail from their message. Vary your opening. Match their language (EN/HI/TA/TE/KN/MR/BN). Never say "As an AI"."""


def _clean_reply(raw_text: str) -> str:
    """Strips markdown, emojis, and bullet leaders from generated text."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    if text.startswith(("```", "'''")):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"```$", "", text).strip()
    if text.startswith(('"', "'")) and text.endswith(('"', "'")) and len(text) > 2:
        text = text[1:-1].strip()
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    lines = [re.sub(r"^[\*\-\•\d+\.]\s*", "", l).strip() for l in text.splitlines() if l.strip()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _call_gemini_api(
    user_message: str,
    system_instruction: str,
    conversation_history: List[Dict[str, str]],
    model_name: str,
    api_key: str,
) -> str:
    """Calls Gemini with optimised settings for minimum latency."""

    # Trim history to last 4 turns (not 6) to reduce context size
    recent_history = (conversation_history or [])[-4:]

    # ── google-genai SDK (preferred, faster) ──────────────────────────────────
    if genai and types:
        http_opts = types.HttpOptions(timeout=6000)   # 6 s hard timeout
        client = genai.Client(api_key=api_key, http_options=http_opts)

        contents = []
        for turn in recent_history:
            role = "user" if turn.get("role") in ("user", "human") else "model"
            content = turn.get("content", "")
            if content:
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=content)])
                )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,          # lower temp = faster sampling, more consistent
            max_output_tokens=100,    # 2-3 sentences comfortably fits in 100 tokens
            top_p=0.85,
        )

        models_to_try = [model_name]
        for alt in ["gemini-3.5-flash-lite", "gemini-3.6-flash"]:
            if alt not in models_to_try:
                models_to_try.append(alt)

        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m, contents=contents, config=config
                )
                return response.text or ""
            except Exception as e:
                err = str(e).lower()
                if any(c in err for c in ["404", "429", "not found", "quota", "unavailable"]):
                    continue
                raise e

    # ── legacy google.generativeai SDK fallback ───────────────────────────────
    if legacy_genai:
        legacy_genai.configure(api_key=api_key)
        chat_history = []
        for turn in recent_history:
            role = "user" if turn.get("role") in ("user", "human") else "model"
            content = turn.get("content", "")
            if content:
                chat_history.append({"role": role, "parts": [content]})

        for m in [model_name, "gemini-3.5-flash-lite", "gemini-3.6-flash"]:
            try:
                model = legacy_genai.GenerativeModel(
                    model_name=m,
                    system_instruction=system_instruction,
                    generation_config={"temperature": 0.4, "max_output_tokens": 180},
                )
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(user_message)
                if response and response.text:
                    return response.text
            except Exception:
                continue

    raise RuntimeError("No Google Gemini SDK available.")


def generate_reply(
    user_message: str,
    risk_level: str,
    distress_score: float,
    critical_themes: List[str],
    conversation_history: List[Dict[str, str]],
    language: str = "en",
    escalation_flag: bool = False,
    recommended_interventions: Optional[List[str]] = None,
) -> str:
    """
    Returns Gemini-generated reply. Falls back to a safe template on any failure.
    Optimised for <3 s median response time.
    """
    norm_risk = str(risk_level).lower().split(".")[-1]
    if norm_risk not in FALLBACK_REPLIES:
        norm_risk = "medium"
    fallback_str = FALLBACK_REPLIES[norm_risk]

    api_key = _get_api_key()
    if not api_key or (not genai and not legacy_genai):
        return fallback_str

    model_name = _get_model_name()
    themes_str = ", ".join(critical_themes) if critical_themes else "none"

    system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
        risk_level=norm_risk,
        distress_score=round(float(distress_score), 1),
        critical_themes=themes_str,
        escalation_flag=bool(escalation_flag),
    )

    # Goodbye shortcut — no need to hit the model
    if re.search(r"\b(bye|goodbye|see you|good night|take care)\b", user_message.lower()):
        system_instruction += "\nUser is saying goodbye. Reply with a short warm farewell only."
        fallback_str = "Take care of yourself. I'm here whenever you need to talk."

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _call_gemini_api,
                user_message=user_message,
                system_instruction=system_instruction,
                conversation_history=conversation_history or [],
                model_name=model_name,
                api_key=api_key,
            )
            raw_result = future.result(timeout=7.0)   # 7 s wall-clock timeout

        cleaned = _clean_reply(raw_result)
        return cleaned if cleaned else fallback_str

    except Exception:
        return fallback_str
