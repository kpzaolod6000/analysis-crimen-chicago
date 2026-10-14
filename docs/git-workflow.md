# Flujo de trabajo Git — modelo de nvie (GitFlow)

**Fuente de práctica:** [A successful Git branching model](https://nvie.com/posts/a-successful-git-branching-model/)
(Vincent Driessen, 2010). Este doc adapta el modelo a este repo; no lo
reinventa. Dos adaptaciones conscientes:

1. **`main` en vez de `master`** (convención moderna de GitHub; mismo rol).
2. **Tags `vX.Y.Z`** (el artículo usa `1.2`; el prefijo `v` es el estándar
   de facto y lo usan los Releases de GitHub).

> Nota del propio autor (2020): GitFlow no es dogma; para software con
> *continuous delivery* recomienda GitHub Flow. Aquí sigue teniendo sentido
> porque el proyecto se libera **por versiones** (un tag por sprint), sin
> despliegue continuo: cada merge a `main` = un release verificado.

## 1. Idea central: descentralizado pero centralizado

`origin` (GitHub) es el repo de referencia. Todo lo demás (ramas
`feature/*`) vive primero local y se publica cuando se quiere compartir.
Aquí hay un solo desarrollador, así que `origin` sirve como respaldo + CI.

## 2. Ramas principales (permanentes)

| Rama | Rol |
|---|---|
| `main` | `HEAD` siempre refleja un estado **listo para producción**. Cada commit aquí es, por definición, un release → lleva **tag**. |
| `develop` | Integración: el último estado entregado para el **próximo** release. De aquí salen las ramas de soporte y aquí vuelve todo. |

`main` no recibe commits directos NUNCA: solo merges de `release-*`/`hotfix-*`.

## 3. Ramas de soporte (temporales)

| Tipo | Nace de | Va a | Naming |
|---|---|---|---|
| `feature/*` | `develop` | `develop` | libre (ej. `feature/sprint2-socrata-helper`) |
| `release-*` | `develop` | `main` **y** `develop` | `release-<versión>` (ej. `release-0.2.0`) |
| `hotfix-*` | `main` | `main` **y** `develop` | `hotfix-<versión>` (ej. `hotfix-0.1.1`) |

Reglas del artículo que adoptamos:

- **Siempre `--no-ff` al fusionar** features/release/hotfix: conserva la
  existencia histórica de la rama, agrupa sus commits y permite revertir la
  feature completa con un solo `git revert -m 1`.
- **La versión se asigna al crear la `release-*`**, no antes: hasta ese
  momento `develop` es "el próximo release" sin número decidido.
- En `release-*` solo fixes y metadata de release; **features nuevas
  prohibidas** (esperan al próximo release).
- En `hotfix-*`: fix mínimo urgente sobre un tag de producción.

## 4. Feature branch (un paso del plan)

```powershell
git checkout develop; git pull
git checkout -b feature/sprint2-socrata-helper develop
# ... commits (Conventional Commits), CI verde en la rama ...
git checkout develop
git merge --no-ff feature/sprint2-socrata-helper
git branch -d feature/sprint2-socrata-helper
git push origin develop
```

Con remote, el mismo ciclo se puede hacer vía PR hacia `develop`
(la rama sí se publica) — el merge debe ser **--no-ff** igual.
Opcional: `git config --global merge.ff false` no se recomienda global;
el flag explícito es más claro.

## 5. Release branch (cierre de sprint)

Cuando `develop` tiene todo lo que va en el sprint:

```powershell
# 1. crear la rama y "bump" de versión (aquí se decide el número)
git checkout -b release-0.2.0 develop
# bump aquí = marcar [x] el sprint en docs/plan.md + entrada final en
# docs/changelog.md (no hay versión en código que mantener aún)
git add -A; git commit -m "chore: bump version to 0.2.0"

# 2. si aparecen bugs: fixes aquí (nunca features)

# 3. terminar el release
git checkout main
git merge --no-ff release-0.2.0
git tag -a v0.2.0 -m "Sprint 2: ingesta Socrata -> raw.crimes"

git checkout develop
git merge --no-ff release-0.2.0        # los fixes vuelven a develop
git branch -d release-0.2.0
git push origin main develop --tags
```

## 6. Hotfix branch (fix urgente en "producción")

Aquí "producción" = el último tag de `main` (lo que otro host estaría
reproduciendo). Nace de `main` (o del tag), bump de PARCHE:

```powershell
git checkout -b hotfix-0.1.1 main
# fix + commit(s)
git checkout main
git merge --no-ff hotfix-0.1.1
git tag -a v0.1.1 -m "hotfix: ..."
git checkout develop
git merge --no-ff hotfix-0.1.1
git branch -d hotfix-0.1.1
git push origin main develop --tags
```

**Excepción del artículo:** si existe una `release-*` abierta, el hotfix se
fusiona a esa rama (no a `develop`); llegará a `develop` cuando el release
termine. (Si `develop` lo necesita ya, se puede fusionar a ambas.)

## 7. Tags (SemVer)

`vMAYOR.MENOR.PARCHE` — MAYOR `0` = desarrollo inicial; PARCHE solo para
hotfixes. Un tag por release en `main`, siempre anotados (`-a`):

| Release | Tag |
|---|---|
| Sprint 1 | `v0.1.0` |
| Sprint 2 | `v0.2.0` |
| ... | `v0.N.0` |
| Sistema completo (Sprint 10) | `v1.0.0` |

Ver: `git tag` · detalle: `git show v0.1.0` · GitHub Releases se crean desde
cada tag cuando exista el remote.

## 8. CI y ramas (GitHub Actions)

`.github/workflows/ci.yml` — workflow **`ci`**, job `lint-and-test`:

- **Triggers:** push a `main`, `develop` y `feature/**`; y PRs hacia
  `main`/`develop`. Con el trigger de `feature/**`, cada push de tu rama se
  valida ANTES del merge — no descubres el rojo al abrir el PR.
- **Entorno:** `ubuntu-latest`, Python 3.12, dependencias de
  `python/requirements.txt` + `requirements-dev.txt`.
- **Pasos:**
  1. `make lint` → `ruff check python`
  2. `make test-integration` → pytest contra un **servicio Postgres 16 de
     GitHub** en el puerto 5433 (misma convención que `docker-compose.test.yml`
     local; las migraciones las aplican los tests, no hay paso de migrate).
- **Dónde verlo:** GitHub → pestaña *Actions* → run "ci" por cada commit.

Reglas:

- Ningún merge a `develop` ni a `main` con CI rojo.
- **Ruff sin config y sin fijar:** no hay `ruff.toml`/`pyproject.toml` y
  `requirements-dev.txt` instala `ruff>=0.8` (flotante) → el CI siempre
  lintea con la ÚLTIMA ruff y tu ruff local puede ir atrás. Ese drift fue el
  caso real del hotfix `v0.2.1` (RUF100: local verde, CI rojo). Mitigación
  propuesta: fijar versión exacta en `requirements-dev.txt`.
- Al crear el remote: proteger `main` en GitHub (Settings → Branches →
  Add rule): require PR + status checks (`ci`) + no bypass.
  (El artículo no habla de PRs —son de la era pre-GitHub-flow—, pero la
  protección de `main` es la materialización moderna de "main = releases".)

## 9. Estado actual y estreno del modelo

`develop` existe (creada desde `main` en el commit del Paso 3). El Paso 4
(Makefile + CI) sigue sin commitear en `main`; para estrenar el modelo:

```powershell
# 1. commitear el Paso 4 y liberar el Sprint 1 (esto es un mini-release):
git add -A; git commit -m "feat: add Makefile and CI closing Sprint 1"
git tag -a v0.1.0 -m "Sprint 1: fundaciones (infra, raw.crimes, tests, Makefile, CI)"

# 2. sincronizar develop con main (develop no tiene releases propios aún):
git checkout develop; git merge --no-ff main

# 3. el Sprint 2 ya nace como feature desde develop (ver §4):
git checkout -b feature/sprint2-socrata-helper develop
```

## 10. Cheat sheet — comandos por escenario

Referencia rápida del día a día. `git switch` = la forma moderna de
`git checkout <rama>` (idéntica para cambiar/crear ramas). El CI corre en
**cada push** (main, develop y `feature/**`) — ver §8.

### 10.1 Empezar un paso del sprint (rama desde `develop`)

```powershell
git switch develop
git pull
git switch -c feature/sprint3-staging develop
```

### 10.2 Guardar avance (repetir cuantas veces haga falta)

```powershell
git status --short
git add python/ docs/          # o los archivos específicos
git commit -m "feat: ..."      # Conventional Commits: feat/fix/chore/docs/ci
git push -u origin feature/sprint3-staging   # 1a vez; luego: git push
```

### 10.3 Terminar un paso (ya revisado y verificado)

```powershell
git switch develop
git merge --no-ff feature/sprint3-staging
git branch -d feature/sprint3-staging
git push origin develop
git push origin --delete feature/sprint3-staging   # opcional: borrar la remota
```

### 10.4 Cierre de sprint (release, versión MENOR)

```powershell
git switch develop; git pull
git switch -c release-0.3.0
# bump: [x] del sprint en docs/plan.md + entrada de cierre en docs/changelog.md
git add -A; git commit -m "chore: bump version to 0.3.0"
git switch main
git merge --no-ff release-0.3.0
git tag -a v0.3.0 -m "Sprint 3: data warehouse"
git switch develop
git merge --no-ff release-0.3.0   # "Already up to date" = normal
git branch -d release-0.3.0
git push origin main develop --tags
```

### 10.5 Bug en el último tag ("producción") — hotfix, versión PARCHE

```powershell
git switch -c hotfix-0.3.1 main     # SIEMPRE desde main, nunca desde develop
# fix + su entrada en docs/changelog.md (+ checklist en docs/verification.md)
git add python/ docs/
git commit -m "fix: ..."
git switch main
git merge --no-ff hotfix-0.3.1
git tag -a v0.3.1 -m "hotfix: ..."
git switch develop
git merge --no-ff hotfix-0.3.1      # el fix no se pierde para el próximo sprint
git branch -d hotfix-0.3.1
git push origin main develop --tags
```

### 10.6 ¿Qué rama creo? (decisión en 5 segundos)

| Escenario | Rama | Nace de | Tag |
|---|---|---|---|
| Paso del sprint | `feature/*` | `develop` | — |
| Cierre de sprint | `release-X.Y.0` | `develop` | MENOR `vX.Y.0` |
| Bug en un tag existente | `hotfix-X.Y.Z` | **`main`** | PARCHE `vX.Y.Z` |

### 10.7 Si el CI sale rojo

1. GitHub → pestaña *Actions* → run fallido → abrir el step rojo y leer el log.
2. Rojo en push de `feature/*` o `develop` (sin tag): corregir con un commit
   nuevo en la misma rama (o en una ramita) y push. Nunca mergear con rojo.
3. Rojo en `main` YA taggeado: `hotfix-X.Y.(Z+1)` desde `main` (caso real:
   `v0.2.0` rojo por RUF100 → `v0.2.1`, ver changelog).

### 10.8 Inspección (para saber dónde estás)

```powershell
git status --short
git log --oneline --graph --all -10
git branch -a
git tag -l; git show v0.2.1
```
