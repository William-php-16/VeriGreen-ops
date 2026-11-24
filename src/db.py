import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
import yaml

DEFAULT_DB_PATH = Path("data/audit_pipeline.db")
DEFAULT_YAML_PATH = Path("config/esrs_standards.yaml")


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH, reset: bool = False) -> None:
    if reset and db_path.exists():
        db_path.unlink()

    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                file_hash TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL CHECK(doc_type IN ('pdf', 'csv')),
                page_count INTEGER NOT NULL DEFAULT 1,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS document_pages (
                page_id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                content_text TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                UNIQUE(doc_id, page_number)
            );

            CREATE TABLE IF NOT EXISTS esrs_requirements (
                req_id TEXT PRIMARY KEY,
                framework TEXT NOT NULL,
                standard TEXT NOT NULL,
                topic TEXT NOT NULL,
                requirement_text TEXT NOT NULL,
                is_quantitative INTEGER NOT NULL DEFAULT 0,
                mandatory INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS assessments (
                assess_id INTEGER PRIMARY KEY AUTOINCREMENT,
                req_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                readiness_score REAL NOT NULL CHECK(readiness_score >= 1.0 AND readiness_score <= 5.0),
                evidence_quote TEXT NOT NULL DEFAULT '',
                page_number INTEGER NOT NULL DEFAULT 0,
                gap_reason TEXT NOT NULL DEFAULT '',
                numeric_verified INTEGER,
                numeric_discrepancy TEXT NOT NULL DEFAULT '',
                greenwash_flag INTEGER NOT NULL DEFAULT 0,
                greenwash_reason TEXT NOT NULL DEFAULT '',
                assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (req_id) REFERENCES esrs_requirements(req_id) ON DELETE CASCADE,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                UNIQUE(req_id, doc_id)
            );

            CREATE TABLE IF NOT EXISTS disclosure_drafts (
                draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
                req_id TEXT UNIQUE NOT NULL,
                draft_markdown TEXT NOT NULL,
                human_approved INTEGER NOT NULL DEFAULT 0,
                reviewer_notes TEXT NOT NULL DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (req_id) REFERENCES esrs_requirements(req_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_pages_doc ON document_pages(doc_id);
            CREATE INDEX IF NOT EXISTS idx_assess_req ON assessments(req_id);
            CREATE INDEX IF NOT EXISTS idx_assess_doc ON assessments(doc_id);
            """
        )


def seed_yaml(yaml_path: Path = DEFAULT_YAML_PATH, db_path: Path = DEFAULT_DB_PATH) -> int:
    if not yaml_path.exists():
        raise FileNotFoundError(f"Rulebook not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)

    default_fw = payload.get("framework", "ESRS_2026")
    reqs = payload.get("requirements", [])
    count = 0

    with get_connection(db_path) as conn:
        for r in reqs:
            conn.execute(
                """
                INSERT INTO esrs_requirements (
                    req_id, framework, standard, topic, requirement_text, is_quantitative, mandatory
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(req_id) DO UPDATE SET
                    framework = excluded.framework,
                    standard = excluded.standard,
                    topic = excluded.topic,
                    requirement_text = excluded.requirement_text,
                    is_quantitative = excluded.is_quantitative,
                    mandatory = excluded.mandatory;
                """,
                (
                    r["req_id"],
                    r.get("framework", default_fw),
                    r["standard"],
                    r["topic"],
                    r["requirement_text"].strip(),
                    int(bool(r.get("is_quantitative", False))),
                    int(bool(r.get("mandatory", True))),
                ),
            )
            count += 1
    return count


def compute_file_hash(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def cmd_status(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        tables = [
            "documents",
            "document_pages",
            "esrs_requirements",
            "assessments",
            "disclosure_drafts",
        ]
        summary = {}
        for t in tables:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {t}").fetchone()
            summary[t] = row["cnt"]
    print(json.dumps({"db_path": str(db_path), "counts": summary}, indent=2))


def cmd_list_unassessed(db_path: Path, framework: str | None = None) -> None:
    query = """
        SELECT r.req_id, r.framework, r.standard, r.topic, r.requirement_text, r.is_quantitative,
               d.doc_id, d.filename, d.doc_type
        FROM esrs_requirements r
        CROSS JOIN documents d
        LEFT JOIN assessments a ON a.req_id = r.req_id AND a.doc_id = d.doc_id
        WHERE a.assess_id IS NULL
    """
    params: list[str] = []
    if framework:
        query += " AND r.framework = ?"
        params.append(framework)
    query += " ORDER BY d.doc_id, r.req_id;"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_get_pages(db_path: Path, doc_id: str) -> None:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT page_number, content_text
            FROM document_pages
            WHERE doc_id = ?
            ORDER BY page_number ASC;
            """,
            (doc_id,),
        ).fetchall()
    print(json.dumps([dict(r) for r in rows], indent=2))


def cmd_save_assessment(db_path: Path, raw_json: str) -> None:
    data = json.loads(raw_json)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO assessments (
                req_id, doc_id, readiness_score, evidence_quote, page_number,
                gap_reason, numeric_verified, numeric_discrepancy,
                greenwash_flag, greenwash_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(req_id, doc_id) DO UPDATE SET
                readiness_score = excluded.readiness_score,
                evidence_quote = excluded.evidence_quote,
                page_number = excluded.page_number,
                gap_reason = excluded.gap_reason,
                numeric_verified = COALESCE(excluded.numeric_verified, assessments.numeric_verified),
                numeric_discrepancy = CASE
                    WHEN excluded.numeric_discrepancy != '' THEN excluded.numeric_discrepancy
                    ELSE assessments.numeric_discrepancy
                END,
                greenwash_flag = excluded.greenwash_flag,
                greenwash_reason = excluded.greenwash_reason,
                assessed_at = CURRENT_TIMESTAMP;
            """,
            (
                data["req_id"],
                data["doc_id"],
                float(data["readiness_score"]),
                data.get("evidence_quote", ""),
                int(data.get("page_number", 0)),
                data.get("gap_reason", ""),
                data.get("numeric_verified"),
                data.get("numeric_discrepancy", ""),
                int(bool(data.get("greenwash_flag", False))),
                data.get("greenwash_reason", ""),
            ),
        )
    print(f"Saved assessment for {data['req_id']} on {data['doc_id']}.")


def cmd_save_draft(db_path: Path, req_id: str, file_path: Path) -> None:
    markdown_text = file_path.read_text(encoding="utf-8")
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO disclosure_drafts (req_id, draft_markdown, human_approved)
            VALUES (?, ?, 0)
            ON CONFLICT(req_id) DO UPDATE SET
                draft_markdown = excluded.draft_markdown,
                human_approved = 0,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (req_id, markdown_text),
        )
    print(f"Saved unapproved draft for {req_id} (human_approved=0).")


def cmd_approve(db_path: Path, req_id: str, notes: str) -> None:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE disclosure_drafts
            SET human_approved = 1, reviewer_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE req_id = ?;
            """,
            (notes, req_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"No draft found for req_id={req_id}")
    print(f"Approved disclosure draft for {req_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriGreen-ops SQLite Audit State Manager")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite DB")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize DB schema and seed YAML rulebook")
    p_init.add_argument("--reset", action="store_true", help="Drop existing DB first")
    p_init.add_argument("--yaml", type=Path, default=DEFAULT_YAML_PATH)

    p_seed = sub.add_parser("seed", help="Upsert an additional YAML rulebook without wiping existing assessments")
    p_seed.add_argument("--yaml", type=Path, required=True, help="Path to YAML rulebook file")

    sub.add_parser("status", help="Show table row counts")
    p_unassessed = sub.add_parser("list-unassessed", help="List unassessed (req_id, doc_id) pairs")
    p_unassessed.add_argument("--framework", default=None, help="Optional framework filter (e.g. ESRS_2026, VS, EU_SFDR_PAI)")

    p_pages = sub.add_parser("get-pages", help="Get extracted pages for a document")
    p_pages.add_argument("--doc-id", required=True)

    p_save = sub.add_parser("save-assessment", help="Upsert an assessment JSON record")
    p_save.add_argument("--json", required=True)

    p_draft = sub.add_parser("save-draft", help="Save a Markdown draft from file")
    p_draft.add_argument("--req-id", required=True)
    p_draft.add_argument("--file", type=Path, required=True)

    p_app = sub.add_parser("approve", help="Mark a disclosure draft as human-approved")
    p_app.add_argument("--req-id", required=True)
    p_app.add_argument("--notes", default="Verified against source evidence")

    args = parser.parse_args()

    if args.command == "init":
        init_db(args.db, reset=args.reset)
        count = seed_yaml(args.yaml, args.db)
        print(f"Initialized {args.db} and seeded {count} requirements.")
    elif args.command == "seed":
        init_db(args.db, reset=False)
        count = seed_yaml(args.yaml, args.db)
        print(f"Seeded {count} requirements from {args.yaml} into {args.db}.")
    elif args.command == "status":
        cmd_status(args.db)
    elif args.command == "list-unassessed":
        cmd_list_unassessed(args.db, framework=args.framework)
    elif args.command == "get-pages":
        cmd_get_pages(args.db, args.doc_id)
    elif args.command == "save-assessment":
        cmd_save_assessment(args.db, args.json)
    elif args.command == "save-draft":
        cmd_save_draft(args.db, args.req_id, args.file)
    elif args.command == "approve":
        cmd_approve(args.db, args.req_id, args.notes)


if __name__ == "__main__":
    main()