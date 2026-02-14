"""Co-occurrence engine — line-level and shabad-level pair analysis (bd-9qw.2).

Computes entity pair co-occurrence at two window levels:
  - LINE: Two entities appearing on the same line (tightest association).
  - SHABAD: Two entities appearing in the same shabad/hymn (thematic association).

For each window, collects unique entity IDs, generates sorted pairs (A < B),
and computes metrics: raw_count, PMI, normalized PMI, and Jaccard similarity.

Only pairs with raw_count >= min_count are retained (sparse output).

Stability measures (bd-9qw.3):
  1. Minimum entity frequency: exclude rare entities from co-occurrence.
  2. Laplace smoothing: add-k smoothing prevents extreme PMI for rare pairs.
  3. Minimum PMI support: pairs below threshold get pmi=None (insufficient evidence).

Reference: PLAN.md Section 5.1
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.analysis.match import MatchRecord

_console = Console()


# ---------------------------------------------------------------------------
# Window level
# ---------------------------------------------------------------------------


class WindowLevel(StrEnum):
    """Co-occurrence window granularity."""

    LINE = "line"
    SHABAD = "shabad"


# ---------------------------------------------------------------------------
# Co-occurrence pair record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CooccurrencePair:
    """A co-occurrence pair with association metrics.

    Attributes:
        entity_a: First entity ID (alphabetically smaller).
        entity_b: Second entity ID (alphabetically larger).
        window_level: The window level at which this pair co-occurs.
        raw_count: Number of windows containing both entities.
        pmi: Pointwise Mutual Information: log2(P(A,B) / (P(A) * P(B))).
             None if raw_count < min_pmi_support (insufficient evidence).
        npmi: Normalized PMI: pmi / -log2(P(A,B)), bounded [-1, 1].
              None if raw_count < min_pmi_support (insufficient evidence).
        jaccard: Jaccard similarity: |both| / |either|.
    """

    entity_a: str
    entity_b: str
    window_level: str
    raw_count: int
    pmi: float | None
    npmi: float | None
    jaccard: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "window_level": self.window_level,
            "raw_count": self.raw_count,
            "pmi": round(self.pmi, 6) if self.pmi is not None else None,
            "npmi": round(self.npmi, 6) if self.npmi is not None else None,
            "jaccard": round(self.jaccard, 6),
        }


# ---------------------------------------------------------------------------
# Window grouping
# ---------------------------------------------------------------------------


def _group_matches_by_line(
    matches: list[MatchRecord],
) -> dict[str, set[str]]:
    """Group entity IDs by line_uid.

    Skips nested matches to avoid inflating co-occurrence counts.

    Returns:
        Mapping from line_uid to set of entity_ids found in that line.
    """
    groups: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.nested_in is not None:
            continue
        groups[m.line_uid].add(m.entity_id)
    return dict(groups)


def _group_matches_by_shabad(
    matches: list[MatchRecord],
    line_to_shabad: dict[str, str],
) -> dict[str, set[str]]:
    """Group entity IDs by shabad_uid.

    Skips nested matches and lines without shabad assignment.

    Args:
        matches: All match records.
        line_to_shabad: Mapping from line_uid to shabad_uid.

    Returns:
        Mapping from shabad_uid to set of entity_ids found in that shabad.
    """
    groups: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.nested_in is not None:
            continue
        shabad_uid = line_to_shabad.get(m.line_uid)
        if shabad_uid is not None:
            groups[shabad_uid].add(m.entity_id)
    return dict(groups)


def build_line_to_shabad_map(
    records: list[dict[str, Any]],
) -> dict[str, str]:
    """Build a mapping from line_uid to shabad_uid from corpus records.

    Uses the ``meta.shabad_uid`` field if present. Falls back to grouping
    lines by ang number (``ang`` field) as a coarse shabad proxy when
    shabad boundaries are not yet annotated.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).

    Returns:
        Mapping from line_uid to shabad_uid.
    """
    line_to_shabad: dict[str, str] = {}

    for rec in records:
        line_uid = rec.get("line_uid", "UNKNOWN")
        shabad_uid = rec.get("meta", {}).get("shabad_uid")
        if shabad_uid is not None:
            line_to_shabad[line_uid] = shabad_uid
        else:
            # Fallback: use ang number as a coarse shabad grouping
            ang = rec.get("ang")
            if ang is not None:
                line_to_shabad[line_uid] = f"ang:{ang}"

    return line_to_shabad


# ---------------------------------------------------------------------------
# Pair counting
# ---------------------------------------------------------------------------


def _count_pairs(
    windows: dict[str, set[str]],
) -> dict[tuple[str, str], int]:
    """Count co-occurring entity pairs across windows.

    For each window, generates all sorted pairs (A < B) from the unique
    entity set and increments the pair counter.

    Returns:
        Mapping from (entity_a, entity_b) to raw co-occurrence count.
    """
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)

    for entities in windows.values():
        if len(entities) < 2:
            continue
        for a, b in combinations(sorted(entities), 2):
            pair_counts[(a, b)] += 1

    return dict(pair_counts)


def _count_entity_occurrences(
    windows: dict[str, set[str]],
) -> dict[str, int]:
    """Count how many windows each entity appears in.

    Returns:
        Mapping from entity_id to window count.
    """
    counts: dict[str, int] = defaultdict(int)
    for entities in windows.values():
        for eid in entities:
            counts[eid] += 1
    return dict(counts)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def _compute_pmi(
    p_ab: float,
    p_a: float,
    p_b: float,
) -> float:
    """Compute Pointwise Mutual Information.

    PMI = log2(P(A,B) / (P(A) * P(B)))

    Returns 0.0 if any probability is zero (undefined case).
    """
    if p_ab <= 0.0 or p_a <= 0.0 or p_b <= 0.0:
        return 0.0
    return math.log2(p_ab / (p_a * p_b))


def _compute_smoothed_pmi(
    count_ab: int,
    count_a: int,
    count_b: int,
    total_windows: int,
    num_unique_entities: int,
    smoothing_k: float,
) -> float:
    """Compute Laplace-smoothed Pointwise Mutual Information.

    Formula::

        smoothed_pmi = log2(
            (count(A,B) + k) * N_eff
            / ((count(A) + k*V) * (count(B) + k*V))
        )

    Where:
        - k is the smoothing constant (default 1)
        - V is the number of unique entities
        - N_eff = total_windows + k * V * V (adjusted total)

    Smoothing prevents log(0) and dampens extreme values for rare pairs.

    Returns 0.0 if computation would be undefined.
    """
    v = num_unique_entities
    n_eff = total_windows + smoothing_k * v * v

    numerator = (count_ab + smoothing_k) * n_eff
    denominator = (count_a + smoothing_k * v) * (count_b + smoothing_k * v)

    if denominator <= 0 or numerator <= 0:
        return 0.0

    return math.log2(numerator / denominator)


def _compute_npmi(
    pmi: float,
    p_ab: float,
) -> float:
    """Compute Normalized PMI, bounded [-1, 1].

    NPMI = PMI / -log2(P(A,B))

    Returns 0.0 if P(A,B) is zero or 1.0 (degenerate cases).
    """
    if p_ab <= 0.0 or p_ab >= 1.0:
        return 0.0
    denominator = -math.log2(p_ab)
    if denominator == 0.0:
        return 0.0
    return pmi / denominator


def _compute_jaccard(
    count_both: int,
    count_a: int,
    count_b: int,
) -> float:
    """Compute Jaccard similarity.

    J(A,B) = |windows with both| / |windows with either|
           = count_both / (count_a + count_b - count_both)

    Returns 0.0 if denominator is zero.
    """
    denom = count_a + count_b - count_both
    if denom <= 0:
        return 0.0
    return count_both / denom


# ---------------------------------------------------------------------------
# Entity frequency filtering
# ---------------------------------------------------------------------------


def _filter_by_entity_freq(
    windows: dict[str, set[str]],
    min_entity_freq: int,
) -> dict[str, set[str]]:
    """Remove rare entities from windows based on minimum frequency.

    Entities appearing in fewer than ``min_entity_freq`` windows are
    stripped from all windows. Windows left empty after filtering are
    dropped entirely.

    Args:
        windows: Mapping from window_id to set of entity_ids.
        min_entity_freq: Minimum number of windows an entity must appear in.

    Returns:
        Filtered copy of windows with rare entities removed.
    """
    if min_entity_freq <= 1:
        return windows

    # Count entity frequencies across all windows
    entity_counts = _count_entity_occurrences(windows)
    frequent = {
        eid for eid, count in entity_counts.items()
        if count >= min_entity_freq
    }

    # Filter windows
    filtered: dict[str, set[str]] = {}
    for wid, entities in windows.items():
        kept = entities & frequent
        if kept:
            filtered[wid] = kept

    return filtered


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


def compute_cooccurrence(
    windows: dict[str, set[str]],
    window_level: WindowLevel,
    *,
    min_count: int = 2,
    min_entity_freq: int = 1,
    smoothing_k: float = 0.0,
    min_pmi_support: int = 0,
) -> list[CooccurrencePair]:
    """Compute co-occurrence pairs and metrics for a set of windows.

    Stability measures (bd-9qw.3):
      - ``min_entity_freq``: Exclude entities appearing in fewer windows.
      - ``smoothing_k``: Laplace smoothing for PMI (0 = no smoothing).
      - ``min_pmi_support``: Pairs below this threshold get pmi/npmi=None.

    Args:
        windows: Mapping from window_id to set of entity_ids.
        window_level: LINE or SHABAD.
        min_count: Minimum raw_count to include a pair. Default 2.
        min_entity_freq: Minimum window count for an entity to be included.
        smoothing_k: Laplace smoothing constant (0 = unsmoothed).
        min_pmi_support: Minimum raw_count for PMI computation. Pairs with
            raw_count < min_pmi_support get pmi=None, npmi=None.

    Returns:
        List of :class:`CooccurrencePair` records, sorted by raw_count
        descending, then by entity_a/entity_b alphabetically.
    """
    # Apply entity frequency filter
    filtered_windows = _filter_by_entity_freq(windows, min_entity_freq)

    total_windows = len(filtered_windows)
    if total_windows == 0:
        return []

    # Count pairs and individual entity occurrences
    pair_counts = _count_pairs(filtered_windows)
    entity_counts = _count_entity_occurrences(filtered_windows)
    num_unique_entities = len(entity_counts)

    # Build pair records with metrics
    pairs: list[CooccurrencePair] = []

    for (entity_a, entity_b), raw_count in pair_counts.items():
        if raw_count < min_count:
            continue

        count_a = entity_counts.get(entity_a, 0)
        count_b = entity_counts.get(entity_b, 0)

        jaccard = _compute_jaccard(raw_count, count_a, count_b)

        # PMI computation: depends on min_pmi_support and smoothing
        pmi: float | None
        npmi: float | None

        if min_pmi_support > 0 and raw_count < min_pmi_support:
            # Insufficient evidence — suppress PMI
            pmi = None
            npmi = None
        elif smoothing_k > 0:
            # Smoothed PMI
            pmi = _compute_smoothed_pmi(
                raw_count, count_a, count_b,
                total_windows, num_unique_entities, smoothing_k,
            )
            # NPMI normalization with smoothed joint probability
            v = num_unique_entities
            n_eff = total_windows + smoothing_k * v * v
            p_ab_smoothed = (raw_count + smoothing_k) / n_eff
            npmi = _compute_npmi(pmi, p_ab_smoothed)
        else:
            # Unsmoothed PMI
            p_ab = raw_count / total_windows
            p_a = count_a / total_windows
            p_b = count_b / total_windows
            pmi = _compute_pmi(p_ab, p_a, p_b)
            npmi = _compute_npmi(pmi, p_ab)

        pairs.append(
            CooccurrencePair(
                entity_a=entity_a,
                entity_b=entity_b,
                window_level=str(window_level),
                raw_count=raw_count,
                pmi=pmi,
                npmi=npmi,
                jaccard=jaccard,
            ),
        )

    # Sort: highest raw_count first, then alphabetically
    pairs.sort(
        key=lambda p: (-p.raw_count, p.entity_a, p.entity_b),
    )

    return pairs


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def compute_all_cooccurrence(
    matches: list[MatchRecord],
    records: list[dict[str, Any]],
    *,
    min_count: int = 2,
    min_entity_freq: int = 1,
    smoothing_k: float = 0.0,
    min_pmi_support: int = 0,
    output_path: Path | None = None,
) -> dict[str, list[CooccurrencePair]]:
    """Compute co-occurrence at both line and shabad levels.

    Args:
        matches: All match records from the matching engine.
        records: Corpus record dicts (from ggs_lines.jsonl).
        min_count: Minimum raw_count threshold for pair inclusion.
        min_entity_freq: Minimum window count for an entity to be included.
        smoothing_k: Laplace smoothing constant (0 = unsmoothed).
        min_pmi_support: Minimum raw_count for PMI computation.
        output_path: If provided, write cooccurrence.json.

    Returns:
        Dict with keys ``"line"`` and ``"shabad"``, each containing
        a list of :class:`CooccurrencePair` records.
    """
    t0 = time.monotonic()

    stability_desc = []
    if min_entity_freq > 1:
        stability_desc.append(f"min_entity_freq={min_entity_freq}")
    if smoothing_k > 0:
        stability_desc.append(f"smoothing_k={smoothing_k}")
    if min_pmi_support > 0:
        stability_desc.append(f"min_pmi_support={min_pmi_support}")
    stability_str = (
        f" ({', '.join(stability_desc)})" if stability_desc else ""
    )

    _console.print(
        "\n[bold]Phase 2: Computing co-occurrence "
        f"from {len(matches)} matches "
        f"across {len(records)} lines{stability_str}...[/bold]\n",
    )

    cooccurrence_kwargs = {
        "min_count": min_count,
        "min_entity_freq": min_entity_freq,
        "smoothing_k": smoothing_k,
        "min_pmi_support": min_pmi_support,
    }

    # Line-level co-occurrence
    line_windows = _group_matches_by_line(matches)
    line_pairs = compute_cooccurrence(
        line_windows, WindowLevel.LINE, **cooccurrence_kwargs,
    )
    _console.print(
        f"  Line-level: {len(line_pairs)} pairs "
        f"(from {len(line_windows)} windows with matches)",
    )

    # Shabad-level co-occurrence
    line_to_shabad = build_line_to_shabad_map(records)
    shabad_windows = _group_matches_by_shabad(matches, line_to_shabad)
    shabad_pairs = compute_cooccurrence(
        shabad_windows, WindowLevel.SHABAD, **cooccurrence_kwargs,
    )
    _console.print(
        f"  Shabad-level: {len(shabad_pairs)} pairs "
        f"(from {len(shabad_windows)} windows with matches)",
    )

    elapsed = time.monotonic() - t0
    _console.print(
        f"  Completed in {elapsed:.2f}s",
    )

    result = {
        "line": line_pairs,
        "shabad": shabad_pairs,
    }

    # Write output
    if output_path is not None:
        _write_output(result, output_path)

    return result


def _write_output(
    result: dict[str, list[CooccurrencePair]],
    output_path: Path,
) -> None:
    """Write co-occurrence results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output: dict[str, Any] = {}
    for level, pairs in result.items():
        output[level] = {
            "pair_count": len(pairs),
            "pairs": [p.to_dict() for p in pairs],
        }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    _console.print(f"  Written to {output_path}")
