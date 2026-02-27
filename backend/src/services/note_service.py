from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Text, and_, case, delete, func, or_, select
from sqlalchemy.orm import Session

from src.models import Link, Note, NoteSource, Topic
from src.schemas import NoteAppend, NotePatch

from src.services.audit_service import log_audit_event

FIXED_TOPIC_ORDER = [
    "top_fx_product_strategy",
    "top_fx_engineering_arch",
    "top_fx_operations_delivery",
    "top_fx_growth_marketing",
    "top_fx_finance_legal",
    "top_fx_learning_research",
    "top_fx_other",
]


class NoteService:
    def __init__(self, db: Session):
        self.db = db

    def append(self, payload: NoteAppend) -> Note:
        if payload.topic_id:
            self._validate_topic(payload.topic_id)
        note = Note(
            id=f"nte_{uuid.uuid4().hex[:12]}",
            title=payload.title,
            body=payload.body,
            tags_json=payload.tags,
            topic_id=payload.topic_id,
            status="active",
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

    def search(
        self,
        *,
        page: int,
        page_size: int,
        topic_id: Optional[str] = None,
        unclassified: bool = False,
        status: str = "active",
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ):
        stmt = select(Note)
        count_stmt = select(func.count()).select_from(Note)

        if status:
            stmt = stmt.where(Note.status == status)
            count_stmt = count_stmt.where(Note.status == status)
        if unclassified:
            stmt = stmt.where(Note.topic_id.is_(None))
            count_stmt = count_stmt.where(Note.topic_id.is_(None))
        elif topic_id:
            stmt = stmt.where(Note.topic_id == topic_id)
            count_stmt = count_stmt.where(Note.topic_id == topic_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Note.title.ilike(like), Note.body.ilike(like)))
            count_stmt = count_stmt.where(or_(Note.title.ilike(like), Note.body.ilike(like)))
        if tag:
            # tags_json is a JSON array; text match is sufficient for MVP filter.
            tag_like = f'%"{tag}"%'
            stmt = stmt.where(Note.tags_json.cast(Text).ilike(tag_like))
            count_stmt = count_stmt.where(Note.tags_json.cast(Text).ilike(tag_like))

        stmt = stmt.order_by(Note.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        note_ids = [n.id for n in items]
        source_count_map = self._build_source_count_map(note_ids)
        source_items_map = self._build_source_items_map(note_ids)
        linked_map = self._build_linked_map(note_ids)
        rows = [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "tags": n.tags_json,
                "topic_id": n.topic_id,
                "status": n.status,
                "source_count": source_count_map.get(n.id, 0),
                "sources": source_items_map.get(n.id, []),
                "linked_task_ids": linked_map.get(n.id, {}).get("task_ids", []),
                "linked_note_ids": linked_map.get(n.id, {}).get("note_ids", []),
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in items
        ]
        return rows, total

    def patch(self, note_id: str, payload: NotePatch) -> Optional[Note]:
        note = self.db.get(Note, note_id)
        if not note:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            self._validate_topic(patch_data["topic_id"])

        if "tags" in patch_data:
            note.tags_json = patch_data.pop("tags") or []
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
            action="patch_note",
            target_type="note",
            target_id=note.id,
            source_refs=[],
        )
        return note

    def delete(self, note_id: str) -> bool:
        note = self.db.get(Note, note_id)
        if not note:
            return False

        source_refs = [src.source_value for src in self.db.scalars(select(NoteSource).where(NoteSource.note_id == note_id))]
        self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.from_type == "note", Link.from_id == note_id),
                    and_(Link.to_type == "note", Link.to_id == note_id),
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
            action="delete_note",
            target_type="note",
            target_id=note_id,
            source_refs=source_refs,
        )
        return True

    def list_sources(self, note_id: str) -> list[NoteSource]:
        if self.db.get(Note, note_id) is None:
            raise ValueError("NOTE_NOT_FOUND")
        return list(
            self.db.scalars(
                select(NoteSource)
                .where(NoteSource.note_id == note_id)
                .order_by(NoteSource.id.asc())
            )
        )

    def batch_classify(self, note_ids: list[str], topic_id: str) -> dict:
        self._validate_topic(topic_id)
        unique_ids = list(dict.fromkeys(note_ids))
        if not unique_ids:
            return {"updated": 0, "failed": 0, "failures": []}
        notes = list(self.db.scalars(select(Note).where(Note.id.in_(unique_ids))))
        note_map = {n.id: n for n in notes}
        updated = 0
        failures: list[dict[str, str]] = []
        for note_id in unique_ids:
            note = note_map.get(note_id)
            if note is None:
                failures.append({"note_id": note_id, "reason": "NOTE_NOT_FOUND"})
                continue
            note.topic_id = topic_id
            self.db.add(note)
            updated += 1
        self.db.commit()
        if updated:
            log_audit_event(
                self.db,
                actor_type="user",
                actor_id="local",
                tool="api",
                action="batch_classify_note",
                target_type="note_batch",
                target_id=f"classified:{updated}",
                source_refs=[],
            )
        return {"updated": updated, "failed": len(failures), "failures": failures}

    def topic_summary(self, *, status: str = "active") -> list[dict]:
        count_stmt = select(Note.topic_id, func.count()).group_by(Note.topic_id)
        if status:
            count_stmt = count_stmt.where(Note.status == status)
        rows = list(self.db.execute(count_stmt).all())
        counts = {row[0]: int(row[1]) for row in rows}

        ordering = case(
            *[(Topic.id == topic_id, idx) for idx, topic_id in enumerate(FIXED_TOPIC_ORDER, start=1)],
            else_=999,
        )
        topics = list(
            self.db.scalars(
                select(Topic).where(Topic.status == "active").order_by(ordering, Topic.name_en.asc())
            )
        )
        items = [
            {
                "topic_id": topic.id,
                "topic_name": topic.name_en,
                "count": counts.get(topic.id, 0),
            }
            for topic in topics
        ]
        items.append(
            {
                "topic_id": None,
                "topic_name": "Unclassified",
                "count": counts.get(None, 0),
            }
        )
        return items

    def _build_source_count_map(self, note_ids: list[str]) -> dict[str, int]:
        if not note_ids:
            return {}
        rows = list(
            self.db.execute(
                select(NoteSource.note_id, func.count())
                .where(NoteSource.note_id.in_(note_ids))
                .group_by(NoteSource.note_id)
            ).all()
        )
        return {row[0]: int(row[1]) for row in rows}

    def _build_source_items_map(self, note_ids: list[str]) -> dict[str, list[dict[str, str]]]:
        if not note_ids:
            return {}
        rows = list(
            self.db.execute(
                select(NoteSource.note_id, NoteSource.source_type, NoteSource.source_value)
                .where(NoteSource.note_id.in_(note_ids))
                .order_by(NoteSource.note_id.asc())
            ).all()
        )
        mapped: dict[str, list[dict[str, str]]] = {note_id: [] for note_id in note_ids}
        for note_id, source_type, source_value in rows:
            mapped.setdefault(note_id, []).append({"type": source_type, "value": source_value})
        return mapped

    def _build_linked_map(self, note_ids: list[str]) -> dict[str, dict[str, list[str]]]:
        if not note_ids:
            return {}
        rows = list(
            self.db.scalars(
                select(Link).where(
                    or_(
                        and_(Link.from_type == "note", Link.from_id.in_(note_ids)),
                        and_(Link.to_type == "note", Link.to_id.in_(note_ids)),
                    )
                )
            )
        )
        mapped: dict[str, dict[str, list[str]]] = {
            note_id: {"task_ids": [], "note_ids": []} for note_id in note_ids
        }
        for row in rows:
            if row.from_type == "note":
                note_id = row.from_id
                other_type = row.to_type
                other_id = row.to_id
            else:
                note_id = row.to_id
                other_type = row.from_type
                other_id = row.from_id
            if note_id not in mapped:
                continue
            if other_type == "task":
                mapped[note_id]["task_ids"].append(other_id)
            elif other_type == "note":
                mapped[note_id]["note_ids"].append(other_id)
        return mapped

    def _validate_topic(self, topic_id: str) -> None:
        if self.db.get(Topic, topic_id) is None:
            raise ValueError("TOPIC_NOT_FOUND")
