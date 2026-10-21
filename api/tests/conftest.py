"""Fixtures for the API tests (TestClient + test DB on 5433).

Maps TEST_POSTGRES_* (CI/local convention) to API_POSTGRES_* so the app's
dependency resolves to the test database, then applies the warehouse stack
(001/003/004/005 + seed + functions + views) and seeds 3 known rows.
"""

import os
from pathlib import Path

import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


# TEST_POSTGRES_* (convención de python/tests) -> API_POSTGRES_* (app)
for _dst, _src in [
    ("API_POSTGRES_HOST", "TEST_POSTGRES_HOST"),
    ("API_POSTGRES_PORT", "TEST_POSTGRES_PORT"),
    ("API_POSTGRES_USER", "TEST_POSTGRES_USER"),
    ("API_POSTGRES_PASSWORD", "TEST_POSTGRES_PASSWORD"),
    ("API_POSTGRES_DB", "TEST_POSTGRES_DB"),
]:
    if os.getenv(_src):
        os.environ[_dst] = os.environ[_src]

# defaults locales (CI setea TEST_POSTGRES_*; local no): la app y los
# fixtures deben caer SIEMPRE en la DB de pruebas (5433), nunca en dev
os.environ.setdefault("API_POSTGRES_HOST", "localhost")
os.environ.setdefault("API_POSTGRES_PORT", "5433")
os.environ.setdefault("API_POSTGRES_USER", "postgres")
os.environ.setdefault("API_POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("API_POSTGRES_DB", "chicago_crimes_test")

# importable: api.app (REPO_ROOT en sys.path para los fixtures)
import sys

sys.path.insert(0, str(REPO_ROOT))

# seed de 3 filas conocidas (áreas 22/41/76 del catálogo real):
#   3 crímenes, 1 arresto (33.3%), fechas 2026-09-15..2026-09-20,
#   3 tipos, 2 áreas (una sin área), 3 locations
SEED_ROWS_SQL = """
INSERT INTO raw.crimes (id, date, iucr, primary_type, description, block,
                        location_description, community_area, district,
                        latitude, longitude, arrest, domestic)
VALUES
  ('API-01', '2026-09-15T10:00:00', '0820', 'THEFT', '$500 AND UNDER',
   '001XX N STATE ST', 'STREET', 22, 4, 41.88, -87.63, True, False),
  ('API-02', '2026-09-15T11:00:00', '0310', 'BATTERY', 'SIMPLE',
   '02XX W MADISON ST', 'APARTMENT', 41, 8, 41.79, -87.65, False, True),
  ('API-03', '2026-09-20T22:00:00', '0312', 'ROBBERY', 'ARMED: HANDGUN',
   '030XX W OHIO ST', 'STREET', NULL, 2, 41.88, -87.64, False, False)
"""


@pytest.fixture(scope="session")
def api_db():
    """Aplica todo el stack al warehouse de pruebas y siembra filas.

    Usa EXACTAMENTE la misma configuración de conexión que la app
    (connection_settings), así fixtures y app golpean la misma DB.
    """
    from api.app.db import connection_settings

    conn = psycopg2.connect(**connection_settings())
    conn.autocommit = True
    for sql in [
        _read("database/migrations/001_raw.sql"),
        _read("database/migrations/003_staging.sql"),
        _read("database/migrations/004_dims_fact.sql"),
        _read("database/migrations/005_hotspot_clusters.sql"),
        _read("database/functions/load_warehouse.sql"),
        _read("database/views/analytics.sql"),
    ]:
        with conn.cursor() as cur:
            cur.execute(sql)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE raw.crimes, warehouse.fact_crime, warehouse.dim_date, "
            "warehouse.dim_crime_type, warehouse.dim_location, "
            "warehouse.dim_district, warehouse.dim_community_area "
            "RESTART IDENTITY CASCADE"
        )
        # seed DESPUÉS del truncate: el loader NO repobla dim_community_area
        # (diseño: el seed la posee); si se quedara antes, el truncate la
        # dejaría vacía y los community_area_key de fact serían NULL
        cur.execute(_read("database/seeds/community_areas.sql"))
        cur.execute(SEED_ROWS_SQL)
        cur.execute("SELECT warehouse.load_warehouse()")
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def api_client(api_db):
    """TestClient contra la app (la conexión se resuelve por request)."""
    from fastapi.testclient import TestClient

    from api.app.main import create_app

    return TestClient(create_app())
