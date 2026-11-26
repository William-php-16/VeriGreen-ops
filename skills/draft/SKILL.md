---
name: draft
description: Synthesize formal ESRS/VS disclosure drafts with mandatory inline page citations and explicit [DATA GAP] markers for low scores or unverified metrics.
---

# `/verigreen draft` - Citation-Backed ESRS / VS Disclosure Drafting

Invoke via `/verigreen draft` to compile formal, audit-ready ESRS and Voluntary SME (`VS`) disclosure sections in `disclosure_drafts` from verified `assessments` without inventing any ungrounded figures.

## Pre-Flight & Data Retrieval

1. Read `config/company_context.md` to align entity name, consolidation boundaries, reporting fiscal year, and active regulatory scope.
2. Retrieve current assessments and verification/greenwashing flags:
   - **Windows:**
     ```powershell
     .\.venv\Scripts\python.exe src/db.py get-assessments
     ```
   - **macOS / Linux:**
     ```bash
     .venv/bin/python src/db.py get-assessments
     ```

## Mandatory Drafting Rules

For each requirement (`req_id`) in scope:

1. **Mandatory Inline Page Citations (FR-5.1):**
   - Every factual sentence in `draft_markdown` MUST end with an explicit citation: `[Source: <filename>, p.<page_number>]` (use `p.1` for CSV sources).
   - Uncited factual assertions are strictly prohibited.
2. **Mandatory `[DATA GAP]` Markers (FR-5.2, No Invented Numbers):**
   - Whenever `readiness_score < 3.5` OR `numeric_verified = 0`, you MUST NOT invent, extrapolate, estimate, or smooth over missing metrics, baseline years, or conflicting figures.
   - Insert an explicit tag in the prose:
     `[DATA GAP: <action required: specific missing datapoint, baseline, or numeric discrepancy>]`
   - When `numeric_verified = 0`, explicitly report the mathematical discrepancy noted in `numeric_discrepancy` rather than choosing one figure silently.
3. **Anti-Greenwashing Compliance:**
   - If `greenwash_flag = 1`, NEVER repeat the flagged marketing claim as verified corporate fact. Either omit the unsubstantiated claim or frame it under a remediation `[DATA GAP: Remove or substantiate "<phrase>" per EU Green Claims rules: <greenwash_reason>]`.
4. **Formal Assurance Tone:**
   - Write concise, objective, third-person regulatory prose suitable for limited-assurance review under Revised ESRS 2026 / VS.

## Humanization Pass (Required Before Saving)

Before saving any draft to `disclosure_drafts`, apply [skills/humanize/SKILL.md](../humanize/SKILL.md) to the prose:
- Remove em dashes, banned AI buzzwords, filler phrases, superficial `-ing` tack-ons, rule-of-three padding, and negative parallelisms.
- **Strictly preserve** all numbers, units, percentages, verbatim quotes, `[Source: <filename>, p.<page_number>]` citations, and `[DATA GAP: ...]` markers verbatim.

## Persistence (HITL Lock)

Save each drafted section via `src/db.py save-draft` (which always initializes/resets `human_approved = 0`):

- **Windows:**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py save-draft --req-id "<REQ_ID>" --file "<PATH_TO_DRAFT_MD>"
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py save-draft --req-id "<REQ_ID>" --file "<PATH_TO_DRAFT_MD>"
  ```

*(Or pass `--markdown "<TEXT>"` if supported by the CLI. Never attempt to set `human_approved = 1` inside `/verigreen draft`.)*

## Output

List every `req_id` drafted, the count of inline citations and `[DATA GAP]` tags inserted, and direct the human reviewer to run `/verigreen approve` before exporting.
