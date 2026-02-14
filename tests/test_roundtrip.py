"""Roundtrip and determinism tests (bd-3jj.9).

Roundtrip tests verify the most important quality property: running the full
pipeline twice on the same inputs produces byte-identical outputs.  Also
validates schemas on all output artifacts and cross-artifact consistency.

Reference: PLAN.md Section 10
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from ggs.analysis.features import FEATURE_DIMENSIONS, compute_corpus_features
from ggs.analysis.match import run_matching
from ggs.analysis.tagger import run_tagger
from ggs.corpus.pipeline import _process_ang_html, run_phase0
from ggs.lexicon.loader import LexiconIndex, load_lexicon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture_corpus(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load Ang 1-5 through the Phase 0 pipeline and return records."""
    all_records: list[dict[str, Any]] = []
    for ang in range(1, 6):
        html_path = fixtures_dir / "html" / f"ang_{ang:03d}.html"
        html = html_path.read_text(encoding="utf-8")
        records = _process_ang_html(html, ang=ang)
        all_records.extend(records)
    return all_records


def _load_test_lexicon() -> LexiconIndex:
    """Load the test lexicon from fixtures."""
    paths = {"test": "tests/fixtures/lexicon/test_entities.yaml"}
    return load_lexicon(paths, base_dir=Path("."))


