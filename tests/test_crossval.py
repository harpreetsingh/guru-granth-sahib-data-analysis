"""Cross-validation framework tests (bd-15c.7).

Tests discrepancy classification, line comparison, ang sampling,
primary corpus reading, and end-to-end cross-validation.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ggs.corpus.crossval import (
    CrossValidationReport,
    DiscrepancyType,
    LineComparison,
    classify_discrepancy,
    compare_ang_lines,
    read_primary_ang_lines,
    run_cross_validation,
    sample_angs,
)

# ---------------------------------------------------------------------------
# Mock secondary source
# ---------------------------------------------------------------------------


class MockSecondarySource:
    """A mock secondary source for testing."""

    def __init__(
        self,
        data: dict[int, list[str]] | None = None,
    ) -> None:
        self._data = data or {}

    @property
    def name(self) -> str:
        return "mock_source"

    def fetch_ang_lines(self, ang: int) -> list[str]:
        if ang not in self._data:
            return []
        return self._data[ang]


# ---------------------------------------------------------------------------
# Discrepancy classification tests
# ---------------------------------------------------------------------------


class TestClassifyDiscrepancy:
    """Tests for classify_discrepancy."""

    def test_whitespace_only(self) -> None:
        result = classify_discrepancy(
            "ਹਰਿ  ਨਾਮੁ  ਜਪ",
            "ਹਰਿ ਨਾਮੁ ਜਪ",
        )
        assert result == DiscrepancyType.WHITESPACE_ONLY

    def test_vishram_only(self) -> None:
        result = classify_discrepancy(
            "ਹਰਿ ਨਾਮੁ। ਜਪ",
            "ਹਰਿ ਨਾਮੁ ਜਪ",
        )
        assert result == DiscrepancyType.VISHRAM_ONLY

    def test_nasal_only(self) -> None:
        # Tippi (ੰ) vs bindi (ਂ)
        result = classify_discrepancy(
            "ਸੰਤ",
            "ਸਂਤ",
        )
        assert result == DiscrepancyType.NASAL_ONLY

    def test_nukta_only(self) -> None:
        # With nukta ਖ਼ vs without ਖ
        result = classify_discrepancy(
            "ਖ਼ਾਲਸਾ",
            "ਖਾਲਸਾ",
        )
        assert result == DiscrepancyType.NUKTA_ONLY

    def test_substantive(self) -> None:
        result = classify_discrepancy(
            "ਹਰਿ ਨਾਮੁ",
            "ਅਲਾਹੁ ਜਪ",
        )
        assert result == DiscrepancyType.SUBSTANTIVE


# ---------------------------------------------------------------------------
# Line comparison tests
# ---------------------------------------------------------------------------


class TestCompareAngLines:
    """Tests for compare_ang_lines."""

    def test_identical_lines(self) -> None:
        primary = ["ਹਰਿ ਨਾਮੁ", "ਸਤਿ ਨਾਮੁ"]
        secondary = ["ਹਰਿ ਨਾਮੁ", "ਸਤਿ ਨਾਮੁ"]
        results = compare_ang_lines(1, primary, secondary)
        assert all(r.match for r in results)
        assert len(results) == 2

    def test_discrepancy_detected(self) -> None:
        primary = ["ਹਰਿ ਨਾਮੁ"]
        secondary = ["ਅਲਾਹੁ ਜਪ"]
        results = compare_ang_lines(1, primary, secondary)
        assert not results[0].match
        assert results[0].discrepancy_type is not None

    def test_extra_line_in_secondary(self) -> None:
        primary = ["ਹਰਿ ਨਾਮੁ"]
        secondary = ["ਹਰਿ ਨਾਮੁ", "ਸਤਿ ਨਾਮੁ"]
        results = compare_ang_lines(1, primary, secondary)
        assert results[0].match
        assert not results[1].match
        assert results[1].discrepancy_type == DiscrepancyType.EXTRA_LINE

    def test_missing_line_in_secondary(self) -> None:
        primary = ["ਹਰਿ ਨਾਮੁ", "ਸਤਿ ਨਾਮੁ"]
        secondary = ["ਹਰਿ ਨਾਮੁ"]
        results = compare_ang_lines(1, primary, secondary)
        assert results[0].match
        assert not results[1].match
        assert results[1].discrepancy_type == DiscrepancyType.MISSING_LINE

    def test_empty_lines(self) -> None:
        results = compare_ang_lines(1, [], [])
        assert results == []


# ---------------------------------------------------------------------------
# Ang sampling tests
# ---------------------------------------------------------------------------


class TestSampleAngs:
    """Tests for sample_angs."""

    def test_sample_size(self) -> None:
        result = sample_angs(
            total_angs=1430,
            sample_size=50,
            rng=random.Random(42),
        )
        # Stratified sampling may produce slightly fewer due to dedup
        assert len(result) <= 50
        assert len(result) >= 40  # Should be close to 50

    def test_all_in_range(self) -> None:
        result = sample_angs(
            total_angs=100,
            sample_size=10,
            rng=random.Random(42),
        )
        assert all(1 <= a <= 100 for a in result)

    def test_sorted(self) -> None:
        result = sample_angs(
            total_angs=1430,
            sample_size=50,
            rng=random.Random(42),
        )
        assert result == sorted(result)

    def test_full_coverage(self) -> None:
        result = sample_angs(
            total_angs=10, sample_size=20,
        )
        assert result == list(range(1, 11))

    def test_deterministic_with_rng(self) -> None:
        r1 = sample_angs(rng=random.Random(42))
        r2 = sample_angs(rng=random.Random(42))
        assert r1 == r2


# ---------------------------------------------------------------------------
# Primary corpus reader tests
# ---------------------------------------------------------------------------


class TestReadPrimaryAngLines:
    """Tests for read_primary_ang_lines."""

    def test_reads_correct_ang(self) -> None:
        records = [
            {"ang": 1, "gurmukhi": "ਹਰਿ ਨਾਮੁ"},
            {"ang": 1, "gurmukhi": "ਸਤਿ ਨਾਮੁ"},
            {"ang": 2, "gurmukhi": "ਅਲਾਹੁ ਜਪ"},
        ]
        lines = read_primary_ang_lines(records, 1)
        assert len(lines) == 2
        assert lines[0] == "ਹਰਿ ਨਾਮੁ"

    def test_missing_ang(self) -> None:
        records = [{"ang": 1, "gurmukhi": "ਹਰਿ"}]
        lines = read_primary_ang_lines(records, 99)
        assert lines == []


# ---------------------------------------------------------------------------
# LineComparison serialization tests
# ---------------------------------------------------------------------------


class TestLineComparisonSerialization:
    """Tests for LineComparison.to_dict."""

    def test_matching_line(self) -> None:
        lc = LineComparison(
            ang=1, line_index=0,
            primary_text="ਹਰਿ", secondary_text="ਹਰਿ",
            match=True,
        )
        d = lc.to_dict()
        assert d["match"] is True
        assert "primary_text" not in d

    def test_non_matching_line(self) -> None:
        lc = LineComparison(
            ang=1, line_index=0,
            primary_text="ਹਰਿ", secondary_text="ਅਲਾਹੁ",
            match=False,
            discrepancy_type=DiscrepancyType.SUBSTANTIVE,
        )
        d = lc.to_dict()
        assert d["match"] is False
        assert d["primary_text"] == "ਹਰਿ"
        assert d["discrepancy_type"] == "substantive"


# ---------------------------------------------------------------------------
# Report serialization tests
# ---------------------------------------------------------------------------


class TestCrossValidationReport:
    """Tests for CrossValidationReport."""

    def test_to_dict(self) -> None:
        report = CrossValidationReport(
            source_secondary="test",
            angs_sampled=5,
            total_lines_compared=10,
            total_matches=8,
            total_discrepancies=2,
        )
        d = report.to_dict()
        assert d["match_rate"] == 0.8
        assert d["angs_sampled"] == 5

    def test_write_to_file(self, tmp_path: Path) -> None:
        report = CrossValidationReport()
        output = tmp_path / "crossval.json"
        report.write(output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert "match_rate" in data


# ---------------------------------------------------------------------------
# End-to-end cross-validation tests
# ---------------------------------------------------------------------------


class TestRunCrossValidation:
    """Tests for run_cross_validation."""

    def test_perfect_match(self) -> None:
        records = [
            {"ang": 1, "gurmukhi": "ਹਰਿ ਨਾਮੁ"},
            {"ang": 1, "gurmukhi": "ਸਤਿ ਨਾਮੁ"},
        ]
        source = MockSecondarySource({
            1: ["ਹਰਿ ਨਾਮੁ", "ਸਤਿ ਨਾਮੁ"],
        })
        report = run_cross_validation(
            records, source,
            sample_size=1,
            total_angs=1,
            rng=random.Random(0),
        )
        assert report.total_matches == 2
        assert report.total_discrepancies == 0

    def test_with_discrepancies(self) -> None:
        records = [
            {"ang": 1, "gurmukhi": "ਹਰਿ ਨਾਮੁ"},
        ]
        source = MockSecondarySource({
            1: ["ਅਲਾਹੁ ਜਪ"],
        })
        report = run_cross_validation(
            records, source,
            sample_size=1,
            total_angs=1,
            rng=random.Random(0),
        )
        assert report.total_discrepancies == 1

    def test_output_written(self, tmp_path: Path) -> None:
        records = [
            {"ang": 1, "gurmukhi": "ਹਰਿ ਨਾਮੁ"},
        ]
        source = MockSecondarySource({1: ["ਹਰਿ ਨਾਮੁ"]})
        output = tmp_path / "crossval.json"
        run_cross_validation(
            records, source,
            sample_size=1,
            total_angs=1,
            rng=random.Random(0),
            output_path=output,
        )
        assert output.exists()

    def test_empty_corpus(self) -> None:
        source = MockSecondarySource({})
        report = run_cross_validation(
            [], source, sample_size=1,
            total_angs=1,
            rng=random.Random(0),
        )
        assert report.total_lines_compared == 0
