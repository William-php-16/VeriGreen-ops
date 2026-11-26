---
name: humanize
description: Edit ESRS and Voluntary SME disclosure drafts so they read like an experienced sustainability consultant wrote them, without altering facts, numbers, quotes, citations, or [DATA GAP] tags.
---

# `/humanize` — Consultant-Grade ESG Prose Polish

Rewrite drafted sustainability disclosures so they read cleanly, directly, and credibly, removing generic AI phrasing before saving to `disclosure_drafts`.

## Immutable Integrity Rule

**NEVER** alter, round, reword, or remove any of the following during humanization:
1. **Numbers, units, and percentages** (e.g., `1,420.5 tCO2e`, `12.4%`, `2025`, `1%`).
2. **Exact verbatim quotes** copied from source documents.
3. **Inline page citations** (`[Source: <filename>, p.<page_number>]`).
4. **`[DATA GAP: ...]` markers** and any recorded `numeric_discrepancy` details.

Every factual sentence must still end with its `[Source: <filename>, p.<page_number>]` citation.

## Strict Anti-AI Editing Rules

Apply every rule below to narrative prose:

1. **Zero Em Dashes:** Never use `—`. Replace em dashes with commas, periods, or parentheses.
2. **Ban AI Buzzwords:** Remove and rewrite any occurrence of `testament`, `pivotal`, `landscape`, `underscoring`, `fostering`, `holistic`, `robust`, `serves as`, `delve`, `showcasing` (and their inflections).
3. **Cut Filler & Superficial `-ing` Tack-Ons:** Delete padded lead-ins (such as "it is important to note that", "in order to", "as part of its ongoing commitment") and trailing `-ing` clauses that merely restate intent ("...demonstrating the company's dedication to sustainability").
4. **Avoid Rule-of-Three Padding & Negative Parallelisms:** Do not pad sentences with forced three-item adjective or noun lists, and avoid constructions like `not only ... but also` or `is not just ... it is ...`.
5. **Active Voice & Varied Sentence Length:** Prefer direct subject-verb-object sentences ("The company measured Scope 1 emissions across four plants...") and mix short, crisp statements with fuller explanatory sentences.

## Final Anti-AI Check

Before finalizing any humanized draft:
1. Scan the text for `—` and all banned buzzwords; replace any remaining matches.
2. Confirm every number, unit, percentage, verbatim quote, `[Source: ...]` citation, and `[DATA GAP: ...]` tag matches the pre-edit draft verbatim.
