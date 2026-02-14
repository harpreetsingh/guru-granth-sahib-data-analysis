"""Match engine tests (bd-3jj.5).

Verifies Aho-Corasick matching: must-match, must-not-match, span accuracy,
overlap resolution, confidence levels, and boundary enforcement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ggs.analysis.match import (
    Confidence,
    MatchingEngine,
    MatchRecord,
)
from ggs.lexicon.loader import LexiconIndex, load_lexicon

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def lexicon_index() -> LexiconIndex:
    """Load the full lexicon for matching tests."""
    paths = {
        "entities": "lexicon/entities.yaml",
        "nirgun": "lexicon/nirgun.yaml",
        "sagun_narrative": "lexicon/sagun_narrative.yaml",
        "perso_arabic": "lexicon/perso_arabic.yaml",
        "sanskritic": "lexicon/sanskritic.yaml",
    }
    return load_lexicon(paths, base_dir=Path("."))


@pytest.fixture()
def engine(lexicon_index: LexiconIndex) -> MatchingEngine:
    """Build matching engine from full lexicon."""
    return MatchingEngine.from_lexicon(lexicon_index)


@pytest.fixture()
def test_engine() -> MatchingEngine:
    """Build matching engine from test fixtures lexicon."""
    paths = {
        "test": "tests/fixtures/lexicon/test_entities.yaml",
    }
    index = load_lexicon(paths, base_dir=Path("."))
    return MatchingEngine.from_lexicon(index)


# ---------------------------------------------------------------------------
# Must-match fixtures
# ---------------------------------------------------------------------------


class TestMustMatch:
    """Known strings that MUST produce specific matches."""

    def test_must_match_hari(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line("ਹਰਿ ਜਪ", "uid1")
        entity_ids = {m.entity_id for m in matches}
        assert "HARI" in entity_ids

    def test_must_match_naam(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line("ਨਾਮੁ ਜਪ", "uid2")
        entity_ids = {m.entity_id for m in matches}
        assert "NAAM" in entity_ids

    def test_must_match_allah(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line("ਅਲਾਹੁ ਅਲਖ", "uid3")
        entity_ids = {m.entity_id for m in matches}
        assert "ALLAH" in entity_ids
        assert "ALAKH" in entity_ids

    def test_must_match_waheguru(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line(
            "ਵਾਹਿਗੁਰੂ ਸਤਿ", "uid4",
        )
        entity_ids = {m.entity_id for m in matches}
        assert "WAHEGURU" in entity_ids

    def test_must_match_nirankar(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line(
            "ਨਿਰੰਕਾਰੁ ਅਕਾਲ", "uid5",
        )
        entity_ids = {m.entity_id for m in matches}
        assert "NIRANKAR" in entity_ids
        assert "AKAL" in entity_ids

    def test_must_match_krishna_murari(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line(
            "ਮੁਰਾਰਿ ਕੇਸਵ", "uid6",
        )
        entity_ids = {m.entity_id for m in matches}
        assert "KRISHNA" in entity_ids

    def test_must_match_multiple_forms(
        self, engine: MatchingEngine,
    ) -> None:
        """ਹਰਿ and ਹਰੀ both match HARI."""
        m1 = engine.match_line("ਹਰਿ ਜਪ", "uid7")
        m2 = engine.match_line("ਹਰੀ ਜਪ", "uid8")
        assert any(m.entity_id == "HARI" for m in m1)
        assert any(m.entity_id == "HARI" for m in m2)


# ---------------------------------------------------------------------------
# Must-not-match fixtures (false positive guards)
# ---------------------------------------------------------------------------


class TestMustNotMatch:
    """Strings that must NOT produce certain matches."""

    def test_must_not_match_substring(
        self, engine: MatchingEngine,
    ) -> None:
        """ਹਰਿਆ (green) must not match ਹਰਿ (Hari)."""
        matches = engine.match_line("ਹਰਿਆ ਵੇਖ", "uid20")
        entity_ids = {m.entity_id for m in matches}
        assert "HARI" not in entity_ids

    def test_must_not_match_prefix_substring(
        self, engine: MatchingEngine,
    ) -> None:
        """ਨਾਮੁ inside ਸਨਾਮੁ should not match."""
        matches = engine.match_line("ਸਨਾਮੁ", "uid21")
        entity_ids = {m.entity_id for m in matches}
        assert "NAAM" not in entity_ids

    def test_empty_line_no_matches(
        self, engine: MatchingEngine,
    ) -> None:
        matches = engine.match_line("", "uid22")
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# Span accuracy
# ---------------------------------------------------------------------------


class TestSpanAccuracy:
    """Match spans are correct character offsets."""

    def test_span_correct_naam(
        self, engine: MatchingEngine,
    ) -> None:
        """Match for ਨਾਮੁ in 'ਸਤਿ ਨਾਮੁ ਕਰਤਾ'."""
        matches = engine.match_line(
            "ਸਤਿ ਨਾਮੁ ਕਰਤਾ", "uid30",
        )
        naam_matches = [
            m for m in matches if m.entity_id == "NAAM"
        ]
        assert len(naam_matches) >= 1
        m = naam_matches[0]
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        assert text[m.span[0]:m.span[1]] == "ਨਾਮੁ"

    def test_span_correct_hari(
        self, engine: MatchingEngine,
    ) -> None:
        """Match for ਹਰਿ in 'ਜਪ ਹਰਿ ਨਾਮੁ'."""
        text = "ਜਪ ਹਰਿ ਨਾਮੁ"
        matches = engine.match_line(text, "uid31")
        hari_matches = [
            m for m in matches if m.entity_id == "HARI"
        ]
        assert len(hari_matches) >= 1
        m = hari_matches[0]
        assert text[m.span[0]:m.span[1]] == "ਹਰਿ"

    def test_all_spans_extract_correctly(
        self, engine: MatchingEngine,
    ) -> None:
        """All span offsets extract to the matched_form."""
        text = (
            "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ "
            "ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ "
            "ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ"
        )
        matches = engine.match_line(text, "uid32")
        for m in matches:
            extracted = text[m.span[0]:m.span[1]]
            assert extracted == m.matched_form, (
                f"{m.entity_id}: span {m.span} extracts "
                f"{extracted!r}, expected {m.matched_form!r}"
            )


# ---------------------------------------------------------------------------
# Overlap resolution
# ---------------------------------------------------------------------------


class TestOverlapResolution:
    """Overlapping matches are resolved correctly."""

    def test_nested_matches_both_kept(
        self, engine: MatchingEngine,
    ) -> None:
        """SATNAM containing NAAM — both kept, NAAM has nested_in."""
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        matches = engine.match_line(text, "uid40")

        satnam = [
            m for m in matches if m.entity_id == "SATNAM"
        ]
        naam = [
            m for m in matches if m.entity_id == "NAAM"
        ]

        assert len(satnam) >= 1, "SATNAM should match"
        assert len(naam) >= 1, "NAAM should match (nested)"
        assert naam[0].nested_in == "SATNAM"

    def test_nested_match_has_nested_in_field(
        self, engine: MatchingEngine,
    ) -> None:
        """The nested match's nested_in field is not None."""
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        matches = engine.match_line(text, "uid41")
        nested = [m for m in matches if m.nested_in is not None]
        assert len(nested) >= 1

    def test_non_overlapping_independent(
        self, engine: MatchingEngine,
    ) -> None:
        """Non-overlapping matches are all independent."""
        text = "ਹਰਿ ਅਲਾਹੁ"
        matches = engine.match_line(text, "uid42")
        assert all(m.nested_in is None for m in matches)


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class TestConfidence:
    """Confidence scoring is correct."""

    def test_unambiguous_high_confidence(
        self, engine: MatchingEngine,
    ) -> None:
        """ਅਲਾਹੁ (unique to ALLAH) has HIGH confidence."""
        matches = engine.match_line("ਅਲਾਹੁ ਜਪ", "uid50")
        allah = [
            m for m in matches if m.entity_id == "ALLAH"
        ]
        assert len(allah) >= 1
        assert allah[0].confidence == Confidence.HIGH

    def test_unambiguous_no_ambiguity(
        self, engine: MatchingEngine,
    ) -> None:
        """HIGH confidence matches have no ambiguity record."""
        matches = engine.match_line("ਵਾਹਿਗੁਰੂ ਜਪ", "uid51")
        waheguru = [
            m for m in matches
            if m.entity_id == "WAHEGURU"
        ]
        assert len(waheguru) >= 1
        assert waheguru[0].ambiguity is None


