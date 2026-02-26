# Memrail

Memrail is a governed memory + task system for OpenClaw workflows.

It focuses on one core principle:
- **Agent can propose writes, human keeps final control.**

## Current Version (MVP)

### 1. Governed write pipeline
- `dry-run -> commit/reject -> undo-last`
- Full audit trace for write operations.

### 2. Task Command Center (desktop-first)
- `Tasks` page is the main execution workspace.
- Supports search, filters, grouped list, and detail editing in one screen.
- Task detail card is rendered above the execution graph (no overlay drawer).
- Includes execution canvas (DAG-like graph) for idea/goal flow.
- Node operations are context-menu driven (`...` on selected node):
  - `+ Add Step` (inline panel near the selected node)
  - `Set Status` (`waiting / execute / done`)
  - `Rename`
  - `Delete` (leaf node only, and non-start node)
- Branch relation type (`refine/initiate/handoff`) is labeled directly on edges.

### 3. Knowledge board
- Topic-based knowledge management.
- Supports classify/edit/archive with source-aware notes.

### 4. Change review inbox
- Human review surface for proposed writes.
- Commit/reject proposals and undo last commit.

### 5. Task-scoped idea page
- `/ideas` is a task-scoped tool.
- It requires `task_id` context (opened from task workflow), not top-level nav.
- Ideas can be promoted to `idea` or `goal` route nodes.

## Tech Stack
- Backend: FastAPI + SQLAlchemy
- Frontend: Next.js 14
- Default DB: SQLite
- Optional DB: PostgreSQL

## Prerequisites
- Python 3.10+
- Node.js 18+

## Quickstart

### 1) Clone

```bash
git clone https://github.com/zhuamber370/memrail.git
cd memrail
```

### 2) Configure env

```bash
cp .env.example .env
cp .env frontend/.env.local
```

Notes:
- Backend reads `backend/.env` and root `.env`.
- Frontend reads `frontend/.env.local`.
- Default local mode:
  - `AFKMS_DB_BACKEND=sqlite`
  - `AFKMS_REQUIRE_AUTH=false`

### 3) Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

### 4) Run frontend

```bash
cd frontend
npm install
npm run dev
```

### 5) Verify
- Backend: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Frontend: [http://127.0.0.1:3000](http://127.0.0.1:3000)

## Optional: PostgreSQL

Set in `.env`:
- `AFKMS_DB_BACKEND=postgres`
- `AFKMS_DB_HOST`
- `AFKMS_DB_PORT`
- `AFKMS_DB_NAME`
- `AFKMS_DB_USER`
- `AFKMS_DB_PASSWORD`

Bootstrap:

```bash
cd backend
source .venv/bin/activate
python3 scripts/bootstrap_postgres.py
```

## OpenClaw Skill

Install workspace skill:

```bash
bash scripts/install_openclaw_kms_skill.sh
```

Check:

```bash
openclaw skills info kms --json
openclaw skills check --json
```

## Documentation Map

- **Authoritative current docs**:
  - `README.md`
  - `backend/README.md`
  - `frontend/README.md`
  - `docs/reports/mvp-release-notes.md`
  - `docs/reports/mvp-e2e-checklist.md`

## Security

For security disclosures, follow `SECURITY.md`.

## License

Apache-2.0. See `LICENSE`.
