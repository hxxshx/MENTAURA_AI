"""
WebSocket API — real-time chat with the Mentaura backend.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from schemas.chat import ChatMessage
from ai_service.chatbot import get_chatbot


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, victim_id: str, ws: WebSocket):
        await ws.accept()
        self.active[victim_id] = ws

    def disconnect(self, victim_id: str):
        self.active.pop(victim_id, None)


manager = ConnectionManager()


@router.websocket("/ws/chat/{victim_id}")
async def websocket_chat(websocket: WebSocket, victim_id: str):
    await manager.connect(victim_id, websocket)
    chatbot = get_chatbot()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid JSON"})
                continue

            session_id = data.get("session_id", f"session-{victim_id}")
            text = data.get("message", "")

            if not text:
                await websocket.send_json({"error": "empty message"})
                continue

            msg = ChatMessage(
                victim_id=victim_id,
                session_id=session_id,
                message=text,
                channel=data.get("channel", "chatbot"),
            )

            response = chatbot.process_turn(msg)
            await websocket.send_json(_serialize_response(response))

    except WebSocketDisconnect:
        manager.disconnect(victim_id)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        manager.disconnect(victim_id)


def _serialize_response(response) -> dict:
    out = {
        "session_id": response.session_id,
        "reply": response.reply,
        "turn_number": response.turn_number,
        "timestamp": response.timestamp.isoformat(),
        "explanation": response.explanation,
    }

    if response.distress:
        out["distress"] = {
            "score": response.distress.distress_score,
            "risk_level": _enum_str(response.distress.risk_level),
            "risk_factors": response.distress.risk_factors,
            "reason_codes": response.distress.reason_codes,
        }

    if response.text_analysis:
        out["text_analysis"] = {
            "language": response.text_analysis.detected_language,
            "sentiment": response.text_analysis.sentiment_label,
            "emotion": response.text_analysis.emotion_label,
            "critical_themes": response.text_analysis.critical_themes,
        }

    if response.escalation:
        out["escalation"] = {
            "flag": response.escalation.escalation_flag,
            "trend": _enum_str(response.escalation.trend_direction),
            "avg_delta": response.escalation.avg_delta,
        }

    if response.intervention:
        out["intervention"] = {
            "recommended": [_enum_str(i) for i in response.intervention.recommended_interventions],
            "priority": _enum_str(response.intervention.priority),
            "reasoning": response.intervention.reasoning,
        }

    return out


def _enum_str(val) -> str:
    if hasattr(val, "value"):
        return val.value
    s = str(val)
    return s.split(".")[-1] if "." in s else s
