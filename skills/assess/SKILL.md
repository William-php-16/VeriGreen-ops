---
name: assess
description: Evaluate ingested documents against Revised ESRS 2026 and Voluntary SME (VS) requirements using a strict 1.0-5.0 readiness rubric with exact verbatim page citations.
---

# `/assess` — ESRS / VS Readiness Scoring

Score each unassessed `(req_id, doc_id)` pair on the strict `1.0`–`5.0` readiness scale and persist exact, database-verified verbatim citations via `src/db.py save-assessment`.

## Pre-Flight Checks

1. Read `config/company_context.md` to confirm the organization profile, reporting fiscal year, consolidation boundaries, and active frameworks (`ESRS_2026` vs. `VS`).
2. Fetch pending `(req_id, doc_id)` pairs and extracted page text:
   - **Windows:** `.venv\Scripts\python.exe src/db.py get-pending --mode assess`
   - **macOS / Linux:** `.venv/bin/python src/db.py get-pending --mode assess`

## Strict 1.0–5.0 Readiness Rubric

Evaluate every `(req_id, doc_id)` pair strictly against these anchor definitions:

| Score | Anchor Definition | Quote & Page Requirement |
| :--- | :--- | :--- |
| `1.0` | **No mention** of the requirement in the document. | `evidence_quote = ""`, `page_number = 0` |
| `2.0` | **Vague aspiration** only (no binding policy, target, or metric). | Exact verbatim quote + `page_number >= 1` |
| `3.0` | **Qualitative policy only** (governance or policy stated, no quantitative metric or target). | Exact verbatim quote + `page_number >= 1` |
| `4.0` | **Quantitative metric + target year** (missing baseline year, full methodology, or assurance). | Exact verbatim quote + `page_number >= 1` |
| `5.0` | **Audit-ready disclosure** (full quantitative metric + baseline year + methodology + assurance status). | Exact verbatim quote + `page_number >= 1` |

Intermediate half-point scores (e.g., `2.5`, `3.5`, `4.5`) must follow the same verbatim quote and `page_number >= 1` rules as scores `> 1.0`.

## Anti-Hallucination Citation Rules

1. **Verbatim Substring Only:** For any `readiness_score > 1.0`, copy `evidence_quote` **word-for-word** from `document_pages.content_text` for that `doc_id` and `page_number`. Never paraphrase, synthesize across pages, or insert invented ellipses (`...`).
2. **Exact 1-Indexed Page Number:** Provide the exact integer `page_number` (`1 <= page_number <= documents.page_count`; always `1` for CSV sources).
3. **Zero-Mention Rule:** If `readiness_score == 1.0`, you MUST set `evidence_quote = ""` and `page_number = 0`.
4. **Actionable `gap_reason`:** For any score `< 5.0`, state the specific missing elements (e.g., missing baseline year, missing location-based Scope 2, missing Scope 3 inventory, or lack of limited assurance).

## Persistence

Save every assessment through `src/db.py save-assessment` (never write raw SQL):

- **Windows:**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py save-assessment --req-id "<REQ_ID>" --doc-id "<DOC_ID>" --score <SCORE> --quote "<VERBATIM_QUOTE>" --page <PAGE_INT> --gap-reason "<GAP_REASON>"
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py save-assessment --req-id "<REQ_ID>" --doc-id "<DOC_ID>" --score <SCORE> --quote "<VERBATIM_QUOTE>" --page <PAGE_INT> --gap-reason "<GAP_REASON>"
  ```

*(If passing structured JSON via `--json`, ensure the payload includes `req_id`, `doc_id`, `readiness_score`, `evidence_quote`, `page_number`, and `gap_reason`.)*

If `save-assessment` rejects a quote or page number, re-read the exact page text in `document_pages` and correct the substring before retrying.

## Output

Summarize the scored requirements, highlight critical gaps (`readiness_score < 3.5`), and suggest running `/verify` (for quantitative reconciliation) and `/greenwash` next.
