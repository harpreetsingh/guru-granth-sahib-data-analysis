"""Score computation engine — raw + context + sigmoid (bd-2zi.1).

Converts Phase 1 matches and Phase 2 features into continuous dimension
scores per line, following the formula from PLAN.md Section 6.1:

    raw_signal(D, L)     = sum of weights for all rules that fire on L for D
    context_signal(D, L) = mean(raw_signal(D, neighbor)) for neighbors in shabad
    combined(D, L)       = (1 - context_weight) * raw + context_weight * context
    score(D, L)          = sigmoid(combined(D, L))

    sigmoid(x) = 1 / (1 + exp(-k * (x - x0)))

Each dimension (nirgun, sagun_narrative, critique_ritual, etc.) has its own
rule set with weights, and its own sigmoid parameters (k, x0).
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from ggs.analysis.features import FEATURE_DIMENSIONS
from ggs.analysis.match import MatchRecord

_console = Console()


# ---------------------------------------------------------------------------
# Configuration data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScoringRule:
    """A single scoring rule for a dimension.

    Exactly one condition field should be set. The ``weight`` is added to the
    raw signal when the condition fires.

    Attributes:
        weight: Signal weight added when this rule fires.
        match_entity: Entity IDs that trigger this rule.
        match_register: Register name whose density triggers this rule.
        has_negation_of_form: If True, rule fires when negation-of-form
            pattern is detected on the line.
        co_occurs_negation: If True, rule fires when ritual+negation
            co-occurrence is detected on the line.
    """

    weight: float
    match_entity: tuple[str, ...] = ()
    match_register: str | None = None
    has_negation_of_form: bool = False
    co_occurs_negation: bool = False


@dataclass(frozen=True, slots=True)
class DimensionConfig:
    """Configuration for a single scoring dimension.

    Attributes:
        name: Dimension name (e.g. ``"nirgun"``).
        sigmoid_k: Steepness of the sigmoid curve.
        sigmoid_x0: Midpoint of the sigmoid curve.
        rules: Ordered list of scoring rules.
    """

    name: str
    sigmoid_k: float
    sigmoid_x0: float
    rules: tuple[ScoringRule, ...]


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Full scoring configuration parsed from config.yaml.

    Attributes:
        context_weight: Weight for shabad-level context signal (0-1).
        dimensions: All dimension configs keyed by name.
    """

    context_weight: float
    dimensions: dict[str, DimensionConfig]


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


