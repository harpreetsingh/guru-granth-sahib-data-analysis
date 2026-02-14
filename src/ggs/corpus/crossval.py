"""Cross-validation framework for corpus quality assurance (bd-15c.7).

Compares the primary corpus (from SriGranth) against secondary sources
to catch systematic errors. Discrepancies are WARNINGs, not errors.

Strategy (PLAN.md Section 3.1):
  1. Sample N angs from a secondary source
  2. Parse/normalize both primary and secondary text
  3. Compare line-by-line (after normalization)
  4. Classify discrepancies (whitespace-only, nukta-only, substantive)
  5. Write cross_validation.jsonl report

Secondary sources can differ legitimately in whitespace, nukta usage,
vishram markers, and minor spelling variants.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from rich.console import Console

_console = Console()


# ---------------------------------------------------------------------------
# Discrepancy classification
# ---------------------------------------------------------------------------


class DiscrepancyType(StrEnum):
    """Classification of discrepancies between sources."""

    WHITESPACE_ONLY = "whitespace_only"
    NUKTA_ONLY = "nukta_only"
    NASAL_ONLY = "nasal_only"
    VISHRAM_ONLY = "vishram_only"
    SUBSTANTIVE = "substantive"
    EXTRA_LINE = "extra_line"
    MISSING_LINE = "missing_line"


# ---------------------------------------------------------------------------
# Comparison result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineComparison:
    """Result of comparing a single line between two sources.

    Attributes:
        ang: Ang number.
        line_index: Position within the ang (0-based).
        primary_text: Normalized text from primary source.
        secondary_text: Normalized text from secondary source.
        match: Whether the texts match exactly.
        discrepancy_type: Type of discrepancy if they don't match.
    """

    ang: int
    line_index: int
    primary_text: str
    secondary_text: str
    match: bool
    discrepancy_type: DiscrepancyType | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ang": self.ang,
            "line_index": self.line_index,
            "match": self.match,
        }
        if not self.match:
            d["primary_text"] = self.primary_text
            d["secondary_text"] = self.secondary_text
            d["discrepancy_type"] = (
                str(self.discrepancy_type) if self.discrepancy_type
                else None
            )
        return d


@dataclass(slots=True)
class CrossValidationReport:
    """Aggregated cross-validation report.

    Attributes:
        source_primary: Name of the primary source.
        source_secondary: Name of the secondary source.
        angs_sampled: Number of angs compared.
        total_lines_compared: Total lines compared across all angs.
        total_matches: Lines that matched exactly.
        total_discrepancies: Lines that did not match.
        discrepancy_counts: Count per discrepancy type.
        comparisons: All individual line comparisons.
    """

    source_primary: str = "srigranth"
    source_secondary: str = "unknown"
    angs_sampled: int = 0
    total_lines_compared: int = 0
    total_matches: int = 0
    total_discrepancies: int = 0
    discrepancy_counts: dict[str, int] = field(default_factory=dict)
    comparisons: list[LineComparison] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_primary": self.source_primary,
            "source_secondary": self.source_secondary,
            "angs_sampled": self.angs_sampled,
            "total_lines_compared": self.total_lines_compared,
            "total_matches": self.total_matches,
            "total_discrepancies": self.total_discrepancies,
            "match_rate": (
                round(
                    self.total_matches / self.total_lines_compared,
                    4,
                )
                if self.total_lines_compared > 0
                else 0.0
            ),
            "discrepancy_counts": dict(self.discrepancy_counts),
            "discrepancies": [
                c.to_dict() for c in self.comparisons
                if not c.match
            ],
        }

    def write(self, path: Path) -> None:
        """Write report to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(
                self.to_dict(), fh, indent=2, ensure_ascii=False,
            )


# ---------------------------------------------------------------------------
# Discrepancy classification logic
# ---------------------------------------------------------------------------


# Nukta characters
_NUKTA_CHARS = frozenset({
    "\u0A3C",  # ਼ (nukta)
    "\u0A33",  # ਲ਼
    "\u0A36",  # ਸ਼
    "\u0A59",  # ਖ਼
    "\u0A5A",  # ਗ਼
    "\u0A5B",  # ਜ਼
    "\u0A5C",  # ੜ
    "\u0A5E",  # ਫ਼
})

# Nasal markers
_NASAL_CHARS = frozenset({"\u0A70", "\u0A02"})  # ੰ (tippi), ਂ (bindi)

# Vishram markers
_VISHRAM_CHARS = frozenset({
    "\u0964",  # ।
    "\u0965",  # ॥
    ";", ",",
})


