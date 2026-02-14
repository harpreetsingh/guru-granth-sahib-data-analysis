"""Bundle manifest and lineage generation (bd-9i3.4).

Produces ``manifest.json`` and ``lineage.json`` for the web bundle.
These files provide the provenance and transparency layer that makes
the webapp data trustworthy and auditable.

manifest.json: records exactly what produced the bundle data —
    versions, stats, hashes, timestamps.

lineage.json: maps each aggregate/chart in the webapp to the exact
    pipeline step, config parameters, and lexicon files that produced it.

Reference: PLAN.md Section 8
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from ggs import __version__
from ggs.pipeline.manifest import file_sha256

_console = Console()


# ---------------------------------------------------------------------------
# Bundle manifest
# ---------------------------------------------------------------------------


def build_bundle_manifest(
    *,
    corpus_stats: dict[str, Any] | None = None,
    lexicon_stats: dict[str, Any] | None = None,
    pipeline_config: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Build the bundle manifest.json content.

    The manifest tells users exactly what version of everything
    produced the data they're looking at.

    Args:
        corpus_stats: Corpus statistics (lines, tokens, shabads, etc.).
        lexicon_stats: Lexicon statistics (entities, aliases, hashes).
        pipeline_config: Key config parameters used in this run.
        artifacts: List of artifact file descriptors.
        git_commit: Git commit hash (short form).

    Returns:
        Manifest dict ready for JSON serialization.
    """
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "generator_version": __version__,
    }

    if git_commit is not None:
        manifest["git_commit"] = git_commit

    if corpus_stats is not None:
        manifest["corpus_stats"] = corpus_stats

    if lexicon_stats is not None:
        manifest["lexicon_stats"] = lexicon_stats

    if pipeline_config is not None:
        manifest["pipeline_config"] = pipeline_config

    if artifacts is not None:
        manifest["artifacts"] = artifacts

    return manifest


def compute_artifact_descriptors(
    bundle_dir: Path,
) -> list[dict[str, Any]]:
    """Compute artifact descriptors for all files in the bundle.

    Each descriptor includes file path, size, and SHA-256 hash.

    Args:
        bundle_dir: Path to the web_bundle directory.

    Returns:
        List of artifact descriptor dicts.
    """
    descriptors: list[dict[str, Any]] = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in ("manifest.json", "lineage.json"):
            continue
        rel = str(path.relative_to(bundle_dir))
        size_bytes = path.stat().st_size
        sha256 = file_sha256(path)
        descriptors.append({
            "file": rel,
            "size_bytes": size_bytes,
            "sha256": sha256,
        })
    return descriptors


