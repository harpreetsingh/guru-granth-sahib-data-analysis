"""Whitespace tokenizer with token_spans tracking (bd-15c.2).

Splits normalized Gurmukhi text into tokens and records character
offsets for each token.  Structural markers (rahao, numerals, dandas)
are extracted and removed before tokenization.

Algorithm (PLAN.md Section 3.5):
  1. Extract and remove structural markers (ਰਹਾਉ, numerals ੧੨੩, ॥)
  2. Split on whitespace
  3. Strip residual punctuation from token boundaries
  4. Filter empty tokens

Output: tokens list + token_spans list + structural_markers metadata
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Version — recorded in run_manifest.json
# ---------------------------------------------------------------------------

TOKENIZER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Structural markers to extract before tokenization
# Rahao (ਰਹਾਉ) and its common variant spellings
_RAHAO = re.compile(r"\bਰਹਾਉ\b")

# Gurmukhi numerals used as pauri/stanza markers (stand-alone)
_GURMUKHI_NUMERAL = re.compile(r"[੦੧੨੩੪੫੬੭੮੯]+")

# Double danda (section separator)
_DOUBLE_DANDA = re.compile(r"॥")

# Single danda
_SINGLE_DANDA = re.compile(r"।")

# Residual punctuation that may cling to token boundaries
# Includes common Gurmukhi/Devanagari punctuation
_BOUNDARY_PUNCT = re.compile(
    r"^[।॥;,.\-–—:!?()]+|[।॥;,.\-–—:!?()]+$"
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenizeResult:
    """Result of tokenizing a single line.

    Attributes:
        tokens: List of Gurmukhi word tokens.
        token_spans: Parallel list of ``[start, end]`` char offsets
            into the original ``gurmukhi`` string.
        structural_markers: Extracted markers (ਰਹਾਉ, numerals, ॥)
            with their original positions.
    """

    tokens: list[str] = field(default_factory=list)
    token_spans: list[list[int]] = field(default_factory=list)
    structural_markers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core tokenizer
# ---------------------------------------------------------------------------


def _extract_structural_markers(text: str) -> tuple[str, list[str]]:
    """Extract structural markers and return cleaned text + markers.

    Structural markers include:
      - ਰਹਾਉ (rahao / pause marker)
      - Gurmukhi numerals at word boundaries (pauri markers like ੧, ੨੩)
      - ॥ (double danda — section separator)
      - । (single danda)

    The markers are extracted (removed from text) so that they do not
    become tokens.  They are returned as a list for metadata storage.
    """
    markers: list[str] = []

    # Extract rahao
    for m in _RAHAO.finditer(text):
        markers.append(m.group())
    text = _RAHAO.sub(" ", text)

    # Extract double dandas (before single, to avoid partial matches)
    for m in _DOUBLE_DANDA.finditer(text):
        markers.append(m.group())
    text = _DOUBLE_DANDA.sub(" ", text)

    # Extract single dandas
    for m in _SINGLE_DANDA.finditer(text):
        markers.append(m.group())
    text = _SINGLE_DANDA.sub(" ", text)

    # Extract stand-alone Gurmukhi numerals.
    # We only extract numerals that are surrounded by whitespace or
    # string boundaries (stand-alone markers, not part of a word).
    numeral_pattern = re.compile(r"(?:^|\s)([੦੧੨੩੪੫੬੭੮੯]+)(?:\s|$)")
    for m in numeral_pattern.finditer(text):
        markers.append(m.group(1))
    text = numeral_pattern.sub(" ", text)

    return text, markers


def _strip_boundary_punct(token: str) -> str:
    """Remove punctuation that clings to token boundaries."""
    return _BOUNDARY_PUNCT.sub("", token)


def tokenize(gurmukhi: str) -> TokenizeResult:
    """Tokenize a normalized Gurmukhi string.

    Args:
        gurmukhi: Post-normalization Gurmukhi text.

    Returns:
        A :class:`TokenizeResult` with tokens, spans, and markers.
    """
    if not gurmukhi or not gurmukhi.strip():
        return TokenizeResult()

    # Step 1: Extract structural markers
    cleaned, structural_markers = _extract_structural_markers(gurmukhi)

    # Step 2: Split on whitespace and compute spans
    # We iterate over the original (post-marker-extraction) text to
    # find token positions.  Since we replaced markers with spaces,
    # we need to track positions in the ORIGINAL gurmukhi string.
    #
    # Strategy: find each token's position in the original string
    # by scanning for the actual text.
    tokens: list[str] = []
    token_spans: list[list[int]] = []

    # Use regex to find word-like sequences in the original string,
    # skipping structural markers
    # A "word" is a sequence of non-whitespace, non-danda, non-numeral-marker chars
    # Actually, we should find tokens in the cleaned text first,
    # then map back to original positions.

    # Simpler approach: iterate through original string, build
    # tokens by finding their positions directly.
    pos = 0
    for raw_token in cleaned.split():
        # Strip residual punctuation
        token = _strip_boundary_punct(raw_token)
        if not token:
            continue

        # Find this token in the original gurmukhi string
        # Search from current position forward
        idx = gurmukhi.find(token, pos)
        if idx == -1:
            # If exact match fails (marker removal changed text),
            # try from beginning as fallback
            idx = gurmukhi.find(token)
        if idx == -1:
            # Token was manufactured by marker removal — skip
            continue

        tokens.append(token)
        token_spans.append([idx, idx + len(token)])
        pos = idx + len(token)

    return TokenizeResult(
        tokens=tokens,
        token_spans=token_spans,
        structural_markers=structural_markers,
    )
