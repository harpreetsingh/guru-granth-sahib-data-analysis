"""Register density aggregations and sliding window analysis (bd-9qw.4).

Aggregates per-line density scores (from features.py) into higher-level
views:
  - By ang: mean density per ang
  - By raga: mean, median, std per raga section
  - Sliding window: rolling mean density over W-ang windows

Produces time-series-like data enabling visualization of register shifts
across the 1430 angs of the Guru Granth Sahib.

Reference: PLAN.md Section 5.2
"""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from ggs.analysis.features import FEATURE_DIMENSIONS

_console = Console()


# ---------------------------------------------------------------------------
# Raga section mapping
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RagaSection:
    """A raga section with its ang range.

    Attributes:
        id: Raga identifier (e.g. ``"SRI"``).
        romanized: Romanized name (e.g. ``"Sri Raag"``).
        ang_start: First ang in the section.
        ang_end: Last ang in the section (inclusive).
    """

    id: str
    romanized: str
    ang_start: int
    ang_end: int


def load_raga_sections(ragas_path: Path) -> list[RagaSection]:
    """Load raga sections from ragas.yaml.

    Includes preamble and epilogue as pseudo-raga sections.

    Args:
        ragas_path: Path to ragas.yaml.

    Returns:
        List of RagaSection in text order.
    """
    data = yaml.safe_load(ragas_path.read_text(encoding="utf-8"))

    sections: list[RagaSection] = []

    # Preamble
    preamble = data.get("preamble", {})
    if preamble:
        sections.append(
            RagaSection(
                id="PREAMBLE",
                romanized=preamble.get("romanized", "Preamble"),
                ang_start=preamble.get("ang_start", 1),
                ang_end=preamble.get("ang_end", 13),
            ),
        )

    # Ragas
    for raga in data.get("ragas", []):
        sections.append(
            RagaSection(
                id=raga["id"],
                romanized=raga.get("romanized", raga["id"]),
                ang_start=raga["ang_start"],
                ang_end=raga["ang_end"],
            ),
        )

    # Epilogue
    epilogue = data.get("epilogue", {})
    if epilogue:
        sections.append(
            RagaSection(
                id="EPILOGUE",
                romanized=epilogue.get("romanized", "Epilogue"),
                ang_start=epilogue.get("ang_start", 1354),
                ang_end=epilogue.get("ang_end", 1430),
            ),
        )

    return sections


def ang_to_raga(
    ang: int,
    sections: list[RagaSection],
) -> str | None:
    """Map an ang number to its raga section ID.

    Returns None if the ang doesn't fall in any known section.
    """
    for section in sections:
        if section.ang_start <= ang <= section.ang_end:
            return section.id
    return None


# ---------------------------------------------------------------------------
# Aggregation records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AngDensity:
    """Mean density per register for a single ang.

    Attributes:
        ang: Ang number (1-1430).
        line_count: Number of lines in this ang.
        densities: Mean density per feature dimension.
    """

    ang: int
    line_count: int
    densities: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ang": self.ang,
            "line_count": self.line_count,
            "densities": {
                k: round(v, 6) for k, v in self.densities.items()
            },
        }


@dataclass(frozen=True, slots=True)
class RagaDensity:
    """Aggregated density stats per register for a raga section.

    Attributes:
        raga_id: Raga section identifier.
        romanized: Human-readable raga name.
        ang_start: First ang.
        ang_end: Last ang (inclusive).
        line_count: Total lines in this raga.
        stats: Per-dimension stats dict with mean, median, std.
    """

    raga_id: str
    romanized: str
    ang_start: int
    ang_end: int
    line_count: int
    stats: dict[str, dict[str, float]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raga_id": self.raga_id,
            "romanized": self.romanized,
            "ang_start": self.ang_start,
            "ang_end": self.ang_end,
            "line_count": self.line_count,
            "stats": {
                dim: {k: round(v, 6) for k, v in s.items()}
                for dim, s in self.stats.items()
            },
        }


@dataclass(frozen=True, slots=True)
class WindowDensity:
    """Rolling-window density for a single window position.

    Attributes:
        window_start: First ang in this window.
        window_end: Last ang in this window (inclusive).
        densities: Mean density per feature dimension within this window.
    """

    window_start: int
    window_end: int
    densities: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_start": self.window_start,
            "window_end": self.window_end,
            "densities": {
                k: round(v, 6) for k, v in self.densities.items()
            },
        }


