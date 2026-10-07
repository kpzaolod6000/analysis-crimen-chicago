---
name: chicago-data-ingestion
description: Convenciones de ingesta Socrata/n8n del proyecto Chicago Crimes (dataset id, SoQL, paginación, ventanas temporales, UPSERT incremental). Usar SIEMPRE que se diseñe o modifique la ingesta de datos, workflows n8n o queries Socrata.
---

# Convenciones de Ingesta — Chicago Crimes

## Fuentes (ids oficiales)

- Crímenes 2001–presente: dataset `ijzp-q8t2`
  https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2
- Community areas (77, geometrías): dataset `cauq-8yn6`
  https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6
- Docs Socrata (SoQL, paginación): https://dev.socrata.com/docs/

## Reglas de queries Socrata

1. **Siempre filtrar por rango de fechas** (nunca OFFSET profundo:
   Socrata degrada con páginas profundas).
   `$where=date >= '2026-01-01T00:00:00' AND date < '2026-02-01T00:00:00'`
2. **ORDER BY id** para paginación determinista.
3. `$$app_token` si se configura (rate limits).
4. Formato JSON por defecto; limit máximo por página según docs vigentes
   (verificar en dev.socrata.com/docs/paging.html).

## Modos de ingesta

- **Backfill**: por ventanas año/mes (`2023-01 → 2023-02`), un ciclo n8n por
  ventana. Empezar en desarrollo con 1 mes → 3 meses → 1 año → histórico.
- **Incremental**: semanal, ventana solapada de **14–30 días**
  (`date > now - 30d`), NO `date > last_run` (los datos son preliminares:
  ~7 días de retraso y correcciones posteriores → UPSERT por `id`).

## Division of labor (no negociable)

- n8n: schedule, HTTP, validación básica, batch, inserción en raw, disparar
  SQL, log en `pipeline_runs`.
- PostgreSQL: todas las transformaciones pesadas (raw → staging → warehouse).

## Validación básica antes de insertar en raw

- `id` presente y no duplicado.
- `date` parseable.
- `latitude`/`longitude` en rango o nulos (Socrata permite nulos).
- Rechazos van a log, no rompen el run completo.

## Log de cada run

Insertar en `pipeline_runs` (ver skill `chicago-postgres`): status
(SUCCESS/PARTIAL/FAILED), records_received/inserted/updated/failed,
error_message.
