"""
Output of the Text Analyzer module.
Represents what we learned from the victim's free text.
"""

from pydantic import BaseModel, Field


class CriticalTheme(str):
    """Marker class — kept simple; values come as strings."""
    pass


class TextAnalysisResult(BaseModel):
    """Full analysis of one piece of free text."""
    text: str = Field(..., description="Original analyzed text")
    detected_language: str = Field(..., description="ISO code, e.g. 'en', 'hi'")

    # Sentiment
    sentiment_label: str = Field(..., description="positive | negative | neutral")
    sentiment_score: float = Field(..., ge=0.0, le=1.0)

    # Emotion (top emotion + full distribution)
    emotion_label: str = Field(..., description="fear | sadness | anger | joy | ...")
    emotion_score: float = Field(..., ge=0.0, le=1.0)
    emotion_distribution: dict[str, float] = Field(default_factory=dict)

    # Critical themes (safety-critical)
    critical_themes: list[str] = Field(
        default_factory=list,
        description="e.g. ['suicidal_ideation', 'self_harm', 'threats', 'hopelessness']"
    )

    # Derived
    distress_intensity: str = Field(
        ..., description="low | medium | high — derived from sentiment + emotion"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "I feel so alone and hopeless",
                "detected_language": "en",
                "sentiment_label": "negative",
                "sentiment_score": 0.94,
                "emotion_label": "sadness",
                "emotion_score": 0.98,
                "emotion_distribution": {"sadness": 0.98, "fear": 0.01},
                "critical_themes": ["hopelessness"],
                "distress_intensity": "high",
            }
        }