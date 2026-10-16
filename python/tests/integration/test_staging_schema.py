"""Integration tests for the staging layer (003_staging.sql).

staging.crimes is a VIEW over raw.crimes applying the cleaning rules of
skill chicago-data-quality (trim/empty->NULL text, (0,0) coords -> NULL,
out-of-range coords -> NULL, community_area outside 1-77 -> NULL). Tests
seed known raw rows and assert each cleaning rule against the view.
"""

import pytest
from conftest import apply_migration

STAGING_COLUMNS = {
    "id",
    "case_number",
    "date",
    "block",
    "iucr",
    "primary_type",
    "description",
    "location_description",
    "arrest",
    "domestic",
    "beat",
    "district",
    "ward",
    "community_area",
    "fbi_code",
    "x_coordinate",
    "y_coordinate",
    "year",
    "updated_on",
    "latitude",
    "longitude",
    "location",
    "loaded_at",
}

INSERT_SQL = """
INSERT INTO raw.crimes (id, date, primary_type, community_area, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s)
"""

# (id, date, primary_type, community_area, latitude, longitude)
SEED_ROWS = [
    ("STG-01", "2026-09-01T10:00:00", "THEFT", 25, 41.87, -87.62),  # fully valid
    ("STG-02", "2026-09-02T10:00:00", "  BATTERY  ", 3, 41.9, -87.7),  # padded
    ("STG-03", "2026-09-03T10:00:00", "", 8, 41.8, -87.6),  # empty string
    ("STG-04", "2026-09-04T10:00:00", "NARCOTICS", 10, 0.0, 0.0),  # (0,0)
    ("STG-05", "2026-09-05T10:00:00", "ASSAULT", 3, 91.0, -87.7),  # out of range
    ("STG-06", "2026-09-06T10:00:00", "ROBBERY", 0, 41.85, -87.65),  # ca 0
    ("STG-07", "2026-09-07T10:00:00", "BURGLARY", 99, 41.84, -87.66),  # ca 99
    ("STG-08", "2026-09-08T10:00:00", "MOTOR VEHICLE THEFT", 1, None, -87.67),
    ("STG-09", None, "THEFT", 25, 41.86, -87.68),  # NULL date stays (row kept)
]


@pytest.fixture(scope="module")
def staging_db(migrated_db):
    """Migración 003 aplicada + raw.crimes con filas fixture conocidas."""
    apply_migration(migrated_db, "003_staging.sql")
    with migrated_db.cursor() as cur:
        cur.execute("TRUNCATE raw.crimes")
        cur.executemany(INSERT_SQL, SEED_ROWS)
    return migrated_db


def test_migration_is_idempotent(staging_db):
    apply_migration(staging_db, "003_staging.sql")


def test_view_columns_match_raw(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'staging' AND table_name = 'crimes'
            """
        )
        actual = {row[0] for row in cur.fetchall()}
    assert actual == STAGING_COLUMNS


def test_row_count_matches_raw(staging_db):
    with staging_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM staging.crimes")
        (staging_count,) = cur.fetchone()
        cur.execute("SELECT count(*) FROM raw.crimes")
        (raw_count,) = cur.fetchone()
    assert staging_count == raw_count == 9


def test_trims_padded_text(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT primary_type FROM staging.crimes WHERE id = 'STG-02'"
        )
        (primary_type,) = cur.fetchone()
    assert primary_type == "BATTERY"


def test_empty_string_becomes_null(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT primary_type FROM staging.crimes WHERE id = 'STG-03'"
        )
        (primary_type,) = cur.fetchone()
    assert primary_type is None  # contrato: '' (o solo espacios) -> NULL


def test_zero_zero_coordinates_become_null(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT latitude, longitude FROM staging.crimes WHERE id = 'STG-04'"
        )
        latitude, longitude = cur.fetchone()
    assert latitude is None
    assert longitude is None


def test_out_of_range_coordinates_become_null(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT latitude, longitude FROM staging.crimes WHERE id = 'STG-05'"
        )
        latitude, longitude = cur.fetchone()
    assert latitude is None
    assert longitude is None


def test_valid_coordinates_kept(staging_db):
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT latitude, longitude FROM staging.crimes WHERE id = 'STG-01'"
        )
        latitude, longitude = cur.fetchone()
    assert latitude == 41.87
    assert longitude == -87.62


def test_partial_coordinates_kept_as_is(staging_db):
    # lat NULL + lon present: staging keeps the partial pair untouched
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT latitude, longitude FROM staging.crimes WHERE id = 'STG-08'"
        )
        latitude, longitude = cur.fetchone()
    assert latitude is None
    assert longitude == -87.67


def test_community_area_outside_catalog_becomes_null(staging_db):
    # 0 (unknown in old records) and 99 (invalid) both map to NULL
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT community_area FROM staging.crimes WHERE id = 'STG-06'"
        )
        (zero_area,) = cur.fetchone()
        cur.execute(
            "SELECT community_area FROM staging.crimes WHERE id = 'STG-07'"
        )
        (invalid_area,) = cur.fetchone()
        cur.execute(
            "SELECT community_area FROM staging.crimes WHERE id = 'STG-01'"
        )
        (valid_area,) = cur.fetchone()
    assert zero_area is None
    assert invalid_area is None
    assert valid_area == 25


def test_null_date_row_still_present(staging_db):
    # staging cleans VALUES, not rows; warehouse decides filters on load
    with staging_db.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM staging.crimes WHERE id = 'STG-09' AND date IS NULL"
        )
        (rows,) = cur.fetchone()
    assert rows == 1