def _load_tagging_config() -> dict[str, Any]:
    """Load the tagging section from config.yaml."""
    config_path = Path("config/config.yaml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return config["tagging"]


def _run_full_pipeline(
    fixtures_dir: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Run the full pipeline (Phase 0-3) and return output file paths.

    Returns a dict mapping artifact name to path.
    """
    # Phase 0: corpus extraction
    html_dir = fixtures_dir / "html"
    corpus_dir = output_dir / "corpus"
    run_phase0(input_dir=html_dir, output_dir=corpus_dir)

    # Load corpus records from JSONL
    jsonl_path = corpus_dir / "ggs_lines.jsonl"
    records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    ]

    # Load lexicon
    index = _load_test_lexicon()

    # Phase 1: matching
    matches_path = output_dir / "matches.jsonl"
    matches = run_matching(records, index, output_path=matches_path)

    # Phase 2: features
    features_path = output_dir / "features.jsonl"
    features = compute_corpus_features(
        records, matches, index, output_path=features_path,
    )

    # Phase 3: tagging
    tagging_config = _load_tagging_config()
    tags_dir = output_dir / "tags"
    run_tagger(
        records, matches, features, tagging_config, output_dir=tags_dir,
    )

    return {
        "ggs_lines.jsonl": jsonl_path,
        "run_manifest.json": corpus_dir / "run_manifest.json",
        "validation_report.json": corpus_dir / "validation_report.json",
        "matches.jsonl": matches_path,
        "features.jsonl": features_path,
        "tags.jsonl": tags_dir / "tags.jsonl",
        "distribution.csv": tags_dir / "nirgun_sagun_distribution.csv",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Test 1: Full pipeline determinism
# ---------------------------------------------------------------------------


class TestPipelineDeterminism:
    """Running the full pipeline twice produces byte-identical outputs.

    This catches: non-deterministic iteration order, timestamp leaks,
    random seeds, dict ordering issues.
    """

    def test_phase0_determinism(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Phase 0 produces identical JSONL on two runs."""
        html_dir = fixtures_dir / "html"

        # Run 1
        out1 = tmp_path / "run1"
        run_phase0(input_dir=html_dir, output_dir=out1)

        # Run 2
        out2 = tmp_path / "run2"
        run_phase0(input_dir=html_dir, output_dir=out2)

        # Compare ggs_lines.jsonl byte-for-byte
        content1 = (out1 / "ggs_lines.jsonl").read_bytes()
        content2 = (out2 / "ggs_lines.jsonl").read_bytes()
        assert content1 == content2, (
            "Phase 0 ggs_lines.jsonl differs between two identical runs"
        )

    def test_phase0_validation_report_determinism(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Phase 0 validation_report.json is deterministic."""
        html_dir = fixtures_dir / "html"

        out1 = tmp_path / "run1"
        run_phase0(input_dir=html_dir, output_dir=out1)

        out2 = tmp_path / "run2"
        run_phase0(input_dir=html_dir, output_dir=out2)

        content1 = (out1 / "validation_report.json").read_bytes()
        content2 = (out2 / "validation_report.json").read_bytes()
        assert content1 == content2, (
            "Phase 0 validation_report.json differs between runs"
        )

    def test_matching_determinism(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Phase 1 matching produces identical output on two runs."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()

        # Run 1
        path1 = tmp_path / "matches1.jsonl"
        run_matching(records, index, output_path=path1)

        # Run 2
        path2 = tmp_path / "matches2.jsonl"
        run_matching(records, index, output_path=path2)

        content1 = path1.read_bytes()
        content2 = path2.read_bytes()
        assert content1 == content2, (
            "matches.jsonl differs between two identical runs"
        )

    def test_features_determinism(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Phase 2 features produces identical output on two runs."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)

        # Run 1
        path1 = tmp_path / "features1.jsonl"
        compute_corpus_features(records, matches, index, output_path=path1)

        # Run 2
        path2 = tmp_path / "features2.jsonl"
        compute_corpus_features(records, matches, index, output_path=path2)

        content1 = path1.read_bytes()
        content2 = path2.read_bytes()
        assert content1 == content2, (
            "features.jsonl differs between two identical runs"
        )

    def test_tagging_determinism(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Phase 3 tagging produces identical output on two runs."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)
        features = compute_corpus_features(records, matches, index)
        tagging_config = _load_tagging_config()

        # Run 1
        out1 = tmp_path / "tags1"
        run_tagger(
            records, matches, features, tagging_config, output_dir=out1,
        )

        # Run 2
        out2 = tmp_path / "tags2"
        run_tagger(
            records, matches, features, tagging_config, output_dir=out2,
        )

        content1 = (out1 / "tags.jsonl").read_bytes()
        content2 = (out2 / "tags.jsonl").read_bytes()
        assert content1 == content2, (
            "tags.jsonl differs between two identical runs"
        )

        # Also check distribution CSV
        csv1 = (out1 / "nirgun_sagun_distribution.csv").read_bytes()
        csv2 = (out2 / "nirgun_sagun_distribution.csv").read_bytes()
        assert csv1 == csv2, (
            "nirgun_sagun_distribution.csv differs between runs"
        )


# ---------------------------------------------------------------------------
# Test 2: Schema validation on all outputs
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Every JSONL record conforms to its expected schema."""

    def test_matches_schema(
        self, fixtures_dir: Path,
    ) -> None:
        """Every record in matches output conforms to match schema."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)

        for m in matches:
            d = m.to_dict()
            # Required fields per PLAN.md Section 4.3
            assert "line_uid" in d
            assert isinstance(d["line_uid"], str)
            assert "entity_id" in d
            assert isinstance(d["entity_id"], str)
            assert "matched_form" in d
            assert isinstance(d["matched_form"], str)
            assert "span" in d
            assert isinstance(d["span"], list)
            assert len(d["span"]) == 2
            assert all(isinstance(x, int) for x in d["span"])
            assert d["span"][0] < d["span"][1], (
                f"Invalid span: {d['span']}"
            )
            assert "rule_id" in d
            assert isinstance(d["rule_id"], str)
            assert "confidence" in d
            assert d["confidence"] in {"HIGH", "MEDIUM", "LOW"}
            # ambiguity and nested_in may be None
            assert "ambiguity" in d
            assert "nested_in" in d

    def test_features_schema(
        self, fixtures_dir: Path,
    ) -> None:
        """Every record in features output conforms to feature schema."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)
        features = compute_corpus_features(records, matches, index)

        for feat in features:
            assert "line_uid" in feat
            assert isinstance(feat["line_uid"], str)
            assert "token_count" in feat
            assert isinstance(feat["token_count"], int)
            assert feat["token_count"] >= 0
            assert "features" in feat
            assert isinstance(feat["features"], dict)

            # All feature dimensions must be present
            for dim in FEATURE_DIMENSIONS:
                assert dim in feat["features"], (
                    f"Missing feature dimension: {dim}"
                )
                dim_data = feat["features"][dim]
                assert "count" in dim_data
                assert isinstance(dim_data["count"], int)
                assert dim_data["count"] >= 0
                assert "density" in dim_data
                assert isinstance(dim_data["density"], float)
                assert 0.0 <= dim_data["density"] <= 1.0, (
                    f"Density out of range: {dim_data['density']}"
                )
                assert "matched_tokens" in dim_data
                assert isinstance(dim_data["matched_tokens"], list)

    def test_tags_schema(
        self, fixtures_dir: Path,
    ) -> None:
        """Every record in tags output conforms to tag schema."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)
        features = compute_corpus_features(records, matches, index)
        tagging_config = _load_tagging_config()
        tags = run_tagger(records, matches, features, tagging_config)

        for tag in tags:
            d = tag.to_dict()
            assert "line_uid" in d
            assert isinstance(d["line_uid"], str)
            assert "scores" in d
            assert isinstance(d["scores"], dict)
            # All scores are floats in [0, 1]
            for dim_name, score_val in d["scores"].items():
                assert isinstance(score_val, float), (
                    f"Score for {dim_name} is not float: {type(score_val)}"
                )
                assert 0.0 <= score_val <= 1.0, (
                    f"Score for {dim_name} out of range: {score_val}"
                )
            assert "primary_tag" in d
            assert d["primary_tag"] is None or isinstance(
                d["primary_tag"], str,
            )
            assert "secondary_tags" in d
            assert isinstance(d["secondary_tags"], list)
            assert "rules_fired" in d
            assert isinstance(d["rules_fired"], list)
            assert "evidence_tokens" in d
            assert isinstance(d["evidence_tokens"], list)
            assert "score_breakdown" in d
            assert isinstance(d["score_breakdown"], dict)

    def test_manifest_schema(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """run_manifest.json conforms to manifest schema."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(input_dir=html_dir, output_dir=output_dir)

        manifest_path = output_dir / "run_manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"),
        )

        assert "schema_version" in manifest
        assert isinstance(manifest["schema_version"], str)
        assert "phase" in manifest
        assert isinstance(manifest["phase"], str)
        assert "generator_version" in manifest
        assert isinstance(manifest["generator_version"], str)
        assert "generated_at" in manifest
        assert isinstance(manifest["generated_at"], str)
        # git_commit may be None or str
        assert "git_commit" in manifest
        assert "wall_clock_seconds" in manifest
        assert isinstance(manifest["wall_clock_seconds"], (int, float))
        assert manifest["wall_clock_seconds"] >= 0
        assert "record_counts" in manifest
        assert isinstance(manifest["record_counts"], dict)

    def test_validation_report_schema(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """validation_report.json conforms to validation schema."""
        html_dir = fixtures_dir / "html"
        output_dir = tmp_path / "corpus"
        run_phase0(input_dir=html_dir, output_dir=output_dir)

        report_path = output_dir / "validation_report.json"
        report = json.loads(
            report_path.read_text(encoding="utf-8"),
        )

        assert "total_lines" in report
        assert isinstance(report["total_lines"], int)
        assert report["total_lines"] > 0
        assert "verdict" in report
        assert report["verdict"] in {"PASS", "FAIL"}
        assert "checks_passed" in report
        assert isinstance(report["checks_passed"], dict)
        assert "checks_failed" in report
        assert isinstance(report["checks_failed"], dict)
        assert "error_count" in report
        assert isinstance(report["error_count"], int)
        assert "warning_count" in report
        assert isinstance(report["warning_count"], int)
        assert "errors" in report
        assert isinstance(report["errors"], list)
        assert "warnings" in report
        assert isinstance(report["warnings"], list)


# ---------------------------------------------------------------------------
# Test 3: Cross-artifact consistency
# ---------------------------------------------------------------------------


class TestCrossArtifactConsistency:
    """Every line_uid and entity_id referenced in downstream artifacts
    exists in the upstream source artifacts."""

    @pytest.fixture()
    def pipeline_artifacts(
        self, fixtures_dir: Path,
    ) -> dict[str, Any]:
        """Run the full pipeline and return all artifacts in memory."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)
        features = compute_corpus_features(records, matches, index)
        tagging_config = _load_tagging_config()
        tags = run_tagger(records, matches, features, tagging_config)

        return {
            "records": records,
            "index": index,
            "matches": matches,
            "features": features,
            "tags": tags,
        }

    def test_match_line_uids_in_corpus(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Every line_uid in matches exists in ggs_lines corpus."""
        records = pipeline_artifacts["records"]
        matches = pipeline_artifacts["matches"]

        corpus_uids = {r["line_uid"] for r in records}
        for m in matches:
            assert m.line_uid in corpus_uids, (
                f"Match references unknown line_uid: {m.line_uid}"
            )

    def test_feature_line_uids_in_corpus(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Every line_uid in features exists in ggs_lines corpus."""
        records = pipeline_artifacts["records"]
        features = pipeline_artifacts["features"]

        corpus_uids = {r["line_uid"] for r in records}
        for feat in features:
            assert feat["line_uid"] in corpus_uids, (
                f"Feature references unknown line_uid: {feat['line_uid']}"
            )

    def test_tag_line_uids_in_corpus(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Every line_uid in tags exists in ggs_lines corpus."""
        records = pipeline_artifacts["records"]
        tags = pipeline_artifacts["tags"]

        corpus_uids = {r["line_uid"] for r in records}
        for tag in tags:
            assert tag.line_uid in corpus_uids, (
                f"Tag references unknown line_uid: {tag.line_uid}"
            )

    def test_match_entity_ids_in_lexicon(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Every entity_id in matches exists in the loaded lexicon."""
        index = pipeline_artifacts["index"]
        matches = pipeline_artifacts["matches"]

        for m in matches:
            assert m.entity_id in index.entities, (
                f"Match references unknown entity_id: {m.entity_id}"
            )

    def test_features_cover_all_corpus_lines(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Features are computed for every line in the corpus."""
        records = pipeline_artifacts["records"]
        features = pipeline_artifacts["features"]

        assert len(features) == len(records), (
            f"Feature count ({len(features)}) != "
            f"corpus line count ({len(records)})"
        )

    def test_tags_cover_all_corpus_lines(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Tags are generated for every line in the corpus."""
        records = pipeline_artifacts["records"]
        tags = pipeline_artifacts["tags"]

        assert len(tags) == len(records), (
            f"Tag count ({len(tags)}) != "
            f"corpus line count ({len(records)})"
        )

    def test_match_spans_within_gurmukhi_bounds(
        self, pipeline_artifacts: dict[str, Any],
    ) -> None:
        """Match spans are valid indices into the gurmukhi field."""
        records = pipeline_artifacts["records"]
        matches = pipeline_artifacts["matches"]

        text_by_uid = {r["line_uid"]: r["gurmukhi"] for r in records}
        for m in matches:
            text = text_by_uid.get(m.line_uid, "")
            start, end = m.span
            assert 0 <= start < end <= len(text), (
                f"Match span [{start}, {end}] out of bounds "
                f"for text of length {len(text)} "
                f"(line_uid={m.line_uid})"
            )
            # The extracted text should match the matched_form
            extracted = text[start:end]
            assert extracted == m.matched_form, (
                f"Span [{start}, {end}] extracts {extracted!r}, "
                f"expected {m.matched_form!r}"
            )


# ---------------------------------------------------------------------------
# Test 4: JSONL serialization roundtrip
# ---------------------------------------------------------------------------


class TestJsonlRoundtrip:
    """Records survive JSON serialization and deserialization."""

    def test_match_record_roundtrip(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """MatchRecord -> dict -> JSON -> dict -> verify equality."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()

        path = tmp_path / "matches.jsonl"
        matches = run_matching(records, index, output_path=path)

        if not matches:
            pytest.skip("No matches found with test lexicon")

        # Read back and compare
        reloaded = _read_jsonl(path)
        assert len(reloaded) == len(matches)

        for original, loaded in zip(matches, reloaded, strict=True):
            original_dict = original.to_dict()
            assert original_dict == loaded, (
                f"Roundtrip mismatch: {original_dict} != {loaded}"
            )

    def test_feature_record_roundtrip(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Feature records survive JSONL roundtrip."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)

        path = tmp_path / "features.jsonl"
        features = compute_corpus_features(
            records, matches, index, output_path=path,
        )

        reloaded = _read_jsonl(path)
        assert len(reloaded) == len(features)

        for original, loaded in zip(features, reloaded, strict=True):
            assert original == loaded, (
                f"Feature roundtrip mismatch for "
                f"{original.get('line_uid', 'UNKNOWN')}"
            )

    def test_tag_record_roundtrip(
        self, fixtures_dir: Path, tmp_path: Path,
    ) -> None:
        """Tag records survive JSONL roundtrip."""
        records = _load_fixture_corpus(fixtures_dir)
        index = _load_test_lexicon()
        matches = run_matching(records, index)
        features = compute_corpus_features(records, matches, index)
        tagging_config = _load_tagging_config()

        tags_dir = tmp_path / "tags"
        tags = run_tagger(
            records, matches, features, tagging_config,
            output_dir=tags_dir,
        )

        tags_path = tags_dir / "tags.jsonl"
        reloaded = _read_jsonl(tags_path)
        assert len(reloaded) == len(tags)

        for original, loaded in zip(tags, reloaded, strict=True):
            original_dict = original.to_dict()
            assert original_dict == loaded, (
                f"Tag roundtrip mismatch for {original.line_uid}"
            )
