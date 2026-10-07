# Harness de desarrollo (opencode + skills + MCP)

Este proyecto no solo usa opencode: tiene su propio **harness** de
agentes, skills y servidores MCP configurados alrededor del pipeline.
Este documento explica qué es cada pieza, para qué sirve, su link principal
y en qué sprint se usa.

> Prerrequisito pendiente en esta máquina: **Node.js LTS** (los MCP de
> Context7 y Playwright se lanzan con `npx`; Playwright/Vite también lo
> necesitarán en el frontend). Instalar desde https://nodejs.org/
> Tras cualquier cambio en `opencode.json`, agentes o skills hay que
> **reiniciar opencode** para que recargue la configuración.

---

## 1. Piezas y qué hace cada una

### Agentes personalizados (`.opencode/agent/`)

Agentes especializados que se invocan con `@nombre` o como subagentes.
Definen un rol, restricciones y apuntan a `docs/plan.md` y `AGENTS.md`.
Docs opencode: https://opencode.ai/docs/ — schema: https://opencode.ai/config.json

| Agente | Qué hace | Estado |
|---|---|---|
| `@architect` | Diseña/revisa decisiones de arquitectura antes de tocar código | creado |
| `@data-engineer` | Implementa Sprints 1–4: Docker, Postgres, ingesta, warehouse, SQL | creado |
| `@qa` | Revisa cada cambio: ¿tiene tests? ¿cubre casos límite? | creado |
| `@postgres` | Especialista SQL/migrations | Sprint 3 (cuando exista el warehouse) |
| `@data-scientist` | EDA, DBSCAN, features, predicción | Sprint 5 |
| `@backend` | FastAPI, schemas, servicios | Sprint 6 |
| `@frontend` | D3, mapa, filtros | Sprint 7 |
| `@devops` | CI, Docker, observabilidad | Sprint 10 |

No se crean los 8 el día 1: un agente solo es útil cuando las convenciones
de SU capa existen (si no, su prompt serían palabras vacías).

### Skills del proyecto (`.opencode/skills/`)

Instrucciones cargadas automáticamente cuando la tarea las necesita.
A diferencia de una colección pública, **codifican las reglas de ESTE
pipeline**: ids de datasets, capas de Postgres, ventanas de ingesta,
validaciones. Viven en `.opencode/skills/<nombre>/SKILL.md`.

| Skill | Qué contiene | Sprint |
|---|---|---|
| `chicago-postgres` | capas raw/staging/warehouse, naming, migrations idempotentes, modelo dimensional | 1–4 |
| `chicago-data-ingestion` | ids Socrata (`ijzp-q8t2`, `cauq-8yn6`), SoQL, paginación, ventanas, UPSERT, división n8n/Postgres | 2 |
| `chicago-data-quality` | validaciones por campo, métricas (null/duplicate rate), dónde viven los data tests | 2+ |
| `chicago-n8n` | convenciones de workflows (nodos, error flow, logging) | 2 |
| `chicago-data-science` | split temporal, features con lags, DBSCAN, evaluación | 5 |
| `chicago-fastapi` | estructura routers/services/schemas, TestClient | 6 |
| `chicago-d3-dashboard` | data-testid, estructura de charts, api.js | 7 |

(Las tres primeras están creadas; el resto se crea en su sprint.)

### Skills externas (opcional)

**Superpowers** — metodología completa de desarrollo para agentes (TDD
RED-GREEN-REFACTOR, debugging sistemático, escritura de planes) con soporte
oficial para OpenCode. https://github.com/obra/superpowers
Estado: **opcional, diferido**. Nuestro `AGENTS.md` + skills ya codifican la
metodología; instalar Superpowers añadiría solapamiento. Reevaluar en
Sprint 5+ si se quiere TDD estricto.

### Servidores MCP (en `opencode.json`)

Los MCP dan al agente herramientas extra (no texto: acciones reales).

| MCP | Qué hace | Link | Estado |
|---|---|---|---|
| **Context7** | Documentación actualizada de librerías (FastAPI, D3, scikit-learn, n8n) inyectada en el contexto, sin versiones desactualizadas | https://github.com/upstash/context7 | activo (requiere Node.js) |
| **Playwright** | El agente maneja un navegador real: navegar, click, screenshots, inspeccionar el DOM del dashboard mientras lo construimos | https://github.com/microsoft/playwright-mcp | activo (requiere Node.js) |
| **Postgres MCP Pro** | Consultas/explain/index-tuning sobre la DB **en modo restringido (solo lectura)** | https://github.com/crystaldba/postgres-mcp | definido, `enabled: false` hasta Sprint 1 |
| **n8n instance MCP** | n8n trae servidor MCP incorporado: crear/editar workflows de la instancia n8n local desde el agente | https://docs.n8n.io/connect/connect-to-n8n-mcp-server | Sprint 2 (requiere n8n corriendo + API key) |

