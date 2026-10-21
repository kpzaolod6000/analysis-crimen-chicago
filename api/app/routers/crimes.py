"""Crimes router: reads over the warehouse star."""

import fastapi

from api.app.db import Conn
from api.app.schemas.crimes import (
    AreaRanking,
    CrimesSummary,
    CrimeTypeCount,
    HotspotsResponse,
    MonthlyTrend,
)
from api.app.services import crimes as crimes_service

router = fastapi.APIRouter(prefix="/api/crimes", tags=["crimes"])


@router.get("/summary", response_model=CrimesSummary)
def get_crimes_summary(conn: Conn):
    return crimes_service.crimes_summary(conn)


@router.get("/trends", response_model=list[MonthlyTrend])
def get_crimes_trends(conn: Conn):
    return crimes_service.monthly_trends(conn)


@router.get("/by-type", response_model=list[CrimeTypeCount])
def get_crimes_by_type(
    conn: Conn,
    limit: int | None = fastapi.Query(default=None, ge=1, le=100),
):
    return crimes_service.crime_types(conn, limit)


@router.get("/by-community-area", response_model=list[AreaRanking])
def get_crimes_by_community_area(
    conn: Conn,
    limit: int | None = fastapi.Query(default=None, ge=1, le=100),
):
    return crimes_service.area_ranking(conn, limit)


@router.get("/hotspots", response_model=HotspotsResponse)
def get_crimes_hotspots(
    conn: Conn,
    run_key: int | None = fastapi.Query(default=None, ge=1),
):
    data = crimes_service.hotspots(conn, run_key)
    if data is None:
        raise fastapi.HTTPException(
            status_code=404,
            detail="no hotspot runs stored (run the DBSCAN notebook first)",
        )
    return data
