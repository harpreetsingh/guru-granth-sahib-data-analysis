"""Gold set evaluation framework tests (bd-2zi.5).

Tests gold label loading/saving, per-category metrics computation,
full evaluation, threshold sweep, error analysis, confusion matrix,
stratified sampling, and CSV report generation.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import pytest

from ggs.analysis.evaluation import (
    CategoryMetrics,
    ErrorRecord,
    EvaluationResult,
    GoldLabel,
    ThresholdSweepPoint,
    collect_errors,
    compute_category_metrics,
    error_confusion_matrix,
    evaluate,
    generate_evaluation_csv,
    load_gold_labels,
    run_evaluation,
    save_gold_labels,
    stratified_sample,
    threshold_sweep,
)

# ---------------------------------------------------------------------------
# GoldLabel tests
# ---------------------------------------------------------------------------


class TestGoldLabel:
    """Tests for GoldLabel."""

    def test_to_dict(self) -> None:
        label = GoldLabel(
            line_uid="line:1",
            category="nirgun_leaning",
            confidence="certain",
            annotator="hsingh",
            notes="Clear nirgun reference",
        )
        d = label.to_dict()
        assert d["line_uid"] == "line:1"
        assert d["category"] == "nirgun_leaning"
        assert d["confidence"] == "certain"
        assert d["annotator"] == "hsingh"
        assert d["notes"] == "Clear nirgun reference"

    def test_from_dict(self) -> None:
        data = {
            "line_uid": "line:1",
            "category": "mixed",
            "confidence": "probable",
            "annotator": "hsingh",
            "notes": "",
        }
        label = GoldLabel.from_dict(data)
        assert label.line_uid == "line:1"
        assert label.category == "mixed"
        assert label.confidence == "probable"

    def test_from_dict_defaults(self) -> None:
        label = GoldLabel.from_dict({})
        assert label.line_uid == ""
        assert label.category == ""
        assert label.confidence == "certain"
        assert label.annotator == ""

    def test_roundtrip(self) -> None:
        label = GoldLabel(
            line_uid="line:42",
            category="nirgun_leaning",
            secondary_categories=["universalism"],
            confidence="certain",
            annotator="hsingh",
            notes="Test roundtrip",
        )
        restored = GoldLabel.from_dict(label.to_dict())
        assert restored.line_uid == label.line_uid
        assert restored.category == label.category
        assert restored.secondary_categories == label.secondary_categories
        assert restored.confidence == label.confidence


class TestGoldLabelIO:
    """Tests for load_gold_labels and save_gold_labels."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        labels = [
            GoldLabel(
                line_uid="line:1",
                category="nirgun_leaning",
            ),
            GoldLabel(
                line_uid="line:2",
                category="mixed",
                confidence="probable",
            ),
        ]
        path = tmp_path / "gold_labels.jsonl"
        save_gold_labels(labels, path)

        assert path.exists()
        loaded = load_gold_labels(path)
        assert len(loaded) == 2
        assert loaded[0].line_uid == "line:1"
        assert loaded[0].category == "nirgun_leaning"
        assert loaded[1].category == "mixed"

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_gold_labels(tmp_path / "nonexistent.jsonl")

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "gold.jsonl"
        save_gold_labels([GoldLabel(line_uid="l:1", category="x")], path)
        assert path.exists()

    def test_load_skips_blank_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "gold.jsonl"
        path.write_text(
            '{"line_uid": "line:1", "category": "nirgun_leaning"}\n'
            "\n"
            '{"line_uid": "line:2", "category": "mixed"}\n',
            encoding="utf-8",
        )
        labels = load_gold_labels(path)
        assert len(labels) == 2


# ---------------------------------------------------------------------------
# CategoryMetrics tests
# ---------------------------------------------------------------------------


