"""API tests: /api/crimes/summary (against the 3 seeded rows, hand-computed).

Fixture: API-01 (THEFT, arrest), API-02 (BATTERY), API-03 (ROBBERY, no
area) -> 3 crimes, 1 arrest (33.3%), 2026-09-15..2026-09-20, 3 types,
2 areas.
"""


def test_summary_counts(api_client):
    resp = api_client.get("/api/crimes/summary")
    assert resp.status_code == 200
    assert resp.json() == {
        "crime_count": 3,
        "arrest_count": 1,
        "arrest_rate_pct": 33.3,
        "first_crime_date": "2026-09-15",
        "last_crime_date": "2026-09-20",
        "distinct_crime_types": 3,
        "distinct_community_areas": 2,
    }


def test_summary_schema_fields(api_client):
    resp = api_client.get("/api/crimes/summary")
    assert set(resp.json().keys()) == {
        "crime_count", "arrest_count", "arrest_rate_pct",
        "first_crime_date", "last_crime_date",
        "distinct_crime_types", "distinct_community_areas",
    }
