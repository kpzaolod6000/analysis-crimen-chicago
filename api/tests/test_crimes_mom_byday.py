"""API tests: /api/crimes/mom + /api/crimes/by-day (Sprint 7 · Paso 8a).

Fixture (API-01..03): all September 2026 — Tue 10h/11h (arrest on THEFT),
Sun 22h ROBBERY, one row without area. Hand-computed:
    mom:    single row 2026-09: 3 crimes, prev/change NULL (first month)
    by-day: Tue (weekday, 2 crimes) + Sun (weekend, 1), ISO order
"""


def test_mom_first_month_nulls(api_client):
    body = api_client.get("/api/crimes/mom").json()
    assert body == [
        {
            "month_date": "2026-09-01",
            "crime_count": 3,
            "prev_crime_count": None,
            "change_abs": None,
            "change_pct": None,
        }
    ]


def test_mom_empty_filter_month(api_client):
    body = api_client.get("/api/crimes/mom", params={"month": 8}).json()
    assert body == []


def test_mom_filter_by_type(api_client):
    body = api_client.get("/api/crimes/mom", params={"primary_type": "THEFT"}).json()
    assert body[0]["crime_count"] == 1


def test_by_day_iso_order_and_weekend(api_client):
    body = api_client.get("/api/crimes/by-day").json()
    assert body == [
        {"day_of_week": 2, "day_name": "Tuesday", "is_weekend": False,
         "crime_count": 2},
        {"day_of_week": 7, "day_name": "Sunday", "is_weekend": True,
         "crime_count": 1},
    ]


def test_by_day_filter_by_area(api_client):
    body = api_client.get("/api/crimes/by-day", params={"community_area": 22}).json()
    assert body == [
        {"day_of_week": 2, "day_name": "Tuesday", "is_weekend": False,
         "crime_count": 1},
    ]
