# Verificación por sprint y paso — checklist de pruebas + git

**Propósito:** cada paso revisable del plan deja aquí sus comandos de
verificación (contenido/tests) y sus comandos git. Se llena ANTES de dar el
paso por terminado (regla de `AGENTS.md`); es el complemento accionable del
registro histórico de `docs/changelog.md` y de la estrategia de
[docs/testing.md](testing.md).

## Cómo se usa

1. Al cerrar un paso, el asistente agrega una sub-sección con: objetos
   revisables, verificación (tests/lint/manual) y git (add/commit/push).
2. Vos corrés todo, marcanos `[x]` (o avisanos y lo marcamos). Un paso solo
   está cerrado cuando su checklist está en verde **y quedó commiteado**.

---

## Sprint 1 — Fundaciones (cerrado, tag `v0.1.0`)

- **Objetos:** `docker-compose.yml` + `.env(*.example)`,
  `database/migrations/001_raw.sql`, `python/tests/integration/`,
  `Makefile`, `python/requirements(.dev)?.txt`, `.github/workflows/ci.yml`,
  `docker-compose.test.yml`.
- **Verificar:**
  - `docker compose up -d` → postgres `healthy` + n8n
  - `docker compose exec -T postgres psql -U postgres -d chicago_crimes
    -f /database/migrations/001_raw.sql` → CREATE (solo NOTICE si ya aplica)
  - `docker compose -f docker-compose.test.yml up -d`
  - `pytest python/tests/integration -v` → 8 passed
  - `ruff check python` → passed
- **Git:** commits individuales `feat:`/`chore:` en `main`; release con
  `release-*`→ no aplicó (pre-GitFlow); el release quedó como tag
  `v0.1.0` anotado en `main` + push `origin main v0.1.0`.

---

## Sprint 2 — Ingesta

### Paso 1 — Helper Socrata/SoQL `[x]`

- **Objetos revisables:**
  - `python/src/ingestion/socrata.py` — helper (build_params,
    date_window_where, fetch_page, paginate)
  - `python/src/ingestion/__init__.py` — paquete
  - `python/tests/unit/conftest.py` — bootstrap sys.path
  - `python/tests/unit/test_socrata.py` — 17 tests
- **Verificar contenido:**
  - `pytest python/tests/unit -v` → 17 passed
  - `pytest python/tests -q` → 25 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Git:**
  ```powershell
  git status --short                       # ~6 archivos ?? / M en python/ y docs
  git add python/ docs/changelog.md docs/verification.md
  git commit -m "feat: add socrata soql helper with unit tests"
  git push -u origin feature/sprint2-socrata-helper
  # integración con red: merge --no-ff a develop + borrar rama (§4 git-workflow.md)
  ```

### Paso 2 — Workflow n8n → raw.crimes `[x]` (pendiente de run manual tuyo)

- **Objetos revisables:**
  - `database/migrations/002_operational.sql` — schema `ops` + `ops.pipeline_runs`
  - `python/tests/integration/test_operational_schema.py` — 6 tests
  - `n8n/workflows/sprint2-socrata-raw.json` — workflow exportable
    (Trigger → Ventana → HTTP Socrata → Validar → SQL payload →
    upsert bulk en raw.crimes → log en pipeline_runs)
- **Verificar contenido (hecho por el asistente):**
  - `pytest python/tests -q` → 31 passed · `ruff check python` → passed
  - JSON del workflow parsea (7 nodos, 6 conexiones)
  - `002_operational.sql` aplicado en dev (`psql -f`, CREATE x3)
