"""Parallel execution framework — ProcessPoolExecutor (bd-tun.4).

Provides a generic parallel execution wrapper for computationally intensive
pipeline phases. Results from all workers are merged and sorted to ensure
deterministic, byte-identical output regardless of worker count or
completion order.

Parallelism strategy (PLAN.md Section 9):
  - Phase 1 (Lexical): Parallel by ang
  - Phase 2 (Structural): Parallel by ang
  - Phase 3 (Tagging): Parallel by shabad
  - Phase 0, Bundle: Sequential (rate-limited / aggregation)

Reference: PLAN.md Section 9
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, TypeVar

from rich.console import Console

from ggs.pipeline.errors import FatalPipelineError

_console = Console()

T = TypeVar("T")
R = TypeVar("R")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParallelConfig:
    """Configuration for parallel execution.

    Attributes:
        workers: Number of worker processes. None means cpu_count().
            Set to 1 for debugging (sequential execution with easier
            stack traces).
    """

    workers: int | None = None

    @property
    def effective_workers(self) -> int:
        """Return the actual number of workers to use."""
        if self.workers is not None and self.workers >= 1:
            return self.workers
        return os.cpu_count() or 1

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ParallelConfig:
        """Parse from the ``parallelism`` section of config.yaml."""
        workers = config.get("workers")
        if workers is not None:
            workers = int(workers)
        return cls(workers=workers)


# ---------------------------------------------------------------------------
# Worker result
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WorkerResult:
    """Result from a single worker partition.

    Attributes:
        partition_key: Identifier for this partition (e.g. ang number).
        result: The actual result data from the worker function.
        error: Exception if the worker failed, None if successful.
        elapsed_seconds: Wall-clock time for this worker.
    """

    partition_key: str
    result: Any = None
    error: Exception | None = None
    elapsed_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Partitioning helpers
# ---------------------------------------------------------------------------


def partition_by_key(
    records: list[dict[str, Any]],
    key: str,
) -> dict[str, list[dict[str, Any]]]:
    """Partition records into groups by a key field.

    Args:
        records: List of record dicts.
        key: The field name to group by (e.g. "ang", "shabad_uid").

    Returns:
        Mapping from key value (as string) to list of records.
    """
    partitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        k = rec.get(key)
        if k is not None:
            partitions[str(k)].append(rec)
    return dict(partitions)


def partition_by_ang(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Partition corpus records by ang number.

    Args:
        records: Corpus record dicts.

    Returns:
        Mapping from ang number (as string) to records for that ang.
    """
    return partition_by_key(records, "ang")