# ---------------------------------------------------------------------------
# Boundary enforcement
# ---------------------------------------------------------------------------


class TestBoundaryEnforcement:
    """Word boundary rules are enforced."""

    def test_left_boundary_space(
        self, engine: MatchingEngine,
    ) -> None:
        """Match at start of line is valid."""
        matches = engine.match_line("ਹਰਿ ਜਪ", "uid60")
        assert any(m.entity_id == "HARI" for m in matches)

    def test_right_boundary_end(
        self, engine: MatchingEngine,
    ) -> None:
        """Match at end of line is valid."""
        matches = engine.match_line("ਜਪ ਹਰਿ", "uid61")
        assert any(m.entity_id == "HARI" for m in matches)

    def test_both_boundaries_space(
        self, engine: MatchingEngine,
    ) -> None:
        """Match surrounded by spaces is valid."""
        matches = engine.match_line(
            "ਜਪ ਹਰਿ ਨਾਮੁ", "uid62",
        )
        assert any(m.entity_id == "HARI" for m in matches)

    def test_no_match_mid_word(
        self, engine: MatchingEngine,
    ) -> None:
        """No match if entity appears mid-word."""
        # ਨਾਮ embedded in a longer word
        matches = engine.match_line("ਗੁਨਾਮ", "uid63")
        naam_matches = [
            m for m in matches if m.entity_id == "NAAM"
        ]
        assert len(naam_matches) == 0


