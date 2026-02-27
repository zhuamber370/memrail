from tests.helpers import make_client, uniq


OPS_MANUAL = "ops_manual"
MECHANISM_SPEC = "mechanism_spec"
DECISION_RECORD = "decision_record"


def _payload(marker: str, **extra) -> dict:
    payload = {
        "title": f"knowledge_title_{marker}",
        "body": f"knowledge body {marker}",
    }
    payload.update(extra)
    return payload


def test_create_and_get_knowledge_note():
    client = make_client()
    marker = uniq("kb_create")
    created = client.post("/api/v1/knowledge", json=_payload(marker))
    assert created.status_code == 201, created.text
    note_id = created.json()["id"]
    assert created.json()["category"] == MECHANISM_SPEC

    fetched = client.get(f"/api/v1/knowledge/{note_id}")
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert body["id"] == note_id
    assert body["title"] == f"knowledge_title_{marker}"
    assert body["body"] == f"knowledge body {marker}"
    assert body["category"] == MECHANISM_SPEC
    assert body["status"] == "active"


def test_create_knowledge_validates_title_body_and_category():
    client = make_client()
    missing_body = client.post("/api/v1/knowledge", json={"title": "x"})
    assert missing_body.status_code == 422

    missing_title = client.post("/api/v1/knowledge", json={"body": "x"})
    assert missing_title.status_code == 422

    bad_category = client.post("/api/v1/knowledge", json={"title": "x", "body": "y", "category": "bad"})
    assert bad_category.status_code == 422


def test_create_knowledge_supports_manual_category_override():
    client = make_client()
    marker = uniq("kb_manual_cat")
    created = client.post(
        "/api/v1/knowledge",
        json=_payload(marker, category=OPS_MANUAL),
    )
    assert created.status_code == 201, created.text
    assert created.json()["category"] == OPS_MANUAL


def test_list_knowledge_filters_status_query_and_category():
    client = make_client()
    marker = uniq("kb_filter")
    keep = client.post(
        "/api/v1/knowledge",
        json={"title": f"keep_{marker}", "body": "排障命令：执行并验证", "category": OPS_MANUAL},
    )
    archive_me = client.post(
        "/api/v1/knowledge",
        json={"title": f"archive_{marker}", "body": "路线决策：选择 A", "category": DECISION_RECORD},
    )
    assert keep.status_code == 201, keep.text
    assert archive_me.status_code == 201, archive_me.text
    archive_id = archive_me.json()["id"]

    archived = client.post(f"/api/v1/knowledge/{archive_id}/archive")
    assert archived.status_code == 200, archived.text

    active_list = client.get(f"/api/v1/knowledge?page=1&page_size=100&status=active&q={marker}")
    assert active_list.status_code == 200, active_list.text
    active_ids = {item["id"] for item in active_list.json()["items"]}
    assert keep.json()["id"] in active_ids
    assert archive_id not in active_ids
    active_categories = {item["id"]: item["category"] for item in active_list.json()["items"]}
    assert active_categories[keep.json()["id"]] == OPS_MANUAL

    archived_list = client.get(
        f"/api/v1/knowledge?page=1&page_size=100&status=archived&q={marker}&category={DECISION_RECORD}"
    )
    assert archived_list.status_code == 200, archived_list.text
    archived_ids = {item["id"] for item in archived_list.json()["items"]}
    assert archive_id in archived_ids


def test_patch_knowledge_updates_title_body_and_category():
    client = make_client()
    marker = uniq("kb_patch")
    created = client.post("/api/v1/knowledge", json=_payload(marker))
    assert created.status_code == 201, created.text
    note_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/knowledge/{note_id}",
        json={
            "title": f"updated_title_{marker}",
            "body": f"updated body {marker}",
            "category": DECISION_RECORD,
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["title"] == f"updated_title_{marker}"
    assert body["body"] == f"updated body {marker}"
    assert body["category"] == DECISION_RECORD


def test_delete_knowledge_removes_note():
    client = make_client()
    marker = uniq("kb_delete")
    created = client.post("/api/v1/knowledge", json=_payload(marker))
    assert created.status_code == 201, created.text
    note_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/knowledge/{note_id}")
    assert deleted.status_code == 204, deleted.text

    fetched = client.get(f"/api/v1/knowledge/{note_id}")
    assert fetched.status_code == 404, fetched.text
