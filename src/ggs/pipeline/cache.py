"""Incremental caching — .cache/ with input hashing (bd-tun.2).

Prevents re-running expensive pipeline phases when inputs haven't changed.
Each phase stores a hash of all its inputs alongside output artifact hashes.
Before running, if all input hashes match the cached values and all output
artifacts exist with matching hashes, the phase is skipped entirely.

Cache location: ``.cache/`` at project root (gitignored, ephemeral).

Reference: PLAN.md Section 2
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.pipeline.manifest import file_sha256

_console = Console()

# Default cache directory name
CACHE_DIR_NAME = ".cache"


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CacheEntry:
    """A cache entry recording input/output hashes for one pipeline phase.

    Attributes:
        phase: Pipeline phase name (e.g. "lexical", "structural").
        computed_at: ISO timestamp when this entry was computed.
        input_hashes: Mapping from input name to SHA-256 hash.
        output_hashes: Mapping from output name to SHA-256 hash.
    """

    phase: str
    computed_at: str = ""
    input_hashes: dict[str, str] = field(default_factory=dict)
    output_hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "computed_at": self.computed_at,
            "input_hashes": dict(self.input_hashes),
            "output_hashes": dict(self.output_hashes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Reconstruct a CacheEntry from a JSON-parsed dict."""
        return CacheEntry(
            phase=data.get("phase", ""),
            computed_at=data.get("computed_at", ""),
            input_hashes=dict(data.get("input_hashes", {})),
            output_hashes=dict(data.get("output_hashes", {})),
        )


# ---------------------------------------------------------------------------
# Cache manager
# ---------------------------------------------------------------------------


