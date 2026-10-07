CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE TABLE IF NOT EXISTS raw.crimes (
    id                   TEXT PRIMARY KEY,
    case_number          TEXT,
    date                 TIMESTAMP,
    block                TEXT,
    iucr                 TEXT,
    primary_type         TEXT,
    description          TEXT,
    location_description TEXT,
    arrest               BOOLEAN,
    domestic             BOOLEAN,
    beat                 INTEGER,
    district             INTEGER,
    ward                 INTEGER,
    community_area       INTEGER,
    fbi_code             TEXT,
    x_coordinate         DOUBLE PRECISION,
    y_coordinate         DOUBLE PRECISION,
    year                 INTEGER,
    updated_on           TIMESTAMP,
    latitude             DOUBLE PRECISION,
    longitude            DOUBLE PRECISION,
    location             JSONB,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_crimes_date ON raw.crimes (date);
