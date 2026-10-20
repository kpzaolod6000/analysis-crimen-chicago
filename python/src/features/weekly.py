"""Features semanales por community area (plan §8, ML Nivel 2).

Transformaciones puras de pandas sobre una grilla semanal: la entrada son
eventos (community_area, full_date) y la salida es una serie temporal
semanal por área con lags (1/2/4/8/52 semanas) y targets
(crime_count_next_week, hotspot_next_week).

Sin acceso a DB: los llamadores (notebooks, futura API) traen los eventos
con SQL y esta capa solo transforma — así se puede unit-testear sin
PostgreSQL y cumple "PostgreSQL transforma, Python calcula features".

Grano: una fila por (community_area, semana). La grilla es COMPLETA:
las semanas sin crímenes se rellenan con 0 para que los lags sean
aritmética de calendario y no corrimientos posicionales.
"""

import pandas as pd

LAG_WEEKS = (1, 2, 4, 8)
SAME_WEEK_YEAR_SHIFT = 52  # semanas ISO exactas


def week_start(dates: pd.Series) -> pd.Series:
    """Lunes (ISO) de la semana de cada fecha.

    ISO: lunes inicia la semana; un domingo cae en la semana que EMPIEZA
    6 días antes. Requiere datetime64; devuelve datetime64 a medianoche.
    """
    dates = pd.to_datetime(dates)
    return dates - pd.to_timedelta(dates.dt.weekday, unit="D")


def weekly_counts(events: pd.DataFrame) -> pd.DataFrame:
    """(community_area, full_date) -> grilla semanal completa por área.

    Columnas de entrada: community_area (numérico), full_date (datetime).
    Descarta filas sin fecha (equivalente a lo que ya hace la carga al
    warehouse). Salida: community_area, week_start, crime_count.
    """
    ev = events.copy()
    ev["full_date"] = pd.to_datetime(ev["full_date"])
    ev = ev.dropna(subset=["full_date"])
    ev["week_start"] = week_start(ev["full_date"])

    counts = (
        ev.groupby(["community_area", "week_start"])
        .size()
        .rename("crime_count")
        .reset_index()
    )

    # grilla completa: áreas × todas las semanas del rango global
    full_weeks = pd.DataFrame(
        {"week_start": pd.date_range(counts["week_start"].min(),
                                     counts["week_start"].max(),
                                     freq="7D")}
    )
    areas = pd.DataFrame({"community_area": counts["community_area"].unique()})
    grid = areas.merge(full_weeks, how="cross")
    weekly = grid.merge(counts, how="left", on=["community_area", "week_start"])
    weekly["crime_count"] = weekly["crime_count"].fillna(0).astype(int)

    return weekly.sort_values(
        ["community_area", "week_start"]
    ).reset_index(drop=True)


def hotspot_threshold(weekly: pd.DataFrame, q: float = 0.9) -> float:
    """Umbral de hotspot: percentil `q` del crime_count de la grilla."""
    return float(weekly["crime_count"].quantile(q))


def add_lags(
    weekly: pd.DataFrame, lag_weeks: tuple[int, ...] = LAG_WEEKS
) -> pd.DataFrame:
    """Agrega lag_{w}w por área (shift de w posiciones EN la grilla completa)."""
    out = weekly.copy()
    per_area = out.groupby("community_area")["crime_count"]
    for w in lag_weeks:
        out[f"lag_{w}w"] = per_area.shift(w)
    return out


def build_features(
    weekly: pd.DataFrame,
    lag_weeks: tuple[int, ...] = LAG_WEEKS,
    hotspot_quantile: float = 0.9,
) -> pd.DataFrame:
    """Entrada completa: lags + misma semana del año pasado + targets.

    - lag_{w}w para w en lag_weeks, más lag_52w (misma semana, año anterior).
    - crime_count_next_week: shift(-1) por área; NULL en la última semana.
    - hotspot_next_week: 1 si crime_count_next_week >= umbral
      (percentil hotspot_quantile de TODOS los counts de la grilla);
      0 si no hay semana siguiente (target no definido -> 0).
    """
    out = add_lags(weekly, lag_weeks)
    per_area = out.groupby("community_area")["crime_count"]
    out["lag_52w"] = per_area.shift(SAME_WEEK_YEAR_SHIFT)
    out["crime_count_next_week"] = per_area.shift(-1)

    threshold = hotspot_threshold(out, hotspot_quantile)
    next_week = out["crime_count_next_week"]
    out["hotspot_next_week"] = (next_week.notna() & (next_week >= threshold)).astype(int)
    return out
