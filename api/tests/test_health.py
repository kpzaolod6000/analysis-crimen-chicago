"""API tests: /api/health."""


def test_health_ok(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "database": "ok"}
