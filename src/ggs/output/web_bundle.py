"""Web bundle builder — ang-range chunks, aggregates, manifest (bd-9i3.1, bd-9i3.2).

Orchestrates assembly of all pipeline outputs into the ``web_bundle/``
directory. This is the final step in the analysis pipeline, producing
the data files consumed by the webapp.

Bundle structure::

    web_bundle/
        corpus/             # Ang-range corpus chunks
            chunk_001-100.json
            chunk_101-200.json
            ...
        aggregates.json     # Pre-computed summary statistics
        search_index.json   # Pre-built search index
        manifest.json       # Integrity hashes for all bundle files
        lineage.json        # Provenance / pipeline metadata

Each corpus chunk contains self-contained data for ~100 angs::

    {
      "ang_range": [1, 100],
      "total_lines": 2345,
      "lines": [{...}, ...]
    }

Each line within a chunk includes inlined matches, features, tags,
and computed token_spans for concordance highlighting.

Reference: PLAN.md Section 8
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs.pipeline.manifest import file_sha256

_console = Console()


# ---------------------------------------------------------------------------
# Joined line record
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class JoinedLine:
    """A single line with all pipeline data joined by line_uid.

    Attributes:
        line_uid: Unique line identifier.
        ang: Ang number.
        gurmukhi: Gurmukhi text.
        tokens: Tokenized form.
        meta: Corpus record metadata.
        matches: Entity match records for this line.
        features: Feature data for this line.
        tags: Tag data for this line.
    """

    line_uid: str
    ang: int
    gurmukhi: str
    tokens: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    matches: list[dict[str, Any]] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_uid": self.line_uid,
            "ang": self.ang,
            "gurmukhi": self.gurmukhi,
            "tokens": self.tokens,
            "meta": self.meta,
            "matches": self.matches,
            "features": self.features,
            "tags": self.tags,
        }


def join_pipeline_data(
    records: list[dict[str, Any]],
    matches: list[dict[str, Any]] | None = None,
    features: list[dict[str, Any]] | None = None,
    tags: list[dict[str, Any]] | None = None,
) -> list[JoinedLine]:
    """Join all pipeline outputs by line_uid.

    Args:
        records: Corpus records from ggs_lines.jsonl.
        matches: Match records from matches.jsonl.
        features: Feature records from features.jsonl.
        tags: Tag records from tags.jsonl.

    Returns:
        List of :class:`JoinedLine` in corpus order.
    """
    # Index matches by line_uid
    matches_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if matches:
        for m in matches:
            uid = m.get("line_uid", "")
            matches_by_uid[uid].append(m)

    # Index features by line_uid
    features_by_uid: dict[str, dict[str, Any]] = {}
    if features:
        for f in features:
            features_by_uid[f.get("line_uid", "")] = f.get(
                "features", {},
            )

    # Index tags by line_uid
    tags_by_uid: dict[str, dict[str, Any]] = {}
    if tags:
        for t in tags:
            tags_by_uid[t.get("line_uid", "")] = t

    joined: list[JoinedLine] = []
    for rec in records:
        uid = rec.get("line_uid", "")
        joined.append(
            JoinedLine(
                line_uid=uid,
                ang=rec.get("ang", 0),
                gurmukhi=rec.get("gurmukhi", ""),
                tokens=rec.get("tokens", []),
                meta=rec.get("meta", {}),
                matches=matches_by_uid.get(uid, []),
                features=features_by_uid.get(uid, {}),
                tags=tags_by_uid.get(uid, {}),
            ),
        )

    return joined


# ---------------------------------------------------------------------------
# Corpus chunking
# ---------------------------------------------------------------------------


def compute_token_spans(
    gurmukhi: str,
    tokens: list[str],
) -> list[list[int]]:
    """Compute character-level [start, end) spans for each token.

    Finds each token's position in the Gurmukhi text by scanning left
    to right, ensuring spans are non-overlapping and ordered.

    Args:
        gurmukhi: Full Gurmukhi text of the line.
        tokens: Token list (whitespace-split).

    Returns:
        List of [start, end] pairs, one per token. If a token cannot
        be located, it gets [-1, -1].
    """
    spans: list[list[int]] = []
    search_start = 0

    for token in tokens:
        idx = gurmukhi.find(token, search_start)
        if idx >= 0:
            end = idx + len(token)
            spans.append([idx, end])
            search_start = end
        else:
            spans.append([-1, -1])

    return spans


def _ang_range_key(
    ang: int,
    chunk_size: int,
) -> tuple[str, int, int]:
    """Compute chunk key and ang range for an ang number.

    Returns:
        Tuple of (chunk_name, range_low, range_high).
    """
    if ang <= 0:
        return ("chunk_unknown", 0, 0)
    low = ((ang - 1) // chunk_size) * chunk_size + 1
    high = low + chunk_size - 1
    return (f"chunk_{low:03d}-{high:03d}", low, high)


def chunk_by_ang_range(
    lines: list[JoinedLine],
    chunk_size: int = 100,
) -> dict[str, list[dict[str, Any]]]:
    """Split joined lines into ang-range chunks.

    Args:
        lines: Joined line records.
        chunk_size: Number of angs per chunk (default 100).

    Returns:
        Mapping from chunk name (e.g. "chunk_001-100") to list of
        line dicts in that chunk.
    """
    chunks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in lines:
        key, _, _ = _ang_range_key(line.ang, chunk_size)
        chunks[key].append(line.to_dict())
    return dict(chunks)


def build_corpus_chunks(
    lines: list[JoinedLine],
    chunk_size: int = 100,
) -> dict[str, dict[str, Any]]:
    """Build structured corpus chunks with metadata and token spans.

    Each chunk is a self-contained JSON document::

        {
            "ang_range": [1, 100],
            "total_lines": 2345,
            "lines": [{...}, ...]
        }

    Each line dict includes computed ``token_spans`` for concordance
    highlighting in the webapp.

    Args:
        lines: Joined line records.
        chunk_size: Number of angs per chunk (default 100).

    Returns:
        Mapping from chunk name to structured chunk dict.
    """
    # Group lines by chunk
    raw_chunks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    chunk_ranges: dict[str, tuple[int, int]] = {}

    for line in lines:
        key, low, high = _ang_range_key(line.ang, chunk_size)

        # Add token_spans to the line dict
        line_dict = line.to_dict()
        line_dict["token_spans"] = compute_token_spans(
            line.gurmukhi, line.tokens,
        )
        raw_chunks[key].append(line_dict)

        if key not in chunk_ranges:
            chunk_ranges[key] = (low, high)

    # Build structured chunk dicts
    structured: dict[str, dict[str, Any]] = {}
    for key in sorted(raw_chunks.keys()):
        low, high = chunk_ranges.get(key, (0, 0))
        structured[key] = {
            "ang_range": [low, high],
            "total_lines": len(raw_chunks[key]),
            "lines": raw_chunks[key],
        }

    return structured


def write_chunks(
    chunks: dict[str, list[dict[str, Any]]],
    output_dir: Path,
) -> list[Path]:
    """Write corpus chunks to the output directory.

    Accepts either flat line lists or structured chunk dicts.

    Args:
        chunks: Mapping from chunk name to line dicts or chunk dicts.
        output_dir: Directory to write chunk files into.

    Returns:
        List of paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in sorted(chunks.keys()):
        path = output_dir / f"{name}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(chunks[name], fh, ensure_ascii=False)
        paths.append(path)
    return paths


