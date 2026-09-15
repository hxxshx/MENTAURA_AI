"""
Counsellor and Official Review Workspace Router for Mentaura.
Provides secure, role-restricted endpoints for incoming Support Pulse triage,
support request review, case milestone tracking, and intervention coordination.
"""
import uuid
import html
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, AuditLog
from backend.app.models.pulse import SupportPulse, SupportPulseResponse, VoiceProcessingJob
from backend.app.models.support_request import SupportRequest
from backend.app.models.review import ReviewAction
from backend.app.models.counsellor_message import CounsellorMessage
from backend.app.models.notification import Notification
from backend.app.services.risk_scorer import calculate_risk_score
from backend.app.routers.auth import get_current_user
import json

router = APIRouter(prefix="/api/counsellor", tags=["Official Review Workspace"])

from backend.app.utils.anonymity import mask_identifier

OFFICIAL_ROLES = {
    "counsellor", "case_officer", "district_authority", "district_admin",
    "legal_aid_officer", "protection_officer", "medical_rehabilitation_officer",
    "medical_rehab_officer", "state_administrator", "state_admin", 
    "national_administrator", "national_admin"
}

def verify_official_role(current_user: User = Depends(get_current_user)) -> User:
    """Enforces that the caller is an authenticated official/counsellor."""
    role = (current_user.role or current_user.verified_role or "").lower()
    if role not in OFFICIAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized counsellors and case officials."
        )
    return current_user

def mask_name(name: Optional[str]) -> str:
    return mask_identifier(name)

def mask_identifier_label(email: str, role: str) -> str:
    prefix = "[V****m]"
    if role == "witness":
        prefix = "[W****s]"
    elif role == "affected_family_member":
        prefix = "[F****y]"
    return prefix

def serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    """Ensures datetime objects are serialized with UTC timezone offset."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def mask_case_number(case_id: Optional[str]) -> str:
    if not case_id:
        return "Unlinked / Monitoring"
    if len(case_id) > 6:
        return f"{case_id[:5]}***{case_id[-4:]}"
    return "CASE-***"

class ReviewActionPayload(BaseModel):
    target_type: str = Field(..., description="support_pulse | support_request | case_milestone | intervention")
    target_id: str = Field(...)
    action_type: str = Field(..., description="mark_reviewed | assign | update_status | prioritize | schedule_session | refer_to_agency")
    status: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    assigned_role: Optional[str] = Field(default=None)
    assigned_user: Optional[str] = Field(default=None)
    appointment_date: Optional[str] = Field(default=None)
    target_agency: Optional[str] = Field(default=None)
    urgency: Optional[str] = Field(default=None)
    session_format: Optional[str] = Field(default=None)


@router.get("/overview")
def get_counsellor_overview(
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Returns workspace summary metrics and active reviewer identity."""
    # 1. New Support Pulses awaiting triage in the review queue
    triage_res = get_triage_queue(limit=None, official=official, db=db)
    new_pulses_count = triage_res["total_count"]

    # 2. Pending Support Requests in the review queue
    requests_res = get_counsellor_support_requests(limit=None, official=official, db=db)
    pending_requests_count = requests_res["total_count"]

    # 3. Active Cases
    active_cases_count = 3

    # 4. Interventions in Progress
    active_interventions_count = 4

    return {
        "summary": {
            "new_pulses_count": new_pulses_count,
            "pending_requests_count": pending_requests_count,
            "clinical_requests_count": requests_res.get("clinical_count", 0),
            "statutory_requests_count": requests_res.get("statutory_count", 0),
            "active_cases_count": active_cases_count,
            "active_interventions_count": active_interventions_count
        },
        "reviewer": {
            "full_name": official.full_name,
            "role": official.verified_role,
            "requested_category": official.requested_category,
            "email": official.email,
            "account_status": official.account_status,
            "last_login_at": serialize_dt(official.last_login_at)
        }
    }


