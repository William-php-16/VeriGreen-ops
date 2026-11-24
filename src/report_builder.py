import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

try:
    from db import DEFAULT_DB_PATH, get_connection
except ImportError:
    from src.db import DEFAULT_DB_PATH, get_connection

DEFAULT_OUTPUT_PATH = Path("output/verigreen_assurance_pack.pdf")
DEFAULT_CONTEXT_PATH = Path("config/company_context.md")

# Replace common Unicode punctuation/symbols with ASCII/Latin-1 equivalents so
# core PDF fonts never raise FPDFUnicodeEncodingException on arbitrary source text.
_UNICODE_REPLACEMENTS = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2022": "*",    # bullet
    "\u2026": "...",  # ellipsis
    "\u20ac": "EUR ", # euro sign
    "\u2265": ">=",   # >=
    "\u2264": "<=",   # <=
    "\u2192": "->",   # right arrow
    "\u2082": "2",    # subscript 2 (e.g. CO2)
    "\u00b0": " deg", # degree symbol
    "\u00a0": " ",    # non-breaking space
}


def latin1_safe(text: str | None) -> str:
    """Normalize text for safe rendering with standard FPDF Latin-1 core fonts."""
    if not text:
        return ""
    cleaned = str(text)
    for src_char, repl in _UNICODE_REPLACEMENTS.items():
        cleaned = cleaned.replace(src_char, repl)
    return cleaned.encode("latin-1", errors="replace").decode("latin-1")