- **Verificar en n8n (lo haces vos, ~5 min):**
  > Fix 1 aplicado (2026-10-10): si importaste el JSON ANTES de este fix,
  > corregir en la GUI: (1) nodo "SQL payload..." → pegar el jsCode nuevo
  > (genera `payloadSql` con comillas+escape); (2) nodo "raw.crimes upsert
  > (bulk)" → línea `FROM jsonb_to_recordset(...)` usar
  > `{{ $json.payloadSql }}`. O re-importar el JSON actualizado.
  1. Importar: http://localhost:5673 → menu ⋯ → *Import from File* →
     `n8n/workflows/sprint2-socrata-raw.json`. Si un nodo pide completar
     config al abrir, revisar que los parámetros coincidan con el JSON.
  2. Crear credencial (1a vez): en los 2 nodos Postgres → *Create new
     credential* con **host `postgres`** (red docker), port `5432`,
     DB `chicago_crimes`, user/pass del `.env`. Nombrarla
     `chicago-postgres (docker)` y asignarla a ambos nodos.
  3. Ejecutar el workflow (botón *Execute workflow*). Ventana dev:
     2026-09-01 → 2026-10-01 (~20k registros, 1 request, 1-2 min).
  4. Chequear resultados en DB:
     ```powershell
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM raw.crimes;"
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT min(date), max(date) FROM raw.crimes;"
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT run_id, status, records_received, records_failed FROM ops.pipeline_runs ORDER BY run_id DESC LIMIT 3;"
     ```
  5. Re-run del workflow → `count(*)` NO cambia (UPSERT por `id`) y aparece
     un segundo `run_id` en `pipeline_runs`.
  6. **Smoke test automático** (verifica todo lo anterior + calidad mínima):
     ```powershell
     .\.venv\Scripts\python.exe python/scripts/check_raw_load.py
     ```
     Esperado: filas ≈ window (excluye parcial), ventana sept-2026 completa,
     run SUCCESS/PARTIAL en pipeline_runs, advertencias todas en 0.
- ✅ **Verificado el 2026-10-10:** carga SUCCESS, 19.642 filas (19642
  recibidas, 0 fallidas), 0 duplicados, 0 coords inválidas, 0 ids nulos.
- **Git:**
  ```powershell
  git add database/ python/tests/integration/test_operational_schema.py n8n/ docs/
  git commit -m "feat: socrata-to-raw n8n workflow with pipeline_runs logging"
  git push
  ```

### Paso 3 — Ventana 1 año (bucle mensual) `[ ]` (pendiente de run manual tuyo)

- **Objetos revisables:**
  - `n8n/workflows/sprint2-socrata-raw.json` — reescrito: `Set ventana →
    Meses de la ventana (Code) → Loop Over Items (batch 1) → Socrata: fetch
    mes → Validar + SQL payload (mes) → upsert → log por mes →` retorno al loop
  - `python/src/ingestion/socrata.py` — `month_windows()` (réplica testeable
    del algoritmo del nodo "Meses de la ventana"; mantener ambas en sync)
  - `python/tests/unit/test_socrata.py` — 6 tests nuevos (TestMonthWindows)
  - `python/tests/unit/test_n8n_workflow.py` — 11 tests estructurales (nuevo)
- **Verificar contenido:**
  - `pytest python/tests/unit -v` → 34 passed (17 previos + 6 + 11)
  - `pytest python/tests -q` → 48 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Verificar en n8n (lo haces vos):**
  1. **Borrar** el workflow importado en el Paso 2 (evita duplicados) e
     importar `n8n/workflows/sprint2-socrata-raw.json` (menu ⋯ → *Import
     from File*). Reasignar la credencial `chicago-postgres (docker)` en los
     2 nodos Postgres.
  2. **Smoke del bucle (recomendado, ~5 min):** en "Ventana dev (1 año)"
     cambiar `windowStart` a `2026-06-01T00:00:00` (windowEnd queda
     `2026-10-01T00:00:00`) y ejecutar. Esperado: 4 iteraciones (jun→sep),
     4 filas nuevas en `ops.pipeline_runs` (sep ya existía: UPSERT no duplica).
     ```powershell
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT window_start, status, records_received, records_failed, error_message FROM ops.pipeline_runs ORDER BY run_id DESC LIMIT 6;"
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM raw.crimes;"
     ```
  3. **Run completo 1 año (~15-30 min):** restaurar `windowStart` a
     `2025-10-01T00:00:00` y ejecutar. Esperado: 12 filas nuevas en
     `pipeline_runs` (una por mes, status SUCCESS/PARTIAL, `error_message`
     NULL), `min(date)>=2025-10-01` y `max(date)<2026-10-01` en raw.crimes.
     ```powershell
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT min(date), max(date), count(*) FROM raw.crimes;"
     docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) AS runs, sum(records_received) AS recibidos, sum(records_failed) AS fallidos FROM ops.pipeline_runs WHERE window_start >= '2025-10-01';"
     ```
  4. **Idempotencia:** re-ejecutar el workflow completo → `count(*)` de
     raw.crimes NO cambia (UPSERT por `id`); aparecen 12 `run_id` nuevos.
  5. **Smoke automático:** `.\.venv\Scripts\python.exe python/scripts/check_raw_load.py`
     → filas ≈ ventana anual, advertencias en 0.
