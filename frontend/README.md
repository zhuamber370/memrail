# Frontend

Next.js frontend for Memrail.

## Environment

Frontend reads from `frontend/.env.local`:
- `NEXT_PUBLIC_API_BASE` (e.g. `http://127.0.0.1:8000`)
- `NEXT_PUBLIC_API_KEY`

Recommended sync from root:

```bash
cd frontend
cp ../.env .env.local
```

## Run

```bash
cd frontend
npm install
npm run dev
```

Build check:

```bash
npm run build
```

## Main Pages (Synced 2026-02-27)

- `/tasks`
  - Task Command Center
  - Search/filter/list/detail in one layout
  - Task detail card above route graph
  - Route canvas with node `...` operations:
    - `+ Add Step`
    - `Set Status` (`waiting / execute / done`)
    - `Rename`
    - `Delete` (leaf node only)
  - Edge relation labels rendered on graph

- `/knowledge`
  - Knowledge CRUD workspace backed by `/api/v1/knowledge`
  - List + detail split view
  - Filters:
    - status (`active | archived`)
    - category (`ops_manual | mechanism_spec | decision_record`)
    - keyword search (`q`)
  - Create supports category `auto` inference or explicit category
  - Detail supports edit/archive/delete

- `/changes`
  - Proposal review (diff + summary)
  - Commit/reject and undo-last operations

## Task-scoped helper pages

- `/ideas?task_id=<task_id>`

This page requires task context and is not default top-level navigation.
