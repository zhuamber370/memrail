> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# MemLineage Implementation Input Pack (v0.7, Synced 2026-02-25)

## 1. Build target

Deliver a governed, reviewable, OpenClaw-first memory/task baseline with stable taxonomy and practical human review UI.

Stable domains:
- Topics (fixed taxonomy)
- Tasks (strongly-typed action items)
- Knowledge notes (classifiable/archivable)
- Journals (append-only per day)
- Change governance (`dry-run/commit/reject/undo`)
- Context bundle (agent read aggregation)
- Audit events (queryable trace)

## 2. Delivered baseline

1. Fixed 7-category topic taxonomy stored in DB with EN/ZH names
2. `POST /topics` locked in MVP mode
3. Task status governance with mandatory cancel reason on `cancelled`
4. Required `topic_id` on tasks + source tracking
5. Bulk task cancel, archive-selected, archive read-only view
6. Task delete endpoint + UI delete action
7. Knowledge topic/status support with Topic Board UI
8. Unclassified knowledge workflow + batch classify
9. Knowledge edit/archive/delete operations
10. Persisted `change_actions` with `action_index`
11. Real commit execution (task/note/link)
12. Real undo rollback (reverse order)
13. Commit/undo idempotency via `client_request_id`
14. Audit API filters by actor/tool/action/target/time
15. Changes inbox UI with commit/reject actions
16. Journals APIs (`upsert-append/list/by-date`)
17. Context bundle API (`/api/v1/context/bundle`)
18. Additional change actions: `patch_note`, `upsert_journal_append`
19. OpenClaw contract aligned to explicit-command + DB as source of truth
20. Test-data cleanup script
21. Note migration utility for topic/status backfill

## 3. Data baseline

Core tables:
- `topics`, `topic_aliases`
- `tasks`, `task_sources`, `cycles`
- `notes`, `note_sources`, `links`
- `journals`, `journal_items`
- `change_sets`, `change_actions`, `commits`
- `audit_events`

Reserved:
- `topic_entries`

Compatibility note:
- `tasks.project` remains in DB for legacy compatibility but is not used by API/UI.

## 4. Runtime baseline

- Backend: FastAPI + SQLAlchemy
- Frontend: Next.js
- DB: PostgreSQL
- Runtime schema guard: `ensure_runtime_schema`

## 5. Verification snapshot

Executed:
- Backend: `python3 -m pytest backend/tests/test_changes_api.py -q`
- Frontend: `cd frontend && npm run build`

## 6. Acceptance checklist

1. Invalid `topic_id` on task create returns `TOPIC_NOT_FOUND`
2. `cancelled` task requires `cancelled_reason`
3. Only `done/cancelled` tasks can be archived
4. Task list defaults to `in_progress` and supports priority/status/topic filters
5. Knowledge can be created without topic (`unclassified`)
6. Unclassified notes support batch classify
7. Archived knowledge is read-only
8. Changes can be reviewed and committed in UI
9. Changes can be rejected (proposal deleted)
10. Commit and undo perform real data mutations
11. Audit can trace change/commit/action chain metadata
12. Journals append to same day without duplication
13. Context bundle returns tasks+notes+journals for agent retrieval

## 7. Known gaps

1. Journal triage/close workflow not delivered
2. Advanced audit UI filters not delivered
3. Policy-based auto-approval not delivered
4. Multi-tenant OAuth/token isolation not delivered
5. MCP server not delivered (REST + skill is current path)
