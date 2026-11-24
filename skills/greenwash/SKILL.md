---
name: greenwash
description: Screen extracted evidence quotes against EU Green Claims anti-greenwashing substantiation rules and flag unsubstantiated claims.
---

# `/greenwash` — EU Green Claims Anti-Greenwashing Screen

Inspect all non-empty `evidence_quote` rows in `assessments` for vague, misleading, or unsubstantiated environmental marketing claims under EU Green Claims substantiation standards.

## Pre-Flight & Data Retrieval

1. Read `config/company_context.md` to review entity-specific anti-greenwashing rules.
2. Fetch all assessment records:
   - **Windows:**
     ```powershell
     .\.venv\Scripts\python.exe src/db.py get-assessments
     ```
   - **macOS / Linux:**
     ```bash
     .venv/bin/python src/db.py get-assessments
     ```

## EU Green Claims Screening Criteria

Evaluate every assessment row with a non-empty `evidence_quote`. Set `greenwash_flag = 1` whenever a quote contains or relies upon:

1. **Blanket or Absolute Eco-Claims:** Unqualified terms such as `"carbon neutral"`, `"climate positive"`, `"100% eco-friendly"`, `"100% sustainable"`, `"zero impact"`, `"green"`, or `"net-zero packaging"` without full life-cycle substantiation.
2. **Offset-Only Neutrality Assertions:** Claims of carbon neutrality or net-zero products based on carbon credits/offsets without separately disclosing gross Scope 1/2/3 emissions, the mitigation/reduction hierarchy, life-cycle assessment (LCA) boundaries, and verified registry retirement details.
3. **Cherry-Picked or Unbounded Scope Claims:** Highlighting a single attribute (e.g., recyclable outer box) as proof of total product sustainability while omitting material negative impacts or excluded boundaries.
4. **Unverified Future Promises Presented as Present Fact:** Claims implying achieved sustainability performance without dated milestones, quantitative KPIs, or third-party verification.

If a quote is factual, bounded, and properly qualified (or `evidence_quote == ""`), set `greenwash_flag = 0` and `greenwash_reason = ""`.

## Persistence

Update every screened assessment via `src/db.py update-greenwash`:

- **Windows:**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py update-greenwash --assess-id <ASSESS_ID> --flag <0_OR_1> --reason "<SPECIFIC_SUBSTANTIATION_FAILURE_OR_EMPTY>"
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py update-greenwash --assess-id <ASSESS_ID> --flag <0_OR_1> --reason "<SPECIFIC_SUBSTANTIATION_FAILURE_OR_EMPTY>"
  ```

When `flag = 1`, `greenwash_reason` MUST quote the offending phrase and state the exact substantiation failure (e.g., missing gross LCA emissions, missing verified offset registry, or prohibited absolute claim).

## Output

Summarize all flagged `assess_id` / `req_id` items with their source page citations and recommended compliant rewrites, then suggest running `/draft`.
