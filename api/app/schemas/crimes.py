"""Pydantic schemas for the crimes endpoints."""

from datetime import date, datetime

from pydantic import BaseModel


class CrimesSummary(BaseModel):
    crime_count: int
    arrest_count: int
    arrest_rate_pct: float
    first_crime_date: date | None
    last_crime_date: date | None
    distinct_crime_types: int
    distinct_community_areas: int


class MonthlyTrend(BaseModel):
    month_date: date
    year: int
    month: int
    month_name: str
    crime_count: int
    arrest_count: int
    arrest_rate_pct: float


class CrimeTypeCount(BaseModel):
    primary_type: str
    crime_count: int
    share_pct: float


class AreaRanking(BaseModel):
    community_area: int
    community_area_name: str
    crime_count: int
    share_pct: float
    crime_rank: int


class HotspotRun(BaseModel):
    run_key: int
    eps: float            # metros reales (haversine), guardado por save_run
    min_samples: int
    computed_at: datetime  # serializado a ISO por FastAPI
    n_clusters: int
    n_noise: int


class HotspotCluster(BaseModel):
    cluster_label: int
    centroid_lat: float
    centroid_lon: float
    n_points: int
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


class HotspotsResponse(BaseModel):
    run: HotspotRun
    clusters: list[HotspotCluster]


class WeeklyTypeRow(BaseModel):
    primary_type: str
    crime_count: int
    share_pct: float


class WeeklyAreaRow(BaseModel):
    community_area: int
    community_area_name: str
    crime_count: int


class WeeklyReport(BaseModel):
    period_start: date
    period_end: date
    crime_count: int
    arrest_count: int
    arrest_rate_pct: float
    crime_change_pct: float | None   # vs los 7 días previos; None si no hay base
    top_crime_types: list[WeeklyTypeRow]
    top_areas: list[WeeklyAreaRow]
    hotspots: list[HotspotCluster]   # top 3 de la última corrida DBSCAN


class Health(BaseModel):
    status: str
    database: str
