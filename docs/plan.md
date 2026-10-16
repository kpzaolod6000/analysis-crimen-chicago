# Plan Maestro — Chicago Crimes Analytics Platform

> **Socrata → n8n → PostgreSQL → Python/ML → FastAPI → D3.js → Power Automate**

Este documento es la fuente de verdad del proyecto. Cada sprint se marca como
`[x]` al completarse, y cada cambio de código se documenta en
[docs/changelog.md](changelog.md).

---

## 1. Objetivo

Construir un sistema end-to-end (no un notebook) que:

- Ingiera automáticamente datos del Chicago Data Portal (Socrata API, dataset
  `ijzp-q8t2`, ~8.6M filas / 22 columnas).
- Los almacene en PostgreSQL en capas: `raw → staging → warehouse` (modelo
  dimensional fact/dim).
- Genere métricas analíticas con SQL (window functions, CTE, rankings).
- Ejecute EDA y modelos (DBSCAN, predicción de hotspots) con Python.
- Exponga los resultados vía REST API (FastAPI).
- Los visualice en un dashboard interactivo (D3.js).
- Distribuya un reporte semanal a stakeholders (Power Automate → Email/Teams).

## 2. Reglas de trabajo (importante)

1. **Cambios pequeños e incrementales.** Cada cambio se hace en un paso
   revisable: el usuario revisa el código antes de continuar.
2. **Cada cambio se documenta** en `docs/changelog.md` (qué, por qué, archivos
   tocados, cómo verificarlo).
3. **Tests primero o junto con el código.** Nada se considera "hecho" sin sus
   tests (ver [docs/testing.md](testing.md)).
4. **No se avanza de sprint sin cerrar el anterior** (código + tests + docs).
5. Durante desarrollo se trabaja con **ventanas de datos pequeñas**
   (1 mes → 3 meses → 1 año → histórico completo).
6. **Ramas Git (modelo de nvie/GitFlow):** trabajo diario en `feature/*`
   desde `develop`; merges siempre `--no-ff`; sprints liberados vía
   `release-<versión>` → `main` + tag `vX.Y.Z`; fixes urgentes vía
   `hotfix-<versión>`. Ver [docs/git-workflow.md](git-workflow.md).

## 3. Decisiones técnicas

| Capa         | Tecnología                     | Justificación |
|--------------|--------------------------------|---------------|
| Ingesta/Orquestación | n8n (Docker)          | Orquestador visual: schedule, HTTP, retry, error flows. Las transformaciones pesadas quedan en Postgres. |
| Base de datos| PostgreSQL 16 (Docker)         | Capas raw/staging/warehouse + SQL analítico. |
| Backend/ML   | Python 3.12 (fijada en venv)   | EDA, features, DBSCAN, predicción. El host trae 3.14, pero pandas/sklearn pueden no tener wheels aún. |
| API          | FastAPI                        | Endpoints REST + OpenAPI docs automáticos. |
| Frontend     | D3.js (vanilla JS, Vite)       | Dashboard interactivo sin framework pesado. |
| E2E          | Playwright                     | Tests end-to-end del dashboard. |
| Tests        | pytest (+ httpx, testcontainers opcional) | Unit + integration para Python/API/SQL. |
| Negocio      | Power Automate                 | Reporte semanal Email/Teams consumiendo `/api/reports/weekly`. |

## 4. Arquitectura

```text
┌──────────────────────┐
│ Chicago Data Portal  │  Socrata API (SoQL, paginación)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│         n8n          │  Schedule → HTTP → Validate → Batch → Load → SQL → Log
└──────────┬───────────┘
           ▼
┌─────────────────────────────────────────────┐
│ PostgreSQL                                  │
│  raw.crimes → staging → dims + fact_crime   │
│  + analytical views + pipeline_runs         │
└───────┬─────────────────────────┬───────────┘
        ▼                         ▼
┌───────────────┐         ┌───────────────┐
│ Python EDA/ML│         │    FastAPI     │
│ DBSCAN, pred. │         │ /crimes/*     │
│ → resultados  │         │ /reports/*    │
│ → PostgreSQL  │         └───────┬───────┘
└───────────────┘                 ▼
                          ┌───────────────┐
                          │  D3 Dashboard │ ← Playwright E2E aquí
                          └───────┬───────┘
                                  ▼
                          ┌─────────────────┐
                          │ Power Automate  │  weekly report → Email/Teams
                          └─────────────────┘
```

Principio clave: **n8n orquesta, PostgreSQL transforma**. n8n no debe hacer
transformaciones pesadas.

## 5. Estructura del repositorio

