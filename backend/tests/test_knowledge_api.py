from typing import Optional

from tests.helpers import fixed_topic_id, make_client, uniq


def _playbook_payload(*, topic_id: Optional[str], marker: str):
    return {
        "type": "playbook",
        "title": f"playbook_{marker}",
        "topic_id": topic_id,
        "tags": ["runbook", "ops"],
        "content": {
            "goal": "stabilize service",
            "steps": ["check health", "inspect logs"],
        },
        "evidences": [
            {
                "source_ref": f"chat://knowledge/{marker}",
                "excerpt": "runbook notes",
            }
        ],
    }


def _append_note(
    client,
    *,
    title: str,
    body: str,
    topic_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> str:
    created = client.post(
        "/api/v1/notes/append",
        json={
            "title": title,
            "body": body,
            "topic_id": topic_id,
            "sources": [{"type": "text", "value": f"test://knowledge-migration/{uniq('note_src')}"}],
            "tags": tags or [],
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_create_and_get_knowledge_item():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = uniq("kb_create")
    created = client.post("/api/v1/knowledge", json=_playbook_payload(topic_id=topic_id, marker=marker))
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    fetched = client.get(f"/api/v1/knowledge/{item_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == item_id
    assert body["type"] == "playbook"
    assert body["topic_id"] == topic_id
    assert body["evidence_count"] == 1
    assert len(body["evidences"]) == 1


def test_create_knowledge_requires_evidence():
    client = make_client()
    marker = uniq("kb_evidence")
    payload = _playbook_payload(topic_id=None, marker=marker)
    payload["evidences"] = []
    created = client.post("/api/v1/knowledge", json=payload)
    assert created.status_code == 422


def test_create_knowledge_validates_minimum_content_shape():
    client = make_client()
    marker = uniq("kb_schema")
    payload = _playbook_payload(topic_id=None, marker=marker)
    payload["content"] = {"goal": "x"}
    created = client.post("/api/v1/knowledge", json=payload)
    assert created.status_code == 422


def test_list_knowledge_filters_type_topic_and_status():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = uniq("kb_filter")

    playbook = _playbook_payload(topic_id=topic_id, marker=f"{marker}_playbook")
    decision = {
        "type": "decision",
        "title": f"decision_{marker}",
        "topic_id": topic_id,
        "tags": ["strategy"],
        "content": {
            "decision": "ship v1 first",
            "rationale": "reduce risk",
        },
        "evidences": [{"source_ref": f"chat://knowledge/{marker}/d", "excerpt": "decision basis"}],
    }

    c1 = client.post("/api/v1/knowledge", json=playbook)
    c2 = client.post("/api/v1/knowledge", json=decision)
    assert c1.status_code == 201, c1.text
    assert c2.status_code == 201, c2.text
    decision_id = c2.json()["id"]

    archived = client.post(f"/api/v1/knowledge/{decision_id}/archive")
    assert archived.status_code == 200, archived.text

    active_list = client.get(f"/api/v1/knowledge?page=1&page_size=100&type=playbook&topic_id={topic_id}&status=active")
    assert active_list.status_code == 200
    active_ids = {item["id"] for item in active_list.json()["items"]}
    assert c1.json()["id"] in active_ids
    assert decision_id not in active_ids

    archived_list = client.get("/api/v1/knowledge?page=1&page_size=100&type=decision&status=archived")
    assert archived_list.status_code == 200
    archived_ids = {item["id"] for item in archived_list.json()["items"]}
    assert decision_id in archived_ids


def test_append_evidence_to_existing_knowledge():
    client = make_client()
    marker = uniq("kb_evidence_append")
    created = client.post("/api/v1/knowledge", json=_playbook_payload(topic_id=None, marker=marker))
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    appended = client.post(
        f"/api/v1/knowledge/{item_id}/evidences",
        json={"source_ref": f"chat://knowledge/{marker}/2", "excerpt": "follow-up proof"},
    )
    assert appended.status_code == 201, appended.text

    detail = client.get(f"/api/v1/knowledge/{item_id}")
    assert detail.status_code == 200
    assert detail.json()["evidence_count"] == 2
    assert len(detail.json()["evidences"]) == 2


def test_migration_candidates_infer_type_and_exclude_migrated_note():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = uniq("kb_migrate_candidates")

    decision_note_id = _append_note(
        client,
        title=f"Decision {marker}",
        body="Final choice: use option A because risk is lower.",
        topic_id=topic_id,
        tags=["strategy"],
    )
    playbook_note_id = _append_note(
        client,
        title=f"Incident Playbook {marker}",
        body="- detect issue\n- contain blast radius\n- verify recovery",
        topic_id=topic_id,
        tags=["ops"],
    )
    brief_note_id = _append_note(
        client,
        title=f"Weekly brief {marker}",
        body="Customer trend update and one-line summary.",
        topic_id=topic_id,
        tags=["report"],
    )

    listed = client.get("/api/v1/knowledge/migration/candidates?page=1&page_size=20")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    by_note = {item["note_id"]: item for item in payload["items"]}

    assert by_note[decision_note_id]["inferred_type"] == "decision"
    assert by_note[playbook_note_id]["inferred_type"] == "playbook"
    assert by_note[brief_note_id]["inferred_type"] == "brief"

    committed = client.post(
        "/api/v1/knowledge/migration/commit",
        json={"note_ids": [decision_note_id]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["migrated"] == 1

    listed_after = client.get("/api/v1/knowledge/migration/candidates?page=1&page_size=20")
    assert listed_after.status_code == 200, listed_after.text
    note_ids_after = {item["note_id"] for item in listed_after.json()["items"]}
    assert decision_note_id not in note_ids_after


def test_migration_commit_enforces_batch_limit_and_writes_knowledge_with_evidence():
    client = make_client()
    marker = uniq("kb_migrate_commit")

    over_limit_note_ids: list[str] = []
    for index in range(21):
        over_limit_note_ids.append(
            _append_note(
                client,
                title=f"Over limit {marker}-{index}",
                body="batch limit validation",
                tags=["limit"],
            )
        )

    over_limit = client.post(
        "/api/v1/knowledge/migration/commit",
        json={"note_ids": over_limit_note_ids},
    )
    assert over_limit.status_code == 422

    note_a = _append_note(
        client,
        title=f"Decision record {marker}",
        body="Decision: pick blue rollout for lower risk.",
        tags=["decision"],
    )
    note_b = _append_note(
        client,
        title=f"Playbook guide {marker}",
        body="- prepare\n- execute\n- verify",
        tags=["playbook"],
    )

    commit_ok = client.post(
        "/api/v1/knowledge/migration/commit",
        json={"note_ids": [note_a, note_b]},
    )
    assert commit_ok.status_code == 200, commit_ok.text
    body = commit_ok.json()
    assert body["migrated"] == 2
    assert body["failed"] == 0
    assert len(body["migrations"]) == 2

    for row in body["migrations"]:
        detail = client.get(f"/api/v1/knowledge/{row['item_id']}")
        assert detail.status_code == 200, detail.text
        source_refs = {ev["source_ref"] for ev in detail.json()["evidences"]}
        assert f"note://{row['note_id']}" in source_refs
