# Changelog del proyecto

Registro de **cada cambio** realizado en el código, en orden cronológico
inverso. Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## Formato de cada entrada

```markdown
## [YYYY-MM-DD] Sprint N — Título corto del cambio

**Qué:** descripción en 1–3 líneas de qué se agregó/modificó.
**Por qué:** la razón o decisión de diseño.
**Archivos:**
- `ruta/al/archivo` — qué contiene o qué cambió
**Tests:**
- `ruta/al/test` — qué cubre
**Cómo verificar:**
- comando(s) para reproducir/validar el cambio
```

Reglas:
1. Una entrada por cambio (aunque el cambio toque varios archivos).
2. Se escribe **antes** de dar el cambio por terminado.
3. Si un cambio posterior revierte o modifica uno anterior, se referencia.
4. Los sprints completados se marcan también en [plan.md](plan.md).

---

## [2026-10-10] Sprint 2 · Paso 2 (cierre) — Smoke test de carga + primer run SUCCESS

**Qué:** (a) script smoke `python/scripts/check_raw_load.py` que contra dev
(5432) reporta filas totales de raw.crimes, ventana real de fechas, últimos
runs de ops.pipeline_runs y advertencias de calidad (duplicados por id,
coords fuera de rango, ids nulos). (b) El usuario re-importó/corrigió los
nodos en n8n tras el Fix 1 y ejecutó el primer run real: raw.crimes quedó
con 19.642 filas (ventana 2026-09), run SUCCESS recibidas=19642/fallidas=0.
**Por qué:** docs/testing.md §2.4 prevé un smoke script que compruebe la
fila de log del run; automatiza la verificación post-load sin SQL manual.
**Archivos:**
- `python/scripts/check_raw_load.py` — smoke check CLI (nuevo)
- `docs/verification.md` — Paso 2: ítem 6 (script) + resultado verificado
**Tests:**
- Smoke ejecutado: OK - 19642 filas, advertencias 0. Suite pytest sigue en
  verde (31), ruff limpio.
**Cómo verificar:**
- `.\\.venv\\Scripts\\python.exe python/scripts/check_raw_load.py` → OK
- Re-run del workflow n8n → count(*) estable (UPSERT), run_id nuevo.

## [2026-10-10] Sprint 2 · Paso 2 (fix 1) — Payload como literal SQL en el workflow n8n