def parse_scoring_config(
    tagging_config: dict[str, Any],
) -> ScoringConfig:
    """Parse the ``tagging`` section of config.yaml into typed config.

    Args:
        tagging_config: The ``tagging`` dict from config.yaml.

    Returns:
        A :class:`ScoringConfig` instance.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    context_weight = float(
        tagging_config.get("context_weight", 0.2),
    )

    raw_dimensions = tagging_config.get("dimensions", {})
    dimensions: dict[str, DimensionConfig] = {}

    for dim_name, dim_conf in raw_dimensions.items():
        sigmoid_k = float(dim_conf.get("sigmoid_k", 2.0))
        sigmoid_x0 = float(dim_conf.get("sigmoid_x0", 1.5))

        rules: list[ScoringRule] = []
        for raw_rule in dim_conf.get("rules", []):
            weight = float(raw_rule.get("weight", 0.0))

            match_entity = raw_rule.get("match_entity", [])
            if isinstance(match_entity, str):
                match_entity = [match_entity]

            rules.append(
                ScoringRule(
                    weight=weight,
                    match_entity=tuple(match_entity),
                    match_register=raw_rule.get(
                        "match_register",
                    ),
                    has_negation_of_form=bool(
                        raw_rule.get("has_negation_of_form", False),
                    ),
                    co_occurs_negation=bool(
                        raw_rule.get("co_occurs_negation", False),
                    ),
                ),
            )

        dimensions[dim_name] = DimensionConfig(
            name=dim_name,
            sigmoid_k=sigmoid_k,
            sigmoid_x0=sigmoid_x0,
            rules=tuple(rules),
        )

    return ScoringConfig(
        context_weight=context_weight,
        dimensions=dimensions,
    )


# ---------------------------------------------------------------------------
# Sigmoid function
# ---------------------------------------------------------------------------


def sigmoid(x: float, k: float, x0: float) -> float:
    """Compute sigmoid function: 1 / (1 + exp(-k * (x - x0))).

    Args:
        x: Input value.
        k: Steepness parameter.
        x0: Midpoint parameter.

    Returns:
        Value in (0, 1).
    """
    z = -k * (x - x0)
    # Clamp to avoid overflow in exp()
    if z > 500:
        return 0.0
    if z < -500:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


# ---------------------------------------------------------------------------
# Line context for rule evaluation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LineContext:
    """Pre-computed context for a single line used during rule evaluation.

    Attributes:
        line_uid: UID of the line.
        shabad_uid: UID of the containing shabad (may be None).
        entity_ids: Set of non-nested entity IDs matched on this line.
        feature_densities: Mapping from feature dimension to density value.
        has_negation_of_form: Whether negation-of-form pattern is detected.
        has_negation_cooccurrence: Whether ritual+negation co-occurrence
            is detected.
    """

    line_uid: str
    shabad_uid: str | None
    entity_ids: set[str] = field(default_factory=set)
    feature_densities: dict[str, float] = field(default_factory=dict)
    has_negation_of_form: bool = False
    has_negation_cooccurrence: bool = False


def build_line_contexts(
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    features: list[dict[str, Any]],
) -> list[LineContext]:
    """Build LineContext objects from corpus records, matches, and features.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: Match records from the matching engine.
        features: Feature records from the feature computation engine.

    Returns:
        List of LineContext objects in corpus order.
    """
    # Index matches by line_uid
    matches_by_line: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.nested_in is not None:
            continue
        matches_by_line[m.line_uid].add(m.entity_id)

    # Index features by line_uid
    features_by_line: dict[str, dict[str, float]] = {}
    for feat in features:
        densities: dict[str, float] = {}
        for dim in FEATURE_DIMENSIONS:
            densities[dim] = feat.get("features", {}).get(
                dim, {},
            ).get("density", 0.0)
        features_by_line[feat["line_uid"]] = densities

    # Detect negation patterns per line
    negation_entity_ids = _detect_negation_entities(matches)
    ritual_entity_ids = _detect_ritual_entities(matches)

    negation_lines = _lines_with_entities(matches, negation_entity_ids)
    ritual_lines = _lines_with_entities(matches, ritual_entity_ids)

    contexts: list[LineContext] = []
    for rec in records:
        line_uid = rec.get("line_uid", "UNKNOWN")
        shabad_uid = rec.get("meta", {}).get("shabad_uid")
        if shabad_uid is None:
            ang = rec.get("ang")
            if ang is not None:
                shabad_uid = f"ang:{ang}"

        entity_ids = matches_by_line.get(line_uid, set())
        densities = features_by_line.get(
            line_uid, {dim: 0.0 for dim in FEATURE_DIMENSIONS},
        )

        # Negation-of-form: this line has negation entities
        has_negation = line_uid in negation_lines

        # Ritual+negation co-occurrence: this line has both
        has_ritual_negation = (
            line_uid in negation_lines
            and line_uid in ritual_lines
        )

        contexts.append(
            LineContext(
                line_uid=line_uid,
                shabad_uid=shabad_uid,
                entity_ids=entity_ids,
                feature_densities=densities,
                has_negation_of_form=has_negation,
                has_negation_cooccurrence=has_ritual_negation,
            ),
        )

    return contexts


def _detect_negation_entities(
    matches: list[MatchRecord],
) -> set[str]:
    """Identify entity IDs that look like negation entities.

    Uses a heuristic: entities with 'NEGATION' in their ID or belonging
    to a negation category.
    """
    negation_ids: set[str] = set()
    for m in matches:
        if "NEGATION" in m.entity_id.upper() or "NEG_" in m.entity_id.upper():
            negation_ids.add(m.entity_id)
    return negation_ids


def _detect_ritual_entities(
    matches: list[MatchRecord],
) -> set[str]:
    """Identify entity IDs that look like ritual entities.

    Uses a heuristic: entities with 'RITUAL' or 'TEERATH' or 'POOJA'
    in their ID.
    """
    ritual_ids: set[str] = set()
    ritual_markers = {"RITUAL", "TEERATH", "POOJA", "JANEYU", "TILAK"}
    for m in matches:
        for marker in ritual_markers:
            if marker in m.entity_id.upper():
                ritual_ids.add(m.entity_id)
                break
    return ritual_ids


def _lines_with_entities(
    matches: list[MatchRecord],
    entity_ids: set[str],
) -> set[str]:
    """Return line_uids that contain at least one of the given entities."""
    lines: set[str] = set()
    for m in matches:
        if m.entity_id in entity_ids and m.nested_in is None:
            lines.add(m.line_uid)
    return lines


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------


def evaluate_rule(
    rule: ScoringRule,
    ctx: LineContext,
) -> float:
    """Evaluate a single rule against a line context.

    Returns the rule's weight if it fires, 0.0 otherwise.
    """
    # match_entity: fires if any entity in rule list matches
    if rule.match_entity:
        if ctx.entity_ids & set(rule.match_entity):
            return rule.weight
        return 0.0

    # match_register: fires if the register density is > 0
    if rule.match_register is not None:
        density = ctx.feature_densities.get(rule.match_register, 0.0)
        if density > 0.0:
            return rule.weight
        return 0.0

    # has_negation_of_form
    if rule.has_negation_of_form:
        if ctx.has_negation_of_form:
            return rule.weight
        return 0.0

    # co_occurs_negation
    if rule.co_occurs_negation:
        if ctx.has_negation_cooccurrence:
            return rule.weight
        return 0.0

    return 0.0


def compute_raw_signal(
    dim_config: DimensionConfig,
    ctx: LineContext,
) -> float:
    """Compute raw signal for a dimension on a single line.

    Sum of weights for all rules that fire.
    """
    return sum(
        evaluate_rule(rule, ctx) for rule in dim_config.rules
    )


# ---------------------------------------------------------------------------
# Score record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineScores:
    """Computed scores for a single line across all dimensions.

    Attributes:
        line_uid: UID of the line.
        shabad_uid: UID of the containing shabad.
        raw_signals: Raw signal per dimension.
        context_signals: Context signal per dimension.
        combined_signals: Combined signal per dimension.
        scores: Final sigmoid-squashed scores per dimension.
    """

    line_uid: str
    shabad_uid: str | None
    raw_signals: dict[str, float]
    context_signals: dict[str, float]
    combined_signals: dict[str, float]
    scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "line_uid": self.line_uid,
            "shabad_uid": self.shabad_uid,
            "raw_signals": {
                k: round(v, 6) for k, v in self.raw_signals.items()
            },
            "context_signals": {
                k: round(v, 6) for k, v in self.context_signals.items()
            },
            "combined_signals": {
                k: round(v, 6) for k, v in self.combined_signals.items()
            },
            "scores": {
                k: round(v, 6) for k, v in self.scores.items()
            },
        }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


def compute_scores(
    contexts: list[LineContext],
    config: ScoringConfig,
) -> list[LineScores]:
    """Compute dimension scores for all lines.

    Steps:
      1. Compute raw_signal for each line and each dimension.
      2. Group lines by shabad.
      3. Compute context_signal as mean of raw_signals in the shabad.
      4. Combine: (1 - cw) * raw + cw * context.
      5. Apply sigmoid per dimension.

    Args:
        contexts: Pre-built line contexts (in corpus order).
        config: Scoring configuration.

    Returns:
        List of :class:`LineScores` in corpus order.
    """
    dim_names = list(config.dimensions.keys())

    # Step 1: Compute raw signals
    raw_by_line: dict[str, dict[str, float]] = {}
    for ctx in contexts:
        raw_signals: dict[str, float] = {}
        for dim_name in dim_names:
            dim_config = config.dimensions[dim_name]
            raw_signals[dim_name] = compute_raw_signal(
                dim_config, ctx,
            )
        raw_by_line[ctx.line_uid] = raw_signals

    # Step 2: Group by shabad
    shabad_lines: dict[str, list[str]] = defaultdict(list)
    for ctx in contexts:
        if ctx.shabad_uid is not None:
            shabad_lines[ctx.shabad_uid].append(ctx.line_uid)

    # Step 3: Compute context signals
    context_by_line: dict[str, dict[str, float]] = {}
    for ctx in contexts:
        ctx_signals: dict[str, float] = {}
        neighbors = shabad_lines.get(ctx.shabad_uid or "", [])

        for dim_name in dim_names:
            if len(neighbors) <= 1:
                # No neighbors or alone in shabad — context = 0
                ctx_signals[dim_name] = 0.0
            else:
                # Mean of all neighbors' raw signals (including self)
                total = sum(
                    raw_by_line[n][dim_name]
                    for n in neighbors
                )
                ctx_signals[dim_name] = total / len(neighbors)

        context_by_line[ctx.line_uid] = ctx_signals

    # Step 4 + 5: Combine and sigmoid
    cw = config.context_weight
    results: list[LineScores] = []

    for ctx in contexts:
        raw = raw_by_line[ctx.line_uid]
        context = context_by_line[ctx.line_uid]
        combined: dict[str, float] = {}
        scores: dict[str, float] = {}

        for dim_name in dim_names:
            dim_config = config.dimensions[dim_name]
            c = (1.0 - cw) * raw[dim_name] + cw * context[dim_name]
            combined[dim_name] = c
            scores[dim_name] = sigmoid(
                c, dim_config.sigmoid_k, dim_config.sigmoid_x0,
            )

        results.append(
            LineScores(
                line_uid=ctx.line_uid,
                shabad_uid=ctx.shabad_uid,
                raw_signals=raw,
                context_signals=context,
                combined_signals=combined,
                scores=scores,
            ),
        )

    return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def compute_all_scores(
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    features: list[dict[str, Any]],
    tagging_config: dict[str, Any],
) -> list[LineScores]:
    """End-to-end score computation from raw inputs.

    Parses config, builds line contexts, computes scores.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: All match records from the matching engine.
        features: Feature records from the feature computation engine.
        tagging_config: The ``tagging`` section of config.yaml.

    Returns:
        List of :class:`LineScores` for all lines.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Phase 3: Computing dimension scores "
        f"for {len(records)} lines...[/bold]\n",
    )

    config = parse_scoring_config(tagging_config)
    _console.print(
        f"  Dimensions: {', '.join(config.dimensions.keys())}",
    )
    _console.print(
        f"  Context weight: {config.context_weight}",
    )

    contexts = build_line_contexts(records, matches, features)
    results = compute_scores(contexts, config)

    # Summary stats
    scored_count = sum(
        1 for r in results
        if any(v > 0.5 for v in r.scores.values())
    )

    elapsed = time.monotonic() - t0
    _console.print(
        f"  {scored_count}/{len(results)} lines have "
        f"score > 0.5 in at least one dimension",
    )
    _console.print(f"  Completed in {elapsed:.2f}s")

    return results
