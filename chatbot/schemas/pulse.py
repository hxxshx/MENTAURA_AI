"""
Input from victim / helpline / chatbot.
This is the raw signal that enters the AI pipeline.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CaseStage(str, Enum):
    FIR_FILED = "fir_filed"
    INVESTIGATION = "investigation"
    COURT = "court"
    POST_JUDGMENT = "post_judgment"
    REHABILITATION = "rehabilitation"


class WellbeingState(str, Enum):
    VERY_UNSAFE = "very_unsafe"
    UNSAFE = "unsafe"
    NEUTRAL = "neutral"
    SAFE = "safe"
    VERY_SAFE = "very_safe"


class AffectingFactor(str, Enum):
    THREATS = "threats"
    SELF_HARM = "self_harm"
    SUICIDAL_THOUGHTS = "suicidal_thoughts"
    FINANCIAL_STRESS = "financial_stress"
    SOCIAL_OSTRACISM = "social_ostracism"
    LEGAL_STRESS = "legal_stress"
    DISPLACEMENT = "displacement"
    HEALTH_ISSUES = "health_issues"


class SupportNeed(str, Enum):
    COUNSELLING = "counselling"
    LEGAL_AID = "legal_aid"
    PROTECTION = "protection"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    RELOCATION = "relocation"
    REHABILITATION = "rehabilitation"


class PulseInput(BaseModel):
    """
    One pulse = one interaction with a victim.
    Comes from: chatbot, IVRS transcript, SMS, app, web portal.
    """
    victim_id: str = Field(..., description="Unique victim identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Structured fields (from chatbot form / IVRS menu)
    wellbeing_state: Optional[WellbeingState] = None
    affecting_factors: list[AffectingFactor] = Field(default_factory=list)
    support_needs: list[SupportNeed] = Field(default_factory=list)
    case_stage: Optional[CaseStage] = None

    # Free-text (from chatbot / voice transcript / SMS body)
    feeling_text: Optional[str] = Field(
        None, description="Response to: How are you feeling today?"
    )
    difficulty_text: Optional[str] = Field(
        None, description="Response to: What has been most difficult recently?"
    )
    notes: Optional[str] = Field(None, description="Any additional free text")

    class Config:
        use_enum_values = True