**Qué:** fij del error "Syntax error at line 30 near '['" detectado en el
primer run manual: n8n interpola `{{ $json.payload }}` inyectando el JSON
SIN comillas dentro del SQL (jsonb_to_recordset([...) → sintaxis inválida;
además los registros con apóstrofes (ej. CTA "L" TRAIN) romperían el
literal). El Code node ahora emite `payloadSql` — el JSON envuelto en
comillas simples con `'` escapado a `''` — y el nodo upsert usa
`jsonb_to_recordset({{ $json.payloadSql }}::jsonb)`.
**Por qué:** expresiones de n8n son interpolación textual; un JSON crudo no
es un literal SQL válido.
**Archivos:**
- `n8n/workflows/sprint2-socrata-raw.json` — jsCode (payloadSql) + query
**Tests:**
- JSON re-validado (payloadSql presente en ambos nodos; no queda
  `{{ $json.payload }}`)
**Cómo verificar:**
- Re-run del workflow desde n8n (con los 2 nodos ya corregidos en la GUI
  o re-importando el JSON); debe completar y poblar raw.crimes.

## [2026-10-10] Sprint 2 · Paso 2 — Workflow n8n Socrata→raw.crimes + pipeline_runs

**Qué:** (a) migración `002_operational.sql` con la capa operacional:
schema `ops` + tabla `ops.pipeline_runs` (log de runs: status RUNNING/SUCCESS/
PARTIAL/FAILED, conteos por run) + 6 tests de integración nuevos. (b) Workflow
n8n exportable (`manualTrigger` → Set ventana dev 2026-09→10 → HTTP Socrata
($where half-open + ORDER BY id + $limit 50000) → Filter valida id/date → Code
serializa a JSON (paid orchestration, transformación queda en SQL) → Postgres
INSERT bulk con `jsonb_to_recordset` + UPSERT `ON CONFLICT (id)` → log del run).
**Por qué:** primer pipeline end-to-end (Socrata → n8n → raw.crimes). El upsert
bulk en una sola sentencia evita ~20k round-trips n8n↔PG (la validación
permanece en n8n según la división de trabajo). records_inserted/updated quedan
NULL en este MVP (se refina en Sprint 10); la paginación en bucle para ventanas
anuales llega en el Paso 3.
**Archivos:**
- `database/migrations/002_operational.sql` — schema ops + pipeline_runs (nuevo)
- `python/tests/integration/test_operational_schema.py` — 6 tests (nuevo)
- `n8n/workflows/sprint2-socrata-raw.json` — workflow exportable (nuevo)
- `docs/verification.md` — checklist del Paso 2 (importar, credencial, run,
  re-run idempotente, queries de smoke)
**Tests:**
- `python/tests/integration` → 14 passed (8 raw + 6 operational); total 31
- Ruff limpio; `002_operational.sql` aplicado y verificado en dev (CREATE x3)
**Cómo verificar:**
- Ejecutar el checklist del Paso 2 en `docs/verification.md` (importar
  workflow, crear credencial `chicago-postgres (docker)`, run manual, y las
  3 queries de smoke + re-run idempotente).
**Pendiente detectado:**
- Mayor riesgo del JSON exportado a ciegas: `typeVersion` de los nodos n8n;
  si el import falla, abrir el nodo en la GUI y ajustar (params esenciales
  están completos).

## [2026-10-10] Sprint 2 — Checklist de verificación por paso (docs/verification.md)

**Qué:** nuevo `docs/verification.md`: checklist accionable por sprint/paso
con (1) los objetos revisables, (2) las verificaciones de contenido
(tests/lint/manual con comandos exactos) y (3) los pasos git
(add/commit/push en el flujo GitFlow). Ya completado para todo Sprint 1 y el
Paso 1 del Sprint 2; los pasos siguientes se llenan al implementarlos.
**Por qué:** el usuario pidió guardar por sprint los pasos de verificación y
git que hasta ahora solo vivían en el chat y dispersos entre docs.
**Archivos:**
- `docs/verification.md` — checklist por paso (nuevo)
- `AGENTS.md` — regla 2 extendida: todo paso debe dejar su checklist aquí
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Ejecutar tal cual la checklist del Sprint 2 · Paso 1 (pytest 17/25 + ruff
  + git add/commit/push); los comandos son los ya validados en esta sesión.

## [2026-10-10] Sprint 2 · Paso 1 — Helper Python Socrata/SoQL + tests unitarios

**Qué:** primer módulo de `python/src/ingestion/`: `socrata.py` con 4 piezas —
`build_params` (construye `$where/$select/$order/$limit/$offset/$$app_token`),
`date_window_where` (rango half-open `date >= start AND date < end`),
`fetch_page` (GET JSON con urllib, sin dependencias nuevas) y `paginate`
(generador por páginas con `ORDER BY id` determinista, para alimentar al
workflow n8n). 17 tests unitarios nuevos sin red (fake fetch + monkeypatch).
**Por qué:** Sprint 2 pide "helper opcional para explorar Socrata / construir
queries SoQL"; centraliza las reglas de la skill `chicago-data-ingestion`
(nunca OFFSET profundo sin filtro de fechas, ORDER BY id, límite de página
<= 50000) en un solo lugar testable. `urllib` del stdlib evita sumar
`requests` al requirements.
**Archivos:**
- `python/src/ingestion/socrata.py` — helper (nuevo)
- `python/src/ingestion/__init__.py` — paquete (nuevo)
- `python/tests/unit/conftest.py` — sys.path hacia `python/src` (nuevo)
- `python/tests/unit/test_socrata.py` — 17 tests (nuevo)
**Tests:**
- `python/tests/unit` → 17 passed · total 25 passed (unit + integration)
- `ruff check python` → All checks passed (se corrigieron: import Callable
  desde collections.abc, TypeError para respuesta no-lista, orden de imports,
  variable dummy `_calls`)
**Cómo verificar:**
- `pytest python/tests/unit -v`
- `ruff check python`
- Aún sin red: en el Paso 2/3 el helper se consume solo desde n8n vía HTTP;
  para explorar a mano: `socrata.fetch_page("ijzp-q8t2",
  socrata.build_params(where=socrata.date_window_where(...), limit=5))`

## [2026-10-10] Sprint 1 — Modelo Git alineado al artículo de nvie (GitFlow)

**Qué:** reescrito `docs/git-workflow.md` para seguir el artículo
"A successful Git branching model" (nvie, 2010) como práctica explícita:
reglas de origen/destino por tipo de rama, merges siempre `--no-ff`,
versión asignada al crear la `release-*`, prohibición de features en
release, excepción del hotfix con `release-*` abierta y nota de reflexión
del autor (por qué GitFlow sí aplica aquí). Naming ajustado al artículo:
`release-0.2.0` / `hotfix-0.1.1` (antes `release/sprintN`). Adaptaciones
documentadas: `main` por `master` y tags `vX.Y.Z`.
**Por qué:** el usuario pidió tomar el artículo como práctica; el doc
anterior era "GitFlow simplificado" con naming propio y sin las reglas
formales (no-ff, bump, excepción hotfix→release).
**Archivos:**
- `docs/git-workflow.md` — reescrito (9 secciones, fuente citada)
- `docs/plan.md` — §2 regla 6 con naming del artículo
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Leer `docs/git-workflow.md` y comparar §3-§6 con el artículo; los comandos
  son los del modelo estrenado en §9.

## [2026-10-10] Sprint 1 — Modelo de ramas, tags y releases

**Qué:** se formalizó el flujo Git (GitFlow simplificado) en el nuevo
`docs/git-workflow.md`: roles de `main/develop/feature/release/hotfix`,
naming, ciclo por paso, cierre de sprint con tag SemVer (`v0.1.0` = Sprint 1),
mapeo con el CI y checklist de protección de `main` al crear el remote. Se
creó la rama `develop`, el CI ahora corre en `main` y `develop`, y el plan
(§2, regla 6) + `AGENTS.md` referencian el modelo.
**Por qué:** el usuario pidió trabajar con buenas prácticas (main, develop,
feature, release, tags) antes del Sprint 2; sin modelo, los commits caían
todos a `main` sin releases versionados.
**Archivos:**
- `docs/git-workflow.md` — modelo completo + comandos (nuevo)
- `docs/plan.md` — §2, regla 6 (ramas)
- `AGENTS.md` — doc clave + regla 6 (feature/*, no directo a main)
- `README.md` — tabla de docs (+1 fila)
- `.github/workflows/ci.yml` — triggers en `[main, develop]`
**Tests:**
- No aplica (docs + config CI). YAML del workflow re-validado abajo.
**Cómo verificar:**
- `git branch -a` → `main` + `develop`
- `git log --oneline --graph --all` → `develop` desde el commit del Paso 3
- Leer `docs/git-workflow.md` §7 para estrenar el modelo (commit Paso 4 en
  `main`, tag `v0.1.0`, merge a `develop`).

## [2026-10-10] Sprint 1 · Paso 4 — Makefile real + CI básico (cierra Sprint 1)

**Qué:** se creó el `Makefile` raíz (atajos `up/down/migrate/test-up/
test-down/test-unit/test-integration/lint`, recetas `sh` portables para CI y
Git Bash) y el CI con GitHub Actions (`.github/workflows/ci.yml`: ruff +
`make test-integration` contra un servicio Postgres 16 en 5433). El lint
obligó a ordenar los imports de `test_raw_schema.py`. Con esto se marca el
**Sprint 1 como `[x]`** en el plan y se actualiza el estado del README.
**Por qué:** centralizar comandos (pedido del usuario) y que cada push
verifique lint + tests sin "en mi máquina funciona". El CI usa el servicio
Postgres de GitHub en vez de `docker-compose.test.yml` (mismo puerto y DB).
**Archivos:**
- `Makefile` — atajos del proyecto (nuevo)
- `.github/workflows/ci.yml` — lint + integración en push/PR a main (nuevo)
- `python/requirements-dev.txt` — ruff (nuevo)
- `python/tests/integration/test_raw_schema.py` — fix de imports (ruff I001)
- `docs/plan.md` — Sprint 1 marcado `[x]`
- `README.md` — estado: Sprint 1 hecho, próximo Sprint 2
**Tests:**
- `ruff check python` → All checks passed
- `python/tests/integration` → 8 passed (re-verificado)
- `.github/workflows/ci.yml` validado como YAML; `migrate` re-ejecutado en
  dev (idempotente, solo NOTICEs)
**Cómo verificar:**
- `make test-up` (o `docker compose -f docker-compose.test.yml up -d`)
- `make lint` y `make test-integration` (en Windows sin `make`: `ruff check
  python` y `pytest python/tests/integration -v` desde el `.venv`)
- El CI corre solo tras el push a GitHub (pendiente de remote).
**Pendientes detectados:**
- `make test-unit` existe pero se activa en el Sprint 2 (aún no hay tests unit).
- Sin `make` en Windows: usar Git Bash o los comandos de `docs/`.
- El CI se ejecutará de verdad al conectar el remote y pushear (§8 dev-env).

## [2026-10-07] Sprint 1 — Comandos de verificación guardados en docs

**Qué:** los comandos de verificación dados en el chat (levantar/apagar la DB
de pruebas, correr los tests de integración en PowerShell y bash) quedaron
guardados en la documentación: nueva §9 en `docs/database.md` y comandos
previos + invocación en `docs/testing.md` §4 (marcado Sprint 1 ✅).
**Por qué:** el usuario pidió que ningún comando de verificación viva solo en
el chat; la documentación es la referencia reutilizable en cualquier host.
**Archivos:**
- `docs/database.md` — §9 nueva: DB de pruebas (conexión, variables, up/down)
- `docs/testing.md` — §4: previo (levantar DB) + comandos PowerShell/bash
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Seguir `docs/testing.md` §4 y `docs/database.md` §9; los comandos son los
  ya validados en el Paso 3 (8 passed).

## [2026-10-07] Sprint 1 — Makefile en la planificación

**Qué:** se añadió el `Makefile` a la planificación: figura en la estructura
del repo (§5) y como ítem del checklist del Sprint 1 (atajos `up`, `down`,
`migrate`, `test-unit`, `test-integration`, `lint`; el CI lo usará). También
se registró `docker-compose.test.yml` (creado en el Paso 3) en ambos sitios.
**Por qué:** el usuario pidió que los comandos del proyecto quedaran
centralizados en un `Makefile` antes de continuar; así el Sprint 1 lo crea
como parte de las fundaciones y el CI lo reutiliza.
**Archivos:**
- `docs/plan.md` — §5 (estructura) y Sprint 1 (checklist + resultado)
**Tests:**
- No aplica (solo planificación).
**Cómo verificar:**
- Leer `docs/plan.md` §5 y el checklist del Sprint 1.
**Pendiente (no hecho aquí):**
- Crear el archivo `Makefile` real (siguiente paso del Sprint 1).

## [2026-10-07] Sprint 1 · Paso 3 — Tests de integración de 001_raw

**Qué:** suite de integración que aplica `001_raw.sql` sobre una DB de pruebas
aislada (Docker, puerto 5433) y verifica schemas, tabla `raw.crimes`
(23 columnas + tipos), PK en `id`, índice en `date`, idempotencia de la
migración y enforcement de la PK (duplicados/nulos). Se añadió
`docker-compose.test.yml` y `python/requirements.txt` (pytest + psycopg2-binary).
**Por qué:** el Paso 2 quedó con verificación solo manual; la regla del
proyecto exige test automatizado y el plan (Sprint 1) pide tests de
integración de esquemas/tipos. La DB de pruebas evita tocar desarrollo (5432).
**Archivos:**
- `python/tests/integration/conftest.py` — fixtures (conexión + migración)
- `python/tests/integration/test_raw_schema.py` — 8 tests
- `docker-compose.test.yml` — servicio `postgres-test` en 5433 (nuevo)
- `python/requirements.txt` — pytest + psycopg2-binary (nuevo)
**Tests:**
- `python/tests/integration/test_raw_schema.py` — 8 passed
**Cómo verificar:**
- `docker compose -f docker-compose.test.yml up -d`
- `.\.venv\Scripts\python.exe -m pytest python/tests/integration -v` → 8 passed

## [2026-10-06] Sprint 1 · Paso 2b — Referencia de comandos de base de datos

**Qué:** se creó `docs/database.md`, una referencia reutilizable de todos los
comandos para operar PostgreSQL (conexión, aplicar migraciones, psql
interactivo, meta-comandos, GUI, reset), con versiones para PowerShell y bash.
**Por qué:** el usuario pidió que los comandos quedaran documentados para poder
usarlos en otro host o en el servidor; hasta ahora solo vivían en el chat y en
el changelog (que es un registro, no una referencia).
**Archivos:**
- `docs/database.md` — guía de operación de la BD (nueva)
- `README.md` — añadida a la tabla de documentación
- `AGENTS.md` — añadida a "Documentación clave"
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Seguir `docs/database.md` §3 para aplicar migraciones y §4 para consultar;
  los comandos coinciden con los ya validados en el Paso 2.

## [2026-10-06] Sprint 1 · Paso 2 — Migración 001_raw (schemas + raw.crimes)

**Qué:** primera migración SQL: crea los schemas `raw`, `staging`, `warehouse`
y la tabla `raw.crimes` (copia fiel de los campos de Socrata + columna de
auditoría `loaded_at`). Se añadió un montaje de solo-lectura `./database` al
contenedor Postgres para aplicar migraciones con `psql -f`.
**Por qué:** es la capa de entrada del modelo raw→staging→warehouse (plan §6 y
skill `chicago-postgres`). DDL idempotente (`IF NOT EXISTS`) para poder
re-ejecutar sin romper.
**Archivos:**
- `database/migrations/001_raw.sql` — schemas + `raw.crimes` + índice por `date`
- `docker-compose.yml` — postgres monta `./database:/database:ro`
**Decisiones de diseño:**
- `id TEXT PRIMARY KEY` → fuerza NOT NULL + UNIQUE (regla de `chicago-data-quality`).
- `date`/`updated_on` como `TIMESTAMP` (naive): Socrata entrega hora local de
  Chicago sin offset; guardarla literal evita conversiones indeseadas.
- `updated_on` es el campo de Socrata (= `source_updated_at` del plan §6).
- `location JSONB` preserva el compuesto original (human_address/point).
- `loaded_at TIMESTAMPTZ DEFAULT now()` = auditoría de cuándo ingestamos.
- Índice solo en `date` (consultas por ventana); sin sobre-indexar raw.
**Tests:**
- Verificación manual aplicada (ver abajo). El **test de integración
  automatizado** (DB de pruebas en 5433 + pytest) es el Paso 3 inmediato; el
  paso no se cierra hasta que exista y pase.
**Cómo verificar:**
- `docker compose up -d` (recrea postgres con el montaje)
- `docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/migrations/001_raw.sql`
  → `CREATE SCHEMA` x3, `CREATE TABLE`, `CREATE INDEX`
- `docker compose exec postgres psql -U postgres -d chicago_crimes -c "\dn"` → raw/staging/warehouse
- `... -c "\d raw.crimes"` → 23 columnas, PK en id, índice idx_raw_crimes_date

## [2026-10-06] Sprint 1 · Paso 1 — Infraestructura base (docker-compose)

**Qué:** se creó la infraestructura local con Docker Compose: servicio
`postgres` (PostgreSQL 16) y servicio `n8n`, con volúmenes persistentes,
healthcheck y red compartida. Se añadió `.env.example` y el `.env` local.
**Por qué:** es la primera meta del plan (Sprint 1): Postgres + n8n corriendo
en contenedores, sin instalaciones manuales, de forma reproducible en cualquier
host. n8n usa SQLite propio (volumen) y se conectará a Postgres por nombre de
servicio en los workflows.
**Archivos:**
- `docker-compose.yml` — servicios `postgres` (5432) y `n8n` (5673), volúmenes
  `postgres_data`/`n8n_data`, healthcheck `pg_isready`, `depends_on` saludable
- `.env.example` — variables documentadas (credenciales dev, puertos, TZ
  `America/Lima` = hora local del operador en Perú); se copia a `.env`
- `.env` — creado localmente (ignorado por git)
**Tests:**
- Todavía no hay código Python; la verificación de este paso es de
  infraestructura (ver "Cómo verificar"). Los tests de integración de esquemas
  llegan en el Paso 2/3 con las migrations.
**Cómo verificar:**
- `docker compose config --quiet` → sin errores (ya validado).
- `docker compose up -d` → ambos contenedores `Up`/`healthy` en
  `docker compose ps`.
- Postgres: `docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT version();"`
- n8n: abrir http://localhost:5673 (primera vez pide crear cuenta de owner).

## [2026-10-06] Sprint 0.7 — Git, licencia y Python 3.12

**Qué:** se resolvieron los 3 pendientes de la revisión: (1) fijar Python 3.12
para el venv, (2) definir el momento de empezar con git y documentar los
comandos, y (3) añadir la licencia MIT.
**Por qué:** decisiones del usuario tras la auditoría. Python 3.12 evita
problemas de wheels (pandas/numpy/scikit-learn) con el 3.14 del host; git se
inicia antes del Sprint 1 para versionar el planning y dar base al CI; la
licencia es recomendable para un proyecto de portafolio público.
**Archivos:**
- `LICENSE` — texto MIT estándar (titular pendiente de personalizar)
- `docs/dev-environment.md` — §4 venv con `py -3.12`; §7 checklist actualizado;
  **§8 nuevo**: control de versiones (cuándo y comandos de `git init`/remote)
- `docs/plan.md` — §3 fija Python 3.12; nuevo **Sprint 0.7** con las decisiones
**Tests:**
- No aplica (solo documentación y licencia).
**Cómo verificar:**
- `LICENSE` existe en la raíz.
- `docs/dev-environment.md` §8 lista los comandos de `git init` + push.
- `py -3.12 --version` responde 3.12.x tras instalar Python 3.12.
**Acción pendiente del usuario:**
- Editar `LICENSE` y cambiar `[Tu Nombre]` por tu nombre.
- Instalar Python 3.12 y ejecutar los comandos de `docs/dev-environment.md` §8
  (`git init`, primer commit, remote de GitHub).

## [2026-10-06] Sprint 0.6 — Revisión de consistencia (correcciones)

**Qué:** auditoría del estado del proyecto a petición del usuario. Se corrigió
un bug (heading `## Sprint 0` perdido en este changelog) y varias
inconsistencias: `.nvmrc` referenciado pero inexistente, README desactualizado
(estado y tabla de docs), estructura de repo en `plan.md` sin los archivos del
harness, y Node fijado a una versión ya EOL.
**Por qué:** revisar que no se escapara nada antes de arrancar el Sprint 1; la
documentación debe ser coherente y reproducible en otro host.
**Archivos:**
- `docs/changelog.md` — restaurado el heading `## [2026-10-06] Sprint 0` +
  esta entrada
- `.nvmrc` — creado (fija Node `22` LTS; ya se citaba en dev-environment)
- `docs/dev-environment.md` — §3 y §7: Node 22 LTS en vez de 20.11.0 (20 llega
  a EOL en 2026)
- `README.md` — estado actualizado (Sprints 0–0.6) + tabla de docs completa +
  puntero al checklist de instalación
- `docs/plan.md` — §5: la estructura de repo incluye `.opencode/`,
  `opencode.json`, `.github/`, `.vscode/`, `.gitignore`, `.editorconfig`, `.nvmrc`
- `AGENTS.md` — nueva sección "Documentación clave"
**Tests:**
- No aplica (solo documentación/configuración).
**Cómo verificar:**
- `docs/changelog.md` muestra el heading `## [2026-10-06] Sprint 0 — Plan...`.
- `.nvmrc` existe y contiene `22`.
- README lista `dev-environment.md`, `harness.md` y `harness-install.md`.
**Pendientes detectados (decisión del usuario, no corregidos aquí):**
- Host tiene Python **3.14.8**; el plan fija 3.12+. pandas/scikit-learn pueden
  no tener wheels para 3.14 → recomiendo crear el venv con Python 3.12.
- Repo **sin `git init`** ni remote: el CI de GitHub Actions (Sprint 1) lo
  necesita.
- Sin `LICENSE` (opcional; recomendable MIT para portafolio).

## [2026-10-06] Sprint 0.6 — Entorno de desarrollo e ingeniería de software

**Qué:** se creó la guía del entorno de desarrollo (Docker, CI con GitHub
Actions, nvm, venv, extensiones de VS Code, buenas prácticas) junto con los
primeros archivos de convención del repo: `.gitignore`, `.editorconfig` y
`.vscode/extensions.json`. Se añadió el CI básico al checklist del Sprint 1.
**Por qué:** el proyecto usa Docker/CI desde el Sprint 1 y el usuario pidió
aprender cada herramienta de ingeniería antes de usarla; las convenciones
(`.gitignore`, `.editorconfig`) deben existir antes de `git init`.
**Archivos:**
- `docs/dev-environment.md` — guía: qué es cada herramienta, para qué sirve
  aquí, links oficiales y checklist de instalación del host
- `.gitignore` — excluye secretos (`.env`), `.venv/`, `node_modules/`, caches
- `.editorconfig` — indentación (4 en Python, 2 en JS/YAML/SQL), LF, UTF-8
- `.vscode/extensions.json` — 12 extensiones recomendadas (Python, Ruff,
  Docker, Jupyter, SQLTools, Playwright, GitLens, YAML, REST Client...)
- `docs/plan.md` — Sprint 1: añadido ítem de CI con GitHub Actions
**Tests:**
- No aplica (solo documentación y archivos de convención).
**Cómo verificar:**
- Abrir VS Code en la raíz del proyecto → pestaña Extensions debería ofrecer
  las recomendaciones de `.vscode/extensions.json`.
- Confirmar que `.env` y `.venv/` aparecerían ignorados: `git status` (tras
  `git init`) no debe listarlos.
- Seguir el checklist de instalación de `docs/dev-environment.md` §7
  (Docker Desktop, nvm-windows, venv).

## [2026-10-06] Sprint 0.5 — Manifiesto portable del harness (docs/harness-install.md)

**Qué:** se creó un archivo de instalación con la lista completa de agentes,
skills y MCPs del harness, prerrequisitos del host, checklist de archivos y
pasos para replicarlo en otra máquina.
**Por qué:** el repo debe ser portable: el harness viaja con el código y este
documento permite instalarlo en otro host sin conocimientos previos.
**Archivos:**
- `docs/harness-install.md` — manifiesto: prerrequisitos, pasos, checklist,
  contenido de `opencode.json`, activación de lo diferido y verificación
- `docs/harness.md` — enlace al manifiesto
- `docs/plan.md` — añadido al checklist del Sprint 0.5
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Seguir `docs/harness-install.md` §4 (checklist de archivos) y §7
  (verificación) en el host destino.

## [2026-10-06] Sprint 0.5 — Harness de desarrollo (agents, skills, MCP)

**Qué:** se configuró el harness de opencode: servidores MCP (Context7 y
Playwright activos, Postgres MCP Pro preparado), 3 agentes personalizados
(`@architect`, `@data-engineer`, `@qa`) y 3 skills del proyecto
(`chicago-postgres`, `chicago-data-ingestion`, `chicago-data-quality`).
**Por qué:** los agentes/skills codifican las reglas del pipeline (capas
Postgres, ventanas Socrata, validaciones) y los MCP dan herramientas reales
al asistente; se crean solo las piezas de los sprints cercanos para evitar
over-engineering. Ver evaluación de la propuesta original en
`docs/harness.md` §2.
**Archivos:**
- `opencode.json` — MCPs (formato strict JSON con `$schema`)
- `.opencode/agent/architect.md` — diseño/revisión de arquitectura
- `.opencode/agent/data-engineer.md` — Sprints 1–4 (infra, ingesta, SQL)
- `.opencode/agent/qa.md` — verificación de tests en cada cambio
- `.opencode/skills/chicago-postgres/SKILL.md` — convenciones de BD
- `.opencode/skills/chicago-data-ingestion/SKILL.md` — convenciones Socrata/n8n
- `.opencode/skills/chicago-data-quality/SKILL.md` — validaciones y métricas
- `docs/harness.md` — doc completa: qué hace cada pieza, links, uso por sprint
- `docs/plan.md` — añadido Sprint 0.5
**Tests:**
- No aplica (solo configuración/markdown; sin código ejecutable).
**Cómo verificar:**
- Prerrequisito: instalar Node.js LTS (https://nodejs.org/) — `npx` lanza los
  MCP de Context7 y Playwright.
- Reiniciar opencode y comprobar que Context7 y Playwright figuran como
  servidores MCP conectados.
- Invocar `@qa` (p. ej. "revisa el último cambio") para ver un agente en acción.

## [2026-10-06] Sprint 0 — Plan, estrategia de tests y convenciones

**Qué:** se creó la documentación base del proyecto: plan maestro por sprints,
estrategia de tests (unitarios, integración y E2E con Playwright), este
changelog y las reglas de trabajo incremental.
**Por qué:** el proyecto exige cambios pequeños revisables por el usuario,
tests en cada capa y documentación de cada cambio antes de escribir código.
**Archivos:**
- `docs/plan.md` — arquitectura, decisiones, sprints 0–10, MVP y alcance
- `docs/testing.md` — pirámide de tests + ruta de aprendizaje de Playwright
- `docs/changelog.md` — este documento y su convención
- `README.md` — visión general y arranque rápido
- `AGENTS.md` — reglas para asistentes de código (tests, changelog, idioma)
**Tests:**
- No aplica (solo documentación; no hay código aún).
**Cómo verificar:**
- Leer `docs/plan.md` y aprobar/ajustar los sprints antes de iniciar Sprint 1.