def write_structured_chunks(
    chunks: dict[str, dict[str, Any]],
    output_dir: Path,
) -> list[Path]:
    """Write structured corpus chunks to the output directory.

    Args:
        chunks: Mapping from chunk name to structured chunk dicts.
        output_dir: Directory to write chunk files into.

    Returns:
        List of paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in sorted(chunks.keys()):
        path = output_dir / f"{name}.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(chunks[name], fh, ensure_ascii=False)
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------


def compute_aggregates(
    lines: list[JoinedLine],
) -> dict[str, Any]:
    """Compute summary statistics for the webapp dashboard.

    Produces:
      - Total corpus stats (lines, tokens, unique entities)
      - Top entities by frequency
      - Entity distribution by author
      - Nirgun/sagun distribution summary
      - Ang range

    Args:
        lines: Joined line records.

    Returns:
        Aggregates dict ready for JSON serialization.
    """
    total_lines = len(lines)
    total_tokens = sum(len(line.tokens) for line in lines)

    # Entity frequency
    entity_freq: dict[str, int] = defaultdict(int)
    for line in lines:
        for m in line.matches:
            eid = m.get("entity_id", "")
            if eid:
                entity_freq[eid] += 1

    unique_entities = len(entity_freq)
    top_entities = sorted(
        entity_freq.items(), key=lambda x: x[1], reverse=True,
    )[:50]

    # Entity by author
    entity_by_author: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int),
    )
    for line in lines:
        author = line.meta.get("author", "unknown")
        for m in line.matches:
            eid = m.get("entity_id", "")
            if eid:
                entity_by_author[author][eid] += 1

    # Tag distribution
    tag_counts: dict[str, int] = defaultdict(int)
    for line in lines:
        primary = line.tags.get("primary_tag")
        label = primary if primary else "unclassified"
        tag_counts[label] += 1

    # Unique shabads
    shabad_uids: set[str] = set()
    for line in lines:
        uid = line.meta.get("shabad_uid")
        if uid:
            shabad_uids.add(uid)

    # Ang range
    angs = [line.ang for line in lines if line.ang > 0]
    ang_min = min(angs) if angs else 0
    ang_max = max(angs) if angs else 0

    return {
        "corpus": {
            "total_lines": total_lines,
            "total_tokens": total_tokens,
            "unique_entities": unique_entities,
            "unique_shabads": len(shabad_uids),
            "ang_range": {"min": ang_min, "max": ang_max},
        },
        "top_entities": [
            {"entity_id": eid, "count": count}
            for eid, count in top_entities
        ],
        "entity_by_author": {
            author: dict(entities)
            for author, entities in sorted(entity_by_author.items())
        },
        "tag_distribution": dict(sorted(tag_counts.items())),
    }


# ---------------------------------------------------------------------------
# Manifest (integrity hashes)
# ---------------------------------------------------------------------------


def compute_bundle_manifest(
    bundle_dir: Path,
) -> dict[str, str]:
    """Compute SHA-256 hashes for all files in the bundle.

    Args:
        bundle_dir: Path to the web_bundle directory.

    Returns:
        Mapping from relative path to SHA-256 hash string.
    """
    hashes: dict[str, str] = {}
    for path in sorted(bundle_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            rel = str(path.relative_to(bundle_dir))
            hashes[rel] = file_sha256(path)
    return hashes


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ValidationResult:
    """Result of bundle validation.

    Attributes:
        valid: Whether the bundle passed all checks.
        errors: List of validation error messages.
        warnings: List of validation warning messages.
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_bundle(bundle_dir: Path) -> ValidationResult:
    """Validate bundle integrity.

    Checks:
      - All chunk files parse as valid JSON
      - aggregates.json exists and parses
      - manifest.json exists and hashes match

    Args:
        bundle_dir: Path to the web_bundle directory.

    Returns:
        A :class:`ValidationResult`.
    """
    result = ValidationResult()

    # Check corpus directory
    corpus_dir = bundle_dir / "corpus"
    if not corpus_dir.exists():
        result.errors.append("corpus/ directory missing")
        result.valid = False
    else:
        for chunk_path in sorted(corpus_dir.glob("*.json")):
            try:
                with chunk_path.open(encoding="utf-8") as fh:
                    json.load(fh)
            except (json.JSONDecodeError, OSError) as e:
                result.errors.append(
                    f"Invalid chunk file {chunk_path.name}: {e}",
                )
                result.valid = False

    # Check aggregates.json
    agg_path = bundle_dir / "aggregates.json"
    if not agg_path.exists():
        result.errors.append("aggregates.json missing")
        result.valid = False
    else:
        try:
            with agg_path.open(encoding="utf-8") as fh:
                json.load(fh)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid aggregates.json: {e}")
            result.valid = False

    # Check manifest.json and verify hashes
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        result.warnings.append("manifest.json missing (no integrity check)")
    else:
        try:
            with manifest_path.open(encoding="utf-8") as fh:
                manifest = json.load(fh)
            file_hashes = manifest.get("file_hashes", {})
            for rel_path, expected_hash in file_hashes.items():
                full_path = bundle_dir / rel_path
                if not full_path.exists():
                    result.errors.append(
                        f"Manifest references missing file: {rel_path}",
                    )
                    result.valid = False
                else:
                    actual = file_sha256(full_path)
                    if actual != expected_hash:
                        result.errors.append(
                            f"Hash mismatch for {rel_path}: "
                            f"expected {expected_hash}, got {actual}",
                        )
                        result.valid = False
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid manifest.json: {e}")
            result.valid = False

    return result


