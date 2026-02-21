from src.config import Settings


def test_default_database_url_points_to_245_postgres():
    settings = Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "@192.168.50.245:5432/afkms" in settings.database_url
