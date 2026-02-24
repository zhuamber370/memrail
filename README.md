# kms-for-agent

Agent-First Knowledge/Task Management MVP.

## 1) Clone

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd kms-for-agent
```

## 2) Configure env

```bash
cp .env.example .env
```

Edit `.env` only (DB host/user/password/api key/api base).

## 3) Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

## 4) Run frontend

```bash
cd frontend
npm install
npm run dev
```

## 5) Verify

- Backend health: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Language switch in sidebar: default EN, switch to 中文.

## 6) OpenClaw Global Skill (Generic Flow)

Set runtime env for OpenClaw:

```bash
export KMS_BASE_URL="http://127.0.0.1:8000"
export KMS_API_KEY="<your_api_key>"
```

Install skill to OpenClaw workspace directory `<workspace>/skills/kms`:

```bash
cd /Users/celastin/Desktop/projects/kms-for-agent
bash scripts/install_openclaw_kms_skill.sh
```

The script auto-detects workspace from `~/.openclaw/openclaw.json` (`agents.defaults.workspace`).

Verify discovery:

```bash
openclaw skills info kms --json
openclaw skills check --json
```

## 7) Governance flow (current)

All write proposals use the same flow:

1. `POST /api/v1/changes/dry-run`
2. user decision:
   - approve: `POST /api/v1/changes/{change_set_id}/commit`
   - reject and delete proposal: `DELETE /api/v1/changes/{change_set_id}`
3. if needed, rollback latest commit: `POST /api/v1/commits/undo-last`

Frontend `/changes` page supports:
- review proposal summary/diff
- commit selected proposal
- reject selected proposal
- undo last commit
