"""Phase 1 aggregate reports and CSV generation (bd-4i2.7).

Produces human-readable CSV reports and webapp-ready JSON aggregations
from match results:

  - entity_counts.csv: Total count per entity across entire corpus
  - entity_counts_by_ang_bucket.csv: Count per entity x ang range
  - entity_counts_by_raga.csv: Count per entity x raga section
  - aggregates.json: Pre-computed JSON for the webapp dashboard

All counts include normalized metrics (per 1,000 lines, per 10,000 tokens).

Reference: PLAN.md Section 4.4
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.analysis.density import RagaSection, ang_to_raga, load_raga_sections
from ggs.analysis.match import MatchRecord
from ggs.lexicon.loader import LexiconIndex

_console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ang bucket size for grouping
ANG_BUCKET_SIZE = 100


# ---------------------------------------------------------------------------
# Data indexing
# ---------------------------------------------------------------------------


def _build_line_ang_map(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    """Build line_uid -> ang mapping from corpus records."""
    return {
        rec.get("line_uid", ""): rec.get("ang", 0)
        for rec in records
        if rec.get("ang") is not None
    }


def _build_line_token_counts(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    """Build line_uid -> token_count mapping from corpus records."""
    return {
        rec.get("line_uid", ""): len(rec.get("tokens", []))
        for rec in records
    }


def _ang_bucket(ang: int) -> str:
    """Convert an ang number to a bucket label like '1-100', '101-200'."""
    bucket_start = ((ang - 1) // ANG_BUCKET_SIZE) * ANG_BUCKET_SIZE + 1
    bucket_end = bucket_start + ANG_BUCKET_SIZE - 1
    return f"{bucket_start}-{bucket_end}"


# ---------------------------------------------------------------------------
# Entity count aggregation
# ---------------------------------------------------------------------------


def count_entities(
    matches: list[MatchRecord],
) -> dict[str, int]:
    """Count total occurrences per entity (excluding nested matches).

    Returns:
        Mapping from entity_id to total count.
    """
    counts: dict[str, int] = defaultdict(int)
    for m in matches:
        if m.nested_in is not None:
            continue
        counts[m.entity_id] += 1
    return dict(counts)


def count_entities_by_ang_bucket(
    matches: list[MatchRecord],
    line_to_ang: dict[str, int],
) -> dict[str, dict[str, int]]:
    """Count entity occurrences per ang bucket.

    Returns:
        Mapping from entity_id to {bucket_label: count}.
    """
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )
    for m in matches:
        if m.nested_in is not None:
            continue
        ang = line_to_ang.get(m.line_uid)
        if ang is not None:
            bucket = _ang_bucket(ang)
            counts[m.entity_id][bucket] += 1
    return {k: dict(v) for k, v in counts.items()}


def count_entities_by_raga(
    matches: list[MatchRecord],
    line_to_ang: dict[str, int],
    sections: list[RagaSection],
) -> dict[str, dict[str, int]]:
    """Count entity occurrences per raga section.

    Returns:
        Mapping from entity_id to {raga_id: count}.
    """
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )
    for m in matches:
        if m.nested_in is not None:
            continue
        ang = line_to_ang.get(m.line_uid)
        if ang is not None:
            raga_id = ang_to_raga(ang, sections)
            if raga_id is not None:
                counts[m.entity_id][raga_id] += 1
    return {k: dict(v) for k, v in counts.items()}


def count_unique_lines(
    matches: list[MatchRecord],
) -> dict[str, int]:
    """Count unique lines per entity.

    Returns:
        Mapping from entity_id to count of distinct line_uids.
    """
    lines_by_entity: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.nested_in is not None:
            continue
        lines_by_entity[m.entity_id].add(m.line_uid)
    return {k: len(v) for k, v in lines_by_entity.items()}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _normalize_per_k_lines(
    count: int,
    total_lines: int,
    k: int = 1000,
) -> float:
    """Normalize count per K lines."""
    if total_lines == 0:
        return 0.0
    return round(count / total_lines * k, 4)


def _normalize_per_k_tokens(
    count: int,
    total_tokens: int,
    k: int = 10000,
) -> float:
    """Normalize count per K tokens."""
    if total_tokens == 0:
        return 0.0
    return round(count / total_tokens * k, 4)


# ---------------------------------------------------------------------------
# CSV generation
# ---------------------------------------------------------------------------


def generate_entity_counts_csv(
    entity_counts: dict[str, int],
    unique_lines: dict[str, int],
    total_lines: int,
    total_tokens: int,
    index: LexiconIndex,
) -> str:
    """Generate entity_counts.csv content.

    Columns: entity_id, canonical_form, category, tradition, register,
             count, unique_lines, per_1000_lines, per_10000_tokens
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "entity_id", "canonical_form", "category", "tradition",
        "register", "count", "unique_lines",
        "per_1000_lines", "per_10000_tokens",
    ])

    for eid in sorted(
        entity_counts.keys(),
        key=lambda e: -entity_counts[e],
    ):
        entity = index.entities.get(eid)
        writer.writerow([
            eid,
            entity.canonical_form if entity else "",
            entity.category if entity else "",
            entity.tradition or "" if entity else "",
            entity.register or "" if entity else "",
            entity_counts[eid],
            unique_lines.get(eid, 0),
            _normalize_per_k_lines(
                entity_counts[eid], total_lines,
            ),
            _normalize_per_k_tokens(
                entity_counts[eid], total_tokens,
            ),
        ])

    return output.getvalue()


