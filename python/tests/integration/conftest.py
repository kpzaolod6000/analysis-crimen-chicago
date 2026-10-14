"""Fixtures compartidos para los tests de integración contra PostgreSQL.

La DB de pruebas vive en Docker (puerto 5433, ver docker-compose.test.yml),
aislada de desarrollo (5432). Conexión configurable por variables de entorno:

    TEST_POSTGRES_HOST (localhost), TEST_POSTGRES_PORT (5433),
    TEST_POSTGRES_USER (postgres), TEST_POSTGRES_PASSWORD (postgres),
    TEST_POSTGRES_DB (chicago_crimes_test)
"""

import os
import sys
from pathlib import Path

import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "database" / "migrations"

# Bootstrap: hace importable python/src (mismo patrón que tests/unit/conftest.py)
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def get_test_dsn():
    return {
        "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("TEST_POSTGRES_PORT", "5433")),
        "user": os.getenv("TEST_POSTGRES_USER", "postgres"),
        "password": os.getenv("TEST_POSTGRES_PASSWORD", "postgres"),
        "dbname": os.getenv("TEST_POSTGRES_DB", "chicago_crimes_test"),
    }


def apply_migration(conn, filename: str) -> None:
    sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)


@pytest.fixture(scope="session")
def db_conn():
    """Conexión a la DB de pruebas (una por sesión, autocommit)."""
    conn = psycopg2.connect(**get_test_dsn())
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def migrated_db(db_conn):
    """Aplica 001_raw.sql al inicio de la sesión (idempotente)."""
    apply_migration(db_conn, "001_raw.sql")
    return db_conn
