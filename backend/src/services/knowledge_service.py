from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Text, func, or_, select
from sqlalchemy.orm import Session

from src.models import KnowledgeEvidence, KnowledgeItem, Note, NoteSource, Topic
from src.schemas import KnowledgeCreate, KnowledgeEvidenceIn, KnowledgePatch
from src.services.audit_service import log_audit_event

MIGRATION_BATCH_LIMIT = 20
NOTE_EVIDENCE_PREFIX = "note://"


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: KnowledgeCreate) -> dict:
        if payload.topic_id:
            self._validate_topic(payload.topic_id)
        self._validate_content(payload.type, payload.content)
        if not payload.evidences:
            raise ValueError("KNOWLEDGE_EVIDENCE_REQUIRED")

        item = KnowledgeItem(
            id=f"kng_{uuid.uuid4().hex[:12]}",
            type=payload.type,
            title=payload.title,
            topic_id=payload.topic_id,
            tags_json=payload.tags,
            status="active",
            content_json=payload.content,
        )
        self.db.add(item)
        self.db.flush()

        for evidence in payload.evidences:
            self.db.add(
                KnowledgeEvidence(
                    id=f"kbe_{uuid.uuid4().hex[:12]}",
                    item_id=item.id,
                    source_ref=evidence.source_ref,
                    excerpt=evidence.excerpt,
                )
            )

        self.db.commit()
        self.db.refresh(item)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_knowledge_item",
            target_type="knowledge_item",
            target_id=item.id,
            source_refs=[e.source_ref for e in payload.evidences],
        )
        return self.get(item.id) or {}

    def list(
        self,
        *,
        page: int,
        page_size: int,
        type: Optional[str] = None,
        topic_id: Optional[str] = None,
        status: str = "active",
        q: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        stmt = select(KnowledgeItem)
        count_stmt = select(func.count()).select_from(KnowledgeItem)

        if status:
            stmt = stmt.where(KnowledgeItem.status == status)
            count_stmt = count_stmt.where(KnowledgeItem.status == status)
        if type:
            stmt = stmt.where(KnowledgeItem.type == type)
            count_stmt = count_stmt.where(KnowledgeItem.type == type)
        if topic_id:
            stmt = stmt.where(KnowledgeItem.topic_id == topic_id)
            count_stmt = count_stmt.where(KnowledgeItem.topic_id == topic_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    KnowledgeItem.title.ilike(like),
                    KnowledgeItem.content_json.cast(Text).ilike(like),
                )
            )
            count_stmt = count_stmt.where(
                or_(
                    KnowledgeItem.title.ilike(like),
                    KnowledgeItem.content_json.cast(Text).ilike(like),
                )
            )
        if tag:
            tag_like = f'%"{tag}"%'
            stmt = stmt.where(KnowledgeItem.tags_json.cast(Text).ilike(tag_like))
            count_stmt = count_stmt.where(KnowledgeItem.tags_json.cast(Text).ilike(tag_like))

        stmt = stmt.order_by(KnowledgeItem.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        evidence_count_map = self._build_evidence_count_map([item.id for item in items])
        rows = [
            {
                "id": item.id,
                "type": item.type,
                "title": item.title,
                "topic_id": item.topic_id,
                "tags": item.tags_json or [],
                "status": item.status,
                "evidence_count": evidence_count_map.get(item.id, 0),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ]
        return rows, total

    def get(self, item_id: str) -> Optional[dict]:
        item = self.db.get(KnowledgeItem, item_id)
        if not item:
            return None
        evidences = list(
            self.db.scalars(
                select(KnowledgeEvidence)
                .where(KnowledgeEvidence.item_id == item_id)
                .order_by(KnowledgeEvidence.created_at.asc(), KnowledgeEvidence.id.asc())
            )
        )
        return {
            "id": item.id,
            "type": item.type,
            "title": item.title,
            "topic_id": item.topic_id,
            "tags": item.tags_json or [],
            "status": item.status,
            "content": item.content_json or {},
            "evidence_count": len(evidences),
            "evidences": [
                {
                    "id": ev.id,
                    "item_id": ev.item_id,
                    "source_ref": ev.source_ref,
                    "excerpt": ev.excerpt,
                    "created_at": ev.created_at,
                }
                for ev in evidences
            ],
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def patch(self, item_id: str, payload: KnowledgePatch) -> Optional[dict]:
        item = self.db.get(KnowledgeItem, item_id)
        if not item:
            return None

        patch_data = payload.model_dump(exclude_unset=True)
        if not patch_data:
            raise ValueError("NO_PATCH_FIELDS")
        if "topic_id" in patch_data and patch_data["topic_id"] is not None:
            self._validate_topic(patch_data["topic_id"])
        if "content" in patch_data:
            self._validate_content(item.type, patch_data["content"])
            item.content_json = patch_data.pop("content")
        if "tags" in patch_data:
            item.tags_json = patch_data.pop("tags") or []

        for key, value in patch_data.items():
            setattr(item, key, value)

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="patch_knowledge_item",
            target_type="knowledge_item",
            target_id=item.id,
            source_refs=[],
        )
        return self.get(item.id)

    def archive(self, item_id: str) -> Optional[dict]:
        item = self.db.get(KnowledgeItem, item_id)
        if not item:
            return None
        if item.status != "archived":
            item.status = "archived"
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            log_audit_event(
                self.db,
                actor_type="user",
                actor_id="local",
                tool="api",
                action="archive_knowledge_item",
                target_type="knowledge_item",
                target_id=item.id,
                source_refs=[],
            )
        return self.get(item.id)

    def append_evidence(self, item_id: str, payload: KnowledgeEvidenceIn) -> Optional[dict]:
        item = self.db.get(KnowledgeItem, item_id)
        if not item:
            return None
        evidence = KnowledgeEvidence(
            id=f"kbe_{uuid.uuid4().hex[:12]}",
            item_id=item.id,
            source_ref=payload.source_ref,
            excerpt=payload.excerpt,
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="append_knowledge_evidence",
            target_type="knowledge_item",
            target_id=item.id,
            source_refs=[payload.source_ref],
        )
        return {
            "id": evidence.id,
            "item_id": evidence.item_id,
            "source_ref": evidence.source_ref,
            "excerpt": evidence.excerpt,
            "created_at": evidence.created_at,
        }

    def delete(self, item_id: str) -> bool:
        item = self.db.get(KnowledgeItem, item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="delete_knowledge_item",
            target_type="knowledge_item",
            target_id=item_id,
            source_refs=[],
        )
        return True

    def list_migration_candidates(self, *, page: int, page_size: int) -> tuple[list[dict], int]:
        notes = list(
            self.db.scalars(
                select(Note).where(Note.status == "active").order_by(Note.updated_at.desc(), Note.id.asc())
            )
        )
        migrated_note_ids = self._load_migrated_note_ids()
        pending_notes = [note for note in notes if note.id not in migrated_note_ids]

        total = len(pending_notes)
        start = (page - 1) * page_size
        selected_notes = pending_notes[start : start + page_size]
        source_map = self._build_note_source_map([note.id for note in selected_notes])

        rows: list[dict] = []
        for note in selected_notes:
            inferred_type = self._infer_note_type(note)
            content = self._build_note_content(note, inferred_type)
            evidences = self._build_note_evidences(note, source_map.get(note.id, []))
            rows.append(
                {
                    "note_id": note.id,
                    "title": note.title,
                    "topic_id": note.topic_id,
                    "tags": self._normalize_tags(note.tags_json),
                    "inferred_type": inferred_type,
                    "content": content,
                    "evidences": evidences,
                }
            )
        return rows, total

    def commit_migration(self, *, note_ids: list[str]) -> dict:
        ordered_ids = list(dict.fromkeys(note_ids))
        if len(ordered_ids) > MIGRATION_BATCH_LIMIT:
            raise ValueError("MIGRATION_BATCH_TOO_LARGE")

        notes = list(self.db.scalars(select(Note).where(Note.id.in_(ordered_ids), Note.status == "active")))
        note_map = {note.id: note for note in notes}
        source_map = self._build_note_source_map(ordered_ids)
        migrated_note_ids = self._load_migrated_note_ids()

        migrated = 0
        skipped = 0
        failures: list[dict[str, str]] = []
        migrations: list[dict[str, str]] = []

        for note_id in ordered_ids:
            if note_id in migrated_note_ids:
                skipped += 1
                continue
            note = note_map.get(note_id)
            if note is None:
                failures.append({"note_id": note_id, "reason": "NOTE_NOT_FOUND_OR_INACTIVE"})
                continue

            inferred_type = self._infer_note_type(note)
            content = self._build_note_content(note, inferred_type)
            evidences = self._build_note_evidences(note, source_map.get(note.id, []))
            if not evidences:
                failures.append({"note_id": note_id, "reason": "KNOWLEDGE_EVIDENCE_REQUIRED"})
                continue

            self._validate_content(inferred_type, content)
            item = KnowledgeItem(
                id=f"kng_{uuid.uuid4().hex[:12]}",
                type=inferred_type,
                title=note.title,
                topic_id=note.topic_id,
                tags_json=self._normalize_tags(note.tags_json),
                status="active",
                content_json=content,
            )
            self.db.add(item)
            self.db.flush()
            for evidence in evidences:
                self.db.add(
                    KnowledgeEvidence(
                        id=f"kbe_{uuid.uuid4().hex[:12]}",
                        item_id=item.id,
                        source_ref=evidence["source_ref"],
                        excerpt=evidence["excerpt"],
                    )
                )
            migrations.append({"note_id": note.id, "item_id": item.id})
            migrated += 1

        if migrated:
            self.db.commit()
            for row in migrations:
                log_audit_event(
                    self.db,
                    actor_type="user",
                    actor_id="local",
                    tool="api",
                    action="migrate_note_to_knowledge_item",
                    target_type="knowledge_item",
                    target_id=row["item_id"],
                    source_refs=[f"{NOTE_EVIDENCE_PREFIX}{row['note_id']}"],
                    metadata={"note_id": row["note_id"]},
                    auto_commit=False,
                )
            self.db.commit()

        return {
            "migrated": migrated,
            "skipped": skipped,
            "failed": len(failures),
            "failures": failures,
            "migrations": migrations,
        }

    def _build_evidence_count_map(self, item_ids: list[str]) -> dict[str, int]:
        if not item_ids:
            return {}
        rows = list(
            self.db.execute(
                select(KnowledgeEvidence.item_id, func.count())
                .where(KnowledgeEvidence.item_id.in_(item_ids))
                .group_by(KnowledgeEvidence.item_id)
            ).all()
        )
        return {row[0]: int(row[1]) for row in rows}

    def _build_note_source_map(self, note_ids: list[str]) -> dict[str, list[NoteSource]]:
        if not note_ids:
            return {}
        rows = list(
            self.db.scalars(
                select(NoteSource)
                .where(NoteSource.note_id.in_(note_ids))
                .order_by(NoteSource.note_id.asc(), NoteSource.id.asc())
            )
        )
        mapped: dict[str, list[NoteSource]] = {note_id: [] for note_id in note_ids}
        for row in rows:
            mapped.setdefault(row.note_id, []).append(row)
        return mapped

    def _load_migrated_note_ids(self) -> set[str]:
        refs = list(
            self.db.scalars(
                select(KnowledgeEvidence.source_ref).where(KnowledgeEvidence.source_ref.like(f"{NOTE_EVIDENCE_PREFIX}%"))
            )
        )
        note_ids: set[str] = set()
        for ref in refs:
            if not isinstance(ref, str):
                continue
            if not ref.startswith(NOTE_EVIDENCE_PREFIX):
                continue
            note_id = ref[len(NOTE_EVIDENCE_PREFIX) :].strip()
            if note_id:
                note_ids.add(note_id)
        return note_ids

    def _infer_note_type(self, note: Note) -> str:
        text = f"{note.title}\n{note.body}".lower()
        decision_keywords = [
            "decision",
            "decide",
            "rationale",
            "tradeoff",
            "trade-off",
            "决策",
            "决定",
            "取舍",
        ]
        playbook_keywords = [
            "playbook",
            "runbook",
            "sop",
            "checklist",
            "steps",
            "流程",
            "步骤",
            "操作",
        ]
        if any(keyword in text for keyword in decision_keywords):
            return "decision"
        if any(keyword in text for keyword in playbook_keywords):
            return "playbook"
        return "brief"

    def _build_note_content(self, note: Note, inferred_type: str) -> dict:
        title = (note.title or "").strip() or "Untitled"
        body = (note.body or "").strip()
        if inferred_type == "decision":
            rationale = body or f"Decision record for {title}"
            return {"decision": title, "rationale": rationale}
        if inferred_type == "playbook":
            steps = self._extract_steps(body)
            return {"goal": title, "steps": steps}
        summary = body or title
        highlights = self._extract_highlights(body, fallback=title)
        return {"summary": summary, "highlights": highlights}

    def _build_note_evidences(self, note: Note, sources: list[NoteSource]) -> list[dict[str, str]]:
        excerpt = self._build_excerpt(note.body)
        seen_refs: set[str] = set()
        evidences: list[dict[str, str]] = []

        root_ref = f"{NOTE_EVIDENCE_PREFIX}{note.id}"
        seen_refs.add(root_ref)
        evidences.append({"source_ref": root_ref, "excerpt": excerpt})

        for source in sources:
            source_ref = (source.source_value or "").strip()
            if not source_ref or source_ref in seen_refs:
                continue
            evidences.append({"source_ref": source_ref, "excerpt": excerpt})
            seen_refs.add(source_ref)
        return evidences

    def _build_excerpt(self, body: str) -> str:
        text = " ".join((body or "").strip().split())
        if not text:
            return "Imported from note migration."
        if len(text) <= 240:
            return text
        return f"{text[:237]}..."

    def _extract_steps(self, body: str) -> list[str]:
        lines = [(line or "").strip() for line in (body or "").splitlines()]
        cleaned: list[str] = []
        for line in lines:
            if not line:
                continue
            if line.startswith("-") or line.startswith("*"):
                line = line[1:].strip()
            if len(line) > 2 and line[0].isdigit() and line[1] in [".", "、", ")"]:
                line = line[2:].strip()
            if line:
                cleaned.append(line)
        if cleaned:
            return cleaned[:8]
        fallback = (body or "").strip()
        if fallback:
            return [fallback[:120]]
        return ["Review and execute."]

    def _extract_highlights(self, body: str, *, fallback: str) -> list[str]:
        lines = [(line or "").strip() for line in (body or "").splitlines() if (line or "").strip()]
        highlights: list[str] = []
        for line in lines:
            normalized = line
            if normalized.startswith("-") or normalized.startswith("*"):
                normalized = normalized[1:].strip()
            if normalized:
                highlights.append(normalized)
            if len(highlights) >= 5:
                break
        if highlights:
            return highlights
        return [fallback]

    def _normalize_tags(self, tags: object) -> list[str]:
        if not isinstance(tags, list):
            return []
        normalized: list[str] = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            stripped = tag.strip()
            if stripped:
                normalized.append(stripped)
        return normalized

    def _validate_topic(self, topic_id: str) -> None:
        if self.db.get(Topic, topic_id) is None:
            raise ValueError("TOPIC_NOT_FOUND")

    def _validate_content(self, item_type: str, content: dict) -> None:
        if not isinstance(content, dict):
            raise ValueError("KNOWLEDGE_CONTENT_INVALID")
        if item_type == "playbook":
            goal = content.get("goal")
            steps = content.get("steps")
            if not isinstance(goal, str) or not goal.strip():
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            if not isinstance(steps, list) or not steps or any(not isinstance(step, str) or not step.strip() for step in steps):
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            return
        if item_type == "decision":
            decision = content.get("decision")
            rationale = content.get("rationale")
            if not isinstance(decision, str) or not decision.strip():
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            if not isinstance(rationale, str) or not rationale.strip():
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            return
        if item_type == "brief":
            summary = content.get("summary")
            highlights = content.get("highlights")
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            if not isinstance(highlights, list) or not highlights or any(
                not isinstance(highlight, str) or not highlight.strip() for highlight in highlights
            ):
                raise ValueError("KNOWLEDGE_CONTENT_INVALID")
            return
        raise ValueError("KNOWLEDGE_TYPE_INVALID")