# ---------------------------------------------------------------------------
# Index features by ang
# ---------------------------------------------------------------------------


def _index_features_by_ang(
    feature_records: list[dict[str, Any]],
    corpus_records: list[dict[str, Any]],
) -> dict[int, list[dict[str, float]]]:
    """Build a mapping from ang number to list of density dicts.

    Args:
        feature_records: Feature records from features.jsonl.
        corpus_records: Corpus records from ggs_lines.jsonl.

    Returns:
        Mapping from ang to list of density dicts for each line.
    """
    # Build line_uid -> ang mapping
    uid_to_ang: dict[str, int] = {}
    for rec in corpus_records:
        line_uid = rec.get("line_uid", "")
        ang = rec.get("ang")
        if ang is not None:
            uid_to_ang[line_uid] = ang

    # Group feature densities by ang
    by_ang: dict[int, list[dict[str, float]]] = defaultdict(list)
    for feat in feature_records:
        line_uid = feat.get("line_uid", "")
        ang = uid_to_ang.get(line_uid)
        if ang is None:
            continue

        densities: dict[str, float] = {}
        features = feat.get("features", {})
        for dim in FEATURE_DIMENSIONS:
            densities[dim] = features.get(dim, {}).get("density", 0.0)
        by_ang[ang].append(densities)

    return dict(by_ang)


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------


def _safe_mean(values: list[float]) -> float:
    """Compute mean, returning 0.0 for empty lists."""
    if not values:
        return 0.0
    return statistics.mean(values)


def _safe_median(values: list[float]) -> float:
    """Compute median, returning 0.0 for empty lists."""
    if not values:
        return 0.0
    return statistics.median(values)


