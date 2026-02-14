"""Register density aggregation and sliding window tests (bd-9qw.4).

Tests per-ang aggregation, per-raga aggregation, sliding window computation,
raga section loading, and output serialization.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ggs.analysis.density import (
    AngDensity,
    RagaSection,
    WindowDensity,
    _index_features_by_ang,
    _safe_mean,
    _safe_median,
    _safe_stdev,
    ang_to_raga,
    compute_all_density_aggregations,
    compute_ang_densities,
    compute_raga_densities,
    compute_sliding_window,
    load_raga_sections,
)
from ggs.analysis.features import FEATURE_DIMENSIONS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_sections() -> list[RagaSection]:
    """Small set of raga sections for testing."""
    return [
        RagaSection(
            id="PREAMBLE", romanized="Preamble",
            ang_start=1, ang_end=3,
        ),
        RagaSection(
            id="SRI", romanized="Sri Raag",
            ang_start=4, ang_end=6,
        ),
    ]


@pytest.fixture()
def sample_features_by_ang() -> dict[int, list[dict[str, float]]]:
    """Sample density data indexed by ang."""
    dims = {dim: 0.0 for dim in FEATURE_DIMENSIONS}
    return {
        1: [
            {**dims, "perso_arabic": 0.1, "sanskritic": 0.2},
            {**dims, "perso_arabic": 0.3, "sanskritic": 0.0},
        ],
        2: [
            {**dims, "perso_arabic": 0.0, "sanskritic": 0.4},
        ],
        3: [
            {**dims, "perso_arabic": 0.2, "sanskritic": 0.1},
        ],
        4: [
            {**dims, "perso_arabic": 0.5, "sanskritic": 0.0},
        ],
        5: [
            {**dims, "perso_arabic": 0.0, "sanskritic": 0.6},
            {**dims, "perso_arabic": 0.1, "sanskritic": 0.5},
        ],
    }


@pytest.fixture()
def ragas_yaml(tmp_path: Path) -> Path:
    """Create a test ragas.yaml file."""
    data = {
        "preamble": {
            "romanized": "Preamble",
            "ang_start": 1,
            "ang_end": 3,
        },
        "ragas": [
            {
                "id": "SRI",
                "romanized": "Sri Raag",
                "ang_start": 4,
                "ang_end": 6,
            },
        ],
        "epilogue": {
            "romanized": "Epilogue",
            "ang_start": 7,
            "ang_end": 10,
        },
    }
    path = tmp_path / "ragas.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Safe stats tests
# ---------------------------------------------------------------------------


class TestSafeStats:
    """Tests for _safe_mean, _safe_median, _safe_stdev."""

    def test_safe_mean_basic(self) -> None:
        assert abs(_safe_mean([1.0, 2.0, 3.0]) - 2.0) < 1e-10

    def test_safe_mean_empty(self) -> None:
        assert _safe_mean([]) == 0.0

    def test_safe_median_basic(self) -> None:
        assert abs(_safe_median([1.0, 2.0, 3.0]) - 2.0) < 1e-10

    def test_safe_median_empty(self) -> None:
        assert _safe_median([]) == 0.0

    def test_safe_stdev_basic(self) -> None:
        result = _safe_stdev([1.0, 2.0, 3.0])
        assert result > 0.0

    def test_safe_stdev_empty(self) -> None:
        assert _safe_stdev([]) == 0.0

    def test_safe_stdev_single(self) -> None:
        assert _safe_stdev([5.0]) == 0.0


# ---------------------------------------------------------------------------
# Raga section tests
# ---------------------------------------------------------------------------


class TestRagaSections:
    """Tests for load_raga_sections and ang_to_raga."""

    def test_load_raga_sections(self, ragas_yaml: Path) -> None:
        sections = load_raga_sections(ragas_yaml)
        assert len(sections) == 3  # preamble + SRI + epilogue
        assert sections[0].id == "PREAMBLE"
        assert sections[1].id == "SRI"
        assert sections[2].id == "EPILOGUE"

    def test_ang_to_raga(
        self, sample_sections: list[RagaSection],
    ) -> None:
        assert ang_to_raga(1, sample_sections) == "PREAMBLE"
        assert ang_to_raga(3, sample_sections) == "PREAMBLE"
        assert ang_to_raga(4, sample_sections) == "SRI"
        assert ang_to_raga(6, sample_sections) == "SRI"

    def test_ang_to_raga_not_found(
        self, sample_sections: list[RagaSection],
    ) -> None:
        assert ang_to_raga(99, sample_sections) is None

    def test_real_ragas_yaml(self) -> None:
        """Load the actual ragas.yaml from config."""
        path = Path("config/ragas.yaml")
        if path.exists():
            sections = load_raga_sections(path)
            # 31 ragas + preamble + epilogue = 33
            assert len(sections) == 33


# ---------------------------------------------------------------------------
# Index features by ang tests
# ---------------------------------------------------------------------------


class TestIndexFeaturesByAng:
    """Tests for _index_features_by_ang."""

    def test_indexes_correctly(self) -> None:
        corpus_records = [
            {"line_uid": "line:1", "ang": 1},
            {"line_uid": "line:2", "ang": 1},
            {"line_uid": "line:3", "ang": 2},
        ]
        feature_records = [
            {
                "line_uid": "line:1",
                "features": {"perso_arabic": {"density": 0.1}},
            },
            {
                "line_uid": "line:2",
                "features": {"perso_arabic": {"density": 0.2}},
            },
            {
                "line_uid": "line:3",
                "features": {"perso_arabic": {"density": 0.3}},
            },
        ]
        result = _index_features_by_ang(
            feature_records, corpus_records,
        )
        assert len(result[1]) == 2  # two lines on ang 1
        assert len(result[2]) == 1

    def test_missing_ang_skipped(self) -> None:
        corpus_records = [
            {"line_uid": "line:1"},  # no ang field
        ]
        feature_records = [
            {"line_uid": "line:1", "features": {}},
        ]
        result = _index_features_by_ang(
            feature_records, corpus_records,
        )
        assert result == {}


# ---------------------------------------------------------------------------
# Per-ang aggregation tests
# ---------------------------------------------------------------------------


class TestComputeAngDensities:
    """Tests for compute_ang_densities."""

    def test_mean_density_per_ang(
        self, sample_features_by_ang: dict,
    ) -> None:
        results = compute_ang_densities(sample_features_by_ang)
        # Ang 1: mean of [0.1, 0.3] = 0.2 for perso_arabic
        ang1 = next(r for r in results if r.ang == 1)
        assert abs(ang1.densities["perso_arabic"] - 0.2) < 1e-6

    def test_sorted_by_ang(
        self, sample_features_by_ang: dict,
    ) -> None:
        results = compute_ang_densities(sample_features_by_ang)
        angs = [r.ang for r in results]
        assert angs == sorted(angs)

    def test_line_count_correct(
        self, sample_features_by_ang: dict,
    ) -> None:
        results = compute_ang_densities(sample_features_by_ang)
        ang1 = next(r for r in results if r.ang == 1)
        assert ang1.line_count == 2
        ang2 = next(r for r in results if r.ang == 2)
        assert ang2.line_count == 1

    def test_empty_input(self) -> None:
        results = compute_ang_densities({})
        assert results == []

    def test_to_dict(
        self, sample_features_by_ang: dict,
    ) -> None:
        results = compute_ang_densities(sample_features_by_ang)
        d = results[0].to_dict()
        assert "ang" in d
        assert "line_count" in d
        assert "densities" in d


# ---------------------------------------------------------------------------
# Per-raga aggregation tests
# ---------------------------------------------------------------------------


class TestComputeRagaDensities:
    """Tests for compute_raga_densities."""

    def test_raga_aggregation(
        self,
        sample_features_by_ang: dict,
        sample_sections: list[RagaSection],
    ) -> None:
        results = compute_raga_densities(
            sample_features_by_ang, sample_sections,
        )
        assert len(results) == 2

    def test_preamble_line_count(
        self,
        sample_features_by_ang: dict,
        sample_sections: list[RagaSection],
    ) -> None:
        results = compute_raga_densities(
            sample_features_by_ang, sample_sections,
        )
        preamble = next(r for r in results if r.raga_id == "PREAMBLE")
        # Angs 1,2,3 => 2+1+1 = 4 lines
        assert preamble.line_count == 4

    def test_raga_stats_computed(
        self,
        sample_features_by_ang: dict,
        sample_sections: list[RagaSection],
    ) -> None:
        results = compute_raga_densities(
            sample_features_by_ang, sample_sections,
        )
        preamble = next(r for r in results if r.raga_id == "PREAMBLE")
        stats = preamble.stats["perso_arabic"]
        assert "mean" in stats
        assert "median" in stats
        assert "stdev" in stats

    def test_empty_raga_section(
        self, sample_features_by_ang: dict,
    ) -> None:
        """Raga section with no matching angs has zero line count."""
        sections = [
            RagaSection(
                id="EMPTY", romanized="Empty",
                ang_start=100, ang_end=200,
            ),
        ]
        results = compute_raga_densities(
            sample_features_by_ang, sections,
        )
        assert results[0].line_count == 0

    def test_to_dict(
        self,
        sample_features_by_ang: dict,
        sample_sections: list[RagaSection],
    ) -> None:
        results = compute_raga_densities(
            sample_features_by_ang, sample_sections,
        )
        d = results[0].to_dict()
        assert "raga_id" in d
        assert "stats" in d
        assert "line_count" in d


# ---------------------------------------------------------------------------
# Sliding window tests
# ---------------------------------------------------------------------------


class TestComputeSlidingWindow:
    """Tests for compute_sliding_window."""

    def test_basic_window(
        self, sample_features_by_ang: dict,
    ) -> None:
        ang_densities = compute_ang_densities(
            sample_features_by_ang,
        )
        windows = compute_sliding_window(
            ang_densities, window_size=3,
        )
        assert len(windows) > 0

    def test_window_positions(
        self, sample_features_by_ang: dict,
    ) -> None:
        ang_densities = compute_ang_densities(
            sample_features_by_ang,
        )
        windows = compute_sliding_window(
            ang_densities, window_size=3,
        )
        # With angs 1-5 and window=3, should get windows starting at 1,2,3
        starts = [w.window_start for w in windows]
        assert 1 in starts
        assert 3 in starts

    def test_window_end_correct(self) -> None:
        ang_densities = [
            AngDensity(
                ang=i,
                line_count=1,
                densities={dim: 0.0 for dim in FEATURE_DIMENSIONS},
            )
            for i in range(1, 6)
        ]
        windows = compute_sliding_window(
            ang_densities, window_size=3,
        )
        for w in windows:
            assert w.window_end == w.window_start + 2

    def test_single_ang_window(self) -> None:
        ang_densities = [
            AngDensity(
                ang=1,
                line_count=1,
                densities={"perso_arabic": 0.5},
            ),
        ]
        windows = compute_sliding_window(
            ang_densities, window_size=1,
        )
        assert len(windows) == 1
        assert windows[0].densities["perso_arabic"] == 0.5

    def test_empty_input(self) -> None:
        windows = compute_sliding_window([], window_size=5)
        assert windows == []

    def test_window_larger_than_data(self) -> None:
        ang_densities = [
            AngDensity(
                ang=1,
                line_count=1,
                densities={dim: 0.0 for dim in FEATURE_DIMENSIONS},
            ),
        ]
        windows = compute_sliding_window(
            ang_densities, window_size=100,
        )
        # Window is larger than data range, so no windows can fit
        assert windows == []

    def test_to_dict(self) -> None:
        wd = WindowDensity(
            window_start=1,
            window_end=5,
            densities={"perso_arabic": 0.123456789},
        )
        d = wd.to_dict()
        assert d["window_start"] == 1
        assert d["densities"]["perso_arabic"] == 0.123457


# ---------------------------------------------------------------------------
# Batch processing tests
# ---------------------------------------------------------------------------


class TestComputeAllDensityAggregations:
    """Tests for compute_all_density_aggregations."""

    def test_end_to_end(
        self, ragas_yaml: Path,
    ) -> None:
        corpus_records = [
            {"line_uid": "line:1", "ang": 1},
            {"line_uid": "line:2", "ang": 4},
        ]
        feature_records = [
            {
                "line_uid": "line:1",
                "features": {
                    dim: {"density": 0.1 if dim == "perso_arabic" else 0.0}
                    for dim in FEATURE_DIMENSIONS
                },
            },
            {
                "line_uid": "line:2",
                "features": {
                    dim: {"density": 0.2 if dim == "sanskritic" else 0.0}
                    for dim in FEATURE_DIMENSIONS
                },
            },
        ]
        result = compute_all_density_aggregations(
            feature_records, corpus_records, ragas_yaml,
            window_size=3,
        )
        assert "by_ang" in result
        assert "by_raga" in result
        assert "sliding_window" in result

    def test_writes_output(
        self, ragas_yaml: Path, tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "density.json"
        compute_all_density_aggregations(
            [], [], ragas_yaml,
            output_path=output_path,
        )
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "by_ang" in data
        assert "by_raga" in data
        assert "sliding_window" in data
