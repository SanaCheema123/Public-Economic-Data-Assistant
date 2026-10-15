from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def audit(db: Session, action: str, user_id: str | None = None, request_id: str | None = None, metadata: dict | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, request_id=request_id, metadata_json=metadata or {}))
