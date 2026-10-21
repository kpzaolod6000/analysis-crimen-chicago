"""API tests: /api/crimes/hotspots (runs DBSCAN persisted in the warehouse).

The api_db fixture leaves hotspot tables EMPTY (the warehouse loader does
not touch them), so test_hotspots_404 runs against no runs. hotspots_db
seeds one run (eps 200 m / min_samples 25) with 2 clusters by hand.
"""

import pytest
from fastapi.testclient import TestClient

RUN_FIELDS = {"run_key", "eps", "min_samples", "computed_at",
              "n_clusters", "n_noise"}
CLUSTER_FIELDS = {"cluster_label", "centroid_lat", "centroid_lon",
                  "n_points", "min_lat", "max_lat", "min_lon", "max_lon"}


@pytest.fixture
def hotspots_client(api_db):
    """TestClient con 1 corrida sembrada (2 clusters: 120 y 40 puntos);
    los hotspots quedan vacíos al terminar (estado base del api_db)."""
    from api.app.main import create_app

    with api_db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO warehouse.hotspot_runs
                (eps, min_samples, n_clusters, n_noise)
            VALUES (200.0, 25, 2, 100)
            RETURNING run_key
            """
        )
        (run_key,) = cur.fetchone()
        cur.execute(
            """
            INSERT INTO warehouse.hotspot_clusters
                (run_key, cluster_label, centroid_lat, centroid_lon,
                 n_points, min_lat, max_lat, min_lon, max_lon)
            VALUES
              (%s, 0, 41.8880, -87.6277, 120, 41.8728, 41.8999, -87.6396, -87.6170),
              (%s, 1, 41.9643, -87.6551, 40, 41.9590, 41.9690, -87.6614, -87.6487)
            """,
            (run_key, run_key),
        )
    client = TestClient(create_app())
    yield client
    with api_db.cursor() as cur:
        cur.execute("TRUNCATE warehouse.hotspot_clusters, warehouse.hotspot_runs RESTART IDENTITY")


def test_hotspots_404_when_no_runs(api_client):
    resp = api_client.get("/api/crimes/hotspots")
    assert resp.status_code == 404


def test_hotspots_latest_run(hotspots_client):
    resp = hotspots_client.get("/api/crimes/hotspots")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"run", "clusters"}
    assert body["run"]["run_key"] == 1
    assert set(body["run"]) == RUN_FIELDS
    assert body["run"]["eps"] == 200.0
    assert body["run"]["min_samples"] == 25
    assert body["run"]["n_clusters"] == 2
    assert body["run"]["n_noise"] == 100
    # clusters ordenados por volumen DESC (el más denso primero)
    assert [c["cluster_label"] for c in body["clusters"]] == [0, 1]
    assert [c["n_points"] for c in body["clusters"]] == [120, 40]
    assert all(set(c) == CLUSTER_FIELDS for c in body["clusters"])


def test_hotspots_explicit_run(hotspots_client):
    resp = hotspots_client.get("/api/crimes/hotspots", params={"run_key": 1})
    assert resp.status_code == 200
    assert resp.json()["run"]["run_key"] == 1


def test_hotspots_unknown_run_404(hotspots_client):
    resp = hotspots_client.get("/api/crimes/hotspots", params={"run_key": 999})
    assert resp.status_code == 404
