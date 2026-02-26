import json

from sqlalchemy import create_engine, text

from tests.helpers import fixed_topic_id, make_client
from tests.helpers import database_url
from tests.helpers import uniq


def _truncate_commits():
    engine = create_engine(database_url(), future=True)
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("DELETE FROM commits"))
        else:
            conn.execute(text("TRUNCATE TABLE commits"))


def test_dry_run_commit_undo_last_flow():
    client = make_client()
    topic_id = fixed_topic_id(client)

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {"title": "x", "status": "todo", "source": "test://changes", "topic_id": topic_id},
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


def test_dry_run_create_task_missing_topic_id_returns_422():
    client = make_client()
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {"title": "x", "status": "todo", "source": "test://changes"},
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 422


def test_reject_proposed_change_set_deletes_it():
    client = make_client()
    topic_id = fixed_topic_id(client)
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": f"reject_me_{uniq('task')}",
                        "status": "todo",
                        "source": f"test://{uniq('reject')}",
                        "topic_id": topic_id,
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    rejected = client.delete(f"/api/v1/changes/{chg_id}")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["change_set_id"] == chg_id

    detail = client.get(f"/api/v1/changes/{chg_id}")
    assert detail.status_code == 404


def test_reject_committed_change_set_returns_409():
    client = make_client()
    topic_id = fixed_topic_id(client)
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": f"reject_committed_{uniq('task')}",
                        "status": "todo",
                        "source": f"test://{uniq('reject_commit')}",
                        "topic_id": topic_id,
                    },
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    rejected = client.delete(f"/api/v1/changes/{chg_id}")
    assert rejected.status_code == 409
    body = rejected.json()
    assert body["error"]["code"] == "CHANGE_SET_NOT_PROPOSED"


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
    topic_id = fixed_topic_id(client)
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
                        "topic_id": topic_id,
                        "cycle_id": "cyc_123",
                        "due": "2099-04-01",
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
    assert any("due" in line for line in diff)


def test_dry_run_summary_has_entity_and_field_counts():
    client = make_client()
    topic_id = fixed_topic_id(client)
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
                        "topic_id": topic_id,
                        "cycle_id": "cyc_123",
                    },
                },
                {
                    "type": "update_task",
                    "payload": {
                        "task_id": "tsk_123",
                        "priority": "P1",
                        "due": "2099-04-01",
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
    assert summary["field_due"] == 1


def test_dry_run_includes_structured_diff_items():
    client = make_client()
    topic_id = fixed_topic_id(client)
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
                        "topic_id": topic_id,
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


def test_dry_run_persists_change_actions():
    client = make_client()
    topic_id = fixed_topic_id(client)
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {"title": "persist-actions", "status": "todo", "source": "test", "topic_id": topic_id},
                },
                {
                    "type": "append_note",
                    "payload": {"title": "n", "body": "b", "sources": [{"type": "text", "value": "test://x"}]},
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    engine = create_engine(database_url(), future=True)
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM change_actions WHERE change_set_id = :change_set_id"),
            {"change_set_id": chg_id},
        ).scalar_one()
    assert int(count) == 2


def test_commit_with_same_client_request_id_is_idempotent():
    client = make_client()
    topic_id = fixed_topic_id(client)
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": "idempotent-commit",
                        "status": "todo",
                        "source": "test://changes",
                        "topic_id": topic_id,
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    payload = {
        "approved_by": {"type": "user", "id": "usr_1"},
        "client_request_id": f"idem-{uniq('commit')}",
    }
    first = client.post(f"/api/v1/changes/{chg_id}/commit", json=payload)
    assert first.status_code == 200
    second = client.post(f"/api/v1/changes/{chg_id}/commit", json=payload)
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()
    assert first_body["commit_id"] == second_body["commit_id"]


def test_commit_executes_create_task_action():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = f"test://{uniq('chg_task_src')}"
    title = f"chg_task_{uniq('title')}"

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": title,
                        "status": "todo",
                        "priority": "P2",
                        "source": marker,
                        "topic_id": topic_id,
                    },
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    listed = client.get("/api/v1/tasks?page=1&page_size=100&topic_id=" + topic_id)
    assert listed.status_code == 200
    assert any(item["title"] == title and item["source"] == marker for item in listed.json()["items"])

    engine = create_engine(database_url(), future=True)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT apply_result_json
                FROM change_actions
                WHERE change_set_id = :change_set_id
                LIMIT 1
                """
            ),
            {"change_set_id": chg_id},
        ).scalar_one()
    if isinstance(row, str):
        row = json.loads(row)
    assert isinstance(row, dict)
    assert row.get("status") == "applied"
    assert row.get("entity") == "task"


def test_commit_executes_update_task_and_link_action():
    client = make_client()
    topic_id = fixed_topic_id(client)

    created_task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"seed_task_{uniq('seed')}",
            "status": "todo",
            "priority": "P3",
            "source": f"test://{uniq('seed_task_src')}",
            "topic_id": topic_id,
        },
    )
    assert created_task.status_code == 201
    task_id = created_task.json()["id"]

    created_note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"seed_note_{uniq('seed')}",
            "body": "seed body",
            "sources": [{"type": "text", "value": f"test://{uniq('seed_note_src')}"}],
            "tags": ["seed"],
        },
    )
    assert created_note.status_code == 201
    note_id = created_note.json()["id"]

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "update_task",
                    "payload": {"task_id": task_id, "priority": "P1"},
                },
                {
                    "type": "link_entities",
                    "payload": {
                        "from_type": "note",
                        "from_id": note_id,
                        "to_type": "task",
                        "to_id": task_id,
                        "relation": "supports",
                    },
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    commit = client.post(
        f"/api/v1/changes/{chg_id}/commit",
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    listed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed.status_code == 200
    changed = [item for item in listed.json()["items"] if item["id"] == task_id]
    assert changed
    assert changed[0]["priority"] == "P1"

    engine = create_engine(database_url(), future=True)
    with engine.connect() as conn:
        link_count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM links
                WHERE from_type='note' AND from_id=:from_id
                  AND to_type='task' AND to_id=:to_id
                  AND relation='supports'
                """
            ),
            {"from_id": note_id, "to_id": task_id},
        ).scalar_one()
    assert int(link_count) >= 1


