"""
Mentaura Backend — Model Loader (Singleton)
Loads HuggingFace models ONCE. Every module imports from here.
No module loads its own model — prevents RAM bloat and slow inference.
"""

import time
from functools import lru_cache

try:
    from transformers import pipeline
    from sentence_transformers import SentenceTransformer
except Exception as e:
    pipeline = None
    SentenceTransformer = None

from config import get_settings


class ModelRegistry:
    """
    Holds all pretrained models as lazy singletons.
    First access loads the model; subsequent accesses are instant.
    Falls back gracefully if weights are unavailable or offline.
    """

    def __init__(self):
        self._sentiment_pipe = None
        self._emotion_pipe = None
        self._embedder = None
        self._loaded = False
        self._load_time = 0.0

    def _load_all(self):
        """Load every model. Called once, on first use."""
        if self._loaded:
            return

        settings = get_settings()
        start = time.time()

        if pipeline is None or not settings.ENABLE_HEAVY_TRANSFORMERS:
            print("[INFO] Fast multilingual heuristic NLP active (instant response mode).")
            self._loaded = True
            return

        try:
            print(f"⏳ Loading sentiment model: {settings.SENTIMENT_MODEL}")
            self._sentiment_pipe = pipeline(
                "sentiment-analysis",
                model=settings.SENTIMENT_MODEL,
                tokenizer=settings.SENTIMENT_MODEL,
                top_k=None,
                truncation=True,
                max_length=512,
            )

            print(f"⏳ Loading emotion model: {settings.EMOTION_MODEL}")
            self._emotion_pipe = pipeline(
                "text-classification",
                model=settings.EMOTION_MODEL,
                tokenizer=settings.EMOTION_MODEL,
                top_k=None,
                truncation=True,
                max_length=512,
            )

            if SentenceTransformer:
                print(f"⏳ Loading embedding model: {settings.EMBEDDING_MODEL}")
                self._embedder = SentenceTransformer(settings.EMBEDDING_MODEL)

            self._load_time = time.time() - start
            print(f"✅ All models loaded in {self._load_time:.2f}s")
        except Exception as e:
            print(f"⚠️ Model loading encountered error ({e}); using resilient fallback.")
        finally:
            self._loaded = True

    @property
    def sentiment(self):
        if not self._loaded:
            self._load_all()
        return self._sentiment_pipe

    @property
    def emotion(self):
        if not self._loaded:
            self._load_all()
        return self._emotion_pipe

    @property
    def embedder(self):
        if not self._loaded:
            self._load_all()
        return self._embedder

    @property
    def load_time(self) -> float:
        return self._load_time


@lru_cache()
def get_models() -> ModelRegistry:
    """Global accessor — always returns the same instance."""
    return ModelRegistry()


if __name__ == "__main__":
    print("🚀 Mentaura — Model Loader Smoke Test")
    registry = get_models()
    print(f"Sentiment: {type(registry.sentiment).__name__}")
    print(f"Emotion:   {type(registry.emotion).__name__}")
    print(f"Embedder:  {type(registry.embedder).__name__}")
    print(f"✅ Total load time: {registry.load_time:.2f}s")