def _safe_stdev(values: list[float]) -> float:
    """Compute sample standard deviation, returning 0.0 for < 2 values."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


# ---------------------------------------------------------------------------
# Per-ang aggregation
# ---------------------------------------------------------------------------


def compute_ang_densities(
    features_by_ang: dict[int, list[dict[str, float]]],
) -> list[AngDensity]:
    """Compute mean density per register for each ang.

    Args:
        features_by_ang: Mapping from ang to list of density dicts.

    Returns:
        List of AngDensity records, sorted by ang number.
    """
    results: list[AngDensity] = []

    for ang in sorted(features_by_ang.keys()):
        line_densities = features_by_ang[ang]
        line_count = len(line_densities)

        mean_densities: dict[str, float] = {}
        for dim in FEATURE_DIMENSIONS:
            values = [d.get(dim, 0.0) for d in line_densities]
            mean_densities[dim] = _safe_mean(values)

        results.append(
            AngDensity(
                ang=ang,
                line_count=line_count,
                densities=mean_densities,
            ),
        )

    return results


# ---------------------------------------------------------------------------
# Per-raga aggregation
# ---------------------------------------------------------------------------


def compute_raga_densities(
    features_by_ang: dict[int, list[dict[str, float]]],
    sections: list[RagaSection],
) -> list[RagaDensity]:
    """Compute density statistics per raga section.

    For each raga, aggregates all line densities from its ang range and
    computes mean, median, and standard deviation per register.

    Args:
        features_by_ang: Mapping from ang to list of density dicts.
        sections: Raga sections from ragas.yaml.

    Returns:
        List of RagaDensity records in section order.
    """
    results: list[RagaDensity] = []

    for section in sections:
        # Collect all line densities in this raga's ang range
        all_densities: list[dict[str, float]] = []
        for ang in range(section.ang_start, section.ang_end + 1):
            all_densities.extend(features_by_ang.get(ang, []))

        line_count = len(all_densities)

        stats: dict[str, dict[str, float]] = {}
        for dim in FEATURE_DIMENSIONS:
            values = [d.get(dim, 0.0) for d in all_densities]
            stats[dim] = {
                "mean": _safe_mean(values),
                "median": _safe_median(values),
                "stdev": _safe_stdev(values),
            }

        results.append(
            RagaDensity(
                raga_id=section.id,
                romanized=section.romanized,
                ang_start=section.ang_start,
                ang_end=section.ang_end,
                line_count=line_count,
                stats=stats,
            ),
        )

    return results


# ---------------------------------------------------------------------------
# Sliding window
# ---------------------------------------------------------------------------


def compute_sliding_window(
    ang_densities: list[AngDensity],
    *,
    window_size: int = 20,
) -> list[WindowDensity]:
    """Compute rolling-mean density using a sliding window.

    Slides a window of ``window_size`` angs across all angs, computing
    the mean density per register within each window position.

    Args:
        ang_densities: Per-ang density records (sorted by ang).
        window_size: Number of angs per window (default 20).

    Returns:
        List of WindowDensity records.
    """
    if not ang_densities or window_size < 1:
        return []

    results: list[WindowDensity] = []

    # Build ang -> densities lookup
    density_lookup: dict[int, dict[str, float]] = {
        ad.ang: ad.densities for ad in ang_densities
    }

    all_angs = sorted(density_lookup.keys())
    if not all_angs:
        return []

    min_ang = all_angs[0]
    max_ang = all_angs[-1]

    for start in range(min_ang, max_ang - window_size + 2):
        end = start + window_size - 1

        # Collect densities from angs in this window
        window_dims: dict[str, list[float]] = {
            dim: [] for dim in FEATURE_DIMENSIONS
        }
        for ang in range(start, end + 1):
            if ang in density_lookup:
                for dim in FEATURE_DIMENSIONS:
                    window_dims[dim].append(
                        density_lookup[ang].get(dim, 0.0),
                    )

        # Compute mean for this window
        mean_densities: dict[str, float] = {}
        for dim in FEATURE_DIMENSIONS:
            mean_densities[dim] = _safe_mean(window_dims[dim])

        results.append(
            WindowDensity(
                window_start=start,
                window_end=end,
                densities=mean_densities,
            ),
        )

    return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def compute_all_density_aggregations(
    feature_records: list[dict[str, Any]],
    corpus_records: list[dict[str, Any]],
    ragas_path: Path,
    *,
    window_size: int = 20,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Compute all density aggregations: by ang, by raga, sliding window.

    Args:
        feature_records: Feature records (from features.jsonl).
        corpus_records: Corpus records (from ggs_lines.jsonl).
        ragas_path: Path to ragas.yaml configuration.
        window_size: Sliding window size in angs.
        output_path: If provided, write aggregations to JSON.

    Returns:
        Dict with keys ``"by_ang"``, ``"by_raga"``, ``"sliding_window"``.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Phase 2: Computing register density "
        f"aggregations from {len(feature_records)} lines...[/bold]\n",
    )

    # Index features by ang
    features_by_ang = _index_features_by_ang(
        feature_records, corpus_records,
    )
    _console.print(
        f"  Indexed features across {len(features_by_ang)} angs",
    )

    # Per-ang densities
    ang_densities = compute_ang_densities(features_by_ang)

    # Per-raga densities
    sections = load_raga_sections(ragas_path)
    raga_densities = compute_raga_densities(features_by_ang, sections)

    raga_with_lines = sum(
        1 for r in raga_densities if r.line_count > 0
    )
    _console.print(
        f"  {raga_with_lines}/{len(raga_densities)} raga sections "
        f"have matching lines",
    )

    # Sliding window
    window_densities = compute_sliding_window(
        ang_densities, window_size=window_size,
    )
    _console.print(
        f"  Sliding window: {len(window_densities)} positions "
        f"(window_size={window_size})",
    )

    elapsed = time.monotonic() - t0
    _console.print(f"  Completed in {elapsed:.2f}s")

    result = {
        "by_ang": ang_densities,
        "by_raga": raga_densities,
        "sliding_window": window_densities,
    }

    if output_path is not None:
        _write_output(result, output_path)

    return result


def _write_output(
    result: dict[str, Any],
    output_path: Path,
) -> None:
    """Write density aggregation results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "by_ang": [ad.to_dict() for ad in result["by_ang"]],
        "by_raga": [rd.to_dict() for rd in result["by_raga"]],
        "sliding_window": [
            wd.to_dict() for wd in result["sliding_window"]
        ],
    }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    _console.print(f"  Written to {output_path}")