def test_commit_failure_rolls_back_all_actions():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = f"test://{uniq('rollback_task_src')}"
    title = f"rollback_task_{uniq('title')}"

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": title,
                        "status": "todo",
                        "priority": "P2",
                        "source": marker,
                        "topic_id": topic_id,
                    },
                },
                {
                    "type": "update_task",
                    "payload": {"task_id": "tsk_missing_for_rollback", "priority": "P1"},
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    commit = client.post(
        f"/api/v1/changes/{chg_id}/commit",
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 422

    listed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed.status_code == 200
    assert all(item["title"] != title for item in listed.json()["items"])


def test_undo_last_reverts_created_task():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = f"test://{uniq('undo_task_src')}"
    title = f"undo_task_{uniq('title')}"

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": title,
                        "status": "todo",
                        "priority": "P2",
                        "source": marker,
                        "topic_id": topic_id,
                    },
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    listed_before = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed_before.status_code == 200
    assert any(item["title"] == title for item in listed_before.json()["items"])

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_1"}, "reason": "undo create"},
    )
    assert undo.status_code == 200
    assert undo.json()["status"] == "reverted"

    listed_after = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed_after.status_code == 200
    assert all(item["title"] != title for item in listed_after.json()["items"])


def test_undo_last_reverts_updated_task_priority():
    client = make_client()
    topic_id = fixed_topic_id(client)

    seed = client.post(
        "/api/v1/tasks",
        json={
            "title": f"undo_update_seed_{uniq('task')}",
            "status": "todo",
            "priority": "P3",
            "source": f"test://{uniq('seed_task_src')}",
            "topic_id": topic_id,
        },
    )
    assert seed.status_code == 201
    task_id = seed.json()["id"]

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "update_task",
                    "payload": {"task_id": task_id, "priority": "P1"},
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    listed_changed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed_changed.status_code == 200
    changed = [item for item in listed_changed.json()["items"] if item["id"] == task_id]
    assert changed and changed[0]["priority"] == "P1"

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_1"}, "reason": "undo update"},
    )
    assert undo.status_code == 200

    listed_reverted = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed_reverted.status_code == 200
    reverted = [item for item in listed_reverted.json()["items"] if item["id"] == task_id]
    assert reverted and reverted[0]["priority"] == "P3"


