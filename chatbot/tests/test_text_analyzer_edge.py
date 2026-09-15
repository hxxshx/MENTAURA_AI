"""Edge case testing for Text Analyzer. Real world is messy."""
from ai_service.text_analyzer import get_text_analyzer


EDGE_CASES = [
    ("", "empty string"),
    ("   ", "whitespace only"),
    ("...", "just punctuation"),
    ("😢😢😢", "emoji only"),
    ("ok", "single word"),
    ("I am scared मुझे डर लग रहा है", "Hinglish mix"),
    ("I want to die. I want to die. I want to die.", "repeated"),
    ("a" * 5000, "very long input"),
    ("12345", "numbers only"),
    ("I'm fine.", "denial (positive-looking)"),
    ("Everything is ok now 🙂", "positive with emoji"),
    ("I dont want 2 liv", "text-speak: dont want 2 liv"),
    ("i wanna die", "text-speak: wanna die"),
    ("cant go on anymore", "text-speak: cant go on"),
    ("no reason 2 live", "text-speak: no reason 2 live"),
    ("i gv up", "text-speak: gv up"),
]


def main():
    print("🧪 Text Analyzer — Edge Case Tests\n")
    analyzer = get_text_analyzer()

    for text, desc in EDGE_CASES:
        print(f"━━━ [{desc}] ━━━")
        print(f"   Input: {text[:80]}{'...' if len(text) > 80 else ''}")
        try:
            result = analyzer.analyze(text)
            if result is None:
                print(f"   → Returned None (empty input handled) ✅")
            else:
                print(f"   Lang:      {result.detected_language}")
                print(f"   Sentiment: {result.sentiment_label} ({result.sentiment_score:.2f})")
                print(f"   Emotion:   {result.emotion_label} ({result.emotion_score:.2f})")
                print(f"   Themes:    {result.critical_themes}")
                print(f"   Intensity: {result.distress_intensity}")
        except Exception as e:
            print(f"   ❌ ERROR: {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    main()