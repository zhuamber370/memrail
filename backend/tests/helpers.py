import os
import uuid
from typing import Optional

from fastapi.testclient import TestClient

from src.app import create_app


def database_url() -> str:
    host = os.getenv("AFKMS_DB_HOST", "192.168.50.245")
    port = os.getenv("AFKMS_DB_PORT", "5432")
    name = os.getenv("AFKMS_DB_NAME", "afkms")
    user = os.getenv("AFKMS_DB_USER", "afkms")
    password = os.getenv("AFKMS_DB_PASSWORD", "afkms")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def make_client(*, require_auth: bool = False, api_key: Optional[str] = None) -> TestClient:
    app = create_app(database_url(), require_auth=require_auth, api_key=api_key)
    return TestClient(app)


def uniq(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