def _strip_chars(text: str, chars: frozenset[str]) -> str:
    """Remove specified characters from text."""
    return "".join(c for c in text if c not in chars)


def classify_discrepancy(
    primary: str,
    secondary: str,
) -> DiscrepancyType:
    """Classify the type of discrepancy between two strings.

    Classification priority (most benign first):
      1. Whitespace-only: texts match after collapsing whitespace
      2. Vishram-only: texts match after stripping vishram markers
      3. Nasal-only: texts match after stripping nasal differences
      4. Nukta-only: texts match after stripping nukta characters
      5. Substantive: texts differ in content

    Args:
        primary: Normalized text from primary source.
        secondary: Normalized text from secondary source.

    Returns:
        The :class:`DiscrepancyType` that best classifies the difference.
    """
    # Whitespace-only
    if primary.split() == secondary.split():
        return DiscrepancyType.WHITESPACE_ONLY

    # Vishram-only
    p_no_vishram = _strip_chars(primary, _VISHRAM_CHARS).split()
    s_no_vishram = _strip_chars(secondary, _VISHRAM_CHARS).split()
    if p_no_vishram == s_no_vishram:
        return DiscrepancyType.VISHRAM_ONLY

    # Nasal-only
    p_no_nasal = _strip_chars(primary, _NASAL_CHARS)
    s_no_nasal = _strip_chars(secondary, _NASAL_CHARS)
    if p_no_nasal.split() == s_no_nasal.split():
        return DiscrepancyType.NASAL_ONLY

    # Nukta-only
    p_no_nukta = _strip_chars(primary, _NUKTA_CHARS)
    s_no_nukta = _strip_chars(secondary, _NUKTA_CHARS)
    if p_no_nukta.split() == s_no_nukta.split():
        return DiscrepancyType.NUKTA_ONLY

    return DiscrepancyType.SUBSTANTIVE


# ---------------------------------------------------------------------------
# Secondary source protocol
# ---------------------------------------------------------------------------


class SecondarySource(Protocol):
    """Protocol for secondary corpus sources."""

    @property
    def name(self) -> str:
        """Human-readable name of the source."""
        ...

    def fetch_ang_lines(self, ang: int) -> list[str]:
        """Fetch normalized Gurmukhi lines for a given ang.

        Returns:
            List of normalized Gurmukhi line strings.
        """
        ...


# ---------------------------------------------------------------------------
# Line comparison
# ---------------------------------------------------------------------------


def compare_ang_lines(
    ang: int,
    primary_lines: list[str],
    secondary_lines: list[str],
) -> list[LineComparison]:
    """Compare lines from two sources for a single ang.

    Uses a simple positional comparison. Lines at the same index
    are compared. Extra/missing lines at the end are noted.

    Args:
        ang: Ang number being compared.
        primary_lines: Normalized lines from primary source.
        secondary_lines: Normalized lines from secondary source.

    Returns:
        List of :class:`LineComparison` records.
    """
    comparisons: list[LineComparison] = []
    max_len = max(len(primary_lines), len(secondary_lines))

    for i in range(max_len):
        p_text = primary_lines[i] if i < len(primary_lines) else ""
        s_text = secondary_lines[i] if i < len(secondary_lines) else ""

        if i >= len(primary_lines):
            comparisons.append(
                LineComparison(
                    ang=ang,
                    line_index=i,
                    primary_text="",
                    secondary_text=s_text,
                    match=False,
                    discrepancy_type=DiscrepancyType.EXTRA_LINE,
                ),
            )
        elif i >= len(secondary_lines):
            comparisons.append(
                LineComparison(
                    ang=ang,
                    line_index=i,
                    primary_text=p_text,
                    secondary_text="",
                    match=False,
                    discrepancy_type=DiscrepancyType.MISSING_LINE,
                ),
            )
        elif p_text == s_text:
            comparisons.append(
                LineComparison(
                    ang=ang,
                    line_index=i,
                    primary_text=p_text,
                    secondary_text=s_text,
                    match=True,
                ),
            )
        else:
            disc_type = classify_discrepancy(p_text, s_text)
            comparisons.append(
                LineComparison(
                    ang=ang,
                    line_index=i,
                    primary_text=p_text,
                    secondary_text=s_text,
                    match=False,
                    discrepancy_type=disc_type,
                ),
            )

    return comparisons


# ---------------------------------------------------------------------------
# Ang sampling
# ---------------------------------------------------------------------------


