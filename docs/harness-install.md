# Instalación del harness en otro host

Manifiesto portable de todo lo configurado en este proyecto (Sprint 0.5).
Permite replicar el harness (agentes + skills + MCP) en cualquier otra
máquina. Referencia de qué hace cada pieza: [harness.md](harness.md).

---

## 1. Qué es portable y qué no

| Pieza | ¿Viaja con el repo? | Cómo |
|---|---|---|
| Agentes (`@architect`, `@data-engineer`, `@qa`) | **Sí** | archivos `.md` en `.opencode/agent/` |
| Skills (`chicago-*`) | **Sí** | carpetas en `.opencode/skills/` con `SKILL.md` |
| MCP Context7 | **Sí** (config) | `opencode.json` la lanza con `npx`; el paquete se descarga solo |
| MCP Playwright | **Sí** (config) | igual: `npx -y @playwright/mcp` se descarga solo |
| MCP Postgres (Postgres MCP Pro) | Config sí, **binario no** | requiere `pipx install postgres-mcp` en el host |
| MCP n8n (instancia) | No (pendiente) | se configura en Sprint 2 contra la n8n local |
| Documentación (`docs/`, `AGENTS.md`) | **Sí** | archivos del repo |

Conclusión: **clonar/copiar el repo ya instala agentes, skills y la
configuración MCP**. Solo hay que instalar prerrequisitos en el host.

## 2. Prerrequisitos del host

| Requisito | Para qué | Cómo verificar | Link |
|---|---|---|---|
| opencode | el propio asistente | `opencode --version` | https://opencode.ai/docs/ |
| Node.js ≥ 20 LTS | lanzar MCPs con `npx` (Context7, Playwright) y luego Vite/Playwright | `node --version` | https://nodejs.org/ |
| Python ≥ 3.12 | proyecto + Postgres MCP Pro | `python --version` | https://www.python.org/ |
| pipx (Sprint 1) | instalar binario `postgres-mcp` | `pipx --version` | https://pipx.pypa.io/ |

En Windows, pipx: `python -m pip install --user pipx` y luego `python -m pipx ensurepath`.

## 3. Pasos de instalación

```bash
# 1. Clonar/copiar el repo (trae .opencode/ + opencode.json + docs/)
git clone <url-del-repo> && cd crimen-chicago

# 2. Instalar Node.js LTS (si falta) y reiniciar la terminal:
node --version

# 3. (Opcional ya, obligatorio en Sprint 1) Postgres MCP Pro:
pipx install postgres-mcp

# 4. Abrir opencode EN LA RAÍZ DEL PROYECTO:
opencode
```

opencode detecta automáticamente `opencode.json` y `.opencode/` del
directorio actual: no hay que registrar nada a mano.

## 4. Archivos que deben existir tras la copia (checklist)

```text
opencode.json                                    ← MCPs (Context7, Playwright activos; postgres disabled)
.opencode/agent/architect.md
.opencode/agent/data-engineer.md
.opencode/agent/qa.md
.opencode/skills/chicago-postgres/SKILL.md
.opencode/skills/chicago-data-ingestion/SKILL.md
.opencode/skills/chicago-data-quality/SKILL.md
AGENTS.md
docs/harness.md
docs/harness-install.md                          ← este archivo
```

## 5. Contenido de `opencode.json` (referencia rápida)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context7":  { "type": "local", "command": ["npx", "-y", "@upstash/context7-mcp"], "enabled": true },
    "playwright": { "type": "local", "command": ["npx", "-y", "@playwright/mcp"], "enabled": true },
    "postgres":  { "type": "local", "enabled": false,
                   "command": ["postgres-mcp", "--access-mode=restricted",
                               "postgresql://postgres:postgres@localhost:5432/chicago_crimes"] }
  }
}
```

Notas:
- `mcp.*.command` es **array de strings** (formato strict JSON, sin comentarios).
- La primera ejecución de `npx` descarga el paquete del MCP (por eso se pide Node ≥ 20).
- Context7 funciona sin API key (rate limit bajo); clave opcional en
  https://context7.com/dashboard → añadir `--api-key` al command.
- **NO** usar `@modelcontextprotocol/server-postgres` (archivado 2025-07 por
  SQL injection); usar Postgres MCP Pro. Ver [harness.md](harness.md) §2.

## 6. Activar lo diferido

| Cuándo | Qué hacer |
|---|---|
| Sprint 1 (exista la DB) | `pipx install postgres-mcp` → en `opencode.json` poner `"postgres": { ..., "enabled": true }` → reiniciar opencode |
| Sprint 2 (n8n corriendo) | Activar el MCP incorporado de n8n (docs: https://docs.n8n.io/connect/connect-to-n8n-mcp-server): crear API key en n8n y añadir la entrada `mcp.n8n` a `opencode.json` |
| Sprint 5+ (opcional) | Superpowers (metodología TDD/debugging): https://github.com/obra/superpowers — soporta OpenCode |

## 7. Verificación (checklist final)

1. `opencode` arranca sin errores de config (si falla el arranque por config
   rota: `OPENCODE_DISABLE_PROJECT_CONFIG=1` para editar y recuperar).
2. Context7 y Playwright aparecen como servidores MCP conectados.
3. Al escribir `@` en la sesión aparecen `architect`, `data-engineer`, `qa`.
4. Preguntar algo de SQL del proyecto y comprobar que cita la skill
   `chicago-postgres` (las skills se activan solas cuando aplica).
5. Tras cualquier cambio de config: **reiniciar opencode** (la config no se
   recarga en caliente).
