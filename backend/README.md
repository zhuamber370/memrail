# Backend

FastAPI backend for Memrail.

## Environment

Backend reads env from process, `backend/.env`, and repo-root `.env`.

### Core (SQLite default)
- `AFKMS_DB_BACKEND=sqlite`
- `AFKMS_SQLITE_PATH` (default: `data/afkms.sqlite3`)

### PostgreSQL mode
- `AFKMS_DB_BACKEND=postgres`
- `AFKMS_DB_HOST`
- `AFKMS_DB_PORT`
- `AFKMS_DB_NAME`
- `AFKMS_DB_USER`
- `AFKMS_DB_PASSWORD`

### Optional
- `AFKMS_DATABASE_URL` (direct SQLAlchemy URL override)
- `AFKMS_REQUIRE_AUTH=true|false`
- `KMS_API_KEY`
- `AFKMS_PG_ADMIN_*` (bootstrap script admin connection)

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn src.app:app --reload --port 8000
```

Enable API auth:

```bash
export AFKMS_REQUIRE_AUTH=true
export KMS_API_KEY="<your_api_key>"
python3 -m uvicorn src.app:app --reload --port 8000
```

## Core Domains / APIs

- `topics`: fixed taxonomy
- `tasks`: task lifecycle + archive
- `notes`: knowledge notes
- `journals`: append-only daily records
- `changes`: governed write flow (`dry-run/commit/reject/undo`)
- `ideas`: task-scoped idea entities
- `routes`: task-scoped route graph entities
  - route node APIs include create/patch/**delete**
  - edge APIs include create/delete
  - hierarchy fields:
    - route: `parent_route_id`, `spawned_from_node_id`
    - node: `parent_node_id`, `refinement_status`
    - node log: `log_type`, `source_ref`
  - hierarchy validation:
    - spawned route node must be `decision`
    - parent node must stay in same route and cannot form cycles
    - non-`candidate` route cannot rewire `parent_route_id`
- `context`: aggregated retrieval bundle
- `audit`: event trace query

## Tests

Full:

```bash
cd backend
python3 -m pytest -q
```

Note:
- In local SQLite mode, some `tests/test_changes_api.py` cases depend on PostgreSQL-specific behavior (for example `TRUNCATE`) and may fail.
- For route-graph verification in SQLite mode, use targeted tests below.

Route graph targeted:

```bash
python3 -m pytest -q backend/tests/test_routes_api.py
```

## Scripts

```bash
python3 backend/scripts/bootstrap_postgres.py
python3 backend/scripts/cleanup_test_data.py
python3 backend/scripts/migrate_notes_topic_status.py
```

- `bootstrap_postgres.py`: initialize PostgreSQL role/database.
- `cleanup_test_data.py`: cleanup test-marked data.
- `migrate_notes_topic_status.py`: historical data backfill helper.