# ---------------------------------------------------------------------------
# Bundle builder
# ---------------------------------------------------------------------------


def build_bundle(
    records: list[dict[str, Any]],
    *,
    matches: list[dict[str, Any]] | None = None,
    features: list[dict[str, Any]] | None = None,
    tags: list[dict[str, Any]] | None = None,
    output_dir: Path | None = None,
    chunk_size: int = 100,
) -> dict[str, Any]:
    """Build the complete web bundle.

    Steps:
      1. Join all pipeline data by line_uid
      2. Chunk corpus by ang range
      3. Compute aggregates
      4. Write all files
      5. Compute manifest hashes
      6. Validate bundle

    Args:
        records: Corpus records from ggs_lines.jsonl.
        matches: Match records (optional).
        features: Feature records (optional).
        tags: Tag records (optional).
        output_dir: Bundle output directory.
        chunk_size: Number of angs per corpus chunk.

    Returns:
        Bundle summary dict with stats and validation result.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Building web bundle "
        f"from {len(records)} records...[/bold]\n",
    )

    # Step 1: Join
    lines = join_pipeline_data(records, matches, features, tags)
    _console.print(f"  Joined {len(lines)} lines")

    # Step 2: Chunk
    chunks = chunk_by_ang_range(lines, chunk_size)
    _console.print(f"  Created {len(chunks)} corpus chunks")

    # Step 3: Aggregates
    aggregates = compute_aggregates(lines)
    _console.print(
        f"  Aggregates: {aggregates['corpus']['total_lines']} lines, "
        f"{aggregates['corpus']['unique_entities']} entities",
    )

    # Step 4: Write
    summary: dict[str, Any] = {
        "total_lines": len(lines),
        "total_chunks": len(chunks),
        "aggregates": aggregates["corpus"],
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write corpus chunks
        corpus_dir = output_dir / "corpus"
        chunk_paths = write_chunks(chunks, corpus_dir)
        _console.print(
            f"  Written {len(chunk_paths)} chunk files to {corpus_dir}",
        )

        # Write aggregates
        agg_path = output_dir / "aggregates.json"
        with agg_path.open("w", encoding="utf-8") as fh:
            json.dump(aggregates, fh, ensure_ascii=False, indent=2)
        _console.print(f"  Written {agg_path}")

        # Step 5: Manifest
        file_hashes = compute_bundle_manifest(output_dir)
        manifest = {
            "bundle_version": "1.0.0",
            "total_files": len(file_hashes),
            "file_hashes": file_hashes,
        }
        manifest_path = output_dir / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)
        _console.print(f"  Written {manifest_path}")

        summary["file_hashes"] = file_hashes

        # Step 6: Validate
        validation = validate_bundle(output_dir)
        summary["validation"] = validation.to_dict()
        if validation.valid:
            _console.print("  Bundle validation: PASSED")
        else:
            _console.print(
                f"  Bundle validation: FAILED "
                f"({len(validation.errors)} errors)",
            )

    elapsed = time.monotonic() - t0
    summary["elapsed_seconds"] = round(elapsed, 3)
    _console.print(f"  Completed in {elapsed:.2f}s")

    return summary
