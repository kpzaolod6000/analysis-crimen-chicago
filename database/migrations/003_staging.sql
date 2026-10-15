-- 003_staging.sql — capa staging: limpieza/normalización de raw.crimes
-- (skill chicago-postgres: staging limpia; raw nunca se modifica después
-- de cargar; warehouse solo se alimenta desde staging).
--
-- staging.crimes es una VIEW (no tabla): cero duplicación de datos, siempre
-- sincronizada con raw y la transformación queda en una sola sentencia SQL.
-- Idempotente vía CREATE OR REPLACE (misma lista de columnas en evoluciones).
--
-- Reglas de limpieza aplicadas (skill chicago-data-quality):
--   * texto: btrim + '' -> NULL (Socrata permite strings vacíos)
--   * coordenadas (0,0) -> NULL ambas (Socrata a veces emite origen nulo)
--   * coordenadas fuera de rango -> NULL ambas (defensa)
--   * coordenadas parciales (solo lat o solo lon) se conservan tal cual
--   * community_area fuera de 1..77 -> NULL (los 0 de registros viejos =
--     "unknown"; el catálogo oficial son 77 áreas, 1-77)
-- Los filtrados de filas (ej. date IS NULL) son decisión del warehouse al
-- poblar fact, no de staging.

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE VIEW staging.crimes AS
SELECT
    id,
    btrim(case_number)            AS case_number,
    date,
    btrim(block)                  AS block,
    btrim(iucr)                   AS iucr,
    btrim(primary_type)           AS primary_type,
    btrim(description)            AS description,
    btrim(location_description)   AS location_description,
    arrest,
    domestic,
    beat,
    district,
    ward,
    CASE
        WHEN community_area BETWEEN 1 AND 77 THEN community_area
        ELSE NULL
    END                           AS community_area,
    btrim(fbi_code)               AS fbi_code,
    x_coordinate,
    y_coordinate,
    year,
    updated_on,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL THEN latitude
        WHEN latitude NOT BETWEEN -90 AND 90
            OR longitude NOT BETWEEN -180 AND 180 THEN NULL::double precision
        WHEN latitude = 0 AND longitude = 0 THEN NULL::double precision
        ELSE latitude
    END                           AS latitude,
    CASE
        WHEN latitude IS NULL OR longitude IS NULL THEN longitude
        WHEN latitude NOT BETWEEN -90 AND 90
            OR longitude NOT BETWEEN -180 AND 180 THEN NULL::double precision
        WHEN latitude = 0 AND longitude = 0 THEN NULL::double precision
        ELSE longitude
    END                           AS longitude,
    location,
    loaded_at
FROM raw.crimes;
