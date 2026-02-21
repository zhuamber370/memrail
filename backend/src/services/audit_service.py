from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.models import AuditEvent


def log_audit_event(
    db: Session,
    *,
    actor_type: str,
    actor_id: str,
    tool: str,
    action: str,
    target_type: str,
    target_id: str,
    source_refs: Optional[list] = None,
    before_hash: Optional[str] = None,
    after_hash: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditEvent:
    event = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        actor_type=actor_type,
        actor_id=actor_id,
        tool=tool,
        action=action,
        target_type=target_type,
        target_id=target_id,
        source_refs_json=source_refs or [],
        before_hash=before_hash,
        after_hash=after_hash,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit_events(db: Session, *, page: int, page_size: int) -> tuple[list[AuditEvent], int]:
    stmt = (
        select(AuditEvent)
        .order_by(desc(AuditEvent.occurred_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(stmt))
    total = int(db.query(AuditEvent).count())
    return items, total
