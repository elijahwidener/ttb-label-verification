# Architecture overview

C4 diagrams: [c4-level1-context.mermaid](c4-level1-context.mermaid),
[c4-level2-containers.mermaid](c4-level2-containers.mermaid).

## Two-actor model with pre-processing

The 5-second bar is about the **agent's** experience. All AI work happens at
submission time (submitter waits ~5–15 s per application); by the time an agent opens
anything, results are pre-computed rows in Postgres. Agents only review WARN — PASS is
auto-approved and FAIL auto-rejected at insert time.

## Request flow (submit)

1. Frontend `POST /api/upload-url` per image → write-only 5-min SAS for the
   **quarantine** container → browser PUTs the image directly to Blob Storage.
2. Frontend `POST /api/submit` with the two blob URLs + declared form data.
3. API downloads from quarantine, Pillow-validates/normalizes (JPEG q85, ≤2048px),
   sends both images in **one** Claude call (`claude-sonnet-4-6`, 10 s timeout, one
   retry on timeout/529) that returns per-field extraction + per-image quality.
4. Unusable image → quarantine blobs deleted, 400 `image_unusable` with `failed_side`;
   nothing is ever stored permanently.
5. Usable → bytes promoted to the **labels** container, quarantine deleted, validation
   engine compares declared vs extracted, row inserted with auto-decision, 201 returned
   with the full field-result table.

## Serving topology

- Azure Static Web App (Standard) hosts the React SPA (under `/ttb/`) + Python
  managed functions (under `/api`).
- Public entry is `elijahwf.com/ttb` via Vercel rewrites (see vercel.json at repo
  root): `/ttb/*` → SWA `/ttb/*` and `/ttb/api/*` → SWA `/api/*`. The SPA picks its
  API base by hostname (client.js).
- PostgreSQL Flexible Server (Burstable) stores applications/batches; Blob Storage
  stores images in private containers (agent UI uses 60-min read SAS).
