"""Check which languages work for sentiment + themes. Don't guess — measure."""
from ai_service.text_analyzer import get_text_analyzer


LANG_TESTS = [
    # (text, expected_lang, description)
    # --- English ---
    ("I am very scared for my safety.", "en", "English - fear"),

    # --- Hindi ---
    ("मुझे बहुत डर लग रहा है।", "hi", "Hindi - fear"),
    ("मैं मरना चाहता हूँ।", "hi", "Hindi - suicidal"),

    # --- Telugu ---
    ("నాకు చాలా భయంగా ఉంది.", "te", "Telugu - fear"),

    # --- Tamil ---
    ("எனக்கு மிகவும் பயமாக இருக்கிறது.", "ta", "Tamil - fear"),

    # --- Bengali ---
    ("আমি খুব ভয় পাচ্ছি।", "bn", "Bengali - fear"),

    # --- Marathi ---
    ("मला खूप भीती वाटते.", "mr", "Marathi - fear"),

    # --- Kannada ---
    ("ನನಗೆ ತುಂಬಾ ಭಯವಾಗಿದೆ.", "kn", "Kannada - fear"),

    # --- Malayalam ---
    ("എനിക്ക് വളരെ ഭയമാണ്.", "ml", "Malayalam - fear"),

    # --- Punjabi ---
    ("ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗ ਰਿਹਾ ਹੈ।", "pa", "Punjabi - fear"),

    # --- Gujarati ---
    ("મને ખૂબ ડર લાગે છે.", "gu", "Gujarati - fear"),
]


def main():
    print("🧪 Multilingual Reality Check\n")
    analyzer = get_text_analyzer()

    for text, expected_lang, desc in LANG_TESTS:
        try:
            result = analyzer.analyze(text)
            lang_ok = "✅" if result.detected_language == expected_lang else "⚠️"
            print(f"{lang_ok} [{desc}]")
            print(f"   Text:      {text}")
            print(f"   Detected:  {result.detected_language} (expected {expected_lang})")
            print(f"   Sentiment: {result.sentiment_label} ({result.sentiment_score:.2f})")
            print(f"   Emotion:   {result.emotion_label} ({result.emotion_score:.2f})")
            print(f"   Themes:    {result.critical_themes}")
            print(f"   Intensity: {result.distress_intensity}")
            print()
        except Exception as e:
            print(f"❌ [{desc}] ERROR: {e}\n")


if __name__ == "__main__":
    main()