def partition_by_shabad(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Partition corpus records by shabad_uid.

    Falls back to ang-based grouping if shabad_uid is not available.

    Args:
        records: Corpus record dicts.

    Returns:
        Mapping from shabad_uid to records.
    """
    partitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        shabad_uid = rec.get("meta", {}).get("shabad_uid")
        if shabad_uid is None:
            ang = rec.get("ang")
            shabad_uid = f"ang:{ang}" if ang is not None else "unknown"
        partitions[shabad_uid].append(rec)
    return dict(partitions)


# ---------------------------------------------------------------------------
# Core parallel runner
# ---------------------------------------------------------------------------


def run_parallel(
    func: Callable[[str, list[dict[str, Any]]], Any],
    partitions: dict[str, list[dict[str, Any]]],
    *,
    workers: int | None = None,
    phase_name: str = "parallel",
) -> list[WorkerResult]:
    """Execute a function across partitions in parallel.

    Each partition is submitted as a separate task to ProcessPoolExecutor.
    Results are collected and returned sorted by partition_key for
    deterministic output.

    Args:
        func: Worker function taking (partition_key, records) -> result.
        partitions: Mapping from partition key to record list.
        workers: Number of worker processes (None = cpu_count()).
        phase_name: Name for logging purposes.

    Returns:
        List of :class:`WorkerResult` sorted by partition_key.

    Raises:
        FatalPipelineError: If any worker raises FatalPipelineError.
    """
    if not partitions:
        return []

    effective_workers = workers if workers and workers >= 1 else (os.cpu_count() or 1)

    # For single worker, run sequentially (better debugging)
    if effective_workers == 1:
        return _run_sequential(func, partitions, phase_name)

    return _run_parallel(
        func, partitions, effective_workers, phase_name,
    )


def _run_sequential(
    func: Callable[[str, list[dict[str, Any]]], Any],
    partitions: dict[str, list[dict[str, Any]]],
    phase_name: str,
) -> list[WorkerResult]:
    """Run partitions sequentially (workers=1 mode)."""
    results: list[WorkerResult] = []

    _console.print(
        f"  [{phase_name}] Running {len(partitions)} partitions "
        f"sequentially (workers=1)",
    )

    for key in sorted(partitions.keys()):
        t0 = time.monotonic()
        try:
            result = func(key, partitions[key])
            elapsed = time.monotonic() - t0
            results.append(
                WorkerResult(
                    partition_key=key,
                    result=result,
                    elapsed_seconds=elapsed,
                ),
            )
        except FatalPipelineError:
            raise
        except Exception as e:
            elapsed = time.monotonic() - t0
            results.append(
                WorkerResult(
                    partition_key=key,
                    error=e,
                    elapsed_seconds=elapsed,
                ),
            )

    return results


def _run_parallel(
    func: Callable[[str, list[dict[str, Any]]], Any],
    partitions: dict[str, list[dict[str, Any]]],
    workers: int,
    phase_name: str,
) -> list[WorkerResult]:
    """Run partitions using ProcessPoolExecutor."""
    results: list[WorkerResult] = []

    _console.print(
        f"  [{phase_name}] Running {len(partitions)} partitions "
        f"with {workers} workers",
    )

    with ProcessPoolExecutor(max_workers=workers) as pool:
        # Submit all tasks
        future_to_key: dict[Future[Any], str] = {}
        start_times: dict[str, float] = {}

        for key in sorted(partitions.keys()):
            start_times[key] = time.monotonic()
            future = pool.submit(func, key, partitions[key])
            future_to_key[future] = key

        # Collect results as they complete
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            elapsed = time.monotonic() - start_times[key]

            try:
                result = future.result()
                results.append(
                    WorkerResult(
                        partition_key=key,
                        result=result,
                        elapsed_seconds=elapsed,
                    ),
                )
            except FatalPipelineError:
                # Cancel remaining futures
                for f in future_to_key:
                    f.cancel()
                raise
            except Exception as e:
                results.append(
                    WorkerResult(
                        partition_key=key,
                        error=e,
                        elapsed_seconds=elapsed,
                    ),
                )

    # Sort by partition_key for deterministic output
    results.sort(key=lambda r: r.partition_key)
    return results


# ---------------------------------------------------------------------------
# Result merging
# ---------------------------------------------------------------------------


def merge_results(
    worker_results: list[WorkerResult],
    *,
    sort_key: str | None = None,
) -> list[Any]:
    """Merge successful worker results into a single sorted list.

    Concatenates all result lists and sorts by ``sort_key`` if provided,
    ensuring deterministic output regardless of worker completion order.

    Args:
        worker_results: Results from :func:`run_parallel`.
        sort_key: If provided, sort the merged list by this dict key.

    Returns:
        Merged, sorted list of results.

    Raises:
        FatalPipelineError: If any worker failed.
    """
    failed = [
        wr for wr in worker_results if not wr.success
    ]
    if failed:
        error_msgs = [
            f"  {wr.partition_key}: {wr.error}"
            for wr in failed
        ]
        raise FatalPipelineError(
            f"{len(failed)} worker(s) failed:\n"
            + "\n".join(error_msgs),
            error_type="WORKER_FAILURE",
        )

    merged: list[Any] = []
    for wr in worker_results:
        if isinstance(wr.result, list):
            merged.extend(wr.result)
        else:
            merged.append(wr.result)

    if sort_key is not None:
        merged.sort(
            key=lambda x: x.get(sort_key, "") if isinstance(x, dict) else "",
        )

    return merged


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def summarize_parallel_run(
    worker_results: list[WorkerResult],
    phase_name: str,
) -> dict[str, Any]:
    """Generate a summary of a parallel run for logging/manifest.

    Args:
        worker_results: Results from :func:`run_parallel`.
        phase_name: Name of the phase.

    Returns:
        Summary dict with timing and success/failure counts.
    """
    total = len(worker_results)
    succeeded = sum(1 for wr in worker_results if wr.success)
    failed = total - succeeded

    total_elapsed = sum(wr.elapsed_seconds for wr in worker_results)
    max_elapsed = max(
        (wr.elapsed_seconds for wr in worker_results),
        default=0.0,
    )

    summary = {
        "phase": phase_name,
        "total_partitions": total,
        "succeeded": succeeded,
        "failed": failed,
        "total_worker_seconds": round(total_elapsed, 3),
        "max_worker_seconds": round(max_elapsed, 3),
    }

    if failed > 0:
        summary["failed_partitions"] = [
            wr.partition_key
            for wr in worker_results
            if not wr.success
        ]

    _console.print(
        f"  [{phase_name}] {succeeded}/{total} partitions succeeded "
        f"(max worker time: {max_elapsed:.2f}s)",
    )

    return summary
