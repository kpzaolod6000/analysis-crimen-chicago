"""Integration tests for the warehouse load (database/functions/load_warehouse.sql).

Applies 003 + 004 + the community-areas seed, seeds 8 known raw rows, runs
warehouse.load_warehouse() and verifies the populated star against
hand-computed counts: dim_date generated, dims deduped from staging (with
the ''->NULL contract), fact excluding undated rows, key resolution through
the FK joins, and idempotent reload.
"""

import pytest
from conftest import REPO_ROOT, apply_migration

AREAS_SEED_SQL = (REPO_ROOT / "database" / "seeds" / "community_areas.sql").read_text(
    encoding="utf-8"
)
FUNCTIONS_SQL = (
    REPO_ROOT / "database" / "functions" / "load_warehouse.sql"
).read_text(encoding="utf-8")

INSERT_SQL = """
INSERT INTO raw.crimes
    (id, date, iucr, primary_type, description, block, location_description,
     community_area, district, latitude, longitude, arrest, domestic)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Hand-computed expectations for these 8 rows:
#   distinct crime types: 6 (LW-01/03 share one; LW-08 '' excluded by contract)
#   distinct locations:   7 (LW-07 contributes one, being undated)
#   distinct districts:   6   fact rows: 7 (LW-07 has NULL date -> excluded)
#   LW-06: community_area 0 -> staging NULL -> fact FK NULL
#   LW-08: primary_type '' -> staging NULL -> fact FK NULL
SEED_ROWS = [
    ("LW-01", "2026-09-15T10:30:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 1, 41.87, -87.62, True, False),
    ("LW-02", "2026-09-19T21:00:00", "0620", "BURGLARY", "FORCIBLE ENTRY",
     None, "RESIDENCE", 22, 14, 41.90, -87.70, False, True),
    ("LW-03", "2026-09-15T10:30:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 1, 41.87, -87.63, True, False),
    ("LW-04", "2026-09-20T02:15:00", "0110", "HOMICIDE", "FIRST DEGREE MURDER",
     "02XX W OAKDALE AVE", "APARTMENT", 1, 19, 41.94, -87.64, True, True),
    ("LW-05", "2026-09-15T08:00:00", "0450", "OFFENSE INVOLVING CHILDREN",
     "OTHER OFFENSES INVOLVING CHILDREN", "100XX S HALSTED ST", "ALLEY",
     58, 8, 41.81, -87.65, False, False),
    ("LW-06", "2026-09-15T23:59:59", "0810", "MOTOR VEHICLE THEFT", "AUTOMOBILE",
     None, "AUTO", 0, 11, 41.85, -87.66, False, False),
    ("LW-07", None, "0910", "ARSON", "AGGRAVATED",
     None, "SINGLE FAMILY DWELLING", 66, 8, None, None, True, False),
    ("LW-08", "2026-09-16T12:00:00", "1010", "", "SOME DESCRIPTION",
     "010XX S ABATE AVE", "GARAGE", 61, 6, 41.80, -87.60, False, True),
]


@pytest.fixture(scope="module")
def loaded_db(migrated_db):
    """Aplica 003+004+seed+funciones; siembra 8 filas; ejecuta la carga."""
    apply_migration(migrated_db, "003_staging.sql")
    apply_migration(migrated_db, "004_dims_fact.sql")
    with migrated_db.cursor() as cur:
        cur.execute(
            "TRUNCATE warehouse.fact_crime, warehouse.dim_date, "
            "warehouse.dim_crime_type, warehouse.dim_location, "
            "warehouse.dim_district, warehouse.dim_community_area "
            "RESTART IDENTITY CASCADE"
        )
        cur.execute("TRUNCATE raw.crimes")
        cur.execute(AREAS_SEED_SQL)
        cur.execute(FUNCTIONS_SQL)
        cur.executemany(INSERT_SQL, SEED_ROWS)
        cur.execute("SELECT warehouse.load_warehouse()")
    yield migrated_db
    with migrated_db.cursor() as cur:
        cur.execute(
            "TRUNCATE warehouse.fact_crime, warehouse.dim_date, "
            "warehouse.dim_crime_type, warehouse.dim_location, "
            "warehouse.dim_district, warehouse.dim_community_area "
            "RESTART IDENTITY CASCADE"
        )
        cur.execute("TRUNCATE raw.crimes")


def test_dim_date_matches_range(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute(
            """
            SELECT
              (SELECT count(*) FROM warehouse.dim_date),
              (SELECT count(*) FROM generate_series(
                   '2001-01-01'::date, '2030-12-31'::date, INTERVAL '1 day'))
            """
        )
        (dim_total, expected) = cur.fetchone()
    assert dim_total == expected


def test_dim_date_row_attributes(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute(
            """
            SELECT date_key, year, month, month_name, week, day_of_week,
                   day_name, is_weekend
            FROM warehouse.dim_date WHERE full_date = '2026-09-15'
            """
        )
        row = cur.fetchone()
    assert row == (20260915, 2026, 9, "September", 38, 2, "Tuesday", False)


def test_dim_date_weekend(loaded_db):
    # 2026-09-19 is a Saturday (isodow 6)
    with loaded_db.cursor() as cur:
        cur.execute(
            """
            SELECT day_of_week, day_name, is_weekend
            FROM warehouse.dim_date WHERE full_date = '2026-09-19'
            """
        )
        row = cur.fetchone()
    assert row == (6, "Saturday", True)


def test_dim_crime_type_from_staging(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.dim_crime_type")
        (total,) = cur.fetchone()
        cur.execute(
            "SELECT count(*) FROM warehouse.dim_crime_type "
            "WHERE primary_type = '' OR primary_type IS NULL"
        )
        (empties,) = cur.fetchone()
    assert total == 6
    assert empties == 0


def test_dim_location_from_staging(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.dim_location")
        (total,) = cur.fetchone()
    assert total == 7


def test_dim_district_from_staging(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.dim_district")
        (total,) = cur.fetchone()
    assert total == 6


def test_fact_excludes_undated_rows(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.fact_crime")
        (total,) = cur.fetchone()
    assert total == 7  # 8 seeded, LW-07 (NULL date) excluded


def test_fact_full_mapping_resolves_keys(loaded_db):
    with loaded_db.cursor() as cur:
        cur.execute(
            """
            SELECT f.date_key, d.day_name, ct.primary_type, ca.community_area_name,
                   dist.district, f.hour, f.arrest
            FROM warehouse.fact_crime f
            JOIN warehouse.dim_date d ON d.date_key = f.date_key
            JOIN warehouse.dim_crime_type ct ON ct.crime_type_key = f.crime_type_key
            JOIN warehouse.dim_community_area ca
              ON ca.community_area_key = f.community_area_key
            JOIN warehouse.dim_district dist ON dist.district_key = f.district_key
            WHERE f.crime_id = 'LW-01'
            """
        )
        row = cur.fetchone()
    assert row == (20260915, "Tuesday", "THEFT", "Austin", 1, 10, True)


def test_fact_null_fks_for_unknown_values(loaded_db):
    # LW-06 (community_area 0 -> NULL en staging) y LW-08 (primary_type ''
    # -> NULL) entran a fact con sus FKs correspondientes en NULL.
    with loaded_db.cursor() as cur:
        cur.execute(
            """
            SELECT f.crime_id,
                   (f.community_area_key IS NULL) AS unk_area,
                   (f.crime_type_key IS NULL) AS unk_type
            FROM warehouse.fact_crime f
            WHERE f.crime_id IN ('LW-06', 'LW-08')
            """
        )
        rows = cur.fetchall()
    # dict() revienta con filas de 3 columnas: se arma por comprensión
    unk_flags = {crime_id: (unk_area, unk_type) for crime_id, unk_area, unk_type in rows}
    assert unk_flags == {"LW-06": (True, False), "LW-08": (False, True)}


def test_reload_is_idempotent(loaded_db):
    # Re-cargar la estrella no duplica ni cambia conteos (UPSERT idempotente).
    with loaded_db.cursor() as cur:
        cur.execute("SELECT warehouse.load_warehouse()")
        cur.execute(
            """
            SELECT
              (SELECT count(*) FROM warehouse.fact_crime),
              (SELECT count(*) FROM warehouse.dim_crime_type),
              (SELECT count(*) FROM warehouse.dim_location),
              (SELECT count(*) FROM warehouse.dim_district)
            """
        )
        counts = cur.fetchone()
    assert counts == (7, 6, 7, 6)