- **Riesgos conocidos (si el run falla, revisar esto):**
  - `$('Loop Over Items').item` en "Validar + SQL payload (mes)": es la vía
    documentada para leer el item actual del bucle. Si n8n lanza error de
    expresión ahí, abrir el nodo y revisar que el nombre del nodo de bucle
    sea exactamente `Loop Over Items`.
  - Si un mes devolviera 0 registros, la cadena se detiene en silencio
    (n8n no ejecuta nodos sin input). No ocurre en este dataset (meses
    siempre con datos); se detectaría porque faltan filas en pipeline_runs.
  - Guard de truncamiento: ningún mes histórico supera ~45k registros
    (< pageSize 50000). Si un mes quedara `FAILED` con ese mensaje, avisar:
    requeriría paginación interna (prevista para Sprint 10).
- **Git:**
  ```powershell
  git switch -c feature/sprint2-year-window develop
  git add python/ n8n/ docs/
  git commit -m "feat: add monthly loop to n8n workflow for 1-year window"
  git push -u origin feature/sprint2-year-window
  # tras CI verde: merge --no-ff a develop (§4 git-workflow.md)
  ```

### Paso 4 — Data tests de calidad (unicidad, rangos, nulos) `[ ]` (pendiente de tu verificación)

- **Objetos revisables:**
  - `python/src/ingestion/quality.py` — métricas de calidad (nuevo; única
    fuente de verdad compartida por tests y smoke script)
  - `python/tests/integration/test_data_quality.py` — 12 tests sobre 12
    filas fixture sembradas (nuevo)
  - `python/tests/unit/test_quality.py` — 3 tests unit con cursor falso (nuevo)
  - `python/tests/integration/conftest.py` — bootstrap sys.path a `python/src`
  - `python/scripts/check_raw_load.py` — refactor: consume `quality.py`
    (salida idéntica; variable local `quality` renombrada a `warnings`)
- **Verificar contenido:**
  - `docker compose -f docker-compose.test.yml up -d` (si no está levantada)
  - `pytest python/tests/unit -v` → 37 passed
  - `pytest python/tests -q` → 63 passed (unit + integration)
  - `ruff check python` → All checks passed
  - Smoke sin cambios de comportamiento (contra dev, con datos del Paso 3):
    `.\.venv\Scripts\python.exe python/scripts/check_raw_load.py` → misma
    salida de siempre (3 advertencias en 0)
- **Fixture sembrado (esperado calculado a mano):** 12 filas `DQ-01..12` →
  date nulo=1, lat/lon nulos=1, community_area nulos=2, primary_type nulos=0
  (vacío≠NULL), coords fuera de rango=1, coords (0,0)=1, community_area
  inválida=1, primary_type vacío=1, duplicados=0, ids nulos=0.
