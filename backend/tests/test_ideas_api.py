from tests.helpers import create_test_task, fixed_topic_id, make_client, uniq


def test_idea_lifecycle_and_promote_to_route_node():
    client = make_client()
    topic_id = fixed_topic_id(client)
    task_id = create_test_task(client, prefix="idea_parent_task")

    create = client.post(
        "/api/v1/ideas",
        json={
            "task_id": task_id,
            "title": f"idea_test_{uniq('title')}",
            "problem": "Need a better route planning model",
            "hypothesis": "A DAG route model improves strategic execution",
            "status": "captured",
            "topic_id": topic_id,
            "source": f"test://idea/{uniq('src')}",
        },
    )
    assert create.status_code == 201
    idea_id = create.json()["id"]

    for status in ["triage", "discovery", "ready"]:
        patched = client.patch(f"/api/v1/ideas/{idea_id}", json={"status": status})
        assert patched.status_code == 200
        assert patched.json()["status"] == status

    route = client.post(
        "/api/v1/routes",
        json={
            "task_id": task_id,
            "name": f"route_test_{uniq('name')}",
            "goal": "Ship route graph v1",
            "status": "candidate",
        },
    )
    assert route.status_code == 201
    route_id = route.json()["id"]

    promoted = client.post(
        f"/api/v1/ideas/{idea_id}/promote",
        json={"route_id": route_id, "node_type": "goal"},
    )
    assert promoted.status_code == 201
    promoted_body = promoted.json()
    assert promoted_body["route_id"] == route_id
    assert promoted_body["node_type"] == "goal"


def test_idea_invalid_transition_rejected():
    client = make_client()
    task_id = create_test_task(client, prefix="idea_invalid_task")
    create = client.post(
        "/api/v1/ideas",
        json={
            "task_id": task_id,
            "title": f"idea_test_{uniq('title')}",
            "status": "captured",
            "source": f"test://idea/{uniq('src')}",
        },
    )
    assert create.status_code == 201
    idea_id = create.json()["id"]

    invalid = client.patch(f"/api/v1/ideas/{idea_id}", json={"status": "ready"})
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "IDEA_INVALID_STATUS_TRANSITION"


def test_promote_requires_ready_status():
    client = make_client()
    task_id = create_test_task(client, prefix="idea_promote_task")

    create = client.post(
        "/api/v1/ideas",
        json={
            "task_id": task_id,
            "title": f"idea_test_{uniq('title')}",
            "status": "captured",
            "source": f"test://idea/{uniq('src')}",
        },
    )
    assert create.status_code == 201
    idea_id = create.json()["id"]

    route = client.post(
        "/api/v1/routes",
        json={
            "task_id": task_id,
            "name": f"route_test_{uniq('name')}",
            "goal": "Temp route",
            "status": "candidate",
        },
    )
    assert route.status_code == 201
    route_id = route.json()["id"]

    promoted = client.post(
        f"/api/v1/ideas/{idea_id}/promote",
        json={"route_id": route_id, "node_type": "goal"},
    )
    assert promoted.status_code == 409
    assert promoted.json()["error"]["code"] == "IDEA_NOT_READY"
