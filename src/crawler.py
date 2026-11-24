import argparse
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx
import yaml
from bs4 import BeautifulSoup

try:
    from db import DEFAULT_DB_PATH, init_db
    from ingestor import ingest_file
except ImportError:
    from src.db import DEFAULT_DB_PATH, init_db
    from src.ingestor import ingest_file

DEFAULT_RAW_DIR = Path("data/raw_docs")
DEFAULT_PORTALS_PATH = Path("config/portals.yaml")
SUPPORTED_EXTENSIONS = (".pdf", ".csv")
DEFAULT_KEYWORDS = (
    "esg",
    "csrd",
    "esrs",
    "vsme",
    "sustainab",
    "climate",
    "carbon",
    "emission",
    "ghg",
    "environment",
    "impact",
    "gri",
    "tcfd",
    "scope",
    "net-zero",
    "netzero",
    "biodiversity",
    "annual-report",
    "non-financial",
    "green",
)


def is_esg_relevant(
    url: str,
    anchor_text: str = "",
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
) -> bool:
    """Return True if URL or anchor text matches any ESG/sustainability keyword."""
    haystack = f"{url} {anchor_text}".lower()
    return any(kw in haystack for kw in keywords)


def discover_links(
    html: str,
    base_url: str,
    all_files: bool = False,
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
) -> list[str]:
    """Extract deduplicated absolute .pdf and .csv links from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    discovered: list[str] = []
    seen: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = str(tag["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue

        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in {"http", "https"}:
            continue

        clean_url = parsed._replace(fragment="").geturl()
        if not parsed.path.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        anchor_text = tag.get_text(" ", strip=True)
        if not all_files and not is_esg_relevant(clean_url, anchor_text, keywords):
            continue

        if clean_url not in seen:
            seen.add(clean_url)
            discovered.append(clean_url)

    return discovered


def safe_filename_from_url(file_url: str, fallback_stem: str = "report") -> str:
    """Derive a filesystem-safe .pdf or .csv filename from a URL."""
    parsed = urlparse(file_url)
    raw_name = unquote(Path(parsed.path).name)
    suffix = Path(raw_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = ".pdf"
    stem = Path(raw_name).stem or fallback_stem
    safe_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem).strip(" ._") or fallback_stem
    return f"{safe_stem[:120]}{suffix}"


def _resolve_target_path(dest_dir: Path, filename: str, content: bytes) -> Path:
    """Avoid clobbering an existing file with different content while preserving identical ones."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    existing_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
    incoming_hash = hashlib.sha256(content).hexdigest()
    if existing_hash == incoming_hash:
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    return dest_dir / f"{stem}_{incoming_hash[:8]}{suffix}"


def download_file(client: httpx.Client, file_url: str, dest_dir: Path) -> Path:
    """Download a .pdf or .csv file into dest_dir and return its local Path."""
    response = client.get(file_url)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        raise ValueError(f"Expected PDF/CSV bytes but received HTML ({content_type})")
    if not response.content:
        raise ValueError("Downloaded empty response body")

    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename_from_url(file_url)
    dest_path = _resolve_target_path(dest_dir, filename, response.content)
    if not dest_path.exists():
        dest_path.write_bytes(response.content)
    return dest_path