- **Cierre del Sprint 2 (tras verificar este paso):**
  1. Confirmar que el Paso 3 quedó verificado (12 runs SUCCESS del año).
  2. Avisar al asistente → marca Sprint 2 `[x]` en `docs/plan.md` y
     actualiza el estado del README.
  3. Git (lo haces vos):
     ```powershell
     git switch -c feature/sprint2-data-tests develop
     git add python/ docs/
     git commit -m "feat: add data quality metrics and integration data tests"
     git push -u origin feature/sprint2-data-tests
     # tras CI verde: merge --no-ff a develop; luego release según
     # git-workflow.md §9: rama release-0.2.0 → main + tag v0.2.0 → back-merge a develop
     ```

## Hotfix 0.2.1 — RUF100 (noqa sin usar) en check_raw_load.py

- **Objetos revisables:**
  - `python/scripts/check_raw_load.py` — se elimina el comentario
    `# noqa: E402` (única directiva noqa del repo). E402 no está activado en
    los defaults de ruff (no hay `ruff.toml`/`pyproject.toml`), así que la
    directiva era "unused" y RUF100 la reportaba: CI de `v0.2.0` rojo en lint.
- **Verificar contenido:**
  - `ruff check python` → All checks passed (local Y en CI tras el push)
  - Suite pytest sin cambios (el script pierde solo un comentario)
- **Git:**
  ```powershell
  git switch -c hotfix-0.2.1 main
  git add python/scripts/check_raw_load.py docs/changelog.md docs/verification.md
  git commit -m "fix: remove unused noqa directive (RUF100) in check_raw_load"
  git switch main
  git merge --no-ff hotfix-0.2.1
  git tag -a v0.2.1 -m "hotfix: RUF100 lint in check_raw_load"
  git switch develop
  git merge --no-ff hotfix-0.2.1
  git branch -d hotfix-0.2.1
  git push origin main develop --tags
  ```
- **Limpieza opcional (ramas ya fusionadas que quedaron):**
  ```powershell
  git branch -d release-0.2.0 feature/sprint2-paso3-year-loop feature/sprint2-socrata-helper
  git push origin --delete feature/sprint2-paso3-year-loop
  ```
- **Mejora propuesta (para otro cambio, no este hotfix):** fijar la versión
  de ruff en `requirements-dev.txt` (ej. `ruff==0.x.y` — consultar
  `ruff --version` del CI) para que local y CI linteen igual; el drift de
  versión es por qué tu local no reportó RUF100 y el CI sí.

## Docs — Cheat sheet de git + sección GitHub Actions (git-workflow.md)

- **Objetos revisables:**
  - `docs/git-workflow.md` — §8 ampliado (triggers de ci.yml, pasos del job,
    servicio Postgres de GitHub, drift de ruff) + §10 nuevo: cheat sheet con
    comandos por escenario (empezar paso, guardar avance, terminar paso,
    release, hotfix, decisión de rama, CI rojo, inspección).
- **Verificar contenido:**
  - Leer §10 y comparar con los flujos realmente ejecutados en Sprint 2 y
    el hotfix 0.2.1 (deben coincidir).
- **Git:**
  ```powershell
  git switch -c feature/docs-git-cheatsheet develop
  git add docs/
  git commit -m "docs: add git cheat sheet and CI workflow reference"
  git push -u origin feature/docs-git-cheatsheet
  git switch develop
  git merge --no-ff feature/docs-git-cheatsheet
  git branch -d feature/docs-git-cheatsheet
  git push origin develop
  ```

## Docs — checklist pre-merge en §10.3 (git-workflow.md)

- **Objetos revisables:**
  - `docs/git-workflow.md` — §10.3: checklist "está verde" antes del merge
    (CI en Actions + checklist del paso en este archivo).
- **Verificar contenido:**
  - Leer §10.3: coincide con lo ejecutado al cerrar `feature/sprint3-staging`.
- **Git:**
  ```powershell
  git switch -c feature/docs-premerge-check develop
  git add docs/
  git commit -m "docs: add pre-merge green checklist to git cheat sheet"
  git push -u origin feature/docs-premerge-check
  git switch develop
  git merge --no-ff feature/docs-premerge-check
  git branch -d feature/docs-premerge-check
  git push origin develop
  ```

