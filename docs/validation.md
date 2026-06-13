# Validation engine

`api/shared/validation.py`. Claude extracts (OCR only); this module compares each
extracted value against the declared application data and produces an auditable
PASS / WARN / FAIL per field with a plain-language reason. WARN is the only state that
reaches a human.

## Two axes: extraction confidence vs match quality

These are kept separate by design:

1. **AI confidence** — how sure the model is it *read the label correctly*. Below 0.7
   → WARN regardless of match (the agent should look at the image).
2. **Match quality** — whether the trusted extracted text *means the same* as what was
   declared. This is strict on spelling/content but forgiving on **style**.

## Decision matrix — text fields

(brand_name, class_type, producer_name, producer_address, country_of_origin)

Matching first **normalizes style away** (`normalize_for_match`): lowercase, `&`→`and`,
drop apostrophes/periods/commas, canonicalize corporate suffixes (Inc/Incorporated,
Co/Company, L.L.C./LLC) and street abbreviations (St/Street, Rd/Road, …). Then:

| AI confidence | Normalized comparison | Result |
|---|---|---|
| < 0.7 | (any) | WARN — AI uncertain, agent should look at the label |
| ≥ 0.7 | identical after normalization | PASS |
| ≥ 0.7 | differ, fuzzy ≥ 60 | WARN — real difference beyond formatting (typo or possibly a different entity) |
| ≥ 0.7 | differ, fuzzy < 60 | FAIL — confident mismatch |

This is the key distinction: PASS requires an **exact match once style is stripped**, so
"STONE'S THROW" vs "Stone's Throw" and "Old Tom Distillery LLC" vs "Old Tom Distillery,
L.L.C." pass, but a genuine spelling difference like "Harrow Peak Wnery" vs "Harrow Peak
Winery" does **not** silently pass — it's WARN, because it could be a typo or a different
producer, and only a human can tell. The interviews described fuzzy matching as being for
casing/punctuation, not spelling; this matrix encodes exactly that. Fuzzy score
(`max(ratio, token_sort_ratio)` on the normalized strings) is used only to split WARN
from FAIL.

**Class/type hierarchy:** class_type scoring additionally uses token_set_ratio, so a
declared class lexically contained in the label's more specific designation matches
("Whiskey" vs "Kentucky Straight Bourbon Whiskey" → PASS — same class, more specific
label). **class_type never auto-rejects:** the system models no beverage-type taxonomy
(out of scope), so it can't safely call a class mismatch wrong — a generic "Wine" vs a
specific "Cabernet Sauvignon" has no lexical overlap, and "IPA" vs "India Pale Ale" is
an abbreviation. Any class mismatch is therefore WARN (human confirms), never FAIL.

**Producer name qualifiers:** labels almost always qualify the producer ("Bottled
by X", "Distilled and bottled by X", "Imported by X"). Standard qualifier phrases are
stripped from both sides before scoring — otherwise nearly every real application
WARNs on producer_name. The agent still sees the original transcription in the
field-results table.

**Missing fields:** extracted `null` with high confidence (the model is sure it's
absent) → FAIL for required fields; `null` with low confidence → WARN.

## Field-specific rules

- **alcohol_content** — regex-extract the first percentage from both strings (a bare
  number like "45" also parses — the form submits just the percentage); within
  0.1 pp → PASS, beyond → FAIL, unparseable → FAIL, confidence < 0.6 → WARN.
- **net_contents** — parse value+unit, convert cl/L/fl-oz to mL, compare within 1 mL;
  falls back to normalized string equality if either side doesn't parse; confidence
  < 0.6 → WARN, mismatch → FAIL.
- **country_of_origin** — declared empty + extracted null → PASS; declared empty but
  found on label → FAIL (WARN if low confidence); otherwise the fuzzy matrix.
- **government_warning** — validated against the statutory wording, not declared data.
  Order: confidence < 0.5 → WARN ("partially unreadable") → AI-notes formatting checks
  (title case / not all caps, not bold, small font → FAIL, *even when the wording
  matches*) → "GOVERNMENT WARNING:" prefix must be literally capitalized on the label
  (catches title case directly) → **case-insensitive** whitespace-normalized wording
  match → PASS → otherwise FAIL. The wording match is case-insensitive because the
  statute requires capitals only for "GOVERNMENT WARNING:" — labels that print the
  entire warning in capitals are compliant and must pass.

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
