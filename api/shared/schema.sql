-- Copy of db/schema.sql packaged with the Functions app. Executed idempotently
-- on cold start by shared/db.py (ensure_schema). Keep in sync with db/schema.sql.

CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    front_image_blob_url    TEXT NOT NULL,
    back_image_blob_url     TEXT NOT NULL,

    front_image_deleted     BOOLEAN NOT NULL DEFAULT FALSE,
    back_image_deleted      BOOLEAN NOT NULL DEFAULT FALSE,

    brand_name          TEXT NOT NULL,
    class_type          TEXT NOT NULL,
    alcohol_content     TEXT NOT NULL,
    net_contents        TEXT NOT NULL,
    producer_name       TEXT NOT NULL,
    producer_address    TEXT NOT NULL,
    country_of_origin   TEXT,

    overall_status      TEXT NOT NULL CHECK (overall_status IN ('PASS','WARN','FAIL')),
    field_results       JSONB NOT NULL DEFAULT '[]'::jsonb,
    front_image_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    back_image_quality  JSONB NOT NULL DEFAULT '{}'::jsonb,
    processing_ms       INTEGER,

    decision            TEXT CHECK (decision IN ('APPROVED','REJECTED')),
    decision_source     TEXT CHECK (decision_source IN ('AUTO','AGENT','AGENT_OVERRIDE')),
    decision_at         TIMESTAMPTZ,
    decision_comment    TEXT,

    override_attestation    BOOLEAN NOT NULL DEFAULT FALSE,
    override_explanation    TEXT,
    override_at             TIMESTAMPTZ,
    original_status         TEXT CHECK (original_status IN ('PASS','WARN','FAIL')),

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
