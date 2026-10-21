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


class Health(BaseModel):
    status: str
    database: str