def sample_angs(
    total_angs: int = 1430,
    sample_size: int = 50,
    *,
    rng: random.Random | None = None,
) -> list[int]:
    """Sample ang numbers for cross-validation.

    Uses stratified sampling to ensure coverage across the text.
    Divides the text into ``sample_size`` equal strata and samples
    one ang from each stratum.

    Args:
        total_angs: Total number of angs (default 1430).
        sample_size: Number of angs to sample.
        rng: Optional random.Random instance for reproducibility.

    Returns:
        Sorted list of sampled ang numbers.
    """
    if rng is None:
        rng = random.Random()

    if sample_size >= total_angs:
        return list(range(1, total_angs + 1))

    # Stratified sampling
    stratum_size = total_angs / sample_size
    sampled: list[int] = []

    for i in range(sample_size):
        stratum_start = int(i * stratum_size) + 1
        stratum_end = int((i + 1) * stratum_size)
        stratum_end = min(stratum_end, total_angs)
        ang = rng.randint(stratum_start, stratum_end)
        sampled.append(ang)

    return sorted(set(sampled))


# ---------------------------------------------------------------------------
# Primary corpus reader
# ---------------------------------------------------------------------------


def read_primary_ang_lines(
    corpus_records: list[dict[str, Any]],
    ang: int,
) -> list[str]:
    """Extract normalized lines for a specific ang from the primary corpus.

    Args:
        corpus_records: All corpus records (from ggs_lines.jsonl).
        ang: Ang number to extract.

    Returns:
        List of normalized gurmukhi strings for that ang.
    """
    return [
        rec.get("gurmukhi", "")
        for rec in corpus_records
        if rec.get("ang") == ang
    ]


# ---------------------------------------------------------------------------
# Main cross-validation
# ---------------------------------------------------------------------------


def run_cross_validation(
    corpus_records: list[dict[str, Any]],
    secondary_source: SecondarySource,
    *,
    sample_size: int = 50,
    total_angs: int = 1430,
    rng: random.Random | None = None,
    output_path: Path | None = None,
) -> CrossValidationReport:
    """Run cross-validation comparing primary corpus against a secondary source.

    Args:
        corpus_records: All primary corpus records.
        secondary_source: A secondary source implementing SecondarySource.
        sample_size: Number of angs to sample.
        total_angs: Total number of angs in the corpus (default 1430).
        rng: Optional Random for reproducibility.
        output_path: If provided, write the report to this path.

    Returns:
        A :class:`CrossValidationReport`.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Cross-validation: Comparing primary corpus "
        f"against {secondary_source.name}...[/bold]\n",
    )

    # Sample angs
    sampled_angs = sample_angs(
        total_angs=total_angs,
        sample_size=sample_size,
        rng=rng,
    )
    _console.print(
        f"  Sampled {len(sampled_angs)} angs for comparison",
    )

    report = CrossValidationReport(
        source_secondary=secondary_source.name,
        angs_sampled=len(sampled_angs),
    )

    for ang in sampled_angs:
        primary_lines = read_primary_ang_lines(corpus_records, ang)
        try:
            secondary_lines = secondary_source.fetch_ang_lines(ang)
        except Exception as e:
            _console.print(
                f"  [yellow]Ang {ang}: failed to fetch "
                f"from {secondary_source.name}: {e}[/yellow]",
            )
            continue

        comparisons = compare_ang_lines(
            ang, primary_lines, secondary_lines,
        )
        report.comparisons.extend(comparisons)

    # Compute summary stats
    report.total_lines_compared = len(report.comparisons)
    report.total_matches = sum(
        1 for c in report.comparisons if c.match
    )
    report.total_discrepancies = (
        report.total_lines_compared - report.total_matches
    )

    for c in report.comparisons:
        if not c.match and c.discrepancy_type is not None:
            dt = str(c.discrepancy_type)
            report.discrepancy_counts[dt] = (
                report.discrepancy_counts.get(dt, 0) + 1
            )

    elapsed = time.monotonic() - t0
    match_rate = (
        report.total_matches / report.total_lines_compared * 100
        if report.total_lines_compared > 0
        else 0.0
    )
    _console.print(
        f"  Compared {report.total_lines_compared} lines: "
        f"{report.total_matches} matches, "
        f"{report.total_discrepancies} discrepancies "
        f"({match_rate:.1f}% match rate)",
    )
    _console.print(f"  Completed in {elapsed:.2f}s")

    if output_path is not None:
        report.write(output_path)
        _console.print(f"  Written to {output_path}")

    return report
