"""
REST API — HTTP endpoints for all ML features.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException

from schemas.chat import ChatMessage, ChatResponse
from schemas.pulse import PulseInput
from schemas.distress import DistressResult
from ai_service.chatbot import get_chatbot
from ai_service.text_analyzer import get_text_analyzer
from ai_service.distress_scorer import get_distress_scorer
from session.manager import get_session_manager


router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Mentaura AI Service",
        "timestamp": datetime.utcnow().isoformat(),
        "victims_tracked": get_session_manager().victim_count(),
    }


@router.post("/chat", response_model=ChatResponse)
def chat(message: ChatMessage):
    try:
        chatbot = get_chatbot()
        return chatbot.process_turn(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.post("/voice-transcript", response_model=ChatResponse)
def voice_transcript(message: ChatMessage):
    message.channel = "ivrs_transcript"
    try:
        chatbot = get_chatbot()
        return chatbot.process_turn(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice transcript processing failed: {str(e)}")


@router.post("/distress-score", response_model=DistressResult)
def distress_score(pulse: PulseInput):
    try:
        analyzer = get_text_analyzer()
        scorer = get_distress_scorer()
        text = pulse.feeling_text or pulse.difficulty_text or pulse.notes
        ta = analyzer.analyze(text) if text else None
        return scorer.compute(pulse, ta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/victim/{victim_id}/history")
def victim_history(victim_id: str):
    sessions = get_session_manager()
    history = sessions.get_history(victim_id)
    return {
        "victim_id": victim_id,
        "pulse_count": len(history),
        "scores": [
            {
                "score": r.distress_score,
                "risk_level": r.risk_level.value if hasattr(r.risk_level, "value") else str(r.risk_level),
            }
            for r in history
        ],
    }
