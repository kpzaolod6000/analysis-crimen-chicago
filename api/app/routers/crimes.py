"""Crimes router: reads over the warehouse star."""

import fastapi

from api.app.db import Conn
from api.app.schemas.crimes import (
    AreaRanking,
    CrimesSummary,
    CrimeTypeCount,
    DayHourRow,
    HotspotsResponse,
    MonthlyTrend,
)
from api.app.services import crimes as crimes_service

# filtros compartidos por los endpoints analíticos (Sprint 7 Paso 5):
# el frontend (filters.js) los manda como query params
FilterParams = fastapi.Query(default=None)
filter_type: str | None = fastapi.Query(default=None, min_length=1)
filter_year: int | None = fastapi.Query(default=None, ge=2001)
filter_month: int | None = fastapi.Query(default=None, ge=1, le=12)
filter_area: int | None = fastapi.Query(default=None, ge=1, le=77)


def _filters(primary_type=None, year=None, month=None, community_area=None) -> dict:
    return {
        "primary_type": primary_type,
        "year": year,
        "month": month,
        "community_area": community_area,
    }


router = fastapi.APIRouter(prefix="/api/crimes", tags=["crimes"])


@router.get("/summary", response_model=CrimesSummary)
def get_crimes_summary(
    conn: Conn,
    primary_type: str | None = filter_type,
    year: int | None = filter_year,
    month: int | None = filter_month,
    community_area: int | None = filter_area,
):
    return crimes_service.crimes_summary(
        conn, _filters(primary_type, year, month, community_area)
    )


@router.get("/trends", response_model=list[MonthlyTrend])
def get_crimes_trends(
    conn: Conn,
    primary_type: str | None = filter_type,
    year: int | None = filter_year,
    month: int | None = filter_month,
    community_area: int | None = filter_area,
):
    return crimes_service.monthly_trends(
        conn, _filters(primary_type, year, month, community_area)
    )


@router.get("/by-type", response_model=list[CrimeTypeCount])
def get_crimes_by_type(
    conn: Conn,
    limit: int | None = fastapi.Query(default=None, ge=1, le=100),
    year: int | None = filter_year,
    month: int | None = filter_month,
    community_area: int | None = filter_area,
):
    return crimes_service.crime_types(
        conn, limit, _filters(year=year, month=month, community_area=community_area)
    )


@router.get("/by-community-area", response_model=list[AreaRanking])
def get_crimes_by_community_area(
    conn: Conn,
    limit: int | None = fastapi.Query(default=None, ge=1, le=100),
    primary_type: str | None = filter_type,
    year: int | None = filter_year,
    month: int | None = filter_month,
):
    return crimes_service.area_ranking(
        conn, limit, _filters(primary_type=primary_type, year=year, month=month)
    )


@router.get("/hotspots", response_model=HotspotsResponse)
def get_crimes_hotspots(
    conn: Conn,
    run_key: int | None = fastapi.Query(default=None, ge=1),
):
    # sin filtros: las corridas DBSCAN son precalculadas sobre el snapshot
    # completo (la proveniencia vive en warehouse.hotspot_runs)
    data = crimes_service.hotspots(conn, run_key)
    if data is None:
        raise fastapi.HTTPException(
            status_code=404,
            detail="no hotspot runs stored (run the DBSCAN notebook first)",
        )
    return data


@router.get("/by-hour", response_model=list[DayHourRow])
def get_crimes_by_hour(
    conn: Conn,
    primary_type: str | None = filter_type,
    year: int | None = filter_year,
    month: int | None = filter_month,
    community_area: int | None = filter_area,
):
    return crimes_service.day_hour(
        conn, _filters(primary_type, year, month, community_area)
    )
