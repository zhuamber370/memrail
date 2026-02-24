from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Journal, Note, Task


class ContextService:
    def __init__(self, db: Session):
        self.db = db

    def bundle(
        self,
        *,
        intent: str,
        window_days: int,
        topic_ids: Optional[list[str]],
        include_done: bool,
        tasks_limit: int,
        notes_limit: int,
        journals_limit: int,
    ) -> dict:
        since = datetime.now(timezone.utc).date() - timedelta(days=max(window_days - 1, 0))
        topics = [topic_id for topic_id in (topic_ids or []) if topic_id]

        tasks_stmt = select(Task).where(Task.archived_at.is_(None))
        if not include_done:
            tasks_stmt = tasks_stmt.where(Task.status.notin_(["done", "cancelled"]))
        if topics:
            tasks_stmt = tasks_stmt.where(Task.topic_id.in_(topics))
        tasks_stmt = tasks_stmt.order_by(Task.updated_at.desc()).limit(tasks_limit)
        task_rows = list(self.db.scalars(tasks_stmt))

        notes_stmt = select(Note).where(Note.status == "active")
        if topics:
            notes_stmt = notes_stmt.where(Note.topic_id.in_(topics))
        notes_stmt = notes_stmt.order_by(Note.updated_at.desc()).limit(notes_limit)
        note_rows = list(self.db.scalars(notes_stmt))

        journals_stmt = (
            select(Journal)
            .where(Journal.journal_date >= since)
            .order_by(Journal.journal_date.desc(), Journal.updated_at.desc())
            .limit(journals_limit)
        )
        journal_rows = list(self.db.scalars(journals_stmt))

        return {
            "intent": intent,
            "window_days": window_days,
            "filters": {
                "topic_ids": topics,
                "include_done": include_done,
                "tasks_limit": tasks_limit,
                "notes_limit": notes_limit,
                "journals_limit": journals_limit,
            },
            "summary": {
                "tasks": len(task_rows),
                "notes": len(note_rows),
                "journals": len(journal_rows),
            },
            "tasks": [
                {
                    "id": row.id,
                    "title": row.title,
                    "status": row.status,
                    "priority": row.priority,
                    "topic_id": row.topic_id,
                    "due": row.due.isoformat() if row.due else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in task_rows
            ],
            "notes": [
                {
                    "id": row.id,
                    "title": row.title,
                    "topic_id": row.topic_id,
                    "status": row.status,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "tags": row.tags_json,
                }
                for row in note_rows
            ],
            "journals": [
                {
                    "id": row.id,
                    "journal_date": row.journal_date.isoformat(),
                    "raw_content": row.raw_content,
                    "digest": row.digest,
                    "triage_status": row.triage_status,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in journal_rows
            ],
        }
