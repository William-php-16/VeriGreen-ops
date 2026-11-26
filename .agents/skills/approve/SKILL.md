---
name: approve
description: Display unapproved ESRS/VS disclosure drafts, citations, data gaps, and greenwashing or numeric warnings in the terminal for explicit human sign-off.
---

# `/approve` — Human-in-the-Loop (HITL) Sign-Off Gate

Present unapproved disclosure drafts and all associated audit warnings in the terminal and record explicit human approval via `src/db.py approve-draft`.

## Critical Governance Rule

**NEVER** call `approve-draft` or set `human_approved = 1` automatically, silently, or without an explicit confirmation from the human user in the current terminal session.

## Review & Approval Workflow

1. **Fetch Drafts & Linked Audit Warnings:**
   Inspect unapproved rows in `disclosure_drafts` (`human_approved = 0`) alongside their linked `assessments` (`readiness_score`, `numeric_verified`, `numeric_discrepancy`, `greenwash_flag`, `greenwash_reason`) by querying `src/db.py get-assessments` and `src/db.py status` (or `get-pending --mode approve` if available).
2. **Display Full Review Packet in Terminal (FR-6.1):**
   For each unapproved `req_id` (or the specific `req_id` requested by the user), clearly display:
   - `req_id`, `standard`, `topic`, and current `readiness_score`
   - **Numeric Verification Status:** Warn prominently if `numeric_verified = 0` and print `numeric_discrepancy`
   - **Greenwashing Alerts:** Warn prominently if `greenwash_flag = 1` and print `greenwash_reason`
   - **Full `draft_markdown`:** Including every `[Source: <filename>, p.<page_number>]` citation and `[DATA GAP: ...]` marker
3. **Prompt Human Reviewer:**
   Ask the user explicitly whether they approve the draft (`Approve`, `Reject / Request Revision`, or `Skip`) and invite optional `reviewer_notes` (defaulting to `"Verified against source evidence"` only if the user approves without custom notes).
4. **Persist Approval Only After Explicit Confirmation:**
   For each explicitly approved `req_id`, run `src/db.py approve-draft`:
   - **Windows:**
     ```powershell
     .\.venv\Scripts\python.exe src/db.py approve-draft --req-id "<REQ_ID>" --notes "<REVIEWER_NOTES>"
     ```
   - **macOS / Linux:**
     ```bash
     .venv/bin/python src/db.py approve-draft --req-id "<REQ_ID>" --notes "<REVIEWER_NOTES>"
     ```

   If the user rejects or requests edits to a draft, do NOT approve it; help revise the draft via `/draft` so it remains gated (`human_approved = 0`) until re-reviewed.

## Output

Report which `req_id` drafts were approved (`human_approved = 1`), which remain pending, and indicate whether `/export` is now unblocked.
