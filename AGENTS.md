# AGENTS.md — Reglas para asistentes de código

Reglas que TODO agente (Claude, opencode, etc.) debe seguir en este repo.

## Documentación clave
- `docs/plan.md` — plan maestro y sprints (fuente de verdad del alcance).
- `docs/testing.md` — estrategia de tests por capa.
- `docs/dev-environment.md` — herramientas de ingeniería (Docker, CI, nvm, venv).
- `docs/harness.md` + `docs/harness-install.md` — agentes, skills y MCP.
- `docs/changelog.md` — registro de cada cambio.

## Idioma
- Código e identificadores: en inglés.
- Comunicación, docs, commits y changelog: en español.

## Flujo de trabajo
1. **Cambios pequeños e incrementales.** El usuario revisa cada cambio antes
   de continuar con el siguiente. No hacer varios cambios no solicitados de
   una vez.
2. **Documentar cada cambio** en `docs/changelog.md` (formato definido ahí:
   qué / por qué / archivos / tests / cómo verificar) ANTES de darlo por
   terminado.
3. **Todo cambio de código incluye sus tests.** Sin tests, el cambio no está
   terminado. Ver estrategia en `docs/testing.md`.
4. Al completar un sprint, marcarlo como `[x]` en `docs/plan.md`.
5. Consultar `docs/plan.md` para no salirse del alcance definido (nada de
   Kafka, Airflow, Spark, Kubernetes, LLMs, etc.).

## Testing
- Python/API: `pytest` (unit + integración). Estructura:
  `python/tests/unit/`, `python/tests/integration/`, `api/tests/`.
- E2E del dashboard: Playwright en `dashboard/e2e/` (solo lo que vive en el
  navegador; la API se testea con TestClient, no con Playwright).
- DB de pruebas en Docker, puerto distinto al de desarrollo (ej. 5433).

## Decisiones de diseño (no contradecir sin consultar al usuario)
- n8n **orquesta**; PostgreSQL **transforma**. No poner transformaciones
  pesadas en n8n.
- Ingesta: backfill por ventanas año/mes; incremental semanal con ventana
  solapada de 14–30 días y UPSERT por `id`.
- ML: split **temporal**, nunca aleatorio (train ≤ 2024, test en 2025+).
- En desarrollo: ventanas de datos pequeñas (1 mes → 3 meses → 1 año → todo).
- El frontend D3 nunca se conecta directo a PostgreSQL; siempre vía FastAPI.

## Comandos (completar conforme se agregan sprints)
- Tests unit (python): `pytest python/tests/unit`
- Tests integration (db): `pytest python/tests/integration`
- Tests api: `pytest api/tests`
- Tests e2e: `pytest dashboard/e2e`
- Infra local: `docker compose up -d`