## Sprint 3 — Data Warehouse

### Paso 1 — Migración 003_staging (view de limpieza) `[ ]` (pendiente de tu verificación)

- **Objetos revisables:**
  - `database/migrations/003_staging.sql` — `staging.crimes` como VIEW sobre
    `raw.crimes`: btrim/''→NULL en texto, coords (0,0) y fuera de rango
    →NULL (ambas), parciales se conservan, `community_area` solo 1–77.
  - `python/tests/integration/test_staging_schema.py` — 11 tests (nuevo)
  - `docs/plan.md` — numeración corregida (002 ya ocupado por operational)
- **Verificar contenido:**
  - `docker compose -f docker-compose.test.yml up -d` (si no está levantada)
  - `pytest python/tests/integration -v` → 37 passed (26 + 11)
  - `pytest python/tests -q` → 74 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Verificar en dev (con los datos reales del año cargado):**
  ```powershell
  docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/migrations/003_staging.sql
  # → CREATE VIEW (idempotente si se re-ejecuta)
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM staging.crimes;"
  # → igual al count de raw.crimes
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM staging.crimes WHERE latitude = 0 AND longitude = 0;"
  # → 0 (los (0,0) quedaron NULL; comparar con raw.crimes que los tiene)
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM raw.crimes WHERE community_area NOT BETWEEN 1 AND 77;"
  # → los que sean >0 en raw, en staging son NULL
  ```
- **Git:**
  ```powershell
  git switch -c feature/sprint3-staging develop
  git add database/ python/ docs/
  git commit -m "feat: staging view over raw.crimes with cleaning rules"
  git push -u origin feature/sprint3-staging
  # tras CI verde: merge --no-ff a develop
  ```

### Paso 2 — Migración 004_dims_fact (modelo dimensional) `[ ]` (pendiente de tu verificación)

- **Objetos revisables:**
  - `database/migrations/004_dims_fact.sql` — `warehouse.dim_date`,
    `dim_crime_type`, `dim_location`, `dim_district`, `dim_community_area` +
    `fact_crime` (FKs, UNIQUE naturales NULLS NOT DISTINCT, 3 índices)
  - `python/tests/integration/test_dims_fact_schema.py` — 10 tests (nuevo)
- **Verificar contenido:**
  - `docker compose -f docker-compose.test.yml up -d` (si no está levantada)
  - `pytest python/tests/integration -v` → 47 passed (37 + 10)
  - `pytest python/tests -q` → 84 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Verificar en dev:**
  ```powershell
  docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/migrations/004_dims_fact.sql
  # → CREATE SCHEMA/TABLE/INDEX (idempotente si se re-ejecuta)
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "\dt warehouse.*"
  # → 6 tablas: 5 dims + fact_crime (todas vacías: la carga es el Paso 4)
  ```
- **Git:**
  ```powershell
  git switch -c feature/sprint3-dims-fact develop
  git add database/ python/ docs/
  git commit -m "feat: dimensional model (dims + fact_crime) with constraints"
  git push -u origin feature/sprint3-dims-fact
  # checklist pre-merge de git-workflow.md §10.3 y luego merge --no-ff a develop
  ```

### Paso 3 — Seed community areas (77) `[ ]` (pendiente de tu verificación)

- **Objetos revisables:**
  - `database/seeds/community_areas.sql` — 77 filas, UPSERT idempotente;
    fuente = dataset tabular `igwz-8jzy` (extracto 2026-10-14 via API)
  - `Makefile` — target `seed` nuevo (loop sobre `database/seeds/*.sql`)
  - `python/tests/integration/test_community_areas_seed.py` — 6 tests (nuevo)
  - `docs/plan.md` — ref. del dataset corregida (`igwz-8jzy`, `cauq-8yn6`
    solo es su vista de mapa)
