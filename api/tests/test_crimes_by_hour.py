"""API tests: /api/crimes/by-hour (heatmap day x hour).

Fixture rows: 2 crimes on Tue 2026-09-15 (hours 10 and 11) + 1 on Sun
2026-09-20 (hour 22) -> 3 heatmap cells, ISO order (2 before 7).
"""


def test_by_hour_cells(api_client):
    resp = api_client.get("/api/crimes/by-hour")
    assert resp.status_code == 200
    assert resp.json() == [
        {"day_of_week": 2, "day_name": "Tuesday", "hour": 10, "crime_count": 1},
        {"day_of_week": 2, "day_name": "Tuesday", "hour": 11, "crime_count": 1},
        {"day_of_week": 7, "day_name": "Sunday", "hour": 22, "crime_count": 1},
    ]
