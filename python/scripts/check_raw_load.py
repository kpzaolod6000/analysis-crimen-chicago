"""Smoke test: comprueba que la DB de DESARROLLO quedó poblada tras un run
del workflow n8n (docs/testing.md §2.4).

No usa pytest ni requiere datos: corre contra dev (5432) por defecto y
reporta el estado de `raw.crimes` y `ops.pipeline_runs`. Sale con código 1
si raw.crimes está vacía; advierte (sin fallar) sobre duplicados/coords.
Las métricas de calidad vienen de `ingestion.quality` (misma fuente que los
data tests de integración).

Uso:
    .\\.venv\\Scripts\\python.exe python/scripts/check_raw_load.py
    # contra otra DB: --host --port --user --password --dbname
"""

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion import quality


def query(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description="Smoke check de la carga raw.crimes")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    parser.add_argument("--dbname", default="chicago_crimes")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.dbname,
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        total = quality.total_rows(cur)
        print(f"[raw.crimes] filas totales: {total}")
        if total == 0:
            print("FALLO: raw.crimes esta vacia (el workflow no se ejecuto o fallo)")
            return 1

        (min_date, max_date) = query(
            cur, "SELECT min(date)::text, max(date)::text FROM raw.crimes"
        )[0]
        print(f"[raw.crimes] ventana real: {min_date} -> {max_date}")

        warnings: list[tuple[str, int]] = [
            ("[raw.crimes] ids duplicados (violacion PK/UPSERT)", quality.duplicate_ids(cur)),
            (
                "[raw.crimes] coordenadas fuera de rango",
                quality.out_of_range_coordinates(cur),
            ),
            ("[raw.crimes] ids nulos", quality.null_ids(cur)),
        ]

        rows = query(
            cur,
            "SELECT run_id, workflow_name, status, records_received, records_failed "
            "FROM ops.pipeline_runs ORDER BY run_id DESC LIMIT 5",
        )
        print("[ops.pipeline_runs] ultimos runs:")
        for row in rows:
            print(f"   {row}")

    print("Advertencias (deben ser 0):")
    for label, value in warnings:
        print(f"   {label}: {value}")
    ok = all(value == 0 for _, value in warnings)
    result = "OK" if ok else "CON ADVERTENCIAS"
    print(f"RESULTADO: {result} - {total} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
