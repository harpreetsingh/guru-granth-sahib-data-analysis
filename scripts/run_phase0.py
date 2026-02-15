"""Run the full Phase 0 pipeline: scrape -> parse -> normalize -> tokenize -> validate.

Usage:
    uv run python scripts/run_phase0.py
    uv run python scripts/run_phase0.py --skip-scrape   # if HTML already downloaded
    uv run python scripts/run_phase0.py --ang-start 1 --ang-end 10  # subset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console

from ggs.corpus.pipeline import run_phase0
from ggs.corpus.scrape import ScrapeConfig, scrape_corpus
from ggs.pipeline.errors import ErrorConfig

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
CORPUS_DIR = DATA_DIR / "corpus"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run GGS Phase 0 pipeline",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraping (use existing HTML files)",
    )
    parser.add_argument(
        "--ang-start",
        type=int,
        default=1,
        help="First ang to process (default: 1)",
    )
    parser.add_argument(
        "--ang-end",
        type=int,
        default=1430,
        help="Last ang to process (default: 1430)",
    )
    args = parser.parse_args()

    # Step 1: Scrape
    if not args.skip_scrape:
        console.print(
            "\n[bold cyan]═══ Step 1: Scraping SriGranth.org "
            f"(angs {args.ang_start}-{args.ang_end}) ═══[/bold cyan]\n"
        )
        scrape_config = ScrapeConfig(
            ang_start=args.ang_start,
            ang_end=args.ang_end,
        )
        state = scrape_corpus(RAW_HTML_DIR, config=scrape_config)

        if len(state.completed_angs) == 0:
            console.print("[red]No angs scraped. Aborting.[/red]")
            sys.exit(1)

        console.print(
            f"\n[green]Scrape complete: "
            f"{len(state.completed_angs)} angs downloaded[/green]\n"
        )
    else:
        console.print(
            "\n[yellow]Skipping scrape (--skip-scrape)[/yellow]\n"
        )

    # Step 2: Run Phase 0 pipeline
    console.print(
        "\n[bold cyan]═══ Step 2: Phase 0 Pipeline "
        "(parse → normalize → tokenize → validate) ═══[/bold cyan]\n"
    )

    error_config = ErrorConfig(max_record_errors=100)
    result = run_phase0(
        input_dir=RAW_HTML_DIR,
        output_dir=CORPUS_DIR,
        config_path=CONFIG_PATH,
        error_config=error_config,
        ang_range=(args.ang_start, args.ang_end),
    )

    # Summary
    console.print("\n[bold cyan]═══ Phase 0 Summary ═══[/bold cyan]")
    console.print(f"  Total angs:  {result['total_angs']}")
    console.print(f"  Total lines: {result['total_lines']}")
    console.print(f"  Validation:  {result['validation_verdict']}")
    console.print("  Output files:")
    for f in result.get("output_files", []):
        console.print(f"    {f}")
    console.print()

    if result["validation_verdict"] != "PASS":
        console.print(
            "[yellow]Validation did not PASS. "
            "Check validation_report.json for details.[/yellow]"
        )
        sys.exit(1)

    console.print("[bold green]Phase 0 complete.[/bold green]\n")


if __name__ == "__main__":
    main()
