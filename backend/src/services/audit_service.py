from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func, select
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
    auto_commit: bool = True,
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
    if auto_commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()
    return event


def list_audit_events(
    db: Session,
    *,
    page: int,
    page_size: int,
    actor_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    tool: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    occurred_from: Optional[datetime] = None,
    occurred_to: Optional[datetime] = None,
) -> tuple[list[AuditEvent], int]:
    stmt = select(AuditEvent)
    count_stmt = select(func.count()).select_from(AuditEvent)

    if actor_type:
        stmt = stmt.where(AuditEvent.actor_type == actor_type)
        count_stmt = count_stmt.where(AuditEvent.actor_type == actor_type)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
        count_stmt = count_stmt.where(AuditEvent.actor_id == actor_id)
    if tool:
        stmt = stmt.where(AuditEvent.tool == tool)
        count_stmt = count_stmt.where(AuditEvent.tool == tool)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
        count_stmt = count_stmt.where(AuditEvent.action == action)
    if target_type:
        stmt = stmt.where(AuditEvent.target_type == target_type)
        count_stmt = count_stmt.where(AuditEvent.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
        count_stmt = count_stmt.where(AuditEvent.target_id == target_id)
    if occurred_from:
        stmt = stmt.where(AuditEvent.occurred_at >= occurred_from)
        count_stmt = count_stmt.where(AuditEvent.occurred_at >= occurred_from)
    if occurred_to:
        stmt = stmt.where(AuditEvent.occurred_at <= occurred_to)
        count_stmt = count_stmt.where(AuditEvent.occurred_at <= occurred_to)

    stmt = stmt.order_by(desc(AuditEvent.occurred_at)).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))
    total = int(db.scalar(count_stmt) or 0)
    return items, total
