import argparse
import sqlite3
from pathlib import Path
import fitz  # PyMuPDF
import pandas as pd

from db import DEFAULT_DB_PATH, compute_file_hash, get_connection, init_db


def extract_pdf_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract 1-indexed (page_number, cleaned_text) tuples from a PDF."""
    pages: list[tuple[int, str]] = []
    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((idx, text))
    return pages


def extract_csv_as_markdown(csv_path: Path) -> str:
    """Parse CSV into a deterministic Markdown table plus summary aggregates."""
    df = pd.read_csv(csv_path)
    sections = [f"### Raw Tabular Data: {csv_path.name}\n", df.to_markdown(index=False)]

    # Automatically compute Scope/Year summary if standard emissions columns exist
    cols = {c.lower(): c for c in df.columns}
    if "reporting_year" in cols and "scope" in cols and "emissions_tco2e" in cols:
        yr_col = cols["reporting_year"]
        sc_col = cols["scope"]
        em_col = cols["emissions_tco2e"]
        summary = (
            df.groupby([yr_col, sc_col], as_index=False)[em_col]
            .sum()
            .sort_values([sc_col, yr_col])
        )
        sections.append("\n\n### Deterministic Emissions Summary (Grouped by Year & Scope)\n")
        sections.append(summary.to_markdown(index=False))

    return "\n".join(sections)


def ingest_file(file_path: Path, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Ingest a single PDF or CSV into SQLite with SHA-256 deduplication."""
    suffix = file_path.suffix.lower()
    if suffix not in {".pdf", ".csv"}:
        return {"file": file_path.name, "status": "ignored", "reason": "Unsupported file type"}

    file_hash = compute_file_hash(file_path)
    doc_id = f"{file_path.stem}_{file_hash[:8]}"
    doc_type = suffix.lstrip(".")

    with get_connection(db_path) as conn:
        existing = conn.execute(
            "SELECT doc_id, filename FROM documents WHERE file_hash = ?",
            (file_hash,),
        ).fetchone()

        if existing:
            return {
                "file": file_path.name,
                "status": "skipped_duplicate",
                "doc_id": existing["doc_id"],
            }

        if doc_type == "pdf":
            pages = extract_pdf_pages(file_path)
            if not pages:
                return {
                    "file": file_path.name,
                    "status": "failed",
                    "reason": "No extractable text layer found (scanned PDF)",
                }
        else:
            md_table = extract_csv_as_markdown(file_path)
            pages = [(1, md_table)]

        try:
            conn.execute(
                """
                INSERT INTO documents (doc_id, file_hash, filename, doc_type, page_count)
                VALUES (?, ?, ?, ?, ?);
                """,
                (doc_id, file_hash, file_path.name, doc_type, len(pages)),
            )
            conn.executemany(
                """
                INSERT INTO document_pages (doc_id, page_number, content_text)
                VALUES (?, ?, ?);
                """,
                [(doc_id, page_num, content) for page_num, content in pages],
            )
        except sqlite3.Error as exc:
            return {"file": file_path.name, "status": "error", "reason": str(exc)}

    return {
        "file": file_path.name,
        "status": "ingested",
        "doc_id": doc_id,
        "doc_type": doc_type,
        "pages": len(pages),
    }


def ingest_directory(target_dir: Path, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Recursively ingest all PDF and CSV files in a directory."""
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory not found: {target_dir}")

    init_db(db_path)
    results = []
    for path in sorted(target_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".pdf", ".csv"}:
            results.append(ingest_file(path, db_path))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriGreen-ops Deterministic Document Ingestor")
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path("data/raw_docs"),
        help="Directory containing PDF/CSV files to ingest",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite DB")
    args = parser.parse_args()

    results = ingest_directory(args.dir, args.db)
    if not results:
        print(f"No .pdf or .csv files found in {args.dir}")
        return

    for item in results:
        status = item["status"]
        if status == "ingested":
            print(f"[INGESTED] {item['file']} -> doc_id={item['doc_id']} ({item['pages']} pages)")
        elif status == "skipped_duplicate":
            print(f"[SKIPPED]  {item['file']} (already ingested as {item['doc_id']})")
        else:
            print(f"[WARNING]  {item['file']}: {item.get('reason', status)}")


if __name__ == "__main__":
    main()