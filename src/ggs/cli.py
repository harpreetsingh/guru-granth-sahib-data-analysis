"""GGS command-line interface — Typer framework with subcommand groups (bd-11y.1).

Provides the ``ggs`` CLI with subcommand groups for all pipeline phases:

    ggs corpus extract    -- Phase 0: scrape + parse + normalize + tokenize
    ggs corpus validate   -- Validate an existing corpus
    ggs corpus cross-validate -- Cross-validate against secondary sources
    ggs analysis lexical  -- Phase 1: Aho-Corasick entity matching
    ggs analysis structural -- Phase 2: density/feature computation
    ggs analysis tags     -- Phase 3: rule-based tagging
    ggs pipeline run      -- Run multiple phases in sequence
    ggs lexicon lint      -- Lint all lexicon YAML files
    ggs bundle build      -- Build web bundle from pipeline outputs

Common options (available on all subcommands via the root callback):
    --config, --output, --force, --dry-run, --verbose, --workers
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ggs import __version__

# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------

console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Root application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="ggs",
    help="Guru Granth Sahib — Structured Multi-Layer Textual Analysis Platform",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ---------------------------------------------------------------------------
# Shared state (populated by root callback, consumed by subcommands)
# ---------------------------------------------------------------------------


class _State:
    """Mutable state shared across all subcommands via the root callback."""

    config_path: Path = Path("config/config.yaml")
    output_dir: Path | None = None
    force: bool = False
    dry_run: bool = False
    verbose: bool = False
    workers: int | None = None


_state = _State()


def _display_run_header() -> None:
    """Print a rich panel with the current run configuration."""
    info_lines = [
        f"[bold]Config:[/bold]  {_state.config_path}",
        f"[bold]Output:[/bold]  {_state.output_dir or '(default)'}",
        f"[bold]Force:[/bold]   {_state.force}",
        f"[bold]Dry-run:[/bold] {_state.dry_run}",
        f"[bold]Workers:[/bold] {_state.workers or os.cpu_count() or 1}",
    ]
    console.print(
        Panel(
            "\n".join(info_lines),
            title=f"[bold]ggs v{__version__}[/bold]",
            border_style="blue",
        ),
    )


# ---------------------------------------------------------------------------
# Root callback — common options
# ---------------------------------------------------------------------------


@app.callback()
def main(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            help="Path to config.yaml.",
            exists=True,
            dir_okay=False,
        ),
    ] = Path("config/config.yaml"),
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help="Output directory (overrides per-phase defaults).",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Bypass cache — re-run even if inputs unchanged.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be done without executing.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Increase log verbosity.",
        ),
    ] = False,
    workers: Annotated[
        int | None,
        typer.Option(
            "--workers",
            help="Number of parallel workers (default: cpu_count).",
            min=1,
        ),
    ] = None,
) -> None:
    """Guru Granth Sahib — Structured Multi-Layer Textual Analysis."""
    _state.config_path = config
    _state.output_dir = output
    _state.force = force
    _state.dry_run = dry_run
    _state.verbose = verbose
    _state.workers = workers


# ---------------------------------------------------------------------------
# Subcommand groups
# ---------------------------------------------------------------------------

corpus_app = typer.Typer(
    name="corpus",
    help="Phase 0 — Canonical corpus extraction and validation.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(corpus_app, name="corpus")

analysis_app = typer.Typer(
    name="analysis",
    help="Phases 1-3 — Lexical, structural, and interpretive analysis.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(analysis_app, name="analysis")

pipeline_app = typer.Typer(
    name="pipeline",
    help="Multi-phase pipeline orchestration.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(pipeline_app, name="pipeline")

lexicon_app = typer.Typer(
    name="lexicon",
    help="Lexicon management and QA tools.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(lexicon_app, name="lexicon")

bundle_app = typer.Typer(
    name="bundle",
    help="Web bundle generation.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(bundle_app, name="bundle")


# ---------------------------------------------------------------------------
# corpus subcommands
# ---------------------------------------------------------------------------


@corpus_app.command("extract")
def corpus_extract(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input-dir",
            help="Directory containing raw HTML files.",
        ),
    ] = Path("data/raw_html"),
    ang_start: Annotated[
        int | None,
        typer.Option(help="First ang to process (1-1430)."),
    ] = None,
    ang_end: Annotated[
        int | None,
        typer.Option(help="Last ang to process (1-1430)."),
    ] = None,
) -> None:
    """Extract canonical corpus from raw HTML (Phase 0 pipeline)."""
    from ggs.corpus.pipeline import run_phase0

    _display_run_header()
    output = _state.output_dir or Path("data/corpus")

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would run Phase 0 corpus extraction\n"
            f"  Input:  {input_dir}\n"
            f"  Output: {output}",
        )
        return

    ang_range = None
    if ang_start is not None and ang_end is not None:
        ang_range = (ang_start, ang_end)

    result = run_phase0(
        input_dir=input_dir,
        output_dir=output,
        config_path=_state.config_path,
        ang_range=ang_range,
    )

    _display_result_table("Phase 0: Corpus Extraction", {
        "Lines": str(result["total_lines"]),
        "Angs": str(result["total_angs"]),
        "Verdict": result["validation_verdict"],
    })


@corpus_app.command("validate")
def corpus_validate(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus",
            help="Path to ggs_lines.jsonl.",
        ),
    ] = Path("data/corpus/ggs_lines.jsonl"),
) -> None:
    """Validate an existing corpus JSONL file."""
    import json

    from ggs.corpus.validate import validate_corpus

    _display_run_header()

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would validate "
            f"{corpus_path}",
        )
        return

    if not corpus_path.exists():
        err_console.print(
            f"[red]Error:[/red] Corpus not found: {corpus_path}",
        )
        raise typer.Exit(code=1)

    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]

    report = validate_corpus(records)
    report.display() if hasattr(report, "display") else None

    _display_result_table("Corpus Validation", {
        "Lines": str(report.total_lines),
        "Verdict": report.verdict,
        "Errors": str(len(report.errors)),
        "Warnings": str(len(report.warnings)),
    })

    if report.verdict != "PASS":
        raise typer.Exit(code=1)


@corpus_app.command("cross-validate")
def corpus_cross_validate() -> None:
    """Cross-validate corpus against secondary sources."""
    _display_run_header()

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would run cross-validation",
        )
        return

    console.print(
        "[yellow]Cross-validation requires network access to "
        "secondary sources.[/yellow]\n"
        "Use [bold]ggs corpus extract[/bold] first to build the "
        "primary corpus.",
    )


# ---------------------------------------------------------------------------
# analysis subcommands
# ---------------------------------------------------------------------------


@analysis_app.command("lexical")
def analysis_lexical(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus",
            help="Path to ggs_lines.jsonl.",
        ),
    ] = Path("data/corpus/ggs_lines.jsonl"),
) -> None:
    """Run Phase 1: Aho-Corasick entity matching."""
    import json

    import yaml

    from ggs.analysis.match import run_matching
    from ggs.lexicon.loader import load_lexicon

    _display_run_header()
    output = _state.output_dir or Path("data/analysis")

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would run lexical matching\n"
            f"  Corpus:  {corpus_path}\n"
            f"  Output:  {output}",
        )
        return

    if not corpus_path.exists():
        err_console.print(
            f"[red]Error:[/red] Corpus not found: {corpus_path}",
        )
        raise typer.Exit(code=1)

    config = yaml.safe_load(
        _state.config_path.read_text(encoding="utf-8"),
    )
    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]

    index = load_lexicon(
        config.get("lexicon_paths", {}),
        base_dir=_state.config_path.parent.parent,
    )

    matches_path = output / "matches.jsonl"
    matches = run_matching(records, index, output_path=matches_path)

    _display_result_table("Phase 1: Lexical Matching", {
        "Lines scanned": str(len(records)),
        "Matches found": str(len(matches)),
        "Output": str(matches_path),
    })


@analysis_app.command("structural")
def analysis_structural(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus",
            help="Path to ggs_lines.jsonl.",
        ),
    ] = Path("data/corpus/ggs_lines.jsonl"),
    matches_path: Annotated[
        Path,
        typer.Option(
            "--matches",
            help="Path to matches.jsonl.",
        ),
    ] = Path("data/analysis/matches.jsonl"),
) -> None:
    """Run Phase 2: structural analysis (density/feature computation)."""
    import json

    import yaml

    from ggs.analysis.features import compute_corpus_features
    from ggs.analysis.match import MatchRecord
    from ggs.lexicon.loader import load_lexicon

    _display_run_header()
    output = _state.output_dir or Path("data/analysis")

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would run structural analysis\n"
            f"  Corpus:   {corpus_path}\n"
            f"  Matches:  {matches_path}\n"
            f"  Output:   {output}",
        )
        return

    for path, label in [(corpus_path, "Corpus"), (matches_path, "Matches")]:
        if not path.exists():
            err_console.print(
                f"[red]Error:[/red] {label} not found: {path}",
            )
            raise typer.Exit(code=1)

    config = yaml.safe_load(
        _state.config_path.read_text(encoding="utf-8"),
    )
    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]

    # Reconstruct match records from JSONL
    match_dicts = [
        json.loads(line)
        for line in matches_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]
    matches = [
        MatchRecord(
            line_uid=d["line_uid"],
            entity_id=d["entity_id"],
            matched_form=d["matched_form"],
            span=d["span"],
            rule_id=d.get("rule_id", "alias_exact"),
            confidence=d.get("confidence", "HIGH"),
            ambiguity=d.get("ambiguity"),
            nested_in=d.get("nested_in"),
        )
        for d in match_dicts
    ]

    index = load_lexicon(
        config.get("lexicon_paths", {}),
        base_dir=_state.config_path.parent.parent,
    )

    features_path = output / "features.jsonl"
    features = compute_corpus_features(
        records, matches, index, output_path=features_path,
    )

    _display_result_table("Phase 2: Structural Analysis", {
        "Lines": str(len(records)),
        "Features computed": str(len(features)),
        "Output": str(features_path),
    })


@analysis_app.command("tags")
def analysis_tags(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus",
            help="Path to ggs_lines.jsonl.",
        ),
    ] = Path("data/corpus/ggs_lines.jsonl"),
    matches_path: Annotated[
        Path,
        typer.Option(
            "--matches",
            help="Path to matches.jsonl.",
        ),
    ] = Path("data/analysis/matches.jsonl"),
    features_path: Annotated[
        Path,
        typer.Option(
            "--features",
            help="Path to features.jsonl.",
        ),
    ] = Path("data/analysis/features.jsonl"),
) -> None:
    """Run Phase 3: rule-based interpretive tagging."""
    import json

    import yaml

    from ggs.analysis.match import MatchRecord
    from ggs.analysis.tagger import run_tagger

    _display_run_header()
    output = _state.output_dir or Path("data/analysis")

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would run tagging\n"
            f"  Corpus:    {corpus_path}\n"
            f"  Matches:   {matches_path}\n"
            f"  Features:  {features_path}\n"
            f"  Output:    {output}",
        )
        return

    for path, label in [
        (corpus_path, "Corpus"),
        (matches_path, "Matches"),
        (features_path, "Features"),
    ]:
        if not path.exists():
            err_console.print(
                f"[red]Error:[/red] {label} not found: {path}",
            )
            raise typer.Exit(code=1)

    config = yaml.safe_load(
        _state.config_path.read_text(encoding="utf-8"),
    )
    records = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]

    match_dicts = [
        json.loads(line)
        for line in matches_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]
    matches = [
        MatchRecord(
            line_uid=d["line_uid"],
            entity_id=d["entity_id"],
            matched_form=d["matched_form"],
            span=d["span"],
            rule_id=d.get("rule_id", "alias_exact"),
            confidence=d.get("confidence", "HIGH"),
            ambiguity=d.get("ambiguity"),
            nested_in=d.get("nested_in"),
        )
        for d in match_dicts
    ]

    features = [
        json.loads(line)
        for line in features_path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]

    tagging_config = config.get("tagging", {})
    tags = run_tagger(
        records, matches, features, tagging_config, output_dir=output,
    )

    _display_result_table("Phase 3: Interpretive Tagging", {
        "Lines": str(len(records)),
        "Tags generated": str(len(tags)),
        "Output": str(output),
    })


# ---------------------------------------------------------------------------
# pipeline subcommands
# ---------------------------------------------------------------------------


@pipeline_app.command("run")
def pipeline_run(
    phases: Annotated[
        str,
        typer.Option(
            "--phases",
            help="Comma-separated phase numbers to run (e.g. '0,1,2,3').",
        ),
    ] = "0,1,2,3",
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input-dir",
            help="Directory containing raw HTML files (Phase 0 input).",
        ),
    ] = Path("data/raw_html"),
) -> None:
    """Run multiple pipeline phases in sequence (bd-11y.4).

    Orchestrates Phases 0-3 in order, validating that each phase's
    required inputs exist before running.  If any phase fails, the
    pipeline aborts immediately.
    """
    import time

    import yaml

    from ggs.analysis.features import compute_corpus_features
    from ggs.analysis.match import run_matching
    from ggs.analysis.tagger import run_tagger
    from ggs.corpus.pipeline import run_phase0
    from ggs.lexicon.loader import load_lexicon

    _display_run_header()

    phase_nums = sorted({int(p.strip()) for p in phases.split(",")})
    valid = {0, 1, 2, 3}
    invalid = set(phase_nums) - valid
    if invalid:
        err_console.print(
            f"[red]Error:[/red] Invalid phase numbers: {invalid}. "
            f"Valid: {sorted(valid)}",
        )
        raise typer.Exit(code=1)

    if _state.dry_run:
        console.print(
            f"[yellow]DRY RUN:[/yellow] Would run phases: {phase_nums}",
        )
        return

    console.print(
        f"\n[bold]Pipeline: running phases {phase_nums}[/bold]\n",
    )

    config = yaml.safe_load(
        _state.config_path.read_text(encoding="utf-8"),
    )
    base_output = _state.output_dir or Path("data")
    corpus_dir = base_output / "corpus"
    analysis_dir = base_output / "analysis"
    corpus_path = corpus_dir / "ggs_lines.jsonl"
    matches_path = analysis_dir / "matches.jsonl"
    features_path = analysis_dir / "features.jsonl"

    phase_results: dict[int, dict[str, str]] = {}
    pipeline_t0 = time.monotonic()

    # ------------------------------------------------------------------
    # Phase 0: Corpus extraction
    # ------------------------------------------------------------------
    if 0 in phase_nums:
        t0 = time.monotonic()
        try:
            result = run_phase0(
                input_dir=input_dir,
                output_dir=corpus_dir,
                config_path=_state.config_path,
            )
            elapsed = time.monotonic() - t0
            phase_results[0] = {
                "status": "PASS" if result["validation_verdict"] == "PASS" else "FAIL",
                "time": f"{elapsed:.2f}s",
                "detail": f"{result['total_lines']} lines, {result['total_angs']} angs",
            }
            if result["validation_verdict"] != "PASS":
                err_console.print(
                    "[red]Phase 0 failed validation. Aborting pipeline.[/red]",
                )
                _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
                raise typer.Exit(code=1)
        except typer.Exit:
            raise
        except Exception as exc:
            phase_results[0] = {
                "status": "FAIL",
                "time": f"{time.monotonic() - t0:.2f}s",
                "detail": str(exc),
            }
            _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
            raise typer.Exit(code=1) from exc

    # ------------------------------------------------------------------
    # Phase 1: Lexical matching
    # ------------------------------------------------------------------
    if 1 in phase_nums:
        if not corpus_path.exists():
            err_console.print(
                f"[red]Error:[/red] Phase 1 requires {corpus_path}\n"
                "  Run: [bold]ggs corpus extract[/bold] or include phase 0",
            )
            phase_results[1] = {
                "status": "SKIP",
                "time": "0s",
                "detail": f"Missing {corpus_path}",
            }
            _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
            raise typer.Exit(code=1)

        t0 = time.monotonic()
        try:
            records = _load_jsonl(corpus_path)
            index = load_lexicon(
                config.get("lexicon_paths", {}),
                base_dir=_state.config_path.parent.parent,
            )
            analysis_dir.mkdir(parents=True, exist_ok=True)
            matches = run_matching(records, index, output_path=matches_path)
            elapsed = time.monotonic() - t0
            phase_results[1] = {
                "status": "PASS",
                "time": f"{elapsed:.2f}s",
                "detail": f"{len(matches)} matches from {len(records)} lines",
            }
        except typer.Exit:
            raise
        except Exception as exc:
            phase_results[1] = {
                "status": "FAIL",
                "time": f"{time.monotonic() - t0:.2f}s",
                "detail": str(exc),
            }
            _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
            raise typer.Exit(code=1) from exc

    # ------------------------------------------------------------------
    # Phase 2: Structural analysis (features)
    # ------------------------------------------------------------------
    if 2 in phase_nums:
        for path, label, fix in [
            (corpus_path, "corpus", "ggs corpus extract"),
            (matches_path, "matches", "ggs analysis lexical"),
        ]:
            if not path.exists():
                err_console.print(
                    f"[red]Error:[/red] Phase 2 requires {path}\n"
                    f"  Run: [bold]{fix}[/bold] or include earlier phases",
                )
                phase_results[2] = {
                    "status": "SKIP",
                    "time": "0s",
                    "detail": f"Missing {label}",
                }
                _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
                raise typer.Exit(code=1)

        t0 = time.monotonic()
        try:
            records = _load_jsonl(corpus_path)
            match_records = _load_match_records(matches_path)
            index = load_lexicon(
                config.get("lexicon_paths", {}),
                base_dir=_state.config_path.parent.parent,
            )
            features = compute_corpus_features(
                records, match_records, index,
                output_path=features_path,
            )
            elapsed = time.monotonic() - t0
            phase_results[2] = {
                "status": "PASS",
                "time": f"{elapsed:.2f}s",
                "detail": f"{len(features)} feature vectors",
            }
        except typer.Exit:
            raise
        except Exception as exc:
            phase_results[2] = {
                "status": "FAIL",
                "time": f"{time.monotonic() - t0:.2f}s",
                "detail": str(exc),
            }
            _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
            raise typer.Exit(code=1) from exc

    # ------------------------------------------------------------------
    # Phase 3: Interpretive tagging
    # ------------------------------------------------------------------
    if 3 in phase_nums:
        for path, label, fix in [
            (corpus_path, "corpus", "ggs corpus extract"),
            (matches_path, "matches", "ggs analysis lexical"),
            (features_path, "features", "ggs analysis structural"),
        ]:
            if not path.exists():
                err_console.print(
                    f"[red]Error:[/red] Phase 3 requires {path}\n"
                    f"  Run: [bold]{fix}[/bold] or include earlier phases",
                )
                phase_results[3] = {
                    "status": "SKIP",
                    "time": "0s",
                    "detail": f"Missing {label}",
                }
                _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
                raise typer.Exit(code=1)

        t0 = time.monotonic()
        try:
            records = _load_jsonl(corpus_path)
            match_records = _load_match_records(matches_path)
            feat_records = _load_jsonl(features_path)
            tagging_config = config.get("tagging", {})
            tags = run_tagger(
                records, match_records, feat_records,
                tagging_config, output_dir=analysis_dir,
            )
            elapsed = time.monotonic() - t0
            phase_results[3] = {
                "status": "PASS",
                "time": f"{elapsed:.2f}s",
                "detail": f"{len(tags)} tags generated",
            }
        except typer.Exit:
            raise
        except Exception as exc:
            phase_results[3] = {
                "status": "FAIL",
                "time": f"{time.monotonic() - t0:.2f}s",
                "detail": str(exc),
            }
            _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)
            raise typer.Exit(code=1) from exc

    _display_pipeline_summary(phase_results, time.monotonic() - pipeline_t0)


# ---------------------------------------------------------------------------
# lexicon subcommands
# ---------------------------------------------------------------------------


@lexicon_app.command("lint")
def lexicon_lint_cmd() -> None:
    """Lint all lexicon YAML files for schema conformance and QA."""
    import yaml

    from ggs.lexicon.lint import lint_lexicon

    _display_run_header()

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would lint lexicon files",
        )
        return

    config = yaml.safe_load(
        _state.config_path.read_text(encoding="utf-8"),
    )
    lexicon_paths = config.get("lexicon_paths", {})

    report = lint_lexicon(
        lexicon_paths,
        base_dir=_state.config_path.parent.parent,
    )
    report.display()

    if not report.passed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# bundle subcommands
# ---------------------------------------------------------------------------


@bundle_app.command("build")
def bundle_build(
    corpus_path: Annotated[
        Path,
        typer.Option(
            "--corpus",
            help="Path to ggs_lines.jsonl.",
        ),
    ] = Path("data/corpus/ggs_lines.jsonl"),
    analysis_dir: Annotated[
        Path,
        typer.Option(
            "--analysis-dir",
            help="Directory containing analysis outputs.",
        ),
    ] = Path("data/analysis"),
) -> None:
    """Build web bundle from pipeline outputs."""
    _display_run_header()
    output = _state.output_dir or Path("data/web_bundle")

    if _state.dry_run:
        console.print(
            "[yellow]DRY RUN:[/yellow] Would build web bundle\n"
            f"  Corpus:   {corpus_path}\n"
            f"  Analysis: {analysis_dir}\n"
            f"  Output:   {output}",
        )
        return

    for path, label in [(corpus_path, "Corpus"), (analysis_dir, "Analysis dir")]:
        if not path.exists():
            err_console.print(
                f"[red]Error:[/red] {label} not found: {path}",
            )
            raise typer.Exit(code=1)

    console.print(
        "[yellow]Web bundle build requires all pipeline phases "
        "to have been run first.[/yellow]\n"
        "Bundle builder will be wired in bd-11y.4 (pipeline orchestrator).",
    )


# ---------------------------------------------------------------------------
# Version command
# ---------------------------------------------------------------------------


@app.command("version")
def version_cmd() -> None:
    """Show the GGS platform version."""
    console.print(
        Panel(
            f"[bold]{__version__}[/bold]",
            title="ggs version",
            border_style="green",
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    import json

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").strip().split("\n")
        if line.strip()
    ]


def _load_match_records(path: Path) -> list:
    """Load match records from a JSONL file."""
    import json

    from ggs.analysis.match import MatchRecord

    return [
        MatchRecord(
            line_uid=d["line_uid"],
            entity_id=d["entity_id"],
            matched_form=d["matched_form"],
            span=d["span"],
            rule_id=d.get("rule_id", "alias_exact"),
            confidence=d.get("confidence", "HIGH"),
            ambiguity=d.get("ambiguity"),
            nested_in=d.get("nested_in"),
        )
        for d in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").strip().split("\n")
            if line.strip()
        )
    ]


def _display_result_table(
    title: str,
    results: dict[str, str],
) -> None:
    """Display a rich summary table for a completed phase."""
    table = Table(
        title=title,
        show_header=True,
        header_style="bold blue",
    )
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    for key, value in results.items():
        style = ""
        if value == "PASS":
            style = "green"
        elif value == "FAIL":
            style = "red"
        table.add_row(key, f"[{style}]{value}[/{style}]" if style else value)

    console.print()
    console.print(table)
    console.print()


def _display_pipeline_summary(
    phase_results: dict[int, dict[str, str]],
    total_elapsed: float,
) -> None:
    """Display a rich summary table for the pipeline run."""
    phase_names = {
        0: "Corpus Extraction",
        1: "Lexical Matching",
        2: "Structural Analysis",
        3: "Interpretive Tagging",
    }

    table = Table(
        title="Pipeline Summary",
        show_header=True,
        header_style="bold blue",
    )
    table.add_column("Phase", style="bold")
    table.add_column("Status")
    table.add_column("Time")
    table.add_column("Detail")

    all_pass = True
    for phase_num in sorted(phase_results.keys()):
        result = phase_results[phase_num]
        name = phase_names.get(phase_num, f"Phase {phase_num}")
        status = result["status"]

        if status == "PASS":
            status_display = "[green]PASS[/green]"
        elif status == "FAIL":
            status_display = "[red]FAIL[/red]"
            all_pass = False
        else:
            status_display = f"[yellow]{status}[/yellow]"
            all_pass = False

        table.add_row(
            f"Phase {phase_num}: {name}",
            status_display,
            result["time"],
            result["detail"],
        )

    console.print()
    console.print(table)

    verdict_style = "green" if all_pass else "red"
    verdict = "PASS" if all_pass else "FAIL"
    console.print(
        f"\n[bold {verdict_style}]Pipeline {verdict}[/bold {verdict_style}] "
        f"in {total_elapsed:.2f}s\n",
    )
