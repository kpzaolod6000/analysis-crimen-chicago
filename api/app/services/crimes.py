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


def monthly_trends(conn) -> list[dict]:
    """Tendencia mensual (vw_monthly_crimes), del mes más viejo al más nuevo."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT month_date, year, month, month_name,
               crime_count, arrest_count, arrest_rate_pct
        FROM warehouse.vw_monthly_crimes
        ORDER BY month_date
        """
    )
    rows = cur.fetchall()
    cur.close()
    keys = [
        "month_date", "year", "month", "month_name",
        "crime_count", "arrest_count", "arrest_rate_pct",
    ]
    return [dict(zip(keys, row)) for row in rows]


def crime_types(conn, limit: int | None = None) -> list[dict]:
    """Crímenes por primary_type (fact + dim_crime_type), más share.

    Empates resueltos por orden alfabético del tipo (determinista).
    """
    sql = """
        SELECT ct.primary_type,
               count(*)                                            AS crime_count,
               round(100.0 * count(*) / sum(count(*)) OVER (), 1)  AS share_pct
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_crime_type ct ON ct.crime_type_key = f.crime_type_key
        GROUP BY ct.primary_type
        ORDER BY crime_count DESC, ct.primary_type
    """
    if limit is not None:
        sql += " LIMIT %s"
    cur = conn.cursor()
    cur.execute(sql, (limit,) if limit is not None else None)
    rows = cur.fetchall()
    cur.close()
    keys = ["primary_type", "crime_count", "share_pct"]
    return [dict(zip(keys, row)) for row in rows]


def area_ranking(conn, limit: int | None = None) -> list[dict]:
    """Ranking de community areas (vw_area_crime_ranking), rank ascendente.

    Con empates, se ordena además por número de área (determinista).
    """
    sql = """
        SELECT community_area, community_area_name,
               crime_count, share_pct, crime_rank
        FROM warehouse.vw_area_crime_ranking
        ORDER BY crime_rank, community_area
    """
    if limit is not None:
        sql += " LIMIT %s"
    cur = conn.cursor()
    cur.execute(sql, (limit,) if limit is not None else None)
    rows = cur.fetchall()
    cur.close()
    keys = ["community_area", "community_area_name", "crime_count",
            "share_pct", "crime_rank"]
    return [dict(zip(keys, row)) for row in rows]


def database_ok(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1")
    ok = cur.fetchone() is not None
    cur.close()
    return ok
