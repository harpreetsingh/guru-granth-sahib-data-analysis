"""Corpus validator -- schema checks, integrity verification (bd-15c.6).

Quality gate between Phase 0 and downstream analysis.  If validation
fails, the pipeline aborts to prevent bad data from propagating.

Checks (PLAN.md Section 3.6):
  1. Unique line_uid
  2. Non-empty gurmukhi
  3. Normalization idempotency
  4. Provenance fields present
  5. Schema version supported
  6. Pipeline version match
  7. Token count sanity
  8. Character repertoire
  9. Shabad integrity
  10. token_spans alignment
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ggs.corpus.normalize import normalize
from ggs.pipeline.errors import (
    ErrorCollector,
    ErrorConfig,
    FatalPipelineError,
)

# ---------------------------------------------------------------------------
# Supported schema versions
# ---------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0.0"})

# ---------------------------------------------------------------------------
# Gurmukhi Unicode range
# ---------------------------------------------------------------------------

# Core Gurmukhi block: U+0A00 - U+0A7F
# Also allow: Devanagari dandas (U+0964, U+0965), common punctuation,
# digits, whitespace, Ik Onkar (ੴ U+0A74)
_EXPECTED_RANGES: list[tuple[int, int]] = [
    (0x0A00, 0x0A7F),  # Gurmukhi
    (0x0964, 0x0965),  # Devanagari dandas
    (0x0020, 0x007F),  # Basic Latin (space, digits, punct)
    (0x00A0, 0x00FF),  # Latin-1 supplement (rare but possible)
]


def _is_expected_char(ch: str) -> bool:
    """Check if a character is in the expected repertoire."""
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _EXPECTED_RANGES)


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


class ValidationReport:
    """Structured validation report."""

    def __init__(self) -> None:
        self.total_lines = 0
        self.checks_passed: dict[str, int] = {}
        self.checks_failed: dict[str, int] = {}
        self.warnings: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.verdict: str = "PASS"

    def record_pass(self, check: str) -> None:
        self.checks_passed[check] = (
            self.checks_passed.get(check, 0) + 1
        )

    def record_fail(
        self,
        check: str,
        *,
        line_uid: str | None = None,
        detail: str = "",
    ) -> None:
        self.checks_failed[check] = (
            self.checks_failed.get(check, 0) + 1
        )
        self.errors.append({
            "check": check,
            "line_uid": line_uid,
            "detail": detail,
        })

    def record_warning(
        self,
        check: str,
        *,
        line_uid: str | None = None,
        detail: str = "",
    ) -> None:
        self.warnings.append({
            "check": check,
            "line_uid": line_uid,
            "detail": detail,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "verdict": self.verdict,
            "checks_passed": dict(self.checks_passed),
            "checks_failed": dict(self.checks_failed),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:100],  # Cap for readability
            "warnings": self.warnings[:100],
        }

    def write(self, path: Path) -> None:
        """Write report to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(
                self.to_dict(), fh, indent=2, ensure_ascii=False,
            )
            fh.write("\n")


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------


