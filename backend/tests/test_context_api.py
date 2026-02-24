from datetime import date

from tests.helpers import fixed_topic_id, make_client, uniq


def _future_date_seed() -> date:
    token = uniq("ctx_jdt")
    day = (sum(ord(c) for c in token) % 28) + 1
    return date(2099, 2, day)


def test_context_bundle_default_excludes_done_tasks():
    client = make_client()
    topic_id = fixed_topic_id(client)
    marker = uniq("ctx")

    todo_task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"context_todo_{marker}",
            "status": "todo",
            "priority": "P1",
            "source": f"test://context/{marker}/todo",
            "topic_id": topic_id,
        },
    )
    assert todo_task.status_code == 201
    todo_id = todo_task.json()["id"]

    done_task = client.post(
        "/api/v1/tasks",
        json={
            "title": f"context_done_{marker}",
            "status": "done",
            "priority": "P2",
            "source": f"test://context/{marker}/done",
            "topic_id": topic_id,
        },
    )
    assert done_task.status_code == 201
    done_id = done_task.json()["id"]

    note = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"context_note_{marker}",
            "body": "context body",
            "topic_id": topic_id,
            "sources": [{"type": "text", "value": f"test://context/{marker}/note"}],
            "tags": ["context"],
        },
    )
    assert note.status_code == 201
    note_id = note.json()["id"]

    journal_date = _future_date_seed()
    journal_marker = f"context_journal_{marker}"
    journal = client.post(
        "/api/v1/journals/upsert-append",
        json={
            "journal_date": journal_date.isoformat(),
            "append_text": journal_marker,
            "source": f"test://context/{marker}/journal",
        },
    )
    assert journal.status_code == 200

    bundle = client.get(
        "/api/v1/context/bundle"
        f"?intent=planning&window_days=90&tasks_limit=200&notes_limit=200&journals_limit=200"
    )
    assert bundle.status_code == 200
    payload = bundle.json()
    task_ids = {item["id"] for item in payload["tasks"]}
    note_ids = {item["id"] for item in payload["notes"]}
    journal_dates = {item["journal_date"] for item in payload["journals"]}

    assert todo_id in task_ids
    assert done_id not in task_ids
    assert note_id in note_ids
    assert journal_date.isoformat() in journal_dates

    with_done = client.get(
        "/api/v1/context/bundle"
        "?intent=planning&window_days=90&include_done=true&tasks_limit=200&notes_limit=200&journals_limit=200"
    )
    assert with_done.status_code == 200
    with_done_ids = {item["id"] for item in with_done.json()["tasks"]}
    assert done_id in with_done_ids


def test_context_bundle_supports_topic_filter():
    client = make_client()
    topics_resp = client.get("/api/v1/topics")
    assert topics_resp.status_code == 200
    topics = topics_resp.json()["items"]
    assert len(topics) >= 2
    topic_a = topics[0]["id"]
    topic_b = topics[1]["id"]
    marker = uniq("ctx_topic")

    task_a = client.post(
        "/api/v1/tasks",
        json={
            "title": f"context_topic_a_{marker}",
            "status": "todo",
            "priority": "P2",
            "source": f"test://context/{marker}/task-a",
            "topic_id": topic_a,
        },
    )
    assert task_a.status_code == 201
    task_a_id = task_a.json()["id"]

    task_b = client.post(
        "/api/v1/tasks",
        json={
            "title": f"context_topic_b_{marker}",
            "status": "todo",
            "priority": "P2",
            "source": f"test://context/{marker}/task-b",
            "topic_id": topic_b,
        },
    )
    assert task_b.status_code == 201
    task_b_id = task_b.json()["id"]

    note_a = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"context_note_a_{marker}",
            "body": "body a",
            "topic_id": topic_a,
            "sources": [{"type": "text", "value": f"test://context/{marker}/note-a"}],
            "tags": [],
        },
    )
    assert note_a.status_code == 201
    note_a_id = note_a.json()["id"]

    note_b = client.post(
        "/api/v1/notes/append",
        json={
            "title": f"context_note_b_{marker}",
            "body": "body b",
            "topic_id": topic_b,
            "sources": [{"type": "text", "value": f"test://context/{marker}/note-b"}],
            "tags": [],
        },
    )
    assert note_b.status_code == 201
    note_b_id = note_b.json()["id"]

    bundle = client.get(
        "/api/v1/context/bundle"
        f"?intent=topic-filter&topic_id={topic_a}&window_days=90&tasks_limit=200&notes_limit=200&journals_limit=50"
    )
    assert bundle.status_code == 200
    payload = bundle.json()
    task_ids = {item["id"] for item in payload["tasks"]}
    note_ids = {item["id"] for item in payload["notes"]}

    assert task_a_id in task_ids
    assert task_b_id not in task_ids
    assert note_a_id in note_ids
    assert note_b_id not in note_ids