```text
crimen-chicago/
├── docker/                  # Dockerfiles adicionales
├── n8n/workflows/           # exports JSON de workflows n8n
├── database/
│   ├── migrations/          # DDL versionado (raw, staging, warehouse)
│   ├── seeds/               # datos de prueba (community areas, etc.)
│   ├── views/               # vistas analíticas
│   └── functions/           # funciones/procedures SQL
├── python/
│   ├── notebooks/           # EDA (01_data_quality ... 05_hotspot_model)
│   ├── src/
│   │   ├── ingestion/       # helpers Socrata (paginación, validación)
│   │   ├── analysis/
│   │   ├── features/
│   │   └── models/
│   └── tests/               # unit + integration (pytest)
├── api/
│   ├── app/
│   │   ├── routers/         # /crimes, /reports
│   │   ├── services/
│   │   ├── schemas/         # Pydantic
│   │   └── db/
│   └── tests/               # unit + integration API (pytest + httpx)
├── dashboard/
│   ├── e2e/                 # ★ Playwright (tests end-to-end)
│   ├── src/                 # map.js, trends.js, filters.js, api.js
│   └── assets/
├── docs/                    # plan, testing, changelog, harness, dev-env...
├── .github/workflows/       # CI (GitHub Actions) — Sprint 1
├── .opencode/               # harness: agent/ + skills/
├── .vscode/                 # extensiones recomendadas
├── opencode.json            # config de servidores MCP
├── .editorconfig
├── .gitignore
├── .nvmrc                   # versión de Node fijada (22 LTS)
├── .env.example
├── docker-compose.yml
├── docker-compose.test.yml    # DB de pruebas (puerto 5433) — Sprint 1
├── Makefile                   # atajos: up/down/migrate/tests — Sprint 1
├── AGENTS.md
└── README.md
```

## 6. Modelo de datos (resumen)

**Raw** (`raw.crimes`): copia fiel de Socrata + `loaded_at`, `source_updated_at`.

**Warehouse** (dimensional):

- `fact_crime`: crime_id, date_key, crime_type_key, location_key,
  community_area_key, district_key, hour, arrest, domestic, lat, lon.
- `dim_date` (date_key, full_date, year, month, week, day_name, is_weekend...)
- `dim_crime_type`, `dim_location`, `dim_community_area`, `dim_district`.

**Operacional**: `pipeline_runs` (run_id, workflow_name, started_at, status,
records_received/inserted/updated/failed, error_message).

**Vistas**: `vw_monthly_crimes`, `vw_area_crime_ranking` (RANK),
`vw_month_over_month` (LAG), `vw_day_hour` (heatmap), `vw_area_summary`.

## 7. Estrategia de ingesta

- **Modo A — Backfill**: por ventanas año/mes (Socrata degrada con OFFSET
  profundo; siempre filtrar por rango de fechas + ORDER BY id).
- **Modo B — Incremental**: semanal, ventana solapada de ~14–30 días con
  UPSERT por `id` (los datos son preliminares: se retrasan 7 días y pueden
  corregirse después).
- Validaciones: id NOT NULL/UNIQUE, date NOT NULL, lat ∈ [-90,90],
  lon ∈ [-180,180], community_area válida.

## 8. Reglas de ML

- **Split temporal, nunca aleatorio** para el modelo principal
  (train ≤ 2024, validation/test en 2025+).
- Nivel 1: DBSCAN sobre lat/lon → clusters + ruido.
- Nivel 2: features por `community_area + semana` (lags 1/2/4/8 semanas, mismo
  semana año anterior) → RandomForest/HistGradientBoosting →
  objetivo `crime_count_next_week` o binario `hotspot_next_week`.

## 9. Sprints

Cada sprint incluye sus tests (ver [docs/testing.md](testing.md)).

### Sprint 0 — Plan y convenciones `[x]`
- [x] docs/plan.md (este archivo)
- [x] docs/testing.md (estrategia de tests + ruta Playwright)
- [x] docs/changelog.md (convención de documentación de cambios)
- [x] AGENTS.md + README.md
- Resultado: plan aprobado y reglas de trabajo claras.

### Sprint 0.5 — Harness de desarrollo `[x]`
- [x] `opencode.json` con MCPs (Context7, Playwright activos; Postgres MCP
      Pro preparado, disabled hasta Sprint 1)
- [x] Agentes `@architect`, `@data-engineer`, `@qa` (el resto se crea en su sprint)
- [x] Skills `chicago-postgres`, `chicago-data-ingestion`, `chicago-data-quality`
- [x] `docs/harness.md` — qué hace cada pieza, links y uso por sprint
- [x] `docs/harness-install.md` — manifiesto portable de instalación en otro host
- Resultado: harness documentado; pendiente instalar Node.js LTS (prerrequisito).
- Ver [docs/harness.md](harness.md).

### Sprint 0.7 — Git, licencia y Python 3.12 `[ ]`
- [x] `LICENSE` (MIT) — **reemplazar `[Tu Nombre]`** por el titular real
- [x] Decisión: **git empieza ya** (antes del Sprint 1); momento y comandos en
      `docs/dev-environment.md` §8
- [x] Decisión: venv con **Python 3.12** (el host trae 3.14; pueden faltar
      wheels de pandas/sklearn) — ver `docs/dev-environment.md` §4
- [ ] **(acción del usuario)** instalar Python 3.12, `git init` + primer commit
      + remote de GitHub
- Resultado: repo versionado desde el planning; base lista para el CI (Sprint 1).

