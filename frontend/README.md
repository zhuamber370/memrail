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

## Main Pages (Current)

- `/tasks`
  - Task Command Center
  - Search/filter/list/detail in one layout
  - Execution canvas with node status / rename / delete operations
- `/knowledge`
  - topic-based knowledge board
- `/changes`
  - proposal review and commit/reject/undo

## Task-scoped helper pages

- `/ideas?task_id=<task_id>`

This page requires task context and is not default top-level navigation.
