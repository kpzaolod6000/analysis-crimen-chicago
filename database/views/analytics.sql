-- analytics.sql — vistas analíticas del Sprint 4 (plan §6).
--
-- Principios (skill chicago-postgres):
--   * Agregaciones analíticas en VISTAS; la API nunca re-implementa SQL.
--   * Todas las vistas viven en el schema warehouse y se alimentan SOLO de
--     fact_crime + dims (nunca de raw/staging).
--   * Idempotentes vía CREATE OR REPLACE VIEW.
--   * Sin filtros de negocio (año/tipo): eso lo agrega el consumidor
--     (FastAPI) con WHERE sobre las columnas expuestas.
--   * Orden determinista en las que se consumen directamente
--     (vw_month_over_month); las otras quedan sin ORDER (el cliente pagina
--     filtra como quiera).
--
-- Cargados en dev/targets:
--   make views   # equivale a aplicar este archivo con psql

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ── vw_monthly_crimes ────────────────────────────────────────────────────
-- Tendencia mensual: crimes + arrests + tasa de arresto por mes calendarario.
-- (Socrata entrega hora local: month se saca de dim_date.full_date.)
CREATE OR REPLACE VIEW warehouse.vw_monthly_crimes AS
SELECT
    date_trunc('month', d.full_date)::date AS month_date,
    d.year,
    d.month,
    d.month_name,
    count(*)                          AS crime_count,
    count(*) FILTER (WHERE f.arrest)  AS arrest_count,
    round(100.0 * count(*) FILTER (WHERE f.arrest) / count(*), 1) AS arrest_rate_pct
FROM warehouse.fact_crime f
JOIN warehouse.dim_date d ON d.date_key = f.date_key
GROUP BY 1, 2, 3, 4;

-- ── vw_area_crime_ranking ────────────────────────────────────────────────
-- Ranking de community areas por crime count (RANK con empates: dos
-- empates en 1 -> rank 3 al siguiente). Excluye filas sin area (NULL):
-- no invaden el ranking del geo-dashboard.
CREATE OR REPLACE VIEW warehouse.vw_area_crime_ranking AS
SELECT
    ca.community_area,
    ca.community_area_name,
    count(*)                                           AS crime_count,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct,
    rank() OVER (ORDER BY count(*) DESC)               AS crime_rank
FROM warehouse.fact_crime f
JOIN warehouse.dim_community_area ca ON ca.community_area_key = f.community_area_key
GROUP BY ca.community_area, ca.community_area_name;

-- ── vw_month_over_month ──────────────────────────────────────────────────
-- MoM: crime_count vs mes anterior (LAG) con delta absoluto y porcentual.
-- La primera fila es NULL en prev/change (mes base sin período de comparar).
CREATE OR REPLACE VIEW warehouse.vw_month_over_month AS
WITH monthly AS (
    SELECT
        date_trunc('month', d.full_date)::date AS month_date,
        count(*) AS crime_count
    FROM warehouse.fact_crime f
    JOIN warehouse.dim_date d ON d.date_key = f.date_key
    GROUP BY 1
)
SELECT
    month_date,
    crime_count,
    lag(crime_count) OVER (ORDER BY month_date) AS prev_crime_count,
    crime_count - lag(crime_count) OVER (ORDER BY month_date) AS change_abs,
    round(100.0 * (crime_count - lag(crime_count) OVER (ORDER BY month_date))
          / lag(crime_count) OVER (ORDER BY month_date), 1) AS change_pct
FROM monthly
ORDER BY month_date;

-- ── vw_day_hour ──────────────────────────────────────────────────────────
-- Heatmap día-de-semana x hora (ISODOW: lunes=1..domingo=7, vía dim_date).
CREATE OR REPLACE VIEW warehouse.vw_day_hour AS
SELECT
    d.day_of_week,
    d.day_name,
    f.hour,
    count(*) AS crime_count
FROM warehouse.fact_crime f
JOIN warehouse.dim_date d ON d.date_key = f.date_key
GROUP BY d.day_of_week, d.day_name, f.hour;

-- ── vw_area_summary ──────────────────────────────────────────────────────
-- Resumen por community area (para KPI cards de area): volumen,
-- conteos de arrest/domestic, diversidad de tipos y rango de fechas
-- observado.
CREATE OR REPLACE VIEW warehouse.vw_area_summary AS
SELECT
    ca.community_area,
    ca.community_area_name,
    count(*)                              AS crime_count,
    count(*) FILTER (WHERE f.arrest)      AS arrest_count,
    count(*) FILTER (WHERE f.domestic)    AS domestic_count,
    count(DISTINCT f.crime_type_key)      AS crime_type_count,
    min(d.full_date)                      AS first_crime_date,
    max(d.full_date)                      AS last_crime_date
FROM warehouse.fact_crime f
JOIN warehouse.dim_community_area ca ON ca.community_area_key = f.community_area_key
JOIN warehouse.dim_date d ON d.date_key = f.date_key
GROUP BY ca.community_area, ca.community_area_name;
