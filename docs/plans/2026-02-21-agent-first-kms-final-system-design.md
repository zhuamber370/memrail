> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# MemLineage Final System Design (v0.7, Synced 2026-02-25)

## 1. Product Positioning
- Product sentence: Agent-First Personal OS.
- Core value: governed long-term memory and task persistence for OpenClaw-driven workflows.
- Positioning: OpenClaw-first governance layer, not a replacement for OpenClaw memory/compaction.
- Runtime split:
  - Agent: primary writer/reader through API/MCP.
  - Human: low-frequency reviewer via UI.
- Interaction trigger:
  - write is explicit-command only (no scheduled auto write).

## 2. Architecture (Current)
- Frontend: Next.js App Router (`/tasks`, `/knowledge`, `/changes`).
- Backend: FastAPI + SQLAlchemy service layer.
- Database: PostgreSQL (single DB in MVP).
- Runtime schema guard: backend boot executes `ensure_runtime_schema()` for compatibility upgrades.
- Governance chain: `dry-run -> review diff -> commit/reject -> undo-last -> audit trail`.
- Data source strategy:
  - MemLineage DB is the only source of truth for todo/journal/topic knowledge.
  - Local notes tools are out of production write flow.

## 3. Canonical Information Model

### 3.1 Topics (Fixed Taxonomy)
- `topics` is first-class.
- Fixed 7 categories maintained in DB (EN/ZH names), `POST /topics` locked.
- Purpose: stable organization axis for task and knowledge classification.

### 3.2 Tasks (Action Items)
- Task is strictly for actionable work, not long-form dumping.
- Core fields:
  - `title, status, priority, due, source`
  - `topic_id` (required)
  - `description, acceptance_criteria, next_action, task_type`
  - `cancelled_reason` (required if cancelled)
  - `blocked_by_task_id, cycle_id, next_review_at`
  - `archived_at` (archive state)
- Status machine:
  - active states: `todo, in_progress`
  - terminal states: `done, cancelled`
  - archived is orthogonal (`archived_at`), read-only in UI
- Traceability:
  - every write keeps source in `task_sources`

### 3.3 Knowledge Notes
- `notes` store reusable knowledge entries.
- Core fields:
  - `title, body, tags_json`
  - `topic_id` nullable (null = unclassified)
  - `status` (`active|archived`)
- Traceability:
  - each note append requires `note_sources`.
- Optional relation:
  - weak links via `links` table (`task<->note`, `note<->note`).

### 3.4 Change Governance Entities
- `change_sets`: proposal-level payload and summary.
- `change_actions`: ordered executable actions (`action_index`).
- `commits`: committed result + idempotency key.
- `audit_events`: immutable event log for all write traces.

### 3.5 Journals
- `journals` is active append-only daily log domain.
- Same day uses one row (`journal_date` unique), and subsequent writes append `raw_content`.
- Current APIs:
  - `POST /api/v1/journals/upsert-append`
  - `GET /api/v1/journals`
  - `GET /api/v1/journals/{journal_date}`
- `journal_items/topic_entries` remain reserved for triage-stage expansion.

### 3.6 Agent Read Context
- `GET /api/v1/context/bundle` aggregates latest tasks/notes/journals for agent retrieval.
- Supports topic filter, done-task inclusion toggle, and configurable result limits.

## 4. Write Governance and Safety
- Dry-run persists proposed action batch and diff summary.
- Commit executes persisted actions in one transaction.
- Reject deletes a proposed change set (proposal inbox cleanup).
- Undo rolls back last committed non-undo change set in reverse action order.
- Audit logs actor/time/tool/action/target/source plus chain metadata.
- Idempotency:
  - commit/undo support `client_request_id`.

## 5. Frontend Interaction Design (Current)

### 5.1 Tasks
- Default view: `in_progress`.
- Filters: priority, status, topic.
- Batch write: bulk cancel only (shared reason mandatory).
- Archive actions only available in done/cancelled views.
- Archived list is view-only.

### 5.2 Knowledge
- Human-first board: topic groups, note list, detail pane.
- Unclassified notes can be multi-selected and batch-classified.
- Archived notes are visible under archived filter and read-only.

### 5.3 Changes
- Proposal inbox mode (no raw JSON entry for humans).
- User selects proposal, reviews summary/diff, can commit, reject, or undo-last.

### 5.4 Audit
- Audit APIs are available for agent/tooling access.
- End-user audit page is hidden from navigation and `/audit` redirects to `/tasks`.

## 6. Security and Permission Boundary (MVP)
- API key loaded from env; no key in `AGENTS.md` or skill source.
- Single-user trust boundary in MVP.
- Multi-user token isolation/OAuth is reserved for SaaS phase.
- CORS enabled for local frontend origins; write governance still enforced server-side.

## 7. Current Constraints and Non-Goals
- No graph DB in MVP; relations remain relational (`links`).
- No automatic intelligent reclassification loop yet.
- No full policy engine for risk-based auto-approve yet.
- No audit delete endpoint (audit is treated as immutable record stream).

## 8. Next Iteration Focus
1. Journal triage workflow (`journal_items` resolution + close lifecycle).
2. Optional admin-level audit UI with structured filters.
3. Policy engine for low-risk auto-commit and high-risk manual gate.
4. MCP server as standardized agent entry after REST + skill path is stable.
