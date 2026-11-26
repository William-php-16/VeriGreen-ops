import argparse
import sqlite3
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

try:
    from db import DEFAULT_DB_PATH, get_connection
except ImportError:
    from src.db import DEFAULT_DB_PATH, get_connection


def _open_readonly_fallback(db_path: Path) -> sqlite3.Connection:
    """Open SQLite in read-only URI mode if WAL/write access is unavailable."""
    try:
        return get_connection(db_path)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn


def _score_style(score: float | None) -> tuple[str, str]:
    """Return (formatted_score, rich_style) per rubric thresholds."""
    if score is None:
        return ("N/A", "dim")
    if score < 2.5:
        return (f"{score:.1f}", "bold red")
    if score < 4.0:
        return (f"{score:.1f}", "bold yellow")
    return (f"{score:.1f}", "bold green")


def _fetch_dashboard_data(db_path: Path) -> dict:
    """Query pipeline counts, readiness rows, approval stats, and greenwash flags."""
    conn = _open_readonly_fallback(db_path)
    try:
        counts_row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM documents) AS documents,
                (SELECT COUNT(*) FROM document_pages) AS document_pages,
                (SELECT COUNT(*) FROM esrs_requirements) AS esrs_requirements,
                (SELECT COUNT(*) FROM assessments) AS assessments,
                (SELECT COUNT(*) FROM disclosure_drafts) AS disclosure_drafts,
                (SELECT COUNT(*) FROM disclosure_drafts WHERE human_approved = 1) AS approved_drafts;
            """
        ).fetchone()
        counts = {
            "documents": counts_row["documents"],
            "document_pages": counts_row["document_pages"],
            "esrs_requirements": counts_row["esrs_requirements"],
            "assessments": counts_row["assessments"],
            "disclosure_drafts": counts_row["disclosure_drafts"],
        }
        approved_count = counts_row["approved_drafts"]

        readiness_rows = conn.execute(
            """
            SELECT
                r.req_id,
                r.framework,
                r.standard,
                r.topic,
                r.is_quantitative,
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

        greenwash_rows = conn.execute(
            """
            SELECT
                a.assess_id,
                a.req_id,
                r.standard,
                doc.filename,
                a.page_number,
                a.evidence_quote,
                a.greenwash_reason
            FROM assessments a
            JOIN esrs_requirements r ON r.req_id = a.req_id
            JOIN documents doc ON doc.doc_id = a.doc_id
            WHERE a.greenwash_flag = 1
            ORDER BY a.req_id ASC, doc.filename ASC;
            """
        ).fetchall()
    finally:
        conn.close()

    return {
        "counts": counts,
        "approved_drafts": approved_count,
        "total_drafts": counts["disclosure_drafts"],
        "readiness": [dict(r) for r in readiness_rows],
        "greenwash_alerts": [dict(r) for r in greenwash_rows],
    }


