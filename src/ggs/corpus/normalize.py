"""Gurmukhi Unicode normalization pipeline (bd-15c.1).

Seven-step, ordered pipeline that transforms raw scraped Gurmukhi into a
canonical form suitable for analysis.  Every downstream module consumes
the normalized ``gurmukhi`` field — correctness here is paramount.

Pipeline steps (applied in order):
  1. Unicode NFC
  2. Zero-width character stripping (ZWJ, ZWNJ)
  3. Nukta policy (PRESERVE | STRIP | DUAL)
  4. Nasal marker normalization (CANONICAL_TIPPI | CANONICAL_BINDI | PRESERVE)
  5. Vishram marker handling (STRIP | PRESERVE_SEPARATE)
  6. Halant/conjunct canonicalization (DECOMPOSE | PRESERVE)
  7. Whitespace normalization (collapse runs, trim)

Each step is a pure ``str → str`` function, independently testable.
The full pipeline is idempotent: ``normalize(normalize(x)) == normalize(x)``.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# ---------------------------------------------------------------------------
# Pipeline version — recorded in run_manifest.json
# ---------------------------------------------------------------------------

NORMALIZER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Policy enums
# ---------------------------------------------------------------------------


class NuktaPolicy(StrEnum):
    """How to handle Nukta (਼ U+0A3C) variants."""

    PRESERVE = "PRESERVE"
    STRIP = "STRIP"
    DUAL = "DUAL"


class NasalPolicy(StrEnum):
    """How to normalize nasal markers (Tippi ੰ / Bindi ਂ)."""

    CANONICAL_TIPPI = "CANONICAL_TIPPI"
    CANONICAL_BINDI = "CANONICAL_BINDI"
    PRESERVE = "PRESERVE"


class VishramPolicy(StrEnum):
    """How to handle vishram (pause) markers."""

    STRIP = "STRIP"
    PRESERVE_SEPARATE = "PRESERVE_SEPARATE"


class HalantPolicy(StrEnum):
    """How to handle halant/conjunct forms."""

    DECOMPOSE = "DECOMPOSE"
    PRESERVE = "PRESERVE"


# ---------------------------------------------------------------------------
# Unicode constants for Gurmukhi processing
# ---------------------------------------------------------------------------

# Zero-width characters to strip
ZWJ = "\u200D"  # Zero-Width Joiner
ZWNJ = "\u200C"  # Zero-Width Non-Joiner
ZERO_WIDTH_CHARS = frozenset({ZWJ, ZWNJ})

# Nukta character
NUKTA = "\u0A3C"  # ਼

# Nukta-bearing consonants: base + nukta → composed form
# We map composed (nukta-bearing) forms to their base consonant for STRIP mode.
_NUKTA_MAP: dict[str, str] = {
    "\u0A33": "\u0A32",  # ਲ਼ → ਲ
    "\u0A36": "\u0A38",  # ਸ਼ → ਸ
    "\u0A59": "\u0A16",  # ਖ਼ → ਖ
    "\u0A5A": "\u0A17",  # ਗ਼ → ਗ
    "\u0A5B": "\u0A1C",  # ਜ਼ → ਜ
    "\u0A5C": "\u0A21",  # ੜ  → ਡ (special: ੜ is distinct but has nukta origin)
    "\u0A5E": "\u0A2B",  # ਫ਼ → ਫ
}

# Nasal markers
TIPPI = "\u0A70"  # ੰ
BINDI = "\u0A02"  # ਂ

# Vishram markers commonly found in Gurbani texts
# These include various pause/breath markers used in recitation
_VISHRAM_PATTERNS = re.compile(
    r"[;,]"  # semicolons and commas used as vishram in some sources
    r"|(?<!\d)[।](?!\d)"  # danda (but not between digits)
    r"|॥"  # double danda
)

# Common vishram markers in Gurmukhi texts
_VISHRAM_CHARS = frozenset({
    "\u0964",  # ।  Devanagari danda
    "\u0965",  # ॥  Devanagari double danda
})

# Halant (Virama)
HALANT = "\u0A4D"  # ੍

# Whitespace normalization
_MULTI_SPACE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Step 1 — Unicode NFC
# ---------------------------------------------------------------------------


def step_unicode_nfc(text: str) -> str:
    """Apply Unicode NFC normalization.

    Canonical decomposition followed by canonical composition.  This is the
    standard first step for any Unicode text processing — it ensures that
    equivalent sequences of characters are represented identically.
    """
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------
# Step 2 — Zero-width character stripping
# ---------------------------------------------------------------------------


def step_strip_zero_width(text: str) -> str:
    """Remove ZWJ (U+200D) and ZWNJ (U+200C).

    These are rendering hints inserted by some Gurmukhi fonts / input methods.
    They don't affect linguistic content and must be stripped for consistent
    byte-level comparison.
    """
    return text.translate(str.maketrans("", "", ZWJ + ZWNJ))


# ---------------------------------------------------------------------------
# Step 3 — Nukta policy
# ---------------------------------------------------------------------------


def step_nukta_preserve(text: str) -> str:
    """PRESERVE policy: keep nukta variants distinct (no-op after NFC)."""
    return text


def step_nukta_strip(text: str) -> str:
    """STRIP policy: collapse nukta-bearing consonants to their base forms.

    This operates in two passes:
      1. Replace pre-composed nukta letters (e.g. ਖ਼ U+0A59) with base form.
      2. Remove any remaining standalone nukta (U+0A3C) that was in
         decomposed form (base + nukta).
    """
    # Pass 1: pre-composed nukta letters
    for composed, base in _NUKTA_MAP.items():
        text = text.replace(composed, base)
    # Pass 2: standalone nukta characters
    text = text.replace(NUKTA, "")
    return text


# ---------------------------------------------------------------------------
# Step 4 — Nasal marker normalization
# ---------------------------------------------------------------------------


def step_nasal_canonical_tippi(text: str) -> str:
    """Normalize all Bindi (ਂ) to Tippi (ੰ)."""
    return text.replace(BINDI, TIPPI)


def step_nasal_canonical_bindi(text: str) -> str:
    """Normalize all Tippi (ੰ) to Bindi (ਂ)."""
    return text.replace(TIPPI, BINDI)


def step_nasal_preserve(text: str) -> str:
    """PRESERVE policy: keep source nasal form as-is."""
    return text


# ---------------------------------------------------------------------------
# Step 5 — Vishram marker handling
# ---------------------------------------------------------------------------


def step_vishram_strip(text: str) -> str:
    """STRIP policy: remove vishram (pause) markers entirely.

    Vishram markers are performative notation, not linguistic content.
    We remove common vishram characters used in Gurbani digital texts.
    """
    # Remove vishram punctuation characters
    text = _VISHRAM_PATTERNS.sub("", text)
    return text


def step_vishram_preserve_separate(text: str) -> str:
    """PRESERVE_SEPARATE policy: keep vishram markers but ensure they
    are whitespace-separated so they become their own tokens.
    """
    for char in _VISHRAM_CHARS:
        text = text.replace(char, f" {char} ")
    return text


# ---------------------------------------------------------------------------
# Step 6 — Halant/conjunct canonicalization
# ---------------------------------------------------------------------------


def step_halant_decompose(text: str) -> str:
    """DECOMPOSE policy: decompose pre-composed conjunct forms.

    In Gurmukhi, conjuncts are formed with halant (੍ U+0A4D).  Different
    fonts and input methods may produce different byte sequences for the
    same visual glyph.  Unicode NFC (Step 1) already handles canonical
    ordering, but we additionally ensure that any platform-specific
    pre-composed ligature forms are decomposed to their constituent parts
    (base + halant + second consonant).

    In practice, after NFC, Gurmukhi conjuncts are already in their
    canonical decomposed form (base + halant + following consonant).
    This step is a safeguard that runs NFD on Gurmukhi-range characters
    and then re-applies NFC to ensure the canonical representation.
    """
    # Apply NFD then NFC to ensure maximum canonical decomposition
    # This catches any edge-case pre-composed forms that NFC alone
    # might not decompose (e.g. platform-specific extensions)
    text = unicodedata.normalize("NFD", text)
    text = unicodedata.normalize("NFC", text)
    return text


def step_halant_preserve(text: str) -> str:
    """PRESERVE policy: keep source conjunct encoding as-is."""
    return text


# ---------------------------------------------------------------------------
# Step 7 — Whitespace normalization
# ---------------------------------------------------------------------------


def step_normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space, trim leading/trailing."""
    return _MULTI_SPACE.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------


