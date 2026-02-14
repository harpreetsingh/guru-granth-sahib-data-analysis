"""Shared pytest fixtures for GGS test suite."""

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def html_fixtures_dir() -> Path:
    """Path to HTML snapshot fixtures."""
    return FIXTURES_DIR / "html"


@pytest.fixture
def expected_dir() -> Path:
    """Path to expected output fixtures."""
    return FIXTURES_DIR / "expected"


@pytest.fixture
def lexicon_fixtures_dir() -> Path:
    """Path to lexicon test fixtures."""
    return FIXTURES_DIR / "lexicon"


@pytest.fixture
def ang1_html(html_fixtures_dir: Path) -> str:
    """Raw HTML for Ang 1 (Mool Mantar / Japji Sahib opening)."""
    return (html_fixtures_dir / "ang_001.html").read_text(
        encoding="utf-8",
    )


@pytest.fixture
def normalization_cases(expected_dir: Path) -> list[dict]:
    """Load normalization test cases from YAML fixture."""
    path = expected_dir / "normalization_cases.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    cases = []
    for case in data["cases"]:
        # Merge defaults into each case (case values take precedence)
        merged = {**defaults, **case}
        cases.append(merged)
    return cases


@pytest.fixture
def test_lexicon(lexicon_fixtures_dir: Path) -> dict:
    """Load the test lexicon fixture."""
    path = lexicon_fixtures_dir / "test_entities.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture
def sample_gurmukhi_lines() -> list[str]:
    """A handful of well-known Gurmukhi lines for quick tests."""
    return [
        "ੴ ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ ਨਿਰਭਉ ਨਿਰਵੈਰੁ ਅਕਾਲ ਮੂਰਤਿ ਅਜੂਨੀ ਸੈਭੰ ਗੁਰ ਪ੍ਰਸਾਦਿ ॥",
        "ਆਦਿ ਸਚੁ ਜੁਗਾਦਿ ਸਚੁ ॥",
        "ਹੈ ਭੀ ਸਚੁ ਨਾਨਕ ਹੋਸੀ ਭੀ ਸਚੁ ॥੧॥",
        "ਹੁਕਮੀ ਹੋਵਨਿ ਆਕਾਰ ਹੁਕਮੁ ਨ ਕਹਿਆ ਜਾਈ ॥",
        "ਨਾਨਕ ਹੁਕਮੈ ਜੇ ਬੁਝੈ ਤ ਹਉਮੈ ਕਹੈ ਨ ਕੋਇ ॥੨॥",
    ]
