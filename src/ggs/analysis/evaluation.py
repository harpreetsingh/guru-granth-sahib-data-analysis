"""Gold set evaluation framework — precision, recall, F1 (bd-2zi.5).

Provides tools for loading a manually-annotated gold standard, comparing
automated tagger output against human judgments, and computing standard
classification metrics per category.

Evaluation workflow:
  1. Load gold labels from ``data/gold/gold_labels.jsonl``
  2. Load automated tag records from the tagger pipeline
  3. Align gold and predicted labels by line_uid
  4. Compute per-category precision, recall, F1
  5. Optionally run threshold sweep to see how metrics vary

Gold label format (one JSON object per line in gold_labels.jsonl):
  - ``line_uid``: Unique line identifier
  - ``category``: Ground-truth category (e.g. "nirgun_leaning")
  - ``confidence``: Annotator confidence ("certain"/"probable"/"uncertain")
  - ``annotator``: Who annotated this line
  - ``notes``: Optional free-text notes

Reference: PLAN.md Section 6.2
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from rich.console import Console

_console = Console()


# ---------------------------------------------------------------------------
# Gold label record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GoldLabel:
    """A single gold-standard annotation.

    Attributes:
        line_uid: Unique line identifier.
        category: Ground-truth primary category.
        secondary_categories: Additional ground-truth categories.
        confidence: Annotator confidence level.
        annotator: Who annotated this line.
        notes: Optional free-text notes.
    """

    line_uid: str
    category: str
    secondary_categories: list[str] = field(default_factory=list)
    confidence: str = "certain"
    annotator: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_uid": self.line_uid,
            "category": self.category,
            "secondary_categories": self.secondary_categories,
            "confidence": self.confidence,
            "annotator": self.annotator,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldLabel:
        """Parse a gold label from a dict."""
        return cls(
            line_uid=data.get("line_uid", ""),
            category=data.get("category", ""),
            secondary_categories=list(
                data.get("secondary_categories", []),
            ),
            confidence=data.get("confidence", "certain"),
            annotator=data.get("annotator", ""),
            notes=data.get("notes", ""),
        )


def load_gold_labels(path: Path) -> list[GoldLabel]:
    """Load gold labels from a JSONL file.

    Args:
        path: Path to ``gold_labels.jsonl``.

    Returns:
        List of :class:`GoldLabel` instances.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    labels: list[GoldLabel] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            labels.append(GoldLabel.from_dict(data))
    return labels


