# Backend

FastAPI backend for MemLineage.

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

## API Surface (Synced 2026-03-01)

### Core domains
- `topics`
  - `POST /api/v1/topics`
  - `GET /api/v1/topics`
- `cycles`
  - `POST /api/v1/cycles`
  - `GET /api/v1/cycles`
- `tasks`
  - `POST /api/v1/tasks`
  - `GET /api/v1/tasks`
  - `PATCH /api/v1/tasks/{task_id}`
  - `POST /api/v1/tasks/batch-update`
  - `POST /api/v1/tasks/{task_id}/reopen`
  - `GET /api/v1/tasks/{task_id}/sources`
  - `GET /api/v1/tasks/views/summary`
  - `DELETE /api/v1/tasks/{task_id}`
  - `POST /api/v1/tasks/archive-cancelled`
  - `POST /api/v1/tasks/archive-selected`
- `notes`
  - `POST /api/v1/notes/append`
  - `GET /api/v1/notes/search`
  - `PATCH /api/v1/notes/{note_id}`
  - `DELETE /api/v1/notes/{note_id}`
  - `GET /api/v1/notes/{note_id}/sources`
  - `POST /api/v1/notes/batch-classify`
  - `GET /api/v1/notes/topic-summary`
- `knowledge` (note-backed convenience domain)
  - `POST /api/v1/knowledge`
  - `GET /api/v1/knowledge`
  - `GET /api/v1/knowledge/{item_id}`
  - `PATCH /api/v1/knowledge/{item_id}`
  - `POST /api/v1/knowledge/{item_id}/archive`
  - `DELETE /api/v1/knowledge/{item_id}`
- `links`
  - `GET /api/v1/links`
  - `POST /api/v1/links`
  - `DELETE /api/v1/links/{link_id}`
- `inbox`
  - `POST /api/v1/inbox/captures`
  - `GET /api/v1/inbox`
  - `GET /api/v1/inbox/{inbox_id}`
- `journals`
  - `POST /api/v1/journals/upsert-append`
  - `GET /api/v1/journals`
  - `GET /api/v1/journals/{journal_date}`
  - `GET /api/v1/journals/{journal_date}/items`

### Idea + route execution graph
- `ideas`
  - `POST /api/v1/ideas`
  - `GET /api/v1/ideas`
  - `PATCH /api/v1/ideas/{idea_id}`
  - `POST /api/v1/ideas/{idea_id}/promote`
- `routes`
  - `POST /api/v1/routes`
  - `GET /api/v1/routes`
  - `PATCH /api/v1/routes/{route_id}`
  - `POST /api/v1/routes/{route_id}/nodes`
  - `PATCH /api/v1/routes/{route_id}/nodes/{node_id}`
  - `DELETE /api/v1/routes/{route_id}/nodes/{node_id}`
  - `POST /api/v1/routes/{route_id}/edges`
  - `PATCH /api/v1/routes/{route_id}/edges/{edge_id}`
  - `DELETE /api/v1/routes/{route_id}/edges/{edge_id}`
  - `GET /api/v1/routes/{route_id}/graph`
  - `PATCH /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`
  - `DELETE /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`
  - `POST /api/v1/routes/{route_id}/nodes/{node_id}/logs`
  - `GET /api/v1/routes/{route_id}/nodes/{node_id}/logs`
  - `POST /api/v1/routes/{route_id}/edges/{edge_id}/logs`
  - `GET /api/v1/routes/{route_id}/edges/{edge_id}/logs`
  - `PATCH /api/v1/routes/{route_id}/edges/{edge_id}/logs/{log_id}`
  - `DELETE /api/v1/routes/{route_id}/edges/{edge_id}/logs/{log_id}`

### Governance / audit / context
- `changes`
  - `GET /api/v1/changes`
  - `POST /api/v1/changes/dry-run`
  - `GET /api/v1/changes/{change_set_id}`
  - `POST /api/v1/changes/{change_set_id}/commit`
  - `DELETE /api/v1/changes/{change_set_id}`
- `commits`
  - `POST /api/v1/commits/undo-last`
- `audit`
  - `GET /api/v1/audit/events`
- `context`
  - `GET /api/v1/context/bundle`

## Dry-run Action Types (Agent-exposed)

`POST /api/v1/changes/dry-run` currently accepts:
- `create_task`
- `append_note`
- `update_task`
- `patch_note`
- `upsert_journal_append`
- `link_entities`
- `create_idea`
- `patch_idea`
- `promote_idea`
- `create_route`
- `patch_route`
- `create_route_node`
- `patch_route_node`
- `delete_route_node`
- `create_route_edge`
- `patch_route_edge`
- `delete_route_edge`
- `append_route_node_log`
- `create_knowledge`
- `patch_knowledge`
- `archive_knowledge`
- `delete_knowledge`
- `create_link`
- `delete_link`
- `capture_inbox`

## Data Notes

- `knowledge` API currently persists into the `notes` table (`category: ops_manual | mechanism_spec | decision_record`).
- `knowledge_items`/`knowledge_evidences` tables may exist in schema history, but runtime knowledge CRUD is currently note-backed.
- Route graph logs now use unified `entity_logs` storage (`entity_type + entity_id`), while legacy node log responses remain readable for compatibility.

## Tests

Full:

```bash
cd backend
python3 -m pytest -q
```

Targeted:

```bash
python3 -m pytest -q backend/tests/test_changes_api.py
python3 -m pytest -q backend/tests/test_agent_api_exposure.py
```

## Scripts

```bash
python3 backend/scripts/bootstrap_postgres.py
python3 backend/scripts/cleanup_test_data.py
python3 backend/scripts/migrate_notes_topic_status.py
```

- `bootstrap_postgres.py`: initialize PostgreSQL role/database.
- `cleanup_test_data.py`: cleanup test-marked data.
- `migrate_notes_topic_status.py`: topic/status backfill helper.

Legacy / historical scripts (not part of the current runtime contract):
- `migrate_notes_to_knowledge.py`
- `reset_knowledge_to_notes.py`
