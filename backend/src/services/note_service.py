from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Note, NoteSource
from src.schemas import NoteAppend

from src.services.audit_service import log_audit_event

class NoteService:
    def __init__(self, db: Session):
        self.db = db

    def append(self, payload: NoteAppend) -> Note:
        note = Note(
            id=f"nte_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            body=payload.body,
            tags_json=payload.tags,
        )
        self.db.add(note)
        self.db.flush()

        for src in payload.sources:
            self.db.add(
                NoteSource(
                    id=f"src_{uuid.uuid4().hex[:12]}",
                    note_id=note.id,
                    source_type=src.type,
                    source_value=src.value,
                )
            )

        self.db.commit()
        self.db.refresh(note)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="append_note",
            target_type="note",
            target_id=note.id,
            source_refs=[s.value for s in payload.sources],
        )
        return note

    def search(self, *, page: int, page_size: int):
        stmt = select(Note).order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.query(Note).count())
        rows = [
            {
                "id": n.id,
                "title": n.title,
                "tags": n.tags_json,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in items
        ]
        return rows, total
