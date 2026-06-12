# Validation engine

`api/shared/validation.py`. Claude extracts (OCR only); this module compares each
extracted value against the declared application data and produces an auditable
PASS / WARN / FAIL per field with a plain-language reason. WARN is the only state that
reaches a human.

## Decision matrix — fuzzy fields

(brand_name, class_type, producer_name, producer_address, country_of_origin)

| AI confidence | Fuzzy score | Result |
|---|---|---|
| ≥ 0.7 | ≥ 90 | PASS |
| ≥ 0.7 | 60–89 | WARN — borderline match, agent should review |
| ≥ 0.7 | < 60 | FAIL — confident mismatch |
| < 0.7 | any | WARN — AI uncertain, agent should look at the label |

Fuzzy score = `max(ratio, token_sort_ratio)` (rapidfuzz) on casefolded,
whitespace-normalized strings. Case-insensitivity makes "STONE'S THROW" vs
"Stone's Throw" a 100 (Dave Morrison's example); token_sort forgives word-order
differences in addresses and company suffixes.

**Missing fields:** extracted `null` with high confidence (the model is sure it's
absent) → FAIL for required fields; `null` with low confidence → WARN.

## Field-specific rules

- **alcohol_content** — regex-extract the first percentage from both strings; within
  0.1 pp → PASS, beyond → FAIL, unparseable → FAIL, confidence < 0.6 → WARN.
- **net_contents** — parse value+unit, convert cl/L/fl-oz to mL, compare within 1 mL;
  falls back to normalized string equality if either side doesn't parse; confidence
  < 0.6 → WARN, mismatch → FAIL.
- **country_of_origin** — declared empty + extracted null → PASS; declared empty but
  found on label → FAIL (WARN if low confidence); otherwise the fuzzy matrix.
- **government_warning** — validated against the statutory wording, not declared data.
  Order: confidence < 0.5 → WARN ("partially unreadable") → AI-notes formatting checks
  (title case / not all caps, not bold, small font → FAIL, *even when the wording
  matches*) → whitespace-normalized exact match → PASS → otherwise FAIL.

## Overall roll-up

Any FAIL → FAIL (auto-reject) · else any WARN → WARN (agent queue) · else PASS
(auto-approve).

**Malformed Claude JSON:** every field becomes WARN with confidence 0 and the
application routes to the agent queue; the raw response is logged.

## Thresholds need empirical tuning

All thresholds (90/60 fuzzy, 0.7 / 0.6 / 0.5 confidence boundaries, 0.1 pp ABV
tolerance) are best-guesses informed by stakeholder interviews, not measured against
real label data. Note the spec intentionally uses different confidence boundaries per
field family (0.7 for fuzzy fields, 0.6 for numeric fields, 0.5 for the warning);
before production these should be calibrated on a labeled corpus — measuring agent
agreement with WARN outcomes is the obvious feedback loop.
