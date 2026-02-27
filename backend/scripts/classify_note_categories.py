from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.config import settings
from src.db import build_engine, build_session_local, ensure_runtime_schema
from src.models import Note
from src.services.knowledge_category import infer_knowledge_category


def main() -> None:
    engine = build_engine(settings.database_url)
    ensure_runtime_schema(engine)
    session_local = build_session_local(engine)
    db = session_local()

    updated = 0
    counts: Counter[str] = Counter()

    try:
        with db.begin():
            notes = list(db.scalars(select(Note).order_by(Note.updated_at.desc(), Note.id.asc())))
            for note in notes:
                category = infer_knowledge_category(note.title or "", note.body or "")
                counts[category] += 1
                if note.category != category:
                    note.category = category
                    db.add(note)
                    updated += 1
    finally:
        db.close()

    print(f"updated_notes={updated}")
    print(f"ops_manual={counts.get('ops_manual', 0)}")
    print(f"mechanism_spec={counts.get('mechanism_spec', 0)}")
    print(f"decision_record={counts.get('decision_record', 0)}")


if __name__ == "__main__":
    main()