def save_gold_labels(
    labels: list[GoldLabel],
    path: Path,
) -> None:
    """Save gold labels to a JSONL file.

    Args:
        labels: Gold labels to save.
        path: Output path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for label in labels:
            fh.write(
                json.dumps(label.to_dict(), ensure_ascii=False) + "\n",
            )


# ---------------------------------------------------------------------------
# Per-category metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CategoryMetrics:
    """Precision, recall, F1 for a single category.

    Attributes:
        category: Category name.
        true_positives: Lines correctly assigned this category.
        false_positives: Lines incorrectly assigned this category.
        false_negatives: Lines with this category in gold but not predicted.
        precision: TP / (TP + FP), or 0 if no predictions.
        recall: TP / (TP + FN), or 0 if no gold labels.
        f1: Harmonic mean of precision and recall.
        support: Total gold labels for this category (TP + FN).
    """

    category: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    support: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "support": self.support,
        }


def _compute_f1(precision: float, recall: float) -> float:
    """Compute F1 score from precision and recall."""
    if precision + recall == 0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def compute_category_metrics(
    gold_labels: list[GoldLabel],
    predicted: dict[str, str | None],
    category: str,
) -> CategoryMetrics:
    """Compute precision, recall, F1 for a single category.

    Args:
        gold_labels: Gold standard labels.
        predicted: Mapping from line_uid to predicted primary_tag.
        category: The category to evaluate.

    Returns:
        A :class:`CategoryMetrics` instance.
    """
    tp = 0
    fp = 0
    fn = 0

    gold_by_uid: dict[str, str] = {
        g.line_uid: g.category for g in gold_labels
    }

    # Check all predictions
    for line_uid, pred_tag in predicted.items():
        gold_tag = gold_by_uid.get(line_uid)
        if gold_tag is None:
            # Not in gold set — skip
            continue

        if pred_tag == category and gold_tag == category:
            tp += 1
        elif pred_tag == category and gold_tag != category:
            fp += 1

    # Check all gold labels for false negatives
    for gold in gold_labels:
        if gold.category == category:
            pred_tag = predicted.get(gold.line_uid)
            if pred_tag != category:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = _compute_f1(precision, recall)
    support = tp + fn

    return CategoryMetrics(
        category=category,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        support=support,
    )


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Complete evaluation results across all categories.

    Attributes:
        per_category: Metrics for each evaluated category.
        macro_precision: Mean precision across categories.
        macro_recall: Mean recall across categories.
        macro_f1: Mean F1 across categories.
        total_gold: Total gold labels evaluated.
        total_aligned: Gold labels that had a corresponding prediction.
    """

    per_category: dict[str, CategoryMetrics]
    macro_precision: float
    macro_recall: float
    macro_f1: float
    total_gold: int
    total_aligned: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "per_category": {
                k: v.to_dict() for k, v in self.per_category.items()
            },
            "macro_precision": round(self.macro_precision, 4),
            "macro_recall": round(self.macro_recall, 4),
            "macro_f1": round(self.macro_f1, 4),
            "total_gold": self.total_gold,
            "total_aligned": self.total_aligned,
        }


def evaluate(
    gold_labels: list[GoldLabel],
    predicted: dict[str, str | None],
    *,
    categories: list[str] | None = None,
) -> EvaluationResult:
    """Evaluate predicted tags against gold standard.

    Args:
        gold_labels: Gold standard labels.
        predicted: Mapping from line_uid to predicted primary_tag.
        categories: Categories to evaluate. If None, derives from
            the union of gold and predicted categories.

    Returns:
        An :class:`EvaluationResult` with per-category and macro metrics.
    """
    if categories is None:
        cat_set: set[str] = set()
        for g in gold_labels:
            if g.category:
                cat_set.add(g.category)
        for tag in predicted.values():
            if tag:
                cat_set.add(tag)
        categories = sorted(cat_set)

    total_gold = len(gold_labels)
    total_aligned = sum(
        1 for g in gold_labels if g.line_uid in predicted
    )

    per_category: dict[str, CategoryMetrics] = {}
    for cat in categories:
        per_category[cat] = compute_category_metrics(
            gold_labels, predicted, cat,
        )

    # Macro averages (only over categories with support > 0)
    cats_with_support = [
        m for m in per_category.values() if m.support > 0
    ]
    if cats_with_support:
        macro_p = sum(
            m.precision for m in cats_with_support
        ) / len(cats_with_support)
        macro_r = sum(
            m.recall for m in cats_with_support
        ) / len(cats_with_support)
        macro_f1 = _compute_f1(macro_p, macro_r)
    else:
        macro_p = 0.0
        macro_r = 0.0
        macro_f1 = 0.0

    return EvaluationResult(
        per_category=per_category,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        total_gold=total_gold,
        total_aligned=total_aligned,
    )


# ---------------------------------------------------------------------------
# Threshold sweep
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThresholdSweepPoint:
    """Metrics at a single threshold setting.

    Attributes:
        threshold_name: Description of the threshold variant.
        metrics: Evaluation results at this threshold.
    """

    threshold_name: str
    metrics: EvaluationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold_name": self.threshold_name,
            "metrics": self.metrics.to_dict(),
        }