def render_dashboard(db_path: Path = DEFAULT_DB_PATH, console: Console | None = None) -> dict:
    """Render the VeriGreen-ops Rich terminal dashboard and return fetched metrics."""
    out = console or Console()

    if not db_path.exists():
        out.print(
            Panel(
                f"[bold red]Database not found:[/bold red] {db_path}\n"
                "Run [cyan]python src/db.py init[/cyan] to initialize the audit pipeline.",
                title="VeriGreen-ops Readiness Dashboard",
                border_style="red",
            )
        )
        return {"counts": {}, "approved_drafts": 0, "total_drafts": 0, "readiness": [], "greenwash_alerts": []}

    data = _fetch_dashboard_data(db_path)
    counts = data["counts"]

    # 1. Pipeline Counts Summary
    counts_table = Table(title="VeriGreen-ops Audit Pipeline Counts", box=box.ROUNDED, show_header=True)
    counts_table.add_column("Documents", justify="right", style="cyan")
    counts_table.add_column("Pages", justify="right", style="cyan")
    counts_table.add_column("ESRS/VS Requirements", justify="right", style="magenta")
    counts_table.add_column("Assessments", justify="right", style="blue")
    counts_table.add_column("Drafts", justify="right", style="yellow")
    counts_table.add_column("Approved", justify="right", style="green")
    counts_table.add_row(
        str(counts["documents"]),
        str(counts["document_pages"]),
        str(counts["esrs_requirements"]),
        str(counts["assessments"]),
        str(data["total_drafts"]),
        str(data["approved_drafts"]),
    )
    out.print(counts_table)

    # 2. Human-Approval Progress Bar
    total_drafts = data["total_drafts"]
    approved_drafts = data["approved_drafts"]
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=36, complete_style="green", finished_style="bold green"),
        TextColumn("{task.completed}/{task.total} drafts ({task.percentage:>3.0f}%)"),
        console=out,
        transient=False,
    )
    if total_drafts > 0:
        progress.add_task("HITL Approval Gate", total=total_drafts, completed=approved_drafts)
    else:
        progress.add_task("HITL Approval Gate (no drafts yet)", total=1, completed=0)
    out.print(Panel(progress, title="Human-in-the-Loop Sign-Off Progress", border_style="cyan", box=box.ROUNDED))

    # 3. Color-Coded ESRS / VSME Readiness Table
    readiness_table = Table(title="ESRS / VSME Readiness Matrix", box=box.ROUNDED, show_lines=False)
    readiness_table.add_column("Req ID", style="bold", no_wrap=True)
    readiness_table.add_column("Standard", no_wrap=True)
    readiness_table.add_column("Topic", overflow="fold")
    readiness_table.add_column("Score", justify="center", no_wrap=True)
    readiness_table.add_column("Numeric", justify="center", no_wrap=True)
    readiness_table.add_column("Greenwash", justify="center", no_wrap=True)
    readiness_table.add_column("Approval", justify="center", no_wrap=True)

    for row in data["readiness"]:
        score_text, score_style = _score_style(row["best_score"])

        if not row["is_quantitative"]:
            numeric_cell = Text("N/A", style="dim")
        elif row["numeric_state"] == 0:
            numeric_cell = Text("MISMATCH", style="bold red")
        elif row["numeric_state"] == 1:
            numeric_cell = Text("VERIFIED", style="bold green")
        else:
            numeric_cell = Text("UNVERIFIED", style="yellow")

        gw_cell = Text("FLAGGED", style="bold red") if row["greenwash_flag"] else Text("OK", style="green")

        if not row["has_draft"]:
            app_cell = Text("NO DRAFT", style="dim")
        elif row["draft_approved"] == 1:
            app_cell = Text("APPROVED", style="bold green")
        else:
            app_cell = Text("PENDING", style="bold yellow")

        readiness_table.add_row(
            row["req_id"],
            row["standard"],
            row["topic"],
            Text(score_text, style=score_style),
            numeric_cell,
            gw_cell,
            app_cell,
        )

    out.print(readiness_table)

    # 4. Red Warning Panel for greenwash_flag = 1 Entries
    alerts = data["greenwash_alerts"]
    if alerts:
        lines: list[str] = []
        for idx, item in enumerate(alerts, start=1):
            lines.append(
                f"[bold red]{idx}. {item['req_id']} ({item['standard']}) — "
                f"{item['filename']}, p.{item['page_number']}[/bold red]\n"
                f"   [white]Quote:[/white] \"{item['evidence_quote']}\"\n"
                f"   [yellow]Reason:[/yellow] {item['greenwash_reason']}"
            )
        out.print(
            Panel(
                "\n\n".join(lines),
                title=f"[bold red]WARNING: {len(alerts)} EU Green Claims Flag(s) Detected[/bold red]",
                border_style="red",
                box=box.HEAVY,
            )
        )
    else:
        out.print(
            Panel(
                "[green]No active greenwash_flag = 1 entries detected.[/green]",
                title="EU Green Claims Screen",
                border_style="green",
                box=box.ROUNDED,
            )
        )

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriGreen-ops Rich Terminal Readiness Dashboard")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite DB")
    args = parser.parse_args()
    render_dashboard(db_path=args.db)


if __name__ == "__main__":
    main()
