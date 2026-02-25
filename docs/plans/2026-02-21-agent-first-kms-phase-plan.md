# Agent-First KMS Phase Plan Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver Agent-First KMS MVP end-to-end (backend, API, skill, frontend) with task-management enhancements and governed write operations.

**Architecture:** Cloud-style REST API as the single write center. Web UI and OpenClaw skill share the same service surface. Batch writes follow governed flow (`dry-run/diff/commit/reject/undo/audit`) with conservative dedupe.

**Tech Stack:** Next.js + TypeScript + Tailwind + TanStack Query; FastAPI + Pydantic + SQLAlchemy + Alembic; PostgreSQL.

---

## Phase overview

1. Phase 1: Task domain model and base APIs
2. Phase 2: Governance chain and audit closure
3. Phase 3: OpenClaw skill contract alignment
4. Phase 4: Frontend interaction closure and release validation

## Phase 1: Task domain model and base APIs

**Scope**
- Add task fields: `cycle_id`, `next_review_at`, `blocked_by_task_id`, `archived_at`
- Add cycle model
- Expand query views and batch updates for tasks

**Tasks**
1. Extend `tasks` schema and indexes
2. Add `cycles` schema and indexes
3. Extend `POST /tasks`, `GET /tasks`, `PATCH /tasks/{task_id}`
4. Add `POST /tasks/batch-update`, `POST /tasks/{task_id}/reopen`, `GET /tasks/views/summary`
5. Add `POST /cycles`, `GET /cycles`

**DoD**
1. Views `today|overdue|this_week|backlog|blocked|done` queryable
2. Invalid state transitions return `409`
3. `blocked_by_task_id` must exist and cannot self-reference

## Phase 2: Governance chain and audit closure

**Scope**
- Deliver minimum viable governed chain: dry-run/commit/reject/undo-last/audit
- Conservative dedupe proposal only (no auto-merge)

**Tasks**
1. `POST /changes/dry-run`
2. `POST /changes/{change_set_id}/commit`
3. `DELETE /changes/{change_set_id}`
4. `POST /commits/undo-last`
5. `GET /audit/events`
6. Expose task-enhanced field diffs in dry-run output

## Phase 3: OpenClaw skill contract alignment

**Scope**
- Match action parameters with contract
- Normalize error mapping and retry strategy

**Tasks**
1. `create_task` supports `cycle_id/next_review_at/blocked_by_task_id`
2. `list_tasks` supports `view/cycle_id/blocked/stale_days/updated_before`
3. Retry strategy for `429/500`
4. Forward `client_request_id` for idempotency

## Phase 4: Frontend closure and release validation

**Scope**
- Complete task UX enhancements
- Run full E2E acceptance loop

**Tasks**
1. Task page: preset views and batch operations
2. Task detail: edit cycle/review/blocked fields
3. Review area: stale and blocked fast actions
4. Acceptance loop: `capture -> propose -> commit/reject -> audit -> undo -> audit`

## Milestones

1. M1: task-enhanced APIs available
2. M2: governance chain available
3. M3: skill contract aligned
4. M4: frontend + acceptance checks pass
