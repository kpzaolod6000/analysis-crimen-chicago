r"""FastAPI application factory (Sprint 6).

Run (dev, desde la raíz del repo):
    .\.venv\Scripts\python.exe -m uvicorn api.app.main:app --reload --port 8000
Docs automáticas: http://localhost:8000/docs (OpenAPI).
"""

import fastapi

from api.app.routers import crimes, health, reports


def create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI(
        title="Chicago Crimes API",
        description=(
            "Reads over the crime warehouse (vistas del Sprint 4 + clusters "
            "DBSCAN del Sprint 5). PostgreSQL agrega, la API expone."
        ),
        version="0.6.0",
    )
    app.include_router(health.router)
    app.include_router(crimes.router)
    app.include_router(reports.router)
    return app


app = create_app()
