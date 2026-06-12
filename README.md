# TTB Label Verification Prototype

AI-assisted pre-screening for alcohol label applications. Submitters upload label
photos + declared data; Claude extracts what's physically on the label; a
deterministic validation engine compares declared vs extracted per field; clear
passes auto-approve, clear failures auto-reject (with a submitter override path), and
only the ambiguous middle (WARN) reaches a human agent — pre-computed, so agents never
wait on AI.

**Standalone proof of concept.** Not integrated with COLA; decisions have no
regulatory effect. Live at https://elijahwf.com/ttb (served from Azure via a Vercel
rewrite).

## How it works

```
Submitter ──► SAS upload to quarantine ──► /api/submit
                                             │  Pillow normalize → Claude (1 call:
                                             │  quality check + field extraction)
                 unusable image ◄── 400 ─────┤
                                             ▼
                                      validation engine (api/shared/validation.py)
                                             │  PASS → auto-approve
                                             │  FAIL → auto-reject (submitter can override → WARN)
                                             ▼  WARN → agent queue
Agent ──► /review queue ──► field-by-field table + label images ──► Approve / Reject
```

Architecture detail: [docs/architecture.md](docs/architecture.md) and the C4 diagrams
in [docs/](docs/).

## Repo map

| Path | What |
|---|---|
| `frontend/` | React 18 + Vite + Tailwind SPA (routes `/submit`, `/review`; base path `/ttb/`) |
| `api/` | Azure Functions (Python 3.11): submit pipeline, queue/decision endpoints, retention sweep |
| `api/shared/` | extraction.py (Claude), validation.py (decision engine), blob.py, db.py, prompts.py |
| `infra/main.bicep` | SWA Standard + PostgreSQL Flexible (B1ms) + Blob Storage (quarantine/labels, lifecycle, CORS) |
| `db/schema.sql` | Canonical schema (auto-applied by the API on first connection) |
| `vercel.json` | Deliverable for the personal-site repo — `/ttb` rewrites to the SWA |
| `test-fixtures/` | 20-application batch CSV + README spec for the 40 test label images |
| `docs/` | Architecture, validation rules, trade-offs, retention, deployment runbook, limitations |

## Deploying

Follow [docs/deployment.md](docs/deployment.md): one Bicep deployment, three `az`
commands, two GitHub secrets, push to deploy, plus a Vercel rewrite on the personal
site.

## Key documents

- [docs/validation.md](docs/validation.md) — the PASS/WARN/FAIL rules and thresholds
- [docs/tradeoffs.md](docs/tradeoffs.md) — every non-obvious decision and why
- [docs/limitations.md](docs/limitations.md) — what this prototype intentionally does not do
- [docs/retention.md](docs/retention.md) — image/data retention policy
