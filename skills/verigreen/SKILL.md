---
name: verigreen
description: Master entry point for VeriGreen-ops. Use when the user runs /verigreen with a URL, company name, or sub-command (scan, assess, verify, greenwash, draft, status) to run the end-to-end CSRD and VSME readiness audit pipeline.
---

# VeriGreen-ops Master Orchestrator (`/verigreen`)

Interpret the user's input after `/verigreen` and execute the matching workflow using our deterministic Python scripts (`src/`) and modular rubrics (`skills/`):

## Mode 1: Full Auto-Pipeline (`/verigreen <https://url...>`)
When the user pastes a company sustainability webpage URL:
1. **Crawl & Ingest:** Run `python src/crawler.py --url "<URL>"` to extract landing-page text (`doc_type='web'`) and discover, download, and SHA-256 ingest all sustainability PDFs and emissions CSVs into `data/audit_pipeline.db`.
2. **Discover & Cross-Walk:** Read `skills/discover/SKILL.md` to extract the company profile and current sustainability frameworks, compare against `config/jurisdiction_matrix.yaml`, save via `python src/db.py save-profile`, print the Regulatory Cross-Walk table, and auto-seed matching rulebooks (`python src/db.py seed --yaml <path>`).
3. **Assess Readiness:** Read `skills/assess/SKILL.md` and evaluate every newly ingested `doc_id` against all requirements in `esrs_requirements` (`python src/db.py list-unassessed`), saving 1.0–5.0 scores and exact page citations via `python src/db.py save-assessment`.
4. **Verify & Greenwash Check:** Read `skills/verify/SKILL.md` and `skills/greenwash/SKILL.md`, cross-checking quantitative claims against any ingested CSV tables and flagging unsubstantiated claims under EU Green Claims rules.
5. **Draft & Present Summary:** Read `skills/draft/SKILL.md` to generate citation-backed drafts (`human_approved=0`), print a concise readiness summary table in the terminal, and ask the user which `req_id`s they want to approve (`python src/db.py approve --req-id <ID>`) before exporting the final A4 PDF.

## Mode 2: Sub-Commands
- `/verigreen` (no arguments) -> Show available modes and run `python src/db.py status`.
- `/verigreen batch` -> Run `python src/crawler.py --batch` across `config/portals.yaml`, then run `/assess`.
- `/verigreen draft <REQ_ID>` -> Load `skills/draft/SKILL.md` and compile the disclosure draft for `<REQ_ID>`.
- `/verigreen export` -> Run `python src/report_builder.py` (only exports human-approved drafts).