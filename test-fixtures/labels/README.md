# Test label images — 20 cases

This is the build spec for the 20 test submissions. Each case is **one
submission** that exercises a specific path through the validation engine.

## Files & layout

Images and their declared-data sidecars live in the **`test-fixtures/` directory**
(one level up from this file), alongside `batch-sample.csv`:

- `application-N-front.png` and `application-N-back.png` — the label images (N = 1–20)
- `application-N.json` — the declared application data for that case (what a submitter
  types into the form). Already authored for all 20.

Cases **1–3 already exist** (don't rebuild them). Cases **4–20** need images created;
their `.json` declared data is already written.

The declared data in each `application-N.json` is identical to row N of
`batch-sample.csv`, so the same 20 images test both flows:

- **Single submission** — open one case's two images at `/submit`, type the values from
  its `.json`.
- **Batch** — upload all 40 images + `batch-sample.csv` at `/submit` → Batch.

PNG/JPEG/WEBP are all accepted. These don't need to be photographs — flat rendered
label graphics work, as long as text is legible and the deviation below is faithfully
reproduced.

## Convention for every label

The **declared values come from the JSON / CSV**. The "Label shows" column below says
how the *image* should differ from those declared values — "matches" means render the
declared values verbatim. Render straight-on, well lit, and in focus **except** the
image-quality case (#20).

Unless a case says otherwise, the back label carries the government warning **exactly**:

> GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.

…with `GOVERNMENT WARNING:` in caps and bold, at a font size comparable to surrounding
text. (Printing the **entire** warning in caps is also fine — the wording check is
case-insensitive; only the `GOVERNMENT WARNING:` prefix must be capitalized.)

Fields may appear on either image — the engine reads both together. Front typically
carries brand / class / ABV / net contents; back carries the warning, producer name &
address, and country of origin.

## The 20 cases

| # | Brand | Label shows (difference from the declared JSON) | Expected | Rule exercised |
|---|-------|--------------------------------------------------|----------|----------------|
| 1 | Copper Still Distilling Co. | Matches exactly. Warning bold + all caps. | **PASS** (auto-approved) | Everything matches |
| 2 | Harrow Peak | Warning rendered **title case** (`Government Warning:`) **and not bold**; wording otherwise exact. | **FAIL** (auto-rejected) | Warning must be all caps + bold; tests the override flow |
| 3 | Valle Dorado | Matches, but photograph is **slightly angled with glare** — readable, low confidence. Back shows country `Mexico`. | **WARN** (agent queue) | Low AI confidence → WARN; country present & matching |
| 4 | Iron Gate Brewing | Producer printed `Iron Gate Brewing Incorporated`; address `55 Canal St` (declared "Inc."/"Street"). | **PASS** | Style-only (Inc/Incorporated, St/Street) is forgiven |
| 5 | Smoky Hollow | Class printed `Tennessee Whiskey` (declared just `Whiskey`). | **PASS** | Class hierarchy — declared class contained in the label's more specific one |
| 6 | Northwind | Net contents printed `750 mL` (declared `75 cL`). | **PASS** | Unit conversion (75 cL = 750 mL) |
| 7 | Clachan Mor | Matches; back states country `Scotland` plainly. | **PASS** | Imported product, country declared & matching; "Whisky" spelling |
| 8 | Stone's Throw | Brand printed `STONE'S THROW` (all caps). | **PASS** | Casing/stylization forgiven (Dave Morrison's example) |
| 9 | Cedar Ridge | Producer printed correctly `Cedar Ridge Vineyards Inc.` — **the application JSON has the typo `Vinyards`**. | **FAIL** (auto-rejected) | Clear misspelling → kicked back to submitter |
| 10 | Riverside Cellars | Producer printed with words reordered: `Winery Riverside Cellars`. | **FAIL** (auto-rejected) | Same words, wrong order → mismatch |
| 11 | Old Tom | Producer printed `Old Tom Family Distillery LLC` (extra word "Family"). | **WARN** (agent queue) | Structural difference an agent can judge |
| 12 | Ironworks | Class printed `IPA` (declared `India Pale Ale`). | **WARN** (agent queue) | Acronym — class never auto-rejects |
| 13 | Maison Verte | Class printed `Brut Champagne` (declared generic `Wine`); back states country `France` plainly. | **WARN** (agent queue) | Generic-vs-specific class with no shared word; country matches |
| 14 | Sierra Pine | ABV printed `43% Alc./Vol.` (declared `46%`). | **FAIL** (auto-rejected) | ABV differs beyond 0.1-point tolerance |
| 15 | Harvest Moon | Net contents printed `700 mL` (declared `750 mL`). | **FAIL** (auto-rejected) | Net contents mismatch |
| 16 | Bluewater Rum Co. | Brand on front printed `Château Soleil` (unrelated). | **FAIL** (auto-rejected) | Confident brand mismatch |
| 17 | Glacier Bay | Warning wording altered — `birth defects` → `health issues`; caps/bold otherwise correct. | **FAIL** (auto-rejected) | Warning wording does not match statute |
| 18 | Crimson Oak | Warning wording exact but printed in a **much smaller font** than surrounding text. | **FAIL** (auto-rejected) | Warning font-size anomaly (caught via AI notes) |
| 19 | Fjord | Back shows `Product of Norway` — **country left blank in the JSON**. | **FAIL** (auto-rejected) | Country on label that wasn't declared |
| 20 | Lantern Hill | **Back photo heavy glare** obscuring the warning & producer (unreadable); front fine. | **400 image unusable** (`failed_side: back`) — never stored | Image-quality rejection back to submitter |

## Coverage

- **PASS (6):** 1, 4, 5, 6, 7, 8 — exact, style, class hierarchy, unit conversion, import, casing.
- **WARN (4):** 3, 11, 12, 13 — low confidence, structural producer diff, acronym, generic class.
- **FAIL (9):** 2, 9, 10, 14, 15, 16, 17, 18, 19 — warning format/wording/font, typo, reorder, ABV, net contents, brand, undeclared country.
- **Image unusable (1):** 20.

To also exercise a **front** image rejection (`failed_side: front`), reuse case 20's data
with the front photo motion-blurred instead of the back. To exercise the **submitter
override**, take any FAIL (e.g. #9 or #14), submit it, then click "I disagree" —
it should move to the agent queue as a WARN with your explanation attached.

## Note for maintainers

Two matching behaviors worth knowing when reading results:

- Cases 7 and 13 render the country of origin **plainly** (`Scotland`, `France`) so it
  matches the declared value. Real labels often say "Product of X"; the engine does not
  yet strip that prefix for country (it does for producer qualifiers like "Bottled by"),
  so `Product of Scotland` vs declared `Scotland` would currently land in WARN. A
  prefix-strip for country is a reasonable follow-up if that comes up in real use.
- For the image-quality case (#20) the defect must be severe enough that a human
  couldn't read the affected text either; mild blur correctly comes back as
  usable-with-low-confidence (WARN, like case 3), not rejected.
