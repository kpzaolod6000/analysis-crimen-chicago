"""Data-quality metrics over raw.crimes (skill chicago-data-quality).

Each function takes a psycopg2 cursor and returns a scalar metric, so the
data tests (python/tests/integration/test_data_quality.py) and the smoke
script (python/scripts/check_raw_load.py) share one source of truth.

Skill thresholds (alert examples): duplicate_rate > 0 after UPSERT,
null_rate(date) > 0. Domain notes: (0,0) coordinates are invalid (Socrata
sometimes emits them); old records (2001-2006) legitimately have more NULLs
in lat/lon and community_area.
"""

from psycopg2 import sql

# Columns where null_rate is a defined metric (whitelist: the column name is
# interpolated as a SQL identifier, so it must never come from user input).
NULLABLE_METRIC_COLUMNS = frozenset(
    {
        "date",
        "latitude",
        "longitude",
        "community_area",
        "primary_type",
        "description",
        "location_description",
        "iucr",
        "district",
        "ward",
    }
)

# Columns reported in quality_report["null_rate"] (skill: key columns).
NULL_RATE_COLUMNS = ("date", "latitude", "longitude", "community_area", "primary_type")


def total_rows(cur) -> int:
    """Total rows in raw.crimes."""
    cur.execute("SELECT count(*) FROM raw.crimes")
    return cur.fetchone()[0]


def duplicate_ids(cur) -> int:
    """Ids appearing more than once (must be 0 after UPSERT; PK enforces it)."""
    cur.execute(
        "SELECT count(*) FROM ("
        "SELECT id FROM raw.crimes GROUP BY id HAVING count(*) > 1"
        ") d"
    )
    return cur.fetchone()[0]


def null_ids(cur) -> int:
    """Rows with NULL id (must be 0; PK enforces it)."""
    cur.execute("SELECT count(*) FROM raw.crimes WHERE id IS NULL")
    return cur.fetchone()[0]


def out_of_range_coordinates(cur) -> int:
    """Rows with lat/lon outside [-90,90]/[-180,180] (NULLs are valid)."""
    cur.execute(
        "SELECT count(*) FROM raw.crimes WHERE latitude IS NOT NULL "
        "AND (latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180)"
    )
    return cur.fetchone()[0]


def zero_coordinates(cur) -> int:
    """Rows at exactly (0, 0): Socrata sometimes emits a null origin point."""
    cur.execute(
        "SELECT count(*) FROM raw.crimes WHERE latitude = 0 AND longitude = 0"
    )
    return cur.fetchone()[0]


def invalid_community_area(cur) -> int:
    """Rows with community_area outside the 0-77 catalog (NULLs are valid)."""
    cur.execute(
        "SELECT count(*) FROM raw.crimes "
        "WHERE community_area IS NOT NULL AND community_area NOT BETWEEN 0 AND 77"
    )
    return cur.fetchone()[0]


def empty_primary_type(cur) -> int:
    """Rows with NULL or blank primary_type (unknown crime type)."""
    cur.execute(
        "SELECT count(*) FROM raw.crimes "
        "WHERE primary_type IS NULL OR btrim(primary_type) = ''"
    )
    return cur.fetchone()[0]


def null_counts(cur, column: str) -> tuple[int, int]:
    """(nulls, total) for a whitelisted column, in a single query."""
    if column not in NULLABLE_METRIC_COLUMNS:
        raise ValueError(f"column not measurable: {column!r}")
    query = sql.SQL(
        "SELECT count(*) FILTER (WHERE {} IS NULL), count(*) FROM raw.crimes"
    ).format(sql.Identifier(column))
    cur.execute(query)
    nulls, total = cur.fetchone()
    return nulls, total


def null_rate(cur, column: str) -> float:
    """Fraction of NULLs in a whitelisted column (0.0 when the table is empty)."""
    nulls, total = null_counts(cur, column)
    return nulls / total if total else 0.0


def quality_report(cur) -> dict:
    """All skill metrics in one dict (for logs and the smoke script)."""
    return {
        "total": total_rows(cur),
        "duplicate_ids": duplicate_ids(cur),
        "null_ids": null_ids(cur),
        "out_of_range_coordinates": out_of_range_coordinates(cur),
        "zero_coordinates": zero_coordinates(cur),
        "invalid_community_area": invalid_community_area(cur),
        "empty_primary_type": empty_primary_type(cur),
        "null_rate": {col: null_rate(cur, col) for col in NULL_RATE_COLUMNS},
    }
