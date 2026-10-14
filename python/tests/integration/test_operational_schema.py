"""Integration tests for the operational schema (ops.pipeline_runs).

Covers migration 002_operational.sql: schema/table existence, column types,
status CHECK constraint, identity PK and defaults (started_at, run_id).
"""

import psycopg2
import pytest
from conftest import apply_migration

EXPECTED_COLUMNS = {
    "run_id": "bigint",
    "workflow_name": "text",
    "started_at": "timestamp with time zone",
    "finished_at": "timestamp with time zone",
    "status": "text",
    "window_start": "timestamp without time zone",
    "window_end": "timestamp without time zone",
    "records_received": "integer",
    "records_inserted": "integer",
    "records_updated": "integer",
    "records_failed": "integer",
    "error_message": "text",
}


@pytest.fixture(scope="module")
def ops_db(migrated_db):
    apply_migration(migrated_db, "002_operational.sql")
    return migrated_db


def test_ops_schema_exists(ops_db):
    with ops_db.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ops'"
        )
        assert cur.fetchone() is not None


def test_ops_schema_migration_is_idempotent(ops_db):
    apply_migration(ops_db, "002_operational.sql")


def test_pipeline_runs_columns_and_types(ops_db):
    with ops_db.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'ops' AND table_name = 'pipeline_runs'
            """
        )
        actual = dict(cur.fetchall())
    assert set(actual) == set(EXPECTED_COLUMNS)
    for column, expected in EXPECTED_COLUMNS.items():
        assert actual[column] == expected, f"{column}: {actual[column]} != {expected}"


def test_pipeline_runs_run_id_identity_pk(ops_db):
    with ops_db.cursor() as cur:
        cur.execute(
            """
            SELECT tc.constraint_type, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'ops' AND tc.table_name = 'pipeline_runs'
              AND tc.constraint_type = 'PRIMARY KEY'
            """
        )
        pk = cur.fetchone()
    assert pk and pk[1] == "run_id"
    with ops_db.cursor() as cur:
        cur.execute(
            """
            SELECT is_identity FROM information_schema.columns
            WHERE table_schema = 'ops' AND table_name = 'pipeline_runs'
              AND column_name = 'run_id'
            """
        )
        assert cur.fetchone()[0] == "YES"


def test_pipeline_runs_defaults(ops_db):
    with ops_db.cursor() as cur:
        cur.execute("DELETE FROM ops.pipeline_runs WHERE workflow_name = 'TEST-DEFAULTS'")
        cur.execute(
            "INSERT INTO ops.pipeline_runs (workflow_name, status) "
            "VALUES ('TEST-DEFAULTS', 'RUNNING')"
        )
        cur.execute(
            """
            SELECT run_id, started_at, finished_at FROM ops.pipeline_runs
            WHERE workflow_name = 'TEST-DEFAULTS'
            """
        )
        _run_id, started_at, finished_at = cur.fetchone()
        cur.execute("DELETE FROM ops.pipeline_runs WHERE workflow_name = 'TEST-DEFAULTS'")
    assert started_at is not None
    assert finished_at is None


def test_pipeline_runs_status_check_constraint(ops_db):
    with ops_db.cursor() as cur:
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                "INSERT INTO ops.pipeline_runs (workflow_name, status) "
                "VALUES ('TEST-BAD-STATUS', 'INVALID')"
            )
        ops_db.rollback()
