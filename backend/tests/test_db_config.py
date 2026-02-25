import pytest

from src.config import Settings


def test_default_database_url_uses_sqlite(monkeypatch):
    monkeypatch.delenv("AFKMS_DATABASE_URL", raising=False)
    monkeypatch.delenv("AFKMS_DB_BACKEND", raising=False)
    monkeypatch.delenv("AFKMS_SQLITE_PATH", raising=False)
    monkeypatch.delenv("AFKMS_DB_HOST", raising=False)
    monkeypatch.delenv("AFKMS_DB_PORT", raising=False)
    monkeypatch.delenv("AFKMS_DB_NAME", raising=False)
    monkeypatch.delenv("AFKMS_DB_USER", raising=False)
    monkeypatch.delenv("AFKMS_DB_PASSWORD", raising=False)
    settings = Settings()
    assert settings.database_url.startswith("sqlite+pysqlite:///")
    assert settings.database_url.endswith("/data/afkms.sqlite3")


def test_database_url_can_switch_to_postgres(monkeypatch):
    monkeypatch.delenv("AFKMS_DATABASE_URL", raising=False)
    monkeypatch.setenv("AFKMS_DB_BACKEND", "postgres")
    monkeypatch.setenv("AFKMS_DB_HOST", "192.168.50.245")
    monkeypatch.setenv("AFKMS_DB_PORT", "5432")
    monkeypatch.setenv("AFKMS_DB_NAME", "afkms")
    monkeypatch.setenv("AFKMS_DB_USER", "afkms")
    monkeypatch.setenv("AFKMS_DB_PASSWORD", "afkms")
    settings = Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "@192.168.50.245:5432/afkms" in settings.database_url


def test_database_url_prefers_explicit_override(monkeypatch):
    monkeypatch.setenv("AFKMS_DATABASE_URL", "sqlite+pysqlite:////tmp/afkms-test.db")
    monkeypatch.setenv("AFKMS_DB_BACKEND", "postgres")
    settings = Settings()
    assert settings.database_url == "sqlite+pysqlite:////tmp/afkms-test.db"


def test_auth_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("AFKMS_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("KMS_API_KEY", raising=False)
    settings = Settings()
    assert settings.require_auth is False
    assert settings.kms_api_key == ""


def test_auth_can_be_enabled_via_env(monkeypatch):
    monkeypatch.setenv("AFKMS_REQUIRE_AUTH", "true")
    monkeypatch.setenv("KMS_API_KEY", "secret-key")
    settings = Settings()
    assert settings.require_auth is True
    assert settings.kms_api_key == "secret-key"


def test_auth_rejects_invalid_bool(monkeypatch):
    monkeypatch.setenv("AFKMS_REQUIRE_AUTH", "invalid")
    with pytest.raises(ValueError, match="AFKMS_REQUIRE_AUTH"):
        Settings()
