"""Download all 1430 angs from srigurugranth.com and build ggs_lines.jsonl.

srigurugranth.com serves static HTML files with a clean structure:
  - Gurmukhi: <P class=Gurb><SPAN lang=PA>...</SPAN></p>
  - Roman:    <P class=Roman><SPAN lang=EN>...</SPAN></p>
  - English:  <P class=Trans><SPAN lang=EN>...</SPAN></p>

URL pattern: https://srigurugranth.com/{NNNN}.html (zero-padded to 4 digits)

Usage:
    uv run python scripts/download_srigurugranth.py
    uv run python scripts/download_srigurugranth.py --skip-download  # parse only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ggs.corpus.normalize import NormalizationConfig, normalize
from ggs.corpus.tokenize import tokenize

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw_html_srigurugranth"
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
BASE_URL = "https://srigurugranth.com/{ang:04d}.html"
TOTAL_ANGS = 1430


def _ang_path(ang: int) -> Path:
    return RAW_DIR / f"ang_{ang:04d}.html"


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download_all(*, delay_ms: int = 200) -> int:
    """Download all 1430 ang HTML files.

    Returns count of newly downloaded files.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    with (
        httpx.Client(
            headers={"User-Agent": "ggs-text-analysis/0.1.0"},
            follow_redirects=True,
        ) as client,
        Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress,
    ):
        task = progress.add_task("Downloading", total=TOTAL_ANGS)

        for ang in range(1, TOTAL_ANGS + 1):
            path = _ang_path(ang)
            if path.exists() and path.stat().st_size > 100:
                progress.advance(task)
                continue

            url = BASE_URL.format(ang=ang)
            try:
                resp = client.get(url, timeout=30.0)
                if resp.status_code == 200:
                    path.write_text(resp.text, encoding="utf-8")
                    downloaded += 1
                else:
                    console.print(
                        f"  [yellow]Ang {ang}: HTTP {resp.status_code}[/yellow]"
                    )
            except httpx.HTTPError as exc:
                console.print(f"  [red]Ang {ang}: {exc}[/red]")

            # Be polite — small delay for static files
            time.sleep(delay_ms / 1000.0)
            progress.advance(task)

    return downloaded


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _compute_line_uid(ang: int, line_id: str, gurmukhi: str) -> str:
    content = f"{ang}:{line_id}:{gurmukhi}"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    return f"ang{ang}:sha256:{digest}"


def parse_ang(ang: int) -> list[dict]:
    """Parse a single ang HTML into canonical records."""
    path = _ang_path(ang)
    if not path.exists():
        return []

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # Extract Gurmukhi lines: <P class=Gurb> or case variants
    # BeautifulSoup may lowercase; try multiple approaches
    gurb_lines: list[str] = []

    # Approach 1: regex on raw HTML (most reliable for unquoted attrs)
    pattern = re.compile(
        r'<[Pp]\s+class\s*=\s*["\']?Gurb["\']?\s*>'
        r'<[Ss][Pp][Aa][Nn][^>]*>(.*?)</[Ss][Pp][Aa][Nn]>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        text = m.group(1).strip()
        # Strip any remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            gurb_lines.append(text)

    if not gurb_lines:
        # Approach 2: BeautifulSoup with case-insensitive search
        for p in soup.find_all("p"):
            cls = p.get("class", [])
            if isinstance(cls, list):
                cls_str = " ".join(cls)
            else:
                cls_str = str(cls)
            if "gurb" in cls_str.lower():
                span = p.find("span")
                if span:
                    text = span.get_text(strip=True)
                else:
                    text = p.get_text(strip=True)
                if text:
                    gurb_lines.append(text)

    # Build canonical records
    norm_config = NormalizationConfig()
    records = []

    for idx, raw_text in enumerate(gurb_lines, start=1):
        line_id = f"{ang}:{idx:02d}"
        gurmukhi = normalize(raw_text, norm_config)

        tok_result = tokenize(gurmukhi)
        line_uid = _compute_line_uid(ang, line_id, gurmukhi)

        records.append({
            "schema_version": "1.0.0",
            "ang": ang,
            "line_id": line_id,
            "line_uid": line_uid,
            "gurmukhi_raw": raw_text,
            "gurmukhi": gurmukhi,
            "tokens": tok_result.tokens,
            "token_spans": tok_result.token_spans,
            "meta": {
                "structural_markers": tok_result.structural_markers,
            },
            "source_url": BASE_URL.format(ang=ang),
        })

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download GGS from srigurugranth.com and build corpus",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download, parse existing HTML only",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=200,
        help="Delay between requests in ms (default: 200)",
    )
    args = parser.parse_args()

    # Step 1: Download
    if not args.skip_download:
        console.print(
            "\n[bold cyan]Step 1: Downloading 1430 angs "
            "from srigurugranth.com[/bold cyan]\n"
        )
        count = download_all(delay_ms=args.delay_ms)
        console.print(f"\n[green]Downloaded {count} new files[/green]\n")
    else:
        console.print("[yellow]Skipping download[/yellow]\n")

    # Step 2: Parse all angs
    console.print(
        "[bold cyan]Step 2: Parsing and building "
        "ggs_lines.jsonl[/bold cyan]\n"
    )

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = CORPUS_DIR / "ggs_lines.jsonl"

    all_records = []
    empty_angs = []

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing", total=TOTAL_ANGS)

        for ang in range(1, TOTAL_ANGS + 1):
            records = parse_ang(ang)
            if not records:
                empty_angs.append(ang)
            all_records.extend(records)
            progress.advance(task)

    # Write JSONL
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    console.print(f"\n[bold cyan]Results[/bold cyan]")
    console.print(f"  Total lines:  {len(all_records)}")
    console.print(f"  Total angs:   {TOTAL_ANGS - len(empty_angs)}")
    console.print(f"  Empty angs:   {len(empty_angs)}")
    console.print(f"  Output:       {jsonl_path}")

    if empty_angs:
        console.print(
            f"  [yellow]Empty angs: {empty_angs[:10]}"
            f"{'...' if len(empty_angs) > 10 else ''}[/yellow]"
        )

    console.print(f"\n[bold green]Done.[/bold green]\n")


if __name__ == "__main__":
    main()
