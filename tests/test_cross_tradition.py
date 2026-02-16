"""Cross-tradition and ritual-negation analysis tests (bd-9qw.6).

Tests cross-tradition pair filtering, ritual+negation detection,
sorting behavior, and end-to-end analysis.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ggs.analysis.cooccurrence import CooccurrencePair
from ggs.analysis.cross_tradition import (
    NEGATION_TOKENS,
    CrossTraditionPair,
    RitualNegationLine,
    _is_ritual_entity,
    compute_cross_tradition_analysis,
    filter_cross_tradition_pairs,
    find_ritual_negation_lines,
)
from ggs.analysis.match import MatchRecord
from ggs.lexicon.loader import Entity, LexiconIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_entity(
    entity_id: str,
    tradition: str | None = None,
    category: str = "divine_name",
) -> Entity:
    """Create a minimal entity for testing."""
    return Entity(
        id=entity_id,
        canonical_form=entity_id.lower(),
        aliases=(),
        category=category,
        tradition=tradition,
    )


@pytest.fixture()
def test_index() -> LexiconIndex:
    """A lexicon index with entities from different traditions."""
    return LexiconIndex(
        entities={
            "ALLAH": _make_entity("ALLAH", "islamic"),
            "KHUDA": _make_entity("KHUDA", "islamic"),
            "RAM": _make_entity("RAM", "vaishnava"),
            "KRISHNA": _make_entity("KRISHNA", "vaishnava"),
            "BRAHM": _make_entity("BRAHM", "vedantic"),
            "WAHEGURU": _make_entity("WAHEGURU", "sikh"),
            "TEERATH": _make_entity(
                "TEERATH", "vedantic", category="practice",
            ),
            "NAAM": _make_entity("NAAM", "sikh", category="concept"),
            "NO_TRADITION": _make_entity("NO_TRADITION", None),
        },
        alias_to_entities={},
        file_hashes={},
    )


@pytest.fixture()
def sample_cooccurrence_pairs() -> list[CooccurrencePair]:
    """Co-occurrence pairs including cross-tradition ones."""
    return [
        # Cross-tradition: islamic + vaishnava
        CooccurrencePair(
            entity_a="ALLAH",
            entity_b="RAM",
            window_level="line",
            raw_count=10,
            pmi=2.5,
            npmi=0.8,
            jaccard=0.3,
        ),
        # Same tradition: islamic + islamic
        CooccurrencePair(
            entity_a="ALLAH",
            entity_b="KHUDA",
            window_level="line",
            raw_count=15,
            pmi=3.0,
            npmi=0.9,
            jaccard=0.5,
        ),
        # Cross-tradition: islamic + vedantic
        CooccurrencePair(
            entity_a="BRAHM",
            entity_b="KHUDA",
            window_level="line",
            raw_count=5,
            pmi=1.5,
            npmi=0.6,
            jaccard=0.2,
        ),
        # Cross-tradition with None PMI
        CooccurrencePair(
            entity_a="KRISHNA",
            entity_b="WAHEGURU",
            window_level="line",
            raw_count=3,
            pmi=None,
            npmi=None,
            jaccard=0.1,
        ),
        # Entity without tradition
        CooccurrencePair(
            entity_a="NO_TRADITION",
            entity_b="RAM",
            window_level="line",
            raw_count=8,
            pmi=2.0,
            npmi=0.7,
            jaccard=0.25,
        ),
    ]


# ---------------------------------------------------------------------------
# Cross-tradition pairing tests
# ---------------------------------------------------------------------------


class TestFilterCrossTraditionPairs:
    """Tests for filter_cross_tradition_pairs."""

    def test_filters_cross_tradition(
        self,
        sample_cooccurrence_pairs: list[CooccurrencePair],
        test_index: LexiconIndex,
    ) -> None:
        result = filter_cross_tradition_pairs(
            sample_cooccurrence_pairs, test_index,
        )
        # Should include ALLAH+RAM, BRAHM+KHUDA, KRISHNA+WAHEGURU
        # Should exclude ALLAH+KHUDA (same tradition), NO_TRADITION+RAM
        assert len(result) == 3

    def test_excludes_same_tradition(
        self,
        test_index: LexiconIndex,
    ) -> None:
        pairs = [
            CooccurrencePair(
                entity_a="ALLAH",
                entity_b="KHUDA",
                window_level="line",
                raw_count=10,
                pmi=2.0,
                npmi=0.8,
                jaccard=0.4,
            ),
        ]
        result = filter_cross_tradition_pairs(pairs, test_index)
        assert len(result) == 0

    def test_excludes_no_tradition(
        self,
        test_index: LexiconIndex,
    ) -> None:
        pairs = [
            CooccurrencePair(
                entity_a="NO_TRADITION",
                entity_b="RAM",
                window_level="line",
                raw_count=5,
                pmi=1.0,
                npmi=0.5,
                jaccard=0.2,
            ),
        ]
        result = filter_cross_tradition_pairs(pairs, test_index)
        assert len(result) == 0

    def test_excludes_unknown_entities(
        self,
        test_index: LexiconIndex,
    ) -> None:
        pairs = [
            CooccurrencePair(
                entity_a="UNKNOWN_X",
                entity_b="RAM",
                window_level="line",
                raw_count=5,
                pmi=1.0,
                npmi=0.5,
                jaccard=0.2,
            ),
        ]
        result = filter_cross_tradition_pairs(pairs, test_index)
        assert len(result) == 0

    def test_sorted_by_npmi_descending(
        self,
        sample_cooccurrence_pairs: list[CooccurrencePair],
        test_index: LexiconIndex,
    ) -> None:
        result = filter_cross_tradition_pairs(
            sample_cooccurrence_pairs, test_index,
        )
        # Pairs with NPMI should come first, sorted by NPMI desc
        npmi_pairs = [p for p in result if p.npmi is not None]
        for i in range(len(npmi_pairs) - 1):
            a_npmi = npmi_pairs[i].npmi
            b_npmi = npmi_pairs[i + 1].npmi
            assert a_npmi is not None and b_npmi is not None
            assert a_npmi >= b_npmi

    def test_none_pmi_pairs_sorted_last(
        self,
        sample_cooccurrence_pairs: list[CooccurrencePair],
        test_index: LexiconIndex,
    ) -> None:
        result = filter_cross_tradition_pairs(
            sample_cooccurrence_pairs, test_index,
        )
        # Last pair should be the one with None PMI
        assert result[-1].pmi is None

    def test_tradition_fields_set(
        self,
        test_index: LexiconIndex,
    ) -> None:
        pairs = [
            CooccurrencePair(
                entity_a="ALLAH",
                entity_b="RAM",
                window_level="line",
                raw_count=5,
                pmi=1.0,
                npmi=0.5,
                jaccard=0.2,
            ),
        ]
        result = filter_cross_tradition_pairs(pairs, test_index)
        assert result[0].tradition_a == "islamic"
        assert result[0].tradition_b == "vaishnava"

    def test_empty_pairs(
        self,
        test_index: LexiconIndex,
    ) -> None:
        result = filter_cross_tradition_pairs([], test_index)
        assert result == []


# ---------------------------------------------------------------------------
# CrossTraditionPair serialization tests
# ---------------------------------------------------------------------------


class TestCrossTraditionPairSerialization:
    """Tests for CrossTraditionPair.to_dict."""

    def test_to_dict(self) -> None:
        ct = CrossTraditionPair(
            entity_a="ALLAH",
            entity_b="RAM",
            tradition_a="islamic",
            tradition_b="vaishnava",
            window_level="line",
            raw_count=10,
            pmi=2.5,
            npmi=0.8,
            jaccard=0.3,
        )
        d = ct.to_dict()
        assert d["entity_a"] == "ALLAH"
        assert d["tradition_a"] == "islamic"
        assert d["tradition_b"] == "vaishnava"
        assert d["pmi"] == 2.5

    def test_to_dict_with_none_pmi(self) -> None:
        ct = CrossTraditionPair(
            entity_a="A",
            entity_b="B",
            tradition_a="t1",
            tradition_b="t2",
            window_level="line",
            raw_count=2,
            pmi=None,
            npmi=None,
            jaccard=0.1,
        )
        d = ct.to_dict()
        assert d["pmi"] is None
        assert d["npmi"] is None


# ---------------------------------------------------------------------------
# Ritual entity detection tests
# ---------------------------------------------------------------------------


class TestIsRitualEntity:
    """Tests for _is_ritual_entity."""

    def test_practice_category(self, test_index: LexiconIndex) -> None:
        assert _is_ritual_entity("TEERATH", test_index)

    def test_non_ritual_category(self, test_index: LexiconIndex) -> None:
        assert not _is_ritual_entity("ALLAH", test_index)

    def test_keyword_match(self, test_index: LexiconIndex) -> None:
        # TEERATH also matches by keyword
        assert _is_ritual_entity("TEERATH", test_index)

    def test_unknown_entity_with_ritual_keyword(
        self, test_index: LexiconIndex,
    ) -> None:
        # Entity not in index but has RITUAL in ID
        assert _is_ritual_entity("RITUAL_MARKERS", test_index)

    def test_unknown_non_ritual_entity(
        self, test_index: LexiconIndex,
    ) -> None:
        assert not _is_ritual_entity("UNKNOWN_THING", test_index)


# ---------------------------------------------------------------------------
# Ritual + negation line detection tests
# ---------------------------------------------------------------------------


class TestFindRitualNegationLines:
    """Tests for find_ritual_negation_lines."""

    def test_finds_ritual_negation(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਤੀਰਥਿ ਨਾਵਣ ਜਾਉ ਨਾ",
                "tokens": ["ਤੀਰਥਿ", "ਨਾਵਣ", "ਜਾਉ", "ਨਾ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[0, 6],
            ),
        ]
        result = find_ritual_negation_lines(
            records, matches, test_index,
        )
        assert len(result) == 1
        assert result[0].line_uid == "line:1"
        assert "TEERATH" in result[0].ritual_entities
        assert "ਨਾ" in result[0].negation_tokens

    def test_no_negation_token(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਤੀਰਥਿ ਨਾਵਣ ਜਾਉ",
                "tokens": ["ਤੀਰਥਿ", "ਨਾਵਣ", "ਜਾਉ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[0, 6],
            ),
        ]
        result = find_ritual_negation_lines(
            records, matches, test_index,
        )
        assert len(result) == 0

    def test_no_ritual_entity(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਅਲਾਹੁ ਨਾ",
                "tokens": ["ਅਲਾਹੁ", "ਨਾ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="ALLAH",
                matched_form="ਅਲਾਹੁ",
                span=[0, 5],
            ),
        ]
        result = find_ritual_negation_lines(
            records, matches, test_index,
        )
        assert len(result) == 0

    def test_excludes_nested_matches(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਤੀਰਥਿ ਨਾ",
                "tokens": ["ਤੀਰਥਿ", "ਨਾ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[0, 6],
                nested_in="PARENT",
            ),
        ]
        result = find_ritual_negation_lines(
            records, matches, test_index,
        )
        assert len(result) == 0

    def test_sorted_by_ang(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:2",
                "ang": 50,
                "gurmukhi": "ਤੀਰਥਿ ਬਿਨੁ",
                "tokens": ["ਤੀਰਥਿ", "ਬਿਨੁ"],
            },
            {
                "line_uid": "line:1",
                "ang": 10,
                "gurmukhi": "ਤੀਰਥ ਨਾ",
                "tokens": ["ਤੀਰਥ", "ਨਾ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:2",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[0, 6],
            ),
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥ",
                span=[0, 5],
            ),
        ]
        result = find_ritual_negation_lines(
            records, matches, test_index,
        )
        assert len(result) == 2
        assert result[0].ang == 10
        assert result[1].ang == 50

    def test_empty_inputs(
        self, test_index: LexiconIndex,
    ) -> None:
        result = find_ritual_negation_lines([], [], test_index)
        assert result == []


# ---------------------------------------------------------------------------
# RitualNegationLine serialization tests
# ---------------------------------------------------------------------------


class TestRitualNegationLineSerialization:
    """Tests for RitualNegationLine.to_dict."""

    def test_to_dict(self) -> None:
        rn = RitualNegationLine(
            line_uid="line:1",
            ang=42,
            ritual_entities=["TEERATH"],
            negation_tokens=["ਨਾ"],
            gurmukhi="ਤੀਰਥਿ ਨਾ",
        )
        d = rn.to_dict()
        assert d["line_uid"] == "line:1"
        assert d["ang"] == 42
        assert "TEERATH" in d["ritual_entities"]


# ---------------------------------------------------------------------------
# Negation tokens constant tests
# ---------------------------------------------------------------------------


class TestNegationTokens:
    """Tests for NEGATION_TOKENS constant."""

    def test_contains_known_negation(self) -> None:
        assert "ਨਾ" in NEGATION_TOKENS
        assert "ਨਾਹੀ" in NEGATION_TOKENS
        assert "ਬਿਨੁ" in NEGATION_TOKENS

    def test_does_not_contain_non_negation(self) -> None:
        assert "ਹਰਿ" not in NEGATION_TOKENS


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestComputeCrossTraditionAnalysis:
    """Tests for compute_cross_tradition_analysis."""

    def test_end_to_end(
        self,
        sample_cooccurrence_pairs: list[CooccurrencePair],
        test_index: LexiconIndex,
        tmp_path: Path,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਤੀਰਥਿ ਨਾ",
                "tokens": ["ਤੀਰਥਿ", "ਨਾ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[0, 6],
            ),
        ]
        cooccurrence = {
            "line": sample_cooccurrence_pairs,
            "shabad": [],
        }
        output_path = tmp_path / "cross_tradition.json"

        result = compute_cross_tradition_analysis(
            cooccurrence, records, matches, test_index,
            output_path=output_path,
        )

        assert "cross_tradition_pairs" in result
        assert "ritual_negation_lines" in result
        assert "summary" in result
        assert result["summary"]["ritual_negation_lines"] == 1
        assert result["summary"]["cross_tradition_line_pairs"] == 3

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "cross_tradition_pairs" in data

    def test_empty_inputs(
        self,
        test_index: LexiconIndex,
    ) -> None:
        result = compute_cross_tradition_analysis(
            {"line": [], "shabad": []},
            [], [], test_index,
        )
        assert result["summary"]["cross_tradition_line_pairs"] == 0
        assert result["summary"]["ritual_negation_lines"] == 0
