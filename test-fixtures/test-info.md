# Test Fixtures

The full 20-case test plan — declared data, per-case label deviations, and expected
PASS/WARN/FAIL outcomes — lives in **[labels/README.md](labels/README.md)**.

- `application-N-front.png` / `application-N-back.png` — label images (N = 1–20).
  Cases 1–3 exist; 4–20 are to be created per the spec.
- `application-N.json` — declared application data for single-submission testing.
- `batch-sample.csv` — the same 20 cases for batch-upload testing (declared data +
  matching filenames).