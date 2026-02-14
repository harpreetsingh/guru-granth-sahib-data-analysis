"""SriGranth.org scraper with rate-limiting and protocol compliance (bd-15c.5).

Fetches HTML pages for all 1430 angs with:
  - 500-1500ms random jitter between requests
  - Exponential backoff retry (max 5 retries)
  - Resumable via scrape_state.json
  - Clear User-Agent identification
  - Hard stop on repeated 403/429

Ethics: We are guests on their server.  Rate limiting and transparency
are non-negotiable.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from ggs import __version__
from ggs.corpus.parse_srigranth import parse_ang

_console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = (
    "https://www.srigranth.org/servlet/gurbani.gurbani"
    "?Action=Page&Param={ang}"
)
USER_AGENT = f"ggs-text-analysis/{__version__}"
DEFAULT_TIMEOUT = 30.0  # seconds


# ---------------------------------------------------------------------------
# Failure types (Section 3.2)
# ---------------------------------------------------------------------------


class FailureType(StrEnum):
    FETCH_HTTP_ERROR = "FETCH_HTTP_ERROR"
    FETCH_TIMEOUT = "FETCH_TIMEOUT"
    FETCH_BLOCKED = "FETCH_BLOCKED"
    PARSE_SELECTOR_FAIL = "PARSE_SELECTOR_FAIL"
    PARSE_HEURISTIC_FAIL = "PARSE_HEURISTIC_FAIL"
    OUTPUT_WRITE_FAIL = "OUTPUT_WRITE_FAIL"


@dataclass
class ScrapeFailure:
    """A single scrape failure record."""

    ang: int
    failure_type: str
    message: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    http_status: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Scrape state (resumability)
# ---------------------------------------------------------------------------


@dataclass
class ScrapeState:
    """Persistent scrape state for resumability."""

    completed_angs: set[int] = field(default_factory=set)
    failed_angs: dict[int, str] = field(default_factory=dict)
    started_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    last_updated: str = ""
    consecutive_blocks: int = 0

    @classmethod
    def load(cls, path: Path) -> ScrapeState:
        """Load state from JSON, or return fresh state."""
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        state = cls()
        state.completed_angs = set(data.get("completed_angs", []))
        state.failed_angs = {
            int(k): v
            for k, v in data.get("failed_angs", {}).items()
        }
        state.started_at = data.get("started_at", "")
        state.last_updated = data.get("last_updated", "")
        state.consecutive_blocks = data.get(
            "consecutive_blocks", 0,
        )
        return state

    def save(self, path: Path) -> None:
        """Persist state to JSON."""
        self.last_updated = datetime.now(UTC).isoformat()
        data = {
            "completed_angs": sorted(self.completed_angs),
            "failed_angs": dict(self.failed_angs),
            "started_at": self.started_at,
            "last_updated": self.last_updated,
            "consecutive_blocks": self.consecutive_blocks,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Scraper configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScrapeConfig:
    """Scraping configuration (from config.yaml)."""

    ang_start: int = 1
    ang_end: int = 1430
    delay_ms_min: int = 500
    delay_ms_max: int = 1500
    max_retries: int = 5
    max_consecutive_blocks: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScrapeConfig:
        return cls(
            ang_start=int(
                data.get("ang_start", 1),
            ),
            ang_end=int(
                data.get("ang_end", 1430),
            ),
            delay_ms_min=int(
                data.get("request_delay_ms_min", 500),
            ),
            delay_ms_max=int(
                data.get("request_delay_ms_max", 1500),
            ),
            max_retries=int(
                data.get("max_retries", 5),
            ),
        )


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------


def _jitter_delay(config: ScrapeConfig) -> None:
    """Sleep for a random duration within configured range."""
    delay_ms = random.randint(
        config.delay_ms_min, config.delay_ms_max,
    )
    time.sleep(delay_ms / 1000.0)


def _backoff_delay(attempt: int) -> None:
    """Exponential backoff: 2^attempt seconds, capped at 32s."""
    delay = min(2**attempt, 32)
    _console.print(
        f"  [yellow]Retry in {delay}s (attempt {attempt})[/yellow]"
    )
    time.sleep(delay)


def fetch_ang(
    ang: int,
    *,
    client: httpx.Client,
    config: ScrapeConfig,
) -> tuple[str | None, ScrapeFailure | None]:
    """Fetch a single ang's HTML with retries.

    Returns (html, None) on success, or (None, failure) on error.
    """
    url = BASE_URL.format(ang=ang)

    for attempt in range(config.max_retries):
        try:
            response = client.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code in (403, 429):
                return None, ScrapeFailure(
                    ang=ang,
                    failure_type=FailureType.FETCH_BLOCKED,
                    message=(
                        f"Blocked: HTTP {response.status_code}"
                    ),
                    http_status=response.status_code,
                )

            if response.status_code != 200:
                if attempt < config.max_retries - 1:
                    _backoff_delay(attempt)
                    continue
                return None, ScrapeFailure(
                    ang=ang,
                    failure_type=FailureType.FETCH_HTTP_ERROR,
                    message=(
                        f"HTTP {response.status_code}"
                    ),
                    http_status=response.status_code,
                )

            return response.text, None

        except httpx.TimeoutException:
            if attempt < config.max_retries - 1:
                _backoff_delay(attempt)
                continue
            return None, ScrapeFailure(
                ang=ang,
                failure_type=FailureType.FETCH_TIMEOUT,
                message="Request timed out after all retries",
            )

        except httpx.HTTPError as exc:
            if attempt < config.max_retries - 1:
                _backoff_delay(attempt)
                continue
            return None, ScrapeFailure(
                ang=ang,
                failure_type=FailureType.FETCH_HTTP_ERROR,
                message=str(exc),
            )

    return None, ScrapeFailure(
        ang=ang,
        failure_type=FailureType.FETCH_HTTP_ERROR,
        message="Exhausted all retries",
    )


def scrape_corpus(
    output_dir: Path,
    *,
    config: ScrapeConfig | None = None,
) -> ScrapeState:
    """Scrape all angs from SriGranth.org.

    Args:
        output_dir: Directory for HTML files (data/raw_html/).
        config: Scraping configuration.

    Returns:
        Final :class:`ScrapeState`.
    """
    if config is None:
        config = ScrapeConfig()

    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "scrape_state.json"
    failures_path = output_dir / "failures.jsonl"

    state = ScrapeState.load(state_path)
    failures: list[ScrapeFailure] = []

    angs_to_fetch = [
        ang
        for ang in range(config.ang_start, config.ang_end + 1)
        if ang not in state.completed_angs
    ]

    if not angs_to_fetch:
        _console.print(
            "[green]All angs already scraped.[/green]"
        )
        return state

    _console.print(
        f"\n[bold]Scraping {len(angs_to_fetch)} angs "
        f"({config.ang_start}-{config.ang_end})...[/bold]\n"
    )

    with (
        httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client,
        Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=_console,
        ) as progress,
    ):
        task = progress.add_task(
            "Scraping", total=len(angs_to_fetch),
        )

        for ang in angs_to_fetch:
            # Check for hard stop on repeated blocks
            if (
                state.consecutive_blocks
                >= config.max_consecutive_blocks
            ):
                _console.print(
                    "\n[bold red]HARD STOP:[/bold red] "
                    f"{state.consecutive_blocks} consecutive "
                    "blocked requests. Stopping to avoid "
                    "further issues.\n"
                )
                break

            # Rate limiting jitter
            _jitter_delay(config)

            # Fetch
            html, failure = fetch_ang(
                ang, client=client, config=config,
            )

            if failure is not None:
                failures.append(failure)
                state.failed_angs[ang] = failure.failure_type

                if (
                    failure.failure_type
                    == FailureType.FETCH_BLOCKED
                ):
                    state.consecutive_blocks += 1
                else:
                    state.consecutive_blocks = 0

                progress.advance(task)
                continue

            # Reset block counter on success
            state.consecutive_blocks = 0

            # Validate HTML is parseable
            result = parse_ang(html, ang)  # type: ignore[arg-type]
            if result.errors:
                failures.append(
                    ScrapeFailure(
                        ang=ang,
                        failure_type=(
                            FailureType.PARSE_SELECTOR_FAIL
                        ),
                        message=str(result.errors[0]),
                    ),
                )
                state.failed_angs[ang] = (
                    FailureType.PARSE_SELECTOR_FAIL
                )
            else:
                # Write HTML
                html_path = output_dir / f"ang_{ang:04d}.html"
                try:
                    html_path.write_text(
                        html, encoding="utf-8",  # type: ignore[arg-type]
                    )
                    state.completed_angs.add(ang)
                except OSError as exc:
                    failures.append(
                        ScrapeFailure(
                            ang=ang,
                            failure_type=(
                                FailureType.OUTPUT_WRITE_FAIL
                            ),
                            message=str(exc),
                        ),
                    )

            # Save state periodically
            if ang % 10 == 0:
                state.save(state_path)

            progress.advance(task)

    # Final save
    state.save(state_path)

    # Write failures log
    if failures:
        with failures_path.open("a", encoding="utf-8") as fh:
            for f in failures:
                fh.write(
                    json.dumps(f.to_dict(), ensure_ascii=False)
                    + "\n"
                )

    _console.print(
        f"\n[bold green]Done.[/bold green] "
        f"Completed: {len(state.completed_angs)}, "
        f"Failed: {len(failures)}\n"
    )

    return state