def load_entity_summary(context_path: Path = DEFAULT_CONTEXT_PATH) -> dict[str, str]:
    """Extract basic organization metadata from config/company_context.md if present."""
    info = {
        "entity": "Configured Reporting Entity",
        "fiscal_year": "N/A",
        "framework": "Revised ESRS 2026 / VS",
    }
    if not context_path.exists():
        return info

    content = context_path.read_text(encoding="utf-8")
    patterns = {
        "entity": r"\*\*Legal Entity Name:\*\*\s*(.+)",
        "fiscal_year": r"\*\*Reporting Fiscal Year:\*\*\s*(.+)",
        "framework": r"\*\*Primary Framework:\*\*\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            info[key] = latin1_safe(match.group(1).strip())
    return info


class AssurancePackPDF(FPDF):
    """A4 Assurance Pack renderer with persistent header and page numbering footer."""

    def __init__(self, entity_name: str, generated_at: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.entity_name = latin1_safe(entity_name)
        self.generated_at = latin1_safe(generated_at)
        self.alias_nb_pages()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 16, 15)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 110, 120)
        self.cell(
            0,
            6,
            f"VeriGreen-ops CSRD / VS Assurance Pack | {self.entity_name}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="R",
        )
        self.set_draw_color(210, 215, 220)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 118, 126)
        self.cell(
            0,
            8,
            f"Local-First Deterministic Audit Trail | Generated {self.generated_at} | Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def section_heading(self, title: str) -> None:
        self.ln(4)
        self.set_fill_color(22, 78, 59)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.cell(
            0,
            8,
            f"  {latin1_safe(title)}",
            fill=True,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_text_color(20, 25, 30)
        self.ln(3)


def check_hitl_gate(conn: sqlite3.Connection, approved_only: bool) -> list[str]:
    """Return unapproved req_ids; raise SystemExit(1) if gate blocks export."""
    total_drafts = conn.execute("SELECT COUNT(*) AS cnt FROM disclosure_drafts;").fetchone()["cnt"]
    unapproved_rows = conn.execute(
        "SELECT req_id FROM disclosure_drafts WHERE human_approved = 0 ORDER BY req_id;"
    ).fetchall()
    unapproved_ids = [row["req_id"] for row in unapproved_rows]

    if unapproved_ids and not approved_only:
        print(
            "EXPORT BLOCKED (HITL Gate): Unapproved drafts detected (human_approved = 0):",
            file=sys.stderr,
        )
        for req_id in unapproved_ids:
            print(f"  - {req_id}", file=sys.stderr)
        print(
            "Run /approve (or `python src/db.py approve --req-id <ID>`) before exporting, "
            "or pass --approved-only to export only approved drafts.",
            file=sys.stderr,
        )
        sys.exit(1)

    if total_drafts == 0:
        print(
            "EXPORT BLOCKED: No disclosure drafts found in disclosure_drafts. Run /draft first.",
            file=sys.stderr,
        )
        sys.exit(1)

    return unapproved_ids


def fetch_readiness_matrix(conn: sqlite3.Connection) -> list[dict]:
    """Fetch requirement-level readiness, verification, greenwash, and approval summary."""
    rows = conn.execute(
        """
        SELECT
            r.req_id,
            r.framework,
            r.standard,
            r.topic,
            r.is_quantitative,
            r.mandatory,
            MAX(a.readiness_score) AS best_score,
            MIN(CASE WHEN a.numeric_verified = 0 THEN 0
                     WHEN a.numeric_verified = 1 THEN 1
                     ELSE 2 END) AS numeric_state,
            MAX(COALESCE(a.greenwash_flag, 0)) AS greenwash_flag,
            d.human_approved AS draft_approved,
            CASE WHEN d.draft_id IS NOT NULL THEN 1 ELSE 0 END AS has_draft
        FROM esrs_requirements r
        LEFT JOIN assessments a ON a.req_id = r.req_id
        LEFT JOIN disclosure_drafts d ON d.req_id = r.req_id
        GROUP BY r.req_id
        ORDER BY r.req_id ASC;
        """
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_audit_alerts(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Fetch numeric mismatches, greenwashing flags, and low-readiness gaps."""
    numeric_alerts = conn.execute(
        """
        SELECT a.req_id, r.standard, doc.filename, a.page_number,
               a.evidence_quote, a.numeric_discrepancy
        FROM assessments a
        JOIN esrs_requirements r ON r.req_id = a.req_id
        JOIN documents doc ON doc.doc_id = a.doc_id
        WHERE a.numeric_verified = 0
        ORDER BY a.req_id, doc.filename;
        """
    ).fetchall()

    greenwash_alerts = conn.execute(
        """
        SELECT a.req_id, r.standard, doc.filename, a.page_number,
               a.evidence_quote, a.greenwash_reason
        FROM assessments a
        JOIN esrs_requirements r ON r.req_id = a.req_id
        JOIN documents doc ON doc.doc_id = a.doc_id
        WHERE a.greenwash_flag = 1
        ORDER BY a.req_id, doc.filename;
        """
    ).fetchall()

    gap_alerts = conn.execute(
        """
        SELECT a.req_id, r.standard, doc.filename, a.page_number,
               a.readiness_score, a.gap_reason
        FROM assessments a
        JOIN esrs_requirements r ON r.req_id = a.req_id
        JOIN documents doc ON doc.doc_id = a.doc_id
        WHERE a.readiness_score < 3.5
        ORDER BY a.readiness_score ASC, a.req_id;
        """
    ).fetchall()

    return {
        "numeric": [dict(r) for r in numeric_alerts],
        "greenwash": [dict(r) for r in greenwash_alerts],
        "gaps": [dict(r) for r in gap_alerts],
    }


def fetch_approved_disclosures(conn: sqlite3.Connection) -> list[dict]:
    """Fetch all human-approved disclosure drafts."""
    rows = conn.execute(
        """
        SELECT d.req_id, r.framework, r.standard, r.topic,
               d.draft_markdown, d.reviewer_notes, d.updated_at
        FROM disclosure_drafts d
        JOIN esrs_requirements r ON r.req_id = d.req_id
        WHERE d.human_approved = 1
        ORDER BY d.req_id ASC;
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _format_numeric_label(row: dict) -> str:
    if not row["is_quantitative"]:
        return "N/A"
    state = row["numeric_state"]
    if state == 0:
        return "MISMATCH"
    if state == 1:
        return "VERIFIED"
    return "UNVERIFIED"


def _format_approval_label(row: dict) -> str:
    if not row["has_draft"]:
        return "NO DRAFT"
    return "APPROVED" if row["draft_approved"] == 1 else "PENDING"


def render_cover_and_kpis(
    pdf: AssurancePackPDF,
    entity_info: dict[str, str],
    matrix: list[dict],
    alerts: dict[str, list[dict]],
    approved_count: int,
    skipped_unapproved: list[str],
    generated_at: str,
) -> None:
    pdf.add_page()
    pdf.set_fill_color(17, 56, 42)
    pdf.rect(15, 15, 180, 28, style="F")
    pdf.set_xy(20, 19)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "VeriGreen-ops Assurance Pack", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        6,
        "CSRD (Revised ESRS 2026) & Voluntary SME Standard (VS) Readiness Report",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.cell(0, 5, f"Generated: {generated_at}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(15, 47)
    pdf.set_text_color(20, 25, 30)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.multi_cell(
        pdf.epw,
        5,
        latin1_safe(
            f"Entity: {entity_info['entity']}\n"
            f"Reporting Period: {entity_info['fiscal_year']}\n"
            f"Primary Scope: {entity_info['framework']}"
        ),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    if skipped_unapproved:
        pdf.ln(2)
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(255, 244, 229)
        pdf.set_draw_color(217, 119, 6)
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(
            pdf.epw,
            5,
            latin1_safe(
                "PARTIAL EXPORT (--approved-only): Excluded unapproved drafts awaiting /approve: "
                + ", ".join(skipped_unapproved)
            ),
            border=1,
            fill=True,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    scored = [r["best_score"] for r in matrix if r["best_score"] is not None]
    avg_score = f"{sum(scored) / len(scored):.2f}" if scored else "N/A"
    pdf.ln(3)
    pdf.set_fill_color(242, 245, 247)
    pdf.set_draw_color(200, 208, 214)
    pdf.set_font("Helvetica", "B", 9)
    kpi_text = (
        f"Requirements Tracked: {len(matrix)}   |   "
        f"Avg Best Score: {avg_score} / 5.0   |   "
        f"Numeric Mismatches: {len(alerts['numeric'])}   |   "
        f"Greenwash Alerts: {len(alerts['greenwash'])}   |   "
        f"Approved Drafts: {approved_count}"
    )
    pdf.cell(0, 8, kpi_text, border=1, fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def render_readiness_matrix(pdf: AssurancePackPDF, matrix: list[dict]) -> None:
    pdf.section_heading("1. Executive Readiness Matrix")

    col_widths = [24, 20, 56, 18, 22, 20, 20]
    headers = ["Req ID", "Standard", "Topic", "Score", "Numeric", "Greenwash", "Draft"]

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(232, 238, 241)
    pdf.set_draw_color(185, 195, 205)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 7, header, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for idx, row in enumerate(matrix):
        score_str = f"{row['best_score']:.1f}" if row["best_score"] is not None else "N/A"
        numeric_str = _format_numeric_label(row)
        gw_str = "FLAGGED" if row["greenwash_flag"] else "OK"
        draft_str = _format_approval_label(row)
        topic = latin1_safe(row["topic"])
        if len(topic) > 36:
            topic = topic[:33] + "..."

        fill = idx % 2 == 1
        pdf.set_fill_color(249, 251, 252)
        values = [
            latin1_safe(row["req_id"]),
            latin1_safe(row["standard"]),
            topic,
            score_str,
            numeric_str,
            gw_str,
            draft_str,
        ]
        aligns = ["L", "L", "L", "C", "C", "C", "C"]
        for width, val, align in zip(col_widths, values, aligns):
            pdf.cell(width, 6.5, val, border=1, fill=fill, align=align)
        pdf.ln()


def _render_alert_box(pdf: AssurancePackPDF, header: str, body: str, rgb: tuple[int, int, int]) -> None:
    r, g, b = rgb
    pdf.set_x(pdf.l_margin)
    pdf.set_draw_color(r, g, b)
    pdf.set_fill_color(252, 248, 246)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(r, g, b)
    pdf.multi_cell(
        pdf.epw,
        5.5,
        latin1_safe(header),
        border="LTR",
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(30, 35, 40)
    pdf.multi_cell(
        pdf.epw,
        5,
        latin1_safe(body),
        border="LBR",
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2.5)


def render_audit_alerts(pdf: AssurancePackPDF, alerts: dict[str, list[dict]]) -> None:
    pdf.section_heading("2. Numeric & Greenwashing Audit Alerts")

    if not alerts["numeric"] and not alerts["greenwash"] and not alerts["gaps"]:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.multi_cell(
            pdf.epw,
            5.5,
            "No numeric discrepancies, greenwashing flags, or sub-3.5 readiness gaps detected.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        return

    if alerts["numeric"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "2.1 Quantitative Verification Mismatches (numeric_verified = 0)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for item in alerts["numeric"]:
            _render_alert_box(
                pdf,
                f"[NUMERIC MISMATCH] {item['req_id']} ({item['standard']}) -- {item['filename']}, p.{item['page_number']}",
                f"Evidence Quote: \"{item['evidence_quote']}\"\nDiscrepancy: {item['numeric_discrepancy']}",
                (180, 45, 45),
            )

    if alerts["greenwash"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "2.2 EU Green Claims Anti-Greenwashing Flags (greenwash_flag = 1)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for item in alerts["greenwash"]:
            _render_alert_box(
                pdf,
                f"[GREENWASHING RISK] {item['req_id']} ({item['standard']}) -- {item['filename']}, p.{item['page_number']}",
                f"Flagged Claim: \"{item['evidence_quote']}\"\nSubstantiation Failure: {item['greenwash_reason']}",
                (180, 95, 10),
            )

    if alerts["gaps"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "2.3 Readiness Gaps (readiness_score < 3.5)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for item in alerts["gaps"]:
            loc = f"{item['filename']}, p.{item['page_number']}" if item["page_number"] > 0 else f"{item['filename']} (No mention)"
            _render_alert_box(
                pdf,
                f"[READINESS GAP] {item['req_id']} | Score: {item['readiness_score']:.1f}/5.0 | {loc}",
                f"Gap Rationale: {item['gap_reason'] or 'Insufficient evidence for limited-assurance readiness.'}",
                (65, 85, 110),
            )


def _clean_markdown_line(line: str) -> tuple[str, str]:
    """Classify simple Markdown lines into ('heading'|'bullet'|'body', cleaned_text)."""
    stripped = line.strip()
    if stripped.startswith("### "):
        return ("heading", stripped[4:].strip())
    if stripped.startswith("## "):
        return ("heading", stripped[3:].strip())
    if stripped.startswith("# "):
        return ("heading", stripped[2:].strip())
    if stripped.startswith("- ") or stripped.startswith("* "):
        return ("bullet", "* " + stripped[2:].strip().replace("**", ""))
    return ("body", stripped.replace("**", ""))


def render_approved_disclosures(pdf: AssurancePackPDF, disclosures: list[dict]) -> None:
    pdf.section_heading("3. Human-Approved ESRS / VS Disclosures")

    if not disclosures:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.multi_cell(
            pdf.epw,
            5.5,
            "No human-approved disclosure drafts available in this export.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        return

    for item in disclosures:
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(238, 244, 241)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(17, 56, 42)
        pdf.multi_cell(
            pdf.epw,
            6.5,
            latin1_safe(f"{item['req_id']} -- {item['standard']}: {item['topic']}"),
            fill=True,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(80, 90, 100)
        pdf.multi_cell(
            pdf.epw,
            5,
            latin1_safe(
                f"Status: HUMAN APPROVED | Updated: {item['updated_at']} | "
                f"Reviewer Notes: {item['reviewer_notes'] or 'None'}"
            ),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        pdf.set_text_color(20, 25, 30)
        for raw_line in item["draft_markdown"].splitlines():
            if not raw_line.strip():
                pdf.ln(2)
                continue
            kind, cleaned = _clean_markdown_line(raw_line)
            safe_line = latin1_safe(cleaned)
            if kind == "heading":
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.multi_cell(pdf.epw, 5.5, safe_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            elif kind == "bullet":
                pdf.set_x(pdf.l_margin + 4)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(pdf.epw - 4, 5, safe_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(pdf.epw, 5, safe_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(3)
        pdf.set_draw_color(220, 225, 230)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)


def build_assurance_pack(
    db_path: Path = DEFAULT_DB_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    approved_only: bool = False,
) -> Path:
    """Validate HITL approval state and render the A4 PDF Assurance Pack."""
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}. Run `python src/db.py init` first.", file=sys.stderr)
        sys.exit(1)

    with get_connection(db_path) as conn:
        skipped_unapproved = check_hitl_gate(conn, approved_only=approved_only)
        matrix = fetch_readiness_matrix(conn)
        alerts = fetch_audit_alerts(conn)
        disclosures = fetch_approved_disclosures(conn)

    entity_info = load_entity_summary()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pdf = AssurancePackPDF(entity_name=entity_info["entity"], generated_at=generated_at)
    render_cover_and_kpis(
        pdf=pdf,
        entity_info=entity_info,
        matrix=matrix,
        alerts=alerts,
        approved_count=len(disclosures),
        skipped_unapproved=skipped_unapproved if approved_only else [],
        generated_at=generated_at,
    )
    render_readiness_matrix(pdf, matrix)
    render_audit_alerts(pdf, alerts)
    render_approved_disclosures(pdf, disclosures)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"Exported A4 Assurance Pack -> {output_path} ({len(disclosures)} approved disclosures).")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriGreen-ops A4 PDF Assurance Pack Builder")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite DB")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination path for the rendered A4 PDF",
    )
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Allow exporting only human_approved = 1 drafts while excluding pending drafts",
    )
    args = parser.parse_args()
    build_assurance_pack(db_path=args.db, output_path=args.output, approved_only=args.approved_only)


if __name__ == "__main__":
    main()
