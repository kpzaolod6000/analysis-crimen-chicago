"""Reports router: payloads for Power Automate (weekly report)."""

import fastapi

from api.app.db import Conn
from api.app.schemas.crimes import WeeklyReport
from api.app.services import crimes as crimes_service

router = fastapi.APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/weekly", response_model=WeeklyReport)
def get_weekly_report(conn: Conn):
    data = crimes_service.weekly_report(conn)
    if data is None:
        raise fastapi.HTTPException(
            status_code=404, detail="warehouse has no data"
        )
    return data
