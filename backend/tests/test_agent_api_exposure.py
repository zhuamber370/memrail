import uuid

from sqlalchemy import create_engine, text

from tests.helpers import database_url, fixed_topic_id, make_client, uniq


def _commit_change(client, change_set_id: str) -> dict:
    resp = client.post(
        f"/api/v1/changes/{change_set_id}/commit",
        json={
            "approved_by": {"type": "user", "id": "usr_local"},
            "client_request_id": f"idem-{uniq('commit')}",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_capture_inbox_action_commit_and_undo():
    client = make_client()
    marker = uniq("inbox")

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "capture_inbox",
                    "payload": {
                        "content": f"capture content {marker}",
                        "source": f"chat://openclaw/{marker}",
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200, dry.text
    _commit_change(client, dry.json()["change_set_id"])

    listed = client.get("/api/v1/inbox?page=1&page_size=100")
    assert listed.status_code == 200
    items = listed.json()["items"]
    matched = [item for item in items if item["source"] == f"chat://openclaw/{marker}"]
    assert matched

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_local"}, "reason": "undo inbox capture"},
    )
    assert undo.status_code == 200, undo.text

    listed_after = client.get("/api/v1/inbox?page=1&page_size=100")
    assert listed_after.status_code == 200
    items_after = listed_after.json()["items"]
    assert all(item["source"] != f"chat://openclaw/{marker}" for item in items_after)


def test_delete_link_action_commit_and_undo():
    client = make_client()
    topic_id = fixed_topic_id(client)

    created_task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"link_task_{uniq('task')}",
            "status": "todo",
            "source": f"test://{uniq('task_src')}",
            "topic_id": topic_id,
        },
    )
    assert created_task.status_code == 201, created_task.text
    task_id = created_task.json()["id"]

    created_note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"link_note_{uniq('note')}",
            "body": "seed body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert created_note.status_code == 201, created_note.text
    note_id = created_note.json()["id"]

    created_link = client.post(
        "/api/v1/links",
        json={
            "from_type": "note",
            "from_id": note_id,
            "to_type": "task",
            "to_id": task_id,
            "relation": "supports",
        },
    )
    assert created_link.status_code == 201, created_link.text
    link_id = created_link.json()["id"]

    listed = client.get(f"/api/v1/links?page=1&page_size=50&from_id={note_id}")
    assert listed.status_code == 200
    assert any(item["id"] == link_id for item in listed.json()["items"])

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [{"type": "delete_link", "payload": {"link_id": link_id}}],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200, dry.text
    _commit_change(client, dry.json()["change_set_id"])

    listed_after_delete = client.get(f"/api/v1/links?page=1&page_size=50&from_id={note_id}")
    assert listed_after_delete.status_code == 200
    assert all(item["id"] != link_id for item in listed_after_delete.json()["items"])

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_local"}, "reason": "undo delete link"},
    )
    assert undo.status_code == 200, undo.text

    listed_after_undo = client.get(f"/api/v1/links?page=1&page_size=50&from_id={note_id}")
    assert listed_after_undo.status_code == 200
    assert any(item["id"] == link_id for item in listed_after_undo.json()["items"])


def test_create_route_node_action_commit_and_undo():
    client = make_client()
    topic_id = fixed_topic_id(client)
    task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"route_task_{uniq('task')}",
            "status": "todo",
            "source": f"test://{uniq('task_src')}",
            "topic_id": topic_id,
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    route = client.post(
        "/api/v1/routes",
        json={"task_id": task_id, "name": f"route_{uniq('name')}", "goal": "g", "status": "candidate"},
    )
    assert route.status_code == 201, route.text
    route_id = route.json()["id"]

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [
                {
                    "type": "create_route_node",
                    "payload": {
                        "route_id": route_id,
                        "node_type": "idea",
                        "title": f"node_{uniq('node')}",
                        "description": "desc",
                        "status": "waiting",
                    },
                }
            ],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200, dry.text
    _commit_change(client, dry.json()["change_set_id"])

    graph = client.get(f"/api/v1/routes/{route_id}/graph")
    assert graph.status_code == 200, graph.text
    created_nodes = graph.json()["nodes"]
    assert created_nodes
    created_node_ids = {node["id"] for node in created_nodes}

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_local"}, "reason": "undo create route node"},
    )
    assert undo.status_code == 200, undo.text

    graph_after = client.get(f"/api/v1/routes/{route_id}/graph")
    assert graph_after.status_code == 200, graph_after.text
    node_ids_after = {node["id"] for node in graph_after.json()["nodes"]}
    assert created_node_ids.isdisjoint(node_ids_after)


