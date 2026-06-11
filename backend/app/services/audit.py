from sqlalchemy.orm import Session

from app.models.domain import AuditLog


def audit(db: Session, entity_type: str, entity_id: str | int, action: str, diff: dict | None = None, actor: str = "agent") -> None:
    db.add(AuditLog(entity_type=entity_type, entity_id=str(entity_id), action=action, diff=diff or {}, performed_by=actor))
    db.commit()
