from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
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

    def list(
        self,
        *,
        page: int,
        page_size: int,
        from_type: Optional[str] = None,
        from_id: Optional[str] = None,
        to_type: Optional[str] = None,
        to_id: Optional[str] = None,
        relation: Optional[str] = None,
    ) -> tuple[list[Link], int]:
        stmt = select(Link)
        count_stmt = select(func.count()).select_from(Link)
        if from_type:
            stmt = stmt.where(Link.from_type == from_type)
            count_stmt = count_stmt.where(Link.from_type == from_type)
        if from_id:
            stmt = stmt.where(Link.from_id == from_id)
            count_stmt = count_stmt.where(Link.from_id == from_id)
        if to_type:
            stmt = stmt.where(Link.to_type == to_type)
            count_stmt = count_stmt.where(Link.to_type == to_type)
        if to_id:
            stmt = stmt.where(Link.to_id == to_id)
            count_stmt = count_stmt.where(Link.to_id == to_id)
        if relation:
            stmt = stmt.where(Link.relation == relation)
            count_stmt = count_stmt.where(Link.relation == relation)
        stmt = stmt.order_by(Link.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def delete(self, link_id: str) -> Optional[Link]:
        link = self.db.get(Link, link_id)
        if not link:
            return None
        self.db.delete(link)
        self.db.commit()
        return link
