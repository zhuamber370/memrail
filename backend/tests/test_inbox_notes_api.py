from tests.helpers import make_client, uniq


def test_capture_inbox_and_append_note_validation():
    client = make_client()
    marker = uniq("note_src")

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
