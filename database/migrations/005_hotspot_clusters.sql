-- 005_hotspot_clusters.sql — resultado de DBSCAN (Sprint 5, Paso 5).
--
-- Dos tablas: hotspot_runs (una corrida del algoritmo: parámetros + totales)
-- y hotspot_clusters (un cluster por corrida: centroide + bbox + volumen).
-- El ruido (label -1) NO se guarda como cluster: queda resumido en
-- hotspot_runs.n_noise (los puntos aislados no son hotspots).
-- Idempotente (IF NOT EXISTS) como todas las migrations. La escritura es
-- append-only por run_key: re-correr DBSCAN con otros parámetros crea una
-- corrida nueva sin pisar la anterior (comparación de parámetros).

CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE TABLE IF NOT EXISTS warehouse.hotspot_runs (
    run_key      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    eps          DOUBLE PRECISION NOT NULL,
    min_samples  INTEGER NOT NULL CHECK (min_samples >= 1),
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_clusters   INTEGER NOT NULL CHECK (n_clusters >= 0),
    n_noise      INTEGER NOT NULL CHECK (n_noise >= 0)
);

CREATE TABLE IF NOT EXISTS warehouse.hotspot_clusters (
    cluster_key   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_key       INTEGER NOT NULL REFERENCES warehouse.hotspot_runs (run_key),
    cluster_label INTEGER NOT NULL CHECK (cluster_label >= 0),
    centroid_lat  DOUBLE PRECISION NOT NULL,
    centroid_lon  DOUBLE PRECISION NOT NULL,
    n_points      INTEGER NOT NULL CHECK (n_points >= 1),
    min_lat       DOUBLE PRECISION NOT NULL,
    max_lat       DOUBLE PRECISION NOT NULL,
    min_lon       DOUBLE PRECISION NOT NULL,
    max_lon       DOUBLE PRECISION NOT NULL,
    UNIQUE (run_key, cluster_label)
);

CREATE INDEX IF NOT EXISTS idx_hotspot_clusters_run
    ON warehouse.hotspot_clusters (run_key);
