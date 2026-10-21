"""SQL over the warehouse for the crimes endpoints.

Principle (AGENTS / plan §4): the API only READS the warehouse (facts,
dims and analytics views); all heavy aggregation lives in PostgreSQL.
"""

# (community_area_key, crime_type_key, date_key, arrest)


def crimes_summary(conn) -> dict:
    """Volumen global de la estrella: totales, tasa de arresto y rango."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            count(*)                                                    AS crime_count,
            count(*) FILTER (WHERE f.arrest)                            AS arrest_count,
            CASE WHEN count(*) > 0 THEN
                round(100.0 * count(*) FILTER (WHERE f.arrest) / count(*), 1)
            END                                                         AS arrest_rate_pct,
            min(d.full_date)                                            AS first_crime_date,
            max(d.full_date)                                            AS last_crime_date,
            count(DISTINCT f.crime_type_key)                            AS distinct_crime_types,
            count(DISTINCT f.community_area_key)                        AS distinct_community_areas
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        """
    )
    row = cur.fetchone()
    cur.close()
    keys = [
        "crime_count", "arrest_count", "arrest_rate_pct",
        "first_crime_date", "last_crime_date",
        "distinct_crime_types", "distinct_community_areas",
    ]
    return dict(zip(keys, row))


def database_ok(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1")
    ok = cur.fetchone() is not None
    cur.close()
    return ok
