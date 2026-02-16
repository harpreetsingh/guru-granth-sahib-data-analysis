"""Co-occurrence engine tests (bd-9qw.2, bd-9qw.3).

Tests line-level and shabad-level co-occurrence computation:
pair counting, PMI, normalized PMI, Jaccard, min_count filtering,
window grouping, nested match exclusion, output serialization,
and PMI stability measures (min entity freq, smoothing, min PMI support).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ggs.analysis.cooccurrence import (
    CooccurrencePair,
    WindowLevel,
    _compute_jaccard,
    _compute_npmi,
    _compute_pmi,
    _compute_smoothed_pmi,
    _count_entity_occurrences,
    _count_pairs,
    _filter_by_entity_freq,
    _group_matches_by_line,
    _group_matches_by_shabad,
    _write_output,
    build_line_to_shabad_map,
    compute_all_cooccurrence,
    compute_cooccurrence,
)
from ggs.analysis.match import MatchRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_matches() -> list[MatchRecord]:
    """Matches across multiple lines with some co-occurring entities."""
    return [
        # Line 1: HARI + NAAM co-occur
        MatchRecord(
            line_uid="line:1",
            entity_id="HARI",
            matched_form="ਹਰਿ",
            span=[0, 3],
        ),
        MatchRecord(
            line_uid="line:1",
            entity_id="NAAM",
            matched_form="ਨਾਮੁ",
            span=[4, 8],
        ),
        # Line 2: HARI + NAAM + ALLAH co-occur
        MatchRecord(
            line_uid="line:2",
            entity_id="HARI",
            matched_form="ਹਰਿ",
            span=[0, 3],
        ),
        MatchRecord(
            line_uid="line:2",
            entity_id="NAAM",
            matched_form="ਨਾਮੁ",
            span=[4, 8],
        ),
        MatchRecord(
            line_uid="line:2",
            entity_id="ALLAH",
            matched_form="ਅਲਾਹੁ",
            span=[9, 14],
        ),
        # Line 3: ALLAH + RAM co-occur
        MatchRecord(
            line_uid="line:3",
            entity_id="ALLAH",
            matched_form="ਅਲਾਹੁ",
            span=[0, 5],
        ),
        MatchRecord(
            line_uid="line:3",
            entity_id="RAM",
            matched_form="ਰਾਮ",
            span=[6, 9],
        ),
        # Line 4: HARI alone
        MatchRecord(
            line_uid="line:4",
            entity_id="HARI",
            matched_form="ਹਰਿ",
            span=[0, 3],
        ),
        # Line 5: Nested match — NAAM nested in SATNAM
        MatchRecord(
            line_uid="line:5",
            entity_id="SATNAM",
            matched_form="ਸਤਿ ਨਾਮੁ",
            span=[0, 8],
        ),
        MatchRecord(
            line_uid="line:5",
            entity_id="NAAM",
            matched_form="ਨਾਮੁ",
            span=[4, 8],
            nested_in="SATNAM",
        ),
    ]


@pytest.fixture()
def sample_records() -> list[dict]:
    """Corpus records for the sample matches."""
    return [
        {
            "line_uid": "line:1",
            "ang": 1,
            "meta": {"shabad_uid": "shabad:1"},
        },
        {
            "line_uid": "line:2",
            "ang": 1,
            "meta": {"shabad_uid": "shabad:1"},
        },
        {
            "line_uid": "line:3",
            "ang": 2,
            "meta": {"shabad_uid": "shabad:2"},
        },
        {
            "line_uid": "line:4",
            "ang": 2,
            "meta": {"shabad_uid": "shabad:2"},
        },
        {
            "line_uid": "line:5",
            "ang": 3,
            "meta": {"shabad_uid": "shabad:3"},
        },
    ]


@pytest.fixture()
def line_windows(sample_matches: list[MatchRecord]) -> dict[str, set[str]]:
    """Pre-computed line windows from sample_matches."""
    return _group_matches_by_line(sample_matches)


# ---------------------------------------------------------------------------
# Window grouping tests
# ---------------------------------------------------------------------------


class TestGroupMatchesByLine:
    """Tests for _group_matches_by_line."""

    def test_groups_entities_by_line(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        groups = _group_matches_by_line(sample_matches)
        assert "HARI" in groups["line:1"]
        assert "NAAM" in groups["line:1"]

    def test_excludes_nested_matches(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        groups = _group_matches_by_line(sample_matches)
        # line:5 has SATNAM (not nested) and NAAM (nested_in=SATNAM)
        assert "SATNAM" in groups["line:5"]
        assert "NAAM" not in groups["line:5"]

    def test_all_lines_represented(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        groups = _group_matches_by_line(sample_matches)
        assert set(groups.keys()) == {
            "line:1", "line:2", "line:3", "line:4", "line:5",
        }

    def test_empty_matches(self) -> None:
        groups = _group_matches_by_line([])
        assert groups == {}

    def test_single_entity_per_line(self) -> None:
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="HARI",
                matched_form="ਹਰਿ",
                span=[0, 3],
            ),
        ]
        groups = _group_matches_by_line(matches)
        assert groups == {"line:1": {"HARI"}}


class TestGroupMatchesByShabad:
    """Tests for _group_matches_by_shabad."""

    def test_groups_entities_by_shabad(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        line_to_shabad = {
            "line:1": "shabad:1",
            "line:2": "shabad:1",
            "line:3": "shabad:2",
            "line:4": "shabad:2",
            "line:5": "shabad:3",
        }
        groups = _group_matches_by_shabad(
            sample_matches, line_to_shabad,
        )
        # shabad:1 includes line:1 + line:2 entities
        assert "HARI" in groups["shabad:1"]
        assert "NAAM" in groups["shabad:1"]
        assert "ALLAH" in groups["shabad:1"]
        # shabad:2 includes line:3 + line:4
        assert "ALLAH" in groups["shabad:2"]
        assert "RAM" in groups["shabad:2"]
        assert "HARI" in groups["shabad:2"]

    def test_excludes_nested_matches(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        line_to_shabad = {
            "line:5": "shabad:3",
        }
        groups = _group_matches_by_shabad(
            sample_matches, line_to_shabad,
        )
        assert "SATNAM" in groups.get("shabad:3", set())
        assert "NAAM" not in groups.get("shabad:3", set())

    def test_skips_unmapped_lines(self) -> None:
        matches = [
            MatchRecord(
                line_uid="line:99",
                entity_id="HARI",
                matched_form="ਹਰਿ",
                span=[0, 3],
            ),
        ]
        groups = _group_matches_by_shabad(matches, {})
        assert groups == {}


class TestBuildLineToShabadMap:
    """Tests for build_line_to_shabad_map."""

    def test_uses_meta_shabad_uid(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "meta": {"shabad_uid": "shabad:42"},
            },
        ]
        mapping = build_line_to_shabad_map(records)
        assert mapping["line:1"] == "shabad:42"

    def test_fallback_to_ang(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 5, "meta": {}},
        ]
        mapping = build_line_to_shabad_map(records)
        assert mapping["line:1"] == "ang:5"

    def test_shabad_uid_preferred_over_ang(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 5,
                "meta": {"shabad_uid": "shabad:99"},
            },
        ]
        mapping = build_line_to_shabad_map(records)
        assert mapping["line:1"] == "shabad:99"

    def test_empty_records(self) -> None:
        mapping = build_line_to_shabad_map([])
        assert mapping == {}


# ---------------------------------------------------------------------------
# Pair counting tests
# ---------------------------------------------------------------------------


class TestCountPairs:
    """Tests for _count_pairs."""

    def test_basic_pair_counting(self) -> None:
        windows = {
            "w1": {"A", "B", "C"},
            "w2": {"A", "B"},
            "w3": {"B", "C"},
        }
        counts = _count_pairs(windows)
        assert counts[("A", "B")] == 2
        assert counts[("A", "C")] == 1
        assert counts[("B", "C")] == 2

    def test_single_entity_no_pairs(self) -> None:
        windows = {"w1": {"A"}}
        counts = _count_pairs(windows)
        assert counts == {}

    def test_empty_windows(self) -> None:
        counts = _count_pairs({})
        assert counts == {}

    def test_pairs_are_sorted(self) -> None:
        windows = {"w1": {"Z", "A"}}
        counts = _count_pairs(windows)
        assert ("A", "Z") in counts
        assert ("Z", "A") not in counts

    def test_no_self_pairs(self) -> None:
        """An entity co-occurring with itself is not a pair."""
        windows = {"w1": {"A"}, "w2": {"A"}}
        counts = _count_pairs(windows)
        assert ("A", "A") not in counts


class TestCountEntityOccurrences:
    """Tests for _count_entity_occurrences."""

    def test_basic_counting(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "C"},
            "w3": {"A"},
        }
        counts = _count_entity_occurrences(windows)
        assert counts["A"] == 3
        assert counts["B"] == 1
        assert counts["C"] == 1


# ---------------------------------------------------------------------------
# Metric computation tests
# ---------------------------------------------------------------------------


class TestComputePMI:
    """Tests for _compute_pmi."""

    def test_independent_entities_zero_pmi(self) -> None:
        # P(A,B) = P(A) * P(B) => PMI = 0
        pmi = _compute_pmi(0.04, 0.2, 0.2)
        assert abs(pmi) < 1e-10

    def test_positive_association(self) -> None:
        # P(A,B) > P(A) * P(B) => PMI > 0
        pmi = _compute_pmi(0.1, 0.2, 0.2)
        assert pmi > 0

    def test_negative_association(self) -> None:
        # P(A,B) < P(A) * P(B) => PMI < 0
        pmi = _compute_pmi(0.01, 0.2, 0.2)
        assert pmi < 0

    def test_zero_probability(self) -> None:
        assert _compute_pmi(0.0, 0.2, 0.2) == 0.0
        assert _compute_pmi(0.1, 0.0, 0.2) == 0.0
        assert _compute_pmi(0.1, 0.2, 0.0) == 0.0


class TestComputeNPMI:
    """Tests for _compute_npmi."""

    def test_bounded_range(self) -> None:
        # NPMI should be in [-1, 1] for valid inputs
        pmi = _compute_pmi(0.1, 0.2, 0.2)
        npmi = _compute_npmi(pmi, 0.1)
        assert -1.0 <= npmi <= 1.0

    def test_perfect_association_npmi_one(self) -> None:
        # When P(A,B) = P(A) = P(B), PMI = log2(1/P(A))
        # NPMI = log2(1/P(A)) / log2(1/P(A)) = 1
        p = 0.3
        pmi = _compute_pmi(p, p, p)
        npmi = _compute_npmi(pmi, p)
        assert abs(npmi - 1.0) < 1e-10

    def test_zero_joint_probability(self) -> None:
        npmi = _compute_npmi(0.0, 0.0)
        assert npmi == 0.0


class TestComputeJaccard:
    """Tests for _compute_jaccard."""

    def test_perfect_overlap(self) -> None:
        # Both appear in same 5 windows, neither alone
        j = _compute_jaccard(5, 5, 5)
        assert abs(j - 1.0) < 1e-10

    def test_no_overlap(self) -> None:
        j = _compute_jaccard(0, 5, 5)
        assert j == 0.0

    def test_partial_overlap(self) -> None:
        # 2 windows with both, A in 4, B in 3 => 2 / (4+3-2) = 2/5 = 0.4
        j = _compute_jaccard(2, 4, 3)
        assert abs(j - 0.4) < 1e-10

    def test_zero_denominator(self) -> None:
        j = _compute_jaccard(0, 0, 0)
        assert j == 0.0


# ---------------------------------------------------------------------------
# Core engine tests
# ---------------------------------------------------------------------------


class TestComputeCooccurrence:
    """Tests for compute_cooccurrence."""

    def test_basic_cooccurrence(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "B", "C"},
            "w3": {"B", "C"},
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=2,
        )
        pair_keys = {(p.entity_a, p.entity_b) for p in pairs}
        assert ("A", "B") in pair_keys
        assert ("B", "C") in pair_keys
        # (A, C) only appears once, should be filtered out
        assert ("A", "C") not in pair_keys

    def test_min_count_filtering(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "C"},
        }
        pairs_2 = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=2,
        )
        assert len(pairs_2) == 0  # no pair appears >= 2 times

        pairs_1 = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=1,
        )
        assert len(pairs_1) == 2  # (A,B) and (A,C) each appear once

    def test_sorted_by_raw_count_descending(self) -> None:
        windows = {
            f"w{i}": {"A", "B"} for i in range(5)
        }
        windows["w5"] = {"A", "C"}
        windows["w6"] = {"A", "C"}
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=1,
        )
        # A,B: 5 occurrences; A,C: 2 occurrences
        assert pairs[0].raw_count >= pairs[-1].raw_count

    def test_empty_windows(self) -> None:
        pairs = compute_cooccurrence(
            {}, WindowLevel.LINE, min_count=1,
        )
        assert pairs == []

    def test_window_level_set_correctly(self) -> None:
        windows = {"w1": {"A", "B"}, "w2": {"A", "B"}}
        pairs = compute_cooccurrence(
            windows, WindowLevel.SHABAD, min_count=1,
        )
        assert all(p.window_level == "shabad" for p in pairs)

    def test_pmi_positive_for_strongly_associated(self) -> None:
        # A and B always appear together, rarely with others
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "B"},
            "w3": {"C", "D"},
            "w4": {"C", "D"},
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=2,
        )
        ab_pair = next(
            p for p in pairs
            if p.entity_a == "A" and p.entity_b == "B"
        )
        assert ab_pair.pmi is not None and ab_pair.pmi > 0

    def test_jaccard_correct(self) -> None:
        # A in w1, w2, w3; B in w1, w2; both in w1, w2
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "B"},
            "w3": {"A"},
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=2,
        )
        ab_pair = next(
            p for p in pairs
            if p.entity_a == "A" and p.entity_b == "B"
        )
        # Jaccard = 2 / (3 + 2 - 2) = 2/3
        assert abs(ab_pair.jaccard - 2 / 3) < 1e-6


# ---------------------------------------------------------------------------
# Batch processing tests
# ---------------------------------------------------------------------------


class TestComputeAllCooccurrence:
    """Tests for compute_all_cooccurrence."""

    def test_returns_both_levels(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
    ) -> None:
        result = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
        )
        assert "line" in result
        assert "shabad" in result

    def test_line_level_pairs(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
    ) -> None:
        result = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
        )
        line_pair_keys = {
            (p.entity_a, p.entity_b)
            for p in result["line"]
        }
        # HARI + NAAM co-occur on line:1 and line:2
        assert ("HARI", "NAAM") in line_pair_keys

    def test_shabad_level_has_more_pairs(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
    ) -> None:
        """Shabad windows are wider, so they should find more pairs."""
        result = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
        )
        shabad_pair_keys = {
            (p.entity_a, p.entity_b)
            for p in result["shabad"]
        }
        # Shabad-level should include at least everything line-level has
        # (though not necessarily if min_count filters differently)
        # At minimum, shabad-level should have HARI+RAM since they're
        # in the same shabad:2
        assert ("HARI", "RAM") in shabad_pair_keys

    def test_output_to_file(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "cooccurrence.json"
        compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
            output_path=output_path,
        )
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "line" in data
        assert "shabad" in data
        assert "pair_count" in data["line"]
        assert "pairs" in data["line"]

    def test_empty_matches(
        self, sample_records: list[dict],
    ) -> None:
        result = compute_all_cooccurrence(
            [],
            sample_records,
            min_count=1,
        )
        assert result["line"] == []
        assert result["shabad"] == []


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class TestCooccurrencePairSerialization:
    """Tests for CooccurrencePair.to_dict()."""

    def test_to_dict_fields(self) -> None:
        pair = CooccurrencePair(
            entity_a="ALLAH",
            entity_b="RAM",
            window_level="line",
            raw_count=5,
            pmi=1.234567,
            npmi=0.654321,
            jaccard=0.333333,
        )
        d = pair.to_dict()
        assert d["entity_a"] == "ALLAH"
        assert d["entity_b"] == "RAM"
        assert d["window_level"] == "line"
        assert d["raw_count"] == 5
        assert d["pmi"] == 1.234567
        assert d["npmi"] == 0.654321
        assert d["jaccard"] == 0.333333

    def test_to_dict_rounds_floats(self) -> None:
        pair = CooccurrencePair(
            entity_a="A",
            entity_b="B",
            window_level="shabad",
            raw_count=1,
            pmi=1.23456789012,
            npmi=0.98765432109,
            jaccard=0.11111111111,
        )
        d = pair.to_dict()
        assert d["pmi"] == 1.234568
        assert d["npmi"] == 0.987654
        assert d["jaccard"] == 0.111111


class TestWriteOutput:
    """Tests for _write_output."""

    def test_creates_parent_directories(
        self, tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "sub" / "dir" / "cooccurrence.json"
        _write_output({"line": [], "shabad": []}, output_path)
        assert output_path.exists()

    def test_json_structure(self, tmp_path: Path) -> None:
        pair = CooccurrencePair(
            entity_a="A",
            entity_b="B",
            window_level="line",
            raw_count=3,
            pmi=1.5,
            npmi=0.8,
            jaccard=0.5,
        )
        output_path = tmp_path / "cooccurrence.json"
        _write_output(
            {"line": [pair], "shabad": []},
            output_path,
        )
        data = json.loads(output_path.read_text())
        assert data["line"]["pair_count"] == 1
        assert data["line"]["pairs"][0]["entity_a"] == "A"
        assert data["shabad"]["pair_count"] == 0


# ---------------------------------------------------------------------------
# PMI stability measures tests (bd-9qw.3)
# ---------------------------------------------------------------------------


class TestFilterByEntityFreq:
    """Tests for _filter_by_entity_freq."""

    def test_no_filtering_at_threshold_1(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A"},
        }
        result = _filter_by_entity_freq(windows, min_entity_freq=1)
        assert result == windows

    def test_filters_rare_entities(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "C"},
            "w3": {"A", "B"},
        }
        # B appears in 2 windows, C in 1
        result = _filter_by_entity_freq(windows, min_entity_freq=2)
        assert "C" not in result.get("w2", set())
        assert "A" in result["w1"]
        assert "B" in result["w1"]

    def test_drops_empty_windows_after_filtering(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"C"},  # C only appears once
        }
        result = _filter_by_entity_freq(windows, min_entity_freq=2)
        # After filtering, w2 would be empty and should be dropped
        assert "w2" not in result

    def test_all_entities_meet_threshold(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A", "B"},
        }
        result = _filter_by_entity_freq(windows, min_entity_freq=2)
        assert result == windows

    def test_empty_windows(self) -> None:
        result = _filter_by_entity_freq({}, min_entity_freq=10)
        assert result == {}

    def test_high_threshold_removes_everything(self) -> None:
        windows = {
            "w1": {"A", "B"},
            "w2": {"A"},
        }
        result = _filter_by_entity_freq(windows, min_entity_freq=100)
        assert result == {}


class TestComputeSmoothedPMI:
    """Tests for _compute_smoothed_pmi."""

    def test_smoothed_pmi_dampens_extreme_values(self) -> None:
        # Without smoothing, perfect association gives very high PMI
        # With smoothing, it should be lower
        unsmoothed = _compute_pmi(2 / 10, 2 / 10, 2 / 10)
        smoothed = _compute_smoothed_pmi(
            count_ab=2, count_a=2, count_b=2,
            total_windows=10, num_unique_entities=5,
            smoothing_k=1.0,
        )
        # Smoothed PMI should be strictly lower than unsmoothed
        # for strongly associated rare pairs
        assert smoothed < unsmoothed

    def test_smoothed_pmi_prevents_extreme_for_rare_pair(self) -> None:
        # Rare pair: appears once out of 100 windows
        smoothed = _compute_smoothed_pmi(
            count_ab=1, count_a=1, count_b=1,
            total_windows=100, num_unique_entities=10,
            smoothing_k=1.0,
        )
        # Should produce a finite, reasonable value
        assert -20 < smoothed < 20

    def test_zero_smoothing_gives_same_as_unsmoothed(self) -> None:
        # With k=0, smoothed PMI should match unsmoothed (approximately)
        # k=0 is not recommended but should not crash
        smoothed = _compute_smoothed_pmi(
            count_ab=5, count_a=10, count_b=10,
            total_windows=100, num_unique_entities=5,
            smoothing_k=0.0,
        )
        unsmoothed = _compute_pmi(5 / 100, 10 / 100, 10 / 100)
        assert abs(smoothed - unsmoothed) < 1e-6

    def test_higher_k_dampens_more(self) -> None:
        args = {
            "count_ab": 3,
            "count_a": 5,
            "count_b": 5,
            "total_windows": 100,
            "num_unique_entities": 10,
        }
        pmi_k1 = _compute_smoothed_pmi(**args, smoothing_k=1.0)
        pmi_k5 = _compute_smoothed_pmi(**args, smoothing_k=5.0)
        # Higher k should dampen the PMI (push toward 0)
        assert abs(pmi_k5) <= abs(pmi_k1) + 1e-6


class TestMinPmiSupport:
    """Tests for min_pmi_support in compute_cooccurrence."""

    def test_low_count_pairs_get_none_pmi(self) -> None:
        """Pairs with raw_count < min_pmi_support get pmi=None."""
        windows = {
            f"w{i}": {"A", "B"} for i in range(3)
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_pmi_support=5,
        )
        # A,B appear 3 times, below min_pmi_support=5
        assert len(pairs) == 1
        ab = pairs[0]
        assert ab.pmi is None
        assert ab.npmi is None
        assert ab.jaccard > 0  # Jaccard still computed

    def test_high_count_pairs_get_pmi(self) -> None:
        """Pairs with raw_count >= min_pmi_support get computed pmi."""
        windows = {
            f"w{i}": {"A", "B"} for i in range(10)
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_pmi_support=5,
        )
        assert len(pairs) == 1
        ab = pairs[0]
        assert ab.pmi is not None
        assert ab.npmi is not None

    def test_mixed_support_levels(self) -> None:
        """Some pairs above threshold, some below."""
        # A+B appear 6 times, A+C appear 2 times
        windows = {}
        for i in range(6):
            windows[f"ab{i}"] = {"A", "B"}
        for i in range(2):
            windows[f"ac{i}"] = {"A", "C"}
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_pmi_support=5,
        )
        pair_dict = {(p.entity_a, p.entity_b): p for p in pairs}
        assert pair_dict[("A", "B")].pmi is not None
        assert pair_dict[("A", "C")].pmi is None

    def test_zero_min_pmi_support_computes_all(self) -> None:
        """When min_pmi_support=0, all pairs get PMI computed."""
        windows = {"w1": {"A", "B"}}
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_pmi_support=0,
        )
        assert pairs[0].pmi is not None


class TestMinEntityFreqInCooccurrence:
    """Tests for min_entity_freq in compute_cooccurrence."""

    def test_filters_rare_entities(self) -> None:
        # C appears only once, A and B appear 3 times
        windows = {
            "w1": {"A", "B", "C"},
            "w2": {"A", "B"},
            "w3": {"A", "B"},
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_entity_freq=2,
        )
        pair_keys = {(p.entity_a, p.entity_b) for p in pairs}
        assert ("A", "B") in pair_keys
        # C was filtered out, so no (A,C) or (B,C) pairs
        assert ("A", "C") not in pair_keys
        assert ("B", "C") not in pair_keys

    def test_no_filtering_by_default(self) -> None:
        windows = {
            "w1": {"A", "B"},
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            min_entity_freq=1,
        )
        assert len(pairs) == 1


class TestSmoothingInCooccurrence:
    """Tests for smoothing_k in compute_cooccurrence."""

    def test_smoothing_produces_different_pmi(self) -> None:
        """With smoothing_k > 0, PMI values should differ from unsmoothed."""
        windows = {
            f"w{i}": {"A", "B"} for i in range(5)
        }
        # Add extra windows so totals differ from entity counts
        windows["w5"] = {"A"}
        windows["w6"] = {"B"}

        pairs_raw = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            smoothing_k=0.0,
        )
        pairs_smoothed = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            smoothing_k=1.0,
        )
        raw_pmi = pairs_raw[0].pmi
        smoothed_pmi = pairs_smoothed[0].pmi
        assert raw_pmi is not None
        assert smoothed_pmi is not None
        assert raw_pmi != smoothed_pmi

    def test_smoothing_with_min_pmi_support(self) -> None:
        """Smoothing and min_pmi_support can work together."""
        windows = {
            f"w{i}": {"A", "B"} for i in range(3)
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE,
            min_count=1,
            smoothing_k=1.0,
            min_pmi_support=5,
        )
        # raw_count=3 < min_pmi_support=5
        assert pairs[0].pmi is None


class TestSerializationWithNonePmi:
    """Test serialization when PMI is None."""

    def test_to_dict_with_none_pmi(self) -> None:
        pair = CooccurrencePair(
            entity_a="A",
            entity_b="B",
            window_level="line",
            raw_count=3,
            pmi=None,
            npmi=None,
            jaccard=0.5,
        )
        d = pair.to_dict()
        assert d["pmi"] is None
        assert d["npmi"] is None
        assert d["jaccard"] == 0.5

    def test_to_dict_with_float_pmi(self) -> None:
        pair = CooccurrencePair(
            entity_a="A",
            entity_b="B",
            window_level="line",
            raw_count=10,
            pmi=1.5,
            npmi=0.8,
            jaccard=0.5,
        )
        d = pair.to_dict()
        assert d["pmi"] == 1.5
        assert d["npmi"] == 0.8

    def test_json_output_with_none_pmi(self, tmp_path: Path) -> None:
        pair = CooccurrencePair(
            entity_a="A",
            entity_b="B",
            window_level="line",
            raw_count=3,
            pmi=None,
            npmi=None,
            jaccard=0.5,
        )
        output_path = tmp_path / "cooccurrence.json"
        _write_output(
            {"line": [pair], "shabad": []},
            output_path,
        )
        data = json.loads(output_path.read_text())
        assert data["line"]["pairs"][0]["pmi"] is None
        assert data["line"]["pairs"][0]["npmi"] is None


class TestComputeAllCooccurrenceWithStability:
    """Tests for compute_all_cooccurrence with stability parameters."""

    def test_passes_stability_params(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
    ) -> None:
        """Stability parameters are passed through to compute_cooccurrence."""
        result = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
            min_entity_freq=1,
            smoothing_k=1.0,
            min_pmi_support=5,
        )
        assert "line" in result
        assert "shabad" in result

    def test_min_entity_freq_reduces_pairs(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
    ) -> None:
        # Without frequency filter
        result_all = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
            min_entity_freq=1,
        )
        # With high frequency filter
        result_filtered = compute_all_cooccurrence(
            sample_matches,
            sample_records,
            min_count=1,
            min_entity_freq=10,  # No entity appears >= 10 times
        )
        assert len(result_filtered["line"]) <= len(result_all["line"])
        assert len(result_filtered["shabad"]) <= len(result_all["shabad"])
