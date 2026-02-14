"""Parallel execution framework tests (bd-tun.4).

Tests partitioning, sequential/parallel execution, result merging,
error handling, and configuration parsing.
"""

from __future__ import annotations

import pytest

from ggs.pipeline.errors import FatalPipelineError
from ggs.pipeline.parallel import (
    ParallelConfig,
    WorkerResult,
    merge_results,
    partition_by_ang,
    partition_by_key,
    partition_by_shabad,
    run_parallel,
    summarize_parallel_run,
)

# ---------------------------------------------------------------------------
# Test worker functions (module-level for pickling)
# ---------------------------------------------------------------------------


def _double_records(key: str, records: list[dict]) -> list[dict]:
    """Test worker: return records with doubled 'value' field."""
    return [
        {**r, "value": r.get("value", 0) * 2, "partition": key}
        for r in records
    ]


def _failing_worker(key: str, records: list[dict]) -> list[dict]:
    """Test worker that always raises."""
    msg = f"Worker failed on {key}"
    raise ValueError(msg)


def _identity_worker(key: str, records: list[dict]) -> list[dict]:
    """Test worker: return records as-is."""
    return list(records)


# ---------------------------------------------------------------------------
# ParallelConfig tests
# ---------------------------------------------------------------------------


class TestParallelConfig:
    """Tests for ParallelConfig."""

    def test_default_workers(self) -> None:
        config = ParallelConfig()
        assert config.effective_workers >= 1

    def test_explicit_workers(self) -> None:
        config = ParallelConfig(workers=4)
        assert config.effective_workers == 4

    def test_from_config_with_workers(self) -> None:
        config = ParallelConfig.from_config({"workers": 8})
        assert config.workers == 8

    def test_from_config_null_workers(self) -> None:
        config = ParallelConfig.from_config({"workers": None})
        assert config.workers is None
        assert config.effective_workers >= 1

    def test_from_config_empty(self) -> None:
        config = ParallelConfig.from_config({})
        assert config.workers is None


# ---------------------------------------------------------------------------
# WorkerResult tests
# ---------------------------------------------------------------------------


class TestWorkerResult:
    """Tests for WorkerResult."""

    def test_success(self) -> None:
        wr = WorkerResult(
            partition_key="ang:1",
            result=[{"a": 1}],
        )
        assert wr.success
        assert wr.error is None

    def test_failure(self) -> None:
        wr = WorkerResult(
            partition_key="ang:1",
            error=ValueError("failed"),
        )
        assert not wr.success


# ---------------------------------------------------------------------------
# Partitioning tests
# ---------------------------------------------------------------------------


class TestPartitionByKey:
    """Tests for partition_by_key."""

    def test_basic_partitioning(self) -> None:
        records = [
            {"ang": 1, "text": "a"},
            {"ang": 1, "text": "b"},
            {"ang": 2, "text": "c"},
        ]
        partitions = partition_by_key(records, "ang")
        assert len(partitions) == 2
        assert len(partitions["1"]) == 2
        assert len(partitions["2"]) == 1

    def test_missing_key(self) -> None:
        records = [
            {"text": "no key"},
            {"ang": 1, "text": "has key"},
        ]
        partitions = partition_by_key(records, "ang")
        assert len(partitions) == 1
        assert "1" in partitions

    def test_empty_records(self) -> None:
        partitions = partition_by_key([], "ang")
        assert partitions == {}


class TestPartitionByAng:
    """Tests for partition_by_ang."""

    def test_partitions_by_ang(self) -> None:
        records = [
            {"ang": 1, "line_uid": "a"},
            {"ang": 1, "line_uid": "b"},
            {"ang": 2, "line_uid": "c"},
            {"ang": 3, "line_uid": "d"},
        ]
        partitions = partition_by_ang(records)
        assert len(partitions) == 3
        assert len(partitions["1"]) == 2


class TestPartitionByShabad:
    """Tests for partition_by_shabad."""

    def test_uses_shabad_uid(self) -> None:
        records = [
            {
                "line_uid": "a",
                "meta": {"shabad_uid": "shabad:1"},
            },
            {
                "line_uid": "b",
                "meta": {"shabad_uid": "shabad:1"},
            },
            {
                "line_uid": "c",
                "meta": {"shabad_uid": "shabad:2"},
            },
        ]
        partitions = partition_by_shabad(records)
        assert len(partitions) == 2
        assert len(partitions["shabad:1"]) == 2

    def test_fallback_to_ang(self) -> None:
        records = [
            {"line_uid": "a", "ang": 5, "meta": {}},
            {"line_uid": "b", "ang": 5, "meta": {}},
        ]
        partitions = partition_by_shabad(records)
        assert "ang:5" in partitions
        assert len(partitions["ang:5"]) == 2

    def test_fallback_to_unknown(self) -> None:
        records = [
            {"line_uid": "a", "meta": {}},
        ]
        partitions = partition_by_shabad(records)
        assert "unknown" in partitions


# ---------------------------------------------------------------------------
# run_parallel tests (sequential mode for testing)
# ---------------------------------------------------------------------------


