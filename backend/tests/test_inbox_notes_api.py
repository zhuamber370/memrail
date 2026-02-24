from tests.helpers import fixed_topic_id, make_client, uniq


def test_capture_inbox_and_append_note_validation():
    client = make_client()
    marker = f"test://{uniq('note_src')}"

    cap = client.post(
        "/api/v1/inbox/captures",
        json={"content": "raw input", "source": "chat://demo"},
    )
    assert cap.status_code == 201
    assert cap.json()["id"].startswith("inb_")

    bad_note = client.post(
        "/api/v1/notes/append",
        json={"title": "n1", "body": "b1", "sources": []},
    )
    assert bad_note.status_code == 422

    ok_note = client.post(
        "/api/v1/notes/append",
        json={
            "title": "n1",
            "body": "b1",
            "sources": [{"type": "text", "value": marker}],
            "tags": ["ops"],
        },
    )
    assert ok_note.status_code == 201
    note_id = ok_note.json()["id"]

    listed = client.get("/api/v1/notes/search?page=1&page_size=20")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert any(item["id"] == note_id for item in listed.json()["items"])


def test_delete_note_hard_delete():
    client = make_client()
    created = client.post(
        "/api/v1/notes/append",
        json={
            "title": "Delete Note",
            "body": "body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/notes/{note_id}")
    assert deleted.status_code == 204

    listed = client.get("/api/v1/notes/search?page=1&page_size=100")
    assert listed.status_code == 200
    assert all(item["id"] != note_id for item in listed.json()["items"])

    delete_again = client.delete(f"/api/v1/notes/{note_id}")
    assert delete_again.status_code == 404


def test_search_notes_supports_unclassified_and_topic_filters():
    client = make_client()
    topic_id = fixed_topic_id(client)

    with_topic = client.post(
        "/api/v1/notes/append",
        json={
            "title": "With Topic",
            "body": "body A",
            "topic_id": topic_id,
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": ["ops"],
        },
    )
    assert with_topic.status_code == 201
    with_topic_id = with_topic.json()["id"]

    no_topic = client.post(
        "/api/v1/notes/append",
        json={
            "title": "No Topic",
            "body": "body B",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": ["ops"],
        },
    )
    assert no_topic.status_code == 201
    no_topic_id = no_topic.json()["id"]

    unclassified = client.get("/api/v1/notes/search?page=1&page_size=100&unclassified=true")
    assert unclassified.status_code == 200
    unclassified_ids = {item["id"] for item in unclassified.json()["items"]}
    assert no_topic_id in unclassified_ids
    assert with_topic_id not in unclassified_ids

    by_topic = client.get(f"/api/v1/notes/search?page=1&page_size=100&topic_id={topic_id}")
    assert by_topic.status_code == 200
    by_topic_ids = {item["id"] for item in by_topic.json()["items"]}
    assert with_topic_id in by_topic_ids
    assert no_topic_id not in by_topic_ids


def test_patch_note_can_set_topic_and_archive():
    client = make_client()
    topic_id = fixed_topic_id(client)
    created = client.post(
        "/api/v1/notes/append",
        json={
            "title": "Patch Note",
            "body": "body",
            "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
            "tags": [],
        },
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/notes/{note_id}",
        json={"topic_id": topic_id, "status": "archived"},
    )
    assert patched.status_code == 200

    active = client.get("/api/v1/notes/search?page=1&page_size=100")
    assert active.status_code == 200
    active_ids = {item["id"] for item in active.json()["items"]}
    assert note_id not in active_ids

    archived = client.get("/api/v1/notes/search?page=1&page_size=100&status=archived")
    assert archived.status_code == 200
    archived_ids = {item["id"] for item in archived.json()["items"]}
    assert note_id in archived_ids


def test_batch_classify_and_topic_summary():
    client = make_client()
    topic_id = fixed_topic_id(client)
    ids: list[str] = []
    for i in range(2):
        created = client.post(
            "/api/v1/notes/append",
            json={
                "title": f"Batch Note {i}",
                "body": "body",
                "sources": [{"type": "text", "value": f"test://{uniq('note_src')}"}],
                "tags": [],
            },
        )
        assert created.status_code == 201
        ids.append(created.json()["id"])

    classify = client.post(
        "/api/v1/notes/batch-classify",
        json={"note_ids": ids, "topic_id": topic_id},
    )
    assert classify.status_code == 200
    assert classify.json()["updated"] == 2
    assert classify.json()["failed"] == 0

    summary = client.get("/api/v1/notes/topic-summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert "items" in payload
    assert any(item["topic_id"] == topic_id for item in payload["items"])
    assert any(item["topic_id"] is None for item in payload["items"])
