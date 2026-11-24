import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import dashboard  # noqa: E402
import db  # noqa: E402
import ingestor  # noqa: E402
import report_builder  # noqa: E402


def test_sqlite_initialization(tmp_path: Path) -> None:
    db_path = tmp_path / "test_init.db"
    db.init_db(db_path)
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
    expected = {
        "documents",
        "document_pages",
        "esrs_requirements",
        "assessments",
        "disclosure_drafts",
    }
    assert expected.issubset(tables)


def test_yaml_seeding(tmp_path: Path) -> None:
    db_path = tmp_path / "test_seed.db"
    yaml_path = REPO_ROOT / "config" / "esrs_standards.yaml"
    db.init_db(db_path)

    seeded_count = db.seed_yaml(yaml_path=yaml_path, db_path=db_path)
    assert seeded_count >= 9

    # Re-seeding must be idempotent (upsert without duplicates)
    second_count = db.seed_yaml(yaml_path=yaml_path, db_path=db_path)
    assert second_count == seeded_count

    with db.get_connection(db_path) as conn:
        rows = conn.execute("SELECT req_id, framework FROM esrs_requirements;").fetchall()
    req_ids = {r["req_id"] for r in rows}
    assert len(rows) == seeded_count
    assert {"ESRS-E1-1", "ESRS-E1-6", "ESRS-E5-5", "VS-B3-1"}.issubset(req_ids)


def test_sha256_duplicate_skipping_on_sample(tmp_path: Path) -> None:
    sample_dir = REPO_ROOT / "data" / "sample"
    assert (sample_dir / "sample_emissions.csv").exists()
    assert (sample_dir / "sample_sustainability_report.pdf").exists()

    db_path = tmp_path / "test_ingest.db"
    db.init_db(db_path)

    first_run = ingestor.ingest_directory(sample_dir, db_path=db_path)
    assert len(first_run) == 2
    assert all(item["status"] == "ingested" for item in first_run)

    # Re-ingesting identical directory must skip both via SHA-256 hash
    second_run = ingestor.ingest_directory(sample_dir, db_path=db_path)
    assert len(second_run) == 2
    assert all(item["status"] == "skipped_duplicate" for item in second_run)

    # Renamed copy with identical bytes must also be skipped
    renamed_pdf = tmp_path / "renamed_report.pdf"
    shutil.copy2(sample_dir / "sample_sustainability_report.pdf", renamed_pdf)
    renamed_result = ingestor.ingest_file(renamed_pdf, db_path=db_path)
    assert renamed_result["status"] == "skipped_duplicate"

    with db.get_connection(db_path) as conn:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents;").fetchone()[0]
        page_count = conn.execute("SELECT COUNT(*) FROM document_pages;").fetchone()[0]
    assert doc_count == 2
    assert page_count == 4


def test_dashboard_and_hitl_gate(tmp_path: Path) -> None:
    db_path = tmp_path / "test_dash.db"
    pdf_out = tmp_path / "pack.pdf"
    draft_file = tmp_path / "ESRS-E5-5.md"

    db.init_db(db_path)
    db.seed_yaml(REPO_ROOT / "config" / "esrs_standards.yaml", db_path)
    ingestor.ingest_directory(REPO_ROOT / "data" / "sample", db_path=db_path)

    with db.get_connection(db_path) as conn:
        pdf_doc = conn.execute(
            "SELECT doc_id FROM documents WHERE filename = 'sample_sustainability_report.pdf';"
        ).fetchone()
    assert pdf_doc is not None

    db.cmd_save_assessment(
        db_path,
        json.dumps(
            {
                "req_id": "ESRS-E5-5",
                "doc_id": pdf_doc["doc_id"],
                "readiness_score": 2.0,
                "evidence_quote": "Our flagship retail line now features 100% carbon neutral packaging across all Dutch supermarkets",
                "page_number": 1,
                "gap_reason": "Missing packaging weight outflows and LCA boundaries.",
                "greenwash_flag": 1,
                "greenwash_reason": "Unsubstantiated '100% carbon neutral packaging' claim.",
            }
        ),
    )

    draft_file.write_text(
        "The report claims carbon-neutral packaging [Source: sample_sustainability_report.pdf, p.1]. "
        "[DATA GAP: Substantiate or remove claim.]",
        encoding="utf-8",
    )
    db.cmd_save_draft(db_path, "ESRS-E5-5", draft_file)

    console = Console(record=True, width=120)
    data = dashboard.render_dashboard(db_path=db_path, console=console)
    output = console.export_text()
    assert data["counts"]["documents"] == 2
    assert len(data["greenwash_alerts"]) == 1
    assert "EU Green Claims Flag" in output
    assert "ESRS-E5-5" in output

    # HITL gate blocks export while human_approved = 0
    with pytest.raises(SystemExit) as exc:
        report_builder.build_assurance_pack(db_path=db_path, output_path=pdf_out)
    assert exc.value.code == 1
    assert not pdf_out.exists()


