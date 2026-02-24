# Backend

FastAPI backend for Agent-First KMS MVP.

## Env

Backend reads env from process and `.env`.

Required:
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
python3 backend/scripts/cleanup_test_data.py
python3 backend/scripts/migrate_notes_topic_status.py
```

`cleanup_test_data.py` is recommended after local/API tests.
