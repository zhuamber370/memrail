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
