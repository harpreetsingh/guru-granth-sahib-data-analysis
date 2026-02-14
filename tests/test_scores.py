"""Score computation engine tests (bd-2zi.1).

Tests the scoring pipeline: config parsing, rule evaluation, raw signal,
context signal, combined signal, sigmoid, and end-to-end score computation.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from ggs.analysis.match import MatchRecord
from ggs.analysis.scores import (
    LineContext,
    LineScores,
    ScoringConfig,
    ScoringRule,
    build_line_contexts,
    compute_all_scores,
    compute_raw_signal,
    compute_scores,
    evaluate_rule,
    parse_scoring_config,
    sigmoid,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_tagging_config() -> dict[str, Any]:
    """Minimal tagging config for testing."""
    return {
        "context_weight": 0.2,
        "dimensions": {
            "nirgun": {
                "sigmoid_k": 2.0,
                "sigmoid_x0": 1.5,
                "rules": [
                    {
                        "match_entity": ["WAHEGURU", "NIRANKAR"],
                        "weight": 1.0,
                    },
                    {
                        "match_register": "sanskritic",
                        "weight": 0.3,
                    },
                ],
            },
            "critique_ritual": {
                "sigmoid_k": 2.5,
                "sigmoid_x0": 1.0,
                "rules": [
                    {
                        "match_entity": ["TEERATH"],
                        "weight": 0.5,
                    },
                    {
                        "co_occurs_negation": True,
                        "weight": 1.5,
                    },
                ],
            },
        },
    }


@pytest.fixture()
def simple_config(
    simple_tagging_config: dict[str, Any],
) -> ScoringConfig:
    """Parsed scoring config."""
    return parse_scoring_config(simple_tagging_config)


@pytest.fixture()
def nirgun_line_ctx() -> LineContext:
    """A line with nirgun entity matches."""
    return LineContext(
        line_uid="line:1",
        shabad_uid="shabad:1",
        entity_ids={"WAHEGURU", "NAAM"},
        feature_densities={
            "perso_arabic": 0.0,
            "sanskritic": 0.15,
            "nirgun": 0.2,
            "sagun_narrative": 0.0,
            "ritual": 0.0,
            "cleric": 0.0,
        },
    )


@pytest.fixture()
def neutral_line_ctx() -> LineContext:
    """A line with no entity matches."""
    return LineContext(
        line_uid="line:2",
        shabad_uid="shabad:1",
        entity_ids=set(),
        feature_densities={
            "perso_arabic": 0.0,
            "sanskritic": 0.0,
            "nirgun": 0.0,
            "sagun_narrative": 0.0,
            "ritual": 0.0,
            "cleric": 0.0,
        },
    )


@pytest.fixture()
def ritual_negation_ctx() -> LineContext:
    """A line with ritual + negation co-occurrence."""
    return LineContext(
        line_uid="line:3",
        shabad_uid="shabad:2",
        entity_ids={"TEERATH", "NEG_NOT"},
        feature_densities={
            "perso_arabic": 0.0,
            "sanskritic": 0.0,
            "nirgun": 0.0,
            "sagun_narrative": 0.0,
            "ritual": 0.1,
            "cleric": 0.0,
        },
        has_negation_of_form=True,
        has_negation_cooccurrence=True,
    )


# ---------------------------------------------------------------------------
# Config parsing tests
# ---------------------------------------------------------------------------


class TestParseScoringConfig:
    """Tests for parse_scoring_config."""

    def test_parses_context_weight(
        self, simple_tagging_config: dict,
    ) -> None:
        config = parse_scoring_config(simple_tagging_config)
        assert config.context_weight == 0.2

    def test_parses_dimensions(
        self, simple_tagging_config: dict,
    ) -> None:
        config = parse_scoring_config(simple_tagging_config)
        assert "nirgun" in config.dimensions
        assert "critique_ritual" in config.dimensions

    def test_parses_sigmoid_params(
        self, simple_tagging_config: dict,
    ) -> None:
        config = parse_scoring_config(simple_tagging_config)
        nirgun = config.dimensions["nirgun"]
        assert nirgun.sigmoid_k == 2.0
        assert nirgun.sigmoid_x0 == 1.5

    def test_parses_rules(
        self, simple_tagging_config: dict,
    ) -> None:
        config = parse_scoring_config(simple_tagging_config)
        nirgun = config.dimensions["nirgun"]
        assert len(nirgun.rules) == 2
        assert nirgun.rules[0].weight == 1.0
        assert nirgun.rules[0].match_entity == (
            "WAHEGURU", "NIRANKAR",
        )

    def test_defaults_for_missing_fields(self) -> None:
        config = parse_scoring_config({})
        assert config.context_weight == 0.2
        assert config.dimensions == {}

    def test_string_entity_becomes_tuple(self) -> None:
        tagging = {
            "dimensions": {
                "dim": {
                    "rules": [
                        {"match_entity": "HARI", "weight": 1.0},
                    ],
                },
            },
        }
        config = parse_scoring_config(tagging)
        rule = config.dimensions["dim"].rules[0]
        assert rule.match_entity == ("HARI",)


# ---------------------------------------------------------------------------
# Sigmoid tests
# ---------------------------------------------------------------------------


class TestSigmoid:
    """Tests for the sigmoid function."""

    def test_midpoint_gives_half(self) -> None:
        # sigmoid(x0, k, x0) = 0.5
        result = sigmoid(1.5, 2.0, 1.5)
        assert abs(result - 0.5) < 1e-10

    def test_large_positive_input(self) -> None:
        # Well above x0 => close to 1
        result = sigmoid(10.0, 2.0, 1.5)
        assert result > 0.99

    def test_large_negative_input(self) -> None:
        # Well below x0 => close to 0
        result = sigmoid(-10.0, 2.0, 1.5)
        assert result < 0.01

    def test_zero_input_with_defaults(self) -> None:
        # sigmoid(0, 2.0, 1.5) = 1 / (1 + exp(3)) ~ 0.047
        result = sigmoid(0.0, 2.0, 1.5)
        expected = 1.0 / (1.0 + math.exp(3.0))
        assert abs(result - expected) < 1e-10

    def test_steeper_k(self) -> None:
        # Higher k => sharper transition
        gentle = sigmoid(2.0, 1.0, 1.5)
        steep = sigmoid(2.0, 5.0, 1.5)
        # Both above 0.5, but steep should be closer to 1
        assert steep > gentle

    def test_no_overflow_extreme_positive(self) -> None:
        result = sigmoid(1000.0, 2.0, 1.5)
        assert result == 1.0

    def test_no_overflow_extreme_negative(self) -> None:
        result = sigmoid(-1000.0, 2.0, 1.5)
        assert result == 0.0

    def test_bounded_zero_to_one(self) -> None:
        for x in [-100, -10, -1, 0, 0.5, 1, 1.5, 2, 10, 100]:
            result = sigmoid(x, 2.0, 1.5)
            assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# Rule evaluation tests
# ---------------------------------------------------------------------------


class TestEvaluateRule:
    """Tests for evaluate_rule."""

    def test_match_entity_fires(
        self, nirgun_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=1.0, match_entity=("WAHEGURU",))
        assert evaluate_rule(rule, nirgun_line_ctx) == 1.0

    def test_match_entity_no_match(
        self, nirgun_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=1.0, match_entity=("ALLAH",))
        assert evaluate_rule(rule, nirgun_line_ctx) == 0.0

    def test_match_register_fires(
        self, nirgun_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=0.3, match_register="sanskritic")
        assert evaluate_rule(rule, nirgun_line_ctx) == 0.3

    def test_match_register_zero_density(
        self, nirgun_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=0.3, match_register="perso_arabic")
        assert evaluate_rule(rule, nirgun_line_ctx) == 0.0

    def test_negation_of_form_fires(self) -> None:
        ctx = LineContext(
            line_uid="test",
            shabad_uid=None,
            has_negation_of_form=True,
        )
        rule = ScoringRule(weight=0.8, has_negation_of_form=True)
        assert evaluate_rule(rule, ctx) == 0.8

    def test_negation_of_form_not_present(
        self, neutral_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=0.8, has_negation_of_form=True)
        assert evaluate_rule(rule, neutral_line_ctx) == 0.0

    def test_co_occurs_negation_fires(
        self, ritual_negation_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=1.5, co_occurs_negation=True)
        assert evaluate_rule(rule, ritual_negation_ctx) == 1.5

    def test_no_condition_returns_zero(
        self, nirgun_line_ctx: LineContext,
    ) -> None:
        rule = ScoringRule(weight=1.0)
        assert evaluate_rule(rule, nirgun_line_ctx) == 0.0


# ---------------------------------------------------------------------------
# Raw signal tests
# ---------------------------------------------------------------------------


class TestComputeRawSignal:
    """Tests for compute_raw_signal."""

    def test_sums_multiple_rules(
        self, simple_config: ScoringConfig,
        nirgun_line_ctx: LineContext,
    ) -> None:
        dim = simple_config.dimensions["nirgun"]
        raw = compute_raw_signal(dim, nirgun_line_ctx)
        # Rule 1: WAHEGURU match => 1.0
        # Rule 2: sanskritic density > 0 => 0.3
        assert abs(raw - 1.3) < 1e-10

    def test_zero_when_no_rules_fire(
        self, simple_config: ScoringConfig,
        neutral_line_ctx: LineContext,
    ) -> None:
        dim = simple_config.dimensions["nirgun"]
        raw = compute_raw_signal(dim, neutral_line_ctx)
        assert raw == 0.0

    def test_ritual_critique_with_negation(
        self, simple_config: ScoringConfig,
        ritual_negation_ctx: LineContext,
    ) -> None:
        dim = simple_config.dimensions["critique_ritual"]
        raw = compute_raw_signal(dim, ritual_negation_ctx)
        # Rule 1: TEERATH match => 0.5
        # Rule 2: co_occurs_negation => 1.5
        assert abs(raw - 2.0) < 1e-10


# ---------------------------------------------------------------------------
# Score computation tests
# ---------------------------------------------------------------------------


class TestComputeScores:
    """Tests for compute_scores."""

    def test_basic_scoring(
        self, simple_config: ScoringConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        assert len(results) == 1
        assert "nirgun" in results[0].scores

    def test_scores_bounded_zero_to_one(
        self, simple_config: ScoringConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU", "NIRANKAR"},
                feature_densities={"sanskritic": 0.5},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        for dim_name, score in results[0].scores.items():
            assert 0.0 <= score <= 1.0, (
                f"Score for {dim_name} out of bounds: {score}"
            )

    def test_context_signal_from_neighbors(
        self, simple_config: ScoringConfig,
    ) -> None:
        """Lines in same shabad share context signals."""
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
            LineContext(
                line_uid="line:2",
                shabad_uid="shabad:1",
                entity_ids=set(),
                feature_densities={"sanskritic": 0.0},
            ),
        ]
        results = compute_scores(contexts, simple_config)

        # line:2 has no entities, but its context_signal should reflect
        # that it's in a shabad where line:1 has WAHEGURU
        assert results[1].context_signals["nirgun"] > 0.0

    def test_no_context_for_single_line_shabad(
        self, simple_config: ScoringConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        # Only 1 line in shabad — no meaningful context from neighbors,
        # so context signal is 0 (same behavior as no shabad)
        assert results[0].context_signals["nirgun"] == 0.0

    def test_no_shabad_means_no_context(
        self, simple_config: ScoringConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid=None,
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        assert results[0].context_signals["nirgun"] == 0.0

    def test_combined_signal_formula(
        self, simple_config: ScoringConfig,
    ) -> None:
        """combined = (1 - cw) * raw + cw * context."""
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid=None,
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        r = results[0]
        cw = simple_config.context_weight
        for dim in simple_config.dimensions:
            expected = (
                (1 - cw) * r.raw_signals[dim]
                + cw * r.context_signals[dim]
            )
            assert abs(r.combined_signals[dim] - expected) < 1e-10

    def test_line_scores_to_dict(
        self, simple_config: ScoringConfig,
    ) -> None:
        contexts = [
            LineContext(
                line_uid="line:1",
                shabad_uid="shabad:1",
                entity_ids={"WAHEGURU"},
                feature_densities={"sanskritic": 0.1},
            ),
        ]
        results = compute_scores(contexts, simple_config)
        d = results[0].to_dict()
        assert d["line_uid"] == "line:1"
        assert "scores" in d
        assert "raw_signals" in d
        assert "context_signals" in d
        assert "combined_signals" in d


# ---------------------------------------------------------------------------
# Build line contexts tests
# ---------------------------------------------------------------------------


class TestBuildLineContexts:
    """Tests for build_line_contexts."""

    def test_builds_contexts_from_inputs(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "meta": {"shabad_uid": "shabad:1"},
            },
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 7],
            ),
        ]
        features = [
            {
                "line_uid": "line:1",
                "features": {
                    "perso_arabic": {"density": 0.0},
                    "sanskritic": {"density": 0.1},
                    "nirgun": {"density": 0.2},
                    "sagun_narrative": {"density": 0.0},
                    "ritual": {"density": 0.0},
                    "cleric": {"density": 0.0},
                },
            },
        ]
        contexts = build_line_contexts(records, matches, features)
        assert len(contexts) == 1
        assert "WAHEGURU" in contexts[0].entity_ids
        assert contexts[0].shabad_uid == "shabad:1"
        assert contexts[0].feature_densities["sanskritic"] == 0.1

    def test_excludes_nested_matches(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 1, "meta": {}},
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="SATNAM",
                matched_form="ਸਤਿ ਨਾਮੁ",
                span=[0, 8],
            ),
            MatchRecord(
                line_uid="line:1",
                entity_id="NAAM",
                matched_form="ਨਾਮੁ",
                span=[4, 8],
                nested_in="SATNAM",
            ),
        ]
        features = [{"line_uid": "line:1", "features": {}}]
        contexts = build_line_contexts(records, matches, features)
        assert "SATNAM" in contexts[0].entity_ids
        assert "NAAM" not in contexts[0].entity_ids

    def test_fallback_shabad_from_ang(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 42, "meta": {}},
        ]
        contexts = build_line_contexts(records, [], [])
        assert contexts[0].shabad_uid == "ang:42"


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestComputeAllScores:
    """Tests for compute_all_scores."""

    def test_end_to_end(
        self, simple_tagging_config: dict,
    ) -> None:
        records = [
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
        ]
        matches = [
            MatchRecord(
                line_uid="line:1",
                entity_id="WAHEGURU",
                matched_form="ਵਾਹਿਗੁਰੂ",
                span=[0, 7],
            ),
        ]
        features = [
            {
                "line_uid": "line:1",
                "features": {
                    "sanskritic": {"density": 0.1},
                },
            },
            {
                "line_uid": "line:2",
                "features": {},
            },
        ]
        results = compute_all_scores(
            records, matches, features, simple_tagging_config,
        )
        assert len(results) == 2
        assert all(isinstance(r, LineScores) for r in results)
        # Line 1 should have higher nirgun score than line 2
        assert (
            results[0].scores["nirgun"]
            > results[1].scores["nirgun"]
        )

    def test_empty_inputs(
        self, simple_tagging_config: dict,
    ) -> None:
        results = compute_all_scores(
            [], [], [], simple_tagging_config,
        )
        assert results == []
