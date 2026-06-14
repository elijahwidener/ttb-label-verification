# Test label images

Build images for cases **4–20** (1–3 already exist). The declared data lives in
`../application-N.json` (identical to row N of `../batch-sample.csv`). Each case needs
`application-N-front.png` and `application-N-back.png` in `../` (one level up).

Each prompt below is meant to be pasted into an AI image generator. The **deviation
from the JSON is baked into the prompt** — that's what the case is testing. Render text
legible, straight-on, well lit (except #20). PNG/JPEG/WEBP all fine.

**Government warning** (put on the back label exactly, unless the case says otherwise):

> GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.

`GOVERNMENT WARNING:` must be in caps and bold.
Front usually carries brand / class / ABV / net contents; back carries the warning,
producer name & address, and country of origin.

---

### 4 — Iron Gate Brewing  ·  PASS
**Prompt:** A beer label, front and back. Front: brand "Iron Gate Brewing", class "American Pale Ale", "5.2% Alc./Vol.", "355 mL". Back: producer "Iron Gate Brewing Incorporated", "55 Canal St, Portland, ME 04101", and the government warning in bold caps.
**Why:** Style-only differences (Inc→Incorporated, Street→St) are forgiven.

### 5 — Smoky Hollow  ·  FAIL
**Prompt:** A whiskey label, front and back. Front: brand "Smoky Hollow", class "Tennessee Whiskey", "50% Alc./Vol. (100 Proof)", "750 mL". Back: producer "Smoky Hollow Distillers LLC", "9 Ridge Rd, Asheville, NC 28801", and the government warning.
**Why:** Declared class "Whiskey" is contained in the more specific label class. This should pass but the government warning causes a fail.

### 6 — Northwind  ·  PASS
**Prompt:** A gin label, front and back. Front: brand "Northwind", class "London Dry Gin", "47% Alc./Vol.", "750 mL". Back: producer "Northwind Spirits LLC", "200 Harbor Blvd, Seattle, WA 98101", and the government warning.
**Why:** 750 mL = declared 75 cL (unit conversion).

### 7 — Clachan Mor  ·  PASS
**Prompt:** A Scotch whisky label, front and back. Front: brand "Clachan Mor", class "Single Malt Scotch Whisky", "43% Alc./Vol.", "700 mL". Back: producer "Clachan Mor Distillery Ltd.", "Speyside, Scotland", the word "Scotland" shown plainly, and the government warning.
**Why:** Imported product, country declared & matching.

### 8 — Stone's Throw  ·  PASS
**Prompt:** A rye whiskey label, front and back. Front: brand in all caps "STONE'S THROW", class "Straight Rye Whiskey", "47% Alc./Vol.", "375 mL". Back: producer "Stone's Throw Distilling LLC", "902 Quarry St, Portland, OR 97209", and the government warning.
**Why:** Casing/stylization is forgiven.

### 9 — Cedar Ridge  ·  FAIL
**Prompt:** A wine label, front and back. Front: brand "Cedar Ridge", class "Cabernet Sauvignon", "13.5% Alc./Vol.", "750 mL". Back: producer spelled correctly "Cedar Ridge Vineyards Inc.", "410 Valley Rd, Napa, CA 94558", and the government warning.
**Why:** JSON has the typo "Vinyards"; label is correct → clear misspelling, kicked back.

### 9.1 — Cedar Ridge  ·  PASS
**Prompt:** A wine label, front and back. Front: brand "Cedar Ridge", class "Cabernet Sauvignon", "13.5% Alc./Vol.", "750 mL". Back: producer spelled correctly "Cedar Ridge Vinyards Inc.", "410 Valley Rd, Napa, CA 94558", and the government warning.
**Why:** JSON and label both have "Vinyards"; Should pass even though misspelling

### 10 — Riverside Cellars  ·  FAIL
**Prompt:** A wine label, front and back. Front: brand "Riverside Cellars", class "Pinot Noir", "13% Alc./Vol.", "750 mL". Back: producer with words reordered "Winery Riverside Cellars", "88 River Rd, Dundee, OR 97115", and the government warning.
**Why:** Same words, wrong order → mismatch.

### 11 — Old Tom  ·  WARN
**Prompt:** A gin label, front and back. Front: brand "Old Tom", class "London Dry Gin", "45% Alc./Vol.", "750 mL". Back: producer "Old Tom Family Distillery LLC" (extra word "Family"), "123 Bourbon St, Louisville, KY 40201", and the government warning.
**Why:** Structural producer difference for an agent to judge.

### 12 — Ironworks  ·  WARN
**Prompt:** A beer label, front and back. Front: brand "Ironworks", class "IPA", "6.8% Alc./Vol.", "355 mL". Back: producer "Ironworks Brewing Company", "88 Foundry Ave, Pittsburgh, PA 15201", and the government warning.
**Why:** Acronym for declared "India Pale Ale" — class never auto-rejects.

### 13 — Maison Verte  ·  WARN
**Prompt:** A French wine label, front and back. Front: brand "Maison Verte", class "Brut Champagne", "12% Alc./Vol.", "750 mL". Back: producer "Maison Verte", "14 Rue des Vignes, Épernay, France", the word "France" shown plainly, and the government warning.
**Why:** Generic declared class "Wine" vs specific label, no shared word; country matches.

### 13 — Maison Verte  ·  FAIL
**Prompt:** A French wine label, front and back. Front: brand "Maison Verte", class "Brut Champagne", "12% Alc./Vol.", "750 mL". Back: producer "Maison Verte", "14 Rue des Vignes, Épernay, France", the word "France" shown plainly, and the government warning.
**Why:** The wine bottle is unreadable with the lighting


### 14 — Sierra Pine  ·  FAIL
**Prompt:** A whiskey label, front and back. Front: brand "Sierra Pine", class "American Single Malt Whiskey", "43% Alc./Vol.", "750 mL". Back: producer "Sierra Pine Spirits LLC", "2200 Timber Ln, Truckee, CA 96161", and the government warning.
**Why:** Label ABV 43% vs declared 46% — beyond tolerance.

### 15 — Harvest Moon  ·  FAIL
**Prompt:** A hard cider label, front and back. Front: brand "Harvest Moon", class "Hard Apple Cider", "5.5% Alc./Vol.", "700 mL". Back: producer "Harvest Moon Cidery LLC", "31 Orchard Hill Rd, Geneva, NY 14456", and the government warning.
**Why:** Net contents 700 mL vs declared 750 mL.

### 16 — Bluewater Rum Co.  ·  FAIL
**Prompt:** A rum label, front and back. Front: brand "Château Soleil" (unrelated wrong name), class "Gold Rum", "40% Alc./Vol. (80 Proof)", "750 mL". Back: producer "Bluewater Rum Company Ltd.", "7 Harbor Way, Bridgetown", "Barbados", and the government warning.
**Why:** Confident brand mismatch (declared "Bluewater Rum Co.").

### 17 — Glacier Bay  ·  FAIL
**Prompt:** A vodka label, front and back. Front: brand "Glacier Bay", class "Vodka", "40% Alc./Vol.", "750 mL". Back: producer "Glacier Bay Distillery LLC", "14 Tundra Way, Anchorage, AK 99501", and the government warning but with "birth defects" replaced by "health issues" (bold caps otherwise correct).
**Why:** Warning wording does not match the statute.

### 18 — Crimson Oak  ·  FAIL
**Prompt:** A bourbon label, front and back. Front: brand "Crimson Oak", class "Straight Bourbon Whiskey", "50% Alc./Vol. (100 Proof)", "750 mL". Back: producer "Crimson Oak Distillery LLC", "5 Mill Race Rd, Lawrenceburg, KY 40342", and the government warning printed in a much smaller font than the surrounding text.
**Why:** Warning font-size anomaly.

### 19 — Fjord  ·  FAIL
**Prompt:** An aquavit label, front and back. Front: brand "Fjord", class "Aquavit", "42% Alc./Vol.", "500 mL". Back: producer "Fjord Spirits AS", "Storgata 12, Oslo", the line "Product of Norway", and the government warning.
**Why:** Country shown on label but left blank in the JSON.

### 20 — Lantern Hill  ·  400 image unusable (back)
**Prompt:** A saison beer label, front and back. Front (clean): brand "Lantern Hill", class "Saison", "6.0% Alc./Vol.", "355 mL". Back: producer "Lantern Hill Brewing Co.", "70 Beacon St, Boston, MA 02108" and the government warning, but with heavy glare/blur so the warning and producer are unreadable.
**Why:** Image-quality rejection — back never stored. Defect must be bad enough a human couldn't read it either.

---

## Coverage
- **PASS (6):** 1, 4, 5, 6, 7, 8
- **WARN (4):** 3, 11, 12, 13
- **FAIL (9):** 2, 9, 10, 14, 15, 16, 17, 18, 19
- **Image unusable (1):** 20

To test a **front** rejection, reuse #20 with the front blurred instead. To test the
**submitter override**, submit any FAIL (e.g. #9 or #14) and click "I disagree" — it
moves to the agent queue as a WARN.

## Notes for maintainers
- Cases 7 & 13 show country plainly ("Scotland", "France") so it matches the declared
  value. The engine doesn't yet strip a "Product of" prefix for country, so
  "Product of Scotland" vs "Scotland" would currently land in WARN.
- For #20 the defect must be severe enough a human couldn't read the text either; mild
  blur correctly comes back as WARN (like #3), not rejected.
