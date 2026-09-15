"""
Admin Pending Approvals Router for Official Signups in Mentaura.
Allows state, national, and district administrators to review, approve,
and reject pending official registrations.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import get_db
from backend.app.models.user import User, AuditLog
from backend.app.models.review import ReviewAction
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin Official Approvals"])

ADMIN_ROLES = {
    "state_admin",
    "state_administrator",
    "national_administrator",
    "district_admin",
    "district_authority"
}

ROLE_LABELS = {
    "counsellor": "Psychological Counsellor",
    "case_officer": "Case Coordination Officer",
    "legal_aid_officer": "Legal Aid & DLSA Officer",
    "protection_officer": "Protection & Security Officer",
    "medical_rehabilitation_officer": "Medical & Rehab Officer",
    "district_authority": "District Magistrate / Collector",
    "district_admin": "District Administrator",
    "state_administrator": "State Level Administrator",
    "state_admin": "State Level Administrator",
    "national_administrator": "National Level Administrator"
}

def verify_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Enforce that the caller has an authorized administrator role."""
    role = (current_user.verified_role or "").lower()
    if role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized State and District Administrators only."
        )
    return current_user

def serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def format_role_title(role_key: str) -> str:
    if not role_key:
        return "Official"
    return ROLE_LABELS.get(role_key, role_key.replace("_", " ").title())


class ApproveOfficialPayload(BaseModel):
    user_id: str = Field(..., description="UUID of pending user")
    verified_role: Optional[str] = Field(None, description="Role to assign upon verification")
    district: Optional[str] = Field(None, description="Assigned district")
    state: Optional[str] = Field(None, description="Assigned state")
    notes: Optional[str] = Field(None, description="Approval justification notes")


class RejectOfficialPayload(BaseModel):
    user_id: str = Field(..., description="UUID of pending user")
    reason: Optional[str] = Field(None, description="Rejection reason for audit records")


@router.get("/pending-officials")
def get_pending_officials(
    admin: User = Depends(verify_admin_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns list of official registrations currently awaiting admin review and verification.
    """
    pending_users = db.query(User).filter(
        User.account_status == "pending_verification"
    ).order_by(User.created_at.desc()).all()

    items = []
    for u in pending_users:
        items.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "phone_number": u.phone_number,
            "requested_role": u.requested_category,
            "requested_role_display": format_role_title(u.requested_category),
            "preferred_language": u.preferred_language or "EN",
            "preferred_channel": u.preferred_channel or "web",
            "district": getattr(u, "district", None) or "Chennai District",
            "state": getattr(u, "state", None) or "Tamil Nadu",
            "official_id": u.official_id,
            "account_status": u.account_status,
            "requested_at": serialize_dt(u.created_at)
        })

    return {
        "total_count": len(items),
        "pending_officials": items,
        "admin_reviewer": {
            "name": admin.full_name,
            "role": admin.verified_role,
            "email": admin.email
        }
    }


@router.post("/approve-official")
def approve_official(
    payload: ApproveOfficialPayload,
    admin: User = Depends(verify_admin_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approves a pending official account, assigning their verified role and setting account_status to active.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_role = payload.verified_role or user.requested_category or "counsellor"
    user.verified_role = target_role
    user.account_status = "active"
    user.email_verified = True

    # Record Review Action & Audit Log
    now = datetime.now(timezone.utc)
    action = ReviewAction(
        user_id=admin.id,
        target_type="user_approval",
        target_id=user.id,
        action_type="approve_official",
        status="approved",
        notes=f"Approved official role '{target_role}'. {payload.notes or ''}".strip(),
        performed_at=now
    )
    db.add(action)

    audit = AuditLog(
        user_id=admin.id,
        action="official_approved",
        details=f"Approved user {user.email} as {target_role} by {admin.email}",
        created_at=now
    )
    db.add(audit)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": f"Official {user.full_name} has been successfully verified as {format_role_title(target_role)}.",
        "user_id": user.id,
        "verified_role": user.verified_role,
        "account_status": user.account_status
    }


@router.post("/reject-official")
def reject_official(
    payload: RejectOfficialPayload,
    admin: User = Depends(verify_admin_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rejects a pending official registration and marks the account status as rejected.
    """
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.account_status = "rejected"
    user.verified_role = "rejected"

    # Record Review Action & Audit Log
    now = datetime.now(timezone.utc)
    action = ReviewAction(
        user_id=admin.id,
        target_type="user_rejection",
        target_id=user.id,
        action_type="reject_official",
        status="rejected",
        notes=f"Official request rejected. Reason: {payload.reason or 'Not specified'}",
        performed_at=now
    )
    db.add(action)

    audit = AuditLog(
        user_id=admin.id,
        action="official_rejected",
        details=f"Rejected user {user.email}. Reason: {payload.reason or 'N/A'}",
        created_at=now
    )
    db.add(audit)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": f"Official registration for {user.full_name} has been rejected.",
        "user_id": user.id,
        "account_status": user.account_status
    }
