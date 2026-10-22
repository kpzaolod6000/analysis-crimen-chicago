"""API tests: filter params (primary_type / year / month / community_area).

Hand-computed against the 3 seeded rows:
    API-01 THEFT     2026-09-15 area 22 (arrest)
    API-02 BATTERY   2026-09-15 area 41
    API-03 ROBBERY   2026-09-20 area NULL
Filter combos: THEFT -> 1 crime/1 arrest (100%); year 2025 -> all zero;
BATTERY -> only area 41 in the ranking; area 22 -> heatmap has only the
Tue 10h cell; month 9 -> everything (window is Sept).
"""


def test_summary_filter_by_type(api_client):
    body = api_client.get("/api/crimes/summary", params={"primary_type": "THEFT"}).json()
    assert body["crime_count"] == 1
    assert body["arrest_count"] == 1
    assert body["arrest_rate_pct"] == 100.0
    assert body["distinct_community_areas"] == 1


def test_summary_filter_year_empty_coalesced(api_client):
    body = api_client.get("/api/crimes/summary", params={"year": 2025}).json()
    assert body == {
        "crime_count": 0,
        "arrest_count": 0,
        "arrest_rate_pct": 0.0,          # COALESCE: 0 y no null
        "first_crime_date": None,
        "last_crime_date": None,
        "distinct_crime_types": 0,
        "distinct_community_areas": 0,
    }


def test_summary_filter_area(api_client):
    body = api_client.get("/api/crimes/summary", params={"community_area": 41}).json()
    assert body["crime_count"] == 1 and body["distinct_crime_types"] == 1


def test_trends_filter_by_type(api_client):
    body = api_client.get("/api/crimes/trends", params={"primary_type": "THEFT"}).json()
    assert len(body) == 1
    assert body[0]["crime_count"] == 1 and body[0]["arrest_count"] == 1


def test_trends_filter_month_no_data(api_client):
    body = api_client.get("/api/crimes/trends", params={"month": 8}).json()
    assert body == []


def test_area_ranking_filter_by_type(api_client):
    body = api_client.get(
        "/api/crimes/by-community-area", params={"primary_type": "BATTERY"}
    ).json()
    assert len(body) == 1
    assert body[0]["community_area"] == 41
    assert body[0]["crime_count"] == 1
    assert body[0]["share_pct"] == 100.0   # share sobre el conjunto filtrado
    assert body[0]["crime_rank"] == 1


def test_by_hour_filter_by_area(api_client):
    body = api_client.get("/api/crimes/by-hour", params={"community_area": 22}).json()
    assert body == [
        {"day_of_week": 2, "day_name": "Tuesday", "hour": 10, "crime_count": 1}
    ]


def test_month_out_of_range_rejected(api_client):
    resp = api_client.get("/api/crimes/summary", params={"month": 13})
    assert resp.status_code == 422
