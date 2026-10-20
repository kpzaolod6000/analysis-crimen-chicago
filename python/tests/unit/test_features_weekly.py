"""Unit tests for features.weekly (Sprint 5 · Paso 4).

Hand-computed fixture:
    area 1: 10/20/30/40/50 crimes in weeks W1..W5 (Mon 2026-09-07 onwards)
    area 2: 5 crimes in W1, 7 on a WEDNESDAY of W2 (mid-week date), then
            gaps (weeks W3-W5 zero-filled)
    threshold q=0.9 over [0,0,0,5,7,10,20,30,40,50] -> position 8.1 of the
    sorted list = 40 + 0.1*(50-40) = 41.0, so only the week whose NEXT week
    reaches 50 (area 1, W4) is a hotspot. lags 8w/52w all NaN (5 weeks max).
"""

import datetime as dt

import pandas as pd
import pytest
from features import weekly

W1, W2, W3, W4, W5 = (
    "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05"
)


@pytest.fixture
def events():
    rows = []
    for area, week, n in [
        (1, W1, 10), (1, W2, 20), (1, W3, 30), (1, W4, 40), (1, W5, 50),
        (2, W1, 5),
        (2, "2026-09-16", 7),  # miércoles de W2
    ]:
        rows += [(area, week)] * n
    return pd.DataFrame(rows, columns=["community_area", "full_date"])


@pytest.fixture
def weekly_grid(events):
    return weekly.weekly_counts(events)


@pytest.fixture
def builded(weekly_grid):
    return weekly.build_features(weekly_grid)


# ── week_start (ISO: la semana inicia lunes) ─────────────────────────────

def test_week_start_keeps_monday():
    s = weekly.week_start(pd.Series([pd.Timestamp("2026-09-14")]))
    assert s.iloc[0] == pd.Timestamp("2026-09-14")


def test_week_start_sunday_maps_to_previous_monday():
    # 2026-09-20 es domingo: su semana ISO empezó el lunes 14
    s = weekly.week_start(pd.Series([pd.Timestamp("2026-09-20")]))
    assert s.iloc[0] == pd.Timestamp("2026-09-14")


def test_week_start_midweek_maps_to_monday():
    # 2026-09-16 es miércoles (2026-09-15 es martes, establecido en Sprint 4)
    s = weekly.week_start(pd.Series([pd.Timestamp("2026-09-16")]))
    assert s.iloc[0] == pd.Timestamp("2026-09-14")


# ── weekly_counts: agregación + zero-fill ────────────────────────────────

def test_weekly_counts_full_grid(weekly_grid):
    # 2 áreas × 5 semanas = 10 filas
    assert len(weekly_grid) == 10


def test_weekly_counts_area1_sequence(weekly_grid):
    a1 = weekly_grid[weekly_grid.community_area == 1]
    assert list(a1.crime_count) == [10, 20, 30, 40, 50]
    assert list(a1.week_start.dt.date) == [
        dt.date(2026, 9, 7), dt.date(2026, 9, 14), dt.date(2026, 9, 21),
        dt.date(2026, 9, 28), dt.date(2026, 10, 5),
    ]


def test_weekly_counts_zero_fills_gaps(weekly_grid):
    a2 = weekly_grid[weekly_grid.community_area == 2]
    assert list(a2.crime_count) == [5, 7, 0, 0, 0]


def test_weekly_counts_midweek_date_falls_into_correct_week(weekly_grid):
    # el miércoles 16 aporta a la semana del lunes 14, no crea una nueva
    a2 = weekly_grid[weekly_grid.community_area == 2]
    assert list(a2.week_start.dt.date)[1] == dt.date(2026, 9, 14)


def test_weekly_counts_drops_null_dates():
    ev = pd.DataFrame(
        {"community_area": [1, 1], "full_date": ["2026-09-14", None]}
    )
    grid = weekly.weekly_counts(ev)
    assert len(grid) == 1 and grid.crime_count.iloc[0] == 1


# ── lags: sin leaks entre áreas ──────────────────────────────────────────

def test_lag1_area1(builded):
    a1 = builded[builded.community_area == 1]
    vals = a1.lag_1w
    assert vals.isna().tolist() == [True, False, False, False, False]
    assert vals.dropna().tolist() == [10.0, 20.0, 30.0, 40.0]


def test_lag1_no_cross_area_leak(builded):
    # si los lags fueran posicionales globales, aquí aparecería el 50 del área 1
    a2 = builded[builded.community_area == 2]
    vals = a2.lag_1w
    assert vals.isna().tolist() == [True, False, False, False, False]
    assert vals.dropna().tolist() == [5.0, 7.0, 0.0, 0.0]


def test_lag2_area1(builded):
    a1 = builded[builded.community_area == 1]
    vals = a1.lag_2w
    assert vals.isna().tolist() == [True, True, False, False, False]
    assert vals.dropna().tolist() == [10.0, 20.0, 30.0]


def test_lag8_all_nan_with_5_weeks(builded):
    assert builded.lag_8w.isna().all()


def test_lag52_nan(builded):
    assert builded.lag_52w.isna().all()


# ── targets ──────────────────────────────────────────────────────────────

def test_target_next_week_area1(builded):
    a1 = builded[builded.community_area == 1]
    vals = a1.crime_count_next_week
    assert vals.isna().tolist() == [False, False, False, False, True]
    assert vals.dropna().tolist() == [20.0, 30.0, 40.0, 50.0]


def test_target_last_week_nan(builded):
    last_rows = builded.groupby("community_area").tail(1)
    assert all(v is None or pd.isna(v) for v in last_rows.crime_count_next_week)


def test_hotspot_threshold_value(weekly_grid):
    assert weekly.hotspot_threshold(weekly_grid, q=0.9) == 41.0


def test_hotspot_next_week_binary(builded):
    a1 = builded[builded.community_area == 1]
    # solo W4 alcanza el umbral (su next week = 50 >= 41)
    assert list(a1.hotspot_next_week) == [0, 0, 0, 1, 0]


def test_hotspot_next_week_area2_never(builded):
    a2 = builded[builded.community_area == 2]
    assert list(a2.hotspot_next_week) == [0, 0, 0, 0, 0]
