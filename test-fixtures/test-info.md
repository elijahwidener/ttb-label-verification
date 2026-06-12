# Test Fixtures

## Case 1 — Copper Still Bourbon → PASS
All fields match exactly. Correct government warning (bold, all caps).

## Case 2 — Harrow Peak Wine → FAIL
Government warning is title case and not bold. Per spec, both are hard FAILs.
Use this to test the auto-rejection flow and the submitter override modal.

## Case 3 — Valle Dorado Beer → WARN
Label photo is slightly angled and glare on back photo. Expect Claude to return low confidence on some fields,
triggering WARN. Also tests country of origin (Mexico). 