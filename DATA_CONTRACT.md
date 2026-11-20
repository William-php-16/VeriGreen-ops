# VeriGreen-ops — Data & CLI Contract (`DATA_CONTRACT.md`)

This document is the authoritative specification for the SQLite database (`data/audit_pipeline.db`), deterministic Python CLI scripts (`src/`), YAML rulebook schema (`config/esrs_standards.yaml`), and system vs. user-editable boundaries.

---

## 1. File Ownership & Boundary Contract

| Layer | Files / Directories | Contract |
| :--- | :--- | :--- |
| **System Core Engine** | `src/db.py`, `src/ingestor.py`, `src/report_builder.py`, `DATA_CONTRACT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Deterministic infrastructure. Never modified during normal audit runs. |
| **User-Editable Config** | `config/esrs_standards.yaml`, `config/company_context.md` | Users edit regulatory rulebooks (`ESRS_2026` / `VS`) and company metadata without changing `src/`. |
| **User-Editable Evidence** | `data/raw_docs/` | Users drop corporate `.pdf` and `.csv` files here. |
| **Modular Skills** | `skills/<skill>/SKILL.md` | Prompt workflows invoking `src/` CLI subcommands. |
| **Generated Artifacts** | `data/audit_pipeline.db`, `data/sample/*`, `output/*.pdf` | Created and updated exclusively by `src/` and `scripts/`. |

---

## 2. SQLite Relational Schema (`data/audit_pipeline.db`)

All foreign keys MUST be enforced (`PRAGMA foreign_keys = ON;`).

### 2.1 `documents`
Stores SHA-256 deduplicated ingested source files.

| Column | Type | Constraints | Notes |
| :--- | :--- | :--- | :--- |
| `doc_id` | `TEXT` | `PRIMARY KEY` | Deterministic ID (e.g., first 12 chars of `file_hash` or UUID). |
| `file_hash` | `TEXT` | `UNIQUE NOT NULL` | Hex SHA-256 of raw file bytes. |
| `filename` | `TEXT` | `NOT NULL` | Base filename (e.g., `sample_sustainability_report.pdf`). |
| `doc_type` | `TEXT` | `NOT NULL CHECK(doc_type IN ('pdf', 'csv'))` | File format. |
| `page_count` | `INTEGER` | `NOT NULL CHECK(page_count >= 1)` | Number of pages (`1` for CSVs). |
| `ingested_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC timestamp. |

### 2.2 `document_pages`
Stores lossless page-by-page extracted PDF text or CSV-to-Markdown tables.

| Column | Type | Constraints | Notes |
| :--- | :--- | :--- | :--- |
| `page_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate key. |
| `doc_id` | `TEXT` | `NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE` | Parent document. |
| `page_number` | `INTEGER` | `NOT NULL CHECK(page_number >= 1)` | 1-indexed page number (`1` for CSVs). |
| `content_text` | `TEXT` | `NOT NULL` | Extracted text (PDF) or Markdown table (CSV). |
| — | — | `UNIQUE(doc_id, page_number)` | One row per page per document. |

### 2.3 `esrs_requirements`
Seeded deterministically from `config/esrs_standards.yaml` via `src/db.py init`.

| Column | Type | Constraints | Notes |
| :--- | :--- | :--- | :--- |
| `req_id` | `TEXT` | `PRIMARY KEY` | Requirement ID (e.g., `ESRS-E1-6`, `VS-B3-1`). |
| `framework` | `TEXT` | `NOT NULL` | e.g., `ESRS_2026` or `VS`. |
| `standard` | `TEXT` | `NOT NULL` | e.g., `ESRS E1`, `ESRS E4`, `ESRS E5`, `ESRS S2`, `ESRS G1`, `VS-B3`. |
| `topic` | `TEXT` | `NOT NULL` | Short topic title. |
| `requirement_text` | `TEXT` | `NOT NULL` | Full compliance requirement description. |
| `is_quantitative` | `INTEGER` | `NOT NULL CHECK(is_quantitative IN (0, 1))` | `1` triggers `/verify` numeric reconciliation. |
| `mandatory` | `INTEGER` | `NOT NULL CHECK(mandatory IN (0, 1))` | `1` if mandatory under active standard. |

### 2.4 `assessments`
Stores 1.0–5.0 readiness scores, verbatim quotes, numeric verification flags, and anti-greenwashing flags.

| Column | Type | Constraints | Notes |
| :--- | :--- | :--- | :--- |
| `assess_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate key. |
| `req_id` | `TEXT` | `NOT NULL REFERENCES esrs_requirements(req_id) ON DELETE CASCADE` | Requirement evaluated. |
| `doc_id` | `TEXT` | `NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE` | Source document evaluated. |
| `readiness_score` | `REAL` | `NOT NULL CHECK(readiness_score >= 1.0 AND readiness_score <= 5.0)` | 1.0–5.0 rubric score. |
| `evidence_quote` | `TEXT` | `NOT NULL` | Exact verbatim substring from `document_pages.content_text` (or `""` if score `1.0`). |
| `page_number` | `INTEGER` | `NOT NULL CHECK(page_number >= 0)` | Exact 1-indexed page (or `0` if score `1.0`). |
| `gap_reason` | `TEXT` | `NOT NULL DEFAULT ''` | Explanation of compliance gaps. |
| `numeric_verified` | `INTEGER` | `CHECK(numeric_verified IS NULL OR numeric_verified IN (0, 1))` | `NULL` before `/verify`, `1` if reconciled within 1%, `0` if mismatch. |
| `numeric_discrepancy` | `TEXT` | `NOT NULL DEFAULT ''` | Mathematical explanation when `numeric_verified = 0`. |
| `greenwash_flag` | `INTEGER` | `NOT NULL DEFAULT 0 CHECK(greenwash_flag IN (0, 1))` | `1` if EU Green Claims violation detected. |
| `greenwash_reason` | `TEXT` | `NOT NULL DEFAULT ''` | Substantiation failure rationale. |
| — | — | `UNIQUE(req_id, doc_id)` | One latest assessment per `(req_id, doc_id)` pair. |

### 2.5 `disclosure_drafts`
Stores citation-backed ESRS/VS prose and the mandatory HITL approval gate.

| Column | Type | Constraints | Notes |
| :--- | :--- | :--- | :--- |
| `draft_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate key. |
| `req_id` | `TEXT` | `UNIQUE NOT NULL REFERENCES esrs_requirements(req_id) ON DELETE CASCADE` | One compiled draft per requirement. |
| `draft_markdown` | `TEXT` | `NOT NULL` | Draft text with `[Source: file, p.X]` and `[DATA GAP: ...]` tags. |
| `human_approved` | `INTEGER` | `NOT NULL DEFAULT 0 CHECK(human_approved IN (0, 1))` | Always reset to `0` on save/update; set to `1` only by `/approve`. |
| `reviewer_notes` | `TEXT` | `NOT NULL DEFAULT ''` | Human reviewer sign-off notes. |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC timestamp. |

---

## 3. Readiness Scoring Rubric (`1.0` to `5.0`)

| Score | Anchor Definition | Quote & Page Rule |
| :--- | :--- | :--- |
| `1.0` | **No mention** of the requirement in the document. | `evidence_quote = ""`, `page_number = 0` |
| `2.0` | **Vague aspiration** only (no binding policy, target, or metric). | Verbatim quote + exact `page_number >= 1` |
| `3.0` | **Qualitative policy only** (governance or policy stated, no quantitative metric/target). | Verbatim quote + exact `page_number >= 1` |
| `4.0` | **Quantitative metric + target year** (missing baseline year, full methodology, or assurance). | Verbatim quote + exact `page_number >= 1` |
| `5.0` | **Audit-ready disclosure** (full quantitative metric + baseline year + methodology + assurance status). | Verbatim quote + exact `page_number >= 1` |

Intermediate half-point scores (e.g., `2.5`, `3.5`, `4.5`) follow the same quote/page rules as scores `> 1.0`.

---

## 4. Deterministic Python CLI Contracts (`src/`)

All scripts are invoked via the `.venv` Python interpreter and emit structured JSON (or `rich` tables for human display commands) with deterministic exit codes (`0` = success, non-zero = validation/gate error).

### 4.1 `src/ingestor.py`
- **Invocation:** `python src/ingestor.py [--dir data/raw_docs]`
- **Behavior:**
  1. Scans `--dir` for `.pdf` and `.csv` files.
  2. Computes SHA-256 `file_hash`; skips files whose hash already exists in `documents` (`"Skipped duplicate"`).
  3. **PDFs:** Extracts text page-by-page (1-indexed) via `pymupdf`. If total extracted text across all pages is empty (0 non-whitespace characters), aborts insertion for that file and prints `"ERROR: <filename> contains no extractable text (OCR required)."` without crashing the remaining batch.
  4. **CSVs:** Parses via `pandas` into a clean Markdown table stored in `document_pages` with `page_number = 1`. Catches `pandas.errors.ParserError` or empty DataFrames, logs a descriptive error, and continues the batch.

### 4.2 `src/db.py`
Subcommands:

1. `init [--config config/esrs_standards.yaml] [--db data/audit_pipeline.db]`
   - Creates all 5 tables if absent and upserts `esrs_requirements` from YAML.
2. `get-pending --mode <assess|verify|greenwash|draft>`
   - Returns JSON list of pending items (e.g., unassessed `(req_id, doc_id)` pairs plus their `document_pages` for `assess`).
3. `save-assessment` (accepts `--req-id`, `--doc-id`, `--score`, `--quote`, `--page`, `--gap-reason`, or `--json`)
   - **Mandatory Anti-Hallucination Guardrail:**
     - If `score == 1.0`: enforces `page_number == 0` and `evidence_quote == ""`.
     - If `score > 1.0`: enforces `1 <= page_number <= documents.page_count` and verifies that normalized-whitespace `evidence_quote` is a non-empty substring of normalized-whitespace `document_pages.content_text` for `(doc_id, page_number)`. Rejects invalid inserts with exit code `1`.
4. `get-assessments [--quantitative-only]`
   - Returns JSON rows joining `assessments`, `esrs_requirements`, and `documents` (plus ingested CSV `document_pages` when needed for `/verify`).
5. `update-verification --assess-id <id> --verified <0|1> --discrepancy <text>`
   - Persists `/verify` results (1% relative tolerance check).
6. `update-greenwash --assess-id <id> --flag <0|1> --reason <text>`
   - Persists `/greenwash` EU Green Claims findings.
7. `save-draft --req-id <id> --markdown <text>` (or `--file`)
   - Upserts `disclosure_drafts` and **always forces `human_approved = 0`**.
8. `approve-draft --req-id <id> [--notes <text>]`
   - Sets `human_approved = 1` and saves `reviewer_notes` after explicit interactive user confirmation.
9. `status`
   - Renders a `rich` terminal summary table showing requirements, scores, numeric verification, greenwash flags, and approval status.

### 4.3 `src/report_builder.py`
- **Invocation:** `python src/report_builder.py [--output output/verigreen_assurance_pack.pdf] [--approved-only]`
- **HITL Export Gate:**
  - Checks `SELECT req_id FROM disclosure_drafts WHERE human_approved = 0`.
  - If any unapproved drafts exist and `--approved-only` is NOT passed, exits with code `1` and lists all `req_id`s awaiting `/approve`.
  - When permitted, uses `fpdf2` to render an A4 PDF containing:
    1. Executive Readiness Summary Table
    2. Audit & Greenwashing Alerts
    3. Human-Approved ESRS/VS Disclosures

---

## 5. `config/esrs_standards.yaml` Schema

```yaml
version: "2026.1"
active_frameworks:
  - ESRS_2026
  - VS

requirements:
  - req_id: "ESRS-E1-1"
    framework: "ESRS_2026"        # ESRS_2026 | VS
    standard: "ESRS E1"
    topic: "Short topic title"
    requirement_text: "Detailed disclosure requirement..."
    is_quantitative: false
    mandatory: true
```
