---
name: adding-a-skill
description: Contributor guide for authoring new modular slash-command audit skills in VeriGreen-ops.
---

# Adding a Custom Audit Skill to `VeriGreen-ops`

`VeriGreen-ops` follows the open **Agent Skills (`SKILL.md`)** specification. Every folder inside `skills/<skill-name>/` containing a `SKILL.md` file with valid YAML frontmatter is automatically exposed as a `/<skill-name>` slash command in **Claude Code** (via `.claude/skills`) and **Gemini CLI** (via `.gemini/skills`)—with **zero edits** to `src/`.

---

## 1. Architecture Boundaries for Contributors

Before creating a new skill, keep the core separation of responsibilities intact (see `AGENTS.md` and `DATA_CONTRACT.md`):

- **Regulatory Rulebook (`config/esrs_standards.yaml`):** Add new compliance requirements (e.g., `EUDR-1`, `CBAM-1`, `CSDDD-1`) here, then seed them via `src/db.py init`.
- **Modular Skill Prompt (`skills/<name>/SKILL.md`):** Encode the auditing rubric, cross-checks, and CLI workflow instructions here.
- **Deterministic Engine (`src/`):** Reuse existing `src/ingestor.py`, `src/db.py`, and `src/report_builder.py` subcommands so SHA-256 deduplication, SQLite persistence, and HITL export gates remain deterministic.

---

## 2. Step-by-Step Guide

### Step 1: Add Custom Requirements (Optional)

If your skill audits new regulatory datapoints (for example, EU Deforestation Regulation plot traceability or CBAM embedded emissions), append them to `config/esrs_standards.yaml`:

```yaml
  - req_id: "EUDR-1"
    framework: "ESRS_2026"
    standard: "EUDR"
    topic: "Geolocation & Deforestation-Free Cut-off Verification"
    requirement_text: >
      Disclose supplier polygon/plot coordinates, harvest dates relative to the
      31 December 2020 deforestation cut-off date, and due diligence reference numbers
      for relevant cattle, cocoa, coffee, palm oil, rubber, soy, and wood inputs.
    is_quantitative: false
    mandatory: true
```

Re-seed the SQLite requirements table without wiping existing documents or assessments:

- **Windows:** `.\.venv\Scripts\python.exe src/db.py init`
- **macOS / Linux:** `.venv/bin/python src/db.py init`

### Step 2: Create `skills/<name>/SKILL.md`

Create a directory `skills/<name>/` (lowercase letters, digits, and hyphens only) and add `SKILL.md` with valid YAML frontmatter:

```markdown
---
name: eudr-check
description: Audit ingested supplier declarations and commodity logs against EU Deforestation Regulation (EUDR) cut-off and geolocation rules.
---

# `/eudr-check` — EUDR Supply Chain & Geolocation Audit

Evaluate ingested documents and CSV supplier logs against `EUDR-*` requirements in `data/audit_pipeline.db`.
```

### Step 3: Enforce `VeriGreen-ops` Non-Negotiable Rules

Every custom skill MUST enforce these four guardrails:

1. **Use the Local `.venv` Python Interpreter:** Always invoke `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (macOS/Linux); never call external APIs or mutate `data/audit_pipeline.db` with ad-hoc inline SQL writes.
2. **Exact Verbatim Page Citations:** Every finding stored via `src/db.py save-assessment` with `readiness_score > 1.0` must include an exact verbatim substring `evidence_quote` and 1-indexed `page_number`. Every drafted sentence must end with `[Source: <filename>, p.<page_number>]`.
3. **Explicit `[DATA GAP]` Markers:** Never invent missing supplier coordinates, emission factors, or baseline dates—insert `[DATA GAP: <specific missing evidence>]`.
4. **Preserve the HITL Gate:** Any generated draft must be saved with `human_approved = 0` via `src/db.py save-draft` and approved only after explicit terminal confirmation.

### Step 4: Verify Skill Discovery

1. Ensure the skill junctions/symlinks are active:
   - **Windows:** `powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1`
   - **macOS / Linux:** `bash scripts/setup_unix.sh`
2. Validate YAML frontmatter cleanly:
   ```powershell
   .\.venv\Scripts\python.exe -c "import yaml, pathlib; print(yaml.safe_load(pathlib.Path('skills/eudr-check/SKILL.md').read_text(encoding='utf-8').split('---')[1]))"
   ```
3. Launch `claude` or `gemini` inside the repository root and confirm `/<skill-name>` appears in the slash-command list.

---

## 3. Example Skill Template (`skills/cbam-check/SKILL.md`)

```markdown
---
name: cbam-check
description: Reconcile EU Carbon Border Adjustment Mechanism (CBAM) embedded emissions declarations against supplier CSV smelter/kiln logs.
---

# `/cbam-check` — CBAM Embedded Emissions Reconciliation

Audit `CBAM-*` requirements by cross-checking declared direct and indirect specific embedded emissions (tCO2e per tonne of goods) against ingested supplier production CSVs.

## Steps

1. Inspect unassessed `CBAM-*` pairs via `.venv\Scripts\python.exe src/db.py list-unassessed` (or `get-pending`).
2. Read extracted pages via `.venv\Scripts\python.exe src/db.py get-pages --doc-id <DOC_ID>`.
3. Apply the 1.0–5.0 readiness rubric and persist verbatim quotes via `src/db.py save-assessment`.
4. Flag discrepancies exceeding 1% relative tolerance and insert `[DATA GAP: Missing installation-level verification or default value fallback required]` for unverified figures.
```
