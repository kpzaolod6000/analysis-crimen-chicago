"""Health router: liveness + DB connectivity check."""

import fastapi

from api.app.db import Conn
from api.app.schemas.crimes import Health
from api.app.services import crimes as crimes_service

router = fastapi.APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=Health)
def health(conn: Conn):
    db_ok = crimes_service.database_ok(conn)
    return Health(status="ok", database="ok" if db_ok else "down")