def test_delete_knowledge_action_commit_and_undo():
    client = make_client()
    marker = uniq("knowledge")
    created = client.post(
        "/api/v1/knowledge",
        json={"title": f"title_{marker}", "body": f"body_{marker}", "category": "decision_record"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    dry = client.post(
        "/api/v1/changes/dry-run",
        json={
            "actions": [{"type": "delete_knowledge", "payload": {"item_id": item_id}}],
            "actor": {"type": "agent", "id": "openclaw"},
            "tool": "openclaw-skill",
        },
    )
    assert dry.status_code == 200, dry.text
    _commit_change(client, dry.json()["change_set_id"])

    deleted = client.get(f"/api/v1/knowledge/{item_id}")
    assert deleted.status_code == 404

    undo = client.post(
        "/api/v1/commits/undo-last",
        json={"requested_by": {"type": "user", "id": "usr_local"}, "reason": "undo delete knowledge"},
    )
    assert undo.status_code == 200, undo.text

    restored = client.get(f"/api/v1/knowledge/{item_id}")
    assert restored.status_code == 200
    assert restored.json()["title"] == f"title_{marker}"


def test_task_note_sources_and_journal_items_endpoints():
    client = make_client()
    topic_id = fixed_topic_id(client)

    created_task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"sources_task_{uniq('task')}",
            "status": "todo",
            "source": f"test://{uniq('task_src')}",
            "topic_id": topic_id,
        },
    )
    assert created_task.status_code == 201, created_task.text
    task_id = created_task.json()["id"]

    task_sources = client.get(f"/api/v1/tasks/{task_id}/sources")
    assert task_sources.status_code == 200
    assert task_sources.json()["items"]

    created_note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"sources_note_{uniq('note')}",
            "body": "source body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert created_note.status_code == 201, created_note.text
    note_id = created_note.json()["id"]

    note_sources = client.get(f"/api/v1/notes/{note_id}/sources")
    assert note_sources.status_code == 200
    assert note_sources.json()["items"]

    journal_date = f"2099-05-{(sum(ord(c) for c in uniq('jdt')) % 28) + 1:02d}"
    upsert = client.post(
        "/api/v1/journals/upsert-append",
        json={
            "journal_date": journal_date,
            "append_text": "journal base",
            "source": f"test://{uniq('journal_src')}",
        },
    )
    assert upsert.status_code == 200, upsert.text
    journal_id = upsert.json()["id"]

    engine = create_engine(database_url(), future=True)
    journal_item_id = f"jit_{uuid.uuid4().hex[:12]}"
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO journal_items (
                  id, journal_id, kind, content, resolution, task_id, topic_id, ignore_reason
                )
                VALUES (
                  :id, :journal_id, :kind, :content, :resolution, NULL, NULL, NULL
                )
                """
            ),
            {
                "id": journal_item_id,
                "journal_id": journal_id,
                "kind": "fact",
                "content": "journal item content",
                "resolution": "pending",
            },
        )

    items = client.get(f"/api/v1/journals/{journal_date}/items")
    assert items.status_code == 200, items.text
    ids = [item["id"] for item in items.json()["items"]]
    assert journal_item_id in ids
