"""Bundle manifest and lineage tests (bd-9i3.4).

Tests manifest building, artifact descriptors, corpus/lexicon stats,
lineage entry construction, default lineage, and combined generation.
"""

from __future__ import annotations

import json
from pathlib import Path

from ggs.output.bundle_manifest import (
    build_bundle_manifest,
    build_default_lineage,
    build_lineage_entry,
    compute_artifact_descriptors,
    compute_corpus_stats,
    compute_lexicon_stats,
    generate_bundle_metadata,
    write_bundle_manifest,
    write_lineage,
)

# ---------------------------------------------------------------------------
# build_bundle_manifest tests
# ---------------------------------------------------------------------------


class TestBuildBundleManifest:
    """Tests for build_bundle_manifest."""

    def test_minimal_manifest(self) -> None:
        manifest = build_bundle_manifest()
        assert manifest["schema_version"] == "1.0.0"
        assert "generated_at" in manifest
        assert "generator_version" in manifest

    def test_with_corpus_stats(self) -> None:
        stats = {"total_lines": 100, "total_tokens": 500}
        manifest = build_bundle_manifest(corpus_stats=stats)
        assert manifest["corpus_stats"]["total_lines"] == 100

    def test_with_lexicon_stats(self) -> None:
        stats = {
            "total_lexicon_files": 3,
            "lexicon_hashes": {"entities": "sha256:abc"},
        }
        manifest = build_bundle_manifest(lexicon_stats=stats)
        assert manifest["lexicon_stats"]["total_lexicon_files"] == 3

    def test_with_git_commit(self) -> None:
        manifest = build_bundle_manifest(git_commit="abc123")
        assert manifest["git_commit"] == "abc123"

    def test_without_git_commit(self) -> None:
        manifest = build_bundle_manifest()
        assert "git_commit" not in manifest

    def test_with_artifacts(self) -> None:
        artifacts = [
            {"file": "agg.json", "sha256": "sha256:xyz"},
        ]
        manifest = build_bundle_manifest(artifacts=artifacts)
        assert len(manifest["artifacts"]) == 1

    def test_with_pipeline_config(self) -> None:
        config = {"tagging": {"context_weight": 0.2}}
        manifest = build_bundle_manifest(pipeline_config=config)
        assert manifest["pipeline_config"]["tagging"]["context_weight"] == 0.2


# ---------------------------------------------------------------------------
# Artifact descriptor tests
# ---------------------------------------------------------------------------


class TestComputeArtifactDescriptors:
    """Tests for compute_artifact_descriptors."""

    def test_basic_descriptors(self, tmp_path: Path) -> None:
        f1 = tmp_path / "aggregates.json"
        f1.write_text('{"key": "value"}', encoding="utf-8")
        sub = tmp_path / "corpus"
        sub.mkdir()
        f2 = sub / "chunk.json"
        f2.write_text("[]", encoding="utf-8")

        descs = compute_artifact_descriptors(tmp_path)
        assert len(descs) == 2

        files = {d["file"] for d in descs}
        assert "aggregates.json" in files
        assert "corpus/chunk.json" in files

        for d in descs:
            assert "sha256" in d
            assert d["sha256"].startswith("sha256:")
            assert "size_bytes" in d
            assert d["size_bytes"] > 0

    def test_excludes_manifest_and_lineage(self, tmp_path: Path) -> None:
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
        (tmp_path / "lineage.json").write_text("{}", encoding="utf-8")

        descs = compute_artifact_descriptors(tmp_path)
        files = {d["file"] for d in descs}
        assert "data.json" in files
        assert "manifest.json" not in files
        assert "lineage.json" not in files

    def test_empty_directory(self, tmp_path: Path) -> None:
        descs = compute_artifact_descriptors(tmp_path)
        assert descs == []


# ---------------------------------------------------------------------------
# Corpus stats tests
# ---------------------------------------------------------------------------