def test_list_changes_returns_recent_dry_runs():
    client = make_client()
    topic_id = fixed_topic_id(client)

    first = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": f"list_a_{uniq('chg')}",
                        "status": "todo",
                        "priority": "P2",
                        "source": f"test://{uniq('src')}",
                        "topic_id": topic_id,
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert first.status_code == 200
    first_id = first.json()["change_set_id"]

    second = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": f"list_b_{uniq('chg')}",
                        "status": "todo",
                        "priority": "P2",
                        "source": f"test://{uniq('src')}",
                        "topic_id": topic_id,
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert second.status_code == 200
    second_id = second.json()["change_set_id"]

    listed = client.get("/api/v1/changes?page=1&page_size=20&status=proposed")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] >= 2
    ids = [item["change_set_id"] for item in payload["items"]]
    assert second_id in ids
    assert first_id in ids


def test_get_change_detail_contains_actions():
    client = make_client()
    topic_id = fixed_topic_id(client)
    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_task",
                    "payload": {
                        "title": f"detail_a_{uniq('chg')}",
                        "status": "todo",
                        "priority": "P2",
                        "source": f"test://{uniq('src')}",
                        "topic_id": topic_id,
                    },
                },
                {
                    "type": "append_note",
                    "payload": {
                        "title": f"detail_n_{uniq('chg')}",
                        "body": "body",
                        "sources": [{"type": "text", "value": f"test://{uniq('src')}"}],
                    },
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    chg_id = dry.json()["change_set_id"]

    detail = client.get(f"/api/v1/changes/{chg_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["change_set_id"] == chg_id
    assert body["status"] == "proposed"
    assert len(body["actions"]) == 2
    assert body["actions"][0]["action_index"] == 1
    assert body["actions"][1]["action_index"] == 2


def test_dry_run_supports_patch_note_and_journal_upsert():
    client = make_client()
    note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"dry_patch_note_{uniq('note')}",
            "body": "seed body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert note.status_code == 201
    note_id = note.json()["id"]
    journal_date = f"2099-03-{(sum(ord(c) for c in uniq('jdt')) % 28) + 1:02d}"

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "patch_note",
                    "payload": {
                        "note_id": note_id,
                        "body_append": "increment",
                        "source": f"test://{uniq('patch_note_src')}",
                    },
                },
                {
                    "type": "upsert_journal_append",
                    "payload": {
                        "journal_date": journal_date,
                        "append_text": "journal line",
                        "source": f"test://{uniq('journal_src')}",
                    },
                },
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200
    body = dry.json()
    assert body["summary"]["note_patch"] == 1
    assert body["summary"]["journal_upsert"] == 1
    entities = [item["entity"] for item in body["diff_items"]]
    assert "note" in entities
    assert "journal" in entities


def test_commit_patch_note_and_undo_reverts_body():
    client = make_client()
    marker = uniq("patch_note")
    note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"patch_note_{marker}",
            "body": "base body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert note.status_code == 201
    note_id = note.json()["id"]

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "patch_note",
                    "payload": {
                        "note_id": note_id,
                        "body_append": "new increment",
                        "source": f"test://{uniq('patch_note_src')}",
                    },
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    listed_after = client.get("/api/v1/notes/search?page=1&page_size=100")
    assert listed_after.status_code == 200
    changed = [item for item in listed_after.json()["items"] if item["id"] == note_id]
    assert changed
    assert "base body" in changed[0]["body"]
    assert "new increment" in changed[0]["body"]

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_1"}, "reason": "undo patch note"},
    )
    assert undo.status_code == 200

    listed_reverted = client.get("/api/v1/notes/search?page=1&page_size=100")
    assert listed_reverted.status_code == 200
    reverted = [item for item in listed_reverted.json()["items"] if item["id"] == note_id]
    assert reverted
    assert reverted[0]["body"] == "base body"


def test_commit_upsert_journal_append_and_undo_removes_created_journal():
    client = make_client()
    journal_date = f"2099-04-{(sum(ord(c) for c in uniq('jdt')) % 28) + 1:02d}"
    marker = f"journal_append_{uniq('j')}"

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "upsert_journal_append",
                    "payload": {
                        "journal_date": journal_date,
                        "append_text": marker,
                        "source": f"test://{uniq('journal_src')}",
                    },
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
        json={"approved_by": {"type": "user", "id": "usr_1"}, "client_request_id": f"idem-{uniq('commit')}"},
    )
    assert commit.status_code == 200

    fetched = client.get(f"/api/v1/journals/{journal_date}")
    assert fetched.status_code == 200
    assert marker in fetched.json()["raw_content"]

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_1"}, "reason": "undo journal append"},
    )
    assert undo.status_code == 200

    fetched_after = client.get(f"/api/v1/journals/{journal_date}")
    assert fetched_after.status_code == 404
