---
name: crawl
description: Discover and download corporate ESG/sustainability PDF and CSV files from a webpage or config/portals.yaml into data/raw_docs/ and ingest them with SHA-256 deduplication.
---

# `/verigreen crawl` - Deterministic Sustainability Portal Crawler

Invoke via `/verigreen crawl <url>` or `/verigreen crawl --batch`. Discover `.pdf` and `.csv` sustainability reports from a public webpage (`--url`) or batch portal list (`--batch` via `config/portals.yaml`), save them locally into `data/raw_docs/`, and ingest them directly into `data/audit_pipeline.db` via `ingest_file()`.

## Pre-Flight Checks

1. Ensure the database schema and `esrs_requirements` are initialized before or during crawling:
   - **Windows:** `.\.venv\Scripts\python.exe src\db.py init`
   - **macOS / Linux:** `.venv/bin/python src/db.py init`
2. If the user provides a URL, use `--url "<URL>"`. If the user wants to crawl configured portals, inspect `config/portals.yaml` and pass `--batch`.

## Execution

Run `src/crawler.py` using the project virtual environment:

- **Single URL (Windows PowerShell):**
  ```powershell
  .\.venv\Scripts\python.exe src\crawler.py --url "<URL>"
  ```
- **Single URL (macOS / Linux):**
  ```bash
  .venv/bin/python src/crawler.py --url "<URL>"
  ```
- **Batch Mode (`config/portals.yaml`):**
  ```powershell
  .\.venv\Scripts\python.exe src\crawler.py --batch
  ```

By default, `src/crawler.py` filters discovered `.pdf` and `.csv` links for ESG/sustainability keywords (`esg`, `csrd`, `esrs`, `sustainab`, `climate`, `carbon`, `emission`, `ghg`, etc.). Pass `--all-files` only if the user explicitly wants every `.pdf` and `.csv` file on the target page.

## Deterministic Behavior

- **Local Storage:** Downloaded files are saved to `data/raw_docs/` (collision-safe filenames).
- **SHA-256 Deduplication:** Each downloaded file is passed directly to `ingest_file()` in `src/ingestor.py`. Identical files (even if re-downloaded or renamed) are skipped (`[SKIPPED]`) without duplicating database rows or overwriting existing assessments.

## Output & Next Step

1. Report the exact counts and lists of:
   - **Newly ingested documents** (`[INGESTED] <filename> -> doc_id=<doc_id> (<N> pages)`)
   - **SHA-256 skipped duplicates** (`[SKIPPED] <filename> (already ingested as <doc_id>)`)
   - **Warnings or download/extraction errors** (`[WARNING]`)
2. If one or more new `doc_id`s were ingested, offer to run `/verigreen assess` on those new `doc_id`s next.
