"""Pydantic schemas for the crimes endpoints."""

from datetime import date

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


class Health(BaseModel):
    status: str
    database: str
