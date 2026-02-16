"""Aho-Corasick multi-pattern matching engine (bd-4i2.5).

Scans every line of the corpus against all lexicon entries simultaneously
using Aho-Corasick automaton-based multi-pattern matching.

Algorithm:
  1. Build trie from all alias surface forms in the lexicon
  2. Compile failure links to create an automaton
  3. Scan each line's ``gurmukhi`` field, following the automaton
  4. Post-filter: boundary enforcement (word boundaries only)
  5. Resolve overlapping matches (nested vs. crossing)
  6. Emit match records with spans, confidence, and ambiguity

Time complexity: O(text_length + number_of_matches) per line,
regardless of pattern count.

Reference: PLAN.md Section 4.3
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import ahocorasick  # ty: ignore[unresolved-import]
from rich.console import Console

from ggs.lexicon.loader import LexiconIndex

_console = Console()

# ---------------------------------------------------------------------------
# Match confidence
# ---------------------------------------------------------------------------


class Confidence(StrEnum):
    """Match confidence levels (PLAN.md Section 4.3)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Match record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MatchRecord:
    """A single entity match within a corpus line.

    Attributes:
        line_uid: UID of the line where the match was found.
        entity_id: Lexicon entity that matched.
        matched_form: The actual surface form that matched.
        span: ``[start, end]`` character offsets into ``gurmukhi``.
        rule_id: The matching rule that produced this match.
        confidence: Match confidence level.
        ambiguity: Ambiguity record if confidence < HIGH.
        nested_in: Entity ID of the containing match, or None.
    """

    line_uid: str
    entity_id: str
    matched_form: str
    span: list[int]
    rule_id: str = "alias_exact"
    confidence: str = Confidence.HIGH
    ambiguity: dict[str, Any] | None = None
    nested_in: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d: dict[str, Any] = {
            "line_uid": self.line_uid,
            "entity_id": self.entity_id,
            "matched_form": self.matched_form,
            "span": list(self.span),
            "rule_id": self.rule_id,
            "confidence": self.confidence,
        }
        if self.ambiguity is not None:
            d["ambiguity"] = self.ambiguity
        else:
            d["ambiguity"] = None
        if self.nested_in is not None:
            d["nested_in"] = self.nested_in
        else:
            d["nested_in"] = None
        return d


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------


