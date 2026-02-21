from tests.helpers import make_client


def test_audit_events_contains_write_trace():
    client = make_client()

    created = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": "manual",
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
