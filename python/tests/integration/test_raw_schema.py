"""Tests de integración de la migración 001_raw.sql.

Verifican contra la DB de pruebas (Docker, puerto 5433) que los schemas y la
tabla raw.crimes existen con los tipos, PK e índice esperados, que la
migración es idempotente y que la PK rechaza duplicados y nulos.

Uso:
    docker compose -f docker-compose.test.yml up -d
    pytest python/tests/integration -v
"""

import psycopg2
import pytest

from conftest import apply_migration

EXPECTED_COLUMNS = {
    "id": "text",
    "case_number": "text",
    "date": "timestamp without time zone",
    "block": "text",
    "iucr": "text",
    "primary_type": "text",
    "description": "text",
    "location_description": "text",
    "arrest": "boolean",
    "domestic": "boolean",
    "beat": "integer",
    "district": "integer",
    "ward": "integer",
    "community_area": "integer",
    "fbi_code": "text",
    "x_coordinate": "double precision",
    "y_coordinate": "double precision",
    "year": "integer",
    "updated_on": "timestamp without time zone",
    "latitude": "double precision",
    "longitude": "double precision",
    "location": "jsonb",
    "loaded_at": "timestamp with time zone",
}


def fetch_column_types(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'raw' AND table_name = 'crimes'
            """
        )
        return dict(cur.fetchall())


def test_schemas_exist(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name IN ('raw', 'staging', 'warehouse')
            """
        )
        found = {row[0] for row in cur.fetchall()}
    assert found == {"raw", "staging", "warehouse"}


def test_raw_crimes_table_exists(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'raw' AND table_name = 'crimes'
            """
        )
        assert cur.fetchone() is not None


def test_raw_crimes_columns_and_types(migrated_db):
    actual = fetch_column_types(migrated_db)
    assert set(actual) == set(EXPECTED_COLUMNS), f"missing/extra: {set(actual) ^ set(EXPECTED_COLUMNS)}"
    for column, expected_type in EXPECTED_COLUMNS.items():
        assert actual[column] == expected_type, f"{column}: {actual[column]} != {expected_type}"


def test_raw_crimes_primary_key_on_id(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'raw' AND tc.table_name = 'crimes'
              AND tc.constraint_type = 'PRIMARY KEY'
            """
        )
        pk_columns = [row[0] for row in cur.fetchall()]
    assert pk_columns == ["id"]


def test_raw_crimes_date_index_exists(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'raw' AND tablename = 'crimes'
              AND indexname = 'idx_raw_crimes_date'
            """
        )
        assert cur.fetchone() is not None


def test_migration_is_idempotent(migrated_db):
    # Re-aplicar no debe fallar ni cambiar la estructura.
    before = fetch_column_types(migrated_db)
    apply_migration(migrated_db, "001_raw.sql")
    assert fetch_column_types(migrated_db) == before


def test_primary_key_rejects_duplicates_and_nulls(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute("DELETE FROM raw.crimes WHERE id IN ('TEST-1', 'TEST-2')")
        cur.execute("INSERT INTO raw.crimes (id) VALUES ('TEST-1')")
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO raw.crimes (id) VALUES ('TEST-1')")
        # rollback solo la sentencia fallida (autocommit: limpia el estado)
        migrated_db.rollback()
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cur.execute("INSERT INTO raw.crimes (id) VALUES (NULL)")
        migrated_db.rollback()
        cur.execute("DELETE FROM raw.crimes WHERE id = 'TEST-1'")


def test_insert_and_select_roundtrip(migrated_db):
    with migrated_db.cursor() as cur:
        cur.execute("DELETE FROM raw.crimes WHERE id = 'TEST-2'")
        cur.execute(
            """
            INSERT INTO raw.crimes (id, case_number, primary_type, year, latitude, longitude)
            VALUES ('TEST-2', 'CN123', 'THEFT', 2024, 41.8781, -87.6298)
            """
        )
        cur.execute(
            "SELECT case_number, primary_type, year, loaded_at "
            "FROM raw.crimes WHERE id = 'TEST-2'"
        )
        row = cur.fetchone()
        assert row[0] == "CN123"
        assert row[1] == "THEFT"
        assert row[2] == 2024
        assert row[3] is not None  # loaded_at defaults to now()
        cur.execute("DELETE FROM raw.crimes WHERE id = 'TEST-2'")
