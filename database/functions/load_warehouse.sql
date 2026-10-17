-- load_warehouse.sql — carga staging → warehouse (Sprint 3, Paso 4).
-- Regla del skill chicago-postgres: "warehouse SOLO se alimenta desde
-- staging". Todas las funciones son idempotentes: re-ejecutarlas refresca
-- sin duplicar (UPSERT por clave natural / crime_id).
--
-- Orden de la carga (el orquestador load_warehouse() lo respeta):
--   1. load_dim_date        (calendario generado, no viene de Socrata)
--   2. load_dim_crime_type  (iucr, primary_type, description)
--   3. load_dim_location    (block, location_description)
--   4. load_dim_district
--   5. load_fact_crime
-- (dim_community_area NO se carga desde staging: su source es el seed
--  database/seeds/community_areas.sql con los nombres oficiales.)
--
-- Contratos de la carga:
--   * Staging NULLifica '' (fix del contrato): no se crean miembros de dim
--     con textos vacíos; esa FK queda NULL en fact.
--   * Fact excluye filas sin date (crimen sin fecha no es representable).
--   * ON CONFLICT DO UPDATE en fact: re-cargar una ventana SOLAPADA aplica
--     las correcciones de Socrata (datos preliminares, skill ingestion).

CREATE OR REPLACE FUNCTION warehouse.load_dim_date(
    p_start DATE DEFAULT '2001-01-01',
    p_end   DATE DEFAULT '2030-12-31'
) RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    IF p_start >= p_end THEN
        RAISE EXCEPTION 'p_start (%) debe ser menor que p_end (%)', p_start, p_end;
    END IF;

    INSERT INTO warehouse.dim_date
        (date_key, full_date, year, month, month_name, week, day_of_week, day_name, is_weekend)
    SELECT
        to_char(d, 'YYYYMMDD')::INTEGER,
        d,
        EXTRACT(year FROM d)::SMALLINT,
        EXTRACT(month FROM d)::SMALLINT,
        CASE EXTRACT(month FROM d)::INT
            WHEN 1  THEN 'January'  WHEN 2  THEN 'February'
            WHEN 3  THEN 'March'    WHEN 4  THEN 'April'
            WHEN 5  THEN 'May'      WHEN 6  THEN 'June'
            WHEN 7  THEN 'July'     WHEN 8  THEN 'August'
            WHEN 9  THEN 'September' WHEN 10 THEN 'October'
            WHEN 11 THEN 'November' WHEN 12 THEN 'December'
        END,
        EXTRACT(week FROM d)::SMALLINT,
        EXTRACT(isodow FROM d)::SMALLINT,
        CASE EXTRACT(isodow FROM d)::INT
            WHEN 1 THEN 'Monday'   WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'   WHEN 6 THEN 'Saturday'
            WHEN 7 THEN 'Sunday'
        END,
        EXTRACT(isodow FROM d) >= 6
    FROM generate_series(p_start, p_end, INTERVAL '1 day') AS g(d)
    ON CONFLICT (date_key) DO NOTHING;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$$;

CREATE OR REPLACE FUNCTION warehouse.load_dim_crime_type() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    INSERT INTO warehouse.dim_crime_type (iucr, primary_type, description)
    SELECT DISTINCT s.iucr, s.primary_type, s.description
    FROM staging.crimes s
    WHERE s.primary_type IS NOT NULL
    ON CONFLICT (iucr, primary_type, description) DO NOTHING;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$$;

CREATE OR REPLACE FUNCTION warehouse.load_dim_location() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    INSERT INTO warehouse.dim_location (block, location_description)
    SELECT DISTINCT s.block, s.location_description
    FROM staging.crimes s
    WHERE s.block IS NOT NULL OR s.location_description IS NOT NULL
    ON CONFLICT (block, location_description) DO NOTHING;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$$;

CREATE OR REPLACE FUNCTION warehouse.load_dim_district() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    INSERT INTO warehouse.dim_district (district)
    SELECT DISTINCT s.district
    FROM staging.crimes s
    WHERE s.district IS NOT NULL
    ON CONFLICT (district) DO NOTHING;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$$;

CREATE OR REPLACE FUNCTION warehouse.load_fact_crime() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows INTEGER;
BEGIN
    INSERT INTO warehouse.fact_crime
        (crime_id, date_key, crime_type_key, location_key, community_area_key,
         district_key, hour, arrest, domestic, latitude, longitude)
    SELECT
        s.id,
        to_char(s.date, 'YYYYMMDD')::INTEGER,
        ct.crime_type_key,
        loc.location_key,
        ca.community_area_key,
        dist.district_key,
        EXTRACT(hour FROM s.date)::SMALLINT,
        s.arrest,
        s.domestic,
        s.latitude,
        s.longitude
    FROM staging.crimes s
    LEFT JOIN warehouse.dim_crime_type ct
        ON ct.iucr IS NOT DISTINCT FROM s.iucr
       AND ct.primary_type IS NOT DISTINCT FROM s.primary_type
       AND ct.description IS NOT DISTINCT FROM s.description
    LEFT JOIN warehouse.dim_location loc
        ON loc.block IS NOT DISTINCT FROM s.block
       AND loc.location_description IS NOT DISTINCT FROM s.location_description
    LEFT JOIN warehouse.dim_community_area ca
        ON ca.community_area = s.community_area
    LEFT JOIN warehouse.dim_district dist
        ON dist.district IS NOT DISTINCT FROM s.district
    WHERE s.date IS NOT NULL
    ON CONFLICT (crime_id) DO UPDATE SET
        date_key            = EXCLUDED.date_key,
        crime_type_key      = EXCLUDED.crime_type_key,
        location_key        = EXCLUDED.location_key,
        community_area_key  = EXCLUDED.community_area_key,
        district_key        = EXCLUDED.district_key,
        hour                = EXCLUDED.hour,
        arrest              = EXCLUDED.arrest,
        domestic            = EXCLUDED.domestic,
        latitude            = EXCLUDED.latitude,
        longitude           = EXCLUDED.longitude;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows;
END;
$$;

CREATE OR REPLACE FUNCTION warehouse.load_warehouse() RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    v_rows  INTEGER;
    v_total INTEGER := 0;
BEGIN
    v_rows := warehouse.load_dim_date();
    RAISE NOTICE 'dim_date: %', v_rows;
    v_total := v_total + v_rows;

    v_rows := warehouse.load_dim_crime_type();
    RAISE NOTICE 'dim_crime_type: %', v_rows;
    v_total := v_total + v_rows;

    v_rows := warehouse.load_dim_location();
    RAISE NOTICE 'dim_location: %', v_rows;
    v_total := v_total + v_rows;

    v_rows := warehouse.load_dim_district();
    RAISE NOTICE 'dim_district: %', v_rows;
    v_total := v_total + v_rows;

    v_rows := warehouse.load_fact_crime();
    RAISE NOTICE 'fact_crime: %', v_rows;
    v_total := v_total + v_rows;

    RETURN v_total;
END;
$$;
