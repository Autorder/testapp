import os
import sys

# --------------------------------------------------
# הוספת תיקיית הפרויקט (testapp) ל-Python path
# --------------------------------------------------
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------
# Imports רגילים
# --------------------------------------------------
import importlib
from urllib.parse import urlparse, urlunparse

import psycopg2
import pytest
from psycopg2 import sql


DEFAULT_TEST_DB_NAME = "testapp_test_db"


# --------------------------------------------------
# DB URL helpers
# --------------------------------------------------
def _derive_test_db_url():
    explicit = os.getenv("DATABASE_URL_TEST")
    if explicit:
        return explicit

    base = os.getenv("DATABASE_URL")
    if not base:
        return None

    parsed = urlparse(base)
    return urlunparse(parsed._replace(path=f"/{DEFAULT_TEST_DB_NAME}"))


def _maintenance_db_url(target_db_url):
    parsed = urlparse(target_db_url)
    return urlunparse(parsed._replace(path="/postgres"))


def _db_name(db_url):
    parsed = urlparse(db_url)
    return parsed.path.lstrip("/")


def _ensure_test_db_exists(db_url):
    maintenance_url = _maintenance_db_url(db_url)
    db_name = _db_name(db_url)

    if not db_name:
        raise RuntimeError("Invalid test database URL: missing database name")

    conn = psycopg2.connect(maintenance_url)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,),
            )
            if not cur.fetchone():
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(db_name)
                    )
                )
    finally:
        conn.close()


# --------------------------------------------------
# Fixtures
# --------------------------------------------------
@pytest.fixture(scope="session")
def app_module():
    test_db_url = _derive_test_db_url()
    if not test_db_url:
        pytest.skip(
            "DATABASE_URL or DATABASE_URL_TEST is required for integration tests"
        )

    _ensure_test_db_exists(test_db_url)
    os.environ["DATABASE_URL"] = test_db_url

    # ניקוי cache של מודולים
    for module_name in ("app", "db"):
        if module_name in sys.modules:
            del sys.modules[module_name]

    app_mod = importlib.import_module("app")
    app_mod.app.config.update(TESTING=True)

    return app_mod


@pytest.fixture(scope="session")
def db_module(app_module):
    return importlib.import_module("db")


@pytest.fixture(autouse=True)
def reset_db(db_module):
    db_module.init_db()

    yield

    with db_module.get_cursor() as cur:
        cur.execute(
            """
            TRUNCATE TABLE testapp_appointments, users
            RESTART IDENTITY CASCADE
            """
        )


@pytest.fixture
def client(app_module):
    return app_module.app.test_client()
