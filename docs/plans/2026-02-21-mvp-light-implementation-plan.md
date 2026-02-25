> Documentation Status: Historical Snapshot
> Last synced: 2026-02-25

# Memrail MVP Lightweight Implementation Plan

> Based on: `docs/plans/2026-02-21-agent-first-kms-final-system-design.md`
> Goal: implement a minimal but complete governed MVP.

## Tech stack and runtime assumptions

1. Frontend: `Next.js + TypeScript`
2. Backend: `FastAPI + Pydantic + SQLAlchemy`
3. Database: PostgreSQL (`.env` driven)
4. Local development only (no Docker)

## Task 1: DB model enhancements (Task + Cycle)

**Files**
- `backend/db/schema.sql`
- `backend/db/migrations/001_init.sql`

**Validation**
- Verify task enhancement fields and `cycles` schema are present.

## Task 2: Task API expansion

**Files**
- `backend/src/routes/tasks.py`
- `backend/src/services/task_service.py`
- `backend/src/schemas.py`

**Validation**
- `python3 -m pytest backend/tests -q`
- New task fields are covered by tests.

## Task 3: Additional task endpoints

**Files**
- `backend/src/routes/tasks.py`
- `backend/src/routes/cycles.py`
- `backend/src/app.py`

**Validation**
- Smoke test `batch-update`, `views/summary`, and cycle endpoints.

## Task 4: Error handling hardening

**Files**
- `backend/src/middleware/error_handler.py`
- `backend/src/services/task_service.py`

**Validation**
- Invalid transition returns `409` + `TASK_INVALID_STATUS_TRANSITION`.

## Task 5: OpenClaw skill parameter alignment

**Files**
- `skill/openclaw_skill.py`
- `skill/actions/create_task.py`
- `skill/actions/propose_commit_undo.py`

**Validation**
- Skill forwards new task/query parameters correctly.

## Task 6: Frontend task page updates

**Files**
- `frontend/app/tasks/page.tsx`
- `frontend/src/lib/api.ts`
- `frontend/app/globals.css`

**Validation**
- `cd frontend && npm run build`
- Task page supports new filters and batch flows.

## Task 7: Acceptance regression

**Files**
- `docs/reports/mvp-e2e-checklist.md`

**Validation**
- Run full loop: `capture -> propose -> commit/reject -> audit -> undo -> audit`
- All critical flows pass.
