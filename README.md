# OpenClaw KMS

Governed memory and task system for OpenClaw agents.

`OpenClaw KMS` adds a governance layer on top of OpenClaw memory workflows:
- Agent proposes writes.
- Human reviews and approves/rejects.
- System preserves traceability and rollback.

## Why this project

Most agent memory setups struggle with:
- context loss across long sessions and tool switching,
- noisy autonomous writes with no clear approval gate,
- weak rollback and source traceability,
- no practical human review surface for day-to-day correction.

OpenClaw KMS addresses this with a governed write pipeline and a human-facing review UI.

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

OpenClaw KMS is **OpenClaw-first**:
- It does not replace OpenClaw memory/compaction.
- It adds governed persistence and human approval for higher-quality long-term memory.

## Quickstart

### 1) Clone

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd kms-for-agent
```

### 2) Configure environment

```bash
cp .env.example .env
```

Edit `.env` only.

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

- Backend health: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`

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
