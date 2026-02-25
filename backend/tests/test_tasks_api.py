from tests.helpers import fixed_topic_id, make_client, uniq


def test_create_task_rejects_unknown_field():
    client = make_client()
    topic_id = fixed_topic_id(client)

    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
            "unknown": "x",
        },
    )

    assert res.status_code == 422


def test_create_and_list_tasks():
    client = make_client()
    marker = f"test://{uniq('task_source')}"
    topic_id = fixed_topic_id(client)

    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": marker,
            "topic_id": topic_id,
            "description": "detail",
            "acceptance_criteria": "done when done",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["id"].startswith("tsk_")
    assert body["status"] == "todo"
    assert body["topic_id"] == topic_id

    listed = client.get("/api/v1/tasks?page=1&page_size=20")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["total"] >= 1
    assert any(item["id"] == body["id"] for item in listed_body["items"])


def test_patch_task_status():
    client = make_client()
    topic_id = fixed_topic_id(client)

    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert patch.status_code == 200
    assert patch.json()["status"] == "in_progress"


def test_patch_task_invalid_status_transition_returns_409():
    client = make_client()
    topic_id = fixed_topic_id(client)
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Done",
            "status": "done",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert patch.status_code == 409
    body = patch.json()
    assert body["error"]["code"] == "TASK_INVALID_STATUS_TRANSITION"


def test_batch_update_tasks():
    client = make_client()
    topic_id = fixed_topic_id(client)
    ids = []
    for i in range(2):
        create = client.post(
            "/api/v1/tasks",
            json={
                "title": f"Task Batch {i}",
                "status": "todo",
                "priority": "P3",
                "source": "test://tasks",
                "topic_id": topic_id,
            },
        )
        ids.append(create.json()["id"])

    updated = client.post(
        "/api/v1/tasks/batch-update",
        json={"task_ids": ids, "patch": {"priority": "P1"}},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["updated"] == 2
    assert body["failed"] == 0


def test_reopen_task():
    client = make_client()
    topic_id = fixed_topic_id(client)
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Reopen",
            "status": "done",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    task_id = create.json()["id"]

    reopened = client.post(f"/api/v1/tasks/{task_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "todo"


def test_task_views_summary():
    client = make_client()
    res = client.get("/api/v1/tasks/views/summary")
    assert res.status_code == 200
    body = res.json()
    for key in ["today", "overdue", "this_week", "backlog", "blocked", "done"]:
        assert key in body


def test_patch_task_can_clear_due_with_null():
    client = make_client()
    topic_id = fixed_topic_id(client)
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Clear Fields",
            "status": "todo",
            "priority": "P2",
            "due": "2026-03-01",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"due": None})
    assert patch.status_code == 200
    body = patch.json()
    assert body["due"] is None


def test_delete_task_hard_delete():
    client = make_client()
    topic_id = fixed_topic_id(client)
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Delete",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    delete = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete.status_code == 204

    listed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed.status_code == 200
    assert all(item["id"] != task_id for item in listed.json()["items"])

    delete_again = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_again.status_code == 404


def test_create_task_rejects_project_field():
    client = make_client()
    topic_id = fixed_topic_id(client)
    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task With Project",
            "status": "todo",
            "priority": "P2",
            "project": "Core",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert res.status_code == 422


def test_create_task_rejects_legacy_execution_fields():
    client = make_client()
    topic_id = fixed_topic_id(client)
    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task With Legacy Fields",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
            "next_action": "legacy",
            "task_type": "build",
            "blocked_by_task_id": "tsk_legacy",
            "next_review_at": "2026-03-01T00:00:00Z",
        },
    )
    assert res.status_code == 422


def test_create_task_requires_topic_id():
    client = make_client()
    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "No Topic",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
        },
    )
    assert res.status_code == 422


def test_create_task_rejects_unknown_topic():
    client = make_client()
    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Bad Topic",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": "top_missing",
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "TOPIC_NOT_FOUND"


def test_patch_task_cancel_requires_reason():
    client = make_client()
    topic_id = fixed_topic_id(client)
    created = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Cancel",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    cancelled = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "cancelled"})
    assert cancelled.status_code == 422
    assert cancelled.json()["error"]["code"] == "TASK_CANCEL_REASON_REQUIRED"

    cancelled_ok = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "cancelled", "cancelled_reason": "No longer needed in current phase"},
    )
    assert cancelled_ok.status_code == 200
    assert cancelled_ok.json()["status"] == "cancelled"
    assert cancelled_ok.json()["cancelled_reason"] == "No longer needed in current phase"


def test_archive_cancelled_tasks_hides_from_default_list():
    client = make_client()
    topic_id = fixed_topic_id(client)
    created = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Archive Cancelled",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    cancelled = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "cancelled", "cancelled_reason": "Superseded by newer plan"},
    )
    assert cancelled.status_code == 200

    archived = client.post("/api/v1/tasks/archive-cancelled")
    assert archived.status_code == 200
    assert archived.json()["archived"] >= 1

    listed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed.status_code == 200
    assert all(item["id"] != task_id for item in listed.json()["items"])


def test_archive_selected_tasks_archives_done_and_cancelled_only():
    client = make_client()
    topic_id = fixed_topic_id(client)

    cancelled_create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Selected Archive Cancelled",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert cancelled_create.status_code == 201
    cancelled_task_id = cancelled_create.json()["id"]

    done_create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Selected Archive Done",
            "status": "done",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert done_create.status_code == 201
    done_task_id = done_create.json()["id"]

    todo_create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Selected Archive Todo",
            "status": "todo",
            "priority": "P2",
            "source": "test://tasks",
            "topic_id": topic_id,
        },
    )
    assert todo_create.status_code == 201
    todo_task_id = todo_create.json()["id"]

    cancelled = client.patch(
        f"/api/v1/tasks/{cancelled_task_id}",
        json={"status": "cancelled", "cancelled_reason": "No longer needed"},
    )
    assert cancelled.status_code == 200

    archived = client.post(
        "/api/v1/tasks/archive-selected",
        json={"task_ids": [cancelled_task_id, done_task_id, todo_task_id]},
    )
    assert archived.status_code == 200
    assert archived.json()["archived"] == 2

    listed = client.get("/api/v1/tasks?page=1&page_size=100")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()["items"]}
    assert cancelled_task_id not in ids
    assert done_task_id not in ids
    assert todo_task_id in ids

    archived_list = client.get("/api/v1/tasks?page=1&page_size=100&archived=true")
    assert archived_list.status_code == 200
    archived_ids = {item["id"] for item in archived_list.json()["items"]}
    assert cancelled_task_id in archived_ids
    assert done_task_id in archived_ids
    assert todo_task_id not in archived_ids
