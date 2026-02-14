"""Run manifest generation — provenance anchor for every pipeline run (bd-tun.3).

The run manifest records exactly what was run, with what inputs, producing
what outputs.  It enables reproducibility, integrity verification, debugging,
and incremental caching.

Usage::

    manifest = RunManifest(phase="corpus", config_path=Path("config/config.yaml"))
    manifest.record_input(Path("data/raw_html/"))
    # ... do work ...
    manifest.record_output(Path("data/corpus/ggs_lines.jsonl"))
    manifest.set_record_counts(total_input_lines=60403, total_matches=0)
    manifest.set_error_summary(
        errors=0, warnings=14,
        warning_types={"HIGH_TOKEN_COUNT": 14},
    )
    manifest.finalize(Path("data/corpus/run_manifest.json"))
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ggs import __version__

# ---------------------------------------------------------------------------
# Hashing utility
# ---------------------------------------------------------------------------


def file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest for a single file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(8192):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def dir_sha256(directory: Path) -> str:
    """Compute a deterministic SHA-256 over all files in *directory*.

    Files are sorted by relative path to ensure determinism regardless
    of filesystem ordering.
    """
    h = hashlib.sha256()
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            h.update(str(file_path.relative_to(directory)).encode())
            with file_path.open("rb") as fh:
                while chunk := fh.read(8192):
                    h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _get_git_commit() -> str | None:
    """Return the current short git commit hash, or *None* if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return None


# ---------------------------------------------------------------------------
# Run manifest builder
# ---------------------------------------------------------------------------


class RunManifest:
    """Builder for ``run_manifest.json`` provenance files.

    Args:
        phase: Pipeline phase name (e.g. ``"corpus"``, ``"lexical"``).
        config_path: Path to the configuration file used for this run.
        schema_version: Schema version string for the manifest itself.
    """

    def __init__(
        self,
        phase: str,
        *,
        config_path: Path | None = None,
        schema_version: str = "1.0.0",
    ) -> None:
        self.phase = phase
        self.schema_version = schema_version
        self._start_time = time.monotonic()
        self._generated_at = datetime.now(UTC).isoformat()
        self._git_commit = _get_git_commit()

        self._config_hash: str | None = None
        if config_path is not None and config_path.exists():
            self._config_hash = file_sha256(config_path)

        self._input_hashes: dict[str, str] = {}
        self._output_hashes: dict[str, str] = {}
        self._lexicon_hashes: dict[str, str] = {}
        self._record_counts: dict[str, int] = {}
        self._error_summary: dict[str, Any] = {}
        self._extra: dict[str, Any] = {}

    # -- Input / output tracking ---------------------------------------------

    def record_input(self, path: Path) -> str:
        """Compute and store the hash of an input file or directory.

        Returns the computed hash string.
        """
        name = path.name
        h = dir_sha256(path) if path.is_dir() else file_sha256(path)
        self._input_hashes[name] = h
        return h

    def record_output(self, path: Path) -> str:
        """Compute and store the hash of an output file.

        Returns the computed hash string.
        """
        h = file_sha256(path)
        self._output_hashes[path.name] = h
        return h

    def record_lexicon(self, name: str, path: Path) -> str:
        """Compute and store the hash of a lexicon file.

        Returns the computed hash string.
        """
        h = file_sha256(path)
        self._lexicon_hashes[name] = h
        return h

    # -- Metadata setters ----------------------------------------------------

    def set_record_counts(self, **counts: int) -> None:
        """Set record counts (total_input_lines, total_matches, etc.)."""
        self._record_counts.update(counts)

    def set_error_summary(
        self,
        *,
        errors: int = 0,
        warnings: int = 0,
        warning_types: dict[str, int] | None = None,
    ) -> None:
        """Set error/warning summary from :class:`ErrorCollector.finalize`."""
        self._error_summary = {
            "errors": errors,
            "warnings": warnings,
            "warning_types": warning_types or {},
        }

    def set_extra(self, key: str, value: Any) -> None:
        """Store arbitrary extra metadata in the manifest."""
        self._extra[key] = value

    # -- Finalization --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Build the manifest as a JSON-serializable dict."""
        wall_clock = time.monotonic() - self._start_time
        manifest: dict[str, Any] = {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "generator_version": __version__,
            "generated_at": self._generated_at,
            "git_commit": self._git_commit,
            "wall_clock_seconds": round(wall_clock, 3),
        }
        if self._config_hash is not None:
            manifest["config_hash"] = self._config_hash
        if self._input_hashes:
            manifest["input_hashes"] = dict(self._input_hashes)
        if self._lexicon_hashes:
            manifest["lexicon_hashes"] = dict(self._lexicon_hashes)
        if self._output_hashes:
            manifest["output_artifact_hashes"] = dict(self._output_hashes)
        if self._record_counts:
            manifest["record_counts"] = dict(self._record_counts)
        if self._error_summary:
            manifest["error_summary"] = dict(self._error_summary)
        if self._extra:
            manifest.update(self._extra)
        return manifest

    def finalize(self, output_path: Path) -> dict[str, Any]:
        """Write the manifest to *output_path* and return its dict form.

        Creates parent directories if they don't exist.
        """
        manifest = self.to_dict()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        return manifest
