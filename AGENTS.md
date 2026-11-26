# VeriGreen-ops - Universal CLI Agent Brain (`AGENTS.md`)

`VeriGreen-ops` is an open-source, **local-first native AI CLI agent** for **CSRD (Revised ESRS 2026, Delegated Regulation (EU) 2026/1563)** and **Voluntary SME Standard (VS, Delegated Regulation (EU) 2026/1560)** readiness auditing.

This file is the canonical instruction set loaded by terminal AI coding CLIs (`claude`, `gemini`, `codex`, Antigravity IDE). All agent sessions MUST follow these architectural, anti-hallucination, and governance rules without exception.

---

## 1. Local-First Native CLI Architecture

- **Zero External SaaS / Zero Extra LLM API Keys:** All reasoning runs inside the user's existing terminal AI CLI session. Never send company PDFs, CSVs, or draft disclosures to external APIs, cloud buckets, or third-party endpoints.
- **Deterministic Python & SQLite Backbone:** All file parsing, hashing, database persistence, validation, and PDF rendering MUST go through the deterministic Python scripts in `src/` using the project virtual environment (`.venv`).
  - Windows Python path: `.venv\Scripts\python.exe`
  - macOS / Linux Python path: `.venv/bin/python`
- **Never Bypass `src/db.py`:** Never mutate `data/audit_pipeline.db` with ad-hoc inline SQL (`UPDATE`, `DELETE`, `INSERT`) when a `src/db.py` subcommand exists. All state transitions MUST pass through `src/ingestor.py`, `src/db.py`, and `src/report_builder.py` so deterministic validation guardrails run every time.
- **Modular Skill Execution:** Internal skill modules live in `skills/<skill-name>/SKILL.md` (exposed to CLIs via `.claude/skills`, `.gemini/skills`, and `.agent/skills` directory junctions/symlinks) and are invoked through the unified `/verigreen <subcommand>` router:

| Command | Internal Module / Script | Purpose |
| :--- | :--- | :--- |
| `/verigreen` or `/verigreen status` | `src/dashboard.py` | Print the Rich audit dashboard and next recommended step. |
| `/verigreen <url>` | Full 6-stage pipeline | Run `crawl` -> `discover` -> `assess` -> `verify` -> `greenwash` -> `draft` + `humanize` -> `dashboard` (pausing at Human Gates 1 and 2). |
| `/verigreen crawl <url>` or `/verigreen crawl --batch` | `skills/crawl/SKILL.md`, `src/crawler.py` | Discover, download, and ingest sustainability PDFs/CSVs. |
| `/verigreen ingest` | `skills/ingest/SKILL.md`, `src/ingestor.py` | Parse local PDFs/CSVs in `data/raw_docs/` into SQLite and index `pages_fts`. |
| `/verigreen discover` | `skills/discover/SKILL.md`, `src/db.py save-profile` | Extract company profile, boundary exclusions, and auto-seed matched rulebooks. |
| `/verigreen assess` | `skills/assess/SKILL.md`, `src/db.py search-pages` & `save-assessment` | Score unassessed requirements (`1.0`-`5.0`) with verbatim quotes and boundary caps. |
| `/verigreen verify` | `skills/verify/SKILL.md`, `src/db.py update-verification` | Reconcile PDF numeric claims against CSV and YoY math within 1% tolerance. |
| `/verigreen greenwash` | `skills/greenwash/SKILL.md`, `src/db.py find-claims` & `update-greenwash` | Audit flagged marketing statements against EU Green Claims rules. |
| `/verigreen draft` | `skills/draft/SKILL.md` + `skills/humanize/SKILL.md`, `src/db.py save-draft` | Draft citation-backed prose with `[DATA GAP]` markers and humanize before saving (`human_approved = 0`). |
| `/verigreen draft-rulebook <jurisdiction_or_law>` | `skills/draft_rulebook/SKILL.md` | Generate, validate, and review a new YAML rulebook in `config/examples/`. |
| `/verigreen humanize <req_id\|all>` | `skills/humanize/SKILL.md` | Polish draft prose without altering numbers, units, quotes, citations, or `[DATA GAP]` tags. |
| `/verigreen approve <req_id\|all>` | `skills/approve/SKILL.md`, `src/db.py approve` | Interactive Human-in-the-Loop sign-off gate (`human_approved = 1`). |
| `/verigreen export` | `skills/export/SKILL.md`, `src/report_builder.py` | Render the A4 PDF Assurance Pack (blocked if `human_approved = 0`). |

---

## 2. Strict Anti-Hallucination & Citation Provenance Rules

Every audit finding and drafted disclosure MUST be 100% traceable to ingested source evidence:

