-- TTB Label Verification — canonical schema.
-- A copy lives at api/shared/schema.sql (packaged with the Functions app so the
-- API can run it idempotently on cold start). Keep the two files in sync.

CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- URLs point to the labels container (post-quality-check permanent storage)
    front_image_blob_url    TEXT NOT NULL,
    back_image_blob_url     TEXT NOT NULL,

    -- Set by retention_sweep when blobs are purged after 30 days.
    -- Application record is kept indefinitely; these flags confirm the image is gone.
    front_image_deleted     BOOLEAN NOT NULL DEFAULT FALSE,
    back_image_deleted      BOOLEAN NOT NULL DEFAULT FALSE,

    -- Declared application data (flat for queryability; source of truth for validation)
    brand_name          TEXT NOT NULL,
    class_type          TEXT NOT NULL,
    alcohol_content     TEXT NOT NULL,
    net_contents        TEXT NOT NULL,
    producer_name       TEXT NOT NULL,
    producer_address    TEXT NOT NULL,
    country_of_origin   TEXT,

    -- Extraction + validation results
    overall_status      TEXT NOT NULL CHECK (overall_status IN ('PASS','WARN','FAIL')),
    -- JSONB array of per-field results: { field, declared, extracted, confidence, status, reason }
    field_results       JSONB NOT NULL DEFAULT '[]'::jsonb,
    front_image_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    back_image_quality  JSONB NOT NULL DEFAULT '{}'::jsonb,
    processing_ms       INTEGER,

    -- Decision
    decision            TEXT CHECK (decision IN ('APPROVED','REJECTED')),
    decision_source     TEXT CHECK (decision_source IN ('AUTO','AGENT','AGENT_OVERRIDE')),
    decision_at         TIMESTAMPTZ,
    decision_comment    TEXT,

    -- Submitter override (only populated when a FAIL was disputed)
    override_attestation    BOOLEAN NOT NULL DEFAULT FALSE,
    override_explanation    TEXT,
    override_at             TIMESTAMPTZ,
    original_status         TEXT CHECK (original_status IN ('PASS','WARN','FAIL')),

    -- Batch grouping
    batch_id            UUID
);

CREATE INDEX IF NOT EXISTS idx_applications_pending
    ON applications (submitted_at ASC)
    WHERE overall_status = 'WARN' AND decision IS NULL;

CREATE INDEX IF NOT EXISTS idx_applications_batch
    ON applications (batch_id)
    WHERE batch_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total           INTEGER NOT NULL,
    submitter_note  TEXT
);
