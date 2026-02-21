from tests.helpers import make_client


def test_create_and_list_cycles():
    client = make_client()
    create = client.post(
        "/api/v1/cycles",
        json={
            "name": "Sprint 1",
            "start_date": "2026-02-23",
            "end_date": "2026-03-01",
            "status": "active",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["id"].startswith("cyc_")
    assert body["status"] == "active"

    listed = client.get("/api/v1/cycles")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(item["id"] == body["id"] for item in items)
