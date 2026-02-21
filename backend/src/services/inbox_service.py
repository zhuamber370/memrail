from __future__ import annotations

import uuid

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
