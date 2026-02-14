"""Normalization pipeline tests (bd-3jj.3).

Tests the 7-step Gurmukhi normalization pipeline for correctness,
consistency, and idempotency.
"""

from __future__ import annotations

import pytest

from ggs.corpus.normalize import (
    BINDI,
    TIPPI,
    NasalPolicy,
    NormalizationConfig,
    NuktaPolicy,
    VishramPolicy,
    normalize,
    normalize_dual,
    step_nasal_canonical_tippi,
    step_normalize_whitespace,
    step_nukta_strip,
    step_strip_zero_width,
    step_unicode_nfc,
    step_vishram_strip,
)

# ---------------------------------------------------------------------------
# Fixture-driven tests
# ---------------------------------------------------------------------------


class TestNormalizationFixtures:
    """Run all cases from normalization_cases.yaml fixture."""

    def test_fixture_cases(
        self, normalization_cases: list[dict],
    ) -> None:
        """Each fixture case normalizes to its expected output."""
        for case in normalization_cases:
            config = NormalizationConfig(
                nukta_policy=case.get(
                    "nukta_policy", "PRESERVE",
                ),
                nasal_policy=case.get(
                    "nasal_policy", "CANONICAL_TIPPI",
                ),
                vishram_policy=case.get(
                    "vishram_policy", "STRIP",
                ),
                halant_policy=case.get(
                    "halant_policy", "DECOMPOSE",
                ),
            )
            result = normalize(case["input"], config)
            assert result == case["expected"], (
                f"Case '{case['name']}' failed: "
                f"expected {case['expected']!r}, got {result!r}"
            )


# ---------------------------------------------------------------------------
# Step-level unit tests
# ---------------------------------------------------------------------------


class TestUnicodeNFC:
    """Step 1 — Unicode NFC normalization."""

    def test_nfc_identity(self) -> None:
        """Already-NFC text is unchanged."""
        text = "ਸਤਿ ਨਾਮੁ"
        assert step_unicode_nfc(text) == text

    def test_nfc_empty(self) -> None:
        assert step_unicode_nfc("") == ""


class TestZeroWidthStripping:
    """Step 2 — ZWJ/ZWNJ removal."""

    def test_zwj_removed(self) -> None:
        text = "ਸ\u200Dਤਿ"
        assert step_strip_zero_width(text) == "ਸਤਿ"

    def test_zwnj_removed(self) -> None:
        text = "ਨਾ\u200Cਮੁ"
        assert step_strip_zero_width(text) == "ਨਾਮੁ"

    def test_mixed_zero_width(self) -> None:
        text = "ਸ\u200Dਤਿ\u200C ਨਾ\u200Dਮੁ"
        assert step_strip_zero_width(text) == "ਸਤਿ ਨਾਮੁ"

    def test_no_zero_width(self) -> None:
        text = "ਸਤਿ ਨਾਮੁ"
        assert step_strip_zero_width(text) == text


class TestNuktaPolicy:
    """Step 3 — Nukta handling."""

    def test_strip_khakha(self) -> None:
        """ਖ਼ (U+0A59) collapses to ਖ (U+0A16)."""
        assert step_nukta_strip("\u0A59") == "\u0A16"

    def test_strip_gagha(self) -> None:
        """ਗ਼ (U+0A5A) collapses to ਗ (U+0A17)."""
        assert step_nukta_strip("\u0A5A") == "\u0A17"

    def test_strip_fafa(self) -> None:
        """ਫ਼ (U+0A5E) collapses to ਫ (U+0A2B)."""
        assert step_nukta_strip("\u0A5E") == "\u0A2B"

    def test_preserve_keeps_distinct(self) -> None:
        """PRESERVE policy: ਖ਼ and ਖ remain different."""
        config = NormalizationConfig(nukta_policy=NuktaPolicy.PRESERVE)
        assert normalize("\u0A59", config) != normalize("\u0A16", config)


class TestNasalNormalization:
    """Step 4 — Nasal marker handling."""

    def test_bindi_to_tippi(self) -> None:
        """Default: Bindi (ਂ) normalizes to Tippi (ੰ)."""
        text = f"ਸ{BINDI}ਤ"
        assert step_nasal_canonical_tippi(text) == f"ਸ{TIPPI}ਤ"

    def test_tippi_unchanged(self) -> None:
        """Tippi stays as Tippi under CANONICAL_TIPPI."""
        text = f"ਸ{TIPPI}ਤ"
        assert step_nasal_canonical_tippi(text) == text

    def test_same_word_both_forms(self) -> None:
        """ਸੰਤ (tippi) and ਸਂਤ (bindi) produce same result."""
        config = NormalizationConfig(
            nasal_policy=NasalPolicy.CANONICAL_TIPPI,
        )
        with_tippi = normalize(f"ਸ{TIPPI}ਤ", config)
        with_bindi = normalize(f"ਸ{BINDI}ਤ", config)
        assert with_tippi == with_bindi


