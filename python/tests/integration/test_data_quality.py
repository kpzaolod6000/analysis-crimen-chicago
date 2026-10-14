"""Data tests over raw.crimes (docs/testing.md §2.3 + skill chicago-data-quality).

Seeds 12 fixture rows (valid + known-invalid cases) into the test DB (5433)
and checks each ingestion.quality metric against the hand-computed count.
Real data loaded by n8n is checked separately with the smoke script
(python/scripts/check_raw_load.py against dev, 5432).
"""

import pytest
from ingestion import quality

INSERT_SQL = """
INSERT INTO raw.crimes (id, date, primary_type, community_area, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s)
"""

# (id, date, primary_type, community_area, latitude, longitude)
SEED_ROWS = [
    # 6 fully valid rows
    ("DQ-01", "2026-09-01T10:00:00", "THEFT", 25, 41.8781, -87.6298),
    ("DQ-02", "2026-09-02T11:00:00", "BATTERY", 3, 41.9, -87.7),
    ("DQ-03", "2026-09-03T12:00:00", "NARCOTICS", 10, 41.8, -87.6),
    ("DQ-04", "2026-09-04T13:00:00", "ASSAULT", 8, 41.87, -87.62),
    ("DQ-05", "2026-09-05T14:00:00", "ROBBERY", 40, 41.88, -87.63),
    ("DQ-06", "2026-09-06T15:00:00", "BURGLARY", 1, 41.86, -87.64),
    # old-style record: NULL coords and community_area are valid (skill)
    ("DQ-07", "2003-05-02T12:00:00", "BATTERY", None, None, None),
    # (0,0): Socrata sometimes emits a null origin point -> invalid
    ("DQ-08", "2026-09-03T08:30:00", "NARCOTICS", 10, 0.0, 0.0),
    # latitude out of range -> invalid
    ("DQ-09", "2026-09-04T22:15:00", "ASSAULT", 3, 91.0, -87.7),
    # NULL date -> should have been rejected at ingestion
    ("DQ-10", None, "THEFT", 8, 41.9, -87.6),
    # community_area outside the 0-77 catalog -> invalid
    ("DQ-11", "2026-09-05T03:45:00", "ROBBERY", 99, 41.8, -87.7),
    # blank primary_type -> unknown (its NULL community_area is valid)
    ("DQ-12", "2026-09-06T14:00:00", "", None, 41.87, -87.62),
]
# Expected hand-computed metrics: total=12, date nulls=1 (DQ-10),
# latitude/longitude nulls=1 (DQ-07), community_area nulls=2 (DQ-07, DQ-12),
# primary_type nulls=0 (DQ-12 is blank, not NULL), out_of_range=1 (DQ-09),
# zero_coords=1 (DQ-08), invalid_community_area=1 (DQ-11), empty_type=1 (DQ-12).


@pytest.fixture(scope="module")
def seeded_db(migrated_db):
    """raw.crimes with the 12 known fixture rows (fresh state per module)."""
    with migrated_db.cursor() as cur:
        cur.execute("TRUNCATE raw.crimes")
        cur.executemany(INSERT_SQL, SEED_ROWS)
    return migrated_db


def test_total_rows(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.total_rows(cur) == 12


def test_duplicate_ids_zero(seeded_db):
    # 0 by construction (the PK enforces it); validates the metric query runs.
    with seeded_db.cursor() as cur:
        assert quality.duplicate_ids(cur) == 0


def test_null_ids_zero(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.null_ids(cur) == 0


def test_null_counts_date(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.null_counts(cur, "date") == (1, 12)


def test_null_rate_date(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.null_rate(cur, "date") == pytest.approx(1 / 12)


def test_null_rate_latitude(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.null_rate(cur, "latitude") == pytest.approx(1 / 12)


def test_null_rate_primary_type_is_zero(seeded_db):
    # blank string counts as empty (see below), not as NULL
    with seeded_db.cursor() as cur:
        assert quality.null_rate(cur, "primary_type") == 0.0


def test_out_of_range_coordinates(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.out_of_range_coordinates(cur) == 1


def test_zero_coordinates(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.zero_coordinates(cur) == 1


def test_invalid_community_area(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.invalid_community_area(cur) == 1


def test_empty_primary_type(seeded_db):
    with seeded_db.cursor() as cur:
        assert quality.empty_primary_type(cur) == 1


def test_quality_report_shape(seeded_db):
    with seeded_db.cursor() as cur:
        report = quality.quality_report(cur)
    assert set(report) == {
        "total",
        "duplicate_ids",
        "null_ids",
        "out_of_range_coordinates",
        "zero_coordinates",
        "invalid_community_area",
        "empty_primary_type",
        "null_rate",
    }
    assert report["total"] == 12
    assert report["duplicate_ids"] == 0
    assert report["null_rate"]["community_area"] == pytest.approx(2 / 12)
