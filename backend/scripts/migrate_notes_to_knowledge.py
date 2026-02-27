from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.config import Settings
from src.db import build_engine, build_session_local, ensure_runtime_schema
from src.services.knowledge_service import MIGRATION_BATCH_LIMIT, KnowledgeService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate legacy notes into knowledge_items in controlled batches."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute migration writes. Without this flag the script only previews candidates.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help=f"Batch size per migration run (max {MIGRATION_BATCH_LIMIT}).",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Optional hard cap on batches processed in apply mode (0 means no cap).",
    )
    return parser.parse_args()


def _print_candidate(row: dict) -> None:
    print(
        f"- note_id={row['note_id']} type={row['inferred_type']} "
        f"title={row['title'][:80]}"
    )


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.batch_size > MIGRATION_BATCH_LIMIT:
        raise ValueError(f"batch-size must be between 1 and {MIGRATION_BATCH_LIMIT}")
    if args.max_batches < 0:
        raise ValueError("max-batches must be >= 0")

    settings = Settings()
    engine = build_engine(settings.database_url)
    ensure_runtime_schema(engine)
    session_local = build_session_local(engine)

    with session_local() as db:
        service = KnowledgeService(db)
        preview_items, pending_total = service.list_migration_candidates(page=1, page_size=args.batch_size)

        print(f"database_url={settings.database_url}")
        print(f"pending_total={pending_total}")
        if not preview_items:
            print("nothing_to_migrate=true")
            return

        if not args.apply:
            print("mode=dry-run")
            print(f"preview_count={len(preview_items)}")
            for row in preview_items:
                _print_candidate(row)
            return

        total_migrated = 0
        total_skipped = 0
        total_failed = 0
        batches = 0

        while True:
            if args.max_batches and batches >= args.max_batches:
                break
            items, _ = service.list_migration_candidates(page=1, page_size=args.batch_size)
            if not items:
                break
            requested_ids = [item["note_id"] for item in items]
            result = service.commit_migration(note_ids=requested_ids)
            batches += 1
            total_migrated += int(result["migrated"])
            total_skipped += int(result["skipped"])
            total_failed += int(result["failed"])
            print(
                f"batch={batches} requested={len(requested_ids)} "
                f"migrated={result['migrated']} skipped={result['skipped']} failed={result['failed']}"
            )
            for failure in result["failures"]:
                print(f"  failure note_id={failure['note_id']} reason={failure['reason']}")
            if result["migrated"] == 0 and result["failed"] == 0:
                break

        _, remaining = service.list_migration_candidates(page=1, page_size=args.batch_size)
        print(f"batches={batches}")
        print(f"total_migrated={total_migrated}")
        print(f"total_skipped={total_skipped}")
        print(f"total_failed={total_failed}")
        print(f"remaining_pending={remaining}")


if __name__ == "__main__":
    main()