class TestVishramStripping:
    """Step 5 — Vishram marker removal."""

    def test_double_danda_stripped(self) -> None:
        result = step_vishram_strip("ਸਤਿ ਨਾਮੁ ॥")
        assert "॥" not in result

    def test_no_vishram_unchanged(self) -> None:
        text = "ਸਤਿ ਨਾਮੁ"
        assert step_vishram_strip(text) == text


class TestWhitespaceNormalization:
    """Step 7 — Whitespace collapse and trim."""

    def test_collapse_spaces(self) -> None:
        assert step_normalize_whitespace("ਸਤਿ   ਨਾਮੁ") == "ਸਤਿ ਨਾਮੁ"

    def test_trim(self) -> None:
        assert step_normalize_whitespace("  ਸਤਿ  ") == "ਸਤਿ"

    def test_tabs_and_newlines(self) -> None:
        assert step_normalize_whitespace("ਸਤਿ\t\nਨਾਮੁ") == "ਸਤਿ ਨਾਮੁ"

    def test_empty(self) -> None:
        assert step_normalize_whitespace("") == ""

    def test_whitespace_only(self) -> None:
        assert step_normalize_whitespace("   ") == ""


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end normalization pipeline."""

    def test_mool_mantar(self) -> None:
        raw = "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ ॥"
        result = normalize(raw)
        # Double danda should be stripped (vishram policy STRIP)
        assert "॥" not in result
        # Ik Onkar should be preserved
        assert result.startswith("ੴ")
        # Tippi should be preserved (CANONICAL_TIPPI keeps it)
        assert "ਸੈਭੰ" in result

    def test_empty_string(self) -> None:
        assert normalize("") == ""

    def test_whitespace_only(self) -> None:
        assert normalize("   \t\n  ") == ""

    def test_defaults_match_plan(self) -> None:
        """Default config matches PLAN.md Section 3.4 defaults."""
        config = NormalizationConfig()
        assert config.nukta_policy == NuktaPolicy.PRESERVE
        assert config.nasal_policy == NasalPolicy.CANONICAL_TIPPI
        assert config.vishram_policy == VishramPolicy.STRIP


# ---------------------------------------------------------------------------
# Idempotency — THE critical property
# ---------------------------------------------------------------------------


class TestIdempotency:
    """normalize(normalize(x)) == normalize(x) for all inputs."""

    @pytest.mark.parametrize(
        "text",
        [
            "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            "ਆਦਿ ਸਚੁ ਜੁਗਾਦਿ ਸਚੁ ॥",
            "ਹੁਕਮੀ ਹੋਵਨਿ ਆਕਾਰ ਹੁਕਮੁ ਨ ਕਹਿਆ ਜਾਈ ॥",
            f"ਸ{BINDI}ਤ ਨਾਮੁ",
            "ਸ\u200Dਤਿ\u200C ਨਾਮੁ",
            "  ਸਤਿ   ਨਾਮੁ  ",
            "",
            "   ",
        ],
    )
    def test_idempotent(self, text: str) -> None:
        once = normalize(text)
        twice = normalize(once)
        assert once == twice, (
            f"Not idempotent: normalize(x)={once!r}, "
            f"normalize(normalize(x))={twice!r}"
        )

    def test_idempotent_all_fixture_cases(
        self,
        normalization_cases: list[dict],
    ) -> None:
        """Idempotency holds for every fixture case."""
        for case in normalization_cases:
            config = NormalizationConfig(
                nukta_policy=case.get(
                    "nukta_policy", "PRESERVE",
                ),
                nasal_policy=case.get(
                    "nasal_policy", "CANONICAL_TIPPI",
                ),
                vishram_policy=case.get(
                    "vishram_policy", "STRIP",
                ),
                halant_policy=case.get(
                    "halant_policy", "DECOMPOSE",
                ),
            )
            once = normalize(case["input"], config)
            twice = normalize(once, config)
            assert once == twice, (
                f"Case '{case['name']}' not idempotent"
            )


# ---------------------------------------------------------------------------
# Dual mode
# ---------------------------------------------------------------------------


class TestDualMode:
    """DUAL nukta policy returns both preserved and stripped forms."""

    def test_dual_returns_tuple(self) -> None:
        result = normalize_dual("ਖ਼ਾਲਸਾ")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_dual_preserved_has_nukta(self) -> None:
        preserved, _ = normalize_dual("ਖ਼ਾਲਸਾ")
        assert "\u0A59" in preserved or "\u0A3C" in preserved

    def test_dual_stripped_no_nukta(self) -> None:
        _, stripped = normalize_dual("ਖ਼ਾਲਸਾ")
        assert "\u0A59" not in stripped
        assert "\u0A3C" not in stripped


# ---------------------------------------------------------------------------
# Config from dict
# ---------------------------------------------------------------------------


class TestConfigFromDict:
    """NormalizationConfig.from_dict()."""

    def test_defaults(self) -> None:
        config = NormalizationConfig.from_dict({})
        assert config.nukta_policy == NuktaPolicy.PRESERVE
        assert config.nasal_policy == NasalPolicy.CANONICAL_TIPPI

    def test_override(self) -> None:
        config = NormalizationConfig.from_dict(
            {"nukta_policy": "STRIP"},
        )
        assert config.nukta_policy == NuktaPolicy.STRIP
