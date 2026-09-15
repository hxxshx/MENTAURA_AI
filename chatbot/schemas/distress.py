"""
Output of the Distress Scorer module.
The Dynamic Distress Score (DDS) — the heart of Mentaura.
"""

from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DistressResult(BaseModel):
    """Full distress assessment for one pulse."""
    victim_id: str

    # Core outputs
    distress_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: RiskLevel

    # Explainability
    risk_factors: list[str] = Field(
        default_factory=list,
        description="e.g. ['suicidal_thoughts', 'very_unsafe_state', 'threats_present']"
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Machine-readable codes used to compute the score"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of the score"
    )

    # Breakdown (transparency)
    rule_score: float = Field(..., description="Score from rule engine only")
    text_adjustment: float = Field(
        ..., description="Score adjustment from NLP analysis (±15 max)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "victim_id": "V001",
                "distress_score": 78.0,
                "risk_level": "high",
                "risk_factors": ["very_unsafe_state", "suicidal_thoughts"],
                "reason_codes": ["WELLBEING_VERY_UNSAFE:+50", "THEME_SUICIDAL:+20"],
                "explanation": "Distress is high due to very unsafe feeling and suicidal thoughts.",
                "rule_score": 70.0,
                "text_adjustment": 8.0,
            }
        }