### Sprint 1 — Fundaciones `[x]`
- [x] `docker-compose.yml` (PostgreSQL 16 + n8n), `.env.example`
- [x] `docker-compose.test.yml` (PostgreSQL de pruebas en puerto 5433)
- [x] `Makefile` (atajos: `up`, `down`, `migrate`, `test-unit`, `test-integration`, `lint`)
- [x] `database/migrations/001_raw.sql` (schemas raw/staging/warehouse + raw.crimes)
- [x] Tests de integración: esquemas y tablas existen, tipos correctos
- [x] CI básico con GitHub Actions (`.github/workflows/ci.yml`: ruff + pytest, usando `make`)
- Resultado: `make up` → Postgres + n8n funcionando.

### Sprint 2 — Ingesta (MVP del pipeline) `[x]`
- [x] Helper Python opcional para explorar Socrata / construir queries SoQL
- [x] Workflow n8n: HTTP Socrata → Validate → Batch → raw.crimes (trigger
      manual en dev; el Schedule semanal llega con el incremental, Sprint 10)
- [x] Cargar 1 mes de datos → luego 1 año (bucle por ventanas mensuales)
- [x] Tests de calidad de datos (unicidad, rangos, nulos)
- Resultado: **Socrata → n8n → raw.crimes automático** (primera meta real).

### Sprint 3 — Data Warehouse `[ ]`
- [ ] `003_staging.sql` (limpieza/tipos), `004_dims_fact.sql`
      (la numeración `002` la ocupa `002_operational.sql` del Sprint 2)
- [ ] Seed: community areas (77) del dataset tabular `igwz-8jzy`
      (`cauq-8yn6`, el de la ref. original, es solo su vista de mapa)
- [ ] Tests de integración: integridad referencial fact↔dims, conteos
- Resultado: modelo dimensional poblado desde raw.

### Sprint 4 — SQL Analytics `[ ]`
- [ ] Vistas: `vw_monthly_crimes`, `vw_area_crime_ranking`,
      `vw_month_over_month`, `vw_day_hour`, `vw_area_summary`
- [ ] Tests: resultados de vistas contra fixtures conocidos
- Resultado: SQL analítico con window functions verificado.

### Sprint 5 — Python EDA + ML Nivel 1 `[ ]`
- [ ] Notebooks 01–05 (data quality → hotspots)
- [ ] `src/features/` (features semanales con lags) + tests unit
- [ ] DBSCAN → clusters → guardar en PostgreSQL
- Resultado: hotspots observados calculados y almacenados.

### Sprint 6 — FastAPI `[ ]`
- [ ] Endpoints: `/api/crimes/summary|trends|by-type|by-community-area|hotspots`
- [ ] **`/api/reports/weekly`** (para Power Automate)
- [ ] Tests de integración con TestClient + DB de prueba
- Resultado: API funcional con OpenAPI docs.

### Sprint 7 — D3 Dashboard `[ ]`
- [ ] KPI cards, line chart (hover/zoom/brush), heatmap día×hora
- [ ] Mapa coroplético por community area + filtros (tipo, año, mes, área)
- [ ] Panel hotspots (observado vs predicho)
- Resultado: dashboard completo consumiendo FastAPI.

### Sprint 8 — Playwright E2E `[ ]`
- [ ] Configurar Playwright + aprender con ejercicios guiados (ver testing.md)
- [ ] Tests E2E del dashboard: carga, filtros, tooltips, mapa, KPIs
- Resultado: suite E2E estable en CI.

### Sprint 9 — Power Automate `[ ]`
- [ ] Flujo: Monday 08:00 → GET /api/reports/weekly → Parse JSON →
      HTML → Email + Teams
- [ ] Documentar el flujo con capturas en docs/
- Resultado: reporte semanal automatizado.

### Sprint 10 — ML Nivel 2 + Backfill + Producción `[ ]`
- [ ] Predicción de hotspots (split temporal, evaluación, storage)
- [ ] Endpoint `/api/crimes/predictions` + panel en dashboard
- [ ] Backfill 2001→2026 por ventanas + incremental semanal configurado
- [ ] Workflow n8n de errores (Error Trigger → log → notificación)
- Resultado: sistema completo en "producción".

## 10. MVP (definición de "el proyecto funciona")

```text
Socrata → n8n → PostgreSQL → SQL views → FastAPI → D3
```
con 1 año de datos, tendencias mensuales, tipos, community areas, filtros y
mapa. DBSCAN, predicciones y Power Automate vienen **después**.

## 11. Fuera de alcance (v2)

Kafka, Airflow, Spark, Kubernetes, Redis, microservicios, vector DB, LLMs.
La complejidad correcta ya está en el stack elegido.

## 12. Datos fuente

- Crímenes 2001–presente: https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2
- Boundaries - Community Areas (tabular, 77): https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/igwz-8jzy
  (la ref. original `cauq-8yn6` es solo su vista de mapa; campo número: `area_numbe`, nombre: `community`)
- Socrata docs (SoQL, paginación): https://dev.socrata.com/docs/
