# Known limitations & future work

Honest list of what this prototype does not do.

- **No COLA integration** — standalone proof of concept; approving/rejecting here has
  no effect in any system of record.
- **Beer and wine are treated identically to spirits** — one superset field list.
  Real regulations differ per beverage type; modeling that is future work.
- **No authentication** — anyone with the URL can submit or play agent. Acceptable
  only because there is no sensitive data and no regulatory effect.
- **30-day image retention** — label images are deleted after 30 days (sweep + blob
  lifecycle). Application records and field results are kept indefinitely.
- **Soft decisions** — no email/notification to submitters; they must return to the
  site to see the agent's decision.
- **Front + back images required** — no wrap-around single-label support, no support
  for products needing more than two images.
- **No PDF input** — images only (JPEG/PNG/WEBP).
- **Batch limit: 20 applications** — prototype cap; the architecture (client-
  orchestrated, 5 concurrent) is the same shape needed for 200–300.
- **Browser-orchestrated batches** — closing the tab mid-batch drops queued items;
  completed submissions persist.
- **No rate limiting / abuse protection** on the submit endpoint or overrides.
- **Validation thresholds are best-guesses** needing empirical tuning
  (docs/validation.md).
- **No accessibility audit** — targets WCAG AA (contrast, 44px targets, icon+text
  status, aria attributes) but has not been audited.
- **No structured observability** beyond Azure built-in logs; malformed AI responses
  are logged but not alerted on.
- **Retention sweep depends on a GitHub Actions cron** (SWA managed functions can't
  run timers); if the workflow is disabled, the blob lifecycle policy still deletes
  images but the DB flags lag until the next sweep call.
- **Read-SAS URLs expire after 60 minutes** — an agent who keeps the drawer open
  longer than that must reopen it to re-fetch image URLs.
