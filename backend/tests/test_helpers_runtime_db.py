from src.config import Settings
from tests.helpers import database_url


def test_database_url_follows_runtime_settings_by_default(monkeypatch):
    monkeypatch.setenv("AFKMS_DB_BACKEND", "sqlite")
    monkeypatch.delenv("AFKMS_DATABASE_URL", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert database_url() == Settings().database_url


def test_database_url_uses_postgres_on_github_actions_when_backend_unset(monkeypatch):
    monkeypatch.delenv("AFKMS_DB_BACKEND", raising=False)
    monkeypatch.delenv("AFKMS_DATABASE_URL", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("AFKMS_DB_HOST", "127.0.0.1")
    monkeypatch.setenv("AFKMS_DB_PORT", "5432")
    monkeypatch.setenv("AFKMS_DB_NAME", "afkms")
    monkeypatch.setenv("AFKMS_DB_USER", "afkms")
    monkeypatch.setenv("AFKMS_DB_PASSWORD", "afkms")
    assert database_url() == Settings().postgres_url
