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
