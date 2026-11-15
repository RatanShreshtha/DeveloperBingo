import pytest

from devbingo_backend.app import normalize_database_url


@pytest.mark.parametrize(
    "given, expected",
    [
        (
            "postgres://u:p@host:5432/db",
            "postgresql+psycopg://u:p@host:5432/db",
        ),
        (
            "postgresql://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "postgresql+psycopg://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
    ],
)
def test_host_urls_name_the_psycopg_driver(given, expected):
    assert normalize_database_url(given) == expected