class PipelineCache:
    """Manages incremental caching for pipeline phases.

    Args:
        cache_dir: Path to the cache directory (default ``.cache/``).
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or Path(CACHE_DIR_NAME)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _cache_path(self, phase: str) -> Path:
        """Get the cache file path for a phase."""
        return self._cache_dir / f"{phase}_input_hash.json"

    def load_entry(self, phase: str) -> CacheEntry | None:
        """Load the cached entry for a phase, if it exists.

        Args:
            phase: Pipeline phase name.

        Returns:
            CacheEntry if cache file exists and is valid, None otherwise.
        """
        path = self._cache_path(phase)
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def save_entry(self, entry: CacheEntry) -> Path:
        """Save a cache entry to disk.

        Args:
            entry: The CacheEntry to persist.

        Returns:
            Path where the entry was written.
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(entry.phase)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(entry.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    def invalidate(self, phase: str) -> bool:
        """Remove the cached entry for a phase.

        Args:
            phase: Pipeline phase name.

        Returns:
            True if a cache entry was removed, False if none existed.
        """
        path = self._cache_path(phase)
        if path.exists():
            path.unlink()
            return True
        return False

    def invalidate_all(self) -> int:
        """Remove all cached entries.

        Returns:
            Number of cache entries removed.
        """
        if not self._cache_dir.exists():
            return 0

        count = 0
        for path in self._cache_dir.glob("*_input_hash.json"):
            path.unlink()
            count += 1
        return count


# ---------------------------------------------------------------------------
# Hash collection helpers
# ---------------------------------------------------------------------------


def compute_input_hashes(
    input_paths: dict[str, Path],
) -> dict[str, str]:
    """Compute SHA-256 hashes for a set of named input files.

    Silently skips paths that don't exist.

    Args:
        input_paths: Mapping from descriptive name to file path.

    Returns:
        Mapping from name to ``sha256:...`` hash string.
    """
    hashes: dict[str, str] = {}
    for name, path in sorted(input_paths.items()):
        if path.exists() and path.is_file():
            hashes[name] = file_sha256(path)
    return hashes


def compute_output_hashes(
    output_paths: dict[str, Path],
) -> dict[str, str]:
    """Compute SHA-256 hashes for a set of named output files.

    Silently skips paths that don't exist.

    Args:
        output_paths: Mapping from descriptive name to file path.

    Returns:
        Mapping from name to ``sha256:...`` hash string.
    """
    hashes: dict[str, str] = {}
    for name, path in sorted(output_paths.items()):
        if path.exists() and path.is_file():
            hashes[name] = file_sha256(path)
    return hashes


# ---------------------------------------------------------------------------
# Cache check
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CacheCheckResult:
    """Result of checking whether a phase can be skipped.

    Attributes:
        phase: Pipeline phase name.
        cache_hit: True if all inputs match and all outputs exist.
        reason: Human-readable explanation of the check result.
        cached_entry: The cached entry if one was found.
    """

    phase: str
    cache_hit: bool
    reason: str
    cached_entry: CacheEntry | None = None


def check_cache(
    phase: str,
    input_hashes: dict[str, str],
    output_paths: dict[str, Path],
    cache: PipelineCache,
    *,
    force: bool = False,
) -> CacheCheckResult:
    """Check whether a phase can be skipped based on cached hashes.

    A cache hit requires:
      1. ``force`` is False
      2. A cached entry exists for this phase
      3. ALL current input hashes match the cached input hashes
      4. ALL expected output files exist
      5. ALL output file hashes match the cached output hashes

    Args:
        phase: Pipeline phase name.
        input_hashes: Current input hashes.
        output_paths: Expected output files.
        cache: The PipelineCache instance.
        force: If True, always return cache miss.

    Returns:
        A :class:`CacheCheckResult`.
    """
    if force:
        return CacheCheckResult(
            phase=phase,
            cache_hit=False,
            reason="--force flag set, bypassing cache",
        )

    cached = cache.load_entry(phase)
    if cached is None:
        return CacheCheckResult(
            phase=phase,
            cache_hit=False,
            reason="no cached entry found",
        )

    # Check input hashes match
    if cached.input_hashes != input_hashes:
        changed_keys = []
        for key in set(cached.input_hashes) | set(input_hashes):
            if cached.input_hashes.get(key) != input_hashes.get(key):
                changed_keys.append(key)
        return CacheCheckResult(
            phase=phase,
            cache_hit=False,
            reason=f"input hashes changed: {', '.join(sorted(changed_keys))}",
            cached_entry=cached,
        )

    # Check all outputs exist
    missing_outputs = [
        name for name, path in output_paths.items()
        if not path.exists()
    ]
    if missing_outputs:
        return CacheCheckResult(
            phase=phase,
            cache_hit=False,
            reason=(
                f"output files missing: {', '.join(sorted(missing_outputs))}"
            ),
            cached_entry=cached,
        )

    # Check output hashes match
    current_output_hashes = compute_output_hashes(output_paths)
    if cached.output_hashes != current_output_hashes:
        changed_outputs = []
        all_keys = set(cached.output_hashes) | set(current_output_hashes)
        for key in all_keys:
            if (
                cached.output_hashes.get(key)
                != current_output_hashes.get(key)
            ):
                changed_outputs.append(key)
        return CacheCheckResult(
            phase=phase,
            cache_hit=False,
            reason=(
                "output hashes changed: "
                f"{', '.join(sorted(changed_outputs))}"
            ),
            cached_entry=cached,
        )

    return CacheCheckResult(
        phase=phase,
        cache_hit=True,
        reason="all input and output hashes match",
        cached_entry=cached,
    )


# ---------------------------------------------------------------------------
# Cache update
# ---------------------------------------------------------------------------


def update_cache(
    phase: str,
    input_hashes: dict[str, str],
    output_paths: dict[str, Path],
    cache: PipelineCache,
) -> CacheEntry:
    """Update the cache after a phase completes successfully.

    Computes output hashes and saves the entry.

    Args:
        phase: Pipeline phase name.
        input_hashes: Input hashes for this run.
        output_paths: Output files produced by this phase.
        cache: The PipelineCache instance.

    Returns:
        The saved CacheEntry.
    """
    output_hashes = compute_output_hashes(output_paths)

    entry = CacheEntry(
        phase=phase,
        computed_at=datetime.now(UTC).isoformat(),
        input_hashes=dict(input_hashes),
        output_hashes=output_hashes,
    )

    path = cache.save_entry(entry)
    _console.print(f"  Cache updated: {path}")

    return entry
