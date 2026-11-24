# VeriGreen-ops

**Open-Source, Local-First Native AI CLI Agent for CSRD (Revised ESRS 2026) & Voluntary SME Standard (VS) Readiness Auditing**

`VeriGreen-ops` turns your existing terminal AI coding CLI (**Claude Code**, **Gemini CLI**, **Codex CLI**, or **Antigravity IDE**) into a zero-infrastructure sustainability auditing and assurance-readiness agent backed by deterministic Python (`pymupdf`, `pandas`, `fpdf2`, `rich`) and local SQLite (`data/audit_pipeline.db`).

- **Zero External SaaS / Zero Extra LLM API Keys:** Corporate PDFs, emissions CSVs, and draft disclosures never leave your local machine.
- **Strict Anti-Hallucination Provenance:** Every readiness score `> 1.0` requires an exact verbatim quote and 1-indexed page number; every drafted sentence must end with `[Source: <filename>, p.<page_number>]` or an explicit `[DATA GAP: <action required>]` tag.
- **Human-in-the-Loop (HITL) Export Gate:** `src/report_builder.py` refuses to render the final A4 PDF Assurance Pack (`exit 1`) whenever any draft in `disclosure_drafts` has `human_approved = 0` (unless `--approved-only` is explicitly passed).

---

## Architecture Overview

```text
  Public ESG Portals             User Drop Zone                 User Rulebook & Profile
  config/portals.yaml / --url    data/raw_docs/ (*.pdf, *.csv)  config/esrs_standards.yaml
         |                              |                       config/company_context.md
         v                              v                                  |
  +------------------+          +------------------+              +------------------+
  |  src/crawler.py  | -------> | src/ingestor.py  |              |    src/db.py     |
  | httpx + bs4 link |          | SHA-256 dedup,   | -----------> | SQLite Schema &  |
  | discovery        |          | PyMuPDF & Pandas |              | Audit State CRUD |
  +------------------+          +------------------+              +------------------+
                                                                            ^
                                                                            | (invoked via .venv)
  +-------------------------------------------------------------------------+------------------+
  | Native CLI Agent Brain (AGENTS.md / CLAUDE.md / GEMINI.md)                                 |
  | Modular Skills: skills/<name>/SKILL.md                                                     |
  |   /crawl -> /ingest -> /assess -> /verify -> /greenwash -> /draft -> /approve -> /export   |
  +-------------------------------------------------------------------------+------------------+
                                                                            |
                                                                            v
                                                                  +--------------------+
                                                                  | src/report_builder |
                                                                  | HITL Gate + fpdf2  |
                                                                  +--------------------+
                                                                            |
                                                                            v
                                                             output/verigreen_assurance_pack.pdf
```

### Repository Layout

| Path | Role |
| :--- | :--- |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | Cross-CLI agent brain enforcing citation, numeric tolerance, and HITL rules |
| `DATA_CONTRACT.md` | Authoritative SQLite schema, 1.0–5.0 rubric, and CLI contract |
| `config/esrs_standards.yaml` | User-editable regulatory rulebook (`ESRS_2026` and `VS` modules) |
| `config/portals.yaml` | User-editable corporate sustainability portal URLs for `src/crawler.py --batch` |
| `config/company_context.md` | Organization profile, consolidation boundaries, and fiscal year |
| `src/crawler.py` | Deterministic ESG report crawler (`httpx` + `beautifulsoup4`) feeding `ingest_file()` |
| `src/ingestor.py` | Deterministic PDF/CSV ingestor with SHA-256 deduplication |
| `src/db.py` | SQLite schema initialization, seeding, assessment, draft, and approval CLI |
| `src/report_builder.py` | Pure-Python `fpdf2` A4 PDF Assurance Pack renderer with HITL gate |
| `skills/<name>/SKILL.md` | Modular Agent Skills exposed to `.claude/skills` and `.gemini/skills` |
| `scripts/` | Windows/Unix setup scripts and synthetic benchmark generator (`create_sample_data.py`) |

---

## Quickstart

### 1. Windows (PowerShell)

```powershell
git clone <your-fork-or-repo-url> VeriGreen-ops
cd VeriGreen-ops

# Creates .venv, installs requirements.txt, and links .claude\skills & .gemini\skills -> skills\
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1

# Optional: generate synthetic sample PDF & CSV in data/sample/
.\.venv\Scripts\python.exe scripts\create_sample_data.py

# Initialize SQLite database & seed config/esrs_standards.yaml
.\.venv\Scripts\python.exe src\db.py init

# Launch your terminal AI CLI (Claude Code or Gemini CLI)
claude
# or: gemini
```

### 2. macOS / Linux (Bash)

```bash
git clone <your-fork-or-repo-url> VeriGreen-ops
cd VeriGreen-ops

# Creates .venv, installs requirements.txt, and symlinks .claude/skills & .gemini/skills -> ../skills
bash scripts/setup_unix.sh

# Optional: generate synthetic sample PDF & CSV in data/sample/
.venv/bin/python scripts/create_sample_data.py

# Initialize SQLite database & seed config/esrs_standards.yaml
.venv/bin/python src/db.py init

# Launch your terminal AI CLI
claude
# or: gemini
```

---

## Audit Workflow (Slash Commands)

Inside `claude` or `gemini`, run the modular skills in sequence:

| Command | Skill File | Purpose |
| :--- | :--- | :--- |
| `/crawl` | [`skills/crawl/SKILL.md`](skills/crawl/SKILL.md) | Discovers & downloads `.pdf`/`.csv` reports from URLs or `config/portals.yaml` and deduplicates via `ingest_file()` |
| `/ingest` | [`skills/ingest/SKILL.md`](skills/ingest/SKILL.md) | SHA-256 deduplication, page-by-page PDF indexing, and CSV-to-Markdown conversion |
| `/assess` | [`skills/assess/SKILL.md`](skills/assess/SKILL.md) | 1.0–5.0 readiness scoring with exact verbatim quotes and 1-indexed page numbers |
| `/verify` | [`skills/verify/SKILL.md`](skills/verify/SKILL.md) | Reconciles quantitative PDF claims against CSV tables (1% relative tolerance) |
| `/greenwash` | [`skills/greenwash/SKILL.md`](skills/greenwash/SKILL.md) | Screens quotes against EU Green Claims substantiation rules |
| `/draft` | [`skills/draft/SKILL.md`](skills/draft/SKILL.md) | Compiles ESRS/VS prose with `[Source: file, p.X]` and `[DATA GAP: ...]` tags |
| `/approve` | [`skills/approve/SKILL.md`](skills/approve/SKILL.md) | Displays drafts and warnings in terminal for explicit human sign-off (`human_approved = 1`) |
| `/export` | [`skills/export/SKILL.md`](skills/export/SKILL.md) | Renders the 3-section A4 PDF Assurance Pack via `src/report_builder.py` |
| `/status` | [`skills/status/SKILL.md`](skills/status/SKILL.md) | Prints SQLite pipeline counts and readiness state |

Want to add a custom check (e.g., `/eudr-check` or `/cbam-check`)? Follow [`skills/ADDING_A_SKILL.md`](skills/ADDING_A_SKILL.md).

### Web Portal Crawling (`src/crawler.py` & `config/portals.yaml`)

Fetch public corporate sustainability PDFs/CSVs directly into `data/raw_docs/` with automatic ESG keyword filtering and SHA-256 deduplication:

```powershell
# Single sustainability portal or direct PDF/CSV URL
.\.venv\Scripts\python.exe src\crawler.py --url "https://example.com/sustainability-reports"

# Batch crawl all enabled portals in config/portals.yaml
.\.venv\Scripts\python.exe src\crawler.py --batch

# Include all .pdf/.csv links on a page without ESG keyword filtering
.\.venv\Scripts\python.exe src\crawler.py --url "https://example.com/reports" --all-files
```

---

## Sample Terminal Output (`data/sample/`)

Running the deterministic pipeline on the synthetic benchmark corpus (`sample_sustainability_report.pdf` + `sample_emissions.csv`):

```text
> .\.venv\Scripts\python.exe src\db.py init
Initialized data\audit_pipeline.db and seeded 9 requirements.

> .\.venv\Scripts\python.exe src\ingestor.py --dir data\sample
[INGESTED] sample_emissions.csv -> doc_id=sample_emissions_acdc2533 (1 pages)
[INGESTED] sample_sustainability_report.pdf -> doc_id=sample_sustainability_report_239426d0 (3 pages)

> .\.venv\Scripts\python.exe src\ingestor.py --dir data\sample
[SKIPPED]  sample_emissions.csv (already ingested as sample_emissions_acdc2533)
[SKIPPED]  sample_sustainability_report.pdf (already ingested as sample_sustainability_report_239426d0)

> .\.venv\Scripts\python.exe src\report_builder.py
EXPORT BLOCKED (HITL Gate): Unapproved drafts detected (human_approved = 0):
  - ESRS-E1-1
  - ESRS-E1-4
  - ESRS-E1-6
  - ESRS-E5-5
  - ESRS-G1-1
  - ESRS-S2-1
Run /approve (or `python src/db.py approve --req-id <ID>`) before exporting, or pass --approved-only to export only approved drafts.

> .\.venv\Scripts\python.exe src\db.py approve --req-id ESRS-E1-6 --notes "Reviewed citations and DATA GAP markers."
Approved disclosure draft for ESRS-E1-6.

> .\.venv\Scripts\python.exe src\report_builder.py
Exported A4 Assurance Pack -> output\verigreen_assurance_pack.pdf (6 approved disclosures).

> .\.venv\Scripts\python.exe src\db.py status
{
  "db_path": "data\\audit_pipeline.db",
  "counts": {
    "documents": 2,
    "document_pages": 4,
    "esrs_requirements": 9,
    "assessments": 9,
    "disclosure_drafts": 6
  }
}
```

### Rendered A4 PDF Sections (`output/verigreen_assurance_pack.pdf`)

1. **Executive Readiness Matrix** — Requirement-by-requirement scores (`1.0`–`5.0`), quantitative reconciliation status (`VERIFIED` / `MISMATCH` / `N/A`), EU Green Claims status (`OK` / `FLAGGED`), and draft approval state.
2. **Numeric & Greenwashing Audit Alerts** — Surfaces planted discrepancies (e.g., `ESRS-E1-6`: narrative claims 22% YoY Scope 1 reduction vs. 7.69% calculated from `sample_emissions.csv`) and flagged claims (e.g., `ESRS-E5-5`: `"100% carbon neutral packaging"`).
3. **Human-Approved ESRS / VS Disclosures** — Formal prose with `[Source: <filename>, p.<page_number>]` inline citations, `[DATA GAP: ...]` remediation items, and reviewer sign-off notes.
