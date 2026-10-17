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

## [2026-10-17] Sprint 5 · Paso 1 — Entorno ML + notebook 01_data_quality

**Qué:** `python/requirements.txt` extendido con el stack del sprint (numpy,
pandas, scipy, scikit-learn, matplotlib, ipykernel, jupyterlab — con
secciones comentadas por uso) + notebook `01_data_quality.ipynb` (18
celdas, kernel `chicago-crimes` sobre el `.venv`): conecta a dev (5432) con
psycopg2 sin SQLAlchemy, carga `staging.crimes` completa, perfila dtypes/
describe/nulos (con gráfico), muestra top primary_type, tasas
arrest/domestic + conteo por año, histograma por hora del día, top-10
community areas con nombres (JOIN del seed), comparativo raw vs staging
(zero-coords y vacíos → nulos) y las métricas de `ingestion.quality`
(la misma fuente de los data tests). Cierra con una celda de conclusiones
como guía de preguntas.
**Por qué:** primer puerta de Sprint 5 (Python EDA). El notebook se conecta
a la DB real del repo (no a CSV), usa `staging` (la capa limpia, principio
"PostgreSQL transforma" — el EDA también debe ver datos saneados) y reusa
`quality.py` para no duplicar métricas en pandas. Numpy/pandas ya estaban
en el venv (2.5.3 / 3.0.6, fijadas en este requirements).
**Archivos:**
- `python/requirements.txt` — libro del stack del sprint
- `python/notebooks/01_data_quality.ipynb` — notebook (nuevo)
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- No aplica suite (notebook analítico; no hay código de producción).
  La suite sigue en 111 passed — `ruff check python` para confirmar.
**Cómo verificar:**
- Checklist "Sprint 5 · Paso 1" en `docs/verification.md` (pip install,
  registro del kernel, correr el notebook y revisar outputs sane).

## [2026-10-17] Sprint 4 · Fix 1 — Suite de vistas estabilizado para CI

