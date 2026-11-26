---
name: discover
description: Extract company profile and current sustainability frameworks from ingested web/PDF pages, map applicable regulations and crosswalk blind spots via config/jurisdiction_matrix.yaml, save to company_profiles, and auto-seed matching rulebooks.
---

# `/discover` — Regulatory Applicability & Framework Cross-Walk

Run immediately after `/crawl` (or `/ingest`) and before `/assess` so the audit uses the exact rulebooks required by the entity's jurisdiction, size, and sector.

## Steps

1. **Inspect Ingested Pages:** Query `documents` (`doc_type = 'web'` first, then `'pdf'`) via `python src/db.py get-pages --doc-id <doc_id>` to extract only observed facts:
   - `company_name`, `source_url`, `country` (e.g., `NL`, `EU`, `SK`), `sector` (e.g., `agrifood`, `finance`, `manufacturing`), `employee_count` (integer or `null` if unstated), `consolidation_approach`, `boundary_exclusions`.
   - `detected_frameworks`: voluntary or existing foundations mentioned on the landing page or reports (e.g., `GRI`, `ISO 14001`, `TCFD`, `RSPO`, `SBTi`, `B Corp`, `VSME`, `CSRD`).
   - When adding new documents to an existing audit, run `show-profile --company-id <ID>` first so you only pass newly discovered frameworks, regulations, and exclusions instead of duplicating prior entries.

2. **Evaluate `config/jurisdiction_matrix.yaml`:**
   - Match `(country, employee_count, sector)` against `rules` (`min_employees` / `max_employees`, `country_region`, `sector`) to determine `applicable_regulations` and the required YAML rulebook paths in `config/` and `config/examples/`.
   - Treat `EU` rules (such as `EU-EMPCO-GREEN-CLAIMS`) as applying across all EU member states (including `NL`, `SK`, `DE`, `FR`), and trigger Netherlands-only rules (`NL-ACM-GREEN-CLAIMS`) only when `country` is `NL`.
   - **Unsupported Jurisdiction / Sector Fallback:** If the company's `country` or `sector` has no matching rulebook in `config/jurisdiction_matrix.yaml`, report the coverage gap to the user and offer to run `skills/draft_rulebook/SKILL.md` (`/draft-rulebook`) to generate and validate a new YAML rulebook before `/assess`.
   - For each entry in `detected_frameworks` present under `crosswalks`, record what it covers (`covers`) and its legal gaps (`blind_spots`).

3. **Save Company Profile (Non-Destructive Merge):** Persist new findings via:
   - **Windows:** `.\.venv\Scripts\python.exe src\db.py save-profile --json "<JSON>"`
   - **macOS / Linux:** `.venv/bin/python src/db.py save-profile --json "<JSON>"`
   Include `company_name`, `source_url`, `country`, `sector`, `employee_count`, `consolidation_approach`, `boundary_exclusions`, `detected_frameworks`, `applicable_regulations`, and `crosswalk_summary`. `save-profile` merges `detected_frameworks`, `applicable_regulations`, and `boundary_exclusions` case-insensitively and preserves existing non-empty scalar fields unless `--overwrite` is passed. Only pass `--overwrite` when resetting a company profile from scratch.

4. **Print Compact Regulatory Cross-Walk Table:** Display a concise Markdown table summarizing:
   - Detected Foundation / Framework | Overlaps (`covers`) | Legal Blind Spots (`blind_spots`) | Applicable Mandatory Regulation & Rulebook

5. **Auto-Seed All Matched Rulebooks Before `/assess`:**
   - For every matched rulebook file that exists in `config/` or `config/examples/` (without wiping existing data), run:
     - **Windows:** `.\.venv\Scripts\python.exe src/db.py seed --yaml <rulebook_path>`
     - **macOS / Linux:** `.venv/bin/python src/db.py seed --yaml <rulebook_path>`
   - Do not stop at `config/esrs_standards.yaml` when a more specific rulebook (such as `config/examples/vsme_value_chain_shield.yaml` or `config/examples/acm_dutch_green_claims.yaml`) matches the entity's profile. Complete all `seed` calls before proceeding to `/assess`.
