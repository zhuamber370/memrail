from tests.helpers import fixed_topic_id, make_client


def test_create_and_delete_link():
    client = make_client()
    topic_id = fixed_topic_id(client)

    task = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": "test://links",
            "topic_id": topic_id,
        },
    ).json()

    note = client.post(
        "/api/v1/notes/append",
        json={
            "title": "N",
            "body": "B",
            "sources": [{"type": "text", "value": "test://links"}],
        },
    ).json()

    created = client.post(
        "/api/v1/links",
        json={
            "from_type": "note",
            "from_id": note["id"],
            "to_type": "task",
            "to_id": task["id"],
            "relation": "supports",
        },
    )
    assert created.status_code == 201
    link_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/links/{link_id}")
    assert deleted.status_code == 204
