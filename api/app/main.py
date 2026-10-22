r"""FastAPI application factory (Sprint 6).

Run (dev, desde la raíz del repo):
    .\.venv\Scripts\python.exe -m uvicorn api.app.main:app --reload --port 8000
Docs automáticas: http://localhost:8000/docs (OpenAPI).
"""

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from api.app.routers import crimes, health, reports

# orígenes del dashboard de desarrollo (Vite 5173 / preview 4173);
# API read-only, así que el riesgo de CORS abierto es bajo
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI(
        title="Chicago Crimes API",
        description=(
            "Reads over the crime warehouse (vistas del Sprint 4 + clusters "
            "DBSCAN del Sprint 5). PostgreSQL agrega, la API expone."
        ),
        version="0.6.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(crimes.router)
    app.include_router(reports.router)
    return app


app = create_app()
