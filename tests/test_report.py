"""Phase 1 reports and aggregates tests (bd-4i2.7).

Tests entity counting, ang bucket grouping, raga-level counts,
normalized metrics, CSV generation, and JSON aggregates.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import yaml

from ggs.analysis.match import MatchRecord
from ggs.lexicon.loader import LexiconIndex, load_lexicon
from ggs.output.report import (
    _ang_bucket,
    _normalize_per_k_lines,
    _normalize_per_k_tokens,
    count_entities,
    count_entities_by_ang_bucket,
    count_entities_by_raga,
    count_unique_lines,
    generate_aggregates_json,
    generate_entity_counts_by_bucket_csv,
    generate_entity_counts_by_raga_csv,
    generate_entity_counts_csv,
    generate_phase1_reports,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_matches() -> list[MatchRecord]:
    """Match records for testing."""
    return [
        MatchRecord(
            line_uid="line:1", entity_id="HARI",
            matched_form="ਹਰਿ", span=[0, 3],
        ),
        MatchRecord(
            line_uid="line:1", entity_id="NAAM",
            matched_form="ਨਾਮੁ", span=[4, 8],
        ),
        MatchRecord(
            line_uid="line:2", entity_id="HARI",
            matched_form="ਹਰਿ", span=[0, 3],
        ),
        MatchRecord(
            line_uid="line:3", entity_id="ALLAH",
            matched_form="ਅਲਾਹੁ", span=[0, 5],
        ),
        # Nested match — should be excluded
        MatchRecord(
            line_uid="line:1", entity_id="NAAM",
            matched_form="ਨਾਮੁ", span=[4, 8],
            nested_in="SATNAM",
        ),
    ]


@pytest.fixture()
def sample_records() -> list[dict[str, Any]]:
    """Corpus records for testing."""
    return [
        {
            "line_uid": "line:1", "ang": 1,
            "tokens": ["ਹਰਿ", "ਨਾਮੁ", "ਜਪ"],
        },
        {
            "line_uid": "line:2", "ang": 50,
            "tokens": ["ਹਰਿ", "ਜਪ"],
        },
        {
            "line_uid": "line:3", "ang": 725,
            "tokens": ["ਅਲਾਹੁ", "ਅਲਖ", "ਜਪ"],
        },
    ]


@pytest.fixture()
def test_index() -> LexiconIndex:
    """Load the test fixture lexicon."""
    paths = {"test": "tests/fixtures/lexicon/test_entities.yaml"}
    return load_lexicon(paths, base_dir=Path("."))


@pytest.fixture()
def ragas_yaml(tmp_path: Path) -> Path:
    """Create a minimal ragas.yaml for testing."""
    data = {
        "preamble": {
            "romanized": "Preamble",
            "ang_start": 1,
            "ang_end": 13,
        },
        "ragas": [
            {
                "id": "SRI",
                "romanized": "Sri Raag",
                "ang_start": 14,
                "ang_end": 93,
            },
            {
                "id": "TILANG",
                "romanized": "Raag Tilang",
                "ang_start": 721,
                "ang_end": 727,
            },
        ],
        "epilogue": {
            "romanized": "Epilogue",
            "ang_start": 1354,
            "ang_end": 1430,
        },
    }
    path = tmp_path / "ragas.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Ang bucket tests
# ---------------------------------------------------------------------------


class TestAngBucket:
    """Tests for _ang_bucket."""

    def test_first_bucket(self) -> None:
        assert _ang_bucket(1) == "1-100"
        assert _ang_bucket(50) == "1-100"
        assert _ang_bucket(100) == "1-100"

    def test_second_bucket(self) -> None:
        assert _ang_bucket(101) == "101-200"
        assert _ang_bucket(200) == "101-200"

    def test_last_bucket(self) -> None:
        assert _ang_bucket(1430) == "1401-1500"


# ---------------------------------------------------------------------------
# Entity counting tests
# ---------------------------------------------------------------------------


class TestCountEntities:
    """Tests for count_entities."""

    def test_counts_correctly(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        counts = count_entities(sample_matches)
        assert counts["HARI"] == 2
        assert counts["ALLAH"] == 1

    def test_excludes_nested(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        counts = count_entities(sample_matches)
        # NAAM appears twice: once normal, once nested
        assert counts["NAAM"] == 1

    def test_empty_matches(self) -> None:
        counts = count_entities([])
        assert counts == {}


class TestCountUniqueLines:
    """Tests for count_unique_lines."""

    def test_unique_line_count(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        unique = count_unique_lines(sample_matches)
        assert unique["HARI"] == 2  # line:1 and line:2
        assert unique["ALLAH"] == 1


class TestCountEntitiesByAngBucket:
    """Tests for count_entities_by_ang_bucket."""

    def test_bucket_grouping(
        self, sample_matches: list[MatchRecord],
    ) -> None:
        line_to_ang = {
            "line:1": 1, "line:2": 50, "line:3": 725,
        }
        counts = count_entities_by_ang_bucket(
            sample_matches, line_to_ang,
        )
        assert counts["HARI"]["1-100"] == 2
        assert counts["ALLAH"]["701-800"] == 1


class TestCountEntitiesByRaga:
    """Tests for count_entities_by_raga."""

    def test_raga_grouping(
        self,
        sample_matches: list[MatchRecord],
        ragas_yaml: Path,
    ) -> None:
        from ggs.analysis.density import load_raga_sections
        line_to_ang = {
            "line:1": 1, "line:2": 50, "line:3": 725,
        }
        sections = load_raga_sections(ragas_yaml)
        counts = count_entities_by_raga(
            sample_matches, line_to_ang, sections,
        )
        assert counts["HARI"]["PREAMBLE"] == 1  # ang 1
        assert counts["HARI"]["SRI"] == 1  # ang 50
        assert counts["ALLAH"]["TILANG"] == 1  # ang 725


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------


class TestNormalization:
    """Tests for _normalize_per_k_lines and _normalize_per_k_tokens."""

    def test_per_1000_lines(self) -> None:
        result = _normalize_per_k_lines(50, 10000, k=1000)
        assert abs(result - 5.0) < 1e-6

    def test_per_10000_tokens(self) -> None:
        result = _normalize_per_k_tokens(50, 100000, k=10000)
        assert abs(result - 5.0) < 1e-6

    def test_zero_total_lines(self) -> None:
        assert _normalize_per_k_lines(10, 0) == 0.0

    def test_zero_total_tokens(self) -> None:
        assert _normalize_per_k_tokens(10, 0) == 0.0


# ---------------------------------------------------------------------------
# CSV generation tests
# ---------------------------------------------------------------------------


class TestGenerateCSVs:
    """Tests for CSV generators."""

    def test_entity_counts_csv(
        self, test_index: LexiconIndex,
    ) -> None:
        entity_counts = {"NAAM": 100, "HUKAM": 50}
        unique_lines = {"NAAM": 80, "HUKAM": 40}
        csv_text = generate_entity_counts_csv(
            entity_counts, unique_lines, 1000, 50000, test_index,
        )
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 2
        # Sorted by count descending
        assert rows[0]["entity_id"] == "NAAM"
        assert rows[0]["count"] == "100"
        assert rows[0]["per_1000_lines"] == "100.0"

    def test_entity_counts_by_bucket_csv(self) -> None:
        counts = {
            "HARI": {"1-100": 10, "101-200": 5},
            "ALLAH": {"701-800": 3},
        }
        csv_text = generate_entity_counts_by_bucket_csv(counts)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 3

    def test_entity_counts_by_raga_csv(self) -> None:
        counts = {
            "HARI": {"SRI": 10, "TILANG": 5},
        }
        csv_text = generate_entity_counts_by_raga_csv(counts)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["raga_id"] in ("SRI", "TILANG")


# ---------------------------------------------------------------------------
# JSON aggregates tests
# ---------------------------------------------------------------------------


class TestGenerateAggregatesJson:
    """Tests for generate_aggregates_json."""

    def test_summary(
        self, test_index: LexiconIndex,
    ) -> None:
        entity_counts = {"NAAM": 100}
        agg = generate_aggregates_json(
            entity_counts, {"NAAM": 80}, {}, {},
            1000, 50000, test_index,
        )
        assert agg["summary"]["total_entities_matched"] == 1
        assert agg["summary"]["total_match_count"] == 100

    def test_top_entities_capped_at_50(
        self, test_index: LexiconIndex,
    ) -> None:
        # Create 60 entities
        entity_counts = {f"E{i}": i for i in range(60)}
        agg = generate_aggregates_json(
            entity_counts, {}, {}, {},
            1000, 50000, test_index,
        )
        assert len(agg["top_entities"]) == 50


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestGeneratePhase1Reports:
    """Tests for generate_phase1_reports."""

    def test_end_to_end(
        self,
        sample_matches: list[MatchRecord],
        sample_records: list[dict],
        test_index: LexiconIndex,
        ragas_yaml: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "reports"
        aggregates = generate_phase1_reports(
            sample_matches, sample_records,
            test_index, ragas_yaml,
            output_dir=output_dir,
        )
        assert "summary" in aggregates
        assert (output_dir / "entity_counts.csv").exists()
        assert (output_dir / "entity_counts_by_ang_bucket.csv").exists()
        assert (output_dir / "entity_counts_by_raga.csv").exists()
        assert (output_dir / "aggregates.json").exists()

    def test_empty_inputs(
        self,
        test_index: LexiconIndex,
        ragas_yaml: Path,
    ) -> None:
        aggregates = generate_phase1_reports(
            [], [], test_index, ragas_yaml,
        )
        assert aggregates["summary"]["total_match_count"] == 0