class NormalizationConfig:
    """Configuration for the normalization pipeline.

    Parameters mirror the ``normalization:`` section of ``config.yaml``.
    All parameters have defaults matching the PLAN.md specification.
    """

    def __init__(
        self,
        *,
        nukta_policy: NuktaPolicy | str = NuktaPolicy.PRESERVE,
        nasal_policy: NasalPolicy | str = NasalPolicy.CANONICAL_TIPPI,
        vishram_policy: VishramPolicy | str = VishramPolicy.STRIP,
        halant_policy: HalantPolicy | str = HalantPolicy.DECOMPOSE,
    ) -> None:
        self.nukta_policy = NuktaPolicy(nukta_policy)
        self.nasal_policy = NasalPolicy(nasal_policy)
        self.vishram_policy = VishramPolicy(vishram_policy)
        self.halant_policy = HalantPolicy(halant_policy)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> NormalizationConfig:
        """Create from the ``normalization:`` section of config.yaml."""
        return cls(
            nukta_policy=data.get("nukta_policy", "PRESERVE"),
            nasal_policy=data.get("nasal_policy", "CANONICAL_TIPPI"),
            vishram_policy=data.get("vishram_policy", "STRIP"),
            halant_policy=data.get("halant_policy", "DECOMPOSE"),
        )


