# Estrategia de Tests

El proyecto tiene tres niveles de tests, alineados con la pirámide clásica:

```text
        /  E2E  \        Playwright — dashboard completo (pocos, lentos, realistas)
       /─────────\
      / Integración \    pytest + DB de prueba + TestClient — API, SQL, ingesta (medios)
     /───────────────\
    /    Unitarios    \  pytest — funciones puras de Python (muchos, rápidos)
   ─────────────────────
```

Regla general: **cada cambio de código viene acompañado de sus tests**. Un
cambio sin tests no se considera terminado.

---

## 1. Tests unitarios (pytest)

**Alcance:** funciones puras, sin red ni base de datos.

| Módulo | Qué se testea | Ejemplos |
|---|---|---|
| `python/src/ingestion/` | parsing/validación de registros Socrata | fecha válida, coords en rango, id duplicado detectado |
| `python/src/features/` | construcción de features | lag de 1 semana correcto, misma semana año anterior, sin lookahead (leakage) |
| `python/src/models/` | helpers del modelo | etiqueta hotspot binaria, split temporal respeta cronología |
| `api/app/services/` | lógica de negocio | cálculo WoW change, formato de semana ISO |

**Convenciones:**
- Framework: `pytest` con fixtures.
- Estructura: `tests/unit/test_<modulo>.py`.
- Nombrar tests por comportamiento: `test_rejects_latitude_out_of_range`.
- Un test = un comportamiento. Si un test falla, se sabe exactamente qué rompió.

```python
# ejemplo
def test_rejects_latitude_out_of_range():
    record = {"latitude": 999, "longitude": -87.6, "id": "X1"}
    assert validate_record(record) is None  # o lanza ValidationError
```

## 2. Tests de integración (pytest + Docker)

**Alcance:** código contra dependencias reales (PostgreSQL), pero aislado.

### 2.1 Base de datos
- Postgres de prueba en Docker (puerto distinto, ej. `5433`), esquema efímero.
- Se testean **migrations** (se aplican en orden y son idempotentes), seeds,
  constraints (UNIQUE, NOT NULL, CHECK), y el resultado de las vistas
  analíticas contra fixtures conocidos (ej: 100 crímenes semilla →
  `vw_monthly_crimes` debe devolver exactos valores calculados a mano).

### 2.2 FastAPI
- `TestClient` / `httpx.AsyncClient` con override de la dependencia de DB
  hacia la base de prueba.
- Cada endpoint: 200 con datos, 404/422 en casos límite, shape del JSON
  según el schema Pydantic.

### 2.3 Calidad de datos (data tests)
Sobre `raw.crimes` y `fact_crime` cargados con datos semilla o con 1 mes real:
- `id` NOT NULL y UNIQUE
- `date` NOT NULL
- `latitude BETWEEN -90 AND 90`, `longitude BETWEEN -180 AND 180`
- `community_area` en valores válidos (0–77 / catálogo)
- métricas: `null_rate`, `duplicate_rate`, `invalid_coordinates`

### 2.4 n8n
n8n no se testea unitariamente. Se verifica:
1. El workflow exportado (`n8n/workflows/*.json`) existe y es válido.
2. Ejecución manual contra 1 mes de datos → revisar `pipeline_runs` y los
   conteos en `raw.crimes` (esto lo puede automatizar un script de smoke test
   que compruebe la fila de log del run).

## 3. Tests E2E — Playwright (dashboard)

Playwright **sí es la herramienta correcta** para este proyecto: automatiza
un navegador real (Chromium/Firefox/WebKit), y es ideal para validar el
dashboard D3, que no se puede testear con pytest.

### 3.1 Ruta de aprendizaje (antes de escribir tests del proyecto)

| Paso | Qué aprender | Recurso |
|---|---|---|
| 1 | Instalación y primer test en 5 min | https://playwright.dev/python/docs/intro |
| 2 | Selectores (texto, CSS, data-testid) y auto-waiting | docs → "Locators" |
| 3 | Assertions (`expect(...)`) | docs → "Assertions" |
| 4 | Fixtures y organización (pytest plugin incluido) | docs → "Test runner" |
| 5 | Config: `playwright.config`, base URL, traces en fallo | docs → "Configuration" |

**Ejercicio práctico inicial (Sprint 8, día 1):** crear
`dashboard/e2e/test_smoke.py` que abre `http://localhost:5173` (o el servidor
estático) y verifica que el título "Chicago Crime Analytics" es visible. Con
eso ya se domina el ciclo install → run → report.

Nota de naming (ajustada al estrenar Sprint 8): pytest NO recoge archivos
`*.spec.py` (los interpreta como módulos dot: `smoke.spec` → import falla);
la convención efectiva es `test_*.py` como en todo el repo.

### 3.2 Tests E2E del dashboard (una vez aprendido)

```text
dashboard/e2e/
├── test_smoke.py           # la app carga, título y KPI cards visibles
├── test_filters.py         # filtrar por tipo de crimen actualiza gráficos
├── test_trends.py          # el line chart renderiza N puntos, tooltip en hover
├── test_heatmap.py         # celdas día×hora existen y cambian con filtro de mes
├── test_map.py             # el SVG del mapa tiene 77 paths de community areas
└── test_hotspots.py        # panel observado vs predicho visible
```

- Convención: usar `data-testid` en el HTML del dashboard para selectores
  estables.
- El E2E corre contra: dashboard servido localmente + **FastAPI real con la
  DB de prueba sembrada** (no mocks de red salvo que la API falle).
- Playwright en modo UI (`pytest --headed`) mientras se desarrolla, headless
  en CI.

### 3.3 Cuándo NO usar Playwright
- Para la API: no, se usa TestClient (más rápido y determinista).
- Para la lógica Python: no, se usa pytest puro.
- Playwright solo para lo que vive en el navegador.

## 4. Comandos (se irán llenando por sprint)

| Suite | Comando | Estado |
|---|---|---|
| Unit (python) | `pytest python/tests/unit` | Sprint 2+ |
| Integration (db) | `pytest python/tests/integration` | Sprint 1 ✅ |
| Integration (api) | `pytest api/tests` | Sprint 6 |
| E2E (dashboard) | `pytest dashboard/e2e` | Sprint 8 |

**Previo a los tests de integración:** levantar la DB de pruebas
(ver [docs/database.md](database.md) §9):

```powershell
docker compose -f docker-compose.test.yml up -d
.\.venv\Scripts\python.exe -m pytest python/tests/integration -v
```

bash (Linux/macOS), con el venv activado:

```bash
docker compose -f docker-compose.test.yml up -d
pytest python/tests/integration -v
```

## 5. Cobertura esperada

- No perseguir 100%. Objetivo pragmático:
  - **Unit:** alta cobertura en validación/features (aquí viven los bugs caros).
  - **Integration:** cada vista SQL y cada endpoint cubiertos por al menos un
    happy path + un caso límite.
  - **E2E:** ~6–10 flujos críticos del dashboard.
