from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_role
from ..models import AuditLog
from ..events import event_log

router = APIRouter(tags=["admin"])


@router.get("/audit-logs", summary="[admin] View audit log entries")
def get_logs(
    action: str | None = Query(None, description="Filter by action name"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "user_id": l.user_id,
            "detail": l.detail,
            "timestamp": l.timestamp,
        }
        for l in logs
    ]


@router.get("/events", summary="[admin] View in-memory event bus log")
def get_events(user=Depends(require_role("admin"))):
    """
    Shows all events that have been published since the server started.
    Demonstrates the event-driven layer without needing an external broker.
    """
    return event_log
