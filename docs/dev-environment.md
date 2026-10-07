# Entorno de desarrollo e ingeniería de software

Guía de las herramientas de ingeniería que usa este proyecto: qué es cada
una, para qué sirve aquí, y su link principal. Respuesta rápida:

| ¿Usa? | Qué |
|---|---|
| Docker | **Sí** — PostgreSQL + n8n via `docker-compose.yml` (Sprint 1) |
| CI | **Sí** — GitHub Actions: lint + tests en cada push (Sprint 1+) |
| CD | **No** — no hay servidor de producción; lo más parecido sería publicar el dashboard en GitHub Pages (opcional, v2) |
| nvm | **Sí** — para gestionar Node.js (versión LTS) |
| venv | **Sí** — entorno virtual Python para python/ y api/ |
| VS Code | **Sí** — extensiones recomendadas via `.vscode/extensions.json` |

---

## 1. Docker y Docker Compose

**Qué es:** Docker empaqueta software en *contenedores* (procesos aislados
que siempre corren igual en cualquier máquina). Docker Compose define
múltiples contenedores en un solo archivo YAML (`docker-compose.yml`) y los
levanta con un comando.

**Para qué aquí:** PostgreSQL 16 y n8n corren como contenedores → no hay que
instalar Postgres ni n8n a mano en Windows, y el entorno es reproducible en
cualquier host. Además la DB de tests corre en el puerto 5433 en otro
contenedor.

```bash
docker compose up -d      # levanta todo (Sprint 1)
docker compose down       # apaga todo
docker compose ps         # estado de los contenedores
```

Windows: instalar **Docker Desktop** — https://docs.docker.com/desktop/
Conceptos: https://docs.docker.com/get-started/
Compose: https://docs.docker.com/compose/

## 2. CI con GitHub Actions

**Qué es:** CI (Integración Continua) = cada vez que haces `push` (o abres
un PR), un servidor de GitHub ejecuta automáticamente lint + tests sobre tu
código. GitHub Actions es el servicio de CI incluido en GitHub: se configura
con YAML en `.github/workflows/ci.yml` (gratis para repos públicos).

**Para qué aquí:** nada de "en mi máquina funciona": cada push verifica que
los tests pasan. La suite crece con el proyecto:

| Sprint | CI ejecuta |
|---|---|
| 1 | `ruff` (lint) + tests unit + migration check |
| 2+ | tests de integración (con un contenedor Postgres como *service*) |
| 8 | Playwright E2E |

CD (Despliegue Continuo) **no aplica**: no hay entorno de producción al que
desplegar — n8n/Postgres/dashboard corren local. Si en el futuro quieres
algo parecido: publicar el dashboard en GitHub Pages (acción `deploy-pages`)
— opcional, fuera del alcance actual.

Docs: https://docs.github.com/en/actions

## 3. nvm (en Windows: nvm-windows)

**Qué es:** gestor de versiones de Node.js. Permite tener varias versiones
de Node instaladas y cambiar entre ellas (`nvm install 20.11.0`,
`nvm use 20.11.0`). En Windows el estándar es **nvm-windows** (el nvm
original es para Mac/Linux).

**Para qué aquí:** los MCP (Context7, Playwright) y luego el build del
dashboard necesitan Node ≥ 20 (recomendado: **22 LTS**, la versión fijada en
`.nvmrc`). Con nvm instalas/actualizas Node sin romper otras cosas.

```powershell
nvm install 22         # versión fijada en .nvmrc
nvm use 22
node --version
```

Link: https://github.com/coreybutler/nvm-windows

## 4. Entorno virtual de Python (venv)

**Qué es:** un directorio aislado (`.venv/`) con su propia copia de Python y
sus librerías. Evita ensuciar el Python global y garantiza que todos usan
las mismas versiones (se declaran en `requirements.txt`).

**Para qué aquí:** librerías del proyecto (pandas, scikit-learn, FastAPI,
pytest...) se instalan solo dentro del venv, nunca en el Python global.