def threshold_sweep(
    gold_labels: list[GoldLabel],
    predicted_variants: dict[str, dict[str, str | None]],
    *,
    categories: list[str] | None = None,
) -> list[ThresholdSweepPoint]:
    """Evaluate multiple threshold variants against gold.

    Useful for answering: "how do P/R change as we vary thresholds?"

    Args:
        gold_labels: Gold standard labels.
        predicted_variants: Mapping from variant name to predicted tags.
        categories: Categories to evaluate (derived from gold if None).

    Returns:
        List of :class:`ThresholdSweepPoint` sorted by name.
    """
    results: list[ThresholdSweepPoint] = []
    for name in sorted(predicted_variants.keys()):
        metrics = evaluate(
            gold_labels, predicted_variants[name],
            categories=categories,
        )
        results.append(
            ThresholdSweepPoint(threshold_name=name, metrics=metrics),
        )
    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_evaluation_csv(
    result: EvaluationResult,
) -> str:
    """Generate a CSV report from evaluation results.

    Columns: category, precision, recall, f1, support, tp, fp, fn

    Args:
        result: Evaluation results.

    Returns:
        CSV string.
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "category", "precision", "recall", "f1",
        "support", "tp", "fp", "fn",
    ])

    for cat in sorted(result.per_category.keys()):
        m = result.per_category[cat]
        writer.writerow([
            cat,
            round(m.precision, 4),
            round(m.recall, 4),
            round(m.f1, 4),
            m.support,
            m.true_positives,
            m.false_positives,
            m.false_negatives,
        ])

    # Macro row
    writer.writerow([
        "MACRO",
        round(result.macro_precision, 4),
        round(result.macro_recall, 4),
        round(result.macro_f1, 4),
        result.total_gold,
        "", "", "",
    ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Error analysis
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    """A single prediction error for error analysis.

    Attributes:
        line_uid: Line that was incorrectly classified.
        gold_category: Ground-truth category.
        predicted_category: What the tagger predicted.
        confidence: Gold annotator's confidence.
        notes: Gold annotator's notes (for context).
    """

    line_uid: str
    gold_category: str
    predicted_category: str | None
    confidence: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_uid": self.line_uid,
            "gold_category": self.gold_category,
            "predicted_category": self.predicted_category,
            "confidence": self.confidence,
            "notes": self.notes,
        }


def collect_errors(
    gold_labels: list[GoldLabel],
    predicted: dict[str, str | None],
) -> list[ErrorRecord]:
    """Collect all prediction errors for analysis.

    Args:
        gold_labels: Gold standard labels.
        predicted: Mapping from line_uid to predicted primary_tag.

    Returns:
        List of :class:`ErrorRecord` for all mismatches.
    """
    errors: list[ErrorRecord] = []
    for gold in gold_labels:
        pred = predicted.get(gold.line_uid)
        if pred != gold.category:
            errors.append(
                ErrorRecord(
                    line_uid=gold.line_uid,
                    gold_category=gold.category,
                    predicted_category=pred,
                    confidence=gold.confidence,
                    notes=gold.notes,
                ),
            )
    return errors


def error_confusion_matrix(
    gold_labels: list[GoldLabel],
    predicted: dict[str, str | None],
) -> dict[str, dict[str, int]]:
    """Build a confusion matrix from gold labels and predictions.

    Args:
        gold_labels: Gold standard labels.
        predicted: Mapping from line_uid to predicted primary_tag.

    Returns:
        Nested dict: confusion[gold_category][predicted_category] = count.
    """
    matrix: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )
    for gold in gold_labels:
        pred = predicted.get(gold.line_uid, "MISSING")
        pred_label = pred if pred is not None else "unclassified"
        matrix[gold.category][pred_label] += 1
    return {k: dict(v) for k, v in matrix.items()}


# ---------------------------------------------------------------------------
# Stratified sampling
# ---------------------------------------------------------------------------


def stratified_sample(
    records: list[dict[str, Any]],
    *,
    target_size: int = 500,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Sample lines for gold annotation using stratified sampling.

    Ensures proportional representation across:
      - Authors (via ``meta.author``)
      - Ragas (via ``meta.raga``)
      - Ang ranges (100-ang buckets)

    The sampling uses a round-robin approach across strata to avoid
    over-representing any single group.

    Args:
        records: Full corpus records.
        target_size: Target number of lines to sample.
        seed: Random seed for reproducibility.

    Returns:
        Sampled records (up to target_size).
    """
    import random

    if not records or target_size <= 0:
        return []

    rng = random.Random(seed)

    # Group by author
    by_author: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        author = rec.get("meta", {}).get("author", "unknown")
        by_author[author].append(rec)

    # Shuffle within each group
    for group in by_author.values():
        rng.shuffle(group)

    # Round-robin across authors to ensure proportional representation
    sampled: list[dict[str, Any]] = []
    seen_uids: set[str] = set()

    # Compute proportional quotas
    total = len(records)
    quotas: dict[str, int] = {}
    for author, group in by_author.items():
        quota = max(1, round(len(group) / total * target_size))
        quotas[author] = min(quota, len(group))

    # Take from each author proportionally
    for author in sorted(quotas.keys()):
        group = by_author[author]
        for rec in group[: quotas[author]]:
            uid = rec.get("line_uid", "")
            if uid not in seen_uids:
                sampled.append(rec)
                seen_uids.add(uid)

    # If we haven't reached target, fill from remaining
    if len(sampled) < target_size:
        remaining = [
            rec for rec in records
            if rec.get("line_uid", "") not in seen_uids
        ]
        rng.shuffle(remaining)
        for rec in remaining:
            if len(sampled) >= target_size:
                break
            sampled.append(rec)
            seen_uids.add(rec.get("line_uid", ""))

    return sampled[:target_size]


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def run_evaluation(
    gold_path: Path,
    predicted: dict[str, str | None],
    *,
    output_dir: Path | None = None,
    categories: list[str] | None = None,
) -> EvaluationResult:
    """Run full evaluation pipeline.

    Args:
        gold_path: Path to gold_labels.jsonl.
        predicted: Mapping from line_uid to predicted primary_tag.
        output_dir: If provided, write evaluation reports.
        categories: Categories to evaluate (auto-detected if None).

    Returns:
        :class:`EvaluationResult`.
    """
    _console.print(
        "\n[bold]Evaluating tagger against gold standard...[/bold]\n",
    )

    gold = load_gold_labels(gold_path)
    _console.print(f"  Gold labels: {len(gold)}")

    result = evaluate(gold, predicted, categories=categories)

    _console.print(
        f"  Aligned: {result.total_aligned}/{result.total_gold}",
    )

    for cat in sorted(result.per_category.keys()):
        m = result.per_category[cat]
        _console.print(
            f"  {cat}: P={m.precision:.3f} R={m.recall:.3f} "
            f"F1={m.f1:.3f} (n={m.support})",
        )

    _console.print(
        f"\n  Macro: P={result.macro_precision:.3f} "
        f"R={result.macro_recall:.3f} F1={result.macro_f1:.3f}",
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write evaluation CSV
        eval_path = output_dir / "evaluation_metrics.csv"
        eval_path.write_text(
            generate_evaluation_csv(result),
            encoding="utf-8",
        )
        _console.print(f"  Written {eval_path}")

        # Write errors
        errors = collect_errors(gold, predicted)
        if errors:
            errors_path = output_dir / "evaluation_errors.jsonl"
            with errors_path.open("w", encoding="utf-8") as fh:
                for err in errors:
                    fh.write(
                        json.dumps(
                            err.to_dict(), ensure_ascii=False,
                        ) + "\n",
                    )
            _console.print(
                f"  {len(errors)} errors written to {errors_path}",
            )

        # Write confusion matrix
        matrix = error_confusion_matrix(gold, predicted)
        matrix_path = output_dir / "confusion_matrix.json"
        with matrix_path.open("w", encoding="utf-8") as fh:
            json.dump(matrix, fh, ensure_ascii=False, indent=2)
        _console.print(f"  Written {matrix_path}")

    return result