def load_portals_yaml(portals_path: Path = DEFAULT_PORTALS_PATH) -> list[dict]:
    """Load enabled target portal entries from config/portals.yaml."""
    if not portals_path.exists():
        raise FileNotFoundError(f"Portal config not found: {portals_path}")

    with open(portals_path, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    portals = payload.get("portals", [])
    return [p for p in portals if p.get("enabled", True) and p.get("url")]


def crawl_url(
    target_url: str,
    dest_dir: Path = DEFAULT_RAW_DIR,
    db_path: Path = DEFAULT_DB_PATH,
    all_files: bool = False,
    timeout: float = 30.0,
    max_files: int = 25,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Crawl a webpage (or direct PDF/CSV URL), download files, and ingest via ingest_file()."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    init_db(db_path)

    owns_client = client is None
    if client is None:
        client = httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "VeriGreen-ops/1.0 (Local CSRD Readiness Crawler)"},
        )

    results: list[dict] = []
    try:
        parsed_target = urlparse(target_url)
        if parsed_target.path.lower().endswith(SUPPORTED_EXTENSIONS):
            file_urls = [target_url]
        else:
            resp = client.get(target_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()
            if "application/pdf" in content_type or "text/csv" in content_type:
                file_urls = [str(resp.url)]
            else:
                file_urls = discover_links(
                    resp.text,
                    base_url=str(resp.url),
                    all_files=all_files,
                )

        if not file_urls:
            print(f"[INFO]     No matching .pdf or .csv links found at {target_url}")
            return results

        for file_url in file_urls[:max_files]:
            try:
                local_path = download_file(client, file_url, dest_dir)
                ingest_res = ingest_file(local_path, db_path=db_path)
                ingest_res["source_url"] = file_url
                results.append(ingest_res)
            except (httpx.HTTPError, ValueError, OSError) as exc:
                results.append(
                    {
                        "file": safe_filename_from_url(file_url),
                        "source_url": file_url,
                        "status": "download_error",
                        "reason": str(exc),
                    }
                )
    finally:
        if owns_client:
            client.close()

    return results


def crawl_batch(
    portals_path: Path = DEFAULT_PORTALS_PATH,
    dest_dir: Path = DEFAULT_RAW_DIR,
    db_path: Path = DEFAULT_DB_PATH,
    all_files: bool = False,
    timeout: float = 30.0,
    max_files: int = 25,
) -> list[dict]:
    """Crawl all enabled portals defined in config/portals.yaml."""
    portals = load_portals_yaml(portals_path)
    if not portals:
        print(f"[INFO]     No enabled portals found in {portals_path}")
        return []

    all_results: list[dict] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": "VeriGreen-ops/1.0 (Local CSRD Readiness Crawler)"},
    ) as client:
        for portal in portals:
            name = portal.get("name", portal["url"])
            url = portal["url"]
            print(f"==> Crawling portal: {name} ({url})")
            try:
                portal_results = crawl_url(
                    target_url=url,
                    dest_dir=dest_dir,
                    db_path=db_path,
                    all_files=all_files,
                    timeout=timeout,
                    max_files=max_files,
                    client=client,
                )
                all_results.extend(portal_results)
            except httpx.HTTPError as exc:
                print(f"[WARNING]  Portal failed ({url}): {exc}")
                all_results.append(
                    {
                        "file": name,
                        "source_url": url,
                        "status": "portal_error",
                        "reason": str(exc),
                    }
                )
    return all_results


def print_summary(results: list[dict]) -> None:
    """Print deterministic ingestion and SHA-256 deduplication summary."""
    ingested = 0
    skipped = 0
    warnings = 0

    for item in results:
        status = item.get("status")
        if status == "ingested":
            ingested += 1
            print(f"[INGESTED] {item['file']} -> doc_id={item['doc_id']} ({item['pages']} pages)")
        elif status == "skipped_duplicate":
            skipped += 1
            print(f"[SKIPPED]  {item['file']} (already ingested as {item['doc_id']})")
        else:
            warnings += 1
            print(f"[WARNING]  {item.get('file')}: {item.get('reason', status)}")

    print(
        f"Crawl summary: {ingested} newly ingested, "
        f"{skipped} skipped (SHA-256 duplicate), {warnings} warnings/errors."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VeriGreen-ops Deterministic Sustainability Report Crawler"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--url", help="Single corporate sustainability webpage or direct PDF/CSV URL")
    mode.add_argument(
        "--batch",
        action="store_true",
        help="Crawl all enabled corporate portals from config/portals.yaml",
    )
    parser.add_argument(
        "--portals",
        type=Path,
        default=DEFAULT_PORTALS_PATH,
        help="Path to portals YAML config for --batch mode",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directory to store downloaded PDF/CSV files (default: data/raw_docs)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database (default: data/audit_pipeline.db)",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Download all discovered .pdf and .csv links without ESG keyword filtering",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=25,
        help="Maximum number of files to download per portal URL (default: 25)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.url:
        try:
            results = crawl_url(
                target_url=args.url,
                dest_dir=args.dir,
                db_path=args.db,
                all_files=args.all_files,
                timeout=args.timeout,
                max_files=args.max_files,
            )
        except httpx.HTTPError as exc:
            print(f"ERROR: Failed to fetch {args.url}: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        results = crawl_batch(
            portals_path=args.portals,
            dest_dir=args.dir,
            db_path=args.db,
            all_files=args.all_files,
            timeout=args.timeout,
            max_files=args.max_files,
        )

    print_summary(results)


if __name__ == "__main__":
    main()
