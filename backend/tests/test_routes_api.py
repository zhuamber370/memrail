from tests.helpers import create_test_task, make_client, uniq


def test_single_active_route_enforced():
    client = make_client()
    task_id = create_test_task(client, prefix="route_active_task")

    active_list = client.get(f"/api/v1/routes?page=1&page_size=100&status=active&task_id={task_id}")
    assert active_list.status_code == 200
    active_items = active_list.json()["items"]

    seeded_active_id = None
    if not active_items:
        seeded = client.post(
            "/api/v1/routes",
            json={
                "task_id": task_id,
                "name": f"route_test_{uniq('seed')}",
                "goal": "seed active route for test",
                "status": "active",
            },
        )
        assert seeded.status_code == 201
        seeded_active_id = seeded.json()["id"]

    candidate = client.post(
        "/api/v1/routes",
        json={
            "task_id": task_id,
            "name": f"route_test_{uniq('cand')}",
            "goal": "candidate route",
            "status": "candidate",
        },
    )
    assert candidate.status_code == 201
    candidate_id = candidate.json()["id"]

    to_active = client.patch(f"/api/v1/routes/{candidate_id}", json={"status": "active"})
    assert to_active.status_code == 409
    assert to_active.json()["error"]["code"] == "ROUTE_ACTIVE_CONFLICT"

    if seeded_active_id:
        park_seeded = client.patch(f"/api/v1/routes/{seeded_active_id}", json={"status": "parked"})
        assert park_seeded.status_code == 200


def test_route_nodes_edges_and_logs():
    client = make_client()
    task_id = create_test_task(client, prefix="route_graph_task")

    route1 = client.post(
        "/api/v1/routes",
        json={
            "task_id": task_id,
            "name": f"route_test_{uniq('r1')}",
            "goal": "route graph path 1",
            "status": "candidate",
        },
    )
    assert route1.status_code == 201
    route1_id = route1.json()["id"]

    route2 = client.post(
        "/api/v1/routes",
        json={
            "task_id": task_id,
            "name": f"route_test_{uniq('r2')}",
            "goal": "route graph path 2",
            "status": "candidate",
        },
    )
    assert route2.status_code == 201
    route2_id = route2.json()["id"]

    n1 = client.post(
        f"/api/v1/routes/{route1_id}/nodes",
        json={"node_type": "decision", "title": "Choose direction", "description": "compare options"},
    )
    assert n1.status_code == 201
    n1_id = n1.json()["id"]

    n2 = client.post(
        f"/api/v1/routes/{route1_id}/nodes",
        json={"node_type": "task", "title": "Build MVP", "description": "ship first version"},
    )
    assert n2.status_code == 201
    n2_id = n2.json()["id"]

    edge = client.post(
        f"/api/v1/routes/{route1_id}/edges",
        json={"from_node_id": n1_id, "to_node_id": n2_id, "relation": "depends_on"},
    )
    assert edge.status_code == 201

    graph = client.get(f"/api/v1/routes/{route1_id}/graph")
    assert graph.status_code == 200
    graph_body = graph.json()
    assert graph_body["route_id"] == route1_id
    assert any(item["id"] == n1_id for item in graph_body["nodes"])
    assert any(item["id"] == n2_id for item in graph_body["nodes"])
    assert any(item["from_node_id"] == n1_id and item["to_node_id"] == n2_id for item in graph_body["edges"])

    other_node = client.post(
        f"/api/v1/routes/{route2_id}/nodes",
        json={"node_type": "task", "title": "Cross route node", "description": "cross route"},
    )
    assert other_node.status_code == 201
    other_node_id = other_node.json()["id"]

    cross = client.post(
        f"/api/v1/routes/{route1_id}/edges",
        json={"from_node_id": n1_id, "to_node_id": other_node_id, "relation": "depends_on"},
    )
    assert cross.status_code == 422
    assert cross.json()["error"]["code"] == "ROUTE_EDGE_CROSS_ROUTE"

    log_append = client.post(
        f"/api/v1/routes/{route1_id}/nodes/{n1_id}/logs",
        json={"content": f"log_test_{uniq('log')}", "actor_type": "human", "actor_id": "tester"},
    )
    assert log_append.status_code == 201

    logs = client.get(f"/api/v1/routes/{route1_id}/nodes/{n1_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["items"]

    rename = client.patch(
        f"/api/v1/routes/{route1_id}/nodes/{n2_id}",
        json={"title": "Build MVP v2"},
    )
    assert rename.status_code == 200
    assert rename.json()["title"] == "Build MVP v2"

    delete_node = client.delete(f"/api/v1/routes/{route1_id}/nodes/{n1_id}")
    assert delete_node.status_code == 204

    graph_after_delete = client.get(f"/api/v1/routes/{route1_id}/graph")
    assert graph_after_delete.status_code == 200
    body = graph_after_delete.json()
    assert all(item["id"] != n1_id for item in body["nodes"])
    assert all(item["from_node_id"] != n1_id and item["to_node_id"] != n1_id for item in body["edges"])

    logs_after_delete = client.get(f"/api/v1/routes/{route1_id}/nodes/{n1_id}/logs")
    assert logs_after_delete.status_code == 404
    assert logs_after_delete.json()["error"]["code"] == "ROUTE_NODE_NOT_FOUND"

    delete_again = client.delete(f"/api/v1/routes/{route1_id}/nodes/{n1_id}")
    assert delete_again.status_code == 404
    assert delete_again.json()["error"]["code"] == "ROUTE_NODE_NOT_FOUND"
