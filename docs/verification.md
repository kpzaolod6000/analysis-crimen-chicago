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

### Paso 2 — Workflow n8n → raw.crimes `[ ]`
*(checklist se llena al implementar; verificará: workflow JSON exportado en
`n8n/workflows/`, 1 mes de datos en `raw.crimes`, conteos en `pipeline_runs`)*

### Paso 3 — Ventana 1 año `[ ]`
### Paso 4 — Data tests de calidad (unicidad, rangos, nulos) `[ ]`
