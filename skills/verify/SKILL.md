---
name: verify
description: Cross-check quantitative sustainability claims in PDF assessments against ingested CSV operational and emissions tables within a 1% tolerance.
---

# `/verigreen verify` - Quantitative Narrative vs. CSV Reconciliation

Invoke via `/verigreen verify` to audit every quantitative requirement (`is_quantitative = 1`) by mathematically comparing figures claimed in PDF `evidence_quote` text against ingested CSV Markdown tables (`doc_type = 'csv'`).

## Pre-Flight & Data Retrieval

Fetch all quantitative assessments and ingested CSV tables:

- **Windows:**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py get-assessments --quantitative-only
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py get-assessments --quantitative-only
  ```

## Verification Procedure

For each assessment row where `is_quantitative = 1` and `readiness_score > 1.0`:

1. **Extract Claimed Metrics:** Identify all absolute numbers (e.g., tCO2e, MWh, tonnes, percentages), reporting years, baseline years, scopes, and facility boundaries in `evidence_quote` (and surrounding PDF context if needed).
2. **Locate Ground-Truth CSV Aggregates:** Inspect the Markdown tables and deterministic summaries stored for ingested CSV documents (`doc_type = 'csv'`).
3. **Perform Exact Arithmetic Check (1% Relative Tolerance):**
   - Compute totals, year-over-year percentage changes, and intensity ratios directly from the CSV rows.
   - Calculate relative error: `abs(claimed - calculated) / abs(calculated)`.
   - Mark **`numeric_verified = 1`** ONLY if the claimed figures reconcile with the CSV tables within **1% relative tolerance** (`<= 0.01`).
   - Mark **`numeric_verified = 0`** if:
     - Claimed totals or YoY percentage changes differ from CSV math by more than **1%**, OR
     - Required underlying CSV data is missing, unverified, or excludes a facility/scope claimed in the narrative.
4. **Document Exact Math on Mismatch:** When `numeric_verified = 0`, write a concise, explicit mathematical explanation in `numeric_discrepancy` showing both the PDF claim, the exact CSV calculation, and the percentage variance.

## Persistence

Persist every verification result via `src/db.py update-verification`:

- **Windows:**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py update-verification --assess-id <ASSESS_ID> --verified <0_OR_1> --discrepancy "<EXACT_MATH_OR_EMPTY>"
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py update-verification --assess-id <ASSESS_ID> --verified <0_OR_1> --discrepancy "<EXACT_MATH_OR_EMPTY>"
  ```

## Output

Present a reconciliation table showing each quantitative `req_id`, claimed value, CSV-calculated value, variance, and `PASS` (`numeric_verified = 1`) or `FAIL` (`numeric_verified = 0`), then recommend running `/verigreen greenwash` or `/verigreen draft`.