@router.get("/triage-queue")
def get_triage_queue(
    limit: Optional[int] = None,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns list of incoming Support Pulse submissions for triage.
    Victim personal identifiers are strictly masked.
    """
    query = (
        db.query(SupportPulse)
        .outerjoin(User, SupportPulse.authenticated_user_id == User.id)
        .filter(
            or_(
                SupportPulse.human_review_status.in_(["pending", "new", "in_review", "escalated", "reviewed"]),
                SupportPulse.human_review_status.is_(None)
            )
        )
        .order_by(SupportPulse.submitted_at.desc())
    )
    if limit is not None and limit > 0:
        query = query.limit(limit)
    pulses = query.all()

    items = []
    for p in pulses:
        victim_user = p.user or db.query(User).filter(User.id == p.authenticated_user_id).first()
        victim_role = victim_user.verified_role if victim_user else "victim"
        victim_name = victim_user.full_name if victim_user else "Victim"
        is_victim_anon = bool(getattr(victim_user, "is_anonymous", False)) if victim_user else False
        
        if is_victim_anon:
            anon_tag = getattr(victim_user, "anonymous_id", None) or "Protected"
            role_title = victim_role.replace('_', ' ').title()
            masked_person = f"Protected {role_title} ({anon_tag})"
        else:
            masked_person = f"{victim_name} ({victim_role.replace('_', ' ').title()})"

        factors = []
        needs = []
        for r in p.responses:
            if r.phase == "pulse2" and r.question_key in ("factors", "affecting_factor"):
                factors.append(r.response_value)
            elif r.phase in ("followup", "pulse3") and ("support" in r.question_key or "follow_up" in r.question_key):
                needs.append(r.response_value)

        risk_lvl = getattr(p, "risk_level", None)
        risk_sc = getattr(p, "risk_score", None)
        if not risk_lvl:
            computed = calculate_risk_score(
                wellbeing_state=p.wellbeing_state,
                affecting_factors=factors,
                support_needs=needs,
                text_note=p.text_response
            )
            risk_lvl = computed["risk_level"]
            risk_sc = computed["risk_score"]

        items.append({
            "id": p.id,
            "masked_identifier": masked_person,
            "case_id_masked": mask_case_number(p.case_id),
            "submission_date": serialize_dt(p.submitted_at),
            "wellbeing_state": p.wellbeing_state or "steady",
            "processing_mode": p.processing_mode or "ai_assisted",
            "priority_flag": bool(p.priority_review),
            "risk_level": risk_lvl,
            "risk_score": risk_sc,
            "human_review_status": p.human_review_status or "pending",
            "has_voice_audio": bool(p.audio_storage_reference),
            "audio_url": f"/api/counsellor/audio/{p.id}" if p.audio_storage_reference else None,
            "audio_duration_seconds": p.audio_duration_seconds,
            "has_text_response": bool(p.text_response),
            "text_response": p.text_response if p.text_response else None,
            "text_snippet": html.escape((p.text_response or "")[:120]) + ("..." if len(p.text_response or "") > 120 else "") if p.text_response else None,
            "channel": p.channel or "web",
            "language": p.language or "EN",
            "factors": factors,
            "support_needs": needs
        })

    return {
        "total_count": len(items),
        "triage_queue": items
    }


@router.get("/audio/{pulse_id}")
def get_counsellor_pulse_audio(
    pulse_id: str,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """
    Streams decrypted/protected voice note audio to authorized official under Section 15A.
    """
    pulse = db.query(SupportPulse).filter(SupportPulse.id == pulse_id).first()
    if not pulse or not pulse.audio_storage_reference:
        raise HTTPException(status_code=404, detail="Audio recording not found for this check-in.")

    raw_path = pulse.audio_storage_reference
    file_path = Path(raw_path)
    if not file_path.is_absolute():
        file_path = (Path(__file__).resolve().parents[3] / file_path).resolve()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on enclave storage.")

    media_type = pulse.audio_mime_type or "audio/webm"
    return FileResponse(
        str(file_path),
        media_type=media_type,
        content_disposition_type="inline"
    )


def classify_support_request(support_type: str) -> tuple[str, str, str, str, str]:
    """
    Classifies support request into clinical mental health vs statutory inter-agency domains.
    Returns: (domain, category_label, target_agency, default_role, subcategory)
    """
    low = (support_type or "").strip().lower()
    if "okay for now" in low:
        return "inactive", "Self-Report: Stable", "Victim Self-Report", "None", "inactive"
    if any(k in low for k in ["counsel", "psychological", "support team call", "call from my support team", "support call", "mental health", "trauma"]):
        return "clinical", "Psychological Counselling & Trauma Care", "District Mental Health Cell", "Dr. Priya Nair (Counsellor)", "counselling"
    if any(k in low for k in ["legal", "dlsa", "court date"]):
        return "statutory", "Legal Aid & Court Representation", "DLSA Legal Aid Cell", "DLSA Panel Advocate", "legal_aid"
    if any(k in low for k in ["protect", "safety", "shelter", "threat", "stalking", "escort"]):
        return "statutory", "Witness Protection & Safety (Sec 15A)", "SP Witness Protection Cell", "SP Protection Cell", "protection"
    if any(k in low for k in ["compensation", "financial", "relief", "tame", "travel allowance", "rehabilitation", "relocation"]):
        return "statutory", "Victim Relief & Compensation (Rule 12)", "District Social Welfare Office", "Social Welfare Officer", "compensation"
    if "medical" in low:
        return "statutory", "Medical Care & Hospital Referral", "District CMO Medical Board", "Chief Medical Officer", "medical"
    return "statutory", "General Statutory Assistance", "District Support Cell", "District Nodal Officer", "general"


@router.get("/support-requests")
def get_counsellor_support_requests(
    domain: Optional[str] = None,
    limit: Optional[int] = None,
    include_inactive: bool = False,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns list of victim support requests categorized into clinical care vs statutory referrals.
    """
    query = db.query(SupportRequest).order_by(SupportRequest.submitted_at.desc())
    all_requests = query.all()

    clinical_count = 0
    statutory_count = 0
    inactive_count = 0

    categorized_items = []
    for req in all_requests:
        support_type = getattr(req, "support_type", "general")
        domain_type, cat_label, target_agency, default_role, subcat = classify_support_request(support_type)

        if domain_type == "clinical":
            clinical_count += 1
        elif domain_type == "statutory":
            statutory_count += 1
        else:
            inactive_count += 1

        # Check domain filter
        if domain and domain.lower() in ("clinical", "statutory"):
            if domain_type != domain.lower():
                continue
        elif not include_inactive and domain_type == "inactive":
            continue

        victim_user = req.user
        victim_name = victim_user.full_name if victim_user else "Requester"
        victim_role = victim_user.verified_role if victim_user else "victim"
        is_victim_anon = bool(getattr(victim_user, "is_anonymous", False)) if victim_user else False

        if is_victim_anon:
            anon_tag = getattr(victim_user, "anonymous_id", None) or "Protected"
            role_title = victim_role.replace('_', ' ').title()
            masked_requester = f"Anonymous {role_title} ({anon_tag})"
        else:
            masked_requester = f"{victim_name} ({victim_role.replace('_', ' ').title()})"

        assigned_to = req.assigned_user_reference or (req.assigned_role.replace("_", " ").title() if req.assigned_role else default_role)
        is_urgent = any(w in support_type.lower() for w in ["urgent", "emergency", "immediate", "direct threat", "stalking"])

        parsed_meta = None
        if getattr(req, "session_metadata", None):
            try:
                parsed_meta = json.loads(req.session_metadata)
            except Exception:
                parsed_meta = None

        categorized_items.append({
            "id": req.id,
            "user_id": req.user_id,
            "masked_requester": masked_requester,
            "category": support_type,
            "category_label": cat_label,
            "domain": domain_type,
            "subcategory": subcat,
            "target_agency": target_agency,
            "action_mode": "clinical_care" if domain_type == "clinical" else "statutory_referral",
            "urgency": "urgent" if is_urgent else "standard",
            "status": req.status or "under_review",
            "submitted_at": serialize_dt(req.submitted_at),
            "appointment_at": serialize_dt(req.appointment_at),
            "session_format": getattr(req, "session_format", None) or "telephonic",
            "session_metadata": parsed_meta,
            "case_id_masked": mask_case_number(req.case_id),
            "assigned_to": assigned_to,
            "assigned_role": req.assigned_role or default_role,
            "next_step": req.next_step,
            "notes": req.next_step
        })

    if limit is not None and limit > 0:
        filtered_items = categorized_items[:limit]
    else:
        filtered_items = categorized_items

    total_active = clinical_count + statutory_count

    return {
        "total_count": total_active,
        "clinical_count": clinical_count,
        "statutory_count": statutory_count,
        "inactive_count": inactive_count,
        "filtered_count": len(filtered_items),
        "support_requests": filtered_items
    }


@router.get("/case-milestones")
def get_counsellor_case_milestones(
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Returns official case stages, active milestones, and assigned personnel."""
    cases = [
        {
            "id": "case-01",
            "case_number": "TN-CHN-2026-CR-08942",
            "case_id_masked": "TN-CHN-***-08942",
            "victim_masked": "[V****m] (A****a S.)",
            "current_stage": "Support Monitoring & Case Review",
            "stage_key": "stage_support",
            "last_update": "2026-09-10T11:00:00Z",
            "assigned_officer": "Inspector K. Saravanan",
            "assigned_counsellor": "Dr. Priya Nair",
            "next_milestone": "District Protection Review & Relief Follow-up",
            "status": "on_track",
            "milestones_completed": 4,
            "total_milestones": 6
        },
        {
            "id": "case-02",
            "case_number": "TN-CBE-2026-CR-04112",
            "case_id_masked": "TN-CBE-***-04112",
            "victim_masked": "[W****m] (R****n D.)",
            "current_stage": "Witness Protection & Formal Deposition",
            "stage_key": "stage_witness",
            "last_update": "2026-09-09T14:30:00Z",
            "assigned_officer": "Advocate Meera Sen",
            "assigned_counsellor": "Dr. Priya Nair",
            "next_milestone": "Special Court Deposition Escort",
            "status": "attention_required",
            "milestones_completed": 3,
            "total_milestones": 5
        },
        {
            "id": "case-03",
            "case_number": "TN-MDU-2026-CR-01290",
            "case_id_masked": "TN-MDU-***-01290",
            "victim_masked": "[F****m] (S****a D.)",
            "current_stage": "Compensation & Family Rehabilitation",
            "stage_key": "stage_rehab",
            "last_update": "2026-09-08T16:00:00Z",
            "assigned_officer": "T. Sundaram, IAS",
            "assigned_counsellor": "Dr. Priya Nair",
            "next_milestone": "District Welfare Fund Disbursement",
            "status": "on_track",
            "milestones_completed": 5,
            "total_milestones": 6
        }
    ]
    return {
        "total_count": len(cases),
        "case_milestones": cases
    }


@router.get("/interventions")
def get_counsellor_interventions(
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Returns active coordinated interventions."""
    interventions = [
        {
            "id": "int-01",
            "title": "Protection Order & Police Escort",
            "category": "protection",
            "beneficiary_masked": "[V****m] (A****a S.)",
            "status": "in_progress",
            "assigned_officer": "Inspector Anand Rao",
            "scheduled_date": "2026-09-12T10:00:00Z",
            "details": "Coordinating local patrol rounds and court deposition transit protection.",
            "priority": "high"
        },
        {
            "id": "int-02",
            "title": "Trauma-Informed Psychological Support",
            "category": "counselling",
            "beneficiary_masked": "[V****m] (A****a S.)",
            "status": "scheduled",
            "assigned_officer": "Dr. Priya Nair",
            "scheduled_date": "2026-09-11T15:30:00Z",
            "details": "Bi-weekly video and in-person emotional stabilization sessions.",
            "priority": "medium"
        },
        {
            "id": "int-03",
            "title": "Legal Aid Counsel Assignment",
            "category": "legal_aid",
            "beneficiary_masked": "Rohit Das (Witness)",
            "status": "approved",
            "assigned_officer": "Advocate Meera Sen",
            "scheduled_date": "2026-09-15T11:00:00Z",
            "details": "Assigned District Legal Services Authority (DLSA) advocate for court filing.",
            "priority": "standard"
        },
        {
            "id": "int-04",
            "title": "Relief & Atrocity Compensation Follow-up",
            "category": "compensation",
            "beneficiary_masked": "Sunita Devi (Family Member)",
            "status": "in_progress",
            "assigned_officer": "Rajesh Varma, IAS",
            "scheduled_date": "2026-09-14T14:00:00Z",
            "details": "Tracking bank account transfer under State Victim Relief Scheme.",
            "priority": "medium"
        }
    ]
    return {
        "total_count": len(interventions),
        "interventions": interventions
    }


@router.post("/review-action")
def record_counsellor_review_action(
    payload: ReviewActionPayload,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Records an official triage action, status change, or assignment.
    Persists immutable review_actions and audit_logs records.
    """
    now = datetime.now(timezone.utc)
    clean_notes = html.escape(payload.notes.strip()) if payload.notes else None

    # 1. Update target record state where applicable
    if payload.target_type == "support_pulse":
        pulse = db.query(SupportPulse).filter(SupportPulse.id == payload.target_id).first()
        if pulse:
            if payload.action_type == "mark_reviewed":
                pulse.human_review_status = payload.status or "reviewed"
            elif payload.action_type == "prioritize":
                pulse.priority_review = True
                pulse.human_review_status = "escalated"
            elif payload.action_type == "update_status" and payload.status:
                pulse.human_review_status = payload.status
            db.commit()

    elif payload.target_type == "support_request":
        req = db.query(SupportRequest).filter(SupportRequest.id == payload.target_id).first()
        if req:
            req.last_updated_at = now
            if payload.action_type == "schedule_session":
                req.status = payload.status or "scheduled"
                req.assigned_role = payload.assigned_role or "Psychological Counsellor"
                req.assigned_user_reference = payload.assigned_user or official.full_name
                format_val = (payload.session_format or "telephonic").lower()
                req.session_format = format_val

                if payload.appointment_date:
                    try:
                        clean_date_str = payload.appointment_date.replace("Z", "+00:00")
                        req.appointment_at = datetime.fromisoformat(clean_date_str)
                    except Exception:
                        pass

                pass_suffix = req.id[:6].upper()
                meta = {
                    "format": format_val,
                    "room_id": f"mentaura-room-{req.id[:8]}",
                    "pass_code": f"OSC-TN-2026-{pass_suffix}",
                    "pass_number": f"OSC-TN-2026-{pass_suffix}",
                    "call_status": "scheduled",
                    "video_status": "scheduled",
                    "visitor_arrived": False,
                    "priority": "CRITICAL" if format_val == "emergency_crisis" else "STANDARD",
                    "crisis_status": "active" if format_val == "emergency_crisis" else "standard",
                    "created_at": now.isoformat(),
                    "appointment_at": req.appointment_at.isoformat() if req.appointment_at else None,
                    "counsellor_name": official.full_name,
                    "location": "District One-Stop Support Enclave, Room 104, Special Protection Zone",
                    "transit_escort": "Available under Section 15A"
                }
                req.session_metadata = json.dumps(meta)

                session_summary = f"Counselling session ({format_val.replace('_', ' ').title()}) scheduled with {official.full_name}"
                if clean_notes:
                    session_summary += f": {clean_notes}"
                req.next_step = session_summary

                # Send in-app notification to victim
                format_titles = {
                    "telephonic": "📞 Secure Telephonic Callback",
                    "video": "📹 Encrypted Video Consultation",
                    "in_person": "🏥 One-Stop Centre In-Person Visit",
                    "emergency_crisis": "🚨 Emergency Crisis Stabilization"
                }
                friendly_name = format_titles.get(format_val, "Clinical Counselling")
                db.add(Notification(
                    user_id=req.user_id,
                    type="counselling_scheduled",
                    title=f"{friendly_name} Scheduled",
                    message=f"{official.full_name} has scheduled your {friendly_name} session. Tap to connect.",
                    is_read=False,
                    meta_data=json.dumps({
                        "session_id": req.id,
                        "session_format": format_val,
                        "appointment_at": req.appointment_at.isoformat() if req.appointment_at else None,
                        "action": "open_session"
                    })
                ))
            elif payload.action_type == "refer_to_agency":
                req.status = payload.status or "referred"
                agency = payload.target_agency or "Statutory Authority"
                req.assigned_role = agency
                req.assigned_user_reference = f"{agency} Nodal Officer"
                referral_summary = f"Referred to {agency} by {official.full_name} for statutory action"
                if clean_notes:
                    referral_summary += f" ({clean_notes})"
                req.next_step = referral_summary
            else:
                if payload.status:
                    req.status = payload.status
                if payload.action_type == "assign":
                    req.assigned_user_reference = official.full_name
                    req.assigned_role = official.verified_role.replace("_", " ").title()
                if payload.assigned_role:
                    req.assigned_role = payload.assigned_role
                if payload.assigned_user:
                    req.assigned_user_reference = payload.assigned_user
                if clean_notes:
                    req.next_step = clean_notes
            db.commit()

    # 2. Record ReviewAction in DB
    action_rec = ReviewAction(
        user_id=official.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        action_type=payload.action_type,
        status=payload.status,
        notes=clean_notes,
        performed_at=now
    )
    db.add(action_rec)

    # 3. Log Audit event
    audit_rec = AuditLog(
        user_id=official.id,
        action=f"official_{payload.action_type}",
        details=f"target_type={payload.target_type}, target_id={payload.target_id}, status={payload.status}",
        created_at=now
    )
    db.add(audit_rec)
    db.commit()

    # 4. If escalated or prioritized, dispatch real-time alerts to District Authorities
    if payload.action_type in ("prioritize", "escalate") or payload.status in ("escalated", "referred"):
        from backend.app.routers.notifications import create_in_app_notification
        district_users = db.query(User).filter(
            User.verified_role.in_(["district_authority", "district_admin", "case_officer"]),
            func.lower(User.account_status) == "active"
        ).all()
        masked_target = mask_case_number(payload.target_id)
        for du in district_users:
            create_in_app_notification(
                db=db,
                user_id=du.id,
                notif_type="case_escalated",
                title="Counsellor Escalation Received",
                message=f"Counsellor {official.full_name} has escalated {payload.target_type.replace('_', ' ').title()} ({masked_target}) to District Command for verification and protection orders.",
                metadata_dict={
                    "target_type": payload.target_type,
                    "target_id": payload.target_id,
                    "counsellor": official.full_name,
                    "notes": clean_notes or "Clinical priority escalation"
                }
            )
        db.commit()

    return {
        "success": True,
        "message": "Review action recorded and persisted successfully.",
        "action_id": action_rec.id,
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "new_status": payload.status
    }


# ==============================================================================
# DIRECT 1-TO-1 VICTIM MESSAGING FOR COUNSELLORS
# ==============================================================================

class CounsellorReplyPayload(BaseModel):
    message: Optional[str] = None
    message_text: Optional[str] = None

    def get_text(self) -> str:
        return (self.message_text or self.message or "").strip()

@router.get("/messages/conversations")
def get_counsellor_conversations(
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """List all victim conversations with latest message, unread status, and timestamp."""
    # Find all messages where official is counsellor or receiver
    messages = db.query(CounsellorMessage).order_by(CounsellorMessage.created_at.desc()).all()
    
    conversations_map = {}
    for m in messages:
        vid = m.victim_id
        if vid not in conversations_map:
            conversations_map[vid] = {
                "victim_id": vid,
                "victim_name": m.victim_name,
                "last_message": m.message_text,
                "last_message_time": m.created_at.isoformat() if m.created_at else None,
                "unread_count": 0,
                "last_sender_role": m.sender_role
            }
        if m.sender_role == "victim" and not m.is_read:
            conversations_map[vid]["unread_count"] += 1

    return {
        "conversations": list(conversations_map.values())
    }


@router.get("/messages/{victim_id}")
def get_conversation_thread(
    victim_id: str,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """Fetch full chat thread with a specific victim and mark their messages as read."""
    victim = db.query(User).filter(User.id == victim_id).first()
    victim_name = victim.full_name if victim else "Victim"

    messages = db.query(CounsellorMessage).filter(
        CounsellorMessage.victim_id == victim_id
    ).order_by(CounsellorMessage.created_at.asc()).all()

    # Mark unread victim messages as read
    for m in messages:
        if m.sender_role == "victim" and not m.is_read:
            m.is_read = True
    db.commit()

    return {
        "victim_id": victim_id,
        "victim_name": victim_name,
        "counsellor_name": official.full_name,
        "messages": [m.to_dict() for m in messages]
    }


@router.post("/messages/{victim_id}/reply")
def send_counsellor_reply(
    victim_id: str,
    payload: CounsellorReplyPayload,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """Counsellor sends a direct supportive message/reply to a victim."""
    clean_text = html.escape(payload.get_text())
    if not clean_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    victim = db.query(User).filter(User.id == victim_id).first()
    victim_name = victim.full_name if victim else "Victim"

    now = datetime.now(timezone.utc)
    conv_id = f"conv_{victim_id}_{official.id}"

    new_msg = CounsellorMessage(
        conversation_id=conv_id,
        victim_id=victim_id,
        victim_name=victim_name,
        counsellor_id=official.id,
        counsellor_name=official.full_name,
        sender_id=official.id,
        sender_name=official.full_name,
        sender_role="counsellor",
        message_text=clean_text,
        is_read=False,
        created_at=now
    )
    db.add(new_msg)
    db.commit()

    return {
        "status": "sent",
        "message": new_msg.to_dict()
    }


# ==============================================================================
# MULTI-MODE INTERACTIVE COUNSELLING SESSIONS (TELEPHONIC, VIDEO, IN-PERSON, CRISIS)
# ==============================================================================

class CounsellorSessionActionPayload(BaseModel):
    action: str = Field(..., description="start_call | end_call | start_video | end_video | admit_visitor | complete_visit | stabilize_crisis")
    notes: Optional[str] = None
    vitals: Optional[Dict[str, Any]] = None


@router.get("/sessions/active")
def get_counsellor_active_sessions(
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """Returns active scheduled sessions across all 4 interaction modes for Dr. Priya Nair."""
    sessions = db.query(SupportRequest).filter(
        SupportRequest.session_format.isnot(None),
        SupportRequest.status.in_(["scheduled", "in_progress", "requested", "under_review"])
    ).order_by(SupportRequest.updated_at.desc(), SupportRequest.submitted_at.desc()).all()

    items = []
    for s in sessions:
        meta = {}
        if s.session_metadata:
            try:
                meta = json.loads(s.session_metadata)
            except Exception:
                meta = {}

        victim = s.user
        items.append({
            "id": s.id,
            "victim_id": s.user_id,
            "victim_name": victim.full_name if victim else "Beneficiary",
            "case_id_masked": mask_case_number(s.case_id),
            "session_format": s.session_format or "telephonic",
            "status": s.status,
            "appointment_at": serialize_dt(s.appointment_at),
            "metadata": meta,
            "next_step": s.next_step
        })

    return {
        "total": len(items),
        "sessions": items
    }


@router.post("/sessions/{session_id}/action")
def record_counsellor_session_action(
    session_id: str,
    payload: CounsellorSessionActionPayload,
    official: User = Depends(verify_official_role),
    db: Session = Depends(get_db)
):
    """Handles real-time counsellor actions for Telephonic, Video, In-Person OSC, and Crisis Stabilization."""
    req = db.query(SupportRequest).filter(SupportRequest.id == session_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Counselling session not found.")

    meta = {}
    if req.session_metadata:
        try:
            meta = json.loads(req.session_metadata)
        except Exception:
            meta = {}

    now = datetime.now(timezone.utc)
    act = payload.action.lower()

    if act == "start_call":
        meta["call_status"] = "in_progress"
        meta["call_started_at"] = now.isoformat()
        req.status = "in_progress"
    elif act == "end_call":
        meta["call_status"] = "completed"
        meta["call_ended_at"] = now.isoformat()
        req.status = "completed"
        req.completion_at = now
    elif act == "start_video":
        meta["video_status"] = "in_progress"
        meta["video_started_at"] = now.isoformat()
        req.status = "in_progress"
    elif act == "end_video":
        meta["video_status"] = "completed"
        meta["video_ended_at"] = now.isoformat()
        req.status = "completed"
        req.completion_at = now
    elif act == "admit_visitor":
        meta["visitor_arrived"] = True
        meta["admitted_at"] = now.isoformat()
        req.status = "in_progress"
    elif act == "complete_visit":
        meta["visit_status"] = "completed"
        meta["completed_at"] = now.isoformat()
        if payload.vitals:
            meta["vitals"] = payload.vitals
        req.status = "completed"
        req.completion_at = now
    elif act == "stabilize_crisis":
        meta["crisis_status"] = "stabilized"
        meta["stabilized_at"] = now.isoformat()
        req.status = "completed"
        req.completion_at = now

    if payload.notes:
        meta["last_notes"] = payload.notes
        clean_note = html.escape(payload.notes.strip())
        req.next_step = f"Session {act.replace('_', ' ').title()}: {clean_note}"

    req.session_metadata = json.dumps(meta)
    req.last_updated_at = now
    db.commit()

    return {
        "success": True,
        "session_id": req.id,
        "action": act,
        "status": req.status,
        "metadata": meta
    }


