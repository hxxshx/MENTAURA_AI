"""Verify the Text Analyzer produces correct, well-formed output."""
from ai_service.text_analyzer import get_text_analyzer


def main():
    print("🧪 Testing Text Analyzer\n")
    analyzer = get_text_analyzer()

    test_cases = [
        # (text, expected_themes, description)
        ("I feel very safe and supported today.",
         [], "positive / safe"),

        ("I am scared and nobody is helping me.",
         ["violence_fear"], "fear detected"),

        ("I want to die, there's no point anymore.",
         ["suicidal_ideation", "hopelessness"], "CRITICAL: suicidal ideation"),

        ("They threatened to kill me if I go to court.",
         ["threats"], "threat detected"),

        ("I've been cutting myself again.",
         ["self_harm"], "self-harm detected"),

        # NOTE: emotion model is English-only → falls back to 'neutral' for Hindi.
        #       Sentiment + themes still work correctly. Multilingual emotion = phase 2.
        ("मुझे डर लग रहा है, कोई मदद नहीं कर रहा।",
         ["violence_fear"], "Hindi fear detected"),

        ("I'm angry that nothing is being done.",
         [], "anger but not critical"),
    ]

    passed = 0
    for text, expected_themes, desc in test_cases:
        result = analyzer.analyze(text)
        themes_ok = all(t in result.critical_themes for t in expected_themes)
        status = "✅" if themes_ok else "⚠️"

        print(f"{status} [{desc}]")
        print(f"   Input:     {text}")
        print(f"   Language:  {result.detected_language}")
        print(f"   Sentiment: {result.sentiment_label} ({result.sentiment_score:.2f})")
        print(f"   Emotion:   {result.emotion_label} ({result.emotion_score:.2f})")
        print(f"   Themes:    {result.critical_themes}")
        print(f"   Intensity: {result.distress_intensity}")
        print()

        if themes_ok:
            passed += 1

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ {passed}/{len(test_cases)} theme tests passed")
    print(f"✅ Text Analyzer works" if passed == len(test_cases)
          else f"⚠️  Some theme assertions failed — check patterns")


if __name__ == "__main__":
    main()