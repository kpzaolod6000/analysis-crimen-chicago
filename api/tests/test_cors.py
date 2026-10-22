"""API tests: CORS preflight (the dashboard on Vite 5173 must be allowed)."""

from fastapi.testclient import TestClient  # noqa: F401 — sólo para tipos


def test_cors_preflight_allowed(api_client):
    resp = api_client.options(
        "/api/crimes/summary",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_unknown_origin_not_allowed(api_client):
    resp = api_client.options(
        "/api/crimes/summary",
        headers={
            "Origin": "http://evil-site.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 400
