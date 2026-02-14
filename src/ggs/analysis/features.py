"""Per-line feature computation (bd-9qw.1).

Computes continuous density scores for each line, capturing the register
profile: perso_arabic_density, sanskritic_density, nirgun_density,
sagun_narrative_density, ritual_density, cleric_density.

Each feature is a ratio: count_of_register_matches / total_tokens.
This enables gradient analysis, not just presence/absence.

Reference: PLAN.md Section 5
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.analysis.match import MatchRecord
from ggs.lexicon.loader import LexiconIndex

_console = Console()

# ---------------------------------------------------------------------------
# Feature dimensions
# ---------------------------------------------------------------------------

# Map entity category/register to feature dimensions
# Each dimension aggregates matches by a specific criterion

FEATURE_DIMENSIONS = [
    "perso_arabic",
    "sanskritic",
    "nirgun",
    "sagun_narrative",
    "ritual",
    "cleric",
]


# ---------------------------------------------------------------------------
# Feature record
# ---------------------------------------------------------------------------


def _empty_feature() -> dict[str, Any]:
    """Create an empty feature dict."""
    return {
        "count": 0,
        "density": 0.0,
        "matched_tokens": [],
    }


def _compute_density(count: int, token_count: int) -> float:
    """Compute density ratio, avoiding division by zero."""
    if token_count == 0:
        return 0.0
    return round(count / token_count, 6)


# ---------------------------------------------------------------------------
# Entity -> feature dimension mapping
# ---------------------------------------------------------------------------


def _classify_entity(
    entity_id: str,
    index: LexiconIndex,
) -> list[str]:
    """Classify an entity into feature dimensions.

    An entity can contribute to multiple feature dimensions based on
    its register and category metadata.

    Returns list of feature dimension names.
    """
    entity = index.entities.get(entity_id)
    if entity is None:
        return []

    dimensions: list[str] = []

    # Register-based dimensions
    if entity.register == "perso_arabic":
        dimensions.append("perso_arabic")
    elif entity.register == "sanskritic":
        dimensions.append("sanskritic")

    # Category-based dimensions
    if entity.category == "narrative":
        dimensions.append("sagun_narrative")
    elif entity.category == "practice":
        dimensions.append("ritual")
    elif (
        entity.category == "marker"
        and entity.tradition in ("islamic", "vedantic", "yogic")
    ):
        # Markers from religious traditions contribute to cleric
        dimensions.append("cleric")

    # Nirgun: formless divine names and nirgun concepts
    if (
        entity.category == "divine_name"
        and entity.tradition in ("sikh", "universal")
        and entity.register in ("neutral", "sanskritic")
    ):
        dimensions.append("nirgun")

    # Concept entities from nirgun.yaml typically have
    # tradition=sikh or yogic
    if entity.category == "concept" and entity.tradition in (
        "sikh", "yogic",
    ):
        dimensions.append("nirgun")

    return dimensions


# ---------------------------------------------------------------------------
# Per-line feature computation
# ---------------------------------------------------------------------------


def compute_line_features(
    line_uid: str,
    shabad_uid: str | None,
    token_count: int,
    matches: list[MatchRecord],
    index: LexiconIndex,
) -> dict[str, Any]:
    """Compute feature vector for a single line.

    Args:
        line_uid: UID of the line.
        shabad_uid: UID of the containing shabad.
        token_count: Number of tokens in the line.
        matches: Match records for this line.
        index: Lexicon index for entity metadata lookup.

    Returns:
        Feature record dict.
    """
    features: dict[str, dict[str, Any]] = {
        dim: _empty_feature() for dim in FEATURE_DIMENSIONS
    }

    for match in matches:
        # Skip nested matches to avoid double-counting
        if match.nested_in is not None:
            continue

        dims = _classify_entity(match.entity_id, index)
        for dim in dims:
            if dim in features:
                features[dim]["count"] += 1
                features[dim]["matched_tokens"].append(
                    match.matched_form,
                )

    # Compute densities
    for dim in FEATURE_DIMENSIONS:
        features[dim]["density"] = _compute_density(
            features[dim]["count"], token_count,
        )

    return {
        "line_uid": line_uid,
        "shabad_uid": shabad_uid,
        "token_count": token_count,
        "features": features,
    }


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def compute_corpus_features(
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    index: LexiconIndex,
    *,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Compute features for all corpus records.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: All match records (from matches.jsonl).
        index: Lexicon index.
        output_path: If provided, write features.jsonl.

    Returns:
        List of feature record dicts.
    """
    _console.print(
        f"\n[bold]Phase 2: Computing features for "
        f"{len(records)} lines...[/bold]\n"
    )

    # Group matches by line_uid
    matches_by_line: dict[str, list[MatchRecord]] = (
        defaultdict(list)
    )
    for m in matches:
        matches_by_line[m.line_uid].append(m)

    # Compute features
    feature_records: list[dict[str, Any]] = []

    for rec in records:
        line_uid = rec.get("line_uid", "UNKNOWN")
        shabad_uid = rec.get("meta", {}).get("shabad_uid")
        token_count = len(rec.get("tokens", []))
        line_matches = matches_by_line.get(line_uid, [])

        feat = compute_line_features(
            line_uid=line_uid,
            shabad_uid=shabad_uid,
            token_count=token_count,
            matches=line_matches,
            index=index,
        )
        feature_records.append(feat)

    # Summary
    total_with_features = sum(
        1 for f in feature_records
        if any(
            f["features"][d]["count"] > 0
            for d in FEATURE_DIMENSIONS
        )
    )
    _console.print(
        f"  {total_with_features}/{len(feature_records)} "
        f"lines have at least one feature"
    )

    # Write output
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            for feat in feature_records:
                fh.write(
                    json.dumps(feat, ensure_ascii=False)
                    + "\n"
                )
        _console.print(f"  Written to {output_path}")

    return feature_records