# ---------------------------------------------------------------------------
# Pipeline dispatch tables
# ---------------------------------------------------------------------------

_NUKTA_DISPATCH: dict[NuktaPolicy, type[object] | object] = {
    NuktaPolicy.PRESERVE: step_nukta_preserve,
    NuktaPolicy.STRIP: step_nukta_strip,
    # DUAL handled specially in normalize()
}

_NASAL_DISPATCH = {
    NasalPolicy.CANONICAL_TIPPI: step_nasal_canonical_tippi,
    NasalPolicy.CANONICAL_BINDI: step_nasal_canonical_bindi,
    NasalPolicy.PRESERVE: step_nasal_preserve,
}

_VISHRAM_DISPATCH = {
    VishramPolicy.STRIP: step_vishram_strip,
    VishramPolicy.PRESERVE_SEPARATE: step_vishram_preserve_separate,
}

_HALANT_DISPATCH = {
    HalantPolicy.DECOMPOSE: step_halant_decompose,
    HalantPolicy.PRESERVE: step_halant_preserve,
}


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------


def normalize(
    text: str,
    config: NormalizationConfig | None = None,
) -> str:
    """Apply the full 7-step normalization pipeline.

    Args:
        text: Raw Gurmukhi Unicode string.
        config: Pipeline configuration.  Uses defaults if *None*.

    Returns:
        Canonicalized Gurmukhi string suitable for analysis.

    The pipeline is idempotent: ``normalize(normalize(x)) == normalize(x)``.
    """
    if config is None:
        config = NormalizationConfig()

    # Step 1 — Unicode NFC
    text = step_unicode_nfc(text)

    # Step 2 — Zero-width character stripping
    text = step_strip_zero_width(text)

    # Step 3 — Nukta policy
    if config.nukta_policy is NuktaPolicy.DUAL:
        # DUAL mode is handled by the caller — for the canonical form,
        # we PRESERVE.  The caller should invoke step_nukta_strip
        # separately to get the stripped variant.
        text = step_nukta_preserve(text)
    else:
        nukta_fn = _NUKTA_DISPATCH[config.nukta_policy]
        text = nukta_fn(text)  # type: ignore[operator]

    # Step 4 — Nasal marker normalization
    nasal_fn = _NASAL_DISPATCH[config.nasal_policy]
    text = nasal_fn(text)

    # Step 5 — Vishram marker handling
    vishram_fn = _VISHRAM_DISPATCH[config.vishram_policy]
    text = vishram_fn(text)

    # Step 6 — Halant/conjunct canonicalization
    halant_fn = _HALANT_DISPATCH[config.halant_policy]
    text = halant_fn(text)

    # Step 7 — Whitespace normalization
    text = step_normalize_whitespace(text)

    return text


def normalize_dual(
    text: str,
    config: NormalizationConfig | None = None,
) -> tuple[str, str]:
    """Normalize with DUAL nukta policy, returning both forms.

    Args:
        text: Raw Gurmukhi Unicode string.
        config: Pipeline configuration (nukta_policy is overridden).

    Returns:
        A tuple of ``(preserved_form, stripped_form)`` where:
        - ``preserved_form`` keeps nukta variants distinct
        - ``stripped_form`` collapses nukta variants to base consonants
    """
    if config is None:
        config = NormalizationConfig()

    # Force PRESERVE for the first pass
    preserve_config = NormalizationConfig(
        nukta_policy=NuktaPolicy.PRESERVE,
        nasal_policy=config.nasal_policy,
        vishram_policy=config.vishram_policy,
        halant_policy=config.halant_policy,
    )
    preserved = normalize(text, preserve_config)

    # Force STRIP for the second pass
    strip_config = NormalizationConfig(
        nukta_policy=NuktaPolicy.STRIP,
        nasal_policy=config.nasal_policy,
        vishram_policy=config.vishram_policy,
        halant_policy=config.halant_policy,
    )
    stripped = normalize(text, strip_config)

    return preserved, stripped


def build_step_names(config: NormalizationConfig | None = None) -> Sequence[str]:
    """Return human-readable names of the active pipeline steps.

    Useful for logging and provenance tracking.
    """
    if config is None:
        config = NormalizationConfig()
    return [
        "unicode_nfc",
        "strip_zero_width",
        f"nukta:{config.nukta_policy.value}",
        f"nasal:{config.nasal_policy.value}",
        f"vishram:{config.vishram_policy.value}",
        f"halant:{config.halant_policy.value}",
        "whitespace_normalize",
    ]
