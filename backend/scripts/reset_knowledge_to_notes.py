from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import delete, select

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.config import settings
from src.db import build_engine, build_session_local, ensure_runtime_schema
from src.models import KnowledgeEvidence, KnowledgeItem, Note
from src.services.knowledge_category import infer_knowledge_category


def _content_to_body(content: object) -> str:
    if not isinstance(content, dict):
        return ""
    ordered_keys = ["decision", "rationale", "goal", "steps", "summary", "highlights"]
    lines: list[str] = []
    for key in ordered_keys:
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    lines.append(item.strip())
    return "\n".join(lines).strip()


def main() -> None:
    engine = build_engine(settings.database_url)
    ensure_runtime_schema(engine)
    session_local = build_session_local(engine)
    db = session_local()

    inserted = 0
    skipped_existing = 0
    cleared_items = 0
    cleared_evidences = 0

    try:
        with db.begin():
            knowledge_items = list(
                db.scalars(
                    select(KnowledgeItem)
                    .where(KnowledgeItem.status == "active")
                    .order_by(KnowledgeItem.updated_at.desc(), KnowledgeItem.id.asc())
                )
            )

            for item in knowledge_items:
                exists_note = db.scalar(
                    select(Note.id).where(Note.status == "active", Note.title == item.title).limit(1)
                )
                if exists_note:
                    skipped_existing += 1
                    continue

                body = _content_to_body(item.content_json)
                if not body:
                    body = item.title

                db.add(
                    Note(
                        id=f"nte_{uuid.uuid4().hex[:12]}",
                        title=item.title,
                        body=body,
                        category=infer_knowledge_category(item.title, body),
                        topic_id=None,
                        tags_json=[],
                        status="active",
                    )
                )
                inserted += 1

            cleared_evidences = db.execute(delete(KnowledgeEvidence)).rowcount or 0
            cleared_items = db.execute(delete(KnowledgeItem)).rowcount or 0
    finally:
        db.close()

    print(f"inserted_notes={inserted}")
    print(f"skipped_existing_titles={skipped_existing}")
    print(f"cleared_knowledge_evidences={cleared_evidences}")
    print(f"cleared_knowledge_items={cleared_items}")


if __name__ == "__main__":
    main()