class TestRunParallel:
    """Tests for run_parallel (using workers=1 for testing)."""

    def test_sequential_execution(self) -> None:
        partitions = {
            "1": [{"value": 5}],
            "2": [{"value": 10}],
        }
        results = run_parallel(
            _double_records, partitions, workers=1,
        )
        assert len(results) == 2
        assert all(wr.success for wr in results)
        assert results[0].partition_key == "1"
        assert results[1].partition_key == "2"

    def test_sorted_by_partition_key(self) -> None:
        partitions = {
            "3": [{"value": 30}],
            "1": [{"value": 10}],
            "2": [{"value": 20}],
        }
        results = run_parallel(
            _identity_worker, partitions, workers=1,
        )
        keys = [wr.partition_key for wr in results]
        assert keys == ["1", "2", "3"]

    def test_empty_partitions(self) -> None:
        results = run_parallel(
            _identity_worker, {}, workers=1,
        )
        assert results == []

    def test_worker_failure_captured(self) -> None:
        partitions = {"1": [{"value": 1}]}
        results = run_parallel(
            _failing_worker, partitions, workers=1,
        )
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error is not None

    def test_fatal_error_propagates(self) -> None:
        def fatal_worker(key: str, records: list[dict]) -> list[dict]:
            raise FatalPipelineError(
                "fatal!", error_type="TEST_FATAL",
            )

        partitions = {"1": [{"value": 1}]}
        with pytest.raises(FatalPipelineError):
            run_parallel(fatal_worker, partitions, workers=1)

    def test_elapsed_time_tracked(self) -> None:
        partitions = {"1": [{"value": 1}]}
        results = run_parallel(
            _identity_worker, partitions, workers=1,
        )
        assert results[0].elapsed_seconds >= 0


# ---------------------------------------------------------------------------
# merge_results tests
# ---------------------------------------------------------------------------


class TestMergeResults:
    """Tests for merge_results."""

    def test_merge_list_results(self) -> None:
        results = [
            WorkerResult(
                partition_key="1",
                result=[{"line_uid": "a"}, {"line_uid": "b"}],
            ),
            WorkerResult(
                partition_key="2",
                result=[{"line_uid": "c"}],
            ),
        ]
        merged = merge_results(results)
        assert len(merged) == 3

    def test_merge_with_sort_key(self) -> None:
        results = [
            WorkerResult(
                partition_key="2",
                result=[{"line_uid": "c"}],
            ),
            WorkerResult(
                partition_key="1",
                result=[{"line_uid": "a"}, {"line_uid": "b"}],
            ),
        ]
        merged = merge_results(results, sort_key="line_uid")
        uids = [r["line_uid"] for r in merged]
        assert uids == ["a", "b", "c"]

    def test_merge_raises_on_failure(self) -> None:
        results = [
            WorkerResult(
                partition_key="1",
                result=[{"a": 1}],
            ),
            WorkerResult(
                partition_key="2",
                error=ValueError("oops"),
            ),
        ]
        with pytest.raises(FatalPipelineError, match="1 worker"):
            merge_results(results)

    def test_merge_empty(self) -> None:
        merged = merge_results([])
        assert merged == []

    def test_merge_non_list_results(self) -> None:
        results = [
            WorkerResult(partition_key="1", result="scalar_a"),
            WorkerResult(partition_key="2", result="scalar_b"),
        ]
        merged = merge_results(results)
        assert merged == ["scalar_a", "scalar_b"]


# ---------------------------------------------------------------------------
# summarize_parallel_run tests
# ---------------------------------------------------------------------------


class TestSummarizeParallelRun:
    """Tests for summarize_parallel_run."""

    def test_all_success(self) -> None:
        results = [
            WorkerResult(
                partition_key="1", result=[], elapsed_seconds=0.1,
            ),
            WorkerResult(
                partition_key="2", result=[], elapsed_seconds=0.2,
            ),
        ]
        summary = summarize_parallel_run(results, "test")
        assert summary["total_partitions"] == 2
        assert summary["succeeded"] == 2
        assert summary["failed"] == 0

    def test_with_failures(self) -> None:
        results = [
            WorkerResult(
                partition_key="1", result=[], elapsed_seconds=0.1,
            ),
            WorkerResult(
                partition_key="2",
                error=ValueError("oops"),
                elapsed_seconds=0.05,
            ),
        ]
        summary = summarize_parallel_run(results, "test")
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1
        assert "2" in summary["failed_partitions"]

    def test_empty_results(self) -> None:
        summary = summarize_parallel_run([], "test")
        assert summary["total_partitions"] == 0
        assert summary["succeeded"] == 0

    def test_timing(self) -> None:
        results = [
            WorkerResult(
                partition_key="1", result=[], elapsed_seconds=1.5,
            ),
            WorkerResult(
                partition_key="2", result=[], elapsed_seconds=2.3,
            ),
        ]
        summary = summarize_parallel_run(results, "test")
        assert summary["max_worker_seconds"] == 2.3
        assert summary["total_worker_seconds"] == 3.8
