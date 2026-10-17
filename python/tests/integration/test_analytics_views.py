"""Integration tests for the Sprint 4 analytical views (database/views/analytics.sql).

Seeds 10 known raw rows (V-01..V-10, spanning Aug/Sep 2026 and areas
25/41/77 plus one row without area), runs warehouse.load_warehouse(),
applies the analytics views and asserts every aggregate against counts
computed by hand:

    months:        2026-08 -> 4 crimes / 2 arrests (50.0%)
                   2026-09 -> 6 crimes / 2 arrests (33.3%), prev 4
    ranking:       25 -> 4 (rank 1, 44.4%), 41 -> 4 (rank 1, 44.4%),
                   77 -> 1 (rank 3, 11.1%); V-10 (NULL area) excluded
    day x hour:    (Sat,10,1) (Sat,11,2) (Sat,12,1) (Sat,22,1)
                   (Tue,10,3) (Thu,8,1) (Thu,23,1)
    area summary:  25 {4,2,0,1}, 41 {4,1,1,3}, 77 {1,1,0,1}; sum 9
"""

import pytest
from conftest import REPO_ROOT, apply_migration

AREAS_SEED_SQL = (REPO_ROOT / "database" / "seeds" / "community_areas.sql").read_text(
    encoding="utf-8"
)
FUNCTIONS_SQL = (
    REPO_ROOT / "database" / "functions" / "load_warehouse.sql"
).read_text(encoding="utf-8")
VIEWS_SQL = (REPO_ROOT / "database" / "views" / "analytics.sql").read_text(
    encoding="utf-8"
)

