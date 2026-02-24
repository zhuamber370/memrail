from tests.helpers import fixed_topic_id, make_client, uniq


def test_audit_events_contains_write_trace():
    client = make_client()
    topic_id = fixed_topic_id(client)

    created = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": "test://audit",
            "topic_id": topic_id,
        },
    )
    assert created.status_code == 201

    audit = client.get("/api/v1/audit/events?page=1&page_size=20")
    assert audit.status_code == 200
    body = audit.json()
    assert body["total"] >= 1
    first = body["items"][0]
    assert "actor" in first
    assert "tool" in first
    assert "action" in first
    assert "target" in first


def test_audit_events_support_action_and_target_filters():
    client = make_client()
    topic_id = fixed_topic_id(client)
    created = client.post(
        "/api/v1/tasks",
        json={
            "title": f"Task Filter {uniq('audit')}",
            "status": "todo",
            "priority": "P2",
            "source": "test://audit-filter",
            "topic_id": topic_id,
        },
    )
    assert created.status_code == 201

    filtered = client.get("/api/v1/audit/events?page=1&page_size=50&action=create_task&target_type=task")
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] >= 1
    assert payload["items"]
    assert all(item["action"] == "create_task" for item in payload["items"])
    assert all(item["target"]["type"] == "task" for item in payload["items"])


def test_changes_commit_audit_contains_chain_metadata():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = f"test://{uniq('audit_changes')}"
    title = f"audit_change_task_{uniq('title')}"
    client_request_id = f"req-{uniq('commit')}"

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
        json={
            "approved_by": {"type": "user", "id": "usr_1"},
            "client_request_id": client_request_id,
        },
    )
    assert commit.status_code == 200
    commit_id = commit.json()["commit_id"]

    audit = client.get("/api/v1/audit/events?page=1&page_size=100&action=changes_apply_action")
    assert audit.status_code == 200
    items = audit.json()["items"]
    matched = [
        item
        for item in items
        if item.get("metadata", {}).get("change_set_id") == chg_id
        and item.get("metadata", {}).get("commit_id") == commit_id
        and item.get("metadata", {}).get("request_id") == client_request_id
    ]
    assert matched