def compute_corpus_stats(
    records: list[dict[str, Any]],
    matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute corpus statistics for the manifest.

    Args:
        records: Corpus record dicts.
        matches: Match record dicts (optional).

    Returns:
        Corpus stats dict.
    """
    total_lines = len(records)

    total_tokens = sum(
        len(rec.get("tokens", [])) for rec in records
    )

    angs: set[int] = set()
    shabads: set[str] = set()
    for rec in records:
        ang = rec.get("ang")
        if ang is not None:
            angs.add(ang)
        uid = rec.get("meta", {}).get("shabad_uid")
        if uid:
            shabads.add(uid)

    stats: dict[str, Any] = {
        "total_angs": len(angs),
        "total_lines": total_lines,
        "total_tokens": total_tokens,
        "total_shabads": len(shabads),
    }

    if matches is not None:
        entity_ids: set[str] = set()
        for m in matches:
            eid = m.get("entity_id", "")
            if eid:
                entity_ids.add(eid)
        stats["total_matches"] = len(matches)
        stats["unique_entities_matched"] = len(entity_ids)

    return stats


def compute_lexicon_stats(
    lexicon_paths: dict[str, Path],
) -> dict[str, Any]:
    """Compute lexicon statistics for the manifest.

    Args:
        lexicon_paths: Mapping from lexicon name to file path.

    Returns:
        Lexicon stats dict with file count and hashes.
    """
    hashes: dict[str, str] = {}
    for name, path in sorted(lexicon_paths.items()):
        if path.exists():
            hashes[name] = file_sha256(path)

    return {
        "total_lexicon_files": len(hashes),
        "lexicon_hashes": hashes,
    }


def write_bundle_manifest(
    manifest: dict[str, Any],
    output_path: Path,
) -> None:
    """Write manifest.json to disk.

    Args:
        manifest: Manifest dict.
        output_path: Path to write manifest.json.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------


def build_lineage_entry(
    *,
    produced_by: str,
    inputs: list[str],
    config_params: dict[str, Any] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Build a single lineage entry.

    Args:
        produced_by: Pipeline step that produced this data.
        inputs: List of input file/resource names.
        config_params: Key config parameters used.
        description: Human-readable description.

    Returns:
        Lineage entry dict.
    """
    entry: dict[str, Any] = {
        "produced_by": produced_by,
        "inputs": inputs,
    }
    if config_params:
        entry["config_params"] = config_params
    if description:
        entry["description"] = description
    return entry


def build_default_lineage(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the default lineage.json with standard pipeline entries.

    Maps each aggregate/chart type to the pipeline step that produces it.

    Args:
        config: Full config.yaml dict (for extracting relevant params).

    Returns:
        Lineage dict ready for JSON serialization.
    """
    cfg = config or {}
    norm_cfg = cfg.get("normalization", {})
    cooc_cfg = cfg.get("cooccurrence", {})
    tag_cfg = cfg.get("tagging", {})

    lineage: dict[str, Any] = {
        "entity_matches": build_lineage_entry(
            produced_by="Phase 1: Lexical Analysis",
            inputs=["ggs_lines.jsonl", "lexicon/entities.yaml"],
            config_params={
                "normalization.nukta_policy": norm_cfg.get(
                    "nukta_policy", "PRESERVE",
                ),
                "normalization.nasal_policy": norm_cfg.get(
                    "nasal_policy", "CANONICAL_TIPPI",
                ),
            },
            description=(
                "Entity matches found by Aho-Corasick multi-pattern "
                "matching against the normalized corpus."
            ),
        ),
        "entity_counts_by_author": build_lineage_entry(
            produced_by="Phase 1: Lexical Analysis",
            inputs=["ggs_lines.jsonl", "lexicon/entities.yaml"],
            config_params={
                "normalization.nukta_policy": norm_cfg.get(
                    "nukta_policy", "PRESERVE",
                ),
            },
            description=(
                "Count of entity matches per author, normalized "
                "per 1,000 lines."
            ),
        ),
        "cooccurrence": build_lineage_entry(
            produced_by="Phase 2: Structural Analysis",
            inputs=[
                "ggs_lines.jsonl",
                "matches.jsonl",
            ],
            config_params={
                "cooccurrence.min_entity_freq": cooc_cfg.get(
                    "min_entity_freq", 10,
                ),
                "cooccurrence.smoothing_k": cooc_cfg.get(
                    "smoothing_k", 1,
                ),
                "cooccurrence.min_pmi_support": cooc_cfg.get(
                    "min_pmi_support", 5,
                ),
            },
            description=(
                "Entity co-occurrence pairs with PMI/NPMI scores, "
                "computed using Laplace-smoothed PMI."
            ),
        ),
        "register_density": build_lineage_entry(
            produced_by="Phase 2: Structural Analysis",
            inputs=[
                "ggs_lines.jsonl",
                "matches.jsonl",
                "lexicon/perso_arabic.yaml",
                "lexicon/sanskritic.yaml",
            ],
            config_params={
                "register_density.window_size": cfg.get(
                    "register_density", {},
                ).get("window_size", 20),
            },
            description=(
                "Per-line and windowed register density for "
                "Perso-Arabic and Sanskritic registers."
            ),
        ),
        "tag_scores": build_lineage_entry(
            produced_by="Phase 3: Interpretive Tagging",
            inputs=[
                "ggs_lines.jsonl",
                "matches.jsonl",
                "features.jsonl",
            ],
            config_params={
                "tagging.context_weight": tag_cfg.get(
                    "context_weight", 0.2,
                ),
            },
            description=(
                "Per-line dimension scores (nirgun, sagun_narrative, "
                "critique_ritual, etc.) from rule-based sigmoid scoring."
            ),
        ),
        "tag_categories": build_lineage_entry(
            produced_by="Phase 3: Interpretive Tagging",
            inputs=["tags.jsonl"],
            config_params={
                k: v
                for section in tag_cfg.get("thresholds", {}).values()
                if isinstance(section, dict)
                for k, v in section.items()
            },
            description=(
                "Primary and secondary category labels derived from "
                "continuous scores using configurable thresholds."
            ),
        ),
        "nirgun_sagun_distribution": build_lineage_entry(
            produced_by="Phase 3: Interpretive Tagging",
            inputs=["tags.jsonl"],
            description=(
                "Distribution of nirgun/sagun/mixed categories across "
                "the corpus, broken down by author, raga, and ang bucket."
            ),
        ),
        "search_index": build_lineage_entry(
            produced_by="Bundle: Search Index Builder",
            inputs=[
                "ggs_lines.jsonl",
                "matches.jsonl",
            ],
            description=(
                "Pre-built inverted index for client-side Gurmukhi "
                "text search with token and entity lookups."
            ),
        ),
    }

    return lineage


def write_lineage(
    lineage: dict[str, Any],
    output_path: Path,
) -> None:
    """Write lineage.json to disk.

    Args:
        lineage: Lineage dict.
        output_path: Path to write lineage.json.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(lineage, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Combined generation
# ---------------------------------------------------------------------------


def generate_bundle_metadata(
    *,
    records: list[dict[str, Any]] | None = None,
    matches: list[dict[str, Any]] | None = None,
    lexicon_paths: dict[str, Path] | None = None,
    config: dict[str, Any] | None = None,
    bundle_dir: Path | None = None,
    git_commit: str | None = None,
    output_dir: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate both manifest.json and lineage.json.

    Args:
        records: Corpus records (for corpus stats).
        matches: Match records (for match stats).
        lexicon_paths: Lexicon file paths (for hashes).
        config: Full config dict (for lineage params).
        bundle_dir: Bundle directory (for artifact descriptors).
        git_commit: Git commit hash.
        output_dir: Directory to write files (if provided).

    Returns:
        Tuple of (manifest_dict, lineage_dict).
    """
    _console.print(
        "\n[bold]Generating bundle metadata...[/bold]\n",
    )

    # Build corpus stats
    corpus_stats = None
    if records is not None:
        corpus_stats = compute_corpus_stats(records, matches)
        _console.print(
            f"  Corpus: {corpus_stats['total_lines']} lines, "
            f"{corpus_stats['total_angs']} angs",
        )

    # Build lexicon stats
    lexicon_stats = None
    if lexicon_paths:
        lexicon_stats = compute_lexicon_stats(lexicon_paths)
        _console.print(
            f"  Lexicon: {lexicon_stats['total_lexicon_files']} files",
        )

    # Build artifact descriptors
    artifacts = None
    if bundle_dir is not None and bundle_dir.exists():
        artifacts = compute_artifact_descriptors(bundle_dir)
        _console.print(f"  Artifacts: {len(artifacts)} files")

    # Build manifest
    manifest = build_bundle_manifest(
        corpus_stats=corpus_stats,
        lexicon_stats=lexicon_stats,
        pipeline_config=config,
        artifacts=artifacts,
        git_commit=git_commit,
    )

    # Build lineage
    lineage = build_default_lineage(config)

    # Write files
    if output_dir is not None:
        write_bundle_manifest(
            manifest, output_dir / "manifest.json",
        )
        _console.print(
            f"  Written {output_dir / 'manifest.json'}",
        )

        write_lineage(lineage, output_dir / "lineage.json")
        _console.print(
            f"  Written {output_dir / 'lineage.json'}",
        )

    return manifest, lineage