@dataclass
class MatchingEngine:
    """Aho-Corasick-based multi-pattern matching engine.

    Usage::

        engine = MatchingEngine.from_lexicon(lexicon_index)
        matches = engine.match_line("ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ", line_uid="...")
        all_matches = engine.match_corpus(records)
    """

    _automaton: ahocorasick.Automaton = field(
        repr=False,
    )
    _pattern_info: dict[str, list[str]] = field(
        default_factory=dict,
    )
    _polysemous: set[str] = field(default_factory=set)
    pattern_count: int = 0
    entity_count: int = 0

    @classmethod
    def from_lexicon(cls, index: LexiconIndex) -> MatchingEngine:
        """Build the automaton from a :class:`LexiconIndex`.

        Each alias surface form becomes a pattern in the automaton.
        The automaton maps each pattern to the list of entity_ids
        that share that surface form (handles polysemy).
        """
        automaton = ahocorasick.Automaton()
        pattern_info: dict[str, list[str]] = {}
        polysemous: set[str] = set()
        pattern_count = 0

        for form, entity_ids in index.alias_to_entities.items():
            if not form:
                continue
            pattern_info[form] = entity_ids
            automaton.add_word(form, form)
            pattern_count += 1

            # Track polysemous forms
            if len(entity_ids) > 1:
                polysemous.update(entity_ids)

        automaton.make_automaton()

        return cls(
            _automaton=automaton,
            _pattern_info=pattern_info,
            _polysemous=polysemous,
            pattern_count=pattern_count,
            entity_count=index.entity_count,
        )

    def match_line(
        self,
        gurmukhi: str,
        line_uid: str,
    ) -> list[MatchRecord]:
        """Match all patterns against a single line.

        Args:
            gurmukhi: Normalized Gurmukhi text.
            line_uid: UID of the line.

        Returns:
            List of :class:`MatchRecord` instances, after
            boundary enforcement and overlap resolution.
        """
        if not gurmukhi:
            return []

        # Phase 1: Raw Aho-Corasick scan
        raw_matches = self._scan(gurmukhi)

        # Phase 2: Boundary enforcement
        boundary_matches = self._enforce_boundaries(
            raw_matches, gurmukhi,
        )

        # Phase 3: Build MatchRecords with confidence
        records = self._build_records(
            boundary_matches, line_uid,
        )

        # Phase 4: Resolve overlaps
        resolved = self._resolve_overlaps(records)

        return resolved

    def match_corpus(
        self,
        records: list[dict[str, Any]],
    ) -> list[MatchRecord]:
        """Match all patterns against all corpus records.

        Args:
            records: List of canonical record dicts
                (each must have ``gurmukhi`` and ``line_uid``).

        Returns:
            All matches across all lines.
        """
        all_matches: list[MatchRecord] = []

        for rec in records:
            gurmukhi = rec.get("gurmukhi", "")
            line_uid = rec.get("line_uid", "UNKNOWN")
            matches = self.match_line(gurmukhi, line_uid)
            all_matches.extend(matches)

        return all_matches

    # -- Internal methods ---------------------------------------------------

    def _scan(
        self, text: str,
    ) -> list[tuple[str, int, int]]:
        """Raw Aho-Corasick scan.

        Returns list of ``(matched_form, start, end)`` tuples.
        Note: pyahocorasick returns ``(end_index, value)``
        where end_index is the index of the LAST character.
        """
        results: list[tuple[str, int, int]] = []

        for end_idx, form in self._automaton.iter(text):
            start = end_idx - len(form) + 1
            end = end_idx + 1
            results.append((form, start, end))

        return results

    def _enforce_boundaries(
        self,
        raw_matches: list[tuple[str, int, int]],
        text: str,
    ) -> list[tuple[str, int, int]]:
        """Filter matches that don't fall on word boundaries.

        A match is on a word boundary if:
          - Start is at position 0 OR preceded by whitespace
          - End is at len(text) OR followed by whitespace
        """
        filtered: list[tuple[str, int, int]] = []

        for form, start, end in raw_matches:
            # Check left boundary
            if start > 0 and not text[start - 1].isspace():
                continue

            # Check right boundary
            if end < len(text) and not text[end].isspace():
                continue

            filtered.append((form, start, end))

        return filtered

    def _build_records(
        self,
        matches: list[tuple[str, int, int]],
        line_uid: str,
    ) -> list[MatchRecord]:
        """Build MatchRecord instances with confidence scoring."""
        records: list[MatchRecord] = []

        for form, start, end in matches:
            entity_ids = self._pattern_info.get(form, [])

            for eid in entity_ids:
                # Determine confidence
                if len(entity_ids) > 1:
                    confidence = Confidence.MEDIUM
                    ambiguity = {
                        "alternative_entities": entity_ids,
                        "disambiguation_rule": None,
                    }
                elif eid in self._polysemous:
                    confidence = Confidence.MEDIUM
                    ambiguity = {
                        "alternative_entities": [eid],
                        "disambiguation_rule": None,
                    }
                else:
                    confidence = Confidence.HIGH
                    ambiguity = None

                records.append(
                    MatchRecord(
                        line_uid=line_uid,
                        entity_id=eid,
                        matched_form=form,
                        span=[start, end],
                        confidence=confidence,
                        ambiguity=ambiguity,
                    ),
                )

        return records

    def _resolve_overlaps(
        self,
        records: list[MatchRecord],
    ) -> list[MatchRecord]:
        """Resolve overlapping matches (PLAN.md Section 4.3).

        Rules:
          1. Nested (one contains other): keep BOTH,
             mark shorter as nested_in the longer.
          2. Crossing overlap: keep the LONGER match.
          3. Equal-length: keep both.
        """
        if len(records) <= 1:
            return records

        # Sort by start position, then by span length (longer first)
        sorted_records = sorted(
            records,
            key=lambda r: (r.span[0], -(r.span[1] - r.span[0])),
        )

        resolved: list[MatchRecord] = []
        for rec in sorted_records:
            is_crossing = False
            containing_entity: str | None = None

            for existing in resolved:
                e_start, e_end = existing.span
                r_start, r_end = rec.span

                # Check for overlap
                if r_start < e_end and r_end > e_start:
                    # Overlapping
                    if (
                        e_start <= r_start
                        and e_end >= r_end
                    ):
                        # rec is nested within existing
                        containing_entity = existing.entity_id
                    elif (
                        r_start <= e_start
                        and r_end >= e_end
                    ):
                        # existing is nested within rec
                        # (handled when existing was added)
                        pass
                    else:
                        # Crossing overlap
                        rec_len = r_end - r_start
                        existing_len = e_end - e_start
                        if rec_len <= existing_len:
                            # Discard shorter (rec)
                            is_crossing = True
                            break

            if is_crossing:
                continue

            if containing_entity is not None:
                # Mark as nested
                rec = MatchRecord(
                    line_uid=rec.line_uid,
                    entity_id=rec.entity_id,
                    matched_form=rec.matched_form,
                    span=rec.span,
                    rule_id=rec.rule_id,
                    confidence=rec.confidence,
                    ambiguity=rec.ambiguity,
                    nested_in=containing_entity,
                )

            resolved.append(rec)

        return resolved


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def run_matching(
    records: list[dict[str, Any]],
    lexicon_index: LexiconIndex,
    *,
    output_path: Path | None = None,
) -> list[MatchRecord]:
    """Run matching engine on corpus records and optionally write output.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        lexicon_index: Compiled lexicon index.
        output_path: If provided, write matches to this JSONL file.

    Returns:
        All match records.
    """
    t0 = time.monotonic()

    _console.print(
        f"\n[bold]Phase 1: Matching {len(records)} lines "
        f"against {lexicon_index.entity_count} entities "
        f"({lexicon_index.alias_count} aliases)...[/bold]\n"
    )

    # Build engine
    engine = MatchingEngine.from_lexicon(lexicon_index)

    _console.print(
        f"  Automaton built: {engine.pattern_count} patterns"
    )

    # Match
    all_matches = engine.match_corpus(records)

    elapsed = time.monotonic() - t0
    _console.print(
        f"  Found {len(all_matches)} matches in "
        f"{elapsed:.2f}s"
    )

    # Write output
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            for m in all_matches:
                fh.write(
                    json.dumps(
                        m.to_dict(), ensure_ascii=False,
                    )
                    + "\n"
                )
        _console.print(
            f"  Written to {output_path}"
        )

    return all_matches
