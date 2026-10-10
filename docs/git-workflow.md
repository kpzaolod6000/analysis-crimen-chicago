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

## 8. CI y ramas

`.github/workflows/ci.yml` corre en push a `main`/`develop` y en PRs hacia
ambas. Reglas:

- Ningún merge a `develop` ni a `main` con CI rojo.
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
