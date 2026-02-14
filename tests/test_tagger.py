"""Tagger tests (bd-2zi.3, bd-2zi.4, bd-3jj.7).

Tests tag generation pipeline: threshold parsing, category derivation,
evidence collection, distribution reports, detailed distribution breakdowns,
sensitivity analysis, end-to-end tagging, threshold boundary cases, and
precise score computation verification.
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from ggs.analysis.match import MatchRecord
from ggs.analysis.scores import (
    DimensionConfig,
    LineContext,
    LineScores,
    ScoringConfig,
    ScoringRule,
)
from ggs.analysis.tagger import (
    RuleFiring,
    TagRecord,
    ThresholdConfig,
    _ang_bucket,
    collect_evidence,
    derive_primary_tag,
    derive_secondary_tags,
    generate_detailed_distribution,
    generate_distribution_csv,
    generate_tags,
    parse_threshold_config,
    rederive_tags,
    run_sensitivity_analysis,
    run_tagger,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_thresholds() -> ThresholdConfig:
    """Default threshold configuration."""
    return ThresholdConfig()


@pytest.fixture()
def simple_scoring_config() -> ScoringConfig:
    """A minimal scoring config for testing."""
    return ScoringConfig(
        context_weight=0.0,
        dimensions={
            "nirgun": DimensionConfig(
                name="nirgun",
                sigmoid_k=2.0,
                sigmoid_x0=1.5,
                rules=(
                    ScoringRule(
                        weight=1.0,
                        match_entity=("WAHEGURU",),
                    ),
                ),
            ),
            "sagun_narrative": DimensionConfig(
                name="sagun_narrative",
                sigmoid_k=2.0,
                sigmoid_x0=1.5,
                rules=(
                    ScoringRule(
                        weight=1.0,
                        match_entity=("RAM_NARRATIVE",),
                    ),
                ),
            ),
            "critique_ritual": DimensionConfig(
                name="critique_ritual",
                sigmoid_k=2.5,
                sigmoid_x0=1.0,
                rules=(
                    ScoringRule(
                        weight=1.5,
                        co_occurs_negation=True,
                    ),
                ),
            ),
        },
    )


@pytest.fixture()
def tagging_config() -> dict[str, Any]:
    """Minimal tagging config dict for end-to-end tests."""
    return {
        "context_weight": 0.0,
        "dimensions": {
            "nirgun": {
                "sigmoid_k": 2.0,
                "sigmoid_x0": 1.5,
                "rules": [
                    {"match_entity": ["WAHEGURU"], "weight": 1.0},
                ],
            },
            "sagun_narrative": {
                "sigmoid_k": 2.0,
                "sigmoid_x0": 1.5,
                "rules": [
                    {"match_entity": ["RAM_NARRATIVE"], "weight": 1.0},
                ],
            },
        },
        "thresholds": {
            "nirgun_leaning": {
                "nirgun_min": 0.6,
                "sagun_max": 0.3,
            },
            "sagun_narrative_leaning": {
                "sagun_min": 0.6,
                "nirgun_max": 0.3,
            },
            "mixed": {
                "difference_max": 0.3,
                "both_min": 0.2,
            },
            "universalism": {"min": 0.5},
            "critique_ritual": {"min": 0.5},
            "critique_clerics": {"min": 0.5},
        },
    }


# ---------------------------------------------------------------------------
# Threshold config parsing tests
# ---------------------------------------------------------------------------


class TestParseThresholdConfig:
    """Tests for parse_threshold_config."""

    def test_parses_defaults(self) -> None:
        config = parse_threshold_config({})
        assert config.nirgun_min == 0.6
        assert config.sagun_max_for_nirgun == 0.3

    def test_parses_custom_values(self) -> None:
        config = parse_threshold_config({
            "nirgun_leaning": {
                "nirgun_min": 0.7,
                "sagun_max": 0.2,
            },
        })
        assert config.nirgun_min == 0.7
        assert config.sagun_max_for_nirgun == 0.2

    def test_parses_all_sections(self) -> None:
        config = parse_threshold_config({
            "nirgun_leaning": {
                "nirgun_min": 0.6,
                "sagun_max": 0.3,
            },
            "sagun_narrative_leaning": {
                "sagun_min": 0.6,
                "nirgun_max": 0.3,
            },
            "mixed": {
                "difference_max": 0.3,
                "both_min": 0.2,
            },
            "universalism": {"min": 0.5},
            "critique_ritual": {"min": 0.5},
            "critique_clerics": {"min": 0.5},
        })
        assert config.universalism_min == 0.5
        assert config.critique_ritual_min == 0.5
        assert config.critique_clerics_min == 0.5


# ---------------------------------------------------------------------------
# Category derivation tests
# ---------------------------------------------------------------------------


class TestDerivePrimaryTag:
    """Tests for derive_primary_tag."""

    def test_nirgun_leaning(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"nirgun": 0.8, "sagun_narrative": 0.1}
        tag = derive_primary_tag(scores, default_thresholds)
        assert tag == "nirgun_leaning"

    def test_sagun_narrative_leaning(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"nirgun": 0.1, "sagun_narrative": 0.8}
        tag = derive_primary_tag(scores, default_thresholds)
        assert tag == "sagun_narrative_leaning"

    def test_mixed(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"nirgun": 0.4, "sagun_narrative": 0.4}
        tag = derive_primary_tag(scores, default_thresholds)
        assert tag == "mixed"

    def test_unclassified_low_scores(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"nirgun": 0.1, "sagun_narrative": 0.1}
        tag = derive_primary_tag(scores, default_thresholds)
        assert tag is None

    def test_nirgun_takes_priority_over_mixed(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        # This is nirgun_leaning because nirgun >= 0.6 and sagun < 0.3
        scores = {"nirgun": 0.7, "sagun_narrative": 0.2}
        tag = derive_primary_tag(scores, default_thresholds)
        assert tag == "nirgun_leaning"

    def test_empty_scores(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        tag = derive_primary_tag({}, default_thresholds)
        assert tag is None


class TestDeriveSecondaryTags:
    """Tests for derive_secondary_tags."""

    def test_universalism(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"universalism": 0.7}
        tags = derive_secondary_tags(scores, default_thresholds)
        assert "universalism" in tags

    def test_critique_ritual(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"critique_ritual": 0.8}
        tags = derive_secondary_tags(scores, default_thresholds)
        assert "critique_ritual" in tags

    def test_critique_clerics(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {"critique_clerics": 0.6}
        tags = derive_secondary_tags(scores, default_thresholds)
        assert "critique_clerics" in tags

    def test_multiple_secondary_tags(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {
            "universalism": 0.7,
            "critique_ritual": 0.8,
            "critique_clerics": 0.6,
        }
        tags = derive_secondary_tags(scores, default_thresholds)
        assert len(tags) == 3

    def test_no_secondary_tags(
        self, default_thresholds: ThresholdConfig,
    ) -> None:
        scores = {
            "universalism": 0.1,
            "critique_ritual": 0.2,
            "critique_clerics": 0.1,
        }
        tags = derive_secondary_tags(scores, default_thresholds)
        assert tags == []


# ---------------------------------------------------------------------------
# Evidence collection tests
# ---------------------------------------------------------------------------


class TestCollectEvidence:
    """Tests for collect_evidence."""

    def test_collects_entity_match_evidence(
        self, simple_scoring_config: ScoringConfig,
    ) -> None:
        ctx = LineContext(
            line_uid="line:1",
            shabad_uid="shabad:1",
            entity_ids={"WAHEGURU"},
        )
        ls = LineScores(
            line_uid="line:1",
            shabad_uid="shabad:1",
            raw_signals={"nirgun": 1.0},
            context_signals={"nirgun": 0.0},
            combined_signals={"nirgun": 1.0},
            scores={"nirgun": 0.7},
        )
        matches_by_line = {
            "line:1": [
                MatchRecord(
                    line_uid="line:1",
                    entity_id="WAHEGURU",
                    matched_form="ਵਾਹਿਗੁਰੂ",
                    span=[0, 9],
                ),
            ],
        }

        rules_fired, evidence_tokens, breakdown = collect_evidence(
            ls, ctx, simple_scoring_config, matches_by_line,
        )
        assert "match_entity:WAHEGURU" in rules_fired
        assert "ਵਾਹਿਗੁਰੂ" in evidence_tokens
        assert len(breakdown["nirgun"]) == 1

    def test_no_rules_fired(
        self, simple_scoring_config: ScoringConfig,
    ) -> None:
        ctx = LineContext(
            line_uid="line:1",
            shabad_uid="shabad:1",
            entity_ids=set(),
        )
        ls = LineScores(
            line_uid="line:1",
            shabad_uid="shabad:1",
            raw_signals={},
            context_signals={},
            combined_signals={},
            scores={},
        )
        rules_fired, evidence_tokens, _breakdown = collect_evidence(
            ls, ctx, simple_scoring_config, {},
        )
        assert rules_fired == []
        assert evidence_tokens == []

    def test_deduplicates_evidence(
        self, simple_scoring_config: ScoringConfig,
    ) -> None:
        # Same entity referenced by multiple dimensions
        ctx = LineContext(
            line_uid="line:1",
            shabad_uid="shabad:1",
            entity_ids={"WAHEGURU"},
        )
        ls = LineScores(
            line_uid="line:1",
            shabad_uid="shabad:1",
            raw_signals={},
            context_signals={},
            combined_signals={},
            scores={},
        )
        matches_by_line = {
            "line:1": [
                MatchRecord(
                    line_uid="line:1",
                    entity_id="WAHEGURU",
                    matched_form="ਵਾਹਿਗੁਰੂ",
                    span=[0, 9],
                ),
            ],
        }
        _rules_fired, evidence_tokens, _ = collect_evidence(
            ls, ctx, simple_scoring_config, matches_by_line,
        )
        # Evidence token appears only once even if the same match
        # is relevant to multiple rules
        assert evidence_tokens.count("ਵਾਹਿਗੁਰੂ") == 1


# ---------------------------------------------------------------------------
# RuleFiring serialization tests
# ---------------------------------------------------------------------------


class TestRuleFiringSerialization:
    """Tests for RuleFiring.to_dict."""

    def test_to_dict(self) -> None:
        rf = RuleFiring(
            rule="match_entity:WAHEGURU",
            weight=1.0,
            matched="ਵਾਹਿਗੁਰੂ",
        )
        d = rf.to_dict()
        assert d["rule"] == "match_entity:WAHEGURU"
        assert d["weight"] == 1.0
        assert d["matched"] == "ਵਾਹਿਗੁਰੂ"


# ---------------------------------------------------------------------------
# TagRecord serialization tests
# ---------------------------------------------------------------------------


class TestTagRecordSerialization:
    """Tests for TagRecord.to_dict."""

    def test_to_dict(self) -> None:
        tag = TagRecord(
            line_uid="line:1",
            scores={"nirgun": 0.8, "sagun_narrative": 0.1},
            primary_tag="nirgun_leaning",
            secondary_tags=["critique_ritual"],
            rules_fired=["match_entity:WAHEGURU"],
            evidence_tokens=["ਵਾਹਿਗੁਰੂ"],
            score_breakdown={
                "nirgun": [
                    RuleFiring(
                        rule="match_entity:WAHEGURU",
                        weight=1.0,
                        matched="ਵਾਹਿਗੁਰੂ",
                    ),
                ],
                "sagun_narrative": [],
            },
        )
        d = tag.to_dict()
        assert d["line_uid"] == "line:1"
        assert d["primary_tag"] == "nirgun_leaning"
        assert d["secondary_tags"] == ["critique_ritual"]
        assert d["rules_fired"] == ["match_entity:WAHEGURU"]
        assert "nirgun" in d["score_breakdown"]
        # Empty dimensions are excluded
        assert "sagun_narrative" not in d["score_breakdown"]

    def test_none_primary_tag(self) -> None:
        tag = TagRecord(
            line_uid="line:1",
            scores={},
            primary_tag=None,
            secondary_tags=[],
            rules_fired=[],
            evidence_tokens=[],
            score_breakdown={},
        )
        d = tag.to_dict()
        assert d["primary_tag"] is None

    def test_metadata_in_dict(self) -> None:
        tag = TagRecord(
            line_uid="line:1",
            scores={},
            primary_tag=None,
            secondary_tags=[],
            rules_fired=[],
            evidence_tokens=[],
            score_breakdown={},
            ang=42,
            author="Guru Nanak",
            raga="Sri",
        )
        d = tag.to_dict()
        assert d["ang"] == 42
        assert d["author"] == "Guru Nanak"
        assert d["raga"] == "Sri"

    def test_metadata_defaults(self) -> None:
        tag = TagRecord(
            line_uid="line:1",
            scores={},
            primary_tag=None,
            secondary_tags=[],
            rules_fired=[],
            evidence_tokens=[],
            score_breakdown={},
        )
        assert tag.ang == 0
        assert tag.author == ""
        assert tag.raga == ""


# ---------------------------------------------------------------------------
# Tag generation tests
# ---------------------------------------------------------------------------


class TestGenerateTags:
    """Tests for generate_tags."""

    def test_basic_tag_generation(
        self,
        simple_scoring_config: ScoringConfig,
        default_thresholds: ThresholdConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
            ),
        ]
        line_scores = [
            LineScores(
                line_uid="line:1",
                shabad_uid="shabad:1",
                raw_signals={"nirgun": 1.0},
                context_signals={"nirgun": 0.0},
                combined_signals={"nirgun": 1.0},
                scores={"nirgun": 0.73, "sagun_narrative": 0.1},
            ),
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 9],
            ),
        ]

        tags = generate_tags(
            line_scores, contexts, simple_scoring_config,
            default_thresholds, matches,
        )
        assert len(tags) == 1
        assert tags[0].primary_tag == "nirgun_leaning"

    def test_empty_inputs(
        self,
        simple_scoring_config: ScoringConfig,
        default_thresholds: ThresholdConfig,
    ) -> None:
        tags = generate_tags(
            [], [], simple_scoring_config,
            default_thresholds, [],
        )
        assert tags == []

    def test_unclassified_line(
        self,
        simple_scoring_config: ScoringConfig,
        default_thresholds: ThresholdConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
            ),
        ]
        line_scores = [
            LineScores(
                line_uid="line:1",
                shabad_uid="shabad:1",
                raw_signals={},
                context_signals={},
                combined_signals={},
                scores={"nirgun": 0.1, "sagun_narrative": 0.1},
            ),
        ]
        tags = generate_tags(
            line_scores, contexts, simple_scoring_config,
            default_thresholds, [],
        )
        assert tags[0].primary_tag is None

    def test_passes_through_metadata(
        self,
        simple_scoring_config: ScoringConfig,
        default_thresholds: ThresholdConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
            ),
        ]
        line_scores = [
            LineScores(
                line_uid="line:1",
                shabad_uid="shabad:1",
                raw_signals={},
                context_signals={},
                combined_signals={},
                scores={"nirgun": 0.73, "sagun_narrative": 0.1},
            ),
        ]
        records = [
            {
                "line_uid": "line:1",
                "ang": 42,
                "meta": {
                    "author": "Guru Nanak",
                    "raga": "Sri",
                },
            },
        ]
        tags = generate_tags(
            line_scores, contexts, simple_scoring_config,
            default_thresholds, [], records,
        )
        assert tags[0].ang == 42
        assert tags[0].author == "Guru Nanak"
        assert tags[0].raga == "Sri"

    def test_metadata_defaults_without_records(
        self,
        simple_scoring_config: ScoringConfig,
        default_thresholds: ThresholdConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
            ),
        ]
        line_scores = [
            LineScores(
                line_uid="line:1",
                shabad_uid="shabad:1",
                raw_signals={},
                context_signals={},
                combined_signals={},
                scores={"nirgun": 0.1, "sagun_narrative": 0.1},
            ),
        ]
        tags = generate_tags(
            line_scores, contexts, simple_scoring_config,
            default_thresholds, [],
        )
        assert tags[0].ang == 0
        assert tags[0].author == ""
        assert tags[0].raga == ""


# ---------------------------------------------------------------------------
# Distribution CSV tests
# ---------------------------------------------------------------------------


class TestGenerateDistributionCsv:
    """Tests for generate_distribution_csv."""

    def test_basic_distribution(self) -> None:
        tags = [
            TagRecord(
                line_uid=f"line:{i}",
                scores={},
                primary_tag="nirgun_leaning",
                secondary_tags=[],
                rules_fired=[],
                evidence_tokens=[],
                score_breakdown={},
            )
            for i in range(3)
        ]
        tags.append(
            TagRecord(
                line_uid="line:99",
                scores={},
                primary_tag=None,
                secondary_tags=[],
                rules_fired=[],
                evidence_tokens=[],
                score_breakdown={},
            ),
        )

        csv_text = generate_distribution_csv(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 2  # nirgun_leaning + unclassified

        nirgun_row = next(
            r for r in rows if r["primary_tag"] == "nirgun_leaning"
        )
        assert nirgun_row["count"] == "3"
        assert nirgun_row["percentage"] == "75.0"

    def test_empty_tags(self) -> None:
        csv_text = generate_distribution_csv([])
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 0


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestRunTagger:
    """Tests for run_tagger end-to-end pipeline."""

    def test_end_to_end(
        self,
        tagging_config: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "meta": {"shabad_uid": "shabad:1"},
                "tokens": ["ਵਾਹਿਗੁਰੂ", "ਸਤਿ"],
            },
            {
                "line_uid": "line:2",
                "ang": 1,
                "meta": {"shabad_uid": "shabad:1"},
                "tokens": ["ਰਾਮ", "ਕਹਾਣੀ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 9],
            ),
            MatchRecord(
                line_uid="line:2",
                entity_id="RAM_NARRATIVE",
                matched_form="ਰਾਮ",
                span=[0, 3],
            ),
        ]
        features = [
            {"line_uid": "line:1", "features": {}},
            {"line_uid": "line:2", "features": {}},
        ]

        output_dir = tmp_path / "tags"
        tags = run_tagger(
            records, matches, features,
            tagging_config,
            output_dir=output_dir,
        )

        assert len(tags) == 2
        assert (output_dir / "tags.jsonl").exists()
        assert (output_dir / "nirgun_sagun_distribution.csv").exists()

        # Verify JSONL format
        with (output_dir / "tags.jsonl").open() as fh:
            lines = fh.readlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert "line_uid" in first
        assert "scores" in first
        assert "primary_tag" in first

    def test_empty_corpus(
        self,
        tagging_config: dict[str, Any],
    ) -> None:
        tags = run_tagger([], [], [], tagging_config)
        assert tags == []

    def test_no_output_dir(
        self,
        tagging_config: dict[str, Any],
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "meta": {"shabad_uid": "shabad:1"},
                "tokens": ["ਸਤਿ"],
            },
        ]
        tags = run_tagger(
            records, [], [{"line_uid": "line:1", "features": {}}],
            tagging_config,
        )
        assert len(tags) == 1

    def test_writes_detailed_distribution(
        self,
        tagging_config: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "meta": {
                    "shabad_uid": "shabad:1",
                    "author": "Guru Nanak",
                    "raga": "Sri",
                },
                "tokens": ["ਵਾਹਿਗੁਰੂ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 9],
            ),
        ]
        features = [{"line_uid": "line:1", "features": {}}]
        output_dir = tmp_path / "tags"

        run_tagger(
            records, matches, features,
            tagging_config,
            output_dir=output_dir,
        )

        detailed_path = (
            output_dir / "nirgun_sagun_distribution_detailed.csv"
        )
        assert detailed_path.exists()
        csv_text = detailed_path.read_text(encoding="utf-8")
        assert "group_type" in csv_text
        assert "author" in csv_text

    def test_metadata_populated_in_tags(
        self,
        tagging_config: dict[str, Any],
    ) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 42,
                "meta": {
                    "shabad_uid": "shabad:1",
                    "author": "Guru Nanak",
                    "raga": "Sri",
                },
                "tokens": ["ਵਾਹਿਗੁਰੂ"],
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 9],
            ),
        ]
        features = [{"line_uid": "line:1", "features": {}}]

        tags = run_tagger(
            records, matches, features, tagging_config,
        )
        assert tags[0].ang == 42
        assert tags[0].author == "Guru Nanak"
        assert tags[0].raga == "Sri"


# ---------------------------------------------------------------------------
# Ang bucket tests (bd-2zi.4)
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

    def test_custom_bucket_size(self) -> None:
        assert _ang_bucket(1, bucket_size=50) == "1-50"
        assert _ang_bucket(51, bucket_size=50) == "51-100"

    def test_zero_ang(self) -> None:
        assert _ang_bucket(0) == "unknown"

    def test_negative_ang(self) -> None:
        assert _ang_bucket(-1) == "unknown"


# ---------------------------------------------------------------------------
# Detailed distribution tests (bd-2zi.4)
# ---------------------------------------------------------------------------


class TestGenerateDetailedDistribution:
    """Tests for generate_detailed_distribution."""

    def _make_tag(
        self,
        line_uid: str,
        primary_tag: str | None,
        ang: int = 1,
        author: str = "",
        raga: str = "",
    ) -> TagRecord:
        return TagRecord(
            line_uid=line_uid,
            scores={},
            primary_tag=primary_tag,
            secondary_tags=[],
            rules_fired=[],
            evidence_tokens=[],
            score_breakdown={},
            ang=ang,
            author=author,
            raga=raga,
        )

    def test_empty_tags(self) -> None:
        csv_text = generate_detailed_distribution([])
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 0

    def test_overall_grouping(self) -> None:
        tags = [
            self._make_tag("line:1", "nirgun_leaning"),
            self._make_tag("line:2", "nirgun_leaning"),
            self._make_tag("line:3", None),
        ]
        csv_text = generate_detailed_distribution(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        overall_rows = [
            r for r in rows if r["group_type"] == "overall"
        ]
        assert len(overall_rows) == 2  # nirgun_leaning + unclassified

        nirgun_row = next(
            r for r in overall_rows
            if r["primary_tag"] == "nirgun_leaning"
        )
        assert nirgun_row["count"] == "2"
        assert float(nirgun_row["percentage"]) == pytest.approx(
            66.67, abs=0.01,
        )

    def test_author_grouping(self) -> None:
        tags = [
            self._make_tag(
                "line:1", "nirgun_leaning", author="Guru Nanak",
            ),
            self._make_tag(
                "line:2", "nirgun_leaning", author="Guru Nanak",
            ),
            self._make_tag(
                "line:3", "mixed", author="Kabir",
            ),
        ]
        csv_text = generate_detailed_distribution(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        nanak_rows = [
            r for r in rows
            if r["group_type"] == "author"
            and r["group_value"] == "Guru Nanak"
        ]
        assert len(nanak_rows) == 1
        assert nanak_rows[0]["primary_tag"] == "nirgun_leaning"
        assert nanak_rows[0]["count"] == "2"
        assert nanak_rows[0]["percentage"] == "100.0"

        kabir_rows = [
            r for r in rows
            if r["group_type"] == "author"
            and r["group_value"] == "Kabir"
        ]
        assert len(kabir_rows) == 1
        assert kabir_rows[0]["primary_tag"] == "mixed"

    def test_raga_grouping(self) -> None:
        tags = [
            self._make_tag("line:1", "nirgun_leaning", raga="Sri"),
            self._make_tag("line:2", "mixed", raga="Asa"),
        ]
        csv_text = generate_detailed_distribution(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        raga_rows = [
            r for r in rows if r["group_type"] == "raga"
        ]
        raga_values = {r["group_value"] for r in raga_rows}
        assert "Sri" in raga_values
        assert "Asa" in raga_values

    def test_ang_bucket_grouping(self) -> None:
        tags = [
            self._make_tag("line:1", "nirgun_leaning", ang=1),
            self._make_tag("line:2", "nirgun_leaning", ang=50),
            self._make_tag("line:3", "mixed", ang=150),
        ]
        csv_text = generate_detailed_distribution(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        bucket_rows = [
            r for r in rows if r["group_type"] == "ang_bucket"
        ]
        bucket_values = {r["group_value"] for r in bucket_rows}
        assert "1-100" in bucket_values
        assert "101-200" in bucket_values

        # First bucket has 2 nirgun_leaning lines
        first_bucket = [
            r for r in bucket_rows
            if r["group_value"] == "1-100"
        ]
        assert len(first_bucket) == 1
        assert first_bucket[0]["count"] == "2"

    def test_unknown_metadata(self) -> None:
        tags = [
            self._make_tag("line:1", "nirgun_leaning"),
        ]
        csv_text = generate_detailed_distribution(tags)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        author_rows = [
            r for r in rows if r["group_type"] == "author"
        ]
        assert any(
            r["group_value"] == "unknown" for r in author_rows
        )

    def test_custom_bucket_size(self) -> None:
        tags = [
            self._make_tag("line:1", "nirgun_leaning", ang=1),
            self._make_tag("line:2", "nirgun_leaning", ang=51),
        ]
        csv_text = generate_detailed_distribution(tags, bucket_size=50)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        bucket_rows = [
            r for r in rows if r["group_type"] == "ang_bucket"
        ]
        bucket_values = {r["group_value"] for r in bucket_rows}
        assert "1-50" in bucket_values
        assert "51-100" in bucket_values


# ---------------------------------------------------------------------------
# Sensitivity analysis tests (bd-2zi.4)
# ---------------------------------------------------------------------------


class TestRederiveTags:
    """Tests for rederive_tags."""

    def _make_tag(
        self,
        line_uid: str,
        scores: dict[str, float],
        primary_tag: str | None = None,
        ang: int = 1,
        author: str = "",
        raga: str = "",
    ) -> TagRecord:
        return TagRecord(
            line_uid=line_uid,
            scores=scores,
            primary_tag=primary_tag,
            secondary_tags=[],
            rules_fired=["some_rule"],
            evidence_tokens=["some_evidence"],
            score_breakdown={},
            ang=ang,
            author=author,
            raga=raga,
        )

    def test_rederive_changes_tags(self) -> None:
        # With default thresholds, nirgun=0.55 is NOT nirgun_leaning
        # (needs >= 0.6)
        original = [
            self._make_tag(
                "line:1",
                {"nirgun": 0.55, "sagun_narrative": 0.1},
                primary_tag=None,
            ),
        ]

        # With lower threshold, it becomes nirgun_leaning
        loose = ThresholdConfig(nirgun_min=0.5, sagun_max_for_nirgun=0.3)
        rederived = rederive_tags(original, loose)

        assert rederived[0].primary_tag == "nirgun_leaning"

    def test_preserves_scores(self) -> None:
        original = [
            self._make_tag(
                "line:1",
                {"nirgun": 0.8, "sagun_narrative": 0.1},
            ),
        ]
        rederived = rederive_tags(original, ThresholdConfig())
        assert rederived[0].scores == original[0].scores

    def test_preserves_evidence(self) -> None:
        original = [
            self._make_tag(
                "line:1",
                {"nirgun": 0.8, "sagun_narrative": 0.1},
            ),
        ]
        rederived = rederive_tags(original, ThresholdConfig())
        assert rederived[0].rules_fired == original[0].rules_fired
        assert rederived[0].evidence_tokens == original[0].evidence_tokens

    def test_preserves_metadata(self) -> None:
        original = [
            self._make_tag(
                "line:1",
                {"nirgun": 0.8, "sagun_narrative": 0.1},
                ang=42,
                author="Guru Nanak",
                raga="Sri",
            ),
        ]
        rederived = rederive_tags(original, ThresholdConfig())
        assert rederived[0].ang == 42
        assert rederived[0].author == "Guru Nanak"
        assert rederived[0].raga == "Sri"

    def test_rederive_secondary_tags(self) -> None:
        original = [
            self._make_tag(
                "line:1",
                {
                    "nirgun": 0.8,
                    "sagun_narrative": 0.1,
                    "universalism": 0.45,
                },
            ),
        ]
        # Default threshold: universalism_min=0.5 -> not a secondary
        strict = rederive_tags(original, ThresholdConfig())
        assert "universalism" not in strict[0].secondary_tags

        # Lower threshold: universalism_min=0.4 -> is a secondary
        loose = ThresholdConfig(universalism_min=0.4)
        rederived = rederive_tags(original, loose)
        assert "universalism" in rederived[0].secondary_tags

    def test_empty_tags(self) -> None:
        rederived = rederive_tags([], ThresholdConfig())
        assert rederived == []


class TestRunSensitivityAnalysis:
    """Tests for run_sensitivity_analysis."""

    def test_basic_sensitivity(self) -> None:
        tags = [
            TagRecord(
                line_uid="line:1",
                scores={"nirgun": 0.55, "sagun_narrative": 0.1},
                primary_tag=None,
                secondary_tags=[],
                rules_fired=[],
                evidence_tokens=[],
                score_breakdown={},
            ),
        ]
        variants = {
            "strict": ThresholdConfig(nirgun_min=0.6),
            "loose": ThresholdConfig(nirgun_min=0.5),
        }
        results = run_sensitivity_analysis(tags, variants)

        assert "strict" in results
        assert "loose" in results
        assert results["strict"][0].primary_tag is None
        assert results["loose"][0].primary_tag == "nirgun_leaning"

    def test_empty_variants(self) -> None:
        tags = [
            TagRecord(
                line_uid="line:1",
                scores={},
                primary_tag=None,
                secondary_tags=[],
                rules_fired=[],
                evidence_tokens=[],
                score_breakdown={},
            ),
        ]
        results = run_sensitivity_analysis(tags, {})
        assert results == {}

    def test_multiple_variants_consistent(self) -> None:
        tags = [
            TagRecord(
                line_uid="line:1",
                scores={"nirgun": 0.8, "sagun_narrative": 0.1},
                primary_tag=None,
                secondary_tags=[],
                rules_fired=[],
                evidence_tokens=[],
                score_breakdown={},
            ),
        ]
        variants = {
            "v1": ThresholdConfig(nirgun_min=0.6),
            "v2": ThresholdConfig(nirgun_min=0.7),
            "v3": ThresholdConfig(nirgun_min=0.9),
        }
        results = run_sensitivity_analysis(tags, variants)

        # With nirgun=0.8: v1 and v2 should classify, v3 should not
        assert results["v1"][0].primary_tag == "nirgun_leaning"
        assert results["v2"][0].primary_tag == "nirgun_leaning"
        assert results["v3"][0].primary_tag is None


# ---------------------------------------------------------------------------
# Category derivation with custom thresholds (bd-2zi.4)
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """Tests for category derivation with non-default thresholds."""

    def test_stricter_nirgun_threshold(self) -> None:
        strict = ThresholdConfig(nirgun_min=0.9, sagun_max_for_nirgun=0.1)
        scores = {"nirgun": 0.85, "sagun_narrative": 0.05}
        # 0.85 < 0.9 -> not nirgun_leaning
        assert derive_primary_tag(scores, strict) is None

    def test_looser_nirgun_threshold(self) -> None:
        loose = ThresholdConfig(nirgun_min=0.4, sagun_max_for_nirgun=0.5)
        scores = {"nirgun": 0.45, "sagun_narrative": 0.3}
        assert derive_primary_tag(scores, loose) == "nirgun_leaning"

    def test_mixed_with_tight_difference(self) -> None:
        tight = ThresholdConfig(
            mixed_difference_max=0.1,
            mixed_both_min=0.3,
        )
        # Difference is 0.15 > 0.1 -> not mixed
        scores = {"nirgun": 0.45, "sagun_narrative": 0.3}
        tag = derive_primary_tag(scores, tight)
        assert tag != "mixed"

    def test_mixed_with_loose_difference(self) -> None:
        loose = ThresholdConfig(
            mixed_difference_max=0.5,
            mixed_both_min=0.1,
        )
        scores = {"nirgun": 0.4, "sagun_narrative": 0.15}
        tag = derive_primary_tag(scores, loose)
        assert tag == "mixed"

    def test_secondary_tag_threshold_variation(self) -> None:
        strict = ThresholdConfig(universalism_min=0.8)
        loose = ThresholdConfig(universalism_min=0.3)
        scores = {"universalism": 0.5}

        strict_tags = derive_secondary_tags(scores, strict)
        loose_tags = derive_secondary_tags(scores, loose)

        assert "universalism" not in strict_tags
        assert "universalism" in loose_tags


# ---------------------------------------------------------------------------
# Threshold boundary tests (bd-3jj.7)
# ---------------------------------------------------------------------------


class TestThresholdBoundaries:
    """Boundary tests for category derivation thresholds.

    The default thresholds (nirgun_min=0.6, sagun_max=0.3,
    universalism_min=0.5, etc.) create category boundaries.
    These tests verify correct behavior at scores just above,
    just below, and exactly at each boundary.
    """

    # -- nirgun_min = 0.6 boundary --

    def test_nirgun_exactly_at_threshold(self) -> None:
        """nirgun == 0.6 (exactly at boundary) -> nirgun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.6, "sagun_narrative": 0.1}
        assert derive_primary_tag(scores, config) == "nirgun_leaning"

    def test_nirgun_just_below_threshold(self) -> None:
        """nirgun == 0.5999 (just below boundary) -> NOT nirgun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.5999, "sagun_narrative": 0.1}
        assert derive_primary_tag(scores, config) != "nirgun_leaning"

    def test_nirgun_just_above_threshold(self) -> None:
        """nirgun == 0.6001 (just above boundary) -> nirgun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.6001, "sagun_narrative": 0.1}
        assert derive_primary_tag(scores, config) == "nirgun_leaning"

    # -- sagun_max_for_nirgun = 0.3 boundary --

    def test_sagun_exactly_at_max_for_nirgun(self) -> None:
        """sagun == 0.3 (exactly at boundary) -> NOT nirgun_leaning.

        The condition is sagun < 0.3 (strict less-than), so 0.3
        should disqualify nirgun_leaning.
        """
        config = ThresholdConfig()
        scores = {"nirgun": 0.8, "sagun_narrative": 0.3}
        assert derive_primary_tag(scores, config) != "nirgun_leaning"

    def test_sagun_just_below_max_for_nirgun(self) -> None:
        """sagun == 0.2999 (just below 0.3) -> nirgun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.8, "sagun_narrative": 0.2999}
        assert derive_primary_tag(scores, config) == "nirgun_leaning"

    def test_sagun_just_above_max_for_nirgun(self) -> None:
        """sagun == 0.3001 -> NOT nirgun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.8, "sagun_narrative": 0.3001}
        assert derive_primary_tag(scores, config) != "nirgun_leaning"

    # -- sagun_min = 0.6 boundary --

    def test_sagun_exactly_at_threshold(self) -> None:
        """sagun == 0.6 (exactly at boundary) -> sagun_narrative_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.1, "sagun_narrative": 0.6}
        assert (
            derive_primary_tag(scores, config)
            == "sagun_narrative_leaning"
        )

    def test_sagun_just_below_threshold(self) -> None:
        """sagun == 0.5999 (just below boundary) -> NOT sagun_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.1, "sagun_narrative": 0.5999}
        assert (
            derive_primary_tag(scores, config)
            != "sagun_narrative_leaning"
        )

    # -- nirgun_max_for_sagun = 0.3 boundary --

    def test_nirgun_exactly_at_max_for_sagun(self) -> None:
        """nirgun == 0.3 (exactly at boundary) -> NOT sagun_leaning.

        The condition is nirgun < 0.3, so 0.3 disqualifies.
        """
        config = ThresholdConfig()
        scores = {"nirgun": 0.3, "sagun_narrative": 0.8}
        assert (
            derive_primary_tag(scores, config)
            != "sagun_narrative_leaning"
        )

    def test_nirgun_just_below_max_for_sagun(self) -> None:
        """nirgun == 0.2999 -> sagun_narrative_leaning."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.2999, "sagun_narrative": 0.8}
        assert (
            derive_primary_tag(scores, config)
            == "sagun_narrative_leaning"
        )

    # -- mixed_both_min = 0.2 boundary --

    def test_mixed_both_exactly_at_min(self) -> None:
        """Both scores == 0.2 -> mixed (>= 0.2 threshold)."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.2, "sagun_narrative": 0.2}
        assert derive_primary_tag(scores, config) == "mixed"

    def test_mixed_one_just_below_min(self) -> None:
        """One score just below 0.2 -> NOT mixed."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.1999, "sagun_narrative": 0.2}
        assert derive_primary_tag(scores, config) != "mixed"

    # -- mixed_difference_max = 0.3 boundary --

    def test_mixed_difference_exactly_at_max(self) -> None:
        """Difference == 0.3 -> mixed (abs <= 0.3)."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.5, "sagun_narrative": 0.2}
        assert derive_primary_tag(scores, config) == "mixed"

    def test_mixed_difference_just_above_max(self) -> None:
        """Difference == 0.3001 -> NOT mixed."""
        config = ThresholdConfig()
        scores = {"nirgun": 0.5001, "sagun_narrative": 0.2}
        assert derive_primary_tag(scores, config) != "mixed"

    # -- universalism_min = 0.5 boundary --

    def test_universalism_exactly_at_threshold(self) -> None:
        """universalism == 0.5 -> secondary tag assigned."""
        config = ThresholdConfig()
        scores = {"universalism": 0.5}
        tags = derive_secondary_tags(scores, config)
        assert "universalism" in tags

    def test_universalism_just_below_threshold(self) -> None:
        """universalism == 0.4999 -> no secondary tag."""
        config = ThresholdConfig()
        scores = {"universalism": 0.4999}
        tags = derive_secondary_tags(scores, config)
        assert "universalism" not in tags

    # -- critique_ritual_min = 0.5 boundary --

    def test_critique_ritual_exactly_at_threshold(self) -> None:
        """critique_ritual == 0.5 -> secondary tag assigned."""
        config = ThresholdConfig()
        scores = {"critique_ritual": 0.5}
        tags = derive_secondary_tags(scores, config)
        assert "critique_ritual" in tags

    def test_critique_ritual_just_below_threshold(self) -> None:
        """critique_ritual == 0.4999 -> no secondary tag."""
        config = ThresholdConfig()
        scores = {"critique_ritual": 0.4999}
        tags = derive_secondary_tags(scores, config)
        assert "critique_ritual" not in tags

    # -- critique_clerics_min = 0.5 boundary --

    def test_critique_clerics_exactly_at_threshold(self) -> None:
        """critique_clerics == 0.5 -> secondary tag assigned."""
        config = ThresholdConfig()
        scores = {"critique_clerics": 0.5}
        tags = derive_secondary_tags(scores, config)
        assert "critique_clerics" in tags

    def test_critique_clerics_just_below_threshold(self) -> None:
        """critique_clerics == 0.4999 -> no secondary tag."""
        config = ThresholdConfig()
        scores = {"critique_clerics": 0.4999}
        tags = derive_secondary_tags(scores, config)
        assert "critique_clerics" not in tags


