# Backend

FastAPI backend for Memrail MVP.

## Env

Backend reads env from process and `.env`.

Core (SQLite default):
- `AFKMS_DB_BACKEND=sqlite` (default)
- `AFKMS_SQLITE_PATH` (optional, default `data/afkms.sqlite3`)

PostgreSQL mode (`AFKMS_DB_BACKEND=postgres`):
- `AFKMS_DB_HOST`
- `AFKMS_DB_PORT`
- `AFKMS_DB_NAME`
- `AFKMS_DB_USER`
- `AFKMS_DB_PASSWORD`

Optional:
- `AFKMS_DATABASE_URL` (direct SQLAlchemy URL override)
- `AFKMS_REQUIRE_AUTH` (`true` to enforce bearer auth on `/api/v1/*`)
- `KMS_API_KEY`
- `AFKMS_PG_ADMIN_*` (for bootstrap script when using PostgreSQL)

## Local Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

Enable API key auth (recommended outside local dev):

```bash
export AFKMS_REQUIRE_AUTH=true
export KMS_API_KEY="<your_api_key>"
python3 -m uvicorn src.app:app --reload --port 8000
```

PostgreSQL bootstrap (optional enhancement):

```bash
cd backend
source .venv/bin/activate
python3 scripts/bootstrap_postgres.py
```

Bootstrap behavior:
- uses app DB env: `AFKMS_DB_*`
- uses admin connection env: `AFKMS_PG_ADMIN_*` (optional)
- default admin connection is `postgres` user to `postgres` database on `AFKMS_DB_HOST:AFKMS_DB_PORT`

## Key Domains

- `topics`: fixed taxonomy (7 categories, POST locked)
- `tasks`: structured action items with status governance + archive
- `notes`: knowledge notes with topic/unclassified/archive states
- `journals`: same-day append-only journal storage
- `changes`: dry-run / commit / reject(delete proposal) / undo governance flow
- `context`: aggregated read bundle for agent retrieval
- `audit`: write trace query endpoint

## Test

```bash
cd backend
python3 -m pytest -q
```

Targeted smoke:

```bash
python3 -m pytest backend/tests/test_changes_api.py backend/tests/test_tasks_api.py backend/tests/test_inbox_notes_api.py backend/tests/test_links_api.py backend/tests/test_audit_api.py backend/tests/test_topics_api.py -q
python3 -m pytest backend/tests/test_journals_api.py backend/tests/test_context_api.py -q
```

## Utility Scripts

```bash
python3 backend/scripts/bootstrap_postgres.py
python3 backend/scripts/cleanup_test_data.py
python3 backend/scripts/migrate_notes_topic_status.py
```

- `bootstrap_postgres.py`: for PostgreSQL role/database bootstrap.
- `cleanup_test_data.py`: PostgreSQL-oriented cleanup utility for local/API tests.
- `migrate_notes_topic_status.py`: PostgreSQL migration helper for historical data backfill.
