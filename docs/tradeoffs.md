# Decisions & trade-offs

Decisions made where the spec left room, with reasoning. Updated as the build progressed.

## Build & deployment sequencing

- **All application code was written before pausing for Azure deployment.** The spec
  suggested pausing after Bicep, but nothing in the app code depends on resource values
  (everything is env-var driven), so a single pause with one complete runbook replaces
  two round-trips. The runbook is docs/deployment.md.

## Backend

- **Azure Functions v1 programming model (function.json folders), not the v2 decorator
  model.** SWA *managed* functions are pickier about the v2 model across runtime
  versions; the folder-per-function layout is the most battle-tested path and matches
  the repo structure in the spec.
- **`retention_sweep` is HTTP-triggered, not a timer.** SWA managed functions support
  HTTP triggers only. The daily cadence comes from a scheduled GitHub Actions workflow
  calling the endpoint (guarded by the `RETENTION_SWEEP_KEY` header secret); blob
  lifecycle policies remain the independent backstop. A dedicated Functions app would
  restore a real timer trigger — out of scope for the prototype.
- **Schema auto-applied on cold start** (`CREATE TABLE IF NOT EXISTS` from
  api/shared/schema.sql, once per worker). Removes the manual psql step from
  deployment. db/schema.sql stays canonical; the copy under api/shared must be kept in
  sync.
- **psycopg v3, plain SQL, one connection per request.** SQLAlchemy buys nothing for
  ~10 queries, and on serverless + Burstable Postgres a pool adds failure modes without
  meaningful wins.
- **Quarantine promotion re-uploads bytes instead of server-side blob copy.** The
  submit pipeline already holds the preprocessed JPEG in memory; uploading it to
  `labels` avoids async copy polling, and means the permanent artifact is the
  normalized JPEG actually sent to Claude (more honest audit trail).
- **Quarantine "1-hour TTL" is enforced by app logic, backstopped at 1 day.** Azure
  blob lifecycle granularity is daily; sub-day TTLs aren't expressible. The API deletes
  quarantine blobs synchronously on every outcome, so the lifecycle rule only catches
  abandoned uploads (browser closed mid-flow).
- **Blob containers are private; the agent UI gets 60-minute read-SAS URLs** generated
  in `GET /api/applications/{id}`. Upload SAS is write-only, 5 minutes.
- **Pillow format validation runs before Claude** and returns the same
  `image_unusable` 400 shape as the AI quality check — one failure contract for the
  frontend regardless of which layer rejected the image.
- **`source=AUTO|AGENT` query param added to GET /api/applications** beyond the
  spec'd contract, so the agent UI's Auto-Decided and History tabs can filter
  server-side instead of pulling everything.
- **Model: `claude-sonnet-4-6` as specified.** Extraction is OCR-shaped work; Sonnet's
  latency/cost profile fits the per-submission pre-processing budget.

## Frontend / routing

- **API base switches by hostname** (frontend/src/api/client.js): on `elijahwf.com`
  the SPA calls `/ttb/api/*` (proxied by Vercel), on `*.azurestaticapps.net` it calls
  `/api/*` directly. SWA route rewrites can't splice wildcard segments
  (`/ttb/api/* → /api/*`), so the proxy hop must happen at Vercel — that's why
  vercel.json has the extra `/ttb/api/:path*` rewrite.
- **Vite `outDir: dist/ttb`** so the built files physically live under `/ttb/` on the
  SWA host, matching `base: '/ttb/'`. The SWA root `/` 302-redirects to `/ttb/`.
- **Batch CSV parsed with papaparse** (proper quoting/escaping) rather than a
  hand-rolled splitter; the CSV has quoted addresses with commas.
- **Polling, no websockets**: the review queue refetches every 30 s; spec explicitly
  allows polling.

## Infra

- **Single region (default eastus2), LRS storage, Burstable B1ms Postgres, 7-day
  backups, no HA** — cost floor for a prototype (~$25–35/month total). Postgres
  firewall allows Azure-services traffic only (SWA managed functions have no static
  egress IPs); SSL required.
- **Storage CORS is restricted to the known page origins** (elijahwf.com, www,
  the SWA hostname, localhost dev) instead of `*`, since browsers PUT directly to
  blob storage.
