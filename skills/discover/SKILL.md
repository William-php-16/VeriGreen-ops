---
name: discover
description: Extract company profile and current sustainability frameworks from ingested web/PDF pages, map applicable regulations and crosswalk blind spots via config/jurisdiction_matrix.yaml, save to company_profiles, and auto-seed matching rulebooks.
---

# `/discover` — Regulatory Applicability & Framework Cross-Walk

Run immediately after `/crawl` (or `/ingest`) and before `/assess` so the audit uses the exact rulebooks required by the entity's jurisdiction, size, and sector.

## Steps

1. **Inspect Ingested Pages:** Query `documents` (`doc_type = 'web'` first, then `'pdf'`) via `python src/db.py get-pages --doc-id <doc_id>` to extract only observed facts:
   - `company_name`, `source_url`, `country` (e.g., `NL`, `EU`), `sector` (e.g., `agrifood`, `finance`, `manufacturing`), `employee_count` (integer or `null` if unstated).
   - `detected_frameworks`: voluntary or existing foundations mentioned on the landing page or reports (e.g., `GRI`, `ISO 14001`, `TCFD`, `RSPO`, `SBTi`, `B Corp`, `VSME`, `CSRD`).

2. **Evaluate `config/jurisdiction_matrix.yaml`:**
   - Match `(country, employee_count, sector)` against `rules` (`min_employees` / `max_employees`, `country_region`, `sector`) to determine `applicable_regulations` and the required YAML rulebook paths in `config/` and `config/examples/`.
   - For each entry in `detected_frameworks` present under `crosswalks`, record what it covers (`covers`) and its legal gaps (`blind_spots`).

3. **Save Company Profile:** Persist the result via:
   - **Windows:** `.\.venv\Scripts\python.exe src\db.py save-profile --json "<JSON>"`
   - **macOS / Linux:** `.venv/bin/python src/db.py save-profile --json "<JSON>"`
   Include `company_name`, `source_url`, `country`, `sector`, `employee_count`, `detected_frameworks`, `applicable_regulations`, and `crosswalk_summary`.

4. **Print Compact Regulatory Cross-Walk Table:** Display a concise Markdown table summarizing:
   - Detected Foundation / Framework | Overlaps (`covers`) | Legal Blind Spots (`blind_spots`) | Applicable Mandatory Regulation & Rulebook

5. **Auto-Seed Matching Rulebooks:** For every matched rulebook YAML path (without wiping existing data), run:
   - **Windows:** `.\.venv\Scripts\python.exe src\db.py seed --yaml "<rulebook_path>"`
   - **macOS / Linux:** `.venv/bin/python src/db.py seed --yaml "<rulebook_path>"`
