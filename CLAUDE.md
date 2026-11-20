# VeriGreen-ops — Claude Code Instructions (`CLAUDE.md`)

@AGENTS.md

## Claude Code Session Directives

1. **Load Canonical Rules:** Always read and strictly follow [AGENTS.md](AGENTS.md), [DATA_CONTRACT.md](DATA_CONTRACT.md), and [config/company_context.md](config/company_context.md) before running audit actions.
2. **Skills Discovery:** Native skills are exposed via the `.claude/skills` directory junction pointing to `skills/`. If `.claude/skills` is missing, instruct the user to run `scripts/setup_windows.ps1` (Windows) or `scripts/setup_unix.sh` (macOS/Linux).
3. **Python Execution:** Always invoke the local virtual environment interpreter (`.venv\Scripts\python.exe` on Windows; `.venv/bin/python` on macOS/Linux) when running `src/ingestor.py`, `src/db.py`, or `src/report_builder.py`.
4. **Anti-Hallucination & HITL Enforcement:**
   - Every non-`1.0` assessment requires a verbatim `evidence_quote` and exact 1-indexed `page_number` verified by `src/db.py save-assessment`.
   - Every factual sentence in `/draft` must end with `[Source: <filename>, p.<page_number>]`, or insert `[DATA GAP: <action>]` when `readiness_score < 3.5` or `numeric_verified = 0`.
   - Never set `human_approved = 1` without explicit user confirmation in the terminal.
5. **File Boundaries:** Treat `src/`, `DATA_CONTRACT.md`, and root instruction files as system-owned during audit runs. User customization belongs in `config/esrs_standards.yaml`, `config/company_context.md`, and `data/raw_docs/`.
