"""Phase 0 end-to-end integration and smoke tests (bd-15c.8).

Verifies the full pipeline: parse -> normalize -> tokenize -> validate
using pre-saved HTML fixtures (Angs 1-5).  No network access required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ggs.corpus.normalize import normalize
from ggs.corpus.pipeline import (
    _discover_html_files,
    _process_ang_html,
    run_phase0,
)
from ggs.corpus.validate import validate_corpus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_ang_html(fixtures_dir: Path, ang: int) -> str:
    """Load fixture HTML for a given ang number."""
    path = fixtures_dir / "html" / f"ang_{ang:03d}.html"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Pipeline wiring tests
# ---------------------------------------------------------------------------


class TestPipelineWiring:
    """Verify that parse -> normalize -> tokenize chain works."""

    def test_ang1_full_pipeline(
        self, fixtures_dir: Path,
    ) -> None:
        """Ang 1 HTML produces canonical records with all fields."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        assert len(records) > 0
        for rec in records:
            # Schema fields
            assert "schema_version" in rec
            assert "ang" in rec
            assert "line_id" in rec
            assert "line_uid" in rec
            assert "gurmukhi_raw" in rec
            assert "gurmukhi" in rec
            assert "tokens" in rec
            assert "token_spans" in rec
            assert "meta" in rec
            assert "source_ang_url" in rec

    def test_gurmukhi_is_normalized(
        self, fixtures_dir: Path,
    ) -> None:
        """gurmukhi field is the normalized form of gurmukhi_raw."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        for rec in records:
            expected = normalize(rec["gurmukhi_raw"])
            assert rec["gurmukhi"] == expected, (
                f"gurmukhi field not normalized for "
                f"line {rec['line_id']}"
            )

    def test_tokens_are_populated(
        self, fixtures_dir: Path,
    ) -> None:
        """Each record has tokens and token_spans populated."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        for rec in records:
            # Parallel arrays
            assert len(rec["tokens"]) == len(
                rec["token_spans"]
            )
            # At least some lines should have tokens
        has_tokens = any(
            len(r["tokens"]) > 0 for r in records
        )
        assert has_tokens

    def test_token_spans_align(
        self, fixtures_dir: Path,
    ) -> None:
        """Token spans correctly index into the gurmukhi field."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        for rec in records:
            gurmukhi = rec["gurmukhi"]
            for tok, span in zip(
                rec["tokens"],
                rec["token_spans"],
                strict=True,
            ):
                extracted = gurmukhi[span[0]:span[1]]
                assert extracted == tok, (
                    f"Span {span} extracts {extracted!r}, "
                    f"expected {tok!r} in line {rec['line_id']}"
                )

    def test_structural_markers_in_meta(
        self, fixtures_dir: Path,
    ) -> None:
        """Structural markers are stored in meta."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        for rec in records:
            assert "structural_markers" in rec["meta"]


class TestAllFixtureAngs:
    """Process all fixture angs (1-5) through the pipeline."""

    @pytest.mark.parametrize("ang", [1, 2, 3, 4, 5])
    def test_ang_produces_records(
        self, fixtures_dir: Path, ang: int,
    ) -> None:
        html = _load_ang_html(fixtures_dir, ang)
        records = _process_ang_html(html, ang=ang)
        assert len(records) > 0, (
            f"Ang {ang} produced no records"
        )

    @pytest.mark.parametrize("ang", [1, 2, 3, 4, 5])
    def test_ang_records_validate(
        self, fixtures_dir: Path, ang: int,
    ) -> None:
        """Each ang's records pass corpus validation."""
        html = _load_ang_html(fixtures_dir, ang)
        records = _process_ang_html(html, ang=ang)
        report = validate_corpus(records)
        assert report.verdict == "PASS", (
            f"Ang {ang} validation failed: "
            f"{report.errors[:3]}"
        )


# ---------------------------------------------------------------------------
# Normalization idempotency in pipeline context
# ---------------------------------------------------------------------------


class TestNormalizationInPipeline:
    """Normalization is correctly applied and idempotent."""

    def test_idempotent_gurmukhi(
        self, fixtures_dir: Path,
    ) -> None:
        """Re-normalizing gurmukhi produces the same result."""
        html = _load_ang_html(fixtures_dir, 1)
        records = _process_ang_html(html, ang=1)

        for rec in records:
            re_normalized = normalize(rec["gurmukhi"])
            assert rec["gurmukhi"] == re_normalized


# ---------------------------------------------------------------------------
# Validation integration
# ---------------------------------------------------------------------------


