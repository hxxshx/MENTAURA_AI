"""
Chatbot request/response contracts.
One turn = one message in, one response out (plus full AI analysis).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from schemas.text_analysis import TextAnalysisResult
from schemas.distress import DistressResult
from schemas.escalation import EscalationResult
from schemas.intervention import InterventionResult


class ChatMessage(BaseModel):
    """Incoming message from victim via chatbot / SMS / app / IVRS."""
    victim_id: str
    session_id: str
    message: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = Field(default="EN", description="EN | HI | TA | TE | KN | MR | BN")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    channel: str = Field(
        default="chatbot",
        description="chatbot | sms | app | ivrs_transcript | web | helpline"
    )
    conversation_history: Optional[list] = Field(default=None, description="Previous conversation turns")


class ChatResponse(BaseModel):
    """Full response to one chat turn."""
    session_id: str
    reply: str = Field(..., description="Empathetic reply to show to the victim")

    # Dynamic UI tier & content fields
    severity_level: Optional[str] = "low"
    suggested_actions: Optional[list[str]] = None
    coping_techniques: Optional[list[dict]] = None
    escalation_contact: Optional[dict] = None
    alert_details: Optional[dict] = None
    detected_emotion: Optional[str] = "neutral"

    # AI analysis of this turn
    text_analysis: Optional[TextAnalysisResult] = None
    distress: Optional[DistressResult] = None
    escalation: Optional[EscalationResult] = None
    intervention: Optional[InterventionResult] = None

    # Human-readable explanation (for counsellor dashboards)
    explanation: Optional[str] = Field(
        None, description="Full human-readable report of this turn"
    )

    # Session metadata
    turn_number: int = Field(..., ge=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)