1. **Verbatim Quote Requirement (`save-assessment`):**
   - For any `readiness_score > 1.0`, you MUST provide an **exact verbatim substring** (`evidence_quote`) copied from `document_pages.content_text` and the exact 1-indexed integer `page_number`.
   - For `readiness_score == 1.0` (no mention found), set `evidence_quote = ""` and `page_number = 0`.
   - Never paraphrase, truncate with invented ellipses (`...`), or guess a page number. `src/db.py save-assessment` verifies that `page_number <= documents.page_count` and that `evidence_quote` matches `document_pages.content_text` (normalized whitespace) and will reject invalid records.
2. **Mandatory Inline Citations (`/verigreen draft`):**
   - Every factual sentence in `disclosure_drafts.draft_markdown` MUST end with `[Source: <filename>, p.<page_number>]` (for CSV sources, `p.1`).
   - Uncited factual claims are strictly prohibited.
3. **Mandatory `[DATA GAP]` Markers (No Invented Numbers):**
   - If a requirement has `readiness_score < 3.5` OR `numeric_verified = 0`, you MUST NOT invent, extrapolate, or smooth over missing metrics, targets, or baseline years.
   - Instead, insert an explicit tag: `[DATA GAP: <specific missing datapoint, baseline, or numeric discrepancy>]`.
4. **Quantitative Cross-Verification Tolerance (`1%`):**
   - For every requirement with `is_quantitative = 1`, reconcile narrative claims in PDFs against ingested CSV Markdown tables (`doc_type = 'csv'`).
   - Mark `numeric_verified = 1` ONLY if claimed and calculated values agree within **1% relative tolerance**. Otherwise mark `numeric_verified = 0` and record the exact calculation in `numeric_discrepancy`.
5. **EU Green Claims Anti-Greenwashing Screen:**
   - Flag any quote containing vague or unsubstantiated environmental claims (such as `"carbon neutral"`, `"climate positive"`, `"100% eco-friendly"`, `"zero impact"`, `"net-zero packaging"`, or offset-only assertions lacking gross emissions, LCA boundaries, and registry verification) by setting `greenwash_flag = 1` with a specific `greenwash_reason`.
6. **Human-in-the-Loop (HITL) Sign-Off Gate:**
   - All drafts created by `/verigreen draft` MUST initialize with `human_approved = 0`.
   - **NEVER** set `human_approved = 1` without explicit confirmation from the human user in the terminal during `/verigreen approve`.
   - `src/report_builder.py` MUST refuse to export the A4 PDF Assurance Pack whenever unapproved drafts exist (unless `--approved-only` is explicitly requested by the user).

---

## 3. System vs. User-Editable File Boundaries

Respect strict ownership boundaries between core engine files and user-configurable inputs:

| Path / Directory | Owner / Classification | Editing Policy |
| :--- | :--- | :--- |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | **System (Core Brain)** | Do not modify during normal audit runs. |
| `DATA_CONTRACT.md` | **System (Schema & CLI Contract)** | Authoritative contract for SQLite & JSON/CLI interfaces. |
| `src/` (`db.py`, `ingestor.py`, `report_builder.py`) | **System (Deterministic Engine)** | Do not edit during audit runs; users should never need to edit `src/` to change ESRS/VS rules. |
| `scripts/` (`setup_*`, `create_sample_data.py`) | **System (Tooling & Fixtures)** | Setup and synthetic corpus generators. |
| `config/esrs_standards.yaml` | **User-Editable (Regulatory Rulebook)** | Users customize active frameworks (`ESRS_2026`, `VS`), thresholds, or datapoints here. |
| `config/company_context.md` | **User-Editable (Organization Profile)** | Users edit entity name, employee count, turnover, reporting year, and materiality scope. |
| `data/raw_docs/` | **User-Editable (Source Evidence)** | Users drop corporate PDFs and emissions CSVs here for `/verigreen ingest`. |
| `skills/<name>/SKILL.md` | **Modular Extensible Skills** | Users and contributors can add or tailor audit skills (see `skills/ADDING_A_SKILL.md`). |
| `data/audit_pipeline.db`, `output/*.pdf`, `data/sample/*` | **Generated Runtime Artifacts** | Managed by `src/` and `scripts/` only; never hand-edit. |

---

## 4. Session Pre-Flight Checklist

Before executing any audit workflow:
1. Read `DATA_CONTRACT.md` if inspecting or calling `src/db.py`, `src/ingestor.py`, or `src/report_builder.py`.
2. Read `config/company_context.md` to understand the reporting entity's framework scope (`ESRS_2026` vs. `VS`), fiscal year, and materiality boundaries.
3. Verify `.venv` is used for all Python commands.

## Python Execution
Always run Python scripts using `.venv\Scripts\python.exe` (or `.venv/bin/python` on macOS/Linux) instead of bare `python` so commands work without manual virtual environment activation.