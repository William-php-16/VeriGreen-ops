---
name: verigreen
description: Run the VeriGreen-ops CSRD & VSME readiness audit pipeline (crawl/ingest, assess, verify, greenwash check, draft, approve, export).
---

# Workflow: verigreen

Follow [skills/verigreen/SKILL.md](../../skills/verigreen/SKILL.md) and the guardrails in [AGENTS.md](../../AGENTS.md) using the local `.venv` Python interpreter (`.venv\Scripts\python.exe` on Windows; `.venv/bin/python` on macOS/Linux).

- **With `<URL>`:** Run the full pipeline (`src/crawler.py --url "<URL>"` -> `/discover` -> `/assess` -> `/verify` -> `/greenwash` -> `/draft`), then ask the user which `req_id`s to approve before `/export`.
- **With sub-command (`batch`, `draft <REQ_ID>`, `export`, or individual stages `ingest`/`assess`/`verify`/`greenwash`/`approve`):** Execute the matching mode or `skills/<stage>/SKILL.md`.
- **With no arguments:** Show available modes and run `src/db.py status`.