# ---------------------------------------------------------------------------
# Engine construction
# ---------------------------------------------------------------------------


class TestEngineConstruction:
    """Engine builds correctly from lexicon."""

    def test_pattern_count(
        self, engine: MatchingEngine,
    ) -> None:
        """Engine has patterns loaded."""
        assert engine.pattern_count > 0

    def test_entity_count(
        self, engine: MatchingEngine,
    ) -> None:
        """Engine knows entity count."""
        assert engine.entity_count > 0

    def test_from_test_lexicon(
        self, test_engine: MatchingEngine,
    ) -> None:
        """Engine builds from test fixtures lexicon."""
        assert test_engine.entity_count == 5


# ---------------------------------------------------------------------------
# MatchRecord serialization
# ---------------------------------------------------------------------------


class TestMatchRecordSerialization:
    """MatchRecord.to_dict() produces correct output."""

    def test_to_dict_fields(self) -> None:
        rec = MatchRecord(
            line_uid="test_uid",
            entity_id="HARI",
            matched_form="ਹਰਿ",
            span=[0, 3],
        )
        d = rec.to_dict()
        assert d["line_uid"] == "test_uid"
        assert d["entity_id"] == "HARI"
        assert d["matched_form"] == "ਹਰਿ"
        assert d["span"] == [0, 3]
        assert d["rule_id"] == "alias_exact"
        assert d["confidence"] == "HIGH"
        assert d["ambiguity"] is None
        assert d["nested_in"] is None

    def test_to_dict_with_nested(self) -> None:
        rec = MatchRecord(
            line_uid="test_uid",
            entity_id="NAAM",
            matched_form="ਨਾਮੁ",
            span=[5, 9],
            nested_in="SATNAM",
        )
        d = rec.to_dict()
        assert d["nested_in"] == "SATNAM"

    def test_to_dict_with_ambiguity(self) -> None:
        rec = MatchRecord(
            line_uid="test_uid",
            entity_id="RAM",
            matched_form="ਰਾਮ",
            span=[0, 3],
            confidence=Confidence.MEDIUM,
            ambiguity={
                "alternative_entities": [
                    "RAM",
                    "RAMCHANDRA",
                ],
                "disambiguation_rule": None,
            },
        )
        d = rec.to_dict()
        assert d["confidence"] == "MEDIUM"
        assert d["ambiguity"] is not None
        assert "RAM" in d["ambiguity"]["alternative_entities"]


# ---------------------------------------------------------------------------
# Corpus-level matching
# ---------------------------------------------------------------------------


class TestCorpusMatching:
    """match_corpus() processes multiple records."""

    def test_corpus_matching(
        self, engine: MatchingEngine,
    ) -> None:
        records = [
            {
                "gurmukhi": "ਹਰਿ ਨਾਮੁ ਜਪ",
                "line_uid": "uid70",
            },
            {
                "gurmukhi": "ਅਲਾਹੁ ਅਲਖ",
                "line_uid": "uid71",
            },
        ]
        matches = engine.match_corpus(records)
        assert len(matches) > 0

        # Check that matches come from both lines
        line_uids = {m.line_uid for m in matches}
        assert "uid70" in line_uids
        assert "uid71" in line_uids
