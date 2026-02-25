from __future__ import annotations

from datetime import date
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Journal
from src.schemas import JournalUpsertAppendIn
from src.services.audit_service import log_audit_event


class JournalService:
    def __init__(self, db: Session):
        self.db = db

    def upsert_append(self, payload: JournalUpsertAppendIn) -> Journal:
        append_text = payload.append_text.strip()
        if not append_text:
            raise ValueError("JOURNAL_APPEND_TEXT_REQUIRED")

        journal = self.db.scalars(select(Journal).where(Journal.journal_date == payload.journal_date)).first()
        created = journal is None
        if created:
            journal = Journal(
                id=f"jrn_{uuid.uuid4().hex[:12]}",
                journal_date=payload.journal_date,
                raw_content=append_text,
                digest="",
                triage_status="open",
                source=payload.source,
            )
        else:
            assert journal is not None
            journal.raw_content = self._append_block(journal.raw_content, append_text)
            if not journal.source:
                journal.source = payload.source
        self.db.add(journal)
        self.db.commit()
        self.db.refresh(journal)

        log_audit_event(
            self.db,
            actor_type="user",
            actor_id="local",
            tool="api",
            action="create_journal" if created else "append_journal",
            target_type="journal",
            target_id=journal.id,
            source_refs=[payload.source],
        )
        return journal

    def list(
        self,
        *,
        page: int,
        page_size: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> tuple[list[Journal], int]:
        stmt = select(Journal)
        count_stmt = select(func.count()).select_from(Journal)
        if date_from:
            stmt = stmt.where(Journal.journal_date >= date_from)
            count_stmt = count_stmt.where(Journal.journal_date >= date_from)
        if date_to:
            stmt = stmt.where(Journal.journal_date <= date_to)
            count_stmt = count_stmt.where(Journal.journal_date <= date_to)

        stmt = stmt.order_by(Journal.journal_date.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt))
        total = int(self.db.scalar(count_stmt) or 0)
        return items, total

    def get_by_date(self, journal_date: date) -> Optional[Journal]:
        return self.db.scalars(select(Journal).where(Journal.journal_date == journal_date)).first()

    def _append_block(self, existing: str, addition: str) -> str:
        trimmed = existing.strip()
        if not trimmed:
            return addition
        return f"{trimmed}\n\n{addition}"
