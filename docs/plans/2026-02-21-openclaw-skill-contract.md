> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# OpenClaw Skill Interface Contract (v0.4, Synced 2026-02-24)

## 1. Goal

Define a single entry contract between OpenClaw and Memrail so that:
- all personal knowledge/task/journal data lives in Memrail DB (single source of truth),
- all writes are governed (`dry-run -> user decision(commit/reject)`),
- agent can both write and read accumulated context.

## 2. Mandatory Runtime Rules

1. Trigger mode is explicit-command only.
- No scheduled/automatic writing.
- Write only when user clearly asks to record/update.

2. Storage boundary.
- Stop all Obsidian read/write for production flow.
- Memrail DB is the only source for todo/journal/topic knowledge.

3. Governance boundary.
- Write actions must use `propose_changes` first.
- `commit_changes` only after user confirmation.
- If user rejects proposal, call `reject_changes` (delete proposal).

4. Secret boundary.
- Keep `KMS_BASE_URL` and `KMS_API_KEY` in env/secret manager only.
- Never put secrets in AGENTS.md or skill code.

## 3. Skill Action Set

### 3.1 Write Actions (proposal-first)

1. `record_todo(...)`
- user-provided todo payload only (no auto extraction from other sources)
- maps to change actions: `create_task` or `update_task`

2. `append_journal(...)`
- appends content to same-day journal (single row per day)
- maps to change action: `upsert_journal_append`

3. `upsert_knowledge(...)`
- same-title knowledge updates by patching existing note
- maps to change actions: `append_note` (new) or `patch_note` (existing)

4. `propose_changes(actions, actor, tool)` -> `POST /api/v1/changes/dry-run`
5. `commit_changes(change_set_id, approved_by, client_request_id?)` -> `POST /api/v1/changes/{id}/commit`
6. `reject_changes(change_set_id)` -> `DELETE /api/v1/changes/{id}`
7. `undo_last_commit(requested_by, reason, client_request_id?)` -> `POST /api/v1/commits/undo-last`

### 3.2 Read Actions (agent context)

1. `list_tasks(...)` -> `GET /api/v1/tasks`
2. `search_notes(...)` -> `GET /api/v1/notes/search`
3. `list_journals(...)` -> `GET /api/v1/journals`
4. `get_journal(date)` -> `GET /api/v1/journals/{journal_date}`
5. `list_topics()` -> `GET /api/v1/topics`
6. `get_context_bundle(...)` -> `GET /api/v1/context/bundle`

## 4. API Mapping Summary

- `POST /api/v1/changes/dry-run`
- `POST /api/v1/changes/{change_set_id}/commit`
- `DELETE /api/v1/changes/{change_set_id}`
- `POST /api/v1/commits/undo-last`
- `GET /api/v1/tasks`
- `GET /api/v1/notes/search`
- `GET /api/v1/topics`
- `POST /api/v1/journals/upsert-append`
- `GET /api/v1/journals`
- `GET /api/v1/journals/{journal_date}`
- `GET /api/v1/context/bundle`

## 5. Dedupe / Upsert Policy

1. Todo dedupe candidate:
- active tasks where normalized title matches -> propose `update_task`.

2. Knowledge dedupe candidate:
- notes where normalized title matches -> propose `patch_note` with `body_append`.

3. Journal uniqueness:
- one row per `journal_date`; append to `raw_content` only.

## 6. Source and Audit Requirements

1. Every write payload must include a source ref:
- format recommendation: `chat://openclaw/{thread_id}/{message_range}`

2. Commit/undo should send `client_request_id` for idempotency.

3. Audit must remain queryable by:
- actor/tool/action/target/time
- chain metadata (`change_set_id`, `commit_id`, `action_index`).

## 7. Error and Retry Strategy

- `400/401/403/404/422`: no retry
- `409`: one retry after re-read
- `429`: exponential backoff, max 3 retries
- `500`: exponential backoff, max 2 retries
