-- 004_dims_fact.sql — warehouse dimensional (Sprint 3, Paso 2).
-- Skill chicago-postgres: claves surrogadas `<entidad>_key`, `crime_id`
-- natural como UNIQUE en fact. El warehouse SOLO se alimenta desde staging
-- (la carga llega en el Paso 4); esta migración es solo DDL.
-- Idempotente (IF NOT EXISTS) como todas las migraciones.

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ── dim_date ─────────────────────────────────────────────────────────────
-- date_key surrogada yyyymmdd (Kimball): legible, ordenable y joinable.
-- day_of_week ISO (lunes=1..domingo=7); week = semana ISO del año.
-- month_name/day_name se generan con CASE fijo en la carga (determinista,
-- sin depender del locale del servidor). La población llega en el Paso 4.
CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key     INTEGER PRIMARY KEY,              -- yyyymmdd (ej. 20260915)
    full_date    DATE NOT NULL UNIQUE,
    year         SMALLINT NOT NULL,
    month        SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name   TEXT NOT NULL,
    week         SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name     TEXT NOT NULL,
    is_weekend   BOOLEAN NOT NULL
);

-- ── dim_crime_type ───────────────────────────────────────────────────────
-- Grano: combinación (iucr, primary_type, description) tal como llega de
-- Socrata (un mismo iucr puede variar de description a lo largo de los años).
CREATE TABLE IF NOT EXISTS warehouse.dim_crime_type (
    crime_type_key  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    iucr            TEXT,
    primary_type    TEXT NOT NULL,
    description     TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_crime_type_natural
    ON warehouse.dim_crime_type (iucr, primary_type, description) NULLS NOT DISTINCT;

-- ── dim_location ─────────────────────────────────────────────────────────
-- Grano: (block, location_description). Las coordenadas viven degeneradas
-- en fact_crime (varían por evento, no por ubicación).
CREATE TABLE IF NOT EXISTS warehouse.dim_location (
    location_key          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    block                 TEXT,
    location_description  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dim_location_natural
    ON warehouse.dim_location (block, location_description) NULLS NOT DISTINCT;

-- ── dim_district ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warehouse.dim_district (
    district_key  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    district      SMALLINT NOT NULL UNIQUE
);

-- ── dim_community_area ───────────────────────────────────────────────────
-- Los nombres de las 77 áreas llegan con el seed (Paso 3, dataset cauq-8yn6).
CREATE TABLE IF NOT EXISTS warehouse.dim_community_area (
    community_area_key   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    community_area       SMALLINT NOT NULL UNIQUE,  -- 1-77 (0/NULL = unknown en staging)
    community_area_name  TEXT                        -- se rellena con el seed
);

-- ── fact_crime ───────────────────────────────────────────────────────────
-- Un registro = un crimen. date_key NOT NULL: un crimen sin fecha no entra
-- a fact (la carga lo filtra). Las demás FKs son NULLables (datos faltantes
-- legítimos: community_area en registros viejos, etc.).
CREATE TABLE IF NOT EXISTS warehouse.fact_crime (
    crime_key           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crime_id            TEXT NOT NULL UNIQUE,       -- id natural de Socrata
    date_key            INTEGER NOT NULL REFERENCES warehouse.dim_date (date_key),
    crime_type_key      INTEGER REFERENCES warehouse.dim_crime_type (crime_type_key),
    location_key        INTEGER REFERENCES warehouse.dim_location (location_key),
    community_area_key  INTEGER REFERENCES warehouse.dim_community_area (community_area_key),
    district_key        INTEGER REFERENCES warehouse.dim_district (district_key),
    hour                SMALLINT CHECK (hour BETWEEN 0 AND 23),
    arrest              BOOLEAN,
    domestic            BOOLEAN,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION
);

-- Índices solo en las FKs de filtro/agrupación frecuente (sin sobre-indexar).
CREATE INDEX IF NOT EXISTS idx_fact_crime_date ON warehouse.fact_crime (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_crime_community_area ON warehouse.fact_crime (community_area_key);
CREATE INDEX IF NOT EXISTS idx_fact_crime_crime_type ON warehouse.fact_crime (crime_type_key);
