# Memrail

Memrail is a governed memory + task system for OpenClaw workflows.

Core principle:
- **Agent proposes writes, human keeps final control.**

## Current Scope (Synced 2026-02-27)

### 1. Governed write pipeline
- `dry-run -> commit/reject -> undo-last`
- Batch-level diff, summary, and audit trace for write operations.

### 2. Agent-readable data surface
Backend exposes read APIs for:
- `tasks`, `topics`, `cycles`
- `notes`, `knowledge`, `links`, `inbox`
- `journals` (+ journal items)
- `ideas`, `routes` (+ graph and node logs)
- `changes`, `audit`, `context`

### 3. Task Command Center (desktop-first)
- `/tasks` is the main execution workspace.
- Search/filter/list/detail in one screen.
- Execution canvas (route graph) supports node/edge operations and relation labels.

### 4. Knowledge workspace
- `/knowledge` is a focused knowledge CRUD console.
- Current categories:
  - `ops_manual`
  - `mechanism_spec`
  - `decision_record`
- Status lifecycle: `active | archived`.

### 5. Change review inbox
- `/changes` is the human review surface for agent proposals.
- Supports commit/reject and undo of last commit.

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

Authoritative runtime docs:
- `README.md`
- `backend/README.md`
- `frontend/README.md`
- `openclaw-skill/kms/SKILL.md`
- `docs/guides/agent-api-surface.md`
- `docs/reports/mvp-release-notes.md`
- `docs/reports/mvp-e2e-checklist.md`

Historical design/planning docs live under `docs/plans/` and are not treated as runtime contracts.

## Security

For security disclosures, follow `SECURITY.md`.

## License

Apache-2.0. See `LICENSE`.
