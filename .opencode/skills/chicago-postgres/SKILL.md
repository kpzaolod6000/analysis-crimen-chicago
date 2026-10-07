---
name: chicago-postgres
description: Convenciones de PostgreSQL del proyecto Chicago Crimes (capas raw/staging/warehouse, migrations, modelo dimensional, naming). Usar SIEMPRE que se escriba SQL, una migration, seed o vista para este repo.
---

# Convenciones PostgreSQL — Chicago Crimes

## Capas

```text
raw        → copia fiel de Socrata (solo tipos, sin limpiar) + loaded_at
staging    → limpieza/normalización (tipos correctos, nulos gestionados)
warehouse  → modelo dimensional fact_crime + dim_*
```

Regla: `raw` nunca se modifica después de cargar; la limpieza ocurre en
`staging`; `warehouse` solo se alimenta desde `staging`.

## Ubicación de archivos SQL

```text
database/migrations/   DDL versionado e idempotente (001_raw.sql, 002_staging.sql, ...)
database/seeds/        datos de referencia (community areas, catálogos)
database/views/        vistas analíticas (vw_*)
database/functions/    funciones/procedures
```

## Idempotencia de migrations

```sql
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.crimes (...);
```

## Naming

- Schemas: `raw`, `staging`, `warehouse`.
- Tablas: singular (`fact_crime`, `dim_date`); sin prefijo en raw/staging
  (`raw.crimes`).
- Vistas: `vw_` + significado (`vw_monthly_crimes`).
- Claves: `<entidad>_key` surrogadas en dims; `crime_id` natural (id Socrata)
  como UNIQUE en fact.
- Prefijo `_tmp` para tablas temporales de carga.

## Modelo dimensional (definido en docs/plan.md §6)

- `fact_crime`: crime_id, date_key, crime_type_key, location_key,
  community_area_key, district_key, hour, arrest, domestic, latitude, longitude.
- `dim_date`: date_key, full_date, year, month, month_name, week,
  day_of_week, day_name, is_weekend.
- `dim_crime_type`, `dim_location`, `dim_community_area`, `dim_district`.
- `pipeline_runs` (esquema operacional): run_id, workflow_name, started_at,
  finished_at, status, records_received, records_inserted, records_updated,
  records_failed, error_message.

## Reglas de escritura de SQL

- Transformaciones pesadas en SQL (no en n8n ni pandas).
- Agregaciones analíticas en vistas, no duplicadas en la API.
- Cargas: UPSERT por `id` (`INSERT ... ON CONFLICT (id) DO UPDATE`).
- Siempre `ORDER BY` determinista en queries paginadas de Socrata.
- Tests de cada migration/vista en `python/tests/integration` contra la DB
  de pruebas (puerto 5433), con fixtures de conteos esperados.

## Conexiones

- Desarrollo: `postgresql://postgres:<pass>@localhost:5432/chicago_crimes`
  (credenciales en `.env`, nunca commiteadas).
- Tests: mismo esquema de nombres pero puerto 5433, esquema efímero.
