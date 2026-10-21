# Chicago Crimes Analytics Platform

Pipeline end-to-end de datos públicos de crímenes de Chicago (Socrata API):
ingesta automática con n8n, warehouse dimensional en PostgreSQL, analítica
SQL, EDA y hotspots con Python, API con FastAPI, dashboard interactivo con
D3.js y reporte semanal a stakeholders con Power Automate.

```text
Socrata → n8n → PostgreSQL (raw/staging/warehouse) → Python/ML → FastAPI → D3.js
                                                                    ↘ Power Automate
```

## Documentación

| Documento | Contenido |
|---|---|
| [docs/plan.md](docs/plan.md) | Plan maestro: arquitectura, decisiones, sprints, MVP |
| [docs/testing.md](docs/testing.md) | Estrategia de tests (unit, integración, Playwright E2E) |
| [docs/dev-environment.md](docs/dev-environment.md) | Docker, CI, nvm, venv, VS Code, buenas prácticas |
| [docs/database.md](docs/database.md) | Comandos de operación de PostgreSQL (migraciones, psql, GUI, reset) |
| [docs/git-workflow.md](docs/git-workflow.md) | Ramas, tags y releases (main/develop/feature) |
| [docs/harness.md](docs/harness.md) | Agentes, skills y MCP del proyecto |
| [docs/harness-install.md](docs/harness-install.md) | Instalar el harness en otro host |
| [docs/changelog.md](docs/changelog.md) | Registro de cada cambio realizado |

## Reglas de trabajo

1. Cambios **pequeños e incrementales**: el usuario revisa antes de continuar.
2. **Cada cambio se documenta** en `docs/changelog.md`.
3. **Cada cambio incluye sus tests** (nada está "hecho" sin tests).
4. En desarrollo se usan ventanas de datos pequeñas (1 mes → 1 año → histórico).

## Stack

n8n · PostgreSQL 16 · Python 3.12 · FastAPI · D3.js · Playwright · Power Automate · pytest

## Estado

Sprint 6 completado (FastAPI con OpenAPI docs: `/api/health`,
`/api/crimes/summary|trends|by-type|by-community-area|hotspots` y
`/api/reports/weekly` para Power Automate; 16 tests con TestClient +
DB de pruebas, paso `test-api` en el CI). Release: `v0.6.0`. Próximo
paso: **Sprint 7 — D3 Dashboard** (KPI cards, charts, heatmap y mapa
coroplético consumiendo la API).

Antes de empezar, instala el entorno siguiendo
[docs/dev-environment.md](docs/dev-environment.md) §7 (Docker Desktop, Node
vía nvm, venv de Python).

Ver [docs/plan.md](docs/plan.md) para el roadmap completo.

## Datos fuente

- [Crimes - 2001 to Present](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)
- [Boundaries - Community Areas](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6)
- [Socrata API docs](https://dev.socrata.com/docs/)
