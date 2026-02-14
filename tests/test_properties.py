"""Property-based tests with Hypothesis (bd-3jj.8).

Uses Hypothesis to verify invariants that must hold for ALL inputs,
catching edge cases that hand-picked tests miss.

Properties tested:
  1. Normalization is idempotent
  2. Tokenization produces valid spans
  3. Match spans are within line bounds
  4. Match spans don't cross for the same entity
  5. Feature densities are bounded [0.0, 1.0]
  6. Feature density formula is correct (count / token_count)
  7. Co-occurrence pairs are alphabetically ordered
  8. Sigmoid output is bounded (0, 1)
"""

from __future__ import annotations

from pathlib import Path

import hypothesis.strategies as st
from hypothesis import given, settings

from ggs.analysis.cooccurrence import (
    WindowLevel,
    compute_cooccurrence,
)
from ggs.analysis.features import _compute_density
from ggs.analysis.match import MatchingEngine, MatchRecord
from ggs.analysis.scores import sigmoid
from ggs.corpus.normalize import normalize
from ggs.corpus.tokenize import tokenize
from ggs.lexicon.loader import LexiconIndex, load_lexicon

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Gurmukhi Unicode range: 0x0A00 - 0x0A7F
# Plus common Gurmukhi punctuation: danda, double danda, Ek Onkar
_GURMUKHI_RANGE = "".join(
    chr(c) for c in range(0x0A00, 0x0A80)
    if chr(c).isprintable()
)
_PUNCTUATION = "।॥ੴ"
_WHITESPACE = " "

gurmukhi_char = st.sampled_from(_GURMUKHI_RANGE + _PUNCTUATION + _WHITESPACE)

gurmukhi_text = st.text(
    alphabet=gurmukhi_char,
    min_size=0,
    max_size=200,
)

gurmukhi_word = st.text(
    alphabet=st.sampled_from(_GURMUKHI_RANGE),
    min_size=1,
    max_size=20,
)

gurmukhi_line = st.lists(gurmukhi_word, min_size=1, max_size=15).map(
    " ".join,
)

# Strategy for positive integers (token counts)
positive_int = st.integers(min_value=1, max_value=1000)
non_negative_int = st.integers(min_value=0, max_value=1000)

# Strategy for entity IDs (uppercase letters)
entity_id = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
    min_size=2,
    max_size=15,
).filter(lambda s: s[0].isalpha())

# Strategy for sets of entity IDs
entity_set = st.frozensets(entity_id, min_size=0, max_size=10)


# ---------------------------------------------------------------------------
# Shared fixtures (built once, reused)
# ---------------------------------------------------------------------------


def _get_test_engine() -> MatchingEngine:
    """Build matching engine from test fixtures lexicon."""
    paths = {
        "test": "tests/fixtures/lexicon/test_entities.yaml",
    }
    index = load_lexicon(paths, base_dir=Path("."))
    return MatchingEngine.from_lexicon(index)


def _get_test_lexicon_index() -> LexiconIndex:
    """Load test lexicon index."""
    paths = {
        "test": "tests/fixtures/lexicon/test_entities.yaml",
    }
    return load_lexicon(paths, base_dir=Path("."))


# Module-level singletons to avoid rebuilding per test
_TEST_ENGINE = _get_test_engine()
_TEST_INDEX = _get_test_lexicon_index()

# Known entity surface forms from the test lexicon
_KNOWN_FORMS = _TEST_INDEX.all_surface_forms()


# ---------------------------------------------------------------------------
# Property 1: Normalization is idempotent
# ---------------------------------------------------------------------------


class TestNormalizationIdempotent:
    """normalize(normalize(x)) == normalize(x) for all x."""

    @given(text=gurmukhi_text)
    @settings(max_examples=200)
    def test_idempotent(self, text: str) -> None:
        once = normalize(text)
        twice = normalize(once)
        assert once == twice, (
            f"Normalization not idempotent:\n"
            f"  input:  {text!r}\n"
            f"  once:   {once!r}\n"
            f"  twice:  {twice!r}"
        )

    @given(text=gurmukhi_text)
    @settings(max_examples=100)
    def test_output_is_stripped(self, text: str) -> None:
        result = normalize(text)
        if result:
            assert result == result.strip()

    @given(text=gurmukhi_text)
    @settings(max_examples=100)
    def test_no_double_spaces(self, text: str) -> None:
        result = normalize(text)
        assert "  " not in result


# ---------------------------------------------------------------------------
# Property 2: Tokenization produces valid spans
# ---------------------------------------------------------------------------


class TestTokenizationSpans:
    """Token spans are valid character offsets into the original string."""

    @given(line=gurmukhi_line)
    @settings(max_examples=200)
    def test_spans_within_bounds(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        result = tokenize(normalized)
        for span in result.token_spans:
            assert span[0] >= 0
            assert span[1] <= len(normalized)
            assert span[0] < span[1]

    @given(line=gurmukhi_line)
    @settings(max_examples=200)
    def test_spans_extract_to_tokens(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        result = tokenize(normalized)
        for token, span in zip(
            result.tokens, result.token_spans, strict=True,
        ):
            extracted = normalized[span[0]:span[1]]
            assert extracted == token, (
                f"Span {span} extracts {extracted!r}, "
                f"expected {token!r}"
            )

    @given(line=gurmukhi_line)
    @settings(max_examples=100)
    def test_spans_are_non_overlapping(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        result = tokenize(normalized)
        for i in range(1, len(result.token_spans)):
            prev_end = result.token_spans[i - 1][1]
            curr_start = result.token_spans[i][0]
            assert curr_start >= prev_end, (
                f"Overlapping spans: {result.token_spans[i - 1]} "
                f"and {result.token_spans[i]}"
            )


# ---------------------------------------------------------------------------
# Property 3: Match spans are within line bounds
# ---------------------------------------------------------------------------


class TestMatchSpanBounds:
    """All match spans fall within [0, len(gurmukhi)]."""

    @given(line=gurmukhi_line)
    @settings(max_examples=200)
    def test_spans_within_text(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        matches = _TEST_ENGINE.match_line(normalized, "prop_test")
        for m in matches:
            assert m.span[0] >= 0, (
                f"Span start {m.span[0]} < 0"
            )
            assert m.span[1] <= len(normalized), (
                f"Span end {m.span[1]} > len({len(normalized)})"
            )
            assert m.span[0] < m.span[1], (
                f"Empty or reversed span: {m.span}"
            )

    @given(line=gurmukhi_line)
    @settings(max_examples=200)
    def test_spans_extract_matched_form(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        matches = _TEST_ENGINE.match_line(normalized, "prop_test")
        for m in matches:
            extracted = normalized[m.span[0]:m.span[1]]
            assert extracted == m.matched_form, (
                f"Span extracts {extracted!r}, "
                f"expected {m.matched_form!r}"
            )


# ---------------------------------------------------------------------------
# Property 4: No crossing overlaps for same entity
# ---------------------------------------------------------------------------


class TestMatchNoCrossingOverlap:
    """No two matches for the SAME entity have crossing spans."""

    @given(line=gurmukhi_line)
    @settings(max_examples=200)
    def test_no_crossing_same_entity(self, line: str) -> None:
        normalized = normalize(line)
        if not normalized:
            return
        matches = _TEST_ENGINE.match_line(normalized, "prop_test")

        # Group by entity_id
        by_entity: dict[str, list[MatchRecord]] = {}
        for m in matches:
            by_entity.setdefault(m.entity_id, []).append(m)

        for entity_id, entity_matches in by_entity.items():
            for i, a in enumerate(entity_matches):
                for b in entity_matches[i + 1:]:
                    # Check for crossing overlap (not nested)
                    if (
                        a.span[0] < b.span[1]
                        and b.span[0] < a.span[1]
                    ):
                        # They overlap — must be nested, not crossing
                        a_contains_b = (
                            a.span[0] <= b.span[0]
                            and a.span[1] >= b.span[1]
                        )
                        b_contains_a = (
                            b.span[0] <= a.span[0]
                            and b.span[1] >= a.span[1]
                        )
                        assert a_contains_b or b_contains_a, (
                            f"Crossing overlap for {entity_id}: "
                            f"{a.span} and {b.span}"
                        )


# ---------------------------------------------------------------------------
# Property 5: Feature densities bounded [0.0, 1.0]
# ---------------------------------------------------------------------------


class TestFeatureDensityBounds:
    """Feature density values are always in [0.0, 1.0]."""

    @given(
        count=non_negative_int,
        token_count=positive_int,
    )
    @settings(max_examples=200)
    def test_density_bounded(
        self, count: int, token_count: int,
    ) -> None:
        # Density only makes sense if count <= token_count
        count = min(count, token_count)
        density = _compute_density(count, token_count)
        assert 0.0 <= density <= 1.0, (
            f"Density {density} out of bounds for "
            f"count={count}, tokens={token_count}"
        )

    @given(token_count=positive_int)
    @settings(max_examples=100)
    def test_zero_count_zero_density(
        self, token_count: int,
    ) -> None:
        density = _compute_density(0, token_count)
        assert density == 0.0


# ---------------------------------------------------------------------------
# Property 6: Feature density formula
# ---------------------------------------------------------------------------


class TestFeatureDensityFormula:
    """density = count / token_count."""

    @given(
        count=st.integers(min_value=0, max_value=50),
        token_count=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=200)
    def test_formula_correct(
        self, count: int, token_count: int,
    ) -> None:
        count = min(count, token_count)
        density = _compute_density(count, token_count)
        expected = round(count / token_count, 6)
        assert abs(density - expected) < 1e-10


# ---------------------------------------------------------------------------
# Property 7: Co-occurrence pairs are alphabetically ordered
# ---------------------------------------------------------------------------


class TestCooccurrenceOrdering:
    """Entity pairs always have entity_a < entity_b."""

    @given(
        entities_per_window=st.lists(
            entity_set,
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_pairs_ordered(
        self, entities_per_window: list[frozenset[str]],
    ) -> None:
        windows = {
            f"w{i}": set(entities)
            for i, entities in enumerate(entities_per_window)
        }
        pairs = compute_cooccurrence(
            windows, WindowLevel.LINE, min_count=1,
        )
        for p in pairs:
            assert p.entity_a < p.entity_b, (
                f"Pair not alphabetically ordered: "
                f"({p.entity_a!r}, {p.entity_b!r})"
            )


# ---------------------------------------------------------------------------
# Property 8: Sigmoid output bounded (0, 1)
# ---------------------------------------------------------------------------


class TestSigmoidBounds:
    """Sigmoid output is always in (0, 1) for finite inputs."""

    @given(
        x=st.floats(min_value=-100, max_value=100),
        k=st.floats(min_value=0.1, max_value=10.0),
        x0=st.floats(min_value=-10.0, max_value=10.0),
    )
    @settings(max_examples=300)
    def test_bounded(self, x: float, k: float, x0: float) -> None:
        result = sigmoid(x, k, x0)
        assert 0.0 <= result <= 1.0, (
            f"sigmoid({x}, {k}, {x0}) = {result} out of bounds"
        )

    @given(
        k=st.floats(min_value=0.1, max_value=10.0),
        x0=st.floats(min_value=-10.0, max_value=10.0),
    )
    @settings(max_examples=100)
    def test_midpoint_is_half(self, k: float, x0: float) -> None:
        result = sigmoid(x0, k, x0)
        assert abs(result - 0.5) < 1e-10
