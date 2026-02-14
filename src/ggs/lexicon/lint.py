"""Lexicon linter -- comprehensive QA for lexicon YAML files (bd-4i2.2).

Unlike the loader (which fails fast at runtime), the linter reports ALL
issues for developer review using rich-formatted console output.

Checks:
  1. Schema conformance (required fields, types)
  2. Duplicate aliases across entities
  3. Missing required fields
  4. Normalization collisions
  5. YAML validity
  6. Cross-file ID uniqueness
  7. Alias coverage (valid Gurmukhi)
  8. Controlled vocabulary validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from ggs.corpus.normalize import normalize
from ggs.lexicon.loader import (
    _ID_PATTERN,
    VALID_ALIAS_TYPES,
    VALID_CATEGORIES,
    VALID_REGISTERS,
    VALID_TRADITIONS,
)

_console = Console()


# ---------------------------------------------------------------------------
# Lint result
# ---------------------------------------------------------------------------


@dataclass
class LintIssue:
    """A single lint finding."""

    severity: str  # ERROR | WARNING
    check: str
    file: str
    entity_id: str | None
    message: str


@dataclass
class LintReport:
    """Aggregated lint results."""

    issues: list[LintIssue] = field(default_factory=list)
    files_checked: int = 0
    entities_checked: int = 0

    @property
    def error_count(self) -> int:
        return sum(
            1 for i in self.issues if i.severity == "ERROR"
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for i in self.issues if i.severity == "WARNING"
        )

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def add(
        self,
        severity: str,
        check: str,
        file: str,
        entity_id: str | None,
        message: str,
    ) -> None:
        self.issues.append(
            LintIssue(
                severity=severity,
                check=check,
                file=file,
                entity_id=entity_id,
                message=message,
            ),
        )

    def display(self) -> None:
        """Print rich-formatted report to console."""
        if not self.issues:
            _console.print(
                f"\n[bold green]PASS[/bold green] "
                f"All {self.entities_checked} entities in "
                f"{self.files_checked} files are valid.\n"
            )
            return

        table = Table(
            title="Lexicon Lint Report",
            show_lines=True,
        )
        table.add_column("Severity", style="bold")
        table.add_column("Check")
        table.add_column("File")
        table.add_column("Entity")
        table.add_column("Message")

        for issue in self.issues:
            style = (
                "red" if issue.severity == "ERROR" else "yellow"
            )
            table.add_row(
                f"[{style}]{issue.severity}[/{style}]",
                issue.check,
                issue.file,
                issue.entity_id or "-",
                issue.message,
            )

        _console.print(table)

        verdict_style = (
            "red" if self.error_count > 0 else "yellow"
        )
        verdict_text = (
            "FAIL" if self.error_count > 0 else "WARN"
        )
        _console.print(
            f"\n[bold {verdict_style}]{verdict_text}[/bold {verdict_style}] "
            f"{self.error_count} errors, "
            f"{self.warning_count} warnings "
            f"across {self.entities_checked} entities "
            f"in {self.files_checked} files.\n"
        )


# ---------------------------------------------------------------------------
# Gurmukhi detection
# ---------------------------------------------------------------------------


def _contains_gurmukhi(text: str) -> bool:
    """Check if string contains Gurmukhi characters."""
    return any("\u0A00" <= ch <= "\u0A7F" for ch in text)


# ---------------------------------------------------------------------------
# Linter core
# ---------------------------------------------------------------------------


def lint_file(
    path: Path,
    report: LintReport,
    *,
    seen_ids: dict[str, str],
    alias_index: dict[str, list[tuple[str, str]]],
    normalized_index: dict[str, list[tuple[str, str]]],
) -> None:
    """Lint a single lexicon YAML file.

    Args:
        path: Path to the YAML file.
        report: Report to accumulate findings into.
        seen_ids: Dict tracking entity_id -> source file
            for cross-file uniqueness checks.
        alias_index: Dict tracking alias form ->
            [(entity_id, file)] for duplicate detection.
        normalized_index: Dict tracking normalized form ->
            [(entity_id, file)] for collision detection.
    """
    fname = path.name

    # Check 5: YAML validity
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        report.add(
            "ERROR", "yaml_valid", fname, None,
            f"YAML parse error: {exc}",
        )
        return

    if data is None or "entities" not in data:
        report.add(
            "ERROR", "schema_conformance", fname, None,
            "Missing 'entities' key",
        )
        return

    for raw in data["entities"]:
        report.entities_checked += 1
        eid = raw.get("id", "<MISSING>")

        # Check 3: Required fields
        for req_field in (
            "id", "canonical_form", "aliases", "category",
        ):
            if req_field not in raw:
                report.add(
                    "ERROR", "required_fields", fname, eid,
                    f"Missing required field: {req_field}",
                )

        if "id" not in raw:
            continue

        # ID pattern
        if not _ID_PATTERN.match(eid):
            report.add(
                "ERROR", "id_pattern", fname, eid,
                f"ID must be UPPER_SNAKE_CASE, got: {eid}",
            )

        # Check 6: Cross-file ID uniqueness
        if eid in seen_ids:
            report.add(
                "ERROR", "unique_ids", fname, eid,
                f"Duplicate ID, also in: {seen_ids[eid]}",
            )
        seen_ids[eid] = fname

        # Check 8: Controlled vocabulary
        category = raw.get("category")
        if (
            category is not None
            and category not in VALID_CATEGORIES
        ):
            report.add(
                "ERROR", "controlled_vocab", fname, eid,
                f"Invalid category: {category}",
            )

        tradition = raw.get("tradition")
        if (
            tradition is not None
            and tradition not in VALID_TRADITIONS
        ):
            report.add(
                "ERROR", "controlled_vocab", fname, eid,
                f"Invalid tradition: {tradition}",
            )

        register = raw.get("register")
        if (
            register is not None
            and register not in VALID_REGISTERS
        ):
            report.add(
                "ERROR", "controlled_vocab", fname, eid,
                f"Invalid register: {register}",
            )

        # Check aliases
        aliases = raw.get("aliases", [])
        if not aliases:
            report.add(
                "ERROR", "schema_conformance", fname, eid,
                "Entity has no aliases",
            )
            continue

        for alias_dict in aliases:
            form = alias_dict.get("form")
            atype = alias_dict.get("type")

            if form is None or atype is None:
                report.add(
                    "ERROR", "schema_conformance", fname, eid,
                    f"Alias missing form or type: {alias_dict}",
                )
                continue

            if atype not in VALID_ALIAS_TYPES:
                report.add(
                    "ERROR", "controlled_vocab", fname, eid,
                    f"Invalid alias type: {atype}",
                )

            # Check 7: Alias coverage (valid Gurmukhi)
            if not _contains_gurmukhi(form):
                report.add(
                    "WARNING", "alias_coverage", fname, eid,
                    f"Alias '{form}' has no Gurmukhi chars",
                )

            # Check 2: Duplicate aliases
            if form in alias_index:
                for other_eid, other_file in alias_index[form]:
                    if other_eid != eid:
                        report.add(
                            "WARNING",
                            "duplicate_alias",
                            fname,
                            eid,
                            f"Alias '{form}' shared with "
                            f"{other_eid} ({other_file})",
                        )
            alias_index.setdefault(form, []).append(
                (eid, fname),
            )

            # Check 4: Normalization collisions
            norm_form = normalize(form)
            if norm_form in normalized_index:
                for other_eid, other_file in normalized_index[norm_form]:
                    if other_eid != eid:
                        report.add(
                            "WARNING",
                            "normalization_collision",
                            fname,
                            eid,
                            f"Alias '{form}' normalizes to "
                            f"same form as alias in "
                            f"{other_eid} ({other_file})",
                        )
            normalized_index.setdefault(norm_form, []).append(
                (eid, fname),
            )


def lint_lexicon(
    lexicon_paths: dict[str, str | Path],
    *,
    base_dir: Path | None = None,
) -> LintReport:
    """Lint all lexicon files.

    Args:
        lexicon_paths: Mapping from label to file path.
        base_dir: Base directory for relative path resolution.

    Returns:
        A :class:`LintReport` with all findings.
    """
    report = LintReport()
    seen_ids: dict[str, str] = {}
    alias_index: dict[str, list[tuple[str, str]]] = {}
    normalized_index: dict[str, list[tuple[str, str]]] = {}

    for _label, rel_path in lexicon_paths.items():
        path = Path(rel_path)
        if base_dir is not None:
            path = base_dir / path

        if not path.exists():
            continue

        report.files_checked += 1
        lint_file(
            path,
            report,
            seen_ids=seen_ids,
            alias_index=alias_index,
            normalized_index=normalized_index,
        )

    return report