- **Verificar contenido:**
  - `docker compose -f docker-compose.test.yml up -d` (si no está levantada)
  - `pytest python/tests/integration -v` → 53 passed (47 + 6)
  - `pytest python/tests -q` → 90 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Verificar en dev:**
  ```powershell
  make seed    # o: docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/seeds/community_areas.sql
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM warehouse.dim_community_area;"
  # → 77
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT community_area, community_area_name FROM warehouse.dim_community_area WHERE community_area IN (22, 41, 76);"
  # → 22 Logan Square · 41 Hyde Park · 76 O'Hare
  ```
- **Git:**
  ```powershell
  git switch -c feature/sprint3-seed-areas develop
  git add database/ python/ Makefile docs/
  git commit -m "feat: seed 77 community areas from official dataset"
  git push -u origin feature/sprint3-seed-areas
  # CI verde → merge --no-ff a develop (checklist §10.3)
  ```

### Fix — Contrato staging ''→NULL + F401 del seed `[ ]`

- **Qué pasó:** el CI del seed (runs 20-21) falló en "Lint (ruff)" (F401:
  `Path` sin usar en `test_community_areas_seed.py`) y los tests quedaron
  SKIPPED. Además, releer `003_staging.sql` para el Paso 4 destapó que el
  contrato documentado ("btrim + ''→NULL") no estaba implementado, y el test
  `test_empty_string_becomes_null` codificaba el bug (`== ""` en vez de
  `is None`).
- **Objetos revisables:**
  - `database/migrations/003_staging.sql` — 7 campos de texto con
    `nullif(btrim(col), '')`
  - `python/tests/integration/test_staging_schema.py` — aserción `is None`
  - `python/tests/integration/test_community_areas_seed.py` — import `Path`
    eliminado
- **Verificar contenido:**
  - `pytest python/tests -q` → 90 passed (37 unit + 53 integration)
  - `ruff check python` → All checks passed
- **Verificar en dev (re-aplicar la view corregida):**
  ```powershell
  docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/migrations/003_staging.sql
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM staging.crimes WHERE primary_type = '';"
  # → 0 (los '' y solo-espacios pasaron a NULL)
  ```
- **Lección (regla de oro):** el checklist pre-merge §10.3 incluye CI en
  Actions — no merge con run rojo, ni aunque el push local haya estado verde.
- **Git:**
  ```powershell
  git switch -c fix/staging-contract develop
  git add database/ python/ docs/
  git commit -m "fix: nullify empty strings in staging view (declared contract)"
  git push -u origin fix/staging-contract
  # CI en verde (¡es el fix que lo devuelve!) → merge --no-ff a develop
  ```

### Paso 4 — Carga staging → warehouse `[x]` (carga ejecutada en dev; falta tu pytest/ruff/sanity final)

- ✅ **Verificado el 2026-10-17 (carga, por el asistente):** funciones
  aplicadas (6× CREATE FUNCTION) y `SELECT warehouse.load_warehouse()`
  ejecutado en dev tras migrar Docker a D: → NOTICEs: dim_date 10.957 ·
  dim_crime_type 254 · dim_location 15.350 · dim_district 24 ·
  fact_crime 19.642 (total 46.227). fact == staging con fecha (19.642).
  Nota: un reinicio de postgres a mitad de la 1ª ejecución hizo rollback
  limpio (todo o nada); la re-ejecución idempotente terminó completa.

- **Objetos revisables:**
  - `database/functions/load_warehouse.sql` — 6 funciones idempotentes
    (calendario, 3 dims, fact con resolución de keys, orquestador)
  - `Makefile` — target `load-warehouse` nuevo
  - `python/tests/integration/test_warehouse_load.py` — 10 tests (nuevo)
- **Verificar contenido:**
  - `pytest python/tests/integration -v` → 63 passed (53 + 10)
  - `pytest python/tests -q` → 100 passed (unit + integration)
  - `ruff check python` → All checks passed