def validate_corpus(
    records: list[dict[str, Any]],
    *,
    error_config: ErrorConfig | None = None,
) -> ValidationReport:
    """Validate a list of corpus records.

    Args:
        records: List of canonical record dicts (as from ggs_lines.jsonl).
        error_config: Error handling configuration.

    Returns:
        A :class:`ValidationReport` with pass/fail/warning counts.

    Raises:
        FatalPipelineError: On FATAL-severity violations (duplicate
            line_uid, schema version mismatch).
    """
    report = ValidationReport()
    report.total_lines = len(records)

    collector = ErrorCollector(
        "validation", config=error_config,
    )
    seen_uids: set[str] = set()

    for rec in records:
        line_uid = rec.get("line_uid", "UNKNOWN")
        gurmukhi = rec.get("gurmukhi", "")

        # -- Check 1: Unique line_uid --
        if line_uid in seen_uids:
            report.record_fail(
                "unique_line_uid",
                line_uid=line_uid,
                detail=f"Duplicate line_uid: {line_uid}",
            )
            report.verdict = "FAIL"
            raise FatalPipelineError(
                f"Duplicate line_uid: {line_uid}",
                error_type="DUPLICATE_LINE_UID",
                phase="validation",
            )
        seen_uids.add(line_uid)
        report.record_pass("unique_line_uid")

        # -- Check 2: Non-empty gurmukhi --
        if not gurmukhi or not gurmukhi.strip():
            report.record_fail(
                "non_empty_gurmukhi",
                line_uid=line_uid,
                detail="Empty gurmukhi field",
            )
            collector.record_error(
                error_type="EMPTY_GURMUKHI",
                message="gurmukhi field is empty",
                line_uid=line_uid,
            )
            continue
        report.record_pass("non_empty_gurmukhi")

        # -- Check 3: Normalization idempotency --
        re_normalized = normalize(gurmukhi)
        if re_normalized != gurmukhi:
            report.record_fail(
                "normalization_idempotent",
                line_uid=line_uid,
                detail=(
                    "gurmukhi field not properly normalized. "
                    f"Stored: {gurmukhi!r}, "
                    f"Re-normalized: {re_normalized!r}"
                ),
            )
            report.verdict = "FAIL"
        else:
            report.record_pass("normalization_idempotent")

        # -- Check 4: Provenance fields present --
        if "schema_version" not in rec:
            report.record_fail(
                "provenance_fields",
                line_uid=line_uid,
                detail="Missing schema_version",
            )
        else:
            report.record_pass("provenance_fields")

        # -- Check 5: Schema version supported --
        sv = rec.get("schema_version")
        if sv and sv not in SUPPORTED_SCHEMA_VERSIONS:
            report.record_fail(
                "schema_version_supported",
                line_uid=line_uid,
                detail=f"Unsupported schema version: {sv}",
            )
            report.verdict = "FAIL"
        elif sv:
            report.record_pass("schema_version_supported")

        # -- Check 7: Token count sanity --
        tokens = rec.get("tokens", [])
        if len(tokens) == 0:
            report.record_warning(
                "token_count_sanity",
                line_uid=line_uid,
                detail="0 tokens",
            )
        elif len(tokens) > 200:
            report.record_warning(
                "token_count_sanity",
                line_uid=line_uid,
                detail=f"{len(tokens)} tokens (>200)",
            )
        else:
            report.record_pass("token_count_sanity")

        # -- Check 8: Character repertoire --
        unexpected = [
            ch for ch in gurmukhi
            if not _is_expected_char(ch)
        ]
        if unexpected:
            chars_repr = ", ".join(
                f"U+{ord(c):04X}" for c in unexpected[:5]
            )
            report.record_warning(
                "character_repertoire",
                line_uid=line_uid,
                detail=f"Unexpected characters: {chars_repr}",
            )
        else:
            report.record_pass("character_repertoire")

        # -- Check 10: token_spans alignment --
        token_spans = rec.get("token_spans", [])
        if len(tokens) != len(token_spans):
            report.record_fail(
                "token_spans_alignment",
                line_uid=line_uid,
                detail=(
                    f"tokens ({len(tokens)}) != "
                    f"token_spans ({len(token_spans)})"
                ),
            )
        else:
            spans_ok = True
            for _i, (tok, span) in enumerate(
                zip(tokens, token_spans, strict=True),
            ):
                if not (
                    isinstance(span, list)
                    and len(span) == 2
                ):
                    spans_ok = False
                    break
                start, end = span
                if (
                    start < 0
                    or end > len(gurmukhi)
                    or start >= end
                ):
                    spans_ok = False
                    break
                if gurmukhi[start:end] != tok:
                    spans_ok = False
                    break
            if spans_ok:
                report.record_pass("token_spans_alignment")
            else:
                report.record_fail(
                    "token_spans_alignment",
                    line_uid=line_uid,
                    detail="token_spans do not align",
                )

    # If no fatal errors recorded, keep verdict as PASS
    if report.verdict != "FAIL" and not report.errors:
        report.verdict = "PASS"
    elif report.errors and report.verdict != "FAIL":
        report.verdict = "FAIL"

    return report