def generate_entity_counts_by_bucket_csv(
    counts_by_bucket: dict[str, dict[str, int]],
) -> str:
    """Generate entity_counts_by_ang_bucket.csv content.

    Columns: entity_id, bucket, count
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["entity_id", "ang_bucket", "count"])

    for eid in sorted(counts_by_bucket.keys()):
        for bucket in sorted(counts_by_bucket[eid].keys()):
            writer.writerow([
                eid, bucket, counts_by_bucket[eid][bucket],
            ])

    return output.getvalue()


def generate_entity_counts_by_raga_csv(
    counts_by_raga: dict[str, dict[str, int]],
) -> str:
    """Generate entity_counts_by_raga.csv content.

    Columns: entity_id, raga_id, count
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["entity_id", "raga_id", "count"])

    for eid in sorted(counts_by_raga.keys()):
        for raga_id in sorted(counts_by_raga[eid].keys()):
            writer.writerow([
                eid, raga_id, counts_by_raga[eid][raga_id],
            ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Web aggregates JSON
# ---------------------------------------------------------------------------


def generate_aggregates_json(
    entity_counts: dict[str, int],
    unique_lines: dict[str, int],
    counts_by_bucket: dict[str, dict[str, int]],
    counts_by_raga: dict[str, dict[str, int]],
    total_lines: int,
    total_tokens: int,
    index: LexiconIndex,
) -> dict[str, Any]:
    """Generate webapp-ready aggregates.json content.

    Returns a dict suitable for JSON serialization.
    """
    # Top entities by frequency
    sorted_entities = sorted(
        entity_counts.keys(),
        key=lambda e: -entity_counts[e],
    )
    top_entities = []
    for eid in sorted_entities[:50]:
        entity = index.entities.get(eid)
        top_entities.append({
            "entity_id": eid,
            "canonical_form": (
                entity.canonical_form if entity else ""
            ),
            "count": entity_counts[eid],
            "unique_lines": unique_lines.get(eid, 0),
            "per_1000_lines": _normalize_per_k_lines(
                entity_counts[eid], total_lines,
            ),
        })

    # Entity distribution by raga
    raga_distribution: dict[str, dict[str, int]] = {}
    for eid, raga_counts in counts_by_raga.items():
        for raga_id, count in raga_counts.items():
            if raga_id not in raga_distribution:
                raga_distribution[raga_id] = {}
            raga_distribution[raga_id][eid] = count

    # Summary
    return {
        "summary": {
            "total_entities_matched": len(entity_counts),
            "total_match_count": sum(entity_counts.values()),
            "total_lines": total_lines,
            "total_tokens": total_tokens,
        },
        "top_entities": top_entities,
        "entity_distribution_by_raga": raga_distribution,
        "entity_distribution_by_ang_bucket": {
            eid: buckets
            for eid, buckets in sorted(counts_by_bucket.items())
        },
    }


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def generate_phase1_reports(
    matches: list[MatchRecord],
    records: list[dict[str, Any]],
    index: LexiconIndex,
    ragas_path: Path,
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate all Phase 1 reports and aggregates.

    Args:
        matches: All match records.
        records: Corpus records (from ggs_lines.jsonl).
        index: Lexicon index for entity metadata.
        ragas_path: Path to ragas.yaml.
        output_dir: If provided, write CSV files and aggregates.json.

    Returns:
        The aggregates dict.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Phase 1 Reports: Generating from "
        f"{len(matches)} matches...[/bold]\n",
    )

    # Build indexes
    line_to_ang = _build_line_ang_map(records)
    line_token_counts = _build_line_token_counts(records)
    total_lines = len(records)
    total_tokens = sum(line_token_counts.values())

    # Count entities
    entity_counts = count_entities(matches)
    unique_line_counts = count_unique_lines(matches)

    _console.print(
        f"  {len(entity_counts)} unique entities matched",
    )
    _console.print(
        f"  {sum(entity_counts.values())} total matches "
        f"across {total_lines} lines ({total_tokens} tokens)",
    )

    # By ang bucket
    counts_by_bucket = count_entities_by_ang_bucket(
        matches, line_to_ang,
    )

    # By raga
    sections = load_raga_sections(ragas_path)
    counts_by_raga = count_entities_by_raga(
        matches, line_to_ang, sections,
    )

    # Generate aggregates
    aggregates = generate_aggregates_json(
        entity_counts, unique_line_counts,
        counts_by_bucket, counts_by_raga,
        total_lines, total_tokens, index,
    )

    # Write outputs
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV reports
        csv_path = output_dir / "entity_counts.csv"
        csv_path.write_text(
            generate_entity_counts_csv(
                entity_counts, unique_line_counts,
                total_lines, total_tokens, index,
            ),
            encoding="utf-8",
        )
        _console.print(f"  Written {csv_path}")

        bucket_csv = output_dir / "entity_counts_by_ang_bucket.csv"
        bucket_csv.write_text(
            generate_entity_counts_by_bucket_csv(counts_by_bucket),
            encoding="utf-8",
        )
        _console.print(f"  Written {bucket_csv}")

        raga_csv = output_dir / "entity_counts_by_raga.csv"
        raga_csv.write_text(
            generate_entity_counts_by_raga_csv(counts_by_raga),
            encoding="utf-8",
        )
        _console.print(f"  Written {raga_csv}")

        # JSON aggregates
        agg_path = output_dir / "aggregates.json"
        with agg_path.open("w", encoding="utf-8") as fh:
            json.dump(aggregates, fh, ensure_ascii=False, indent=2)
        _console.print(f"  Written {agg_path}")

    elapsed = time.monotonic() - t0
    _console.print(f"  Completed in {elapsed:.2f}s")

    return aggregates
