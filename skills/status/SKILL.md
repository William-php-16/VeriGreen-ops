---
name: status
description: Display the VeriGreen-ops audit pipeline readiness dashboard, database counts, verification flags, and human approval status.
---

# `/status` — Audit Pipeline Readiness Dashboard

Inspect the current state of `data/audit_pipeline.db` by running `python src/db.py status` via the project virtual environment.

## Execution

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\python.exe src/db.py status
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/db.py status
  ```

## Output & Next-Step Guidance

Present the output cleanly to the user and recommend the next logical workflow step based on the current pipeline state:

1. If `esrs_requirements` is `0`: run `src/db.py init` to seed `config/esrs_standards.yaml`.
2. If `documents` is `0`: place PDF/CSV files in `data/raw_docs/` (or use `data/sample/`) and run `/ingest`.
3. If unassessed `(req_id, doc_id)` pairs remain: run `/assess`.
4. If quantitative assessments have `numeric_verified` unset: run `/verify`.
5. If assessments have not been screened for EU Green Claims: run `/greenwash`.
6. If `disclosure_drafts` are missing or outdated: run `/draft`.
7. If drafts have `human_approved = 0`: run `/approve` before `/export`.
8. When all target drafts are approved: run `/export` to build the A4 PDF Assurance Pack.