> **Versión fijada: Python 3.12.** Tu host trae 3.14, pero `pandas`, `numpy`
> y `scikit-learn` pueden no tener wheels para 3.14 todavía. Instala Python
> 3.12 (https://www.python.org/downloads/) y crea el venv con esa versión
> para no pelear con dependencias en el Sprint 5.

```powershell
# en Windows usa el launcher `py` para elegir la versión:
py -3.12 --version

# crear el venv con 3.12 (una sola vez, en la raíz)
py -3.12 -m venv .venv

# activar en PowerShell (cada sesión nueva)
.\.venv\Scripts\Activate.ps1

# si PowerShell bloquea scripts:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# verificar que el venv usa 3.12
python --version

# instalar/actualizar dependencias (Sprint 1 en adelante)
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Docs: https://docs.python.org/3/tutorial/venv.html
Alternativa moderna (opcional, más rápida): `uv` — https://docs.astral.sh/uv/

## 5. Extensiones de VS Code (recomendadas en `.vscode/extensions.json`)

VS Code detecta el archivo y te ofrece instalarlas todas con un clic
(pestaña Extensions → "Recommended").

| Extensión | Para qué | Link |
|---|---|---|
| Python + Pylance | soporte Python + autocompletado con tipos | https://marketplace.visualstudio.com/items?itemName=ms-python.python |
| Ruff | linter + formatter de Python (el que usará el CI) | https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff |
| Docker | manejar contenedores desde VS Code | https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-docker |
| Jupyter | correr los notebooks EDA | https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter |
| SQLTools + driver PostgreSQL | explorar la DB (tablas, queries) | https://marketplace.visualstudio.com/items?itemName=mtxr.sqltools |
| Playwright Test for VS Code | correr/debuggear tests E2E con UI | https://marketplace.visualstudio.com/items?itemName=ms-playwright.playwright |
| GitLens | historial git/blame en el editor | https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens |
| YAML | esquemas para compose/GitHub Actions | https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml |
| REST Client | probar endpoints FastAPI desde `.http` | https://marketplace.visualstudio.com/items?itemName=humao.rest-client |
| EditorConfig | respeta `.editorconfig` | https://editorconfig.org/ |

## 6. Otras prácticas de ingeniería adoptadas

| Práctica | Qué es | Link |
|---|---|---|
| `.gitignore` | excluye del git lo que no se commitea (`.env`, `.venv/`, `node_modules/`, caches) | https://git-scm.com/docs/gitignore |
| `.env` + `.env.example` | secretos/credenciales locales nunca al git; el `.example` documenta qué variables existen | https://12factor.net/config |
| Ruff | lint + format de Python (una sola herramienta, la usará el CI) | https://docs.astral.sh/ruff/ |
| EditorConfig | convención de indentación/finales de línea compartida por todos los editores | https://editorconfig.org/ |
| Conventional Commits | formato estándar de mensajes de commit (`feat:`, `fix:`...) | https://www.conventionalcommits.org/ |
| pre-commit (opcional, Sprint 2+) | hooks que corren lint antes de cada commit | https://pre-commit.com/ |
| sqlfluff (opcional, Sprint 3+) | linter de SQL para migrations/vistas | https://docs.sqlfluff.com/ |

## 7. Checklist de instalación del host (resumen)

1. Docker Desktop → https://docs.docker.com/desktop/ (reiniciar tras instalar)
2. nvm-windows → https://github.com/coreybutler/nvm-windows → `nvm install 22` (versión de `.nvmrc`)
3. Git → https://git-scm.com/ → `git config --global user.name` y `user.email`
4. **Python 3.12** → https://www.python.org/downloads/ → `py -3.12 -m venv .venv` + activar (ver §4)
5. Abrir VS Code en la raíz → aceptar extensiones recomendadas
6. `git init` + primer commit + remote (ver §8)
7. Verificar: `docker --version`, `node --version`, `py -3.12 --version`

## 8. Control de versiones (git) — cuándo empezamos

**Empezamos YA, antes del Sprint 1.** Razón: el primer commit ya captura todo
el planning (docs + harness + convenciones) y el CI de GitHub Actions
(Sprint 1) tiene un repo sobre el que correr.

```powershell
# una sola vez, en la raíz del proyecto
git init
git add .
git commit -m "chore: scaffold del proyecto (plan, harness, dev-env, convenciones)"

# crear el repo en GitHub (https://github.com/new) y conectarlo:
git remote add origin https://github.com/<tu-usuario>/crimen-chicago.git
git branch -M main
git push -u origin main
```

A partir de aquí, **cada paso revisable = un commit** con formato Conventional
Commits (`feat:`, `fix:`, `docs:`, `chore:`...). El archivo
`.github/workflows/ci.yml` se añade en el Sprint 1.
