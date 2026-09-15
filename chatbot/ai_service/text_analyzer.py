"""
Text Analyzer — Module 4
Extracts sentiment, emotion, language, critical themes, and distress intensity
from a single piece of free text.

Design principles:
- Critical themes (suicide, self-harm, threats) use RULES — safety-critical,
  must never miss. False positives acceptable, false negatives NOT.
- Sentiment + emotion use PRETRAINED transformers — reliable, multilingual.
- Handles text-speak / SMS shorthand because victims in crisis don't write
  in perfect grammar.
- Everything is explainable — every flag has a reason.
"""

import re
from typing import Optional

try:
    from langdetect import detect, LangDetectException
except Exception:
    class LangDetectException(Exception):
        pass
    def detect(text):
        return "en"

from models.loader import get_models
from schemas.text_analysis import TextAnalysisResult


# ============================================================
# CRITICAL THEME PATTERNS (MULTILINGUAL + TEXT-SPEAK)
# ============================================================
# Safety-critical. Recall > precision here.
# Any match → flag. Missing a real case is worse than a false alarm.
#
# NOTE: We do NOT use \b word boundaries on non-ASCII scripts.
# Python's regex \b relies on \w which doesn't include Devanagari,
# Tamil, Telugu, etc. by default. Substring matching works better.
# ============================================================

CRITICAL_THEME_PATTERNS = {
    # ---------------- SUICIDAL IDEATION ----------------
    "suicidal_ideation": [
        # English — standard
        r"\b(kill|end)\s+(my|him|her|them)self\b",
        r"\bkill\s+myself\b",
        r"\bend\s+(my|it\s+all)\b",
        r"\bend\s+my\s+life\b",
        r"\bsuicid(e|al)\b",
        r"\bwant\s+to\s+die\b",
        r"\bwish\s+i\s+(was|were)\s+dead\b",
        r"\bno\s+(point|reason)\s+(in\s+)?(living|life)\b",
        r"\bbetter\s+off\s+dead\b",
        r"\bdon'?t\s+want\s+to\s+live\b",
        r"\bcan'?t\s+go\s+on\b",
        # English — text-speak / SMS shorthand
        r"dont\s+want\s+2\s+liv",
        r"don'?t\s+want\s+2\s+liv",
        r"wanna\s+die",
        r"want\s+2\s+die",
        r"wnt\s+2\s+die",
        r"end\s+it\s+all",
        r"cant\s+go\s+on",
        r"can'?t\s+take\s+(it|this)\s+no\s+more",
        r"no\s+reason\s+2\s+live",
        r"no\s+reason\s+to\s+live",
        r"no\s+will\s+2\s+live",
        r"nvr\s+want\s+2\s+live",
        # Hindi (no \b — Devanagari-safe substring match)
        r"मरना\s+चाहता",
        r"मरना\s+चाहती",
        r"मरना\s+चाहते",
        r"मरना\s+चाहू",
        r"आत्महत्या",
        r"जीना\s+नहीं\s+चाहता",
        r"जीना\s+नहीं\s+चाहती",
        r"जीवन\s+समाप्त",
        r"मौत\s+चाहिए",
        # Telugu
        r"చనిపోవాలని",
        r"ఆత్మహత్య",
        r"బతకాలని\s+లేదు",
        # Tamil
        r"இறக்க\s+விரும்புகிறேன்",
        r"தற்கொலை",
        r"வாழ\s+விரும்பவில்லை",
        # Bengali
        r"আত্মহত্যা",
        r"মরতে\s+চাই",
        r"বাঁচতে\s+চাই\s+না",
        # Marathi
        r"मरायचं\s+आहे",
        r"जगायचं\s+नाही",
        # Kannada
        r"ಸಾಯಬೇಕು",
        r"ಆತ್ಮಹತ್ಯೆ",
        r"ಬದುಕಲು\s+ಇಷ್ಟವಿಲ್ಲ",
        # Malayalam
        r"മരിക്കണം",
        r"ആത്മഹത്യ",
        r"ജീവിക്കാൻ\s+താല്പര്യമില്ല",
        # Punjabi
        r"ਮਰਨਾ\s+ਚਾਹੁੰਦਾ",
        r"ਆਤਮਹੱਤਿਆ",
        r"ਜੀਣਾ\s+ਨਹੀਂ\s+ਚਾਹੁੰਦਾ",
        # Gujarati
        r"મરવા\s+માંગુ",
        r"આત્મહત્યા",
        r"જીવવું\s+નથી\s+જોઈતું",
    ],

    # ---------------- SELF HARM ----------------
    "self_harm": [
        # English
        r"\b(hurt|harm|cut|injure|kill)\s+myself\b",
        r"\bhurting\s+myself\b",
        r"\b(hurt|harm|cut|injure)\s+(my)?self\b",
        r"\bcutting\s+myself\b",
        r"\bself[\s-]?harm\b",
        # Hindi
        r"खुद\s+को\s+नुकसान",
        r"खुद\s+को\s+चोट",
        # Telugu
        r"నన్ను\s+నేను\s+హింసించ",
        # Tamil
        r"என்னையே\s+காயப்படுத்த",
        # Bengali
        r"নিজেকে\s+আঘাত",
        # Marathi
        r"स्वतःला\s+इजा",
    ],

    # ---------------- THREATS ----------------
    "threats": [
        # English
        r"\b(threat|threaten|threatened|threatening)\b",
        r"\bthey\s+will\s+(kill|hurt|harm)\b",
        r"\bgoing\s+to\s+(kill|hurt|harm)\s+me\b",
        r"\bafraid\s+(they|he|she)\s+will\b",
        r"\bscared\s+(they|he|she)\s+will\b",
        # Hindi
        r"धमकी",
        r"जान\s+से\s+मारने",
        r"मार\s+डालेंगे",
        # Telugu
        r"బెదిరించ",
        r"చంపేస్తామని",
        # Tamil
        r"மிரட்ட",
        r"கொலை\s+செய்வ",
        # Bengali
        r"হুমকি",
        r"মেরে\s+ফেলবে",
        # Marathi
        r"मारून\s+टाकतील",
    ],

    # ---------------- HOPELESSNESS ----------------
    "hopelessness": [
        # English
        r"\b(no|nothing)\s+hope\b",
        r"\bhopeless\b",
        r"\bno\s+(way\s+out|future|point)\b",
        r"\bgive\s+up\b",
        r"\bgiven\s+up\b",
        r"\bgv\s+up\b",
        r"\bnothing\s+matters\b",
        # Hindi
        r"निराशा",
        r"कोई\s+उम्मीद\s+नहीं",
        r"कोई\s+रास्ता\s+नहीं",
        # Telugu
        r"ఆశ\s+లేదు",
        r"మార్గం\s+లేదు",
        # Tamil
        r"நம்பிக்கை\s+இல்லை",
        # Bengali
        r"আশা\s+নেই",
        # Marathi
        r"आशा\s+नाही",
    ],

    # ---------------- VIOLENCE FEAR ----------------
    "violence_fear": [
        # English — standard
        r"\b(scared|afraid|terrified|fearful)\b",
        r"\bfear\s+for\s+(my|our)\s+(life|safety)\b",
        r"\bunsafe\b",
        # English — text-speak
        r"\bscrd\b",
        r"\bafrd\b",
        r"\bfrgt?nd\b",
        # Hindi
        r"डर\s+लग",
        r"डरा\s+हुआ",
        r"भयभीत",
        # Telugu
        r"భయంగా",
        r"భయపడ",
        # Tamil
        r"பயமாக",
        r"பயப்பட",
        # Bengali
        r"ভয়\s+পাচ্ছি",
        r"ভীত",
        # Marathi
        r"भीती\s+वाटते",
        r"घाबरलो",
        # Kannada
        r"ಭಯವಾಗಿದೆ",
        r"ಹೆದರಿಕೆ",
        # Malayalam
        r"ഭയമാണ്",
        r"പേടിയാണ്",
        # Punjabi
        r"ਡਰ\s+ਲੱਗ",
        # Gujarati
        r"ડર\s+લાગ",
    ],
}


