# Dev Setup (Contributors)

This guide is optimized for getting a new contributor to a working local environment quickly.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Repo layout

- `backend/` — FastAPI + SQLAlchemy
- `frontend/` — Next.js 14
- `docs/` — documentation

## 1) Clone

```bash
git clone https://github.com/zhuamber370/memlineage.git
cd memlineage
```

## 2) Configure env

```bash
cp .env.example .env
cp .env frontend/.env.local
```

Notes:
- Backend reads `backend/.env` and root `.env`.
- Frontend reads `frontend/.env.local`.

## 3) Run backend

See: `backend/README.md`

Typical local run:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

Verify:
- http://127.0.0.1:8000/health

## 4) Run frontend

See: `frontend/README.md`

```bash
cd frontend
npm install
npm run dev
```

Verify:
- http://127.0.0.1:3000

## 5) Running tests

Backend:

```bash
cd backend
python3 -m pytest -q
python3 scripts/cleanup_test_data.py
```

Frontend:

```bash
cd frontend
npm run build
```

## What to contribute first

Good first contributions (high-signal, low-risk):
- Documentation fixes (API surface sync, README clarity)
- Small UI copy improvements (keep tone factual)
- UX polish on `/changes` diff readability

If you’re unsure, open an issue with:
- Your preferred area (backend/frontend/full-stack/docs)
- Your available time (e.g. 30–60 min / weekend)