class TestValidationIntegration:
    """Validator correctly processes pipeline output."""

    def test_all_angs_pass_validation(
        self, fixtures_dir: Path,
    ) -> None:
        """Combined records from all fixture angs pass validation."""
        all_records: list[dict[str, Any]] = []
        for ang in range(1, 6):
            html = _load_ang_html(fixtures_dir, ang)
            records = _process_ang_html(html, ang=ang)
            all_records.extend(records)

        report = validate_corpus(all_records)
        assert report.verdict == "PASS", (
            f"Combined validation failed with "
            f"{len(report.errors)} errors: "
            f"{report.errors[:5]}"
        )
        assert report.total_lines == len(all_records)

    def test_unique_line_uids(
        self, fixtures_dir: Path,
    ) -> None:
        """All line_uids are unique across fixture angs."""
        all_records: list[dict[str, Any]] = []
        for ang in range(1, 6):
            html = _load_ang_html(fixtures_dir, ang)
            records = _process_ang_html(html, ang=ang)
            all_records.extend(records)

        uids = [r["line_uid"] for r in all_records]
        assert len(uids) == len(set(uids)), (
            "Duplicate line_uids found"
        )


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


class TestFileDiscovery:
    """HTML file discovery logic."""

    def test_discover_fixture_files(
        self, fixtures_dir: Path,
    ) -> None:
        html_dir = fixtures_dir / "html"
        files = _discover_html_files(html_dir)
        assert len(files) == 5
        assert 1 in files
        assert 5 in files

    def test_discover_with_range(
        self, fixtures_dir: Path,
    ) -> None:
        html_dir = fixtures_dir / "html"
        files = _discover_html_files(
            html_dir, ang_range=(2, 4),
        )
        assert len(files) == 3
        assert 1 not in files
        assert 5 not in files


# ---------------------------------------------------------------------------
# Full run_phase0 integration
# ---------------------------------------------------------------------------


class TestRunPhase0:
    """Full pipeline run using run_phase0()."""

    def test_produces_output_files(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """run_phase0 creates ggs_lines.jsonl, manifest, and report."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"

        result = run_phase0(
            input_dir=html_dir,
            output_dir=output_dir,
        )

        # Check output files exist
        assert (output_dir / "ggs_lines.jsonl").exists()
        assert (output_dir / "run_manifest.json").exists()
        assert (
            output_dir / "validation_report.json"
        ).exists()

        # Check result summary
        assert result["total_lines"] > 0
        assert result["total_angs"] == 5
        assert result["validation_verdict"] == "PASS"

    def test_jsonl_is_valid(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """ggs_lines.jsonl contains valid JSONL records."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(
            input_dir=html_dir,
            output_dir=output_dir,
        )

        jsonl_path = output_dir / "ggs_lines.jsonl"
        lines = jsonl_path.read_text(
            encoding="utf-8",
        ).strip().split("\n")
        assert len(lines) > 0

        for line_text in lines:
            rec = json.loads(line_text)
            assert "schema_version" in rec
            assert "ang" in rec
            assert "gurmukhi" in rec
            assert "tokens" in rec
            assert "token_spans" in rec

    def test_manifest_has_provenance(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """run_manifest.json contains provenance information."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(
            input_dir=html_dir,
            output_dir=output_dir,
        )

        manifest_path = output_dir / "run_manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
        )

        assert manifest["phase"] == "corpus"
        assert "generated_at" in manifest
        assert "record_counts" in manifest
        assert manifest["record_counts"]["total_angs"] == 5
        assert manifest["record_counts"]["total_lines"] > 0
        assert "pipeline_versions" in manifest

    def test_validation_report_structure(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """validation_report.json has expected structure."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(
            input_dir=html_dir,
            output_dir=output_dir,
        )

        report_path = output_dir / "validation_report.json"
        report = json.loads(
            report_path.read_text(encoding="utf-8"),
        )

        assert "verdict" in report
        assert "total_lines" in report
        assert "checks_passed" in report
        assert report["verdict"] == "PASS"

    def test_ang1_mool_mantar_in_output(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """The Mool Mantar appears in the first line of output."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(
            input_dir=html_dir,
            output_dir=output_dir,
        )

        jsonl_path = output_dir / "ggs_lines.jsonl"
        first_line = jsonl_path.read_text(
            encoding="utf-8",
        ).split("\n")[0]
        rec = json.loads(first_line)

        assert rec["ang"] == 1
        assert "ੴ" in rec["gurmukhi"]
        assert "ਸਤਿ" in rec["gurmukhi"]

    def test_empty_input_dir(self, tmp_path: Path) -> None:
        """Empty input directory produces zero-line result."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output_dir = tmp_path / "output"

        result = run_phase0(
            input_dir=empty_dir,
            output_dir=output_dir,
        )

        assert result["total_lines"] == 0
        assert result["total_angs"] == 0
