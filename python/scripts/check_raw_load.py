"""Smoke test: comprueba que la DB de DESARROLLO quedó poblada tras un run
del workflow n8n (docs/testing.md §2.4).

No usa pytest ni requiere datos: corre contra dev (5432) por defecto y
reporta el estado de `raw.crimes` y `ops.pipeline_runs`. Sale con código 1
si raw.crimes está vacía; advierte (sin fallar) sobre duplicados/coords.

Uso:
    .\\.venv\\Scripts\\python.exe python/scripts/check_raw_load.py
    # contra otra DB: --host --port --user --password --dbname
"""

import argparse
import sys

import psycopg2


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
        total, = query(cur, "SELECT count(*) FROM raw.crimes")[0]
        print(f"[raw.crimes] filas totales: {total}")
        if total == 0:
            print("FALLO: raw.crimes esta vacia (el workflow no se ejecuto o fallo)")
            return 1

        (min_date, max_date) = query(
            cur, "SELECT min(date)::text, max(date)::text FROM raw.crimes"
        )[0]
        print(f"[raw.crimes] ventana real: {min_date} -> {max_date}")

        (dups,) = query(
            cur,
            "SELECT count(*) FROM (SELECT id FROM raw.crimes GROUP BY id HAVING count(*) > 1) d",
        )[0]
        quality: list[tuple[str, int]] = [("[raw.crimes] ids duplicados (violacion PK/UPSERT)", dups)]

        (bad_coords,) = query(
            cur,
            "SELECT count(*) FROM raw.crimes WHERE latitude IS NOT NULL "
            "AND (latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180)",
        )[0]
        quality.append(("[raw.crimes] coordenadas fuera de rango", bad_coords))

        (null_ids,) = query(cur, "SELECT count(*) FROM raw.crimes WHERE id IS NULL")[0]
        quality.append(("[raw.crimes] ids nulos", null_ids))

        rows = query(
            cur,
            "SELECT run_id, workflow_name, status, records_received, records_failed "
            "FROM ops.pipeline_runs ORDER BY run_id DESC LIMIT 5",
        )
        print("[ops.pipeline_runs] ultimos runs:")
        for row in rows:
            print(f"   {row}")

    print("Advertencias (deben ser 0):")
    for label, value in quality:
        print(f"   {label}: {value}")
    ok = all(value == 0 for _, value in quality)
    result = "OK" if ok else "CON ADVERTENCIAS"
    print(f"RESULTADO: {result} - {total} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
