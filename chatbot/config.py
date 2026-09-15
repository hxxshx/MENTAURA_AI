"""
Mentaura Backend — Central Configuration
All tunable values live here. No magic numbers scattered in code.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ---------- App ----------
    APP_NAME: str = "Mentaura AI Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ---------- Models ----------
    ENABLE_HEAVY_TRANSFORMERS: bool = False
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    EMOTION_MODEL: str = "j-hartmann/emotion-english-distilroberta-base"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ---------- Distress Scoring Thresholds ----------
    RISK_LOW_MAX: int = 30
    RISK_MEDIUM_MAX: int = 60
    RISK_HIGH_MAX: int = 85

    # ---------- Escalation Detection ----------
    ESCALATION_WINDOW: int = 3
    ESCALATION_DELTA: float = 5.0

    # ---------- Chatbot ----------
    MAX_HISTORY_TURNS: int = 20
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings — imported everywhere, created once."""
    return Settings()