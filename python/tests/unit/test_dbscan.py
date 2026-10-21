"""Unit tests for models.dbscan â€” fit + cluster_summaries (pure, no DB).

Synthetic deterministic points: two tight trios (members within ~280 real meters) plus
one far-away outlier. With haversine eps_meters=200 / min_samples=3 DBSCAN must find
exactly 2 clusters and 1 noise point; summaries carry centroid = mean of
members and the bounding box.
"""

import pandas as pd
import pytest
from models import dbscan

CLUSTER_A = [(41.880, -87.630), (41.881, -87.631), (41.879, -87.629)]
CLUSTER_B = [(41.780, -87.600), (41.781, -87.601), (41.779, -87.599)]
OUTLIER = (41.000, -87.000)


@pytest.fixture
def points():
    rows = CLUSTER_A + CLUSTER_B + [OUTLIER]
    return pd.DataFrame(rows, columns=["latitude", "longitude"])


@pytest.fixture
def labels(points):
    return dbscan.fit(points, eps_meters=200, min_samples=3)


def test_fit_finds_two_clusters_and_noise(labels):
    non_noise = {lbl for lbl in labels if lbl >= 0}
    assert len(non_noise) == 2
    assert labels[-1] == -1  # el outlier, Ãºltimo punto


def test_fit_clusters_keep_members_together(labels):
    assert labels[0] == labels[1] == labels[2]   # trio A
    assert labels[3] == labels[4] == labels[5]   # trio B
    assert labels[0] != labels[3]                # A y B distintos


def test_fit_empty_points():
    assert dbscan.fit(pd.DataFrame(columns=["latitude", "longitude"]), eps_meters=200, min_samples=3) == []


def test_summaries_shape_and_order(points, labels):
    summary = dbscan.cluster_summaries(points, labels)
    assert len(summary) == 2
    # ordenado por volumen DESC
    assert list(summary.n_points) == [3, 3]


def test_summaries_centroid_is_mean(points, labels):
    summary = dbscan.cluster_summaries(points, labels)
    row_a = summary[summary.cluster_label == labels[0]].iloc[0]
    lats = [lat for lat, _ in CLUSTER_A]
    lons = [lon for _, lon in CLUSTER_A]
    assert row_a.centroid_lat == pytest.approx(sum(lats) / 3)
    assert row_a.centroid_lon == pytest.approx(sum(lons) / 3)


def test_summaries_bbox(points, labels):
    summary = dbscan.cluster_summaries(points, labels)
    row_b = summary[summary.cluster_label == labels[3]].iloc[0]
    lats = [lat for lat, _ in CLUSTER_B]
    lons = [lon for _, lon in CLUSTER_B]
    assert row_b.min_lat == min(lats) and row_b.max_lat == max(lats)
    assert row_b.min_lon == min(lons) and row_b.max_lon == max(lons)


def test_summaries_empty_when_all_noise():
    pts = pd.DataFrame([(41.0, -87.0), (41.5, -87.5)],
                       columns=["latitude", "longitude"])
    labels = dbscan.fit(pts, eps_meters=50, min_samples=3)
    assert all(lbl == -1 for lbl in labels)
    summary = dbscan.cluster_summaries(pts, labels)
    assert summary.empty