- **Verificar en dev (¡la estrella poblada con tu año real!):**
  ```powershell
  make load-warehouse    # (PowerShell: ver equivalencia abajo)
  ```
  Equivalente PowerShell (make no instalado):
  ```powershell
  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f /database/functions/load_warehouse.sql -c "SELECT warehouse.load_warehouse();"
  ```
  Sanity (los conteos exactos los dan los NOTICEs de la función):
  ```powershell
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT (SELECT count(*) FROM warehouse.fact_crime) AS fact, (SELECT count(*) FROM staging.crimes WHERE date IS NOT NULL) AS esperado;"
  # fact == esperado (solo difieren si raw cambió entre medio)
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT ca.community_area_name, count(*) FROM warehouse.fact_crime f JOIN warehouse.dim_community_area ca ON ca.community_area_key = f.community_area_key GROUP BY 1 ORDER BY 2 DESC LIMIT 5;"
  # → las 5 areas con más crímenes de tu año, con nombres reales
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT warehouse.load_warehouse(); SELECT count(*) FROM warehouse.fact_crime;"
  # re-ejecutar la carga → count no cambia (UPSERT idempotente)
  ```
- **Git:**
  ```powershell
  git switch -c feature/sprint3-load-warehouse develop
  git add database/ python/ Makefile docs/
  git commit -m "feat: load staging into warehouse dims and fact"
  git push -u origin feature/sprint3-load-warehouse
  # CI en Actions verde → merge --no-ff a develop
  ```

---

## Sprint 4 — SQL Analytics

### Paso 1 — Vistas analíticas (analytics.sql) `[x]` (✅ verificado en dev por el usuario, 2026-10-17)

- **Objetos revisables:**
  - `database/views/analytics.sql` — 5 vistas en schema `warehouse`:
    `vw_monthly_crimes` ( + arrests + rate), `vw_area_crime_ranking`
    (RANK + share_pct), `vw_month_over_month` (LAG), `vw_day_hour`,
    `vw_area_summary`
  - `Makefile` — target `views` (loop sobre database/views/*.sql)
  - `python/tests/integration/test_analytics_views.py` — 11 tests con
    fixture de 10 filas raw (V-01..V-10) y resultados a mano
- **Verificar contenido:**
  - `docker compose -f docker-compose.test.yml up -d` (si no está levantada)
  - `pytest python/tests/integration -v` → 74 passed (63 + 11)
  - `pytest python/tests -q` → 111 passed (37 unit + 74 integration)
  - `ruff check python` → All checks passed
- **Verificar en dev (con los 19.642 reales; la estrella del warehouse ya
  está poblada, las vistas se crean encima):**
  ```powershell
  make views     # PowerShell sin make: docker compose exec -T postgres psql -U postgres -d chicago_crimes -f /database/views/analytics.sql
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT * FROM warehouse.vw_monthly_crimes ORDER BY month_date;"
  # → tendencia mensual del año cargado (sept-2026: 19.642, arrests y rate reales)
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT * FROM warehouse.vw_month_over_month;"
  # → primera (única) fila con prev/change NULL
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT * FROM warehouse.vw_area_crime_ranking ORDER BY crime_rank LIMIT 10;"
  # → Logan Square / O'Hare / Hyde Park...
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT * FROM warehouse.vw_day_hour ORDER BY day_of_week, hour LIMIT 20;"
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT * FROM warehouse.vw_area_summary ORDER BY crime_count DESC LIMIT 10;"
  docker compose exec postgres psql -U postgres -d chicago_crimes -c "\dv warehouse.*"
  # → 5 vistas (idempotencia: re-aplicar analytics.sql → CREATE VIEW x5)
  ```
- **Git:**
  ```powershell
  git switch -c feature/sprint4-analytics-views develop
  git add database/ Makefile python/ docs/
  git commit -m "feat: analytical views with window functions"
  git push -u origin feature/sprint4-analytics-views
  # CI en verde (checklist §10.3) → merge --no-ff a develop
  ```
