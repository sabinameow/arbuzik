from .models import AuditLog


def log_action(db, user_id: int, action: str, detail: str = ""):
    log = AuditLog(user_id=user_id, action=action, detail=detail)
    db.add(log)
    db.commit()
