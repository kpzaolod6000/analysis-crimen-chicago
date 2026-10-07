# Base de datos — comandos de operación

Referencia reutilizable para operar PostgreSQL en **cualquier host** (tu PC,
otro equipo o un servidor). Incluye versiones para **PowerShell** (Windows) y
**bash** (Linux/macOS). Asumen que estás en la raíz del proyecto (donde vive
`docker-compose.yml`).

> La migración `001_raw.sql` es idempotente (`IF NOT EXISTS`): puedes
> re-ejecutarla sin duplicar nada. Todas las migraciones deben seguir esa regla.

---

## 1. Datos de conexión

| Desde dónde | Host | Puerto | Usuario | DB |
|---|---|---|---|---|
| Dentro de la red Docker (n8n, otros contenedores) | `postgres` | 5432 | del `.env` | del `.env` |
| Tu PC (terminal, VS Code, GUI) | `localhost` | 5432 | del `.env` | del `.env` |
| Otro servidor remoto | IP/dominio del servidor | 5432 (si está publicado) | del `.env` | del `.env` |

Credenciales de desarrollo (ver `.env` / `.env.example`):
`POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`,
`POSTGRES_DB=chicago_crimes`. **Nunca** usar estas credenciales en producción.

## 2. Levantar la base

```powershell
docker compose up -d          # arranca postgres + n8n
docker compose ps             # postgres debe quedar "healthy"
```

## 3. Aplicar migraciones

**Una migración concreta:**
```powershell
docker compose exec postgres psql -U postgres -d chicago_crimes -f /database/migrations/001_raw.sql
```
La ruta `/database/...` es **dentro del contenedor** (el compose monta
`./database:/database:ro`).

**Todas las migraciones en orden** (útil al configurar un host/servidor nuevo):

PowerShell:
```powershell
Get-ChildItem .\database\migrations\*.sql | Sort-Object Name | ForEach-Object {
  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f "/database/migrations/$($_.Name)"
}
```

bash (Linux/macOS):
```bash
for f in database/migrations/*.sql; do
  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f "/database/${f#database/}"
done
```

## 4. Consultar / ejecutar SQL

**Consulta suelta** (`-c`):
```powershell
docker compose exec postgres psql -U postgres -d chicago_crimes -c "SELECT count(*) FROM raw.crimes;"
```

**Shell interactivo** (`-it`), para escribir SQL a mano:
```powershell
docker compose exec -it postgres psql -U postgres -d chicago_crimes
```
Dentro, el prompt es `chicago_crimes=#`. Usar `\q` para salir.

## 5. Cheatsheet de meta-comandos de psql

| Comando | Qué hace |
|---|---|
| `\dn` | listar schemas |
| `\dt raw.*` | listar tablas de un schema |
| `\d raw.crimes` | describir una tabla (columnas, índices, constraints) |
| `\di` | listar índices |
| `\l` | listar bases de datos |
| `\i /database/migrations/001_raw.sql` | ejecutar un archivo desde dentro del shell |
| `\x` | alterar salida normal/expandida (cómodo con muchas columnas) |
| `\q` | salir |

## 6. Conectar desde una GUI (VS Code SQLTools / DBeaver / pgAdmin)

El puerto 5432 está publicado al host, así que cualquier cliente se conecta con:
`localhost:5432`, usuario/contraseña/DB del `.env`. En VS Code usar las
extensiones recomendadas **SQLTools + driver PostgreSQL**
(ver `.vscode/extensions.json`).

## 7. Reset completo de la base (⚠ borra TODOS los datos)

```powershell
docker compose down -v        # -v elimina los volúmenes (datos de postgres y n8n)
docker compose up -d
# y reaplicar migraciones (sección 3)
```
Solo en desarrollo. `-v` destruye los datos; sin `-v` solo apaga contenedores
pero conserva los volúmenes.

## 8. Apagar / limpiar

```powershell
docker compose stop           # apaga sin borrar
docker compose down           # apaga y quita contenedores (conserva volúmenes)
docker compose logs -f postgres   # ver logs en vivo
```
