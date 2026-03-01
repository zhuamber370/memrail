import pytest

from src.app import create_app
from tests.helpers import make_client


def test_api_key_required_when_auth_enabled():
    client = make_client(require_auth=True, api_key="secret")

    no_auth = client.get("/api/v1/tasks")
    assert no_auth.status_code == 401
    body = no_auth.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["request_id"]

    ok = client.get("/api/v1/tasks", headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


def test_options_preflight_not_blocked_by_auth():
    client = make_client(require_auth=True, api_key="secret")
    res = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code in (200, 204)


def test_options_preflight_allows_localhost_custom_port():
    client = make_client(require_auth=True, api_key="secret")
    res = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://localhost:3002",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code in (200, 204)


def test_auth_enabled_requires_api_key():
    with pytest.raises(RuntimeError, match="KMS_API_KEY"):
        create_app(database_url="sqlite+pysqlite:////tmp/memlineage-auth-test.db", require_auth=True, api_key="")
