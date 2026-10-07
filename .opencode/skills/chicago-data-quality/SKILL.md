---
name: chicago-data-quality
description: Reglas de calidad de datos del proyecto Chicago Crimes (validaciones por campo, métricas de calidad, data tests). Usar al validar datos cargados, escribir data tests o revisar calidad de raw/fact.
---

# Calidad de Datos — Chicago Crimes

## Validaciones por registro (ingesta)

| Campo | Regla | Acción si falla |
|---|---|---|
| `id` | NOT NULL, UNIQUE | rechazar duplicado |
| `date` | NOT NULL, parseable | rechazar |
| `latitude` | BETWEEN -90 AND 90 (o NULL) | marcar inválido |
| `longitude` | BETWEEN -180 AND 180 (o NULL) | marcar inválido |
| `community_area` | valor en catálogo (0–77) o NULL | marcar unknown |
| `primary_type` | no vacío | marcar unknown |

Rechazos se registran (log / `pipeline_runs.records_failed`), nunca rompen
el run completo.

## Métricas de calidad (después de cada carga)

```text
null_rate             por columna clave (date, lat/lon, community_area)
duplicate_rate        ids duplicados vs total
invalid_coordinates   lat/lon fuera de rango
unknown_crime_type    primary_type fuera de catálogo
```

Umbral de ejemplo: alertar si `duplicate_rate > 0` tras UPSERT o
`null_rate(date) > 0`.

## Dónde viven los data tests

- `python/tests/integration/test_data_quality.py` — contra la DB de pruebas
  (puerto 5433) con fixtures semilla y (opcional) contra 1 mes real de datos.
- Unit tests de validadores puros en `python/tests/unit/`.

## Notas del dominio

- Los datos excluyen los últimos 7 días (retraso de publicación).
- Registros preliminares: pueden corregirse después → ventana solapada y
  UPSERT (ver skill `chicago-data-ingestion`).
- Coordenadas 0/0 o fuera de Chicago = inválidas (Socrata a veces emite
  (0,0)); en staging tratarlas como NULL.
- Registros antiguos (~2001–2006) tienen más nulos en lat/lon y
  community_area: no es un bug de ingesta.
