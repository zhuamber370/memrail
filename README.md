# Memrail

Governed memory and task system for OpenClaw agents.

`Memrail` adds a governance layer on top of OpenClaw memory workflows:
- Agent proposes writes.
- Human reviews and approves/rejects.
- System preserves traceability and rollback.

## Why this project

Most agent memory setups struggle with:
- context loss across long sessions and tool switching,
- noisy autonomous writes with no clear approval gate,
- weak rollback and source traceability,
- no practical human review surface for day-to-day correction.

Memrail addresses this with a governed write pipeline and a human-facing review UI.

## What it provides (current MVP)

1. Governed write pipeline:
- Dry-run -> Commit or Reject -> Undo last commit

2. Structured domains:
- Tasks: action-focused, strongly structured
- Knowledge: reusable notes with sources and links

3. Human review UI:
- `/tasks`: maintain task state and structure
- `/knowledge`: review, classify, and maintain knowledge
- `/changes`: review proposals, commit/reject, undo

4. Agent integration:
- OpenClaw workspace skill (`openclaw-skill/kms`)
- REST API as the unified write/read entry

5. Traceability:
- source-aware writes and audit events in backend APIs

## Product positioning

Memrail is **OpenClaw-first**:
- It does not replace OpenClaw memory/compaction.
- It adds governed persistence and human approval for higher-quality long-term memory.

## Prerequisites

- Python 3.10+
- Node.js 18+
- SQLite (bundled with Python) for default local mode
- Optional enhancement: PostgreSQL 14+

## Quickstart

### 1) Clone

```bash
git clone https://github.com/zhuamber370/memrail.git
cd memrail
```

### 2) Configure environment

```bash
cp .env.example .env
```

Edit `.env` only.

Then sync frontend env:

```bash
cp .env frontend/.env.local
```

Notes:
- Backend reads `backend/.env` and root `.env`.
- Frontend (Next.js) reads `frontend/.env.local`; the copy command above keeps a single source of truth.
- Default backend DB mode is SQLite (`AFKMS_DB_BACKEND=sqlite`).
- API key auth is disabled by default (`AFKMS_REQUIRE_AUTH=false`).
- To enforce API auth, set `AFKMS_REQUIRE_AUTH=true` and set `KMS_API_KEY`.

### 3) Run backend (SQLite default)

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

- Backend health: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`

## Optional: Switch to PostgreSQL

1. In `.env`, set:
- `AFKMS_DB_BACKEND=postgres`
- `AFKMS_DB_HOST`, `AFKMS_DB_PORT`, `AFKMS_DB_NAME`, `AFKMS_DB_USER`, `AFKMS_DB_PASSWORD`

2. Bootstrap role/database:

```bash
cd backend
source .venv/bin/activate
python3 scripts/bootstrap_postgres.py
```

Bootstrap defaults:
- admin user: `postgres`
- admin db: `postgres`
- admin host/port: from `AFKMS_DB_HOST` / `AFKMS_DB_PORT`

If needed, override with:
- `AFKMS_PG_ADMIN_HOST`
- `AFKMS_PG_ADMIN_PORT`
- `AFKMS_PG_ADMIN_DB`
- `AFKMS_PG_ADMIN_USER`
- `AFKMS_PG_ADMIN_PASSWORD`

## Core governance flow

1. `POST /api/v1/changes/dry-run`
2. User decision:
- approve: `POST /api/v1/changes/{change_set_id}/commit`
- reject: `DELETE /api/v1/changes/{change_set_id}`
3. rollback if needed: `POST /api/v1/commits/undo-last`

## OpenClaw skill install

Set runtime env for OpenClaw:

```bash
export KMS_BASE_URL="http://127.0.0.1:8000"
export KMS_API_KEY="<your_api_key>"
```

Install skill to workspace:

```bash
cd <repo_root>
bash scripts/install_openclaw_kms_skill.sh
```

Verify:

```bash
openclaw skills info kms --json
openclaw skills check --json
```

## Current scope and boundaries

- Local/self-hosted MVP focus
- No multi-tenant OAuth/billing/SaaS ops yet
- Audit APIs are available; audit page is hidden from end-user navigation

## Discovery keywords

`openclaw memory`, `agent memory`, `persistent agent memory`, `agent context loss`, `governed ai writes`, `dry-run commit undo`, `agent rollback`, `traceable ai actions`, `agent knowledge base`, `openclaw task management`

## Feedback

- Bug report: use the `Bug report` issue template
- Feature request: use the `Feature request` issue template
- Security issue: follow `SECURITY.md` (do not disclose publicly)

## License

Apache-2.0. See `LICENSE`.
