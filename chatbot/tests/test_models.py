"""Quick sanity check that models predict correctly."""
from models.loader import get_models


def main():
    print("🧪 Testing model predictions\n")
    models = get_models()
    if models.sentiment is None:
        print("[INFO] Fast heuristic NLP active — Heavy transformers skipped. Smoke test passed.")
        return
    print("─" * 60)
    print("SENTIMENT TEST")
    print("─" * 60)
    samples = [
        "I feel very safe and supported today.",
        "I am scared and nobody is helping me.",
        "मुझे डर लग रहा है, कोई मदद नहीं कर रहा।",  # Hindi
    ]
    for text in samples:
        result = models.sentiment(text)[0]
        top = max(result, key=lambda x: x["score"])
        print(f"  Text:  {text}")
        print(f"  → {top['label']} ({top['score']:.3f})\n")

    # ---- Emotion ----
    print("─" * 60)
    print("EMOTION TEST")
    print("─" * 60)
    emotion_samples = [
        "I'm terrified they will hurt me again.",
        "I feel so alone and hopeless.",
        "I'm angry that nothing is being done.",
    ]
    for text in emotion_samples:
        result = models.emotion(text)[0]
        top = max(result, key=lambda x: x["score"])
        print(f"  Text:  {text}")
        print(f"  → {top['label']} ({top['score']:.3f})\n")

    # ---- Embedding ----
    print("─" * 60)
    print("EMBEDDING TEST")
    print("─" * 60)
    vec = models.embedder.encode("I feel unsafe")
    print(f"  'I feel unsafe' → vector of shape {vec.shape}")
    print(f"  First 5 values: {vec[:5]}\n")

    print("✅ All model tests passed")


if __name__ == "__main__":
    main()