def test_all_yaml_rulebooks_unique_and_seedable(tmp_path: Path) -> None:
    yaml_files = sorted((REPO_ROOT / "config").glob("*.yaml")) + sorted(
        (REPO_ROOT / "config" / "examples").glob("*.yaml")
    )
    assert len(yaml_files) >= 6

    rulebook_files: list[Path] = []
    seen_req_ids: dict[str, Path] = {}
    total_reqs = 0

    for path in yaml_files:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), f"Invalid YAML mapping in {path}"
        if "requirements" not in payload:
            # Non-rulebook config (e.g. config/portals.yaml) must still parse cleanly
            assert path.name == "portals.yaml", f"Unexpected non-rulebook YAML: {path}"
            continue

        rulebook_files.append(path)
        assert "version" in payload and "active_frameworks" in payload
        reqs = payload["requirements"]
        assert isinstance(reqs, list) and len(reqs) > 0

        for req in reqs:
            for field in (
                "req_id",
                "framework",
                "standard",
                "topic",
                "requirement_text",
                "is_quantitative",
                "mandatory",
            ):
                assert field in req, f"Missing {field} in {path}: {req}"
            req_id = req["req_id"]
            assert req_id not in seen_req_ids, (
                f"Duplicate req_id '{req_id}' in {path} and {seen_req_ids[req_id]}"
            )
            seen_req_ids[req_id] = path
            total_reqs += 1

    assert len(rulebook_files) == 5

    # Seed base rulebook, ingest sample doc, save an assessment, then seed all examples
    db_path = tmp_path / "test_multi_fw.db"
    db.init_db(db_path)
    base_yaml = REPO_ROOT / "config" / "esrs_standards.yaml"
    db.seed_yaml(base_yaml, db_path)
    ingestor.ingest_directory(REPO_ROOT / "data" / "sample", db_path=db_path)

    with db.get_connection(db_path) as conn:
        doc_row = conn.execute("SELECT doc_id FROM documents LIMIT 1;").fetchone()
    assert doc_row is not None
    db.cmd_save_assessment(
        db_path,
        json.dumps(
            {
                "req_id": "ESRS-E1-1",
                "doc_id": doc_row["doc_id"],
                "readiness_score": 1.0,
                "evidence_quote": "",
                "page_number": 0,
                "gap_reason": "Synthetic baseline check.",
            }
        ),
    )

    for example_yaml in sorted((REPO_ROOT / "config" / "examples").glob("*.yaml")):
        proc = subprocess.run(
            [sys.executable, str(SRC_DIR / "db.py"), "--db", str(db_path), "seed", "--yaml", str(example_yaml)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Seeded" in proc.stdout

    with db.get_connection(db_path) as conn:
        req_count = conn.execute("SELECT COUNT(*) FROM esrs_requirements;").fetchone()[0]
        assess_count = conn.execute("SELECT COUNT(*) FROM assessments;").fetchone()[0]
    assert req_count == total_reqs
    assert assess_count == 1  # Existing assessments preserved across `seed` calls

    # Verify --framework filter on list-unassessed (SFDR has 11 PAI indicators * 2 sample docs = 22)
    filtered_proc = subprocess.run(
        [
            sys.executable,
            str(SRC_DIR / "db.py"),
            "--db",
            str(db_path),
            "list-unassessed",
            "--framework",
            "EU_SFDR_PAI",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    filtered_rows = json.loads(filtered_proc.stdout)
    assert len(filtered_rows) == 22
    assert all(r["framework"] == "EU_SFDR_PAI" for r in filtered_rows)