class TestComputeCorpusStats:
    """Tests for compute_corpus_stats."""

    def test_basic_stats(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "tokens": ["a", "b"],
                "meta": {"shabad_uid": "shabad:1"},
            },
            {
                "line_uid": "line:2",
                "ang": 1,
                "tokens": ["c"],
                "meta": {"shabad_uid": "shabad:1"},
            },
            {
                "line_uid": "line:3",
                "ang": 2,
                "tokens": ["d", "e", "f"],
                "meta": {"shabad_uid": "shabad:2"},
            },
        ]
        stats = compute_corpus_stats(records)
        assert stats["total_lines"] == 3
        assert stats["total_tokens"] == 6
        assert stats["total_angs"] == 2
        assert stats["total_shabads"] == 2

    def test_with_matches(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 1, "tokens": []},
        ]
        matches = [
            {"line_uid": "line:1", "entity_id": "WAHEGURU"},
            {"line_uid": "line:1", "entity_id": "WAHEGURU"},
            {"line_uid": "line:1", "entity_id": "RAM"},
        ]
        stats = compute_corpus_stats(records, matches)
        assert stats["total_matches"] == 3
        assert stats["unique_entities_matched"] == 2

    def test_empty_records(self) -> None:
        stats = compute_corpus_stats([])
        assert stats["total_lines"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_angs"] == 0

    def test_no_matches(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 1, "tokens": ["a"]},
        ]
        stats = compute_corpus_stats(records)
        assert "total_matches" not in stats


# ---------------------------------------------------------------------------
# Lexicon stats tests
# ---------------------------------------------------------------------------


class TestComputeLexiconStats:
    """Tests for compute_lexicon_stats."""

    def test_basic_stats(self, tmp_path: Path) -> None:
        f1 = tmp_path / "entities.yaml"
        f2 = tmp_path / "nirgun.yaml"
        f1.write_text("entities: []", encoding="utf-8")
        f2.write_text("nirgun: []", encoding="utf-8")

        stats = compute_lexicon_stats({
            "entities": f1,
            "nirgun": f2,
        })
        assert stats["total_lexicon_files"] == 2
        assert "entities" in stats["lexicon_hashes"]
        assert "nirgun" in stats["lexicon_hashes"]

    def test_missing_file(self, tmp_path: Path) -> None:
        stats = compute_lexicon_stats({
            "missing": tmp_path / "nonexistent.yaml",
        })
        assert stats["total_lexicon_files"] == 0

    def test_empty_paths(self) -> None:
        stats = compute_lexicon_stats({})
        assert stats["total_lexicon_files"] == 0


# ---------------------------------------------------------------------------
# Write manifest tests
# ---------------------------------------------------------------------------


class TestWriteBundleManifest:
    """Tests for write_bundle_manifest."""

    def test_writes_file(self, tmp_path: Path) -> None:
        manifest = {"schema_version": "1.0.0", "test": True}
        path = tmp_path / "manifest.json"
        write_bundle_manifest(manifest, path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["schema_version"] == "1.0.0"
        assert data["test"] is True

    def test_creates_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "manifest.json"
        write_bundle_manifest({"test": True}, path)
        assert path.exists()


# ---------------------------------------------------------------------------
# Lineage entry tests
# ---------------------------------------------------------------------------


class TestBuildLineageEntry:
    """Tests for build_lineage_entry."""

    def test_basic_entry(self) -> None:
        entry = build_lineage_entry(
            produced_by="Phase 1: Lexical Analysis",
            inputs=["ggs_lines.jsonl", "lexicon/entities.yaml"],
            description="Entity matching step.",
        )
        assert entry["produced_by"] == "Phase 1: Lexical Analysis"
        assert len(entry["inputs"]) == 2
        assert entry["description"] == "Entity matching step."

    def test_with_config_params(self) -> None:
        entry = build_lineage_entry(
            produced_by="Phase 2",
            inputs=["matches.jsonl"],
            config_params={"min_entity_freq": 10},
        )
        assert entry["config_params"]["min_entity_freq"] == 10

    def test_without_optional_fields(self) -> None:
        entry = build_lineage_entry(
            produced_by="Phase 1",
            inputs=[],
        )
        assert "config_params" not in entry
        assert "description" not in entry


# ---------------------------------------------------------------------------
# Default lineage tests
# ---------------------------------------------------------------------------


class TestBuildDefaultLineage:
    """Tests for build_default_lineage."""

    def test_has_expected_entries(self) -> None:
        lineage = build_default_lineage()
        expected_keys = [
            "entity_matches",
            "entity_counts_by_author",
            "cooccurrence",
            "register_density",
            "tag_scores",
            "tag_categories",
            "nirgun_sagun_distribution",
            "search_index",
        ]
        for key in expected_keys:
            assert key in lineage, f"Missing lineage entry: {key}"

    def test_each_entry_has_required_fields(self) -> None:
        lineage = build_default_lineage()
        for key, entry in lineage.items():
            assert "produced_by" in entry, (
                f"{key} missing produced_by"
            )
            assert "inputs" in entry, (
                f"{key} missing inputs"
            )

    def test_uses_config_params(self) -> None:
        config = {
            "normalization": {"nukta_policy": "STRIP"},
            "cooccurrence": {"min_entity_freq": 20},
            "tagging": {"context_weight": 0.3},
        }
        lineage = build_default_lineage(config)

        # Normalization config should flow into entity_matches
        assert lineage["entity_matches"]["config_params"][
            "normalization.nukta_policy"
        ] == "STRIP"

        # Cooccurrence config
        assert lineage["cooccurrence"]["config_params"][
            "cooccurrence.min_entity_freq"
        ] == 20

        # Tagging config
        assert lineage["tag_scores"]["config_params"][
            "tagging.context_weight"
        ] == 0.3

    def test_defaults_without_config(self) -> None:
        lineage = build_default_lineage()
        # Should use defaults
        assert lineage["entity_matches"]["config_params"][
            "normalization.nukta_policy"
        ] == "PRESERVE"


# ---------------------------------------------------------------------------
# Write lineage tests
# ---------------------------------------------------------------------------


class TestWriteLineage:
    """Tests for write_lineage."""

    def test_writes_file(self, tmp_path: Path) -> None:
        lineage = {"entity_matches": {"produced_by": "Phase 1"}}
        path = tmp_path / "lineage.json"
        write_lineage(lineage, path)

        assert path.exists()
        data = json.loads(path.read_text())
        assert "entity_matches" in data

    def test_creates_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "lineage.json"
        write_lineage({}, path)
        assert path.exists()


# ---------------------------------------------------------------------------
# Combined generation tests
# ---------------------------------------------------------------------------


class TestGenerateBundleMetadata:
    """Tests for generate_bundle_metadata."""

    def test_basic_generation(self) -> None:
        records = [
            {"line_uid": "line:1", "ang": 1, "tokens": ["a"]},
        ]
        manifest, lineage = generate_bundle_metadata(
            records=records,
        )
        assert "corpus_stats" in manifest
        assert manifest["corpus_stats"]["total_lines"] == 1
        assert "entity_matches" in lineage

    def test_writes_files(self, tmp_path: Path) -> None:
        records = [
            {"line_uid": "line:1", "ang": 1, "tokens": ["a"]},
        ]
        output_dir = tmp_path / "bundle"
        _manifest, _lineage = generate_bundle_metadata(
            records=records,
            output_dir=output_dir,
        )

        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "lineage.json").exists()

        # Verify JSON is valid
        data = json.loads(
            (output_dir / "manifest.json").read_text(),
        )
        assert data["corpus_stats"]["total_lines"] == 1

    def test_with_all_inputs(self, tmp_path: Path) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "tokens": ["a"],
                "meta": {"shabad_uid": "s:1"},
            },
        ]
        matches = [
            {"line_uid": "line:1", "entity_id": "WAHEGURU"},
        ]
        lex = tmp_path / "entities.yaml"
        lex.write_text("entities: []", encoding="utf-8")

        # Create a fake bundle dir
        bundle_dir = tmp_path / "web_bundle"
        bundle_dir.mkdir()
        (bundle_dir / "data.json").write_text("{}", encoding="utf-8")

        config = {"tagging": {"context_weight": 0.2}}

        output_dir = tmp_path / "output"
        manifest, lineage = generate_bundle_metadata(
            records=records,
            matches=matches,
            lexicon_paths={"entities": lex},
            config=config,
            bundle_dir=bundle_dir,
            git_commit="abc123",
            output_dir=output_dir,
        )

        assert manifest["git_commit"] == "abc123"
        assert manifest["corpus_stats"]["total_matches"] == 1
        assert manifest["lexicon_stats"]["total_lexicon_files"] == 1
        assert len(manifest["artifacts"]) == 1
        assert "tag_scores" in lineage

    def test_empty_inputs(self) -> None:
        manifest, lineage = generate_bundle_metadata()
        assert "corpus_stats" not in manifest
        assert "entity_matches" in lineage
