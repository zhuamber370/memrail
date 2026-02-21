from tests.helpers import make_client, uniq


def test_create_task_rejects_unknown_field():
    client = make_client()

    res = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "project": "Core",
            "source": "manual",
            "unknown": "x",
        },
    )

    assert res.status_code == 422


def test_create_and_list_tasks():
    client = make_client()
    marker = uniq("task_source")

    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "project": "Core",
            "source": marker,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["id"].startswith("tsk_")
    assert body["status"] == "todo"

    listed = client.get("/api/v1/tasks?page=1&page_size=20")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["total"] >= 1
    assert any(item["id"] == body["id"] for item in listed_body["items"])


def test_patch_task_status():
    client = make_client()

    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task A",
            "status": "todo",
            "priority": "P2",
            "project": "Core",
            "source": "manual",
        },
    )
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert patch.status_code == 200
    assert patch.json()["status"] == "in_progress"


def test_patch_task_invalid_status_transition_returns_409():
    client = make_client()
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Done",
            "status": "done",
            "priority": "P2",
            "project": "Core",
            "source": "manual",
        },
    )
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert patch.status_code == 409
    body = patch.json()
    assert body["error"]["code"] == "TASK_INVALID_STATUS_TRANSITION"


def test_batch_update_tasks():
    client = make_client()
    ids = []
    for i in range(2):
        create = client.post(
            "/api/v1/tasks",
            json={
                "title": f"Task Batch {i}",
                "status": "todo",
                "priority": "P3",
                "project": "Core",
                "source": "manual",
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
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Reopen",
            "status": "done",
            "priority": "P2",
            "project": "Core",
            "source": "manual",
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


def test_patch_task_can_clear_project_and_due_with_null():
    client = make_client()
    create = client.post(
        "/api/v1/tasks",
        json={
            "title": "Task Clear Fields",
            "status": "todo",
            "priority": "P2",
            "project": "Core",
            "due": "2026-03-01",
            "source": "manual",
        },
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    patch = client.patch(f"/api/v1/tasks/{task_id}", json={"project": None, "due": None})
    assert patch.status_code == 200
    body = patch.json()
    assert body["project"] is None
    assert body["due"] is None
