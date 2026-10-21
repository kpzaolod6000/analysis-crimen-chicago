"""API tests: /api/crimes/trends, /by-type, /by-community-area.

Hand-computed against the 3 seeded rows (API-01..03): single month
2026-09 (3 crimes / 1 arrest / 33.3%), three tied types (share 33.3 each),
two tied areas (22/41, share 50.0 of the 2 RANKED areas — API-03 has no
area and stays out of the ranking view).
"""

from fastapi.testclient import TestClient  # noqa: F401 — sólo para tipos


def test_trends_single_month(api_client):
    resp = api_client.get("/api/crimes/trends")
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "month_date": "2026-09-01",
            "year": 2026,
            "month": 9,
            "month_name": "September",
            "crime_count": 3,
            "arrest_count": 1,
            "arrest_rate_pct": 33.3,
        }
    ]


def test_by_type_counts_and_share(api_client):
    resp = api_client.get("/api/crimes/by-type")
    assert resp.status_code == 200
    # empate 1-1-1: orden alfabético determinista
    assert resp.json() == [
        {"primary_type": "BATTERY", "crime_count": 1, "share_pct": 33.3},
        {"primary_type": "ROBBERY", "crime_count": 1, "share_pct": 33.3},
        {"primary_type": "THEFT", "crime_count": 1, "share_pct": 33.3},
    ]


def test_by_type_limit(api_client):
    resp = api_client.get("/api/crimes/by-type", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1 and body[0]["primary_type"] == "BATTERY"


def test_by_community_area_full(api_client):
    resp = api_client.get("/api/crimes/by-community-area")
    assert resp.status_code == 200
    # share sobre las 2 areas RANKEADAS (API-03, sin área, queda fuera)
    assert resp.json() == [
        {"community_area": 22, "community_area_name": "Logan Square",
         "crime_count": 1, "share_pct": 50.0, "crime_rank": 1},
        {"community_area": 41, "community_area_name": "Hyde Park",
         "crime_count": 1, "share_pct": 50.0, "crime_rank": 1},
    ]


def test_by_community_area_limit(api_client):
    resp = api_client.get("/api/crimes/by-community-area", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1 and body[0]["community_area"] == 22


def test_limit_out_of_range_rejected(api_client):
    resp = api_client.get("/api/crimes/by-type", params={"limit": 500})
    assert resp.status_code == 422
