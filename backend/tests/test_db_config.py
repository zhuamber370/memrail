from src.config import Settings


def test_default_database_url_points_to_local_postgres(monkeypatch):
    monkeypatch.delenv("AFKMS_DB_HOST", raising=False)
    monkeypatch.delenv("AFKMS_DB_PORT", raising=False)
    monkeypatch.delenv("AFKMS_DB_NAME", raising=False)
    monkeypatch.delenv("AFKMS_DB_USER", raising=False)
    monkeypatch.delenv("AFKMS_DB_PASSWORD", raising=False)
    settings = Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "@127.0.0.1:5432/afkms" in settings.database_url
