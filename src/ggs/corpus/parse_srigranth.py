"""SriGranth HTML parser (bd-15c.3).

Extracts structured Gurmukhi text from SriGranth.org HTML pages.
This is the primary data ingestion path — it produces
``gurmukhi_raw`` (exact Unicode from HTML) along with structural
metadata (author, raga, shabad, rahao, pauri).

The parser does **not** normalize.  Normalization is a separate step
(normalize.py).  This separation means parser bugs don't affect
normalization, and normalization changes don't require re-scraping.

URL pattern::

    https://www.srigranth.org/servlet/gurbani.gurbani?Action=Page&Param=<ANG>

Design:
    - Uses BeautifulSoup + lxml for HTML parsing
    - Extracts line-by-line Gurmukhi, preserving original Unicode exactly
    - Parses structural headers (raga changes, author changes)
    - Produces the canonical record format (PLAN.md Section 3.3)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARSER_VERSION = "1.0.0"

BASE_URL = (
    "https://www.srigranth.org/servlet/gurbani.gurbani"
    "?Action=Page&Param={ang}"
)

# Gurmukhi Rahao marker
_RAHAO_PATTERN = re.compile(r"ਰਹਾਉ")

# Gurmukhi numerals for pauri detection (੧-੯੦)
_GURMUKHI_NUMERAL = re.compile(r"[੦੧੨੩੪੫੬੭੮੯]+")

# Mahalla (author) patterns
_MAHALLA_PATTERNS = [
    re.compile(r"ਮਹਲਾ\s*([੧੨੩੪੫੬੭੮੯]+)"),
    re.compile(r"ਮ(?:ਹ?ਲਾ|:)\s*([੧੨੩੪੫੬੭੮੯]+)"),
]

# Gurmukhi numeral to integer mapping
_GURMUKHI_DIGIT_MAP: dict[str, int] = {
    "੦": 0, "੧": 1, "੨": 2, "੩": 3, "੪": 4,
    "੫": 5, "੬": 6, "੭": 7, "੮": 8, "੯": 9,
}

# Known author ID mappings
_AUTHOR_MAP: dict[str, str] = {
    "1": "M1", "2": "M2", "3": "M3", "4": "M4", "5": "M5", "9": "M9",
}


def _gurmukhi_num_to_int(s: str) -> int | None:
    """Convert a Gurmukhi numeral string to an integer."""
    if not s:
        return None
    try:
        return int("".join(str(_GURMUKHI_DIGIT_MAP[ch]) for ch in s))
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ParsedLine:
    """A single parsed line from the SriGranth HTML.

    This is an intermediate representation before the full canonical
    record is assembled.
    """

    ang: int
    line_number: int  # 1-based within the ang
    gurmukhi_raw: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AngParseResult:
    """Complete parse result for a single ang (page)."""

    ang: int
    lines: list[ParsedLine] = field(default_factory=list)
    raga: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Line UID computation
# ---------------------------------------------------------------------------


def compute_line_uid(
    ang: int,
    gurmukhi: str,
    line_id: str = "",
) -> str:
    """Compute stable line UID from ang + line_id + normalized gurmukhi.

    Format: ``ang<N>:sha256:<first 12 hex chars>``

    The ``line_id`` parameter disambiguates repeated lines (refrains)
    on the same ang.  If omitted, only ang + gurmukhi are hashed
    (legacy behavior).

    Note: This is called with **normalized** gurmukhi (not raw).
    The parser itself stores the raw form; the UID is computed
    later after normalization.
    """
    content = f"{ang}:{line_id}:{gurmukhi}"
    digest = hashlib.sha256(
        content.encode("utf-8"),
    ).hexdigest()[:12]
    return f"ang{ang}:sha256:{digest}"


def compute_shabad_uid(ang: int, first_line_id: str) -> str:
    """Compute stable shabad UID from position.

    Format: ``shabad:sha256:<first 12 hex chars>``

    Position-based (not content-based) so that normalization changes
    to one line don't invalidate sibling lines' shabad_uid.
    """
    content = f"{ang}:{first_line_id}"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    return f"shabad:sha256:{digest}"


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def _extract_gurmukhi_lines(soup: BeautifulSoup) -> list[str]:
    """Extract Gurmukhi text lines from SriGranth HTML.

    SriGranth.org renders each ang as a table-based layout.
    Gurmukhi lines appear in table cells with specific class names
    or font styling.  This function extracts the raw Gurmukhi text
    from those cells.

    The extraction strategy:
    1. Look for elements with class containing 'gurm' or 'punjabi'
    2. Fall back to font-face detection for Gurmukhi Unicode ranges
    3. Filter out translation/transliteration lines
    """
    lines: list[str] = []

    # Strategy 1: Look for table rows containing Gurmukhi class markers
    # SriGranth uses various class names and font-face references
    gurmukhi_elements = soup.find_all(
        ["td", "div", "span", "p"],
        class_=re.compile(r"gurm|punjabi|gurbani", re.IGNORECASE),
    )

    if gurmukhi_elements:
        for elem in gurmukhi_elements:
            text = elem.get_text(strip=True)
            if text and _contains_gurmukhi(text):
                lines.append(text)
        if lines:
            return lines

    # Strategy 2: Find all text nodes containing Gurmukhi characters
    # This is a broader search when class-based extraction fails
    for td in soup.find_all("td"):
        text = td.get_text(strip=True)
        if text and _contains_gurmukhi(text) and len(text) > 2:
            # Skip very short strings (likely numerals or labels)
            # Also skip cells that are primarily non-Gurmukhi
            gurmukhi_ratio = _gurmukhi_char_ratio(text)
            if gurmukhi_ratio > 0.3:
                lines.append(text)

    return lines


def _contains_gurmukhi(text: str) -> bool:
    """Check if text contains Gurmukhi Unicode characters (U+0A00-U+0A7F)."""
    return any("\u0A00" <= ch <= "\u0A7F" for ch in text)


def _gurmukhi_char_ratio(text: str) -> float:
    """Fraction of characters in the Gurmukhi Unicode block."""
    if not text:
        return 0.0
    gurmukhi_count = sum(
        1 for ch in text if "\u0A00" <= ch <= "\u0A7F"
    )
    return gurmukhi_count / len(text)


def _detect_raga(text: str) -> str | None:
    """Detect raga name from a header-like line of text."""
    # Raga headers typically start with ਰਾਗੁ or contain ਰਾਗ
    if "ਰਾਗੁ" in text or "ਰਾਗ" in text:
        return text.strip()
    return None


def _detect_author(text: str) -> str | None:
    """Detect author from Mahalla notation in text."""
    for pattern in _MAHALLA_PATTERNS:
        match = pattern.search(text)
        if match:
            num = _gurmukhi_num_to_int(match.group(1))
            if num is not None:
                return _AUTHOR_MAP.get(str(num), f"M{num}")
    return None


def _detect_rahao(text: str) -> bool:
    """Check if line contains the Rahao marker."""
    return bool(_RAHAO_PATTERN.search(text))


def _detect_pauri(text: str) -> int | None:
    """Detect pauri (stanza) number from Gurmukhi numerals in text."""
    match = _GURMUKHI_NUMERAL.search(text)
    if match:
        return _gurmukhi_num_to_int(match.group())
    return None


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_ang(html: str, ang: int) -> AngParseResult:
    """Parse a single ang's HTML into structured records.

    Args:
        html: Raw HTML string from SriGranth.org.
        ang: The ang number (1-1430).

    Returns:
        An :class:`AngParseResult` with parsed lines and metadata.
    """
    soup = BeautifulSoup(html, "lxml")
    result = AngParseResult(ang=ang)

    raw_lines = _extract_gurmukhi_lines(soup)

    if not raw_lines:
        result.errors.append({
            "error_type": "PARSE_SELECTOR_FAIL",
            "message": (
                f"No Gurmukhi lines found in ang {ang} HTML. "
                "HTML structure may have changed."
            ),
            "context": {"ang": ang},
        })
        return result

    # Track state across lines for structural metadata
    current_raga: str | None = None
    current_author: str | None = None
    shabad_counter = 0

    for idx, raw_text in enumerate(raw_lines, start=1):
        # Detect raga changes from headers
        raga = _detect_raga(raw_text)
        if raga is not None:
            current_raga = raga
            if result.raga is None:
                result.raga = raga

        # Detect author from Mahalla notation
        author = _detect_author(raw_text)
        if author is not None:
            current_author = author
            shabad_counter += 1

        line = ParsedLine(
            ang=ang,
            line_number=idx,
            gurmukhi_raw=raw_text,
            meta={
                "raga": current_raga,
                "author": current_author,
                "shabad_id": (
                    f"{current_raga or 'UNK'}-"
                    f"{shabad_counter:03d}"
                    if shabad_counter > 0
                    else None
                ),
                "rahao": _detect_rahao(raw_text),
                "pauri": _detect_pauri(raw_text),
                "structural_markers": [],
            },
        )
        result.lines.append(line)

    return result


def to_canonical_records(
    parse_result: AngParseResult,
    *,
    normalize_fn: Any | None = None,
) -> list[dict[str, Any]]:
    """Convert parse result to canonical record dicts (Section 3.3).

    Args:
        parse_result: Output of :func:`parse_ang`.
        normalize_fn: Optional normalization function ``str -> str``.
            If provided, ``gurmukhi`` is the normalized form and
            ``line_uid`` is computed from it.  Otherwise ``gurmukhi``
            equals ``gurmukhi_raw``.

    Returns:
        List of canonical record dicts ready for JSONL serialization.
    """
    records: list[dict[str, Any]] = []
    ang = parse_result.ang

    for line in parse_result.lines:
        line_id = f"{ang}:{line.line_number:02d}"

        gurmukhi_raw = line.gurmukhi_raw
        if normalize_fn is not None:
            gurmukhi = normalize_fn(gurmukhi_raw)
        else:
            gurmukhi = gurmukhi_raw

        line_uid = compute_line_uid(
            ang, gurmukhi, line_id=line_id,
        )

        record: dict[str, Any] = {
            "schema_version": "1.0.0",
            "ang": ang,
            "line_id": line_id,
            "line_uid": line_uid,
            "gurmukhi_raw": gurmukhi_raw,
            "gurmukhi": gurmukhi,
            "tokens": [],
            "token_spans": [],
            "meta": dict(line.meta),
            "source_ang_url": BASE_URL.format(ang=ang),
        }
        records.append(record)

    return records


def parse_html(
    html: str,
    ang: int,
) -> list[Tag]:
    """Low-level helper: parse HTML and return Gurmukhi-bearing elements.

    Useful for debugging and test fixture generation.
    """
    soup = BeautifulSoup(html, "lxml")
    elements: list[Tag] = []
    for elem in soup.find_all(
        ["td", "div", "span", "p"],
    ):
        text = elem.get_text(strip=True)
        if text and _contains_gurmukhi(text):
            elements.append(elem)
    return elements
