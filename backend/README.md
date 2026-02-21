# Backend

FastAPI backend for Agent-First KMS MVP.

## Env

The backend reads env vars from process env and `.env` (via `python-dotenv`).

Required keys:

- `AFKMS_DB_HOST`
- `AFKMS_DB_PORT`
- `AFKMS_DB_NAME`
- `AFKMS_DB_USER`
- `AFKMS_DB_PASSWORD`

Optional:

- `KMS_API_KEY`

## Local Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

## Test

```bash
cd backend
python3 -m pytest -q
```
