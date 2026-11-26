---
name: ingest
description: Deterministically ingest corporate PDF policies and CSV emissions logs into the local SQLite audit database with SHA-256 deduplication.
---

# `/ingest` — Deterministic Document Ingestion

Ingest source sustainability reports (`.pdf`) and operational emissions/energy logs (`.csv`) into `data/audit_pipeline.db` locally with zero external network calls.

## Pre-Flight Checks

1. Ensure the database schema and regulatory rulebook are initialized (`esrs_requirements` seeded from `config/esrs_standards.yaml`):
   - **Windows:** `.venv\Scripts\python.exe src/db.py init`
   - **macOS / Linux:** `.venv/bin/python src/db.py init`
2. Confirm the target source directory (default: `data/raw_docs/`; use `data/sample/` when testing on synthetic fixtures or `--dir <path>` if the user specifies another directory).

## Execution Steps

Run `src/ingestor.py` using the project virtual environment:

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\python.exe src/ingestor.py --dir data/raw_docs
  ```
- **macOS / Linux:**
  ```bash
  .venv/bin/python src/ingestor.py --dir data/raw_docs
  ```

Pass `--dir <custom_path>` if the user requests a different folder (such as `data/sample`).

## Deterministic Contract & Edge Cases

- **Supported Formats (FR-1.1):** Recursively scans `--dir` for `.pdf` and `.csv` files.
- **SHA-256 Deduplication (FR-1.2):** Computes `file_hash` (SHA-256 of raw bytes). Renamed duplicates with an identical hash are skipped (`Skipped duplicate`) without corrupting existing assessments.
- **PDF Extraction (FR-1.3):** Extracts text 1-indexed page-by-page via `pymupdf` into `document_pages`. If a scanned image-only PDF yields zero extractable characters, `ingestor.py` aborts that file with an error (`OCR required`) and continues the rest of the batch.
- **CSV Conversion (FR-1.4):** Parses CSVs via `pandas` into Markdown tables (plus deterministic Scope/Year aggregates when standard emissions columns exist) stored in `document_pages` with `page_number = 1`. Malformed or empty CSVs are logged without crashing the batch.

## Output

Report the ingested, skipped-duplicate, and failed/warning files returned by `src/ingestor.py`, and suggest running `/assess` next.
