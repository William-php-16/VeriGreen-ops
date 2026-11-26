---
name: draft-rulebook
description: Generate and validate a new YAML regulatory rulebook in config/examples/ for an uncovered jurisdiction or sector
---

# `/draft-rulebook` : Generate & Validate Regulatory Rulebook

Use this workflow when `/discover` finds a country or sector with no matching rulebook in `config/jurisdiction_matrix.yaml`.

## Steps

1. **Inspect Existing Schema:** Read an existing file in `config/examples/` (for example `config/examples/vsme_value_chain_shield.yaml`) to match the exact YAML structure (`version`, `active_frameworks`, `requirements` with `req_id`, `framework`, `standard`, `topic`, `requirement_text`, `keywords`, `is_quantitative`, `mandatory`).
2. **Draft 5 to 10 Enforceable Requirements:** Write 5 to 10 concrete requirements for the target regulation, citing real statutory articles or thresholds. Never invent laws or use em dashes. Include a non-empty `keywords` list of search terms on each requirement for SQLite FTS5 pre-filtering.
3. **Save Under `config/examples/` Only:** Sanitize the filename to lowercase `[a-z0-9_]` and write only to `config/examples/<slug>.yaml` (reject any path escaping `config/examples/`).
4. **Validate Schema:** Run the deterministic validator and fix any reported errors until it exits `0`:
   - **Windows:** `.\.venv\Scripts\python.exe src/db.py validate-rulebook --yaml config/examples/<slug>.yaml`
   - **macOS / Linux:** `.venv/bin/python src/db.py validate-rulebook --yaml config/examples/<slug>.yaml`
5. **Human-in-the-Loop Gate:** Present the drafted requirements and proposed `config/jurisdiction_matrix.yaml` rule entry to the user and ask for explicit confirmation before updating `config/jurisdiction_matrix.yaml` and seeding via `src/db.py seed --yaml config/examples/<slug>.yaml`.
