"""
Output of the Escalation Detector module.
Looks at a sequence of pulses over time.
"""

from enum import Enum
from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


class EscalationResult(BaseModel):
    """Escalation analysis over the last N pulses."""
    victim_id: str
    escalation_flag: bool = Field(
        ..., description="True if distress is escalating"
    )
    trend_direction: TrendDirection

    window_size: int = Field(..., description="How many pulses analyzed")
    recent_scores: list[float] = Field(
        default_factory=list, description="Distress scores in the window"
    )
    avg_delta: float = Field(
        ..., description="Average change per pulse (positive = worsening)"
    )

    escalation_reasons: list[str] = Field(default_factory=list)
    explanation: str

    class Config:
        json_schema_extra = {
            "example": {
                "victim_id": "V001",
                "escalation_flag": True,
                "trend_direction": "worsening",
                "window_size": 3,
                "recent_scores": [55.0, 65.0, 78.0],
                "avg_delta": 11.5,
                "escalation_reasons": ["monotonic_increase", "crossed_to_high"],
                "explanation": "Distress has increased steadily over the last 3 check-ins.",
            }
        }