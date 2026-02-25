> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# Memrail API Contract (v0.7, Synced 2026-02-25)

## 1. Scope and Role Split
- UI is for human review and correction.
- Agent read/write should go through API/MCP tooling, not UI operations.
- Current productionized domains: `topics`, `tasks`, `notes`, `journals`, `links`, `changes`, `context`, `audit`.
- OpenClaw integration mode: explicit user command only, no scheduled automatic write.

## 2. Implemented API Surface

### 2.1 Topics
- `GET /api/v1/topics`
  - returns active fixed taxonomy only (7 categories, ordered):
    - `top_fx_product_strategy`
    - `top_fx_engineering_arch`
    - `top_fx_operations_delivery`
    - `top_fx_growth_marketing`
    - `top_fx_finance_legal`
    - `top_fx_learning_research`
    - `top_fx_other`
  - item fields: `id, name, name_en, name_zh, kind, status, summary, created_at, updated_at`
- `POST /api/v1/topics`
  - locked in MVP fixed-taxonomy mode
  - error: `TOPIC_TAXONOMY_LOCKED` (HTTP 403)

### 2.2 Tasks
- `POST /api/v1/tasks`
  - required: `title, status, source, topic_id`
  - optional: `description, acceptance_criteria, next_action, task_type, priority, due, cycle_id, next_review_at, blocked_by_task_id, cancelled_reason`
  - rule: if `status=cancelled`, `cancelled_reason` is required
- `GET /api/v1/tasks`
  - query: `page,page_size,status,priority,archived,topic_id,cycle_id,blocked,stale_days,due_before,updated_before,view,q`
  - default excludes archived (`archived_at is null`)
  - `archived=true` returns archived set (`archived_at is not null`)
- `PATCH /api/v1/tasks/{task_id}`
  - partial update
  - status transition guard: `done/cancelled -> in_progress` blocked
- `POST /api/v1/tasks/batch-update`
  - request: `{ task_ids, patch }`
- `DELETE /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/archive-selected`
  - request: `{ task_ids }`
  - archives only tasks in `done/cancelled` and not archived
- `POST /api/v1/tasks/archive-cancelled`
  - compatibility endpoint (archive all unarchived cancelled tasks)
- `POST /api/v1/tasks/{task_id}/reopen`
  - compatibility endpoint
- `GET /api/v1/tasks/views/summary`

Task status enums:
- API status: `todo | in_progress | done | cancelled`
- UI adds virtual filter `archived` via `archived=true`

Task type enums:
- `build | research | ops | writing | decision`

Compatibility note:
- DB still has `tasks.project` column for legacy compatibility.
- Current API contract does not expose/read/write `project`.

### 2.3 Notes (Knowledge)
- `POST /api/v1/notes/append`
  - required: `title, body, sources[]`
  - optional: `topic_id, tags[]`
  - rule: `sources.length >= 1`
- `GET /api/v1/notes/search`
  - query: `page,page_size,topic_id,unclassified,status,q,tag`
  - default `status=active`
- `PATCH /api/v1/notes/{note_id}`
  - patch fields: `title, body, topic_id, tags, status`
- `DELETE /api/v1/notes/{note_id}`
- `POST /api/v1/notes/batch-classify`
  - request: `{ note_ids: string[], topic_id: string }`
  - response: `{ updated, failed, failures[] }`
- `GET /api/v1/notes/topic-summary`
  - returns counts for fixed topics + unclassified

Note status enums:
- `active | archived`

### 2.4 Journals
- `POST /api/v1/journals/upsert-append`
  - request: `{ journal_date, append_text, source }`
  - behavior: create if date not exists; otherwise append to same-day `raw_content`
- `GET /api/v1/journals`
  - query: `page,page_size,date_from,date_to`
- `GET /api/v1/journals/{journal_date}`

### 2.5 Links
- `POST /api/v1/links`
  - create relationship between `task/note`
- `DELETE /api/v1/links/{link_id}`

### 2.6 Change Governance
- `POST /api/v1/changes/dry-run`
  - persists `change_sets` + `change_actions(action_index)`
  - returns summary + diff items
- `GET /api/v1/changes`
  - query: `page,page_size,status`
- `GET /api/v1/changes/{change_set_id}`
  - returns detail: summary/diff/actions/apply results
- `POST /api/v1/changes/{change_set_id}/commit`
  - executes persisted actions in one transaction
  - idempotency by `client_request_id`
- `DELETE /api/v1/changes/{change_set_id}`
  - rejects and deletes a proposed change set
  - returns `rejected` on success
  - `404` if not found, `409` if status is not `proposed`
- `POST /api/v1/commits/undo-last`
  - reverses latest non-undo committed change set (reverse action order)

Supported action types (current):
- `create_task`
- `update_task`
- `append_note`
- `patch_note`
- `upsert_journal_append`
- `link_entities`

### 2.7 Context (Agent Read Bundle)
- `GET /api/v1/context/bundle`
  - query: `intent,window_days,topic_id,include_done,tasks_limit,notes_limit,journals_limit`
  - returns aggregated `tasks + notes + journals` for agent context retrieval

### 2.8 Audit
- `GET /api/v1/audit/events`
  - query: `page,page_size,actor_type,actor_id,tool,action,target_type,target_id,occurred_from,occurred_to`
  - returns event + chain metadata (`request_id`, `change_set_id`, `commit_id`, `action_index`, `action_type`)

## 3. Current Frontend Behavior (Synced to Code)

### 3.1 Tasks Page
- Default status filter is `in_progress`.
- Three filter dimensions: `priority`, `status`, `topic`.
- Bulk operation: only `bulk cancel` (single shared reason).
- In `done/cancelled` view, selected tasks can be archived.
- `archived` view is read-only.

### 3.2 Knowledge Page
- Topic-board layout: `topic list -> note list -> note detail`.
- Default to first non-empty topic group or unclassified.
- `unclassified` view supports multi-select batch classify.
- Archived knowledge is view-only.

### 3.3 Changes Page
- Proposal inbox mode (human does not input raw actions JSON).
- Left list = proposed change sets.
- Right detail = summary + diff + applied action ledger (after commit).
- Supports commit selected + reject selected + undo last.

### 3.4 Audit Page
- End-user audit page is hidden from navigation.
- `/audit` route redirects to `/tasks`.
- Audit APIs remain available for programmatic access.

## 4. Validation and Error Codes
- `VALIDATION_ERROR`
- `TOPIC_NOT_FOUND`
- `TOPIC_TAXONOMY_LOCKED`
- `TASK_BLOCKED_BY_NOT_FOUND`
- `TASK_BLOCKED_BY_SELF`
- `TASK_INVALID_STATUS_TRANSITION`
- `TASK_CANCEL_REASON_REQUIRED`
- `TASK_NOT_FOUND`
- `NOTE_NOT_FOUND`
- `CHANGE_SET_NOT_FOUND`
- `CHANGE_SET_NOT_PROPOSED`
- `UNAUTHORIZED`

## 5. Out of Scope / Not Implemented Yet
- Journal triage/close workflow UI and policy-level governance
- Policy engine (low-risk auto-commit / high-risk human gate)
- Multi-tenant OAuth and per-user permission isolation
- MCP server delivery (REST + skill is the current entry path)
