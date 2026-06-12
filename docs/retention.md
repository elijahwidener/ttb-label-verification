# Data retention

No PII is collected anywhere in the system (no submitter accounts, names, or contact
info). What is stored:

| Data | Where | Retention |
|---|---|---|
| Label images (quarantine) | Blob `quarantine` container | Deleted synchronously by the API on every submit outcome; 1-day blob lifecycle rule catches abandoned uploads (Azure lifecycle granularity is daily, so the design's 1-hour TTL is enforced by app logic) |
| Label images (accepted) | Blob `labels` container | 30 days, enforced twice: (1) daily retention sweep (`POST /api/retention-sweep`, called by a scheduled GitHub Actions workflow) deletes blobs and sets `front_image_deleted` / `back_image_deleted` so the DB auditably confirms the purge; (2) independent 30-day blob lifecycle policy as backstop |
| Application records, field results, decisions | PostgreSQL | Indefinite — they are the audit trail |

Rejected-image uploads (quality failures) never reach the `labels` container; they are
deleted from quarantine before the API responds, and the submission is returned to the
submitter as a 400.

All AI traffic goes to a single host, `api.anthropic.com` (easy to allowlist per
Marcus Williams' constraint). Images sent to Claude are not stored by the API beyond
the request (30-day provider retention policies are out of scope of this prototype's
documentation).
