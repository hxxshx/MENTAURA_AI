"""
Output of the Intervention Recommender module.
Rule-based expert system that maps risk → recommended actions.
"""

from enum import Enum
from pydantic import BaseModel, Field


class InterventionType(str, Enum):
    COUNSELLING = "counselling"
    MEDICAL = "medical"
    WITNESS_PROTECTION = "witness_protection"
    RELOCATION = "relocation"
    FINANCIAL_ASSISTANCE = "financial_assistance"
    LEGAL_AID = "legal_aid"
    REHABILITATION = "rehabilitation"


class InterventionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionResult(BaseModel):
    """Recommended interventions + reasoning."""
    victim_id: str
    recommended_interventions: list[InterventionType] = Field(default_factory=list)
    priority: InterventionPriority
    reasoning: str = Field(..., description="Human-readable justification")
    trigger_codes: list[str] = Field(
        default_factory=list, description="Rule codes that fired"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "victim_id": "V001",
                "recommended_interventions": ["counselling", "witness_protection", "legal_aid"],
                "priority": "critical",
                "reasoning": "High distress with threats and court-stage stress.",
                "trigger_codes": ["HIGH_RISK", "THREAT_DETECTED", "COURT_STAGE"],
            }
        }