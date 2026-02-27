from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import InboxItem
from src.schemas import InboxCapture

from src.services.audit_service import log_audit_event

class InboxService:
    def __init__(self, db: Session):
        self.db = db

    def capture(self, payload: InboxCapture) -> InboxItem:
        item = InboxItem(
            id=f"inb_{uuid.uuid4().hex[:12]}",
            content=payload.content,
            source=payload.source,
            status="open",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="capture_inbox",
            target_type="inbox",
            target_id=item.id,
            source_refs=[payload.source],
        )
        return item

    def list(self, *, page: int, page_size: int, status: Optional[str] = None) -> tuple[list[InboxItem], int]:
        stmt = select(InboxItem)
        count_stmt = select(func.count()).select_from(InboxItem)
        if status:
            stmt = stmt.where(InboxItem.status == status)
            count_stmt = count_stmt.where(InboxItem.status == status)
        stmt = stmt.order_by(InboxItem.captured_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def get(self, inbox_id: str) -> Optional[InboxItem]:
        return self.db.get(InboxItem, inbox_id)