# ---------------------------------------------------------------------------
# Precise score computation tests (bd-3jj.7)
# ---------------------------------------------------------------------------


class TestPreciseScoreComputation:
    """Tests verifying exact numerical results from the scoring pipeline.

    Given known rule weights, sigmoid parameters, and context weights,
    the expected output can be computed analytically and verified.
    """

    def test_known_rules_produce_expected_sigmoid(self) -> None:
        """Verify the full scoring formula with known inputs.

        Setup:
          - Dimension: nirgun, sigmoid_k=2.0, sigmoid_x0=1.5
          - Rule: match_entity:WAHEGURU, weight=1.0
          - Context weight: 0.0 (no context blending)
          - Line has entity WAHEGURU

        Expected:
          raw_signal = 1.0 (one rule fires, weight 1.0)
          context_signal = 0.0 (only one line in shabad)
          combined = (1 - 0) * 1.0 + 0 * 0 = 1.0
          score = sigmoid(1.0, k=2.0, x0=1.5)
                = 1 / (1 + exp(-2.0 * (1.0 - 1.5)))
                = 1 / (1 + exp(1.0))
                = 1 / (1 + 2.71828...)
                ~ 0.2689
        """
        import math

        config = ScoringConfig(
            context_weight=0.0,
            dimensions={
                "nirgun": DimensionConfig(
                    name="nirgun",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("WAHEGURU",),
                        ),
                    ),
                ),
            },
        )
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
            ),
        ]
        from ggs.analysis.scores import compute_scores

        results = compute_scores(contexts, config)

        expected_raw = 1.0
        expected_context = 0.0
        expected_combined = 1.0
        expected_score = 1.0 / (1.0 + math.exp(1.0))

        assert results[0].raw_signals["nirgun"] == expected_raw
        assert results[0].context_signals["nirgun"] == expected_context
        assert results[0].combined_signals["nirgun"] == expected_combined
        assert abs(
            results[0].scores["nirgun"] - expected_score,
        ) < 1e-10

    def test_two_rules_both_fire_cumulative_weight(self) -> None:
        """Two rules fire -> raw = sum of weights -> sigmoid of sum.

        Setup:
          - Rule 1: match_entity:WAHEGURU, weight=1.0
          - Rule 2: match_register:sanskritic, weight=0.5
          - k=2.0, x0=1.5, context_weight=0.0
          - Line has WAHEGURU + sanskritic density > 0

        Expected:
          raw = 1.0 + 0.5 = 1.5
          combined = 1.5 (no context)
          score = sigmoid(1.5, 2.0, 1.5) = 0.5 (midpoint)
        """
        config = ScoringConfig(
            context_weight=0.0,
            dimensions={
                "nirgun": DimensionConfig(
                    name="nirgun",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("WAHEGURU",),
                        ),
                        ScoringRule(
                            weight=0.5,
                            match_register="sanskritic",
                        ),
                    ),
                ),
            },
        )
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.3},
            ),
        ]
        from ggs.analysis.scores import compute_scores

        results = compute_scores(contexts, config)

        assert abs(results[0].raw_signals["nirgun"] - 1.5) < 1e-10
        assert abs(results[0].scores["nirgun"] - 0.5) < 1e-10

    def test_context_signal_precise_value(self) -> None:
        """Verify context signal = mean of raw signals in shabad.

        Setup:
          - 3 lines in same shabad
          - Line 1: WAHEGURU match -> raw=1.0
          - Line 2: no match -> raw=0.0
          - Line 3: WAHEGURU match -> raw=1.0
          - context_weight=0.5

        Expected for each line:
          context_signal = mean(1.0, 0.0, 1.0) = 2/3

        For line 2 (no entity):
          combined = (1 - 0.5) * 0.0 + 0.5 * (2/3) = 1/3
          score = sigmoid(1/3, k=2.0, x0=1.5)
        """
        import math

        config = ScoringConfig(
            context_weight=0.5,
            dimensions={
                "nirgun": DimensionConfig(
                    name="nirgun",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("WAHEGURU",),
                        ),
                    ),
                ),
            },
        )
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
            ),
            LineContext(
                line_uid="line:2",
                shabad_uid="shabad:1",
                entity_ids=set(),
            ),
            LineContext(
                line_uid="line:3",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
            ),
        ]
        from ggs.analysis.scores import compute_scores

        results = compute_scores(contexts, config)

        expected_context = 2.0 / 3.0
        for r in results:
            assert abs(
                r.context_signals["nirgun"] - expected_context,
            ) < 1e-10

        # Line 2 (no entity): combined = 0.5 * 0 + 0.5 * (2/3) = 1/3
        line2 = results[1]
        expected_combined = 1.0 / 3.0
        expected_score = 1.0 / (
            1.0 + math.exp(-2.0 * (expected_combined - 1.5))
        )
        assert abs(
            line2.combined_signals["nirgun"] - expected_combined,
        ) < 1e-10
        assert abs(
            line2.scores["nirgun"] - expected_score,
        ) < 1e-10

    def test_no_rules_fire_all_scores_near_zero(self) -> None:
        """Line with no matches -> raw=0 -> sigmoid near 0.

        sigmoid(0, k=2.0, x0=1.5) = 1/(1+exp(3)) ~ 0.047
        This is the "no-signal" baseline.
        """
        import math

        config = ScoringConfig(
            context_weight=0.0,
            dimensions={
                "nirgun": DimensionConfig(
                    name="nirgun",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("WAHEGURU",),
                        ),
                    ),
                ),
                "sagun_narrative": DimensionConfig(
                    name="sagun_narrative",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("RAM_NARRATIVE",),
                        ),
                    ),
                ),
            },
        )
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids=set(),
            ),
        ]
        from ggs.analysis.scores import compute_scores

        results = compute_scores(contexts, config)

        expected = 1.0 / (1.0 + math.exp(3.0))
        for dim in ("nirgun", "sagun_narrative"):
            assert results[0].raw_signals[dim] == 0.0
            assert abs(results[0].scores[dim] - expected) < 1e-10
            assert results[0].scores[dim] < 0.05

    def test_end_to_end_scoring_to_tag(self) -> None:
        """Full pipeline: known weights -> sigmoid -> category derivation.

        Setup:
          - nirgun rules fire with combined raw = 2.5
          - sigmoid(2.5, k=2.0, x0=1.5) = 1/(1+exp(-2.0)) ~ 0.8808
          - sagun rules: nothing fires -> sigmoid(0) ~ 0.0474
          - Result: nirgun=0.8808 > 0.6, sagun=0.0474 < 0.3
          - -> nirgun_leaning
        """
        import math

        config = ScoringConfig(
            context_weight=0.0,
            dimensions={
                "nirgun": DimensionConfig(
                    name="nirgun",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.5,
                            match_entity=("WAHEGURU",),
                        ),
                        ScoringRule(
                            weight=1.0,
                            match_register="sanskritic",
                        ),
                    ),
                ),
                "sagun_narrative": DimensionConfig(
                    name="sagun_narrative",
                    sigmoid_k=2.0,
                    sigmoid_x0=1.5,
                    rules=(
                        ScoringRule(
                            weight=1.0,
                            match_entity=("RAM_NARRATIVE",),
                        ),
                    ),
                ),
            },
        )
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.2},
            ),
        ]
        from ggs.analysis.scores import compute_scores

        results = compute_scores(contexts, config)

        # nirgun: raw = 1.5 + 1.0 = 2.5
        assert abs(results[0].raw_signals["nirgun"] - 2.5) < 1e-10

        expected_nirgun = 1.0 / (1.0 + math.exp(-2.0 * (2.5 - 1.5)))
        assert abs(
            results[0].scores["nirgun"] - expected_nirgun,
        ) < 1e-10
        assert expected_nirgun > 0.6  # nirgun_leaning threshold

        expected_sagun = 1.0 / (1.0 + math.exp(3.0))
        assert abs(
            results[0].scores["sagun_narrative"] - expected_sagun,
        ) < 1e-10
        assert expected_sagun < 0.3  # sagun max for nirgun_leaning

        # Derive category
        tag = derive_primary_tag(
            results[0].scores, ThresholdConfig(),
        )
        assert tag == "nirgun_leaning"
