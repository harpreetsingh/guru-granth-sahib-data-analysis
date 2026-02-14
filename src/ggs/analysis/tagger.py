"""Rule-based interpretive tagger with sigmoid scoring (bd-2zi.3, bd-2zi.4).

Integration point for Phase 3 — wires the score engine, rules config,
and category derivation into a complete tagging pipeline that produces
tag records per line.

Each line gets:
  - Continuous scores per dimension (sigmoid-squashed)
  - A primary_tag derived from threshold logic
  - Zero or more secondary_tags
  - Full evidence trail (rules_fired, evidence_tokens, score_breakdown)

Category derivation uses configurable thresholds (bd-2zi.4) so that
sensitivity analyses can be run with different threshold choices.
The distribution CSV breaks down by author, raga, and ang bucket.

Reference: PLAN.md Section 6.2
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.analysis.match import MatchRecord
from ggs.analysis.scores import (
    LineContext,
    LineScores,
    ScoringConfig,
    build_line_contexts,
    compute_scores,
    evaluate_rule,
    parse_scoring_config,
)

_console = Console()


# ---------------------------------------------------------------------------
# Tag record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RuleFiring:
    """Record of a single rule that fired on a line.

    Attributes:
        rule: Description of the rule (e.g. "match_entity:WAHEGURU").
        weight: The weight contributed by this rule.
        matched: The evidence token or pattern that triggered the rule.
    """

    rule: str
    weight: float
    matched: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "weight": round(self.weight, 4),
            "matched": self.matched,
        }


@dataclass(frozen=True, slots=True)
class TagRecord:
    """Complete tag record for a single line.

    Attributes:
        line_uid: UID of the line.
        scores: Final sigmoid-squashed scores per dimension.
        primary_tag: Derived primary category tag (may be None).
        secondary_tags: Additional tags that apply to the line.
        rules_fired: List of rule descriptions that fired.
        evidence_tokens: Surface forms that contributed to the scores.
        score_breakdown: Per-dimension list of rule firings with evidence.
        ang: Ang number (for distribution breakdowns).
        author: Author attribution (for distribution breakdowns).
        raga: Raga section (for distribution breakdowns).
    """

    line_uid: str
    scores: dict[str, float]
    primary_tag: str | None
    secondary_tags: list[str]
    rules_fired: list[str]
    evidence_tokens: list[str]
    score_breakdown: dict[str, list[RuleFiring]]
    ang: int = 0
    author: str = ""
    raga: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_uid": self.line_uid,
            "scores": {
                k: round(v, 6) for k, v in self.scores.items()
            },
            "primary_tag": self.primary_tag,
            "secondary_tags": self.secondary_tags,
            "rules_fired": self.rules_fired,
            "evidence_tokens": self.evidence_tokens,
            "score_breakdown": {
                dim: [r.to_dict() for r in firings]
                for dim, firings in self.score_breakdown.items()
                if firings
            },
            "ang": self.ang,
            "author": self.author,
            "raga": self.raga,
        }


# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    """Parsed threshold configuration for category derivation.

    Attributes:
        nirgun_min: Minimum nirgun score for nirgun_leaning.
        sagun_max_for_nirgun: Maximum sagun score for nirgun_leaning.
        sagun_min: Minimum sagun score for sagun_narrative_leaning.
        nirgun_max_for_sagun: Maximum nirgun score for sagun_narrative_leaning.
        mixed_difference_max: Max difference between nirgun and sagun for mixed.
        mixed_both_min: Minimum of both nirgun and sagun for mixed.
        universalism_min: Minimum score for universalism secondary tag.
        critique_ritual_min: Minimum score for critique_ritual secondary tag.
        critique_clerics_min: Minimum score for critique_clerics secondary tag.
    """

    nirgun_min: float = 0.6
    sagun_max_for_nirgun: float = 0.3
    sagun_min: float = 0.6
    nirgun_max_for_sagun: float = 0.3
    mixed_difference_max: float = 0.3
    mixed_both_min: float = 0.2
    universalism_min: float = 0.5
    critique_ritual_min: float = 0.5
    critique_clerics_min: float = 0.5


def parse_threshold_config(
    thresholds: dict[str, Any],
) -> ThresholdConfig:
    """Parse the ``thresholds`` section of tagging config.

    Args:
        thresholds: The ``thresholds`` dict from config.yaml.

    Returns:
        A :class:`ThresholdConfig` instance.
    """
    nirgun = thresholds.get("nirgun_leaning", {})
    sagun = thresholds.get("sagun_narrative_leaning", {})
    mixed = thresholds.get("mixed", {})

    return ThresholdConfig(
        nirgun_min=float(nirgun.get("nirgun_min", 0.6)),
        sagun_max_for_nirgun=float(nirgun.get("sagun_max", 0.3)),
        sagun_min=float(sagun.get("sagun_min", 0.6)),
        nirgun_max_for_sagun=float(sagun.get("nirgun_max", 0.3)),
        mixed_difference_max=float(mixed.get("difference_max", 0.3)),
        mixed_both_min=float(mixed.get("both_min", 0.2)),
        universalism_min=float(
            thresholds.get("universalism", {}).get("min", 0.5),
        ),
        critique_ritual_min=float(
            thresholds.get("critique_ritual", {}).get("min", 0.5),
        ),
        critique_clerics_min=float(
            thresholds.get("critique_clerics", {}).get("min", 0.5),
        ),
    )


# ---------------------------------------------------------------------------
# Category derivation
# ---------------------------------------------------------------------------


def derive_primary_tag(
    scores: dict[str, float],
    config: ThresholdConfig,
) -> str | None:
    """Derive the primary theological category from dimension scores.

    Priority (checked in order):
      1. nirgun_leaning: nirgun >= nirgun_min AND sagun < sagun_max
      2. sagun_narrative_leaning: sagun >= sagun_min AND nirgun < nirgun_max
      3. mixed: both above both_min AND difference <= difference_max
      4. None (unclassified)

    Args:
        scores: Dimension scores for a line.
        config: Threshold configuration.

    Returns:
        Primary tag string or None.
    """
    nirgun = scores.get("nirgun", 0.0)
    sagun = scores.get("sagun_narrative", 0.0)

    # Nirgun-leaning
    if (
        nirgun >= config.nirgun_min
        and sagun < config.sagun_max_for_nirgun
    ):
        return "nirgun_leaning"

    # Sagun-narrative-leaning
    if (
        sagun >= config.sagun_min
        and nirgun < config.nirgun_max_for_sagun
    ):
        return "sagun_narrative_leaning"

    # Mixed
    if (
        nirgun >= config.mixed_both_min
        and sagun >= config.mixed_both_min
        and abs(nirgun - sagun) <= config.mixed_difference_max
    ):
        return "mixed"

    return None


def derive_secondary_tags(
    scores: dict[str, float],
    config: ThresholdConfig,
) -> list[str]:
    """Derive secondary tags from dimension scores.

    Tags are not mutually exclusive. A line can be nirgun AND
    critique_ritual simultaneously.

    Args:
        scores: Dimension scores for a line.
        config: Threshold configuration.

    Returns:
        List of secondary tag strings (may be empty).
    """
    tags: list[str] = []

    if scores.get("universalism", 0.0) >= config.universalism_min:
        tags.append("universalism")

    if scores.get("critique_ritual", 0.0) >= config.critique_ritual_min:
        tags.append("critique_ritual")

    if scores.get("critique_clerics", 0.0) >= config.critique_clerics_min:
        tags.append("critique_clerics")

    return tags


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


def _describe_rule(rule_index: int, rule: Any) -> str:
    """Create a human-readable description of a scoring rule.

    Args:
        rule_index: Index of the rule in the dimension's rule list.
        rule: A ScoringRule instance.

    Returns:
        Description string like "match_entity:WAHEGURU".
    """
    if rule.match_entity:
        entities = ",".join(rule.match_entity)
        return f"match_entity:{entities}"
    if rule.match_register is not None:
        return f"match_register:{rule.match_register}"
    if rule.has_negation_of_form:
        return "has_negation_of_form"
    if rule.co_occurs_negation:
        return "co_occurs_negation"
    return f"rule_{rule_index}"


def _find_evidence_token(
    rule: Any,
    ctx: LineContext,
    matches_by_line: dict[str, list[MatchRecord]],
) -> str:
    """Find the surface-form evidence token for a rule firing.

    Args:
        rule: The ScoringRule that fired.
        ctx: LineContext for the line.
        matches_by_line: Mapping from line_uid to match records.

    Returns:
        Evidence string (matched form or pattern description).
    """
    if rule.match_entity:
        entity_set = set(rule.match_entity)
        for m in matches_by_line.get(ctx.line_uid, []):
            if m.entity_id in entity_set and m.nested_in is None:
                return m.matched_form
        return ",".join(rule.match_entity)

    if rule.match_register is not None:
        density = ctx.feature_densities.get(rule.match_register, 0.0)
        return f"register:{rule.match_register}={density:.2f}"

    if rule.has_negation_of_form:
        return "negation_of_form"

    if rule.co_occurs_negation:
        return "ritual+negation"

    return "unknown"


def collect_evidence(
    line_scores: LineScores,
    ctx: LineContext,
    config: ScoringConfig,
    matches_by_line: dict[str, list[MatchRecord]],
) -> tuple[list[str], list[str], dict[str, list[RuleFiring]]]:
    """Collect evidence trail for all rule firings on a line.

    Args:
        line_scores: Computed scores for the line.
        ctx: LineContext for the line.
        config: Scoring configuration.
        matches_by_line: Mapping from line_uid to match records.

    Returns:
        Tuple of (rules_fired, evidence_tokens, score_breakdown).
    """
    all_rules_fired: list[str] = []
    all_evidence_tokens: list[str] = []
    score_breakdown: dict[str, list[RuleFiring]] = {}

    seen_evidence: set[str] = set()

    for dim_name, dim_config in config.dimensions.items():
        firings: list[RuleFiring] = []

        for i, rule in enumerate(dim_config.rules):
            weight_fired = evaluate_rule(rule, ctx)
            if weight_fired > 0.0:
                rule_desc = _describe_rule(i, rule)
                evidence = _find_evidence_token(
                    rule, ctx, matches_by_line,
                )

                firings.append(
                    RuleFiring(
                        rule=rule_desc,
                        weight=weight_fired,
                        matched=evidence,
                    ),
                )

                if rule_desc not in all_rules_fired:
                    all_rules_fired.append(rule_desc)
                if evidence not in seen_evidence:
                    all_evidence_tokens.append(evidence)
                    seen_evidence.add(evidence)

        score_breakdown[dim_name] = firings

    return all_rules_fired, all_evidence_tokens, score_breakdown


# ---------------------------------------------------------------------------
# Tag generation
# ---------------------------------------------------------------------------


def generate_tags(
    line_scores_list: list[LineScores],
    contexts: list[LineContext],
    config: ScoringConfig,
    threshold_config: ThresholdConfig,
    matches: list[MatchRecord],
    records: list[dict[str, Any]] | None = None,
) -> list[TagRecord]:
    """Generate tag records from scored lines.

    Args:
        line_scores_list: Computed scores for all lines.
        contexts: Pre-built line contexts.
        config: Scoring configuration.
        threshold_config: Threshold configuration for category derivation.
        matches: All match records (for evidence collection).
        records: Optional corpus records for extracting metadata
            (ang, author, raga).

    Returns:
        List of :class:`TagRecord` in corpus order.
    """
    # Index matches by line_uid for evidence lookup
    matches_by_line: dict[str, list[MatchRecord]] = defaultdict(list)
    for m in matches:
        if m.nested_in is None:
            matches_by_line[m.line_uid].append(m)

    # Index contexts by line_uid
    ctx_by_line: dict[str, LineContext] = {
        ctx.line_uid: ctx for ctx in contexts
    }

    # Index record metadata by line_uid
    meta_by_line: dict[str, dict[str, Any]] = {}
    if records:
        for rec in records:
            line_uid = rec.get("line_uid", "")
            meta_by_line[line_uid] = {
                "ang": rec.get("ang", 0),
                "author": rec.get("meta", {}).get("author", ""),
                "raga": rec.get("meta", {}).get("raga", ""),
            }

    tags: list[TagRecord] = []

    for ls in line_scores_list:
        ctx = ctx_by_line.get(ls.line_uid)
        if ctx is None:
            continue

        primary_tag = derive_primary_tag(
            ls.scores, threshold_config,
        )
        secondary_tags = derive_secondary_tags(
            ls.scores, threshold_config,
        )

        rules_fired, evidence_tokens, score_breakdown = collect_evidence(
            ls, ctx, config, matches_by_line,
        )

        meta = meta_by_line.get(ls.line_uid, {})

        tags.append(
            TagRecord(
                line_uid=ls.line_uid,
                scores=ls.scores,
                primary_tag=primary_tag,
                secondary_tags=secondary_tags,
                rules_fired=rules_fired,
                evidence_tokens=evidence_tokens,
                score_breakdown=score_breakdown,
                ang=meta.get("ang", 0),
                author=meta.get("author", ""),
                raga=meta.get("raga", ""),
            ),
        )

    return tags


# ---------------------------------------------------------------------------
# Distribution report
# ---------------------------------------------------------------------------


def generate_distribution_csv(
    tags: list[TagRecord],
) -> str:
    """Generate nirgun_sagun_distribution.csv from tag records.

    Columns: primary_tag, count, percentage

    Args:
        tags: All tag records.

    Returns:
        CSV string.
    """
    counts: dict[str, int] = defaultdict(int)
    total = len(tags)

    for tag in tags:
        label = tag.primary_tag or "unclassified"
        counts[label] += 1

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["primary_tag", "count", "percentage"])

    for label in sorted(counts.keys()):
        pct = round(counts[label] / total * 100, 2) if total > 0 else 0.0
        writer.writerow([label, counts[label], pct])

    return output.getvalue()


def _ang_bucket(ang: int, bucket_size: int = 100) -> str:
    """Compute ang bucket label for distribution grouping.

    Args:
        ang: Ang number (1-1430).
        bucket_size: Size of each bucket (default 100).

    Returns:
        Bucket label like "1-100", "101-200", etc.
    """
    if ang <= 0:
        return "unknown"
    low = ((ang - 1) // bucket_size) * bucket_size + 1
    high = low + bucket_size - 1
    return f"{low}-{high}"


def generate_detailed_distribution(
    tags: list[TagRecord],
    *,
    bucket_size: int = 100,
) -> str:
    """Generate detailed distribution CSV with breakdowns.

    Produces category counts grouped by:
      - Overall (group_type="overall")
      - By author (group_type="author")
      - By raga (group_type="raga")
      - By ang bucket (group_type="ang_bucket")

    Columns: group_type, group_value, primary_tag, count, percentage

    Args:
        tags: All tag records (must have ang, author, raga populated).
        bucket_size: Size of ang buckets for grouping (default 100).

    Returns:
        CSV string.
    """
    if not tags:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "group_type", "group_value",
            "primary_tag", "count", "percentage",
        ])
        return output.getvalue()

    # Collect counts per grouping
    # Structure: {(group_type, group_value): {primary_tag: count}}
    group_counts: dict[
        tuple[str, str], dict[str, int]
    ] = defaultdict(lambda: defaultdict(int))
    group_totals: dict[tuple[str, str], int] = defaultdict(int)

    for tag in tags:
        label = tag.primary_tag or "unclassified"

        # Overall
        key_overall = ("overall", "all")
        group_counts[key_overall][label] += 1
        group_totals[key_overall] += 1

        # By author
        author = tag.author or "unknown"
        key_author = ("author", author)
        group_counts[key_author][label] += 1
        group_totals[key_author] += 1

        # By raga
        raga = tag.raga or "unknown"
        key_raga = ("raga", raga)
        group_counts[key_raga][label] += 1
        group_totals[key_raga] += 1

        # By ang bucket
        bucket = _ang_bucket(tag.ang, bucket_size)
        key_bucket = ("ang_bucket", bucket)
        group_counts[key_bucket][label] += 1
        group_totals[key_bucket] += 1

    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "group_type", "group_value",
        "primary_tag", "count", "percentage",
    ])

    for group_key in sorted(group_counts.keys()):
        group_type, group_value = group_key
        total = group_totals[group_key]
        for label in sorted(group_counts[group_key].keys()):
            count = group_counts[group_key][label]
            pct = round(count / total * 100, 2) if total > 0 else 0.0
            writer.writerow([
                group_type, group_value, label, count, pct,
            ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Sensitivity analysis
# ---------------------------------------------------------------------------


def rederive_tags(
    tags: list[TagRecord],
    new_thresholds: ThresholdConfig,
) -> list[TagRecord]:
    """Re-derive primary and secondary tags with different thresholds.

    This enables sensitivity analysis: given existing scored tags, apply
    different threshold configurations to see how category distributions
    change without recomputing scores.

    Args:
        tags: Existing tag records (scores must be populated).
        new_thresholds: New threshold configuration to apply.

    Returns:
        New list of :class:`TagRecord` with updated primary_tag and
        secondary_tags. All other fields (scores, evidence, etc.) are
        preserved.
    """
    rederived: list[TagRecord] = []
    for tag in tags:
        primary = derive_primary_tag(tag.scores, new_thresholds)
        secondary = derive_secondary_tags(tag.scores, new_thresholds)

        rederived.append(
            TagRecord(
                line_uid=tag.line_uid,
                scores=tag.scores,
                primary_tag=primary,
                secondary_tags=secondary,
                rules_fired=tag.rules_fired,
                evidence_tokens=tag.evidence_tokens,
                score_breakdown=tag.score_breakdown,
                ang=tag.ang,
                author=tag.author,
                raga=tag.raga,
            ),
        )

    return rederived


def run_sensitivity_analysis(
    tags: list[TagRecord],
    threshold_variants: dict[str, ThresholdConfig],
) -> dict[str, list[TagRecord]]:
    """Run category derivation with multiple threshold configurations.

    Useful for answering questions like "what happens to the nirgun
    distribution if we lower the threshold from 0.6 to 0.5?"

    Args:
        tags: Existing tag records with scores.
        threshold_variants: Named threshold configurations to test.

    Returns:
        Mapping from variant name to re-derived tag records.
    """
    results: dict[str, list[TagRecord]] = {}
    for variant_name, thresholds in sorted(threshold_variants.items()):
        results[variant_name] = rederive_tags(tags, thresholds)
    return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def run_tagger(
    records: list[dict[str, Any]],
    matches: list[MatchRecord],
    features: list[dict[str, Any]],
    tagging_config: dict[str, Any],
    *,
    output_dir: Path | None = None,
) -> list[TagRecord]:
    """End-to-end tagging pipeline.

    Steps:
      1. Parse config and thresholds
      2. Build line contexts
      3. Compute scores
      4. Generate tags with evidence
      5. Write outputs (tags.jsonl, nirgun_sagun_distribution.csv)

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: All match records.
        features: Feature records from feature computation.
        tagging_config: The ``tagging`` section of config.yaml.
        output_dir: If provided, write output files.

    Returns:
        List of :class:`TagRecord` for all lines.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Phase 3: Tagging "
        f"{len(records)} lines...[/bold]\n",
    )

    # Parse configurations
    scoring_config = parse_scoring_config(tagging_config)
    threshold_config = parse_threshold_config(
        tagging_config.get("thresholds", {}),
    )

    _console.print(
        f"  Dimensions: {', '.join(scoring_config.dimensions.keys())}",
    )

    # Build contexts and compute scores
    contexts = build_line_contexts(records, matches, features)
    line_scores_list = compute_scores(contexts, scoring_config)

    _console.print(
        f"  Scored {len(line_scores_list)} lines",
    )

    # Generate tags
    tags = generate_tags(
        line_scores_list, contexts, scoring_config,
        threshold_config, matches, records,
    )

    # Summary
    tag_counts: dict[str, int] = defaultdict(int)
    for tag in tags:
        label = tag.primary_tag or "unclassified"
        tag_counts[label] += 1

    for label in sorted(tag_counts.keys()):
        _console.print(
            f"  {label}: {tag_counts[label]} lines",
        )

    secondary_count = sum(
        len(t.secondary_tags) for t in tags
    )
    _console.print(
        f"  Secondary tags: {secondary_count} total assignments",
    )

    # Write outputs
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

        # tags.jsonl
        tags_path = output_dir / "tags.jsonl"
        with tags_path.open("w", encoding="utf-8") as fh:
            for tag in tags:
                fh.write(
                    json.dumps(
                        tag.to_dict(), ensure_ascii=False,
                    ) + "\n",
                )
        _console.print(f"  Written {tags_path}")

        # nirgun_sagun_distribution.csv (simple summary)
        dist_path = output_dir / "nirgun_sagun_distribution.csv"
        dist_path.write_text(
            generate_distribution_csv(tags),
            encoding="utf-8",
        )
        _console.print(f"  Written {dist_path}")

        # nirgun_sagun_distribution_detailed.csv (by author/raga/ang)
        detailed_path = (
            output_dir / "nirgun_sagun_distribution_detailed.csv"
        )
        detailed_path.write_text(
            generate_detailed_distribution(tags),
            encoding="utf-8",
        )
        _console.print(f"  Written {detailed_path}")

    elapsed = time.monotonic() - t0
    _console.print(f"  Completed in {elapsed:.2f}s")

    return tags