class TestComputeCategoryMetrics:
    """Tests for compute_category_metrics."""

    def test_perfect_prediction(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="nirgun_leaning"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "nirgun_leaning",
        }
        m = compute_category_metrics(gold, predicted, "nirgun_leaning")
        assert m.true_positives == 2
        assert m.false_positives == 0
        assert m.false_negatives == 0
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0

    def test_all_false_positives(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
        }
        m = compute_category_metrics(gold, predicted, "nirgun_leaning")
        assert m.true_positives == 0
        assert m.false_positives == 1
        assert m.false_negatives == 0
        assert m.precision == 0.0

    def test_all_false_negatives(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        predicted = {
            "line:1": "mixed",
        }
        m = compute_category_metrics(gold, predicted, "nirgun_leaning")
        assert m.true_positives == 0
        assert m.false_positives == 0
        assert m.false_negatives == 1
        assert m.recall == 0.0

    def test_mixed_results(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="nirgun_leaning"),
            GoldLabel(line_uid="line:3", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "mixed",  # FN for nirgun
            "line:3": "nirgun_leaning",  # FP for nirgun
        }
        m = compute_category_metrics(gold, predicted, "nirgun_leaning")
        assert m.true_positives == 1
        assert m.false_positives == 1
        assert m.false_negatives == 1
        assert m.precision == pytest.approx(0.5)
        assert m.recall == pytest.approx(0.5)

    def test_no_predictions(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        m = compute_category_metrics(gold, {}, "nirgun_leaning")
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0

    def test_empty_gold(self) -> None:
        predicted = {"line:1": "nirgun_leaning"}
        m = compute_category_metrics([], predicted, "nirgun_leaning")
        assert m.support == 0
        # No gold labels to check against
        assert m.true_positives == 0

    def test_support_equals_tp_plus_fn(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="nirgun_leaning"),
            GoldLabel(line_uid="line:3", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "mixed",
            "line:3": "nirgun_leaning",
        }
        m = compute_category_metrics(gold, predicted, "nirgun_leaning")
        assert m.support == m.true_positives + m.false_negatives


class TestCategoryMetricsSerialization:
    """Tests for CategoryMetrics serialization."""

    def test_to_dict(self) -> None:
        m = CategoryMetrics(
            category="nirgun_leaning",
            true_positives=8,
            false_positives=2,
            false_negatives=1,
            precision=0.8,
            recall=0.888888,
            f1=0.842105,
            support=9,
        )
        d = m.to_dict()
        assert d["category"] == "nirgun_leaning"
        assert d["precision"] == 0.8
        assert d["recall"] == 0.8889
        assert d["support"] == 9


# ---------------------------------------------------------------------------
# Full evaluation tests
# ---------------------------------------------------------------------------


class TestEvaluate:
    """Tests for evaluate."""

    def test_basic_evaluation(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="mixed"),
            GoldLabel(line_uid="line:3", category="nirgun_leaning"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "nirgun_leaning",
            "line:3": "nirgun_leaning",
        }
        result = evaluate(gold, predicted)
        assert result.total_gold == 3
        assert result.total_aligned == 3
        assert "nirgun_leaning" in result.per_category
        assert "mixed" in result.per_category

    def test_auto_detects_categories(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        predicted = {
            "line:1": "mixed",
        }
        result = evaluate(gold, predicted)
        assert "nirgun_leaning" in result.per_category
        assert "mixed" in result.per_category

    def test_explicit_categories(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        predicted = {"line:1": "nirgun_leaning"}
        result = evaluate(
            gold, predicted,
            categories=["nirgun_leaning", "mixed"],
        )
        assert "nirgun_leaning" in result.per_category
        assert "mixed" in result.per_category

    def test_empty_inputs(self) -> None:
        result = evaluate([], {})
        assert result.total_gold == 0
        assert result.macro_f1 == 0.0

    def test_partial_alignment(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            # line:2 has no prediction
        }
        result = evaluate(gold, predicted)
        assert result.total_gold == 2
        assert result.total_aligned == 1

    def test_macro_averages(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "mixed",
        }
        result = evaluate(gold, predicted)
        # Both categories have perfect scores
        assert result.macro_precision == 1.0
        assert result.macro_recall == 1.0
        assert result.macro_f1 == 1.0


class TestEvaluationResultSerialization:
    """Tests for EvaluationResult.to_dict."""

    def test_to_dict(self) -> None:
        result = EvaluationResult(
            per_category={
                "nirgun_leaning": CategoryMetrics(
                    category="nirgun_leaning",
                    true_positives=5,
                    false_positives=1,
                    false_negatives=1,
                    precision=0.833,
                    recall=0.833,
                    f1=0.833,
                    support=6,
                ),
            },
            macro_precision=0.833,
            macro_recall=0.833,
            macro_f1=0.833,
            total_gold=10,
            total_aligned=10,
        )
        d = result.to_dict()
        assert "per_category" in d
        assert "macro_precision" in d
        assert d["total_gold"] == 10


# ---------------------------------------------------------------------------
# Threshold sweep tests
# ---------------------------------------------------------------------------


class TestThresholdSweep:
    """Tests for threshold_sweep."""

    def test_basic_sweep(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="mixed"),
        ]
        variants = {
            "strict": {"line:1": "nirgun_leaning", "line:2": None},
            "loose": {
                "line:1": "nirgun_leaning",
                "line:2": "nirgun_leaning",
            },
        }
        points = threshold_sweep(gold, variants)
        assert len(points) == 2
        assert points[0].threshold_name == "loose"
        assert points[1].threshold_name == "strict"

    def test_empty_variants(self) -> None:
        gold = [GoldLabel(line_uid="line:1", category="nirgun_leaning")]
        points = threshold_sweep(gold, {})
        assert points == []

    def test_sweep_point_serialization(self) -> None:
        result = EvaluationResult(
            per_category={},
            macro_precision=0.5,
            macro_recall=0.5,
            macro_f1=0.5,
            total_gold=1,
            total_aligned=1,
        )
        point = ThresholdSweepPoint(
            threshold_name="v1", metrics=result,
        )
        d = point.to_dict()
        assert d["threshold_name"] == "v1"
        assert "metrics" in d


# ---------------------------------------------------------------------------
# Error analysis tests
# ---------------------------------------------------------------------------


class TestCollectErrors:
    """Tests for collect_errors."""

    def test_no_errors(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        predicted = {"line:1": "nirgun_leaning"}
        errors = collect_errors(gold, predicted)
        assert errors == []

    def test_collects_mismatches(self) -> None:
        gold = [
            GoldLabel(
                line_uid="line:1",
                category="nirgun_leaning",
                confidence="certain",
                notes="Clear nirgun",
            ),
            GoldLabel(
                line_uid="line:2",
                category="mixed",
            ),
        ]
        predicted = {
            "line:1": "mixed",
            "line:2": "mixed",
        }
        errors = collect_errors(gold, predicted)
        assert len(errors) == 1
        assert errors[0].line_uid == "line:1"
        assert errors[0].gold_category == "nirgun_leaning"
        assert errors[0].predicted_category == "mixed"
        assert errors[0].notes == "Clear nirgun"

    def test_missing_prediction(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        errors = collect_errors(gold, {})
        assert len(errors) == 1
        assert errors[0].predicted_category is None

    def test_error_record_serialization(self) -> None:
        err = ErrorRecord(
            line_uid="line:1",
            gold_category="nirgun_leaning",
            predicted_category="mixed",
            confidence="certain",
            notes="Test",
        )
        d = err.to_dict()
        assert d["line_uid"] == "line:1"
        assert d["gold_category"] == "nirgun_leaning"
        assert d["predicted_category"] == "mixed"


class TestConfusionMatrix:
    """Tests for error_confusion_matrix."""

    def test_basic_matrix(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
            GoldLabel(line_uid="line:2", category="nirgun_leaning"),
            GoldLabel(line_uid="line:3", category="mixed"),
        ]
        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "mixed",
            "line:3": "mixed",
        }
        matrix = error_confusion_matrix(gold, predicted)
        assert matrix["nirgun_leaning"]["nirgun_leaning"] == 1
        assert matrix["nirgun_leaning"]["mixed"] == 1
        assert matrix["mixed"]["mixed"] == 1

    def test_missing_predictions(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        matrix = error_confusion_matrix(gold, {})
        assert matrix["nirgun_leaning"]["MISSING"] == 1

    def test_none_prediction_becomes_unclassified(self) -> None:
        gold = [
            GoldLabel(line_uid="line:1", category="nirgun_leaning"),
        ]
        predicted = {"line:1": None}
        matrix = error_confusion_matrix(gold, predicted)
        assert matrix["nirgun_leaning"]["unclassified"] == 1


# ---------------------------------------------------------------------------
# CSV report tests
# ---------------------------------------------------------------------------


class TestGenerateEvaluationCsv:
    """Tests for generate_evaluation_csv."""

    def test_basic_csv(self) -> None:
        result = EvaluationResult(
            per_category={
                "nirgun_leaning": CategoryMetrics(
                    category="nirgun_leaning",
                    true_positives=8,
                    false_positives=2,
                    false_negatives=1,
                    precision=0.8,
                    recall=0.888,
                    f1=0.842,
                    support=9,
                ),
            },
            macro_precision=0.8,
            macro_recall=0.888,
            macro_f1=0.842,
            total_gold=9,
            total_aligned=9,
        )
        csv_text = generate_evaluation_csv(result)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)

        # One category row + macro row
        assert len(rows) == 2
        assert rows[0]["category"] == "nirgun_leaning"
        assert rows[0]["precision"] == "0.8"
        assert rows[1]["category"] == "MACRO"

    def test_empty_result(self) -> None:
        result = EvaluationResult(
            per_category={},
            macro_precision=0.0,
            macro_recall=0.0,
            macro_f1=0.0,
            total_gold=0,
            total_aligned=0,
        )
        csv_text = generate_evaluation_csv(result)
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 1  # Just MACRO row


# ---------------------------------------------------------------------------
# Stratified sampling tests
# ---------------------------------------------------------------------------


class TestStratifiedSample:
    """Tests for stratified_sample."""

    def test_basic_sample(self) -> None:
        records = [
            {
                "line_uid": f"line:{i}",
                "ang": i,
                "meta": {"author": "Guru Nanak"},
            }
            for i in range(100)
        ]
        sample = stratified_sample(records, target_size=10)
        assert len(sample) == 10

    def test_multiple_authors(self) -> None:
        records = []
        for i in range(50):
            records.append({
                "line_uid": f"nanak:{i}",
                "ang": i,
                "meta": {"author": "Guru Nanak"},
            })
        for i in range(50):
            records.append({
                "line_uid": f"kabir:{i}",
                "ang": i + 50,
                "meta": {"author": "Kabir"},
            })

        sample = stratified_sample(records, target_size=20)
        assert len(sample) == 20

        # Both authors should be represented
        authors = {r["meta"]["author"] for r in sample}
        assert "Guru Nanak" in authors
        assert "Kabir" in authors

    def test_proportional_representation(self) -> None:
        records = []
        # 90 Nanak, 10 Kabir
        for i in range(90):
            records.append({
                "line_uid": f"nanak:{i}",
                "meta": {"author": "Guru Nanak"},
            })
        for i in range(10):
            records.append({
                "line_uid": f"kabir:{i}",
                "meta": {"author": "Kabir"},
            })

        sample = stratified_sample(records, target_size=20)
        nanak_count = sum(
            1 for r in sample
            if r["meta"]["author"] == "Guru Nanak"
        )
        kabir_count = sum(
            1 for r in sample
            if r["meta"]["author"] == "Kabir"
        )

        # Should be roughly proportional (90/10 -> ~18/2)
        assert nanak_count > kabir_count
        assert kabir_count >= 1  # At least 1 from minority group

    def test_empty_records(self) -> None:
        sample = stratified_sample([], target_size=10)
        assert sample == []

    def test_zero_target(self) -> None:
        records = [{"line_uid": "line:1", "meta": {}}]
        sample = stratified_sample(records, target_size=0)
        assert sample == []

    def test_target_larger_than_corpus(self) -> None:
        records = [
            {"line_uid": f"line:{i}", "meta": {}}
            for i in range(5)
        ]
        sample = stratified_sample(records, target_size=100)
        assert len(sample) <= 5

    def test_deterministic_with_seed(self) -> None:
        records = [
            {"line_uid": f"line:{i}", "meta": {"author": "Guru Nanak"}}
            for i in range(100)
        ]
        s1 = stratified_sample(records, target_size=10, seed=42)
        s2 = stratified_sample(records, target_size=10, seed=42)
        assert [r["line_uid"] for r in s1] == [
            r["line_uid"] for r in s2
        ]

    def test_different_seeds_different_results(self) -> None:
        records = [
            {"line_uid": f"line:{i}", "meta": {"author": "Guru Nanak"}}
            for i in range(100)
        ]
        s1 = stratified_sample(records, target_size=10, seed=42)
        s2 = stratified_sample(records, target_size=10, seed=99)
        uids1 = {r["line_uid"] for r in s1}
        uids2 = {r["line_uid"] for r in s2}
        # Very unlikely to be identical with different seeds
        assert uids1 != uids2


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    """Tests for run_evaluation."""

    def test_end_to_end(self, tmp_path: Path) -> None:
        # Write gold file
        gold_path = tmp_path / "gold_labels.jsonl"
        labels = [
            GoldLabel(
                line_uid="line:1",
                category="nirgun_leaning",
            ),
            GoldLabel(
                line_uid="line:2",
                category="mixed",
            ),
        ]
        save_gold_labels(labels, gold_path)

        predicted = {
            "line:1": "nirgun_leaning",
            "line:2": "nirgun_leaning",
        }

        output_dir = tmp_path / "eval_output"
        result = run_evaluation(
            gold_path, predicted, output_dir=output_dir,
        )

        assert result.total_gold == 2
        assert (output_dir / "evaluation_metrics.csv").exists()
        assert (output_dir / "evaluation_errors.jsonl").exists()
        assert (output_dir / "confusion_matrix.json").exists()

    def test_no_output_dir(self, tmp_path: Path) -> None:
        gold_path = tmp_path / "gold.jsonl"
        save_gold_labels(
            [GoldLabel(line_uid="line:1", category="nirgun_leaning")],
            gold_path,
        )
        predicted = {"line:1": "nirgun_leaning"}
        result = run_evaluation(gold_path, predicted)
        assert result.total_gold == 1

    def test_no_errors_no_error_file(self, tmp_path: Path) -> None:
        gold_path = tmp_path / "gold.jsonl"
        save_gold_labels(
            [GoldLabel(line_uid="line:1", category="nirgun_leaning")],
            gold_path,
        )
        predicted = {"line:1": "nirgun_leaning"}
        output_dir = tmp_path / "eval"
        run_evaluation(
            gold_path, predicted, output_dir=output_dir,
        )
        # No errors -> errors file should not exist
        assert not (output_dir / "evaluation_errors.jsonl").exists()
