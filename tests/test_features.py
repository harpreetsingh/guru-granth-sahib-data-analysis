"""Feature computation tests (bd-3jj.6).

Verifies per-line feature density computation: zero matches, known density,
density bounds, density formula, matched tokens, all registers computed,
token_count propagation, shabad_uid propagation, and corpus-level batch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ggs.analysis.features import (
    FEATURE_DIMENSIONS,
    _classify_entity,
    _compute_density,
    _empty_feature,
    compute_corpus_features,
    compute_line_features,
)
from ggs.analysis.match import MatchingEngine, MatchRecord
from ggs.lexicon.loader import LexiconIndex, load_lexicon

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_index() -> LexiconIndex:
    """Load the test fixture lexicon."""
    paths = {
        "test": "tests/fixtures/lexicon/test_entities.yaml",
    }
    return load_lexicon(paths, base_dir=Path("."))


@pytest.fixture()
def full_index() -> LexiconIndex:
    """Load the full lexicon for richer tests."""
    paths = {
        "entities": "lexicon/entities.yaml",
        "nirgun": "lexicon/nirgun.yaml",
        "sagun_narrative": "lexicon/sagun_narrative.yaml",
        "perso_arabic": "lexicon/perso_arabic.yaml",
        "sanskritic": "lexicon/sanskritic.yaml",
    }
    return load_lexicon(paths, base_dir=Path("."))


@pytest.fixture()
def test_engine(test_index: LexiconIndex) -> MatchingEngine:
    """Build matching engine from test lexicon."""
    return MatchingEngine.from_lexicon(test_index)


# ---------------------------------------------------------------------------
# Empty feature tests
# ---------------------------------------------------------------------------


class TestEmptyFeature:
    """Tests for _empty_feature helper."""

    def test_empty_feature_structure(self) -> None:
        f = _empty_feature()
        assert f["count"] == 0
        assert f["density"] == 0.0
        assert f["matched_tokens"] == []


# ---------------------------------------------------------------------------
# Density computation tests
# ---------------------------------------------------------------------------


class TestComputeDensity:
    """Tests for _compute_density."""

    def test_zero_tokens_zero_density(self) -> None:
        assert _compute_density(0, 0) == 0.0

    def test_zero_count(self) -> None:
        assert _compute_density(0, 10) == 0.0

    def test_known_density(self) -> None:
        # 3 / 18 = 0.166667
        density = _compute_density(3, 18)
        assert abs(density - 0.166667) < 1e-5

    def test_full_density(self) -> None:
        density = _compute_density(5, 5)
        assert abs(density - 1.0) < 1e-10

    def test_rounding(self) -> None:
        density = _compute_density(1, 3)
        # Should be rounded to 6 decimal places
        assert density == round(1 / 3, 6)


# ---------------------------------------------------------------------------
# Entity classification tests
# ---------------------------------------------------------------------------


class TestClassifyEntity:
    """Tests for _classify_entity."""

    def test_sanskritic_register(
        self, test_index: LexiconIndex,
    ) -> None:
        # TEERATH is sanskritic register
        dims = _classify_entity("TEERATH", test_index)
        assert "sanskritic" in dims

    def test_ritual_category(
        self, test_index: LexiconIndex,
    ) -> None:
        # TEERATH is practice category
        dims = _classify_entity("TEERATH", test_index)
        assert "ritual" in dims

    def test_nirgun_sikh_concept(
        self, test_index: LexiconIndex,
    ) -> None:
        # SATNAM is concept + sikh tradition
        dims = _classify_entity("SATNAM", test_index)
        assert "nirgun" in dims

    def test_unknown_entity(
        self, test_index: LexiconIndex,
    ) -> None:
        dims = _classify_entity("NONEXISTENT", test_index)
        assert dims == []


# ---------------------------------------------------------------------------
# Per-line feature computation tests
# ---------------------------------------------------------------------------


class TestComputeLineFeatures:
    """Tests for compute_line_features."""

    def test_zero_matches_zero_density(
        self, test_index: LexiconIndex,
    ) -> None:
        """Line with no matches should have all densities = 0."""
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid="shabad:1",
            token_count=10,
            matches=[],
            index=test_index,
        )
        for dim in FEATURE_DIMENSIONS:
            assert feat["features"][dim]["count"] == 0
            assert feat["features"][dim]["density"] == 0.0

    def test_known_density_value(
        self, test_index: LexiconIndex,
    ) -> None:
        """Line with known matches produces expected density."""
        matches = [
            MatchRecord(
                line_uid="test:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥ",
                span=[0, 4],
            ),
        ]
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid="shabad:1",
            token_count=10,
            matches=matches,
            index=test_index,
        )
        # TEERATH is sanskritic register + ritual category
        assert feat["features"]["sanskritic"]["count"] == 1
        assert feat["features"]["ritual"]["count"] == 1
        assert abs(
            feat["features"]["sanskritic"]["density"] - 0.1,
        ) < 1e-6

    def test_density_bounds(
        self, test_index: LexiconIndex,
    ) -> None:
        """All densities are in [0.0, 1.0]."""
        matches = [
            MatchRecord(
                line_uid="test:1",
                entity_id="NAAM",
                matched_form="ਨਾਮੁ",
                span=[0, 4],
            ),
            MatchRecord(
                line_uid="test:1",
                entity_id="SATNAM",
                matched_form="ਸਤਿ ਨਾਮੁ",
                span=[0, 8],
            ),
            MatchRecord(
                line_uid="test:1",
                entity_id="HUKAM",
                matched_form="ਹੁਕਮੁ",
                span=[10, 15],
            ),
        ]
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid=None,
            token_count=5,
            matches=matches,
            index=test_index,
        )
        for dim in FEATURE_DIMENSIONS:
            d = feat["features"][dim]["density"]
            assert 0.0 <= d <= 1.0, (
                f"Density {d} out of bounds for {dim}"
            )

    def test_nested_matches_excluded(
        self, test_index: LexiconIndex,
    ) -> None:
        """Nested matches should not contribute to counts."""
        matches = [
            MatchRecord(
                line_uid="test:1",
                entity_id="SATNAM",
                matched_form="ਸਤਿ ਨਾਮੁ",
                span=[0, 8],
            ),
            MatchRecord(
                line_uid="test:1",
                entity_id="NAAM",
                matched_form="ਨਾਮੁ",
                span=[4, 8],
                nested_in="SATNAM",
            ),
        ]
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid=None,
            token_count=5,
            matches=matches,
            index=test_index,
        )
        # SATNAM is nirgun (concept + sikh tradition)
        # NAAM is nested so should not count
        nirgun_count = feat["features"]["nirgun"]["count"]
        assert nirgun_count == 1  # only SATNAM, not NAAM

    def test_matched_tokens_list(
        self, test_index: LexiconIndex,
    ) -> None:
        """matched_tokens field contains the actual matched forms."""
        matches = [
            MatchRecord(
                line_uid="test:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥ",
                span=[0, 4],
            ),
        ]
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid=None,
            token_count=5,
            matches=matches,
            index=test_index,
        )
        assert "ਤੀਰਥ" in feat["features"]["ritual"]["matched_tokens"]

    def test_all_dimensions_present(
        self, test_index: LexiconIndex,
    ) -> None:
        """All feature dimensions have entries even with zero matches."""
        feat = compute_line_features(
            line_uid="test:1",
            shabad_uid=None,
            token_count=5,
            matches=[],
            index=test_index,
        )
        for dim in FEATURE_DIMENSIONS:
            assert dim in feat["features"]
            assert "count" in feat["features"][dim]
            assert "density" in feat["features"][dim]
            assert "matched_tokens" in feat["features"][dim]

    def test_line_uid_and_shabad_uid_propagation(
        self, test_index: LexiconIndex,
    ) -> None:
        feat = compute_line_features(
            line_uid="test:42",
            shabad_uid="shabad:99",
            token_count=7,
            matches=[],
            index=test_index,
        )
        assert feat["line_uid"] == "test:42"
        assert feat["shabad_uid"] == "shabad:99"
        assert feat["token_count"] == 7


# ---------------------------------------------------------------------------
# Corpus-level feature computation tests
# ---------------------------------------------------------------------------


class TestComputeCorpusFeatures:
    """Tests for compute_corpus_features."""

    def test_processes_all_records(
        self, test_index: LexiconIndex,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "gurmukhi": "ਹੁਕਮੁ ਜਪ",
                "tokens": ["ਹੁਕਮੁ", "ਜਪ"],
                "meta": {"shabad_uid": "shabad:1"},
            },
            {
                "line_uid": "line:2",
                "gurmukhi": "ਨਾਮੁ ਜਪ",
                "tokens": ["ਨਾਮੁ", "ਜਪ"],
                "meta": {"shabad_uid": "shabad:1"},
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="HUKAM",
                matched_form="ਹੁਕਮੁ",
                span=[0, 5],
            ),
            MatchRecord(
                line_uid="line:2",
                entity_id="NAAM",
                matched_form="ਨਾਮੁ",
                span=[0, 4],
            ),
        ]
        results = compute_corpus_features(
            records, matches, test_index,
        )
        assert len(results) == 2

    def test_writes_output_file(
        self,
        test_index: LexiconIndex,
        tmp_path: Path,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "gurmukhi": "ਤੀਰਥ ਜਪ",
                "tokens": ["ਤੀਰਥ", "ਜਪ"],
                "meta": {},
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥ",
                span=[0, 4],
            ),
        ]
        output_path = tmp_path / "features.jsonl"
        compute_corpus_features(
            records, matches, test_index, output_path=output_path,
        )
        assert output_path.exists()
        content = output_path.read_text()
        assert "line:1" in content

    def test_empty_corpus(
        self, test_index: LexiconIndex,
    ) -> None:
        results = compute_corpus_features([], [], test_index)
        assert results == []

    def test_density_formula_in_batch(
        self, test_index: LexiconIndex,
    ) -> None:
        """Verify density = count / token_count across batch results."""
        records = [
            {
                "line_uid": "line:1",
                "gurmukhi": "ਤੀਰਥ ਤੀਰਥਿ ਜਪ ਹਰਿ",
                "tokens": ["ਤੀਰਥ", "ਤੀਰਥਿ", "ਜਪ", "ਹਰਿ"],
                "meta": {},
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥ",
                span=[0, 4],
            ),
            MatchRecord(
                line_uid="line:1",
                entity_id="TEERATH",
                matched_form="ਤੀਰਥਿ",
                span=[5, 10],
            ),
        ]
        results = compute_corpus_features(
            records, matches, test_index,
        )
        feat = results[0]
        # 2 ritual matches, 4 tokens => density 0.5
        ritual = feat["features"]["ritual"]
        assert ritual["count"] == 2
        expected_density = round(2 / 4, 6)
        assert abs(ritual["density"] - expected_density) < 1e-6
