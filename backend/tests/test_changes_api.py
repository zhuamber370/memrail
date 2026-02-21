from sqlalchemy import create_engine, text

from tests.helpers import make_client
from tests.helpers import database_url


def _truncate_commits():
    engine = create_engine(database_url(), future=True)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE commits"))


def test_dry_run_commit_undo_last_flow():
    client = make_client()

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {"title": "x", "status": "todo", "source": "test"},
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    commit = client.post(
        f"/api/v1/changes/{chg_id}/commit",
        json={"approved_by": {"type": "user", "id": "usr_1"}},
    )
    assert commit.status_code == 200
    assert commit.json()["status"] == "committed"

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={
            "requested_by": {"type": "user", "id": "usr_1"},
            "reason": "revert test",
        },
    )
    assert undo.status_code == 200
    assert undo.json()["status"] == "reverted"


def test_undo_last_without_commit_returns_409():
    _truncate_commits()
    client = make_client()
    undo = client.post(
        "/api/v1/commits/undo-last",
        json={
            "requested_by": {"type": "user", "id": "usr_1"},
            "reason": "nothing to undo",
        },
    )
    assert undo.status_code == 409
    body = undo.json()
    assert body["error"]["code"] == "NO_COMMIT_TO_UNDO"


def test_dry_run_diff_contains_task_enhanced_fields():
    client = make_client()
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": "Task with cycle",
                        "status": "todo",
                        "source": "test",
                        "cycle_id": "cyc_123",
                        "blocked_by_task_id": "tsk_999",
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    diff = dry.json()["diff"]
    assert any("cycle_id" in line for line in diff)
    assert any("blocked_by_task_id" in line for line in diff)


def test_dry_run_summary_has_entity_and_field_counts():
    client = make_client()
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": "Task summary",
                        "status": "todo",
                        "source": "test",
                        "cycle_id": "cyc_123",
                    },
                },
                {
                    "type": "update_task",
                    "payload": {
                        "task_id": "tsk_123",
                        "priority": "P1",
                        "blocked_by_task_id": "tsk_999",
                    },
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    summary = dry.json()["summary"]
    assert summary["task_create"] == 1
    assert summary["task_update"] == 1
    assert summary["field_cycle_id"] == 1
    assert summary["field_blocked_by_task_id"] == 1


def test_dry_run_includes_structured_diff_items():
    client = make_client()
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": "Structured diff",
                        "status": "todo",
                        "source": "test",
                        "cycle_id": "cyc_123",
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    body = dry.json()
    assert "diff_items" in body
    assert len(body["diff_items"]) == 1
    item = body["diff_items"][0]
    assert item["entity"] == "task"
    assert item["action"] == "create"
    assert "cycle_id" in item["fields"]
    assert isinstance(item["text"], str)
