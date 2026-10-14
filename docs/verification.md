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

### Paso 3 — Ventana 1 año `[ ]`
### Paso 4 — Data tests de calidad (unicidad, rangos, nulos) `[ ]`
