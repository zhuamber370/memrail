from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from src.models import Link
from src.schemas import LinkCreate

from src.services.audit_service import log_audit_event

class LinkService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: LinkCreate) -> Link:
        link = Link(
            id=f"lnk_{uuid.uuid4().hex[:12]}",
            from_type=payload.from_type,
            from_id=payload.from_id,
            to_type=payload.to_type,
            to_id=payload.to_id,
            relation=payload.relation,
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_link",
            target_type="link",
            target_id=link.id,
        )
        return link

    def delete(self, link_id: str) -> Optional[Link]:
        link = self.db.get(Link, link_id)
        if not link:
            return None
        self.db.delete(link)
        self.db.commit()
        return link
