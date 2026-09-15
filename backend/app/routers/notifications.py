"""
In-App Notifications Router for Counsellors, Case Officers, and Administrators.
Provides endpoints for retrieving notifications, unread counts, and marking notifications as read.
Dispatches alerts when high-risk Support Pulses are submitted or cases are escalated.
Strictly respects privacy: No raw narratives or audio binaries are ever stored or exposed in notifications.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models.user import User, AuditLog
from backend.app.models.notification import Notification
from backend.app.routers.auth import get_current_user

logger = logging.getLogger("mentaura.notifications")

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

ALLOWED_OFFICIAL_ROLES = {
    "counsellor",
    "case_officer",
    "district_admin",
    "district_authority",
    "state_admin",
    "state_administrator",
    "national_administrator"
}


def verify_official_role(user: User = Depends(get_current_user)) -> User:
    """Ensure user is an authorized official or administrator."""
    if user.verified_role not in ALLOWED_OFFICIAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized officials and administrators."
        )
    return user


class MarkReadRequest(BaseModel):
    notification_ids: Optional[List[str]] = None
    mark_all: Optional[bool] = False


# Helper functions for dispatching notifications
def create_in_app_notification(
    db: Session,
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    metadata_dict: Optional[Dict[str, Any]] = None
) -> Optional[Notification]:
    """Create a single notification record for a user safely."""
    try:
        meta_json = json.dumps(metadata_dict) if metadata_dict else None
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            is_read=False,
            meta_data=meta_json
        )
        db.add(notif)
        db.flush()
        
        # Simulated SMS/Email log
        logger.info(
            f"[NOTIFICATION DISPATCH] User {user_id} | Type: {notif_type} | Title: {title} "
            f"(Simulated SMS/Email channel logged - no real external message sent)"
        )
        return notif
    except Exception as e:
        logger.error(f"Failed to create notification for user {user_id}: {e}")
        return None


from sqlalchemy import desc, func

def dispatch_high_risk_pulse_notifications(
    db: Session,
    pulse_id: str,
    masked_identifier: str,
    risk_level: str = "high",
    risk_score: int = 0
):
    """
    Identify relevant recipients (active counsellors and district/state admins)
    and dispatch high_risk_pulse notifications.
    """
    recipients = db.query(User).filter(
        User.verified_role.in_(list(ALLOWED_OFFICIAL_ROLES)),
        func.lower(User.account_status) == "active"
    ).all()

    for recipient in recipients:
        create_in_app_notification(
            db=db,
            user_id=recipient.id,
            notif_type="high_risk_pulse",
            title="High-risk Support Pulse submitted",
            message=f"A high-risk pulse was submitted for {masked_identifier}. Please review in the triage queue.",
            metadata_dict={
                "pulse_id": pulse_id,
                "masked_identifier": masked_identifier,
                "risk_level": risk_level,
                "risk_score": risk_score
            }
        )


def dispatch_pulse_submission_notifications(
    db: Session,
    pulse_id: str,
    masked_identifier: str,
    risk_level: str = "low",
    requested_items: Optional[List[str]] = None,
    timeline: str = "within 24 hours"
):
    """
    Dispatches notification to active counsellors when a support pulse is submitted
    and processed, ensuring rapid team outreach and awareness.
    """
    recipients = db.query(User).filter(
        User.verified_role.in_(list(ALLOWED_OFFICIAL_ROLES)),
        func.lower(User.account_status) == "active"
    ).all()

    req_summary = f" (Requested: {', '.join(requested_items)})" if requested_items else ""
    title = f"Support Pulse Processed ({risk_level.capitalize()})"
    msg = f"Support pulse processed for {masked_identifier}{req_summary}. Team outreach timeline: {timeline}."

    for recipient in recipients:
        create_in_app_notification(
            db=db,
            user_id=recipient.id,
            notif_type="pulse_submitted",
            title=title,
            message=msg,
            metadata_dict={
                "pulse_id": pulse_id,
                "masked_identifier": masked_identifier,
                "risk_level": risk_level,
                "requested_items": requested_items or [],
                "timeline": timeline
            }
        )


def dispatch_case_escalation_notifications(
    db: Session,
    case_id: str,
    masked_case_id: str,
    reason: str,
    escalation_level: str = "urgent",
    assigned_user_id: Optional[str] = None
):
    """
    Dispatch case_escalated notifications to assigned official, case officers, and admins.
    """
    recipients = db.query(User).filter(
        User.verified_role.in_(list(ALLOWED_OFFICIAL_ROLES)),
        func.lower(User.account_status) == "active"
    ).all()

    for recipient in recipients:
        create_in_app_notification(
            db=db,
            user_id=recipient.id,
            notif_type="case_escalated",
            title="Case escalated",
            message=f"Case {masked_case_id} has been escalated to {escalation_level}: {reason}",
            metadata_dict={
                "case_id": case_id,
                "masked_case_id": masked_case_id,
                "reason": reason,
                "escalation_level": escalation_level
            }
        )


@router.get("", response_model=Dict[str, Any])
def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """
    Return recent notifications for the authenticated user, ordered by creation date descending.
    """
    notifs = db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(desc(Notification.created_at)).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).count()

    return {
        "success": True,
        "unread_count": unread_count,
        "total": len(notifs),
        "notifications": [n.to_dict() for n in notifs]
    }


@router.get("/unread-count", response_model=Dict[str, Any])
def get_unread_count(
    user: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """
    Return the total unread notification count for the authenticated user.
    """
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).count()

    return {
        "success": True,
        "unread_count": unread_count
    }


@router.post("/mark-read", response_model=Dict[str, Any])
def mark_notifications_read(
    payload: MarkReadRequest,
    user: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """
    Mark specified notification IDs or all notifications as read for the authenticated user.
    """
    query = db.query(Notification).filter(Notification.user_id == user.id)

    if payload.mark_all or not payload.notification_ids:
        # Mark all unread notifications as read
        updated_count = query.filter(Notification.is_read == False).update(
            {"is_read": True}, synchronize_session="fetch"
        )
    else:
        # Mark specific notification IDs as read
        updated_count = query.filter(
            Notification.id.in_(payload.notification_ids),
            Notification.is_read == False
        ).update({"is_read": True}, synchronize_session="fetch")

    db.commit()

    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).count()

    return {
        "success": True,
        "updated_count": updated_count,
        "unread_count": unread_count,
        "message": f"Marked {updated_count} notification(s) as read."
    }
