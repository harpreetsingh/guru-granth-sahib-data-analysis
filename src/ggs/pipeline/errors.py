"""Pipeline error model — FATAL / ERROR / WARNING severity levels (bd-tun.1).

Uniform error handling contract for all pipeline phases.  Provides:
  - ``Severity`` enum (FATAL, ERROR, WARNING)
  - ``PipelineError`` / ``FatalPipelineError`` exceptions
  - ``ErrorRecord`` dataclass for structured error logging
  - ``ErrorCollector`` accumulator that writes to ``<phase>_errors.jsonl``
    and enforces the max-errors threshold

Usage::

    collector = ErrorCollector(phase="lexical", config=cfg)
    try:
        process(record)
    except RecoverableError as exc:
        collector.record_error(
            line_uid=record["line_uid"],
            error_type="PARSE_FAILURE",
            message=str(exc),
            context={"ang": record["ang"]},
        )
    collector.finalize()   # writes JSONL, returns summary for manifest
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from rich.console import Console

_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    """Pipeline error severity levels (PLAN.md Section 2.1)."""

    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class PipelineError(Exception):
    """Base exception for all pipeline errors.

    Carries structured metadata so callers can convert to an
    ``ErrorRecord`` without losing information.
    """

    def __init__(
        self,
        message: str,
        *,
        severity: Severity = Severity.ERROR,
        error_type: str = "UNKNOWN",
        line_uid: str | None = None,
        phase: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.severity = severity
        self.error_type = error_type
        self.line_uid = line_uid
        self.phase = phase
        self.context = context or {}


class FatalPipelineError(PipelineError):
    """Pipeline cannot continue.  Abort immediately.

    Examples: missing input file, schema validation failure,
    corpus integrity violation.
    """

    def __init__(
        self,
        message: str,
        *,
        error_type: str = "FATAL_ERROR",
        phase: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            severity=Severity.FATAL,
            error_type=error_type,
            phase=phase,
            context=context,
        )


# ---------------------------------------------------------------------------
# Error record (written to <phase>_errors.jsonl)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    """Structured error record matching the schema in PLAN.md Section 2.1.

    Written to ``<phase>_errors.jsonl`` for post-run analysis.
    """

    line_uid: str | None
    phase: str
    severity: str  # Severity value
    error_type: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Error handling configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ErrorConfig:
    """Configuration for error handling (``error_handling:`` in config.yaml).

    Attributes:
        max_record_errors: Maximum ERROR-severity records before aborting.
            Default 100 — exceeding this suggests a systematic issue,
            not isolated bad records.
        strict_mode: If *True*, treat WARNINGs as ERRORs.
    """

    max_record_errors: int = 100
    strict_mode: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ErrorConfig:
        """Create from the ``error_handling:`` section of config.yaml."""
        return cls(
            max_record_errors=int(data.get("max_record_errors", 100)),
            strict_mode=bool(data.get("strict_mode", False)),
        )


# ---------------------------------------------------------------------------
# Error collector
# ---------------------------------------------------------------------------


class ErrorCollector:
    """Accumulates errors and warnings during a pipeline phase.

    Writes ERROR records to ``<phase>_errors.jsonl`` on :meth:`finalize`.
    Enforces the max-errors threshold and ``strict_mode`` escalation.

    Args:
        phase: Pipeline phase name (e.g. ``"corpus"``, ``"lexical"``).
        config: Error handling configuration.
        output_dir: Directory for the ``<phase>_errors.jsonl`` file.
            If *None*, errors are accumulated in memory but not written.
    """

    def __init__(
        self,
        phase: str,
        *,
        config: ErrorConfig | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.phase = phase
        self.config = config or ErrorConfig()
        self.output_dir = output_dir

        self._errors: list[ErrorRecord] = []
        self._warnings: list[ErrorRecord] = []
        self._warning_types: dict[str, int] = {}

    # -- Public API ----------------------------------------------------------

    @property
    def error_count(self) -> int:
        """Number of ERROR-severity records accumulated."""
        return len(self._errors)

    @property
    def warning_count(self) -> int:
        """Number of WARNING-severity records accumulated."""
        return len(self._warnings)

    @property
    def warning_type_counts(self) -> dict[str, int]:
        """Mapping of warning type to count, for manifest summary."""
        return dict(self._warning_types)

    def record_error(
        self,
        *,
        error_type: str,
        message: str,
        line_uid: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an ERROR-severity event.

        Raises ``FatalPipelineError`` if the error count exceeds the
        configured ``max_record_errors`` threshold.
        """
        record = ErrorRecord(
            line_uid=line_uid,
            phase=self.phase,
            severity=Severity.ERROR,
            error_type=error_type,
            message=message,
            context=context or {},
        )
        self._errors.append(record)
        _console.print(
            f"  [red]ERROR[/red] [{self.phase}] {error_type}: {message}"
        )

        if self.error_count > self.config.max_record_errors:
            raise FatalPipelineError(
                f"Error count ({self.error_count}) exceeds threshold "
                f"({self.config.max_record_errors}). Aborting — this likely "
                f"indicates a systematic issue, not isolated bad records.",
                error_type="ERROR_THRESHOLD_EXCEEDED",
                phase=self.phase,
                context={"error_count": self.error_count},
            )

    def record_warning(
        self,
        *,
        warning_type: str,
        message: str,
        line_uid: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record a WARNING-severity event.

        If ``strict_mode`` is enabled, escalates to :meth:`record_error`.
        """
        if self.config.strict_mode:
            self.record_error(
                error_type=warning_type,
                message=f"[strict_mode] {message}",
                line_uid=line_uid,
                context=context,
            )
            return

        record = ErrorRecord(
            line_uid=line_uid,
            phase=self.phase,
            severity=Severity.WARNING,
            error_type=warning_type,
            message=message,
            context=context or {},
        )
        self._warnings.append(record)
        self._warning_types[warning_type] = self._warning_types.get(warning_type, 0) + 1
        _console.print(
            f"  [yellow]WARN[/yellow]  [{self.phase}] {warning_type}: {message}"
        )

    def finalize(self) -> dict[str, Any]:
        """Write accumulated errors to JSONL and return a summary dict.

        The summary dict is suitable for inclusion in ``run_manifest.json``::

            {
                "errors": <int>,
                "warnings": <int>,
                "warning_types": {"HIGH_TOKEN_COUNT": 14, ...}
            }
        """
        if self.output_dir is not None and self._errors:
            errors_path = self.output_dir / f"{self.phase}_errors.jsonl"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with errors_path.open("w", encoding="utf-8") as fh:
                for record in self._errors:
                    fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            _console.print(
                f"  Wrote {len(self._errors)} error(s) to {errors_path}"
            )

        return {
            "errors": self.error_count,
            "warnings": self.warning_count,
            "warning_types": dict(self._warning_types),
        }