INSERT_SQL = """
INSERT INTO raw.crimes
    (id, date, iucr, primary_type, description, block, location_description,
     community_area, district, latitude, longitude, arrest, domestic)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

SEED_ROWS = [
    ("V-01", "2026-08-01T10:00:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 4, None, None, True, False),
    ("V-02", "2026-08-01T11:00:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 4, None, None, False, False),
    ("V-03", "2026-08-01T11:00:00", "0310", "BATTERY", "SIMPLE",
     "02XX W MADISON ST", "APARTMENT", 41, 8, None, None, False, False),
    ("V-04", "2026-08-15T22:00:00", "0312", "ROBBERY", "ARMED: HANDGUN",
     "030XX W OHIO ST", "STREET", 77, 2, None, None, True, False),
    ("V-05", "2026-09-01T10:00:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 4, None, None, True, False),
    ("V-06", "2026-09-01T10:00:00", "0820", "THEFT", "$500 AND UNDER",
     "001XX N STATE ST", "STREET", 25, 4, None, None, False, False),
    ("V-07", "2026-09-01T10:00:00", "0820", "THEFT", "$500 AND UNDER",
     "035XX W NORTH AVE", "SIDEWALK", 41, 8, None, None, True, False),
    ("V-08", "2026-09-10T23:00:00", "0310", "BATTERY", "SIMPLE",
     "060XX S MARTIN L KING DR", "RESIDENCE", 41, 8, None, None, False, True),
    ("V-09", "2026-09-10T08:00:00", "0312", "ROBBERY", "ARMED: HANDGUN",
     "07XX N CLARK ST", "SIDEWALK", 41, 8, None, None, False, False),
    # Sin area: entra a fact (fecha completa) pero NO a ranking/summary
    ("V-10", "2026-09-12T12:00:00", "0310", "BATTERY", "SIMPLE",
     "330XX W CERMAK RD", "STREET", None, 9, None, None, False, False),
]

TRUNCATE_WAREHOUSE = (
    "TRUNCATE warehouse.fact_crime, warehouse.dim_date, "
    "warehouse.dim_crime_type, warehouse.dim_location, "
    "warehouse.dim_district, warehouse.dim_community_area "
    "RESTART IDENTITY CASCADE"
)
TRUNCATE_BOTH = (
    "TRUNCATE raw.crimes, warehouse.fact_crime, warehouse.dim_date, "
    "warehouse.dim_crime_type, warehouse.dim_location, "
    "warehouse.dim_district, warehouse.dim_community_area "
    "RESTART IDENTITY CASCADE"
)


@pytest.fixture(scope="module")
def views_db(migrated_db):
    """003+004+seed+funciones aplicados, 10 filas fixture cargadas y
    views creadas. Deja limpio al terminar el módulo."""
    apply_migration(migrated_db, "003_staging.sql")
    apply_migration(migrated_db, "004_dims_fact.sql")
    with migrated_db.cursor() as cur:
        cur.execute(TRUNCATE_BOTH)
        cur.execute(AREAS_SEED_SQL)
        cur.execute(FUNCTIONS_SQL)
        cur.execute(VIEWS_SQL)
        cur.executemany(INSERT_SQL, SEED_ROWS)
        cur.execute("SELECT warehouse.load_warehouse()")
    yield migrated_db
    with migrated_db.cursor() as cur:
        cur.execute("TRUNCATE raw.crimes")
        cur.execute(TRUNCATE_WAREHOUSE)


def query_rows(views_db, sql: str):
    with views_db.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


# ── estructura ───────────────────────────────────────────────────────────

def test_views_file_is_idempotent(views_db):
    with views_db.cursor() as cur:
        cur.execute(VIEWS_SQL)


def test_five_views_exist(views_db):
    rows = query_rows(
        views_db,
        """
        SELECT view_name FROM information_schema.views
        WHERE table_schema = 'warehouse'
        ORDER BY view_name
        """,
    )
    assert [r[0] for r in rows] == [
        "vw_area_crime_ranking",
        "vw_area_summary",
        "vw_day_hour",
        "vw_month_over_month",
        "vw_monthly_crimes",
    ]


# ── vw_monthly_crimes ────────────────────────────────────────────────────

def test_vw_monthly_crimes_full_rows(views_db):
    import datetime as dt

    rows = query_rows(
        views_db,
        "SELECT month_date, year, month, month_name, crime_count, "
        "arrest_count, arrest_rate_pct FROM warehouse.vw_monthly_crimes "
        "ORDER BY month_date",
    )
    assert rows == [
        (dt.date(2026, 8, 1), 2026, 8, "August", 4, 2, 50.0),
        (dt.date(2026, 9, 1), 2026, 9, "September", 6, 2, 33.3),
    ]


def test_vw_monthly_crimes_sums_to_fact_total(views_db):
    (month_sums, fact_total) = query_rows(
        views_db,
        "SELECT (SELECT sum(crime_count) FROM warehouse.vw_monthly_crimes), "
        "(SELECT count(*) FROM warehouse.fact_crime)",
    )[0]
    assert fact_total == 10
    assert month_sums == fact_total


# ── vw_area_crime_ranking ────────────────────────────────────────────────

def test_vw_area_crime_ranking_full(views_db):
    rows = query_rows(
        views_db,
        "SELECT community_area, community_area_name, crime_count, "
        "share_pct, crime_rank FROM warehouse.vw_area_crime_ranking "
        "ORDER BY crime_rank, community_area",
    )
    assert [(r[0], r[1], r[2], r[3], r[4]) for r in rows] == [
        (25, "Logan Square", 4, 44.4, 1),
        (41, "Hyde Park", 4, 44.4, 1),
        (77, "O'Hare", 1, 11.1, 3),
    ]


def test_vw_area_crime_ranking_excludes_unknown_area(views_db):
    rows = query_rows(
        views_db,
        "SELECT community_area FROM warehouse.vw_area_crime_ranking",
    )
    assert all(r[0] is not None for r in rows)
    assert len(rows) == 3


# ── vw_month_over_month ──────────────────────────────────────────────────

def test_vw_month_over_month_first_month_has_null_change(views_db):
    import datetime as dt

    rows = query_rows(
        views_db,
        "SELECT month_date, crime_count, prev_crime_count, change_abs, "
        "change_pct FROM warehouse.vw_month_over_month ORDER BY month_date",
    )
    assert rows == [
        (dt.date(2026, 8, 1), 4, None, None, None),
        (dt.date(2026, 9, 1), 6, 4, 2, 50.0),
    ]


# ── vw_day_hour ──────────────────────────────────────────────────────────

def test_vw_day_hour_full_heatmap(views_db):
    rows = query_rows(
        views_db,
        "SELECT day_of_week, day_name, hour, crime_count "
        "FROM warehouse.vw_day_hour ORDER BY day_of_week, hour",
    )
    assert rows == [
        (2, "Tuesday", 10, 3),
        (4, "Thursday", 8, 1),
        (4, "Thursday", 23, 1),
        (6, "Saturday", 10, 1),
        (6, "Saturday", 11, 2),
        (6, "Saturday", 12, 1),
        (6, "Saturday", 22, 1),
    ]


def test_vw_day_hour_sums_to_fact_total(views_db):
    (heatmap_total, fact_total) = query_rows(
        views_db,
        "SELECT (SELECT sum(crime_count) FROM warehouse.vw_day_hour), "
        "(SELECT count(*) FROM warehouse.fact_crime)",
    )[0]
    assert heatmap_total == fact_total == 10


# ── vw_area_summary ──────────────────────────────────────────────────────

def test_vw_area_summary_full(views_db):
    import datetime as dt

    rows = query_rows(
        views_db,
        "SELECT community_area, community_area_name, crime_count, "
        "arrest_count, domestic_count, crime_type_count, "
        "first_crime_date, last_crime_date FROM warehouse.vw_area_summary "
        "ORDER BY community_area",
    )
    assert rows == [
        (
            25,
            "Logan Square",
            4,
            2,          # V-01, V-05
            0,
            1,          # única combinación THEFT/$500 AND UNDER
            dt.date(2026, 8, 1),
            dt.date(2026, 9, 1),
        ),
        (
            41,
            "Hyde Park",
            4,
            1,          # V-07
            1,          # V-08
            3,          # THEFT + BATTERY + ROBBERY
            dt.date(2026, 8, 1),
            dt.date(2026, 9, 10),
        ),
        (
            77,
            "O'Hare",
            1,          # V-04
            1,
            0,
            1,
            dt.date(2026, 8, 15),
            dt.date(2026, 8, 15),
        ),
    ]


def test_vw_area_summary_total_excludes_null_area_row(views_db):
    (summary_total,) = query_rows(
        views_db, "SELECT sum(crime_count) FROM warehouse.vw_area_summary"
    )[0]
    # fact total 10: V-10 (sin area) queda fuera del resumen por área
    assert summary_total == 9
