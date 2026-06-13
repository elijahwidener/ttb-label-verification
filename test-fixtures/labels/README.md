# Test label images

Place the 40 label images (front + back per application) in this folder. The
filenames must exactly match the `front_filename` / `back_filename` columns in
`../batch-sample.csv`. This README defines what each image should contain and
the outcome the system is expected to produce.

## Conventions for every image
- Unless a row says otherwise, render every value **exactly as it appears in
  the CSV row** and render the government warning **exactly** as:

  > GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.

  …in **all caps for "GOVERNMENT WARNING:"**, **bold**, at a font size comparable to surrounding text.
  (Printing the *entire* warning in capitals is also fine — the wording check is
  case-insensitive; only the "GOVERNMENT WARNING:" prefix must be capitalized.)
- Photograph/render straight-on, well lit, in focus (except rows 17–18).

## Per-application script

| Row | Files | Deviation from CSV | Expected outcome |
|----|----|----|----|
| 01 | app01-front/back | None — exact match | **PASS** (auto-approved) |
| 02 | app02-front/back | None | **PASS** |
| 03 | app03-front/back | None | **PASS** |
| 04 | app04-front/back | None (back shows "Product of Barbados") | **PASS** |
| 05 | app05-front/back | None | **PASS** |
| 06 | app06-front/back | None (back shows "Product of France") | **PASS** |
| 07 | app07-front/back | None | **PASS** |
| 08 | app08-front/back | None | **PASS** |
| 09 | app09-front/back | Brand rendered as **STONE'S THROW** (all caps) — Dave Morrison's example | **PASS** — fuzzy match is case-insensitive |
| 10 | app10-front/back | Producer name on back reads **"Old Tom Distilling Co."** instead of "Old Tom Distillery LLC" | **WARN** — borderline fuzzy match (60–89), goes to agent queue |
| 11 | app11-front/back | Class/type on front reads **"IPA"** instead of "India Pale Ale" | **WARN** — borderline match, agent judgment |
| 12 | app12-front/back | Alcohol content on front reads **"43% Alc./Vol."** (declared 46%) | **FAIL** — ABV differs by more than 0.1pp (auto-rejected; use to demo the override flow) |
| 13 | app13-front/back | Net contents on front reads **"700 mL"** (declared 750 mL) | **FAIL** — net contents mismatch |
| 14 | app14-front/back | Government warning rendered as **"Government Warning:"** in title case (Jenny Park's example); wording otherwise exact | **FAIL** — warning must be all caps |
| 15 | app15-front/back | Government warning wording altered: replace "birth defects" with **"health issues"** | **FAIL** — wording does not match required text |
| 16 | app16-front/back | Brand on front reads **"Chateau Soleil"** (completely different) | **FAIL** — confident brand mismatch |
| 17 | app17-front/back | Back image has **heavy glare** obscuring the bottom third (warning unreadable, label angle fine) | **400 image_unusable, failed_side=back** — never stored, row shows "Bad back image" with re-upload |
| 18 | app18-front/back | Front image **badly out of focus / motion-blurred** so no text is legible | **400 image_unusable, failed_side=front** |
| 19 | app19-front/back | Back label shows **"Product of Canada"** (CSV declares no country) | **FAIL** — label shows a country of origin that was not declared |
| 20 | app20-front/back | Government warning printed in a **much smaller font** than surrounding text; wording exact | **FAIL** — warning font size (caught via AI notes) |

## Extra images for single-submission testing (optional)

- `single-pass-front.jpg` / `single-pass-back.jpg` — duplicate of row 01's script.
- `single-glare-back.jpg` — duplicate of row 17's glare back, for testing the
  targeted re-upload flow (form data and the good front image must survive).

## Generation tips

These don't all need to be photographs of real bottles — flat rendered label images (e.g., generated graphics) work, as long as the text is legible and the deviations above are faithfully reproduced. For rows 17–18 the defect must be severe enough that a human couldn't read the affected text either; mild blur will (correctly) come back as usable-with-low-confidence instead of rejected.