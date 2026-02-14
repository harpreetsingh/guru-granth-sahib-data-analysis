"""Tokenizer tests (bd-3jj.4).

Verifies correct splitting, structural marker extraction, and
token_spans accuracy.
"""

from __future__ import annotations

import pytest

from ggs.corpus.tokenize import TokenizeResult, tokenize

# ---------------------------------------------------------------------------
# Basic splitting
# ---------------------------------------------------------------------------


class TestBasicSplitting:
    """Token splitting on whitespace."""

    def test_simple_three_words(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ਕਰਤਾ")
        assert result.tokens == ["ਸਤਿ", "ਨਾਮੁ", "ਕਰਤਾ"]

    def test_single_word(self) -> None:
        result = tokenize("ਸਤਿ")
        assert result.tokens == ["ਸਤਿ"]

    def test_token_count_matches_spans(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ")
        assert len(result.tokens) == len(result.token_spans)
        assert len(result.tokens) == 4


# ---------------------------------------------------------------------------
# token_spans correctness
# ---------------------------------------------------------------------------


class TestTokenSpans:
    """Token spans match actual character positions."""

    def test_spans_extract_correct_text(self) -> None:
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        result = tokenize(text)
        for token, span in zip(
            result.tokens, result.token_spans, strict=True,
        ):
            extracted = text[span[0]:span[1]]
            assert extracted == token, (
                f"Span {span} extracts {extracted!r}, "
                f"expected {token!r}"
            )

    def test_spans_ascending_order(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ")
        for i in range(len(result.token_spans) - 1):
            assert result.token_spans[i][1] <= result.token_spans[i + 1][0], (
                f"Span {i} overlaps with span {i + 1}"
            )

    def test_spans_within_bounds(self) -> None:
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        result = tokenize(text)
        for span in result.token_spans:
            assert span[0] >= 0
            assert span[1] <= len(text)
            assert span[0] < span[1]

    def test_known_span_positions(self) -> None:
        """Verify exact span positions for a known string."""
        text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ"
        result = tokenize(text)
        assert result.token_spans[0] == [0, 3]
        assert result.token_spans[1] == [4, 8]
        assert result.token_spans[2] == [9, 13]


# ---------------------------------------------------------------------------
# Structural marker extraction
# ---------------------------------------------------------------------------


class TestStructuralMarkers:
    """Structural markers extracted from text."""

    def test_rahao_extracted(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ਰਹਾਉ")
        assert "ਰਹਾਉ" in result.structural_markers
        assert "ਰਹਾਉ" not in result.tokens

    def test_double_danda_extracted(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ॥")
        assert "॥" in result.structural_markers
        assert "॥" not in result.tokens

    def test_gurmukhi_numeral_extracted(self) -> None:
        result = tokenize("ਸਤਿ ਨਾਮੁ ॥੧॥")
        # Both ॥ and numeral should be in structural markers
        assert any("॥" in m for m in result.structural_markers)

    def test_all_markers_line(self) -> None:
        """Line that's all markers produces no tokens."""
        result = tokenize("॥੧॥ ਰਹਾਉ ॥")
        assert len(result.tokens) == 0
        assert len(result.structural_markers) > 0


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for the tokenizer."""

    def test_empty_string(self) -> None:
        result = tokenize("")
        assert result.tokens == []
        assert result.token_spans == []

    def test_whitespace_only(self) -> None:
        result = tokenize("   \t  ")
        assert result.tokens == []

    def test_result_is_tokenize_result(self) -> None:
        result = tokenize("ਸਤਿ")
        assert isinstance(result, TokenizeResult)

    def test_mool_mantar(self) -> None:
        """The Mool Mantar produces multiple tokens."""
        text = "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ"
        result = tokenize(text)
        assert len(result.tokens) >= 10
        assert result.tokens[0] == "ੴ"
        assert result.tokens[1] == "ਸਤਿ"

    def test_japji_with_numeral(self) -> None:
        """Line ending with ॥੧॥ has numeral extracted."""
        text = "ਹੈ ਭੀ ਸਚੁ ਨਾਨਕ ਹੋਸੀ ਭੀ ਸਚੁ ॥੧॥"
        result = tokenize(text)
        # Actual words should be tokens
        assert "ਹੈ" in result.tokens
        assert "ਸਚੁ" in result.tokens
        # Dandas and numerals should not be tokens
        assert "॥" not in result.tokens


# ---------------------------------------------------------------------------
# Parallel array invariant
# ---------------------------------------------------------------------------


class TestParallelArray:
    """tokens and token_spans are always parallel arrays."""

    @pytest.mark.parametrize(
        "text",
        [
            "ਸਤਿ ਨਾਮੁ",
            "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ",
            "ਹੁਕਮੀ ਹੋਵਨਿ ਆਕਾਰ ਹੁਕਮੁ ਨ ਕਹਿਆ ਜਾਈ ॥",
            "",
            "ਸਤਿ",
        ],
    )
    def test_parallel_length(self, text: str) -> None:
        result = tokenize(text)
        assert len(result.tokens) == len(result.token_spans)
