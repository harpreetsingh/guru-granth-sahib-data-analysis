"""Phase 0 end-to-end pipeline: parse -> normalize -> tokenize -> validate (bd-15c.8).

Wires all Phase 0 components into a single pipeline that:
  1. Reads HTML files (scraped or fixture)
  2. Parses Gurmukhi lines and metadata
  3. Normalizes gurmukhi_raw -> gurmukhi
  4. Tokenizes gurmukhi -> tokens + token_spans
  5. Composes canonical records (PLAN.md Section 3.3)
  6. Validates the corpus
  7. Writes ggs_lines.jsonl + run_manifest.json + validation_report.json

This is the Phase 0 "done" milestone: the corpus is ready for Phase 1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.corpus.normalize import (
    NORMALIZER_VERSION,
    NormalizationConfig,
    normalize,
)
from ggs.corpus.parse_srigranth import (
    PARSER_VERSION,
    parse_ang,
    to_canonical_records,
)
from ggs.corpus.tokenize import TOKENIZER_VERSION, tokenize
from ggs.corpus.validate import validate_corpus
from ggs.pipeline.errors import ErrorConfig
from ggs.pipeline.manifest import RunManifest

_console = Console()

# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


def _process_ang_html(
    html: str,
    ang: int,
    *,
    norm_config: NormalizationConfig | None = None,
) -> list[dict[str, Any]]:
    """Process a single ang's HTML through the full Phase 0 pipeline.

    Steps:
      1. Parse HTML -> AngParseResult (lines + metadata)
      2. Convert to canonical records with normalization
      3. Tokenize each record's gurmukhi field
      4. Return list of canonical record dicts

    Args:
        html: Raw HTML string.
        ang: Ang number.
        norm_config: Normalization configuration.

    Returns:
        List of canonical record dicts ready for JSONL output.
    """
    if norm_config is None:
        norm_config = NormalizationConfig()

    # Step 1-2: Parse and convert to canonical records with normalization
    parse_result = parse_ang(html, ang=ang)

    if parse_result.errors:
        _console.print(
            f"  [yellow]Ang {ang}: {len(parse_result.errors)} "
            f"parse errors[/yellow]"
        )
        return []

    records = to_canonical_records(
        parse_result,
        normalize_fn=lambda text: normalize(text, norm_config),
    )

    # Step 3: Tokenize each record
    for rec in records:
        tok_result = tokenize(rec["gurmukhi"])
        rec["tokens"] = tok_result.tokens
        rec["token_spans"] = tok_result.token_spans
        rec["meta"]["structural_markers"] = (
            tok_result.structural_markers
        )

    return records


def run_phase0(
    input_dir: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    norm_config: NormalizationConfig | None = None,
    error_config: ErrorConfig | None = None,
    ang_range: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Run the full Phase 0 pipeline.

    Args:
        input_dir: Directory containing raw HTML files
            (``ang_NNNN.html`` or ``ang_NNN.html``).
        output_dir: Directory for output artifacts
            (``ggs_lines.jsonl``, ``run_manifest.json``,
            ``validation_report.json``).
        config_path: Path to config.yaml for manifest provenance.
        norm_config: Normalization configuration.
        error_config: Error handling configuration.
        ang_range: Optional ``(start, end)`` to limit which angs
            to process.  Defaults to all HTML files found.

    Returns:
        Dict with summary: ``total_lines``, ``total_angs``,
        ``validation_verdict``, ``output_files``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Start manifest
    manifest = RunManifest(
        phase="corpus",
        config_path=config_path,
    )
    manifest.record_input(input_dir)
    manifest.set_extra(
        "pipeline_versions", {
            "parser": PARSER_VERSION,
            "normalizer": NORMALIZER_VERSION,
            "tokenizer": TOKENIZER_VERSION,
        },
    )

    # Discover HTML files
    html_files = _discover_html_files(input_dir, ang_range)

    if not html_files:
        _console.print(
            "[red]No HTML files found in "
            f"{input_dir}[/red]"
        )
        return {
            "total_lines": 0,
            "total_angs": 0,
            "validation_verdict": "FAIL",
            "output_files": [],
        }

    _console.print(
        f"\n[bold]Phase 0: Processing {len(html_files)} "
        f"ang(s)...[/bold]\n"
    )

    # Process each ang
    all_records: list[dict[str, Any]] = []
    for ang, html_path in sorted(html_files.items()):
        html = html_path.read_text(encoding="utf-8")
        records = _process_ang_html(
            html, ang, norm_config=norm_config,
        )
        all_records.extend(records)

    _console.print(
        f"  Parsed {len(all_records)} lines from "
        f"{len(html_files)} angs"
    )

    # Write ggs_lines.jsonl
    jsonl_path = output_dir / "ggs_lines.jsonl"
    _write_jsonl(all_records, jsonl_path)
    manifest.record_output(jsonl_path)

    # Validate
    _console.print("  Running validation...")
    report = validate_corpus(
        all_records, error_config=error_config,
    )

    # Write validation report
    report_path = output_dir / "validation_report.json"
    report.write(report_path)
    manifest.record_output(report_path)

    # Finalize manifest
    manifest.set_record_counts(
        total_lines=len(all_records),
        total_angs=len(html_files),
    )
    manifest.set_error_summary(
        errors=len(report.errors),
        warnings=len(report.warnings),
    )
    manifest_path = output_dir / "run_manifest.json"
    manifest.finalize(manifest_path)

    verdict = report.verdict
    verdict_style = "green" if verdict == "PASS" else "red"
    _console.print(
        f"\n[bold {verdict_style}]Phase 0 complete: "
        f"{verdict}[/bold {verdict_style}]"
    )
    _console.print(
        f"  Lines: {len(all_records)}, "
        f"Angs: {len(html_files)}, "
        f"Errors: {len(report.errors)}, "
        f"Warnings: {len(report.warnings)}"
    )

    output_files = [
        str(jsonl_path),
        str(report_path),
        str(manifest_path),
    ]

    return {
        "total_lines": len(all_records),
        "total_angs": len(html_files),
        "validation_verdict": verdict,
        "output_files": output_files,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _discover_html_files(
    input_dir: Path,
    ang_range: tuple[int, int] | None = None,
) -> dict[int, Path]:
    """Discover HTML files in *input_dir* and map ang numbers to paths.

    Recognizes filenames like ``ang_0001.html``, ``ang_001.html``,
    or ``ang_1.html``.
    """
    html_files: dict[int, Path] = {}

    for path in sorted(input_dir.glob("ang_*.html")):
        # Extract ang number from filename
        stem = path.stem  # e.g. "ang_001" or "ang_0001"
        parts = stem.split("_", 1)
        if len(parts) != 2:
            continue
        try:
            ang = int(parts[1])
        except ValueError:
            continue

        if ang_range is not None:
            start, end = ang_range
            if ang < start or ang > end:
                continue

        html_files[ang] = path

    return html_files


def _write_jsonl(
    records: list[dict[str, Any]],
    path: Path,
) -> None:
    """Write records as JSONL (one JSON object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(
                json.dumps(rec, ensure_ascii=False) + "\n"
            )
