from src.config import settings
from tests.helpers import database_url


def test_test_helpers_database_url_follows_runtime_settings():
    assert database_url() == settings.database_url
