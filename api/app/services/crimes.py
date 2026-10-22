"""SQL over the warehouse for the crimes endpoints.

Principle (AGENTS / plan §4): the API only READS the warehouse (facts,
dims and analytics views); all heavy aggregation lives in PostgreSQL.
"""

# (community_area_key, crime_type_key, date_key, arrest)

from datetime import timedelta


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


def hotspots(conn, run_key: int | None = None) -> dict | None:
    """Corrida DBSCAN guardada + sus clusters.

    Por defecto la última corrida (run_key DESC); con run_key, esa en
    concreto. None si no hay corridas guardadas (el router responde 404).
    Los clusters salen ordenados por volumen DESC (el hotspot más denso
    primero), mismo criterio que models.dbscan.cluster_summaries.
    """
    cur = conn.cursor()
    run_sql = """
        SELECT run_key, eps, min_samples, computed_at, n_clusters, n_noise
        FROM warehouse.hotspot_runs
    """
    if run_key is not None:
        run_sql += " WHERE run_key = %s"
    else:
        run_sql += " ORDER BY run_key DESC LIMIT 1"
    cur.execute(run_sql, (run_key,) if run_key is not None else None)
    run = cur.fetchone()
    if run is None:
        cur.close()
        return None
    cur.execute(
        """
        SELECT cluster_label, centroid_lat, centroid_lon, n_points,
               min_lat, max_lat, min_lon, max_lon
        FROM warehouse.hotspot_clusters
        WHERE run_key = %s
        ORDER BY n_points DESC
        """,
        (run[0],),
    )
    clusters = [
        dict(zip(
            ["cluster_label", "centroid_lat", "centroid_lon", "n_points",
             "min_lat", "max_lat", "min_lon", "max_lon"],
            row,
        ))
        for row in cur.fetchall()
    ]
    cur.close()
    return {
        "run": dict(zip(
            ["run_key", "eps", "min_samples", "computed_at",
             "n_clusters", "n_noise"],
            run,
        )),
        "clusters": clusters,
    }


def weekly_report(conn) -> dict | None:
    """Reporte semanal para Power Automate (GET /api/reports/weekly).

    Ventana data-driven: los últimos 7 días de datos REALES (end = max
    full_date del fact), no del reloj — funciona igual en dev con 1 mes y
    en backfill completo. Comparación vs los 7 días previos (change None
    si la base tiene 0 crímenes). Hotspots: top 3 de la última corrida
    (vacío si no hay corridas guardadas). None si el warehouse está vacío
    (el router responde 404).
    """
    cur = conn.cursor()

    cur.execute(
        """
        SELECT max(d.full_date)
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        """
    )
    (end,) = cur.fetchone()
    if end is None:
        cur.close()
        return None

    start = end - timedelta(days=6)
    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)

    cur.execute(
        """
        SELECT
            count(*)                                         AS crime_count,
            count(*) FILTER (WHERE f.arrest)                 AS arrest_count,
            CASE WHEN count(*) > 0 THEN
                round(100.0 * count(*) FILTER (WHERE f.arrest) / count(*), 1)
            END                                              AS arrest_rate_pct
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        WHERE d.full_date BETWEEN %s AND %s
        """,
        (start, end),
    )
    crime_count, arrest_count, arrest_rate_pct = cur.fetchone()

    cur.execute(
        """
        SELECT count(*)
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        WHERE d.full_date BETWEEN %s AND %s
        """,
        (prev_start, prev_end),
    )
    (prev_count,) = cur.fetchone()
    change_pct = (
        round(100.0 * (crime_count - prev_count) / prev_count, 1)
        if prev_count > 0 else None
    )

    cur.execute(
        """
        SELECT ct.primary_type,
               count(*)                                            AS crime_count,
               round(100.0 * count(*) / sum(count(*)) OVER (), 1)  AS share_pct
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        JOIN warehouse.dim_crime_type ct ON ct.crime_type_key = f.crime_type_key
        WHERE d.full_date BETWEEN %s AND %s
        GROUP BY ct.primary_type
        ORDER BY crime_count DESC, ct.primary_type
        LIMIT 5
        """,
        (start, end),
    )
    top_types = [
        dict(zip(["primary_type", "crime_count", "share_pct"], row))
        for row in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT ca.community_area, ca.community_area_name, count(*) AS crime_count
        FROM warehouse.fact_crime f
        JOIN warehouse.dim_date d ON d.date_key = f.date_key
        JOIN warehouse.dim_community_area ca
            ON ca.community_area_key = f.community_area_key
        WHERE d.full_date BETWEEN %s AND %s
        GROUP BY ca.community_area, ca.community_area_name
        ORDER BY crime_count DESC, ca.community_area
        LIMIT 5
        """,
        (start, end),
    )
    top_areas = [
        dict(zip(["community_area", "community_area_name", "crime_count"], row))
        for row in cur.fetchall()
    ]

    cur.close()
    latest = hotspots(conn)
    return {
        "period_start": start,
        "period_end": end,
        "crime_count": crime_count,
        "arrest_count": arrest_count,
        "arrest_rate_pct": arrest_rate_pct,
        "crime_change_pct": change_pct,
        "top_crime_types": top_types,
        "top_areas": top_areas,
        "hotspots": latest["clusters"][:3] if latest else [],
    }


def day_hour(conn) -> list[dict]:
    """Heatmap día×hora (vw_day_hour), orden ISO (lunes=1) y hora ascendente."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT day_of_week, day_name, hour, crime_count
        FROM warehouse.vw_day_hour
        ORDER BY day_of_week, hour
        """
    )
    rows = cur.fetchall()
    cur.close()
    keys = ["day_of_week", "day_name", "hour", "crime_count"]
    return [dict(zip(keys, row)) for row in rows]


def database_ok(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1")
    ok = cur.fetchone() is not None
    cur.close()
    return ok
