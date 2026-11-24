---
name: export
description: Render the final A4 PDF Assurance Pack via src/report_builder.py after verifying that all target disclosure drafts have human approval.
---

# `/export` — A4 PDF Assurance Pack Export

Generate the multi-section A4 PDF Assurance Pack using `src/report_builder.py`, enforcing the Human-in-the-Loop (`human_approved = 1`) gate.

## Pre-Flight Check

Optionally check `src/db.py status` first to confirm whether any drafts still have `human_approved = 0`.

## Execution

Invoke `src/report_builder.py` via the project virtual environment:

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\python.exe src/report_builder.py --output output/verigreen_assurance_pack.pdf
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/report_builder.py --output output/verigreen_assurance_pack.pdf
  ```

## HITL Gate & Flags (FR-6.2 & FR-6.3)

- **Strict Approval Gate:** By default, `src/report_builder.py` checks `disclosure_drafts` for `human_approved = 0`. If any unapproved drafts exist, it exits with code `1` and lists the `req_id`s awaiting `/approve`.
- **Never Bypass Without Explicit Request:** Do NOT pass `--approved-only` unless the human user explicitly asks to export only already-approved drafts while excluding pending ones.
- **Required PDF Sections:** The generated A4 PDF (`fpdf2`) renders:
  1. **Executive Readiness Summary Table** (scores, mandatory flags, verification status)
  2. **Audit & Greenwashing Alerts** (numeric discrepancies and EU Green Claims flags)
  3. **Human-Approved ESRS/VS Disclosures** (cited prose and `[DATA GAP]` action items)

## Output

- If export succeeds (exit code `0`), report the exact generated PDF file path (e.g., `output/verigreen_assurance_pack.pdf`).
- If blocked (exit code `1`), display the unapproved `req_id` list and prompt the user to run `/approve`.
