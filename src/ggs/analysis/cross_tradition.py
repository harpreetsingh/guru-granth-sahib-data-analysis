"""Cross-tradition and ritual-negation analysis (bd-9qw.6).

Applies domain-specific filters to co-occurrence results to surface
high-signal analytical patterns:

1. **Cross-tradition pairing**: Pairs where entity_a.tradition != entity_b.tradition,
   ranked by NPMI. Surfaces the GGS's characteristic juxtaposition of
   vocabulary from different devotional traditions.

2. **Ritual + negation**: Lines where ritual markers co-occur with negation
   tokens, capturing the recurring critique-of-ritual pattern.

Reference: PLAN.md Section 5.1
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.analysis.cooccurrence import CooccurrencePair
from ggs.analysis.match import MatchRecord
from ggs.lexicon.loader import LexiconIndex

_console = Console()


# ---------------------------------------------------------------------------
# Negation lexicon
# ---------------------------------------------------------------------------

# Common Gurmukhi negation tokens used in critique-of-ritual contexts
NEGATION_TOKENS: frozenset[str] = frozenset({
    "ਨਾ",
    "ਨਾਹੀ",
    "ਨਹੀ",
    "ਬਿਨੁ",
    "ਬਿਨ",
    "ਬਾਝੁ",
    "ਬਾਝ",
    "ਨਹਿ",
    "ਬਿਨਾ",
    "ਨ",
})

# Entity categories considered ritual markers
RITUAL_CATEGORIES: frozenset[str] = frozenset({
    "practice",
    "marker",
})

# Entity IDs with known ritual associations (supplement category check)
RITUAL_ENTITY_KEYWORDS: frozenset[str] = frozenset({
    "TEERATH",
    "POOJA",
    "JANEYU",
    "TILAK",
    "RITUAL",
    "HAVAN",
    "VRAT",
})


# ---------------------------------------------------------------------------
# Cross-tradition pairing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CrossTraditionPair:
    """A co-occurrence pair from different traditions.

    Attributes:
        entity_a: First entity ID.
        entity_b: Second entity ID.
        tradition_a: Tradition of entity_a.
        tradition_b: Tradition of entity_b.
        window_level: Line or shabad level.
        raw_count: Number of co-occurrences.
        pmi: Pointwise Mutual Information (may be None).
        npmi: Normalized PMI (may be None).
        jaccard: Jaccard similarity.
    """

    entity_a: str
    entity_b: str
    tradition_a: str
    tradition_b: str
    window_level: str
    raw_count: int
    pmi: float | None
    npmi: float | None
    jaccard: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "tradition_a": self.tradition_a,
            "tradition_b": self.tradition_b,
            "window_level": self.window_level,
            "raw_count": self.raw_count,
            "pmi": round(self.pmi, 6) if self.pmi is not None else None,
            "npmi": round(self.npmi, 6) if self.npmi is not None else None,
            "jaccard": round(self.jaccard, 6),
        }


def filter_cross_tradition_pairs(
    pairs: list[CooccurrencePair],
    index: LexiconIndex,
) -> list[CrossTraditionPair]:
    """Filter co-occurrence pairs to those spanning different traditions.

    Entities without a tradition assignment are excluded.
    Results are sorted by NPMI descending (None-PMI pairs go last),
    then by raw_count descending.

    Args:
        pairs: Co-occurrence pairs from the co-occurrence engine.
        index: Lexicon index for entity metadata.

    Returns:
        List of :class:`CrossTraditionPair` records.
    """
    cross_pairs: list[CrossTraditionPair] = []

    for pair in pairs:
        entity_a = index.entities.get(pair.entity_a)
        entity_b = index.entities.get(pair.entity_b)

        if entity_a is None or entity_b is None:
            continue

        tradition_a = entity_a.tradition
        tradition_b = entity_b.tradition

        if tradition_a is None or tradition_b is None:
            continue

        if tradition_a == tradition_b:
            continue

        cross_pairs.append(
            CrossTraditionPair(
                entity_a=pair.entity_a,
                entity_b=pair.entity_b,
                tradition_a=tradition_a,
                tradition_b=tradition_b,
                window_level=pair.window_level,
                raw_count=pair.raw_count,
                pmi=pair.pmi,
                npmi=pair.npmi,
                jaccard=pair.jaccard,
            ),
        )

    # Sort: NPMI descending (None last), then raw_count descending
    def _sort_key(p: CrossTraditionPair) -> tuple[int, float, int]:
        has_npmi = 0 if p.npmi is not None else 1
        npmi_val = -(p.npmi or 0.0)
        return (has_npmi, npmi_val, -p.raw_count)

    cross_pairs.sort(key=_sort_key)
    return cross_pairs


# ---------------------------------------------------------------------------
# Ritual + negation detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RitualNegationLine:
    """A line containing both ritual markers and negation tokens.

    Attributes:
        line_uid: UID of the line.
        ang: Ang number (if available).
        ritual_entities: Entity IDs of ritual markers found on the line.
        negation_tokens: Negation tokens found on the line.
        gurmukhi: The original Gurmukhi text of the line.
    """

    line_uid: str
    ang: int | None
    ritual_entities: list[str]
    negation_tokens: list[str]
    gurmukhi: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_uid": self.line_uid,
            "ang": self.ang,
            "ritual_entities": self.ritual_entities,
            "negation_tokens": self.negation_tokens,
            "gurmukhi": self.gurmukhi,
        }


def _is_ritual_entity(entity_id: str, index: LexiconIndex) -> bool:
    """Check if an entity is a ritual marker.

    Uses both category and ID-keyword heuristics.
    """
    entity = index.entities.get(entity_id)
    if entity is not None and entity.category in RITUAL_CATEGORIES:
        return True

    upper_id = entity_id.upper()
    return any(kw in upper_id for kw in RITUAL_ENTITY_KEYWORDS)


def find_ritual_negation_lines(
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    index: LexiconIndex,
) -> list[RitualNegationLine]:
    """Find lines containing both ritual markers and negation tokens.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: All match records.
        index: Lexicon index for entity metadata.

    Returns:
        List of :class:`RitualNegationLine` records.
    """
    # Index matches by line
    ritual_by_line: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.nested_in is not None:
            continue
        if _is_ritual_entity(m.entity_id, index):
            ritual_by_line[m.line_uid].add(m.entity_id)

    # Index records by line_uid
    record_by_line: dict[str, dict[str, Any]] = {
        rec.get("line_uid", ""): rec for rec in records
    }

    results: list[RitualNegationLine] = []

    for line_uid, ritual_entities in ritual_by_line.items():
        rec = record_by_line.get(line_uid, {})
        tokens = rec.get("tokens", [])
        gurmukhi = rec.get("gurmukhi", "")
        ang = rec.get("ang")

        # Find negation tokens on this line
        found_negation = [
            t for t in tokens if t in NEGATION_TOKENS
        ]

        if found_negation:
            results.append(
                RitualNegationLine(
                    line_uid=line_uid,
                    ang=ang,
                    ritual_entities=sorted(ritual_entities),
                    negation_tokens=found_negation,
                    gurmukhi=gurmukhi,
                ),
            )

    # Sort by ang number
    results.sort(key=lambda r: (r.ang or 0, r.line_uid))
    return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def compute_cross_tradition_analysis(
    cooccurrence_pairs: dict[str, list[CooccurrencePair]],
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    index: LexiconIndex,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run full cross-tradition and ritual-negation analysis.

    Args:
        cooccurrence_pairs: Output from compute_all_cooccurrence,
            with keys "line" and "shabad".
        records: Corpus record dicts.
        matches: All match records.
        index: Lexicon index for entity metadata.
        output_path: If provided, write results JSON.

    Returns:
        Dict with "cross_tradition_pairs" and "ritual_negation_lines".
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Phase 2: Cross-tradition and "
        "ritual-negation analysis...[/bold]\n",
    )

    # Cross-tradition pairs at both levels
    line_cross = filter_cross_tradition_pairs(
        cooccurrence_pairs.get("line", []), index,
    )
    shabad_cross = filter_cross_tradition_pairs(
        cooccurrence_pairs.get("shabad", []), index,
    )

    _console.print(
        f"  Cross-tradition pairs: "
        f"{len(line_cross)} line-level, "
        f"{len(shabad_cross)} shabad-level",
    )

    # Tradition-pair summary
    tradition_pair_counts: dict[str, int] = defaultdict(int)
    for ct in line_cross:
        pair_label = f"{ct.tradition_a}+{ct.tradition_b}"
        tradition_pair_counts[pair_label] += 1

    for label in sorted(tradition_pair_counts.keys()):
        _console.print(
            f"    {label}: {tradition_pair_counts[label]} pairs",
        )

    # Ritual + negation
    ritual_negation = find_ritual_negation_lines(
        records, matches, index,
    )
    _console.print(
        f"  Ritual+negation lines: {len(ritual_negation)}",
    )

    elapsed = time.monotonic() - t0
    _console.print(f"  Completed in {elapsed:.2f}s")

    result: dict[str, Any] = {
        "cross_tradition_pairs": {
            "line": [ct.to_dict() for ct in line_cross],
            "shabad": [ct.to_dict() for ct in shabad_cross],
        },
        "ritual_negation_lines": [
            rn.to_dict() for rn in ritual_negation
        ],
        "summary": {
            "cross_tradition_line_pairs": len(line_cross),
            "cross_tradition_shabad_pairs": len(shabad_cross),
            "ritual_negation_lines": len(ritual_negation),
            "tradition_pair_counts": dict(tradition_pair_counts),
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        _console.print(f"  Written to {output_path}")

    return result
