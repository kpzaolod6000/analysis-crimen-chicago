-- 002_operational.sql — capa operacional: log de runs del pipeline.
-- Referencia: skill chicago-postgres (pipeline_runs) y plan.md §6.
-- Idempotente (IF NOT EXISTS) como todas las migraciones.

CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workflow_name     TEXT NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ,
    status            TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED')),
    window_start      TIMESTAMP,
    window_end        TIMESTAMP,
    records_received  INTEGER,
    records_inserted  INTEGER,
    records_updated   INTEGER,
    records_failed    INTEGER,
    error_message     TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON ops.pipeline_runs (started_at DESC);
