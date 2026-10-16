"""Integration tests for the community areas seed (database/seeds/community_areas.sql).

The seed loads the 77 official community areas (tabular dataset igwz-8jzy;
cauq-8yn6 is only its map view) into warehouse.dim_community_area. Tests
apply 004_dims_fact.sql + the seed file and verify the count, the full 1-77
numbering, non-null names, idempotency and the O'Hare apostrophe edge case.
"""

from pathlib import Path

import pytest
from conftest import REPO_ROOT, apply_migration

SEED_PATH = REPO_ROOT / "database" / "seeds" / "community_areas.sql"

EXPECTED_ZONES = {
    6: "Lake View",
    22: "Logan Square",
    32: "Loop",
    41: "Hyde Park",
    76: "O'Hare",
}


@pytest.fixture(scope="module")
def seeded_areas(migrated_db):
    """Aplica 004 + el seed; limpia las tablas tocadas al fin del módulo."""
    apply_migration(migrated_db, "004_dims_fact.sql")
    with migrated_db.cursor() as cur:
        cur.execute(SEED_PATH.read_text(encoding="utf-8"))
    yield migrated_db
    with migrated_db.cursor() as cur:
        cur.execute(
            "TRUNCATE warehouse.fact_crime, warehouse.dim_community_area "
            "RESTART IDENTITY CASCADE"
        )


def _seed_sql():
    return SEED_PATH.read_text(encoding="utf-8")


def test_seed_is_idempotent(seeded_areas):
    # re-aplica el seed completo: UPSERT debe mantener el total en 77
    with seeded_areas.cursor() as cur:
        cur.execute(_seed_sql())
        cur.execute("SELECT count(*) FROM warehouse.dim_community_area")
        (total,) = cur.fetchone()
    assert total == 77


def test_exactly_77_areas(seeded_areas):
    with seeded_areas.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.dim_community_area")
        (total,) = cur.fetchone()
    assert total == 77


def test_full_numbering_1_to_77(seeded_areas):
    with seeded_areas.cursor() as cur:
        cur.execute("SELECT community_area FROM warehouse.dim_community_area")
        actual = {row[0] for row in cur.fetchall()}
    assert actual == set(range(1, 78))


def test_no_null_names(seeded_areas):
    with seeded_areas.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM warehouse.dim_community_area "
            "WHERE community_area_name IS NULL"
        )
        (nulls,) = cur.fetchone()
    assert nulls == 0


def test_ohare_apostrophe(seeded_areas):
    with seeded_areas.cursor() as cur:
        cur.execute(
            "SELECT community_area_name FROM warehouse.dim_community_area "
            "WHERE community_area = 76"
        )
        (name,) = cur.fetchone()
    assert name == "O'Hare"


def test_spot_check_names(seeded_areas):
    with seeded_areas.cursor() as cur:
        cur.execute("SELECT community_area, community_area_name FROM warehouse.dim_community_area")
        actual = dict(cur.fetchall())
    for number, expected in EXPECTED_ZONES.items():
        assert actual[number] == expected, f"area {number}: {actual[number]!r} != {expected!r}"
