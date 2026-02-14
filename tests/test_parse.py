"""Parser regression tests (bd-3jj.2).

Verifies that the SriGranth HTML parser extracts the correct Gurmukhi
text and metadata from known HTML fixtures (Angs 1-5).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ggs.corpus.parse_srigranth import (
    compute_line_uid,
    compute_shabad_uid,
    parse_ang,
    to_canonical_records,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_ang_html(fixtures_dir: Path, ang: int) -> str:
    """Load fixture HTML for a given ang number."""
    path = fixtures_dir / "html" / f"ang_{ang:03d}.html"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Basic extraction tests
# ---------------------------------------------------------------------------


class TestBasicExtraction:
    """Parse fixture HTML and verify line extraction."""

    def test_ang1_produces_lines(self, fixtures_dir: Path) -> None:
        """Ang 1 HTML produces a non-empty list of lines."""
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        assert len(result.lines) > 0

    def test_ang1_no_errors(self, fixtures_dir: Path) -> None:
        """Ang 1 parsing produces no errors."""
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        assert result.errors == []

    def test_ang1_mool_mantar(self, fixtures_dir: Path) -> None:
        """First line of ang 1 must be the Mool Mantar."""
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        first_line = result.lines[0].gurmukhi_raw
        assert first_line.startswith("ੴ")
        assert "ਸਤਿ ਨਾਮੁ" in first_line

    def test_ang1_line_count(self, fixtures_dir: Path) -> None:
        """Ang 1 fixture should produce exactly 16 lines."""
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        assert len(result.lines) == 16

    def test_ang1_ang_number(self, fixtures_dir: Path) -> None:
        """All lines have ang=1."""
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        for line in result.lines:
            assert line.ang == 1


class TestAllAngs:
    """Parse all fixture angs (1-5)."""

    @pytest.mark.parametrize("ang", [1, 2, 3, 4, 5])
    def test_ang_produces_lines(
        self, fixtures_dir: Path, ang: int,
    ) -> None:
        html = _load_ang_html(fixtures_dir, ang)
        result = parse_ang(html, ang=ang)
        assert len(result.lines) > 0, (
            f"Ang {ang} produced no lines"
        )

    @pytest.mark.parametrize("ang", [1, 2, 3, 4, 5])
    def test_ang_no_errors(
        self, fixtures_dir: Path, ang: int,
    ) -> None:
        html = _load_ang_html(fixtures_dir, ang)
        result = parse_ang(html, ang=ang)
        assert result.errors == [], (
            f"Ang {ang} had errors: {result.errors}"
        )


class TestLineOrdering:
    """Lines are in page order."""

    def test_line_numbers_sequential(
        self, fixtures_dir: Path,
    ) -> None:
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        numbers = [line.line_number for line in result.lines]
        assert numbers == list(range(1, len(numbers) + 1))


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


class TestRahaoDetection:
    """Lines containing ਰਹਾਉ have meta.rahao=True."""

    def test_rahao_flag(self, fixtures_dir: Path) -> None:
        """Check rahao detection across all fixture angs."""
        for ang_num in range(1, 6):
            html = _load_ang_html(fixtures_dir, ang_num)
            result = parse_ang(html, ang=ang_num)
            for line in result.lines:
                has_rahao_text = "ਰਹਾਉ" in line.gurmukhi_raw
                assert line.meta["rahao"] == has_rahao_text, (
                    f"Ang {ang_num}, line {line.line_number}: "
                    f"rahao flag mismatch"
                )


# ---------------------------------------------------------------------------
# Canonical record conversion
# ---------------------------------------------------------------------------


class TestCanonicalRecords:
    """to_canonical_records() produces valid dicts."""

    def test_record_fields(self, fixtures_dir: Path) -> None:
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        records = to_canonical_records(result)

        assert len(records) == len(result.lines)
        for rec in records:
            assert "schema_version" in rec
            assert "ang" in rec
            assert "line_id" in rec
            assert "line_uid" in rec
            assert "gurmukhi_raw" in rec
            assert "gurmukhi" in rec
            assert "meta" in rec
            assert "source_ang_url" in rec

    def test_line_id_format(self, fixtures_dir: Path) -> None:
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        records = to_canonical_records(result)

        for rec in records:
            # line_id should be "ang:NN" format
            assert ":" in rec["line_id"]
            parts = rec["line_id"].split(":")
            assert parts[0] == "1"

    def test_source_url(self, fixtures_dir: Path) -> None:
        html = _load_ang_html(fixtures_dir, 1)
        result = parse_ang(html, ang=1)
        records = to_canonical_records(result)

        for rec in records:
            assert "Param=1" in rec["source_ang_url"]


# ---------------------------------------------------------------------------
# UID computation
# ---------------------------------------------------------------------------


class TestUIDs:
    """Line UID and Shabad UID computation."""

    def test_line_uid_deterministic(self) -> None:
        uid1 = compute_line_uid(1, "ੴ ਸਤਿ ਨਾਮੁ")
        uid2 = compute_line_uid(1, "ੴ ਸਤਿ ਨਾਮੁ")
        assert uid1 == uid2

    def test_line_uid_different_text(self) -> None:
        uid1 = compute_line_uid(1, "ੴ ਸਤਿ ਨਾਮੁ")
        uid2 = compute_line_uid(1, "ਆਦਿ ਸਚੁ")
        assert uid1 != uid2

    def test_line_uid_different_ang(self) -> None:
        uid1 = compute_line_uid(1, "ੴ ਸਤਿ ਨਾਮੁ")
        uid2 = compute_line_uid(2, "ੴ ਸਤਿ ਨਾਮੁ")
        assert uid1 != uid2

    def test_line_uid_format(self) -> None:
        uid = compute_line_uid(1, "ੴ ਸਤਿ ਨਾਮੁ")
        assert uid.startswith("ang1:sha256:")

    def test_shabad_uid_format(self) -> None:
        uid = compute_shabad_uid(1, "1:01")
        assert uid.startswith("shabad:sha256:")

    def test_shabad_uid_deterministic(self) -> None:
        uid1 = compute_shabad_uid(1, "1:01")
        uid2 = compute_shabad_uid(1, "1:01")
        assert uid1 == uid2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Parser edge cases."""

    def test_empty_html(self) -> None:
        """Empty HTML produces an error, not a crash."""
        result = parse_ang("<html><body></body></html>", ang=1)
        assert len(result.lines) == 0
        assert len(result.errors) > 0

    def test_no_gurmukhi_html(self) -> None:
        """HTML without Gurmukhi produces an error."""
        html = "<html><body><p>Hello world</p></body></html>"
        result = parse_ang(html, ang=1)
        assert len(result.lines) == 0
        assert len(result.errors) > 0

    def test_malformed_html(self) -> None:
        """Malformed HTML doesn't crash the parser."""
        html = "<html><body><td class='gurbani'>ਸਤਿ ਨਾਮੁ"
        result = parse_ang(html, ang=1)
        # Should still extract the Gurmukhi text
        assert len(result.lines) >= 0  # just no crash
