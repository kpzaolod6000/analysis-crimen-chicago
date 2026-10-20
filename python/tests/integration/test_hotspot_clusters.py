"""Integration tests for hotspot persistence (005_hotspot_clusters.sql +
models.dbscan.save_run).

Covers: tables/columns exist, save_run writes 1 run + N clusters, second
save_run appends (append-only by run), CHECK constraints (label >= 0,
min_samples >= 1) and the UNIQUE (run_key, cluster_label).
"""


import pandas as pd
import psycopg2
import pytest
from conftest import REPO_ROOT, apply_migration
from models import dbscan

DDL_SQL = (REPO_ROOT / "database" / "migrations" / "005_hotspot_clusters.sql").read_text(
    encoding="utf-8"
)

POINTS = pd.DataFrame(
    [(41.880, -87.630), (41.881, -87.631), (41.879, -87.629)],
    columns=["latitude", "longitude"],
)
LABELS = [0, 0, 0]


@pytest.fixture(scope="module")
def hotspot_db(migrated_db):
    """Aplica 005; deja las tablas de hotspots vacÃ­as al terminar."""
    apply_migration(migrated_db, "005_hotspot_clusters.sql")
    with migrated_db.cursor() as cur:
        cur.execute("TRUNCATE warehouse.hotspot_clusters, warehouse.hotspot_runs RESTART IDENTITY")
    yield migrated_db
    with migrated_db.cursor() as cur:
        cur.execute("TRUNCATE warehouse.hotspot_clusters, warehouse.hotspot_runs RESTART IDENTITY")


def test_migration_is_idempotent(hotspot_db):
    apply_migration(hotspot_db, "005_hotspot_clusters.sql")


def test_hotspot_tables_exist(hotspot_db):
    with hotspot_db.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'warehouse' AND table_type = 'BASE TABLE' "
            "AND table_name LIKE 'hotspot%' ORDER BY table_name"
        )
        names = [r[0] for r in cur.fetchall()]
    assert names == ["hotspot_clusters", "hotspot_runs"]


def test_save_run_writes_run_and_cluster(hotspot_db):
    run_key = dbscan.save_run(hotspot_db, eps_meters=200, min_samples=3,
                              points=POINTS, labels=LABELS)
    with hotspot_db.cursor() as cur:
        cur.execute(
            "SELECT eps, min_samples, n_clusters, n_noise "
            "FROM warehouse.hotspot_runs WHERE run_key = %s",
            (run_key,),
        )
        (eps, min_samples, n_clusters, n_noise) = cur.fetchone()
        cur.execute(
            "SELECT cluster_label, n_points, centroid_lat "
            "FROM warehouse.hotspot_clusters WHERE run_key = %s",
            (run_key,),
        )
        (label, n_points, centroid_lat) = cur.fetchone()
    assert eps == 200.0 and min_samples == 3
    assert n_clusters == 1 and n_noise == 0
    assert label == 0 and n_points == 3
    assert centroid_lat == pytest.approx((41.88 + 41.881 + 41.879) / 3)


def test_save_run_appends_new_run(hotspot_db):
    dbscan.save_run(hotspot_db, eps_meters=400, min_samples=5,
                    points=POINTS, labels=LABELS)
    with hotspot_db.cursor() as cur:
        cur.execute("SELECT count(*) FROM warehouse.hotspot_runs")
        (runs,) = cur.fetchone()
        cur.execute("SELECT count(*) FROM warehouse.hotspot_clusters")
        (clusters,) = cur.fetchone()
    assert runs == 2 and clusters == 2  # append-only, no pisa la corrida 1


def test_all_noise_run_has_zero_clusters(hotspot_db):
    # labels todos -1: corrida vÃ¡lida con n_clusters 0, n_noise 3 y NINGÃšA
    # fila en hotspot_clusters (el ruido no es hotspot)
    run_key = dbscan.save_run(hotspot_db, eps_meters=50, min_samples=3,
                              points=POINTS, labels=[-1, -1, -1])
    with hotspot_db.cursor() as cur:
        cur.execute(
            "SELECT n_clusters, n_noise FROM warehouse.hotspot_runs "
            "WHERE run_key = %s",
            (run_key,),
        )
        (n_clusters, n_noise) = cur.fetchone()
        cur.execute(
            "SELECT count(*) FROM warehouse.hotspot_clusters "
            "WHERE run_key = %s",
            (run_key,),
        )
        (rows,) = cur.fetchone()
    assert n_clusters == 0 and n_noise == 3 and rows == 0


def test_negative_label_rejected_by_ddl(hotspot_db):
    # save_run nunca emite labels negativos (los filtra como ruido); el
    # CHECK del DDL es la defensa de Ãºltima lÃ­nea contra escritura directa
    with hotspot_db.cursor() as cur, pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute(
            """
                INSERT INTO warehouse.hotspot_clusters
                    (run_key, cluster_label, centroid_lat, centroid_lon,
                     n_points, min_lat, max_lat, min_lon, max_lon)
                VALUES (1, -1, 41.0, -87.0, 1, 41.0, 41.0, -87.0, -87.0)
                """
        )
