"""Database connection for the API (psycopg2, one per request).

Config via env vars (API_POSTGRES_*), con defaults de desarrollo
(localhost:5432/chicago_crimes). Los tests apuntan a la DB de pruebas
(5433/chicago_crimes_test) seteando esas variables en su conftest.
"""

import os
from typing import Annotated

import psycopg2
from fastapi import Depends


def connection_settings() -> dict:
    return {
        "host": os.getenv("API_POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("API_POSTGRES_PORT", "5432")),
        "user": os.getenv("API_POSTGRES_USER", "postgres"),
        "password": os.getenv("API_POSTGRES_PASSWORD", "postgres"),
        "dbname": os.getenv("API_POSTGRES_DB", "chicago_crimes"),
    }


def connect_db():
    conn = psycopg2.connect(**connection_settings())
    conn.autocommit = True  # solo lectura: cada query es su propia transacción
    return conn


def get_conn():
    """Dependencia de FastAPI: conexión por request (abre y cierra)."""
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


# Conn = conexión de DB inyectada por FastAPI (patrón Annotated: evita
# B008, que rechaza llamadas en defaults de argumento)
Conn = Annotated[psycopg2.extensions.connection, Depends(get_conn)]