## 2. Evaluación de la propuesta original (ranking del otro agente)

Acertado:
- Las **custom skills valen más que otra colección pública**: codifican
  reglas propias del pipeline. Confirmado.
- Estructura de carpetas (`.opencode/agent/`, `.opencode/skills/`) correcta
  según opencode.
- Playwright MCP y Postgres MCP: sí, valiosos.
- GitHub MCP: bajo — git + `gh` CLI ya lo cubren; sin repo aún, diferido.
- "n8n Docs MCP": existe una versión comunitaria, pero el camino correcto es
  el **MCP incorporado de la propia instancia n8n** (oficial, beta) que
  además permite crear workflows, no solo leer docs.

Correcciones importantes:
1. **Trampa PostgreSQL MCP**: el paquete
   `@modelcontextprotocol/server-postgres` (Anthropic) fue **archivado en
   julio 2025 tras descubrirse un SQL injection** (bypass con `;`). Sigue
   descargándose 21k/semana por tutoriales viejos. Hay que usar
   `crystaldba/postgres-mcp` (Postgres MCP Pro) con `--access-mode=restricted`.
   Fuente: https://github.com/crystaldba/postgres-mcp
2. **Context7 como #1 es discutible**: opencode ya busca en la web. Su valor
   aquí es doc de versiones exactas de librerías (útil, no crítico). Para
   este proyecto el núcleo real es: custom skills + agentes + Postgres MCP
   + Playwright MCP + n8n MCP.
3. **8 agentes + 7 skills + 6 MCPs el día 1 es over-engineering** (y
   contradice su propio consejo de "no instalar un montón de MCPs"): cada
   agente/skill se crea cuando su sprint define las convenciones que debe
   proteger. Aquí se crearon solo las piezas de los sprints cercanos
   (architect, data-engineer, qa + 3 skills) y el resto están planificados
   en la tabla de arriba.
4. `opencode.json` usa formato strict JSON (sin comentarios) y debe llevar
   `"$schema": "https://opencode.ai/config.json"`; `mcp.*.command` es
   **array de strings**, nunca string simple.

## 3. Qué se usa en cada paso del plan (resumen)

| Sprint | Se usa |
|---|---|
| 1 Fundaciones | `@data-engineer`, skills `chicago-postgres` + `chicago-data-ingestion`, Postgres MCP (activar), n8n MCP (activar) |
| 2 Ingesta | skill `chicago-data-ingestion`, skill `chicago-data-quality`, Context7 (docs n8n), `@qa` |
| 3–4 Warehouse + SQL | `@data-engineer`, skill `chicago-postgres`, Postgres MCP (explain/tuning de vistas) |
| 5 Python EDA + DBSCAN | `@data-scientist` (crear), skill `chicago-data-science` (crear), Context7 (pandas/sklearn) |
| 6 FastAPI | `@backend` (crear), skill `chicago-fastapi` (crear), Context7 (docs FastAPI) |
| 7 D3 Dashboard | `@frontend` (crear), skill `chicago-d3-dashboard` (crear), **Playwright MCP** (inspección en vivo del navegador), Context7 (docs D3) |
| 8 Playwright E2E | Playwright MCP + https://playwright.dev/python/docs/intro |
| 9 Power Automate | docs + `@architect` (revisión del flujo) |
| 10 ML Nivel 2 + backfill | skill `chicago-data-science`, `@qa` (leakage), `@devops` (crear) |

## 4. Cómo verificar esta configuración

> Para instalar este harness en otra máquina: [harness-install.md](harness-install.md)

1. Instalar Node.js LTS (https://nodejs.org/) y reiniciar opencode.
2. Comprobar que Context7 y Playwright MCP aparecen como servidores
   conectados en opencode.
3. Invocar `@qa` con "revisa el último cambio" para ver el agente en acción.
4. Al llegar al Sprint 1: instalar Postgres MCP Pro
   (`pipx install postgres-mcp`), poner `"enabled": true` en `opencode.json`
   y reiniciar.