# ============================================================
# DISTRESS INTENSITY WEIGHTS
# ============================================================

EMOTION_DISTRESS_WEIGHT = {
    "fear": 0.85,
    "sadness": 0.45,
    "anger": 0.55,
    "disgust": 0.50,
    "neutral": 0.0,
    "surprise": 0.1,
    "joy": -0.5,
}


# Languages we officially support — used to validate langdetect output
SUPPORTED_LANGS = {"en", "hi", "te", "ta", "bn", "mr", "kn", "ml", "pa", "gu"}


class TextAnalyzer:
    """
    Analyzes free text → sentiment, emotion, critical themes, distress intensity.
    Uses singleton models from models.loader — loaded once, reused.
    """

    def __init__(self):
        self.models = get_models()

    # ----------------------------------------------------------
    # Language detection (hardened for short text)
    # ----------------------------------------------------------
    def _detect_language(self, text: str) -> str:
        """
        Detect language. Falls back to 'en' on failure.

        langdetect is unreliable on short text (<20 chars) — for these we
        assume English unless we see a clear non-Latin script.
        """
        stripped = text.strip()

        # Short text → don't trust langdetect's guess
        if len(stripped) < 20:
            if not any(ord(c) > 127 for c in stripped):
                return "en"

        try:
            lang = detect(stripped)
            # langdetect sometimes returns odd codes for very short text
            if len(stripped) < 20 and lang not in SUPPORTED_LANGS:
                return "en"
            return lang
        except LangDetectException:
            return "en"

    # ----------------------------------------------------------
    # Sentiment
    # ----------------------------------------------------------
    def _analyze_sentiment(self, text: str) -> tuple[str, float, dict]:
        """
        Returns (label, score, full_distribution).
        Label normalized to: positive | negative | neutral
        """
        if not self.models.sentiment:
            text_lower = text.lower()
            neg_words = ["bad", "sad", "scared", "fear", "hurt", "die", "kill", "threat", "pain", "hopeless", "cry", "crying", "anxious", "panic", "terrible", "डर", "பயம்", "బాధ"]
            pos_words = ["good", "fine", "better", "safe", "happy", "ok", "steady", "peace", "अच्छा", "சரி"]
            has_neg = any(w in text_lower for w in neg_words)
            has_pos = any(w in text_lower for w in pos_words)
            if has_neg:
                return "negative", 0.85, {"negative": 0.85, "neutral": 0.10, "positive": 0.05}
            if has_pos:
                return "positive", 0.80, {"negative": 0.05, "neutral": 0.15, "positive": 0.80}
            return "neutral", 0.70, {"negative": 0.15, "neutral": 0.70, "positive": 0.15}

        raw = self.models.sentiment(text)[0]
        distribution = {item["label"].lower(): item["score"] for item in raw}

        top = max(raw, key=lambda x: x["score"])
        label = top["label"].lower()

        label = {
            "label_0": "negative",
            "label_1": "neutral",
            "label_2": "positive",
        }.get(label, label)

        return label, float(top["score"]), distribution

    # ----------------------------------------------------------
    # Emotion
    # ----------------------------------------------------------
    def _analyze_emotion(self, text: str) -> tuple[str, float, dict]:
        """
        Returns (label, score, full_distribution).
        Labels: anger, disgust, fear, joy, neutral, sadness, surprise
        """
        if not self.models.emotion:
            text_lower = text.lower()
            if any(w in text_lower for w in ["fear", "scared", "threat", "gun", "knife", "police", "court", "attack", "डर", "பயம்", "బాధ"]):
                return "fear", 0.85, {"fear": 0.85, "sadness": 0.10, "neutral": 0.05}
            if any(w in text_lower for w in ["hopeless", "sad", "cry", "crying", "depressed", "alone", "रो", "கண்ணீர்"]):
                return "sadness", 0.80, {"sadness": 0.80, "fear": 0.10, "neutral": 0.10}
            if any(w in text_lower for w in ["angry", "rage", "furious", "hate", "गुस्सा"]):
                return "anger", 0.75, {"anger": 0.75, "neutral": 0.25}
            if any(w in text_lower for w in ["good", "safe", "happy", "fine", "peace"]):
                return "joy", 0.80, {"joy": 0.80, "neutral": 0.20}
            return "neutral", 0.75, {"neutral": 0.75, "sadness": 0.15, "fear": 0.10}

        raw = self.models.emotion(text)[0]
        distribution = {item["label"].lower(): item["score"] for item in raw}
        top = max(raw, key=lambda x: x["score"])
        return top["label"].lower(), float(top["score"]), distribution

    # ----------------------------------------------------------
    # Critical themes (rules-based, multilingual)
    # ----------------------------------------------------------
    def _detect_critical_themes(self, text: str) -> list[str]:
        """
        Check text against critical theme regex patterns.
        Multilingual + text-speak aware.
        """
        text_lower = text.lower()
        matched = []
        for theme, patterns in CRITICAL_THEME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched.append(theme)
                    break
        return matched

    # ----------------------------------------------------------
    # Distress intensity
    # ----------------------------------------------------------
    def _compute_distress_intensity(
        self,
        sentiment_label: str,
        emotion_label: str,
        emotion_score: float,
        critical_themes: list[str],
    ) -> str:
        """
        Derive low / medium / high distress intensity.
        Any critical theme → immediately 'high'.
        """
        if critical_themes:
            return "high"

        emotion_weight = EMOTION_DISTRESS_WEIGHT.get(emotion_label, 0.0)
        emotion_contribution = emotion_weight * emotion_score

        if sentiment_label == "negative":
            combined = 0.25 + emotion_contribution
        elif sentiment_label == "positive":
            combined = 0.0 + emotion_contribution
        else:
            combined = 0.15 + emotion_contribution

        if combined >= 0.75:
            return "high"
        elif combined >= 0.30:
            return "medium"
        else:
            return "low"

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------
    def analyze(self, text: str) -> Optional[TextAnalysisResult]:
        """
        Main entry point. Analyze a piece of text end-to-end.
        Returns None if text is empty/whitespace.
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        language = self._detect_language(text)
        sentiment_label, sentiment_score, _ = self._analyze_sentiment(text)
        emotion_label, emotion_score, emotion_dist = self._analyze_emotion(text)
        critical_themes = self._detect_critical_themes(text)
        intensity = self._compute_distress_intensity(
            sentiment_label, emotion_label, emotion_score, critical_themes
        )

        return TextAnalysisResult(
            text=text,
            detected_language=language,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            emotion_label=emotion_label,
            emotion_score=emotion_score,
            emotion_distribution=emotion_dist,
            critical_themes=critical_themes,
            distress_intensity=intensity,
        )


# Singleton accessor
_analyzer_instance: Optional[TextAnalyzer] = None


def get_text_analyzer() -> TextAnalyzer:
    """Return the global TextAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TextAnalyzer()
    return _analyzer_instance