"""API tests: /api/reports/weekly.

Fixture rows (API-01..03) are all inside the last-7-days window
(2026-09-14..2026-09-20, end = max data date): 3 crimes / 1 arrest /
33.3%, previous week (09-07..09-13) empty -> change None, three tied
types (33.3 each), two tied areas (share of window), hotspots [] (the
api_db fixture leaves them empty). The 404 test truncates fact_crime and
re-loads afterwards (loader is idempotent).
"""

from fastapi.testclient import TestClient  # noqa: F401 — sólo para tipos


def test_weekly_report_body(api_client):
    resp = api_client.get("/api/reports/weekly")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] == "2026-09-14"
    assert body["period_end"] == "2026-09-20"
    assert body["crime_count"] == 3
    assert body["arrest_count"] == 1
    assert body["arrest_rate_pct"] == 33.3
    assert body["crime_change_pct"] is None  # semana previa vacía
    assert body["top_crime_types"] == [
        {"primary_type": "BATTERY", "crime_count": 1, "share_pct": 33.3},
        {"primary_type": "ROBBERY", "crime_count": 1, "share_pct": 33.3},
        {"primary_type": "THEFT", "crime_count": 1, "share_pct": 33.3},
    ]
    assert body["top_areas"] == [
        {"community_area": 22, "community_area_name": "Logan Square",
         "crime_count": 1},
        {"community_area": 41, "community_area_name": "Hyde Park",
         "crime_count": 1},
    ]
    assert body["hotspots"] == []


def test_weekly_report_empty_warehouse(api_client):
    from api.app.db import connect_db

    conn = connect_db()  # misma DB de pruebas (env ya seteado por conftest)
    try:
        with conn.cursor() as cur:
            # solo fact: si truncaramos raw.crimes el reload no tendría
            # nada que recargar (raw es la fuente)
            cur.execute("TRUNCATE warehouse.fact_crime CASCADE")
        resp = api_client.get("/api/reports/weekly")
        assert resp.status_code == 404
    finally:
        with conn.cursor() as cur:
            cur.execute("SELECT warehouse.load_warehouse()")
        conn.close()


def test_weekly_report_recoverable_after_empty(api_client):
    # después del truncate+reload del test anterior, el endpoint vuelve a 200
    resp = api_client.get("/api/reports/weekly")
    assert resp.status_code == 200
    assert resp.json()["crime_count"] == 3
