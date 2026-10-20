"""DBSCAN de hotspots (plan §8, ML Nivel 1) — fit + resumen + persistencia.

Entrada: DataFrame de puntos con latitude/longitude (staging ya limpio:
(0,0) y fuera de rango son NULL, así que los llamadores filtran
`latitude IS NOT NULL AND longitude IS NOT NULL`).

Salidas:
- `fit()` -> labels numpy (cluster_label >= 0, ruido = -1)
- `cluster_summaries()` -> DataFrame por cluster: centroide (media), bbox
  y volumen (n_points)
- `save_run()` -> persiste una corrida en warehouse.hotspot_runs +
  warehouse.hotspot_clusters (005_hotspot_clusters.sql), atómicamente.

eps se especifica en METROS (eps_meters): el módulo convierte a radianes
internamente (haversine + ball_tree); el notebook 04 explora radios
reales (p.ej. 200 m).
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

# radio terrestre medio en metros (conversión eps_meters -> eps radianes)
EARTH_RADIUS_M = 6_371_000


def fit(
    points: pd.DataFrame, eps_meters: float, min_samples: int
) -> "list[int]":
    """Ejecuta DBSCAN sobre (latitude, longitude); devuelve labels como ints.

    Métrica haversine (plan §8, decisión 2026-10-17): distancia real en la
    superficie terrestre. Con euclídea en grados el eps no es comparable
    N-S vs E-O (a 41.88° un grado de longitud mide cos(41.88) ≈ 0.745 de un
    grado) — los clusters saldrían elipses estiradas E-O. Con haversine,
    eps_meters es METROS REALES (interpretable para el dashboard).

    sklearn exige: coordenadas en RADIANES + algorithm="ball_tree"
    (kd_tree no soporta haversine). DBSCAN necesita densidad: puntos
    repetidos (misma esquina) cuentan directo, sin dedup.
    """
    if points.empty:
        return []
    coords = np.radians(points[["latitude", "longitude"]].to_numpy(dtype="float64"))
    labels = DBSCAN(
        eps=eps_meters / EARTH_RADIUS_M,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(coords)
    return [int(v) for v in labels]


def cluster_summaries(
    points: pd.DataFrame, labels: "list[int]"
) -> pd.DataFrame:
    """Resumen por cluster (label >= 0): centroide, bbox y n_points.

    Ordenado por n_points DESC (el hotspot más denso primero).
    """
    pts = points.assign(cluster_label=labels)
    pts = pts[pts["cluster_label"] >= 0]
    if pts.empty:
        return pd.DataFrame(
            columns=[
                "cluster_label", "centroid_lat", "centroid_lon",
                "n_points", "min_lat", "max_lat", "min_lon", "max_lon",
            ]
        )
    grouped = pts.groupby("cluster_label").agg(
        centroid_lat=("latitude", "mean"),
        centroid_lon=("longitude", "mean"),
        n_points=("latitude", "size"),
        min_lat=("latitude", "min"),
        max_lat=("latitude", "max"),
        min_lon=("longitude", "min"),
        max_lon=("longitude", "max"),
    )
    return grouped.sort_values("n_points", ascending=False).reset_index()


def save_run(
    conn,
    eps_meters: float,
    min_samples: int,
    points: pd.DataFrame,
    labels: "list[int]",
) -> int:
    """Persiste la corrida completa y devuelve run_key.

    Inserta 1 fila en hotspot_runs (parámetros + totales) y 1 fila por
    cluster en hotspot_clusters. Transacción explícita: o queda la corrida
    completa o nada (independiente del autocommit del llamador). En la DB,
    eps se guarda en METROS (eps_meters) — el valor interpretado por el
    dashboard.
    """
    labels = list(labels)
    n_clusters = len([lbl for lbl in set(labels) if lbl >= 0])
    n_noise = labels.count(-1)
    summaries = cluster_summaries(points, labels)

    was_autocommit = conn.autocommit
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO warehouse.hotspot_runs
                (eps, min_samples, n_clusters, n_noise)
            VALUES (%s, %s, %s, %s)
            RETURNING run_key
            """,
            (eps_meters, min_samples, n_clusters, n_noise),
        )
        (run_key,) = cur.fetchone()
        cur.executemany(
            """
            INSERT INTO warehouse.hotspot_clusters
                (run_key, cluster_label, centroid_lat, centroid_lon,
                 n_points, min_lat, max_lat, min_lon, max_lon)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    run_key,
                    int(row.cluster_label),
                    float(row.centroid_lat),
                    float(row.centroid_lon),
                    int(row.n_points),
                    float(row.min_lat), float(row.max_lat),
                    float(row.min_lon), float(row.max_lon),
                )
                for row in summaries.itertuples(index=False)
            ],
        )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = was_autocommit
    return run_key
