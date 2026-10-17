"""Integration tests for the warehouse dimensional model (004_dims_fact.sql).

Covers: table existence, column sets, PK/UNIQUE constraints, FK enforcement
(fact_crime -> dims), NULLable FKs, NULLS NOT DISTINCT natural keys and the
fact indexes. The population from staging comes in Paso 4; here we only
verify structure and constraint semantics with hand-inserted rows.
"""

import psycopg2
import pytest
from conftest import apply_migration

WAREHOUSE_TABLES = {
    "dim_date",
    "dim_crime_type",
    "dim_location",
    "dim_district",
    "dim_community_area",
    "fact_crime",
}

FACT_COLUMNS = {
    "crime_key",
    "crime_id",
    "date_key",
    "crime_type_key",
    "location_key",
    "community_area_key",
    "district_key",
    "hour",
    "arrest",
    "domestic",
    "latitude",
    "longitude",
}

SEED_DATE_SQL = """
INSERT INTO warehouse.dim_date
    (date_key, full_date, year, month, month_name, week, day_of_week, day_name, is_weekend)
VALUES (20260915, '2026-09-15', 2026, 9, 'September', 38, 2, 'Tuesday', false)
"""

FACT_SQL = """
INSERT INTO warehouse.fact_crime
    (crime_id, date_key, crime_type_key, location_key, community_area_key,
     district_key, hour, arrest, domestic, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


@pytest.fixture(scope="module")
def dims_db(migrated_db):
    """Aplica 004_dims_fact.sql; limpia warehouse al terminar el módulo."""
    apply_migration(migrated_db, "004_dims_fact.sql")
    yield migrated_db
    with migrated_db.cursor() as cur:
        cur.execute(
            "TRUNCATE warehouse.fact_crime, warehouse.dim_date, "
            "warehouse.dim_crime_type, warehouse.dim_location, "
            "warehouse.dim_district, warehouse.dim_community_area "
            "RESTART IDENTITY CASCADE"
        )


@pytest.fixture(scope="module")
def seeded_date(dims_db):
    """Una fila de dim_date para los tests que insertan en fact_crime
    (independiente del orden de ejecución de los tests)."""
    with dims_db.cursor() as cur:
        cur.execute(SEED_DATE_SQL + " ON CONFLICT (date_key) DO NOTHING")
    return dims_db


def test_migration_is_idempotent(dims_db):
    apply_migration(dims_db, "004_dims_fact.sql")


def test_warehouse_tables_exist(dims_db):
    with dims_db.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'warehouse' AND table_type = 'BASE TABLE'"
        )
        actual = {row[0] for row in cur.fetchall()}
    # filtro BASE TABLE: el schema también contiene views analíticas
    # (Sprint 4, database/views/analytics.sql) que no son tablas
    assert actual == WAREHOUSE_TABLES


def test_fact_crime_columns(dims_db):
    with dims_db.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'warehouse' AND table_name = 'fact_crime'"
        )
        actual = {row[0] for row in cur.fetchall()}
    assert actual == FACT_COLUMNS


def test_dim_date_date_key_is_pk_and_full_date_unique(dims_db):
    with dims_db.cursor() as cur:
        cur.execute(
            """
            SELECT kcu.column_name, tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'warehouse' AND tc.table_name = 'dim_date'
            """
        )
        constraints = {(col, ctype) for col, ctype in cur.fetchall()}
    assert ("date_key", "PRIMARY KEY") in constraints
    assert ("full_date", "UNIQUE") in constraints


def test_fact_crime_crime_id_enforces_unique(seeded_date):
    with seeded_date.cursor() as cur:
        cur.execute(FACT_SQL, ("DIM-01", 20260915, None, None, None, None, 10, True, False, 41.87, -87.62))
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(FACT_SQL, ("DIM-01", 20260915, None, None, None, None, 11, False, True, 41.9, -87.7))


def test_fact_crime_fk_enforced_on_bogus_date_key(dims_db):
    with dims_db.cursor() as cur, pytest.raises(psycopg2.errors.ForeignKeyViolation):
        cur.execute(
            FACT_SQL, ("DIM-02", 99999999, None, None, None, None, 10, True, False, None, None)
        )


def test_fact_crime_nullable_dim_fks_accepted(seeded_date):
    # community_area NULL is legitimate (old records): the FK must allow it
    with seeded_date.cursor() as cur:
        cur.execute(FACT_SQL, ("DIM-03", 20260915, None, None, None, None, 23, False, False, None, None))
        cur.execute(
            "SELECT count(*) FROM warehouse.fact_crime WHERE crime_id = 'DIM-03' "
            "AND community_area_key IS NULL"
        )
        (rows,) = cur.fetchone()
    assert rows == 1


def test_fact_crime_hour_check(seeded_date):
    with seeded_date.cursor() as cur, pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute(
            FACT_SQL, ("DIM-04", 20260915, None, None, None, None, 24, True, False, None, None)
        )


def test_dim_crime_type_natural_key_dedupes_nulls(dims_db):
    # NULLS NOT DISTINCT: two rows (NULL, 'THEFT', NULL) must conflict
    with dims_db.cursor() as cur:
        cur.execute(
            "INSERT INTO warehouse.dim_crime_type (iucr, primary_type, description) "
            "VALUES (NULL, 'THEFT', NULL)"
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                "INSERT INTO warehouse.dim_crime_type (iucr, primary_type, description) "
                "VALUES (NULL, 'THEFT', NULL)"
            )


def test_fact_crime_indexes_exist(dims_db):
    with dims_db.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'warehouse' AND tablename = 'fact_crime'"
        )
        actual = {row[0] for row in cur.fetchall()}
    assert {
        "idx_fact_crime_date",
        "idx_fact_crime_community_area",
        "idx_fact_crime_crime_type",
    } <= actual
