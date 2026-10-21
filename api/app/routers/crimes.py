"""Crimes router: reads over the warehouse star."""

import fastapi

from api.app.db import Conn
from api.app.schemas.crimes import CrimesSummary
from api.app.services import crimes as crimes_service

router = fastapi.APIRouter(prefix="/api/crimes", tags=["crimes"])


@router.get("/summary", response_model=CrimesSummary)
def get_crimes_summary(conn: Conn):
    return crimes_service.crimes_summary(conn)
