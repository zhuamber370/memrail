from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from src.models import Link, Note
from src.schemas import KnowledgeCreate, KnowledgePatch
from src.services.knowledge_category import infer_knowledge_category
from src.services.audit_service import log_audit_event


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: KnowledgeCreate) -> dict:
        resolved_category = payload.category or infer_knowledge_category(payload.title, payload.body)
        note = Note(
            id=f"nte_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            body=payload.body,
            category=resolved_category,
            topic_id=None,
            tags_json=[],
            status="active",
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_knowledge_note",
            target_type="note",
            target_id=note.id,
            source_refs=[],
        )
        return self.get(note.id) or {}

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: str = "active",
        category: Optional[str] = None,
        q: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(Note)
        count_stmt = select(func.count()).select_from(Note)

        if status:
            stmt = stmt.where(Note.status == status)
            count_stmt = count_stmt.where(Note.status == status)
        if category:
            stmt = stmt.where(Note.category == category)
            count_stmt = count_stmt.where(Note.category == category)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Note.title.ilike(like), Note.body.ilike(like)))
            count_stmt = count_stmt.where(or_(Note.title.ilike(like), Note.body.ilike(like)))

        stmt = stmt.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        notes = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        rows = [
            {
                "id": note.id,
                "title": note.title,
                "body": note.body,
                "category": note.category,
                "status": note.status,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
            }
            for note in notes
        ]
        return rows, total

    def get(self, item_id: str) -> Optional[dict]:
        note = self.db.get(Note, item_id)
        if not note:
            return None
        return {
            "id": note.id,
            "title": note.title,
            "body": note.body,
            "category": note.category,
            "status": note.status,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }

    def patch(self, item_id: str, payload: KnowledgePatch) -> Optional[dict]:
        note = self.db.get(Note, item_id)
        if not note:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")

        for key, value in patch_data.items():
            setattr(note, key, value)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="patch_knowledge_note",
            target_type="note",
            target_id=note.id,
            source_refs=[],
        )
        return self.get(note.id)

    def archive(self, item_id: str) -> Optional[dict]:
        note = self.db.get(Note, item_id)
        if not note:
            return None
        if note.status != "archived":
            note.status = "archived"
            self.db.add(note)
            self.db.commit()
            self.db.refresh(note)
            log_audit_event(
                self.db,
                actor_type="user",
                actor_id="local",
                tool="api",
                action="archive_knowledge_note",
                target_type="note",
                target_id=note.id,
                source_refs=[],
            )
        return self.get(note.id)

    def delete(self, item_id: str) -> bool:
        note = self.db.get(Note, item_id)
        if not note:
            return False
        self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.from_type == "note", Link.from_id == item_id),
                    and_(Link.to_type == "note", Link.to_id == item_id),
                )
            )
        )
        self.db.delete(note)
        self.db.commit()
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="delete_knowledge_note",
            target_type="note",
            target_id=item_id,
            source_refs=[],
        )
        return True
