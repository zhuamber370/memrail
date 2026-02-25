import os
import uuid
from typing import Optional

from fastapi.testclient import TestClient

from src.app import create_app


def database_url() -> str:
    host = os.getenv("AFKMS_DB_HOST", "127.0.0.1")
    port = os.getenv("AFKMS_DB_PORT", "5432")
    name = os.getenv("AFKMS_DB_NAME", "afkms")
    user = os.getenv("AFKMS_DB_USER", "afkms")
    password = os.getenv("AFKMS_DB_PASSWORD", "afkms")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def make_client(*, require_auth: bool = False, api_key: Optional[str] = None) -> TestClient:
    app = create_app(database_url(), require_auth=require_auth, api_key=api_key)
    return TestClient(app)


def fixed_topic_id(client: TestClient, preferred_id: str = "top_fx_engineering_arch") -> str:
    listed = client.get("/api/v1/topics")
    assert listed.status_code == 200
    items = listed.json()["items"]
    for item in items:
        if item["id"] == preferred_id:
            return item["id"]
    assert items, "expected at least one active fixed topic"
    return items[0]["id"]


def uniq(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def create_test_task(client: TestClient, *, prefix: str = "task") -> str:
    topic_id = fixed_topic_id(client)
    resp = client.post(
        "/api/v1/tasks",
        json={
            "title": f"{prefix}_{uniq('title')}",
            "topic_id": topic_id,
            "status": "todo",
            "source": f"test://task/{uniq('src')}",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]