**Qué:** 6 tests rojos tras integrar las vistas (runs de Actions rojos en la
rama del Paso 1): (a) `test_five_views_exist` — `information_schema.views`
no existe como catalog; va `information_schema.tables` con `table_type =
'VIEW'`; (b) columnas rate/percent (`round(numeric)`) llegan como
`Decimal`, no float — aserciones con `Decimal(...)`;
(c) fixture: los nombres 25/77 eran inventados (en el catálogo real 25 =
Austin, 77 = Edgewater) → fixture con los números correctos de los
spot-checks del seed (22 = Logan Square, 41 = Hyde Park, 76 = O'Hare);
(d) `test_warehouse_tables_exist` (Paso 2): filtra `table_type = 'BASE
TABLE'` (el schema también tiene views); (e) `test_fact_null_fks_...`
(Paso 4): `dict(fetchall())` con filas de 3 columnas → comprehension.
**Por qué:** codifiqué los esperados de memoria (nombres de áreas, tipo de
columna del catalog) en vez de leer el seed/documentación — la misma regla
del seed ("extraer de la API oficial, no de memoria") aplica a los data
tests. Además se mergeó el Paso 1 con Actions rojo (violación de §10.3):
ningún merge con CI rojo, de ahora en más es la segunda lección.
**Archivos:**
- `python/tests/integration/test_analytics_views.py` — fixes (a), (b), (c)
- `python/tests/integration/test_dims_fact_schema.py` — filtro BASE TABLE (d)
- `python/tests/integration/test_warehouse_load.py` — dict comprehension (e)
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `pytest python/tests -q` → 111 passed (37 unit + 74 integration)
- `ruff check python` → All checks passed
**Cómo verificar:**
- Checklist "Fix" del Sprint 4 en `docs/verification.md` (pytest local +
  run del CI de la rama verde en Actions ANTES del merge).

## [2026-10-17] Sprint 4 — Cierre del sprint (bump 0.4.0)

**Qué:** Sprint 4 marcado `[x]` en `docs/plan.md` (Paso 1 = única unidad del
sprint: vistas + tests) y estado del README actualizado (Sprint 4 hecho,
próximo Sprint 5). Verificación en dev quedó ejecutada por el usuario:
`vw_monthly_crimes` con los 19.642 reales (sept-2026 vía rate real),
ranking con nombres reales, MoM con prev NULL (única fila del mes) y
`\dv` las 5 vistas.
**Por qué:** cierre de sprint según git-workflow §5. Con esto el branching
MVP (charlas tarea de plan §10) queda: Socrata → n8n → PostgreSQL → vistas
analíticas → (siguiente: Python/EDA + FastAPI + D3).
**Archivos:**
- `docs/plan.md` — Sprint 4 `[x]`
- `README.md` — §Estado
- `docs/changelog.md`, `docs/verification.md` — registro y nota
**Tests:**
- Suite final 111 passed (37 unit + 74 integration; tras el Fix 1 del
  suite de vistas). Sanity en dev verificado por el usuario (checklist
  del Paso 1).
**Cómo verificar:**
- `docs/plan.md` muestra Sprint 4 `[x]`; tras el release: `git tag -l`
  lista `v0.4.0` y main/develop comparten el merge `--no-ff` del release.

## [2026-10-17] Sprint 4 · Paso 1 — Vistas analíticas (analytics.sql)

**Qué:** `database/views/analytics.sql` (nuevo) con las 5 vistas del plan §6,
todas en schema `warehouse` y alimentadas solo de `fact_crime` + dims:
`vw_monthly_crimes` (mes, crimes, arrests, tasa ~round 1dp),
`vw_area_crime_ranking` (RANK con empates + share_pct; áreas NULL fuera),
`vw_month_over_month` (LAG: prev, delta absoluto y %; primer mes NULL),
`vw_day_hour` (heatmap ISODOW x hour) y `vw_area_summary` (volumen,
arrest/domestic, diversidad de tipos, rango de fechas). Target `views` en el
`Makefile` (patrón migrate/seed) + 11 tests de integración
(test_analytics_views.py) con fixture de 10 filas crudas (V-01..V-10:
aug/sep 2026, áreas 25/41/77, 1 fila sin área) y resultados calculados a
mano por vista.
**Por qué:** primer ítem del Sprint 4. Las vistas centralizan el SQL
analítico (la API las consume, no re-implementa; principio "PostgreSQL
transforma"). Decisiones: sin ORDER BY salvo `vw_month_over_month`
(el consumidor pagina/filtra), rates con `round(..., 1)`,
`RANK()` estándar (empates → 1,1,3), y las filas con `community_area_key`
NULL quedan fuera de ranking/summary pero si populares otros agregados
(monthly, day_hour).
**Archivos:**
- `database/views/analytics.sql` — 5 vistas (nuevo)
- `Makefile` — target `views` (nuevo) + `.PHONY` actualizado
- `python/tests/integration/test_analytics_views.py` — 11 tests (nuevo)
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `pytest python/tests/integration` → 74 passed (63 + 11) · suite total →
  111 passed (37 unit + 74 integration)
- `ruff check python` → limpio
**Cómo verificar:**
- Checklist "Sprint 4 · Paso 1" en `docs/verification.md` (pytest, ruff,
  `make views` en dev y queries de sanity con los 19.642 reales).

## [2026-10-17] Sprint 3 — Cierre del sprint (bump 0.3.0)

**Qué:** Sprint 3 marcado `[x]` en `docs/plan.md` (con el Paso 4 — carga
staging → warehouse — como ítem nuevo del checklist) y estado del README
actualizado (Sprint 3 hecho, próximo Sprint 4). La carga quedó ejecutada en
dev: 19.642 filas en `fact_crime` == staging con fecha, dims a NOTICEs
(10.957 dim_date · 254 crime_type · 15.350 location · 24 district · 77
community_area).
**Por qué:** cierre de sprint según git-workflow §5. El modelo dimensional
está poblado e idempotente; con el fix previo del contrato `''→NULL` la
regla quedó implementada y testeada de verdad.
**Archivos:**
- `docs/plan.md` — Sprint 3 `[x]` (con Paso 4 agregado al checklist)
- `README.md` — §Estado
- `docs/changelog.md`, `docs/verification.md` — esta entrada y nota
**Tests:**
- Verificar contenido (lo ejecutás vos): `pytest python/tests -q` → 100
  passed · `ruff check python` → All checks passed · sanity + idempotencia
  del checklist del Paso 4.
**Cómo verificar:**
- `docs/plan.md` muestra Sprint 3 `[x]`; tras el release: `git tag -l`
  lista `v0.3.0` y el log muestra el merge `--no-ff` del release en ambas.

## [2026-10-16] Sprint 3 · Paso 4 — Carga staging → warehouse (load_warehouse.sql)

**Qué:** `database/functions/load_warehouse.sql` (nuevo): 6 funciones SQL
idempotentes — `load_dim_date(start, end)` (calendario 2001-2030 con
`generate_series` + CASE fijos para month/day_name, determinista), 3 cargas
de dims (`dim_crime_type`, `dim_location`, `dim_district`) con
`SELECT DISTINCT` + `ON CONFLICT DO NOTHING`, `load_fact_crime()` con LEFT
JOINs `IS NOT DISTINCT FROM` para resolver las keys surrogadas y
`ON CONFLICT (crime_id) DO UPDATE` (re-cargas aplican correcciones de
Socrata), y el orquestador `load_warehouse()` (orden calendario → dims →
fact, con NOTICE por paso). Target `load-warehouse` en el `Makefile`
(aplica funciones + ejecuta el orquestador). 10 tests de integración
(test_warehouse_load.py) con 8 filas fixture: dim_date completa y sus
atributos, dims dedupeadas (6/7/6), fact excluye filas sin date (7 de 8),
resolución completa de keys vía joins (LW-01 → Austin/THEFT/hour 10),
FKs NULL para unknown (LW-06 área 0, LW-08 primary_type vacío, probando el
contrato del fix) y recarga idempotente (7/6/7/6 estables).
**Por qué:** cierre del modelo dimensional poblado (result del Sprint 3):
la estrella deja de estar vacía. n8n orquesta, PostgreSQL transforma: la
carga es SQL puro re-ejecutable. `IS NOT DISTINCT FROM` en los joins de
dims maneja NULLs de iucr/block sin perder matches. `dim_community_area`
NO se carga desde staging: su fuente es el seed con los nombres oficiales
(Paso 3). Dos bugs míos corregidos antes de entregar: texto corrupto en el
último test, y orden del fixture (sembraba las 77 areas ANTES del
TRUNCATE, que las borraba).
**Archivos:**
- `database/functions/load_warehouse.sql` — 6 funciones (nuevo)
- `Makefile` — target `load-warehouse` (nuevo) + .PHONY
- `python/tests/integration/test_warehouse_load.py` — 10 tests (nuevo)
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `python/tests/integration` → 63 passed (53 + 10) · suite total → 100 passed
- `ruff check python` → limpio
**Cómo verificar:**
- Checklist del Paso 4 en `docs/verification.md` (pytest, ruff, cargar la
  estrella en dev con el año real y queries de sanity: fact == staging
  con fechas, aliases de nombres vía joins).

## [2026-10-16] Sprint 3 · Fix 1 — Contrato ''→NULL en staging (declarado pero no implementado)

**Qué:** `003_staging.sql` ahora envuelve los 7 campos de texto en
`nullif(btrim(col), '')` (antes solo `btrim`), y
`test_empty_string_becomes_null` corregido para que codifique el contrato
real (antes asertaba `== ""`, que enmascaraba el bug pese a su nombre).
**Por qué:** el contrato declarado (header de 003 y changelog del Paso 1)
dice "btrim + ''→NULL en texto", pero el SQL no lo implementaba y el test —
escrito por error con `assert == ""` en vez de `is None` — hacía pasar
verdes runs que no probaban la regla. Descubierto al releer 003 en la
preparación del Paso 4: `dim_crime_type.primary_type` es NOT NULL y sin esta
regla la carga crearía un miembro de dimensión con tipo vacío.
**Archivos:**
- `database/migrations/003_staging.sql` — 7 campos de texto con nullif
- `python/tests/integration/test_staging_schema.py` — aserción corregida
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- Conteo de suite sin cambios (90 total: 37 unit + 53 integration); el test
  ahora SÍ verifica la regla. Verificación local obligatoria antes de merge.
**Cómo verificar:**
- Checklist "Fix — contrato staging + F401" en `docs/verification.md`
  (incluye re-aplicar 003 en dev y sanity contra datos reales).

## [2026-10-16] Sprint 3 · Fix 2 — F401 en test del seed (CI del seed rojo, tests skipped)

**Qué:** eliminado el `from pathlib import Path` sin uso en
`python/tests/integration/test_community_areas_seed.py` (F401 unused-import).
**Por qué:** los runs 20-21 del CI (seed y su merge a develop, 5470280 y
7b56eae) fallaron en el step "Lint (ruff)" y los tests de integración
quedaron SKIPPED — los commits se mergeatearon sin verificar Actions. El
ruff local tampoco se corrió en esa verificación. Nota: los runs 18-19
(dims-fact) sí fueron verdes, por eso el F401 del seed es el primer FAILO
del lint desde el hotfix 0.2.1.
**Archivos:**
- `python/tests/integration/test_community_areas_seed.py` — import eliminado
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- No aplica funcionalmente (la opción de referencia Path es innecesaria:
  SEED_PATH se construye sobre REPO_ROOT que importamos del conftest).
**Cómo verificar:**
- `ruff check python` → All checks passed
- Tras el fix merge: CI de develop en verde (Actions, run #22+)

## [2026-10-14] Sprint 3 · Paso 3 — Seed de las 77 community areas

**Qué:** `database/seeds/community_areas.sql` (nuevo): UPSERT idempotente de
las 77 community areas oficiales en `warehouse.dim_community_area` (número +
nombre). Nuevo target `seed` en el `Makefile` (mismo patrón que `migrate`,
loop sobre `database/seeds/*.sql`). 6 tests de integración
(test_community_areas_seed.py): total 77, numeración completa 1–77, sin
nombres nullos, idempotencia del seed (re-aplicar → sigue 77), caso del
apóstrofe ("O'Hare") y spot checks (Lake View no "Lakeview", Logan Square,
Loop, Hyde Park).
**Por qué:** tercer ítem del Sprint 3. El seed se extrajo de la API oficial
(NO escrito de memoria); el descubrimiento: `cauq-8yn6` (la ref. del plan)
es solo la **vista de mapa** del dataset tabular **`igwz-8jzy`** — corregido
el plan (Sprint 3 y §12). El source trae nombres EN MAYÚSCULAS y "OHARE"; el
seed guarda Title Case + "O'Hare" (nombre canónico), transformación
documentada en el encabezado del SQL. `ON CONFLICT DO UPDATE` (UPSERT del
skill) para que re-aplicar el seed refresque nombres sin duplicar.
**Archivos:**
- `database/seeds/community_areas.sql` — 77 filas + UPSERT (nuevo)
- `Makefile` — target `seed` (nuevo) + `.PHONY` actualizado
- `python/tests/integration/test_community_areas_seed.py` — 6 tests (nuevo)
- `docs/plan.md` — Sprint 3 y §12: dataset tabular corregido a `igwz-8jzy`
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `python/tests/integration` → 53 passed (47 + 6) · suite total → 90 passed
- `ruff check python` → limpio
**Cómo verificar:**
- Checklist del Paso 3 en `docs/verification.md` (DB de pruebas, pytest,
  ruff, `make seed` en dev y 2 queries de sanity con nombres).

## [2026-10-14] Sprint 3 · Paso 2 — Modelo dimensional (004_dims_fact.sql)

**Qué:** migración `004_dims_fact.sql` con el warehouse dimensional del plan
§6: `dim_date` (date_key yyyymmdd estilo Kimball, month/day_name a generar
con CASE fijo — determinista, sin locale), `dim_crime_type` y `dim_location`
(grano = combinación natural con `UNIQUE ... NULLS NOT DISTINCT` para que los
NULLs no dupliquen), `dim_district`, `dim_community_area` (nombre llega con
el seed del Paso 3) y `fact_crime` (crime_id natural UNIQUE, FK date_key NOT
NULL, demás FKs NULLables, CHECK hour 0-23, índices solo en las FKs de
filtro/agrupación). La población desde staging llega en el Paso 4; aquí va
solo DDL. + 10 tests de integración (estructura, PK/UNIQUE, enforcement de
FKs, FKs NULLables, CHECK de hour, dedupe con NULLs, índices). Fixture
`seeded_date` con `ON CONFLICT DO NOTHING` para que ningún test dependa del
orden de ejecución.
**Por qué:** segundo ítem del Sprint 3. Separar DDL de carga mantiene los
pasos pequeños y revisables; NULLS NOT DISTINCT (PG15+) evita el clásico
"NULL != NULL" que duplicaría miembros de dimensión con iucr/block nulos.
**Archivos:**
- `database/migrations/004_dims_fact.sql` — dims + fact + índices (nuevo)
- `python/tests/integration/test_dims_fact_schema.py` — 10 tests (nuevo)
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `python/tests/integration` → 47 passed (37 + 10) · suite total → 84 passed
- `ruff check python` → limpio
**Cómo verificar:**
- Checklist del Paso 2 en `docs/verification.md` (DB de pruebas, pytest,
  ruff, aplicar en dev y `\dt warehouse.*`).

## [2026-10-14] Docs — checklist pre-merge en el cheat sheet (§10.3)

**Qué:** §10.3 de `docs/git-workflow.md` ahora lista explícitamente qué
verificar ANTES de mergear un feature a `develop`: (1) run del CI en verde en
la pestaña Actions (el push a `feature/**` lo dispara solo) y (2) checklist
del paso en `docs/verification.md` ejecutado localmente.
**Por qué:** pedido del usuario: que el "qué hacer al terminar cada cambio"
quede anotado en el doc de git — hasta ahora esa verificación pre-merge solo
vivía en el chat.
**Archivos:**
- `docs/git-workflow.md` — §10.3 con checklist pre-merge
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Leer §10.3 y comparar con lo ejecutado al cerrar `feature/sprint3-staging`
  (debe coincidir: CI verde en Actions + pytest/ruff local antes del merge).

## [2026-10-14] Sprint 3 · Paso 1 — Capa staging (view staging.crimes)

**Qué:** migración `003_staging.sql`: `staging.crimes` como **VIEW** sobre
`raw.crimes` con las reglas de limpieza del skill chicago-data-quality —
`btrim` + `''→NULL` en campos de texto, coordenadas `(0,0)` y fuera de rango
`→NULL` (ambas), coordenadas parciales se conservan, `community_area` fuera
de 1–77 `→NULL` (los `0` de registros viejos = unknown). Sin filtrado de
filas: eso lo decide el warehouse al poblar fact. + 11 tests de integración
(test_staging_schema.py: sembrando 9 filas raw conocidas y verificando cada
regla contra la view). Corregida la numeración en plan.md (002 ya lo ocupaba
002_operational.sql → staging es 003, dims será 004).
**Por qué:** primer paso del Sprint 3 según el skill chicago-postgres
("staging limpia; warehouse solo se alimenta desde staging"). La decisión de
VIEW sobre tabla: cero datos duplicados, siempre sincronizada con raw, la
transformación queda en una sentencia declarativa (principio "n8n orquesta,
PostgreSQL transforma") y no requiere un paso de carga aparte.
**Archivos:**
- `database/migrations/003_staging.sql` — CREATE OR REPLACE VIEW (nuevo)
- `python/tests/integration/test_staging_schema.py` — 11 tests (nuevo)
- `docs/plan.md` — numeración de migraciones Sprint 3 corregida
- `docs/changelog.md`, `docs/verification.md` — registro y checklist
**Tests:**
- `python/tests/integration` → 37 passed (26 + 11) · suite total → 74 passed
- `ruff check python` → limpio
**Cómo verificar:**
- Checklist del Paso 1 en `docs/verification.md` (pytest, ruff, aplicar la
  migración en dev y 3 queries de sanity contra datos reales).

## [2026-10-14] Docs — Cheat sheet de git por escenario + sección GitHub Actions

**Qué:** en `docs/git-workflow.md` se amplió §8 (ahora "CI y ramas (GitHub
Actions)": triggers de ci.yml —push a main/develop/feature/** y PRs—, pasos
del job, servicio Postgres de GitHub en 5433 y la regla del drift de ruff) y
se añadió §10: cheat sheet con los comandos de los 5 escenarios habituales
(empezar paso, guardar avance, terminar paso, release de sprint, hotfix) más
una tabla de decisión de ramas, protocolo de CI rojo y comandos de inspección.
**Por qué:** el usuario pidió guardar los comandos de cada escenario en un md
(los flujos de Sprint 2 + hotfix 0.2.1 vivían solo en el chat); git-workflow.md
ya era la fuente de git y queda como única referencia. La versión del bump viaja
como feature branch propia (docs-only, después del hotfix).
**Archivos:**
- `docs/git-workflow.md` — §8 ampliado + §10 nuevo
- `docs/changelog.md`, `docs/verification.md` — esta entrada y su checklist
**Tests:**
- No aplica (solo documentación).
**Cómo verificar:**
- Leer §10 y comparar los 5 escenarios con lo realmente ejecutado en
  Sprint 2 y el hotfix 0.2.1 (flujos idénticos salvo el bump en rama release).

## [2026-10-14] Hotfix 0.2.1 — RUF100: noqa sin usar en check_raw_load.py

**Qué:** eliminado el comentario `# noqa: E402` de la línea 23 de
`python/scripts/check_raw_load.py` (la única directiva noqa del repo).
**Por qué:** no existe `ruff.toml`/`pyproject.toml` y ruff NO tiene E402
activado por defecto → la directiva era "unused" y RUF100 la reportaba,
dejando el CI de `v0.2.0` rojo en `make lint`. Corrige la predicción del Paso
4 (que anticipaba un I001: el import tras `sys.path.insert` no ofende a la
config vigente; el problema fue el noqa mismo). Como `v0.2.0` ya está
taggeado en `main`, va como hotfix de versión PARCHE (git-workflow §6).
**Archivos:**
- `python/scripts/check_raw_load.py` — se elimina la directiva
- `docs/changelog.md`, `docs/verification.md` — esta entrada + checklist
**Tests:**
- Sin cambios de comportamiento: Python ignora `noqa` (es un comentario
  normal; solo el linter lo interpreta). Suite queda en 63 passed.
**Cómo verificar:**
- `ruff check python` → All checks passed (local y CI en verde tras el push)
- Tras el hotfix flow: `git tag -l` lista `v0.2.1`.
**Pendiente detectado:**
- Pinnear `ruff>=0.8` a versión exacta en `requirements-dev.txt`: el CI
  instala ruff fresco (última) y el venv local quedó atrás; ese drift explica
  que local no reportara RUF100 y el CI sí.

## [2026-10-14] Sprint 2 — Cierre del sprint (bump 0.2.0)

**Qué:** Sprint 2 marcado `[x]` en `docs/plan.md` (con nota de que el trigger
es manual en dev — el Schedule semanal llega con el incremental en Sprint 10)
y estado del README actualizado (Sprint 2 hecho, próximo Sprint 3).
**Por qué:** cierre de sprint según git-workflow §5. El bump viaja como
último commit del feature branch (no había fixes de release que versionar, así
la rama `release-0.2.0` solo transfiere a `main` + tag `v0.2.0`); en sprints
futuros con fixes de release, el bump se hará en la rama release como indica
el doc.
**Archivos:**
- `docs/plan.md` — Sprint 2 `[x]`
- `README.md` — §Estado
- `docs/changelog.md` — esta entrada
**Tests:**
- No aplica (solo documentación). Suite queda en 63 passed (ver Paso 4).
**Cómo verificar:**
- `docs/plan.md` muestra Sprint 2 `[x]`; tras el release:
  `git tag -l` lista `v0.2.0` y `git log --oneline --graph main develop`
  muestra el merge `--no-ff` del release en ambas ramas.

## [2026-10-13] Sprint 2 · Paso 4 — Data tests de calidad (módulo quality + fixtures)

**Qué:** (a) nuevo `python/src/ingestion/quality.py` con las métricas del skill
chicago-data-quality como funciones sobre cursor: `duplicate_ids`, `null_ids`,
`out_of_range_coordinates`, `zero_coordinates` (Socrata a veces emite (0,0)),
`invalid_community_area` (fuera del catálogo 0–77), `empty_primary_type`,
`null_counts`/`null_rate` por columna con whitelist (el nombre se interpola
como identificador SQL vía `psycopg2.sql.Identifier`) y `quality_report`.
(b) Data tests de integración que siembran 12 filas fixture (`DQ-01..12`,
casos válidos + inválidos conocidos) en la DB de pruebas (5433) y verifican
cada métrica contra el conteo calculado a mano. (c) Tests unitarios de la
lógica pura (cálculo de rate, división por cero, rechazo de columna fuera de
whitelist) con cursor falso. (d) Refactor de `check_raw_load.py` para consumir
`quality.py` (una sola fuente de verdad; salida idéntica — variable local
`quality` renombrada a `warnings` para no chocar con el módulo).
**Por qué:** último ítem del Sprint 2 ("tests de calidad: unicidad, rangos,
nulos"). La whitelist + `sql.Identifier` evita inyección por identificador
(la columna es identificador SQL, no valor parametrizable con `%s`).
`duplicate_ids`/`null_ids` son trivialmente 0 por la PK — el test valida que
la métrica corre; el enforcement ya lo cubre `test_raw_schema.py`. La métrica
`unknown_crime_type` contra catálogo completo queda para Sprint 3 (dims); por
ahora `empty_primary_type` cubre NULL/vacío.
**Archivos:**
- `python/src/ingestion/quality.py` — métricas (nuevo)
- `python/tests/integration/test_data_quality.py` — 12 tests + fixture (nuevo)
- `python/tests/unit/test_quality.py` — 3 tests unit (nuevo)
- `python/tests/integration/conftest.py` — bootstrap sys.path a `python/src`
  (mismo patrón que `tests/unit/conftest.py`)
- `python/scripts/check_raw_load.py` — consume `quality.py` (salida idéntica)
- `docs/verification.md` — checklist del Paso 4 + pasos de cierre del Sprint 2
**Tests:**
- `python/tests/unit` → 37 passed (34 + 3) · `python/tests` → 63 passed (48 + 15)
- `ruff check python` → limpio
- Datos reales (año cargado en Paso 3): se verifican con `check_raw_load.py`,
  que ahora comparte las mismas funciones de métrica ya testeadas.
**Cómo verificar:**
- Checklist del Paso 4 en `docs/verification.md` (DB de pruebas arriba, pytest,
  ruff, smoke script contra dev).
**Pendiente detectado:**
- Si ruff marca I001 (isort) en `check_raw_load.py` por el import tras
  `sys.path.insert`, aplicar `ruff check --fix` (el `# noqa: E402` ya cubre E402).

## [2026-10-13] Sprint 2 · Paso 3 — Bucle mensual para la ventana 1 año (workflow n8n)

**Qué:** el workflow pasa de 1 página suelta (MVP del Paso 2) a un bucle por
ventanas mensuales: `Meses de la ventana` (Code nuevo) genera las sub-ventanas
half-open y `Loop Over Items` (SplitInBatches v3, batch 1) procesa mes a mes:
fetch → validar+payload → upsert → log (1 fila en `pipeline_runs` por mes, con
`error_message`) → retorno al loop. Ventana dev: 2025-10-01 → 2026-10-01
(12 meses, solapa sept-2026 ya cargado → prueba el UPSERT). Se añadió un guard
de truncamiento: si un mes devuelve `pageSize` registros (imposible para este
dataset: máx. histórico ~45k/mes) no se inserta nada y queda `FAILED` con
mensaje. Se eliminó el nodo Filter: la validación vive en el Code node porque
dentro del bucle los conteos deben ser por iteración (`$input.all()` acotado a
la ejecución actual; `$('Nodo').all()` agregaría todas las iteraciones).
**Por qué:** Paso 3 del plan (ventana 1 año). La regla del skill
chicago-data-ingestion es backfill por ventanas año/mes (nunca OFFSET profundo
sin filtro); el bucle mensual la implementa y deja el camino listo para el
backfill histórico de Sprint 10. Se verificó en el código fuente de n8n que el
output 0 de SplitInBatches es `done` y el 1 es `loop` (al revés de lo
intuitivo) y que `$('Loop Over Items').item` es la vía documentada de leer el
item actual del bucle. `month_windows()` en el helper Python es la réplica
testeable del JS del nodo (comentarios cruzados en ambos).
**Archivos:**
- `n8n/workflows/sprint2-socrata-raw.json` — reescrito (8 nodos, bucle)
- `python/src/ingestion/socrata.py` — `month_windows()` nuevo
- `python/tests/unit/test_socrata.py` — 6 tests (TestMonthWindows)
- `python/tests/unit/test_n8n_workflow.py` — 11 tests estructurales (nuevo)
- `docs/verification.md` — checklist del Paso 3 (smoke 3 meses + run anual)
**Tests:**
- `python/tests/unit` → 34 passed (17 previos + 6 month_windows + 11 workflow)
- `pytest python/tests -q` → 48 passed (unit + integration) · ruff limpio
- Los tests estructurales fijan: wiring del bucle (loop-back), conteos por
  iteración, guard de truncamiento, contratos upsert/log y credenciales como
  placeholder (anti-export de credenciales reales).
**Cómo verificar:**
- Ejecutar el checklist del Paso 3 en `docs/verification.md` (smoke del bucle
  con 3-4 meses, luego run anual completo + idempotencia + check_raw_load.py).
**Pendiente detectado:**
- Si un mes devolviera 0 registros, n8n no ejecuta los nodos siguientes y el
  bucle se detendría en silencio (no ocurre en este dataset; se detectaría por
  filas faltantes en pipeline_runs).
- Paginación interna dentro de un mes (OFFSET) queda diferida: ningún mes
  histórico supera pageSize; el guard FAIL ruidoso cubre el caso.

## [2026-10-10] Sprint 2 · Paso 2 (fix 2) — CI valida pushes de feature/*

**Qué:** `.github/workflows/ci.yml` ahora dispara también en push a
`feature/**` (además de main/develop y PRs hacia ellas).
**Por qué:** el git-workflow exige "ningún merge con CI rojo"; sin el
trigger de feature, los commits de la rama iban a GitHub sin verificación y
el CI solo aparecía al abrir el PR. Con este trigger cada push de la rama
se valida antes del PR.
**Archivos:**
- `.github/workflows/ci.yml` — push branches + `feature/**`
**Tests:**
- YAML válido (re-validar en el próximo push); el resto del workflow no cambia
**Cómo verificar:**
- Push de la rama → pestaña Actions en GitHub muestra el run "ci" en verde
  (o rojo, y así se corrige antes del PR).

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
