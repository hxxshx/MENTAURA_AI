"""
Audit Logging Service for Security & Compliance.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.user import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """Record an audit trail event."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address[:45] if ip_address else None,
            created_at=datetime.now(timezone.utc)
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        # Fallback print without interrupting request flow
        print(f"[AUDIT_LOG_ERROR] {action}: {e}")
