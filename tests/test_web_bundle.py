"""Web bundle builder tests (bd-9i3.1, bd-9i3.2).

Tests pipeline data joining, corpus chunking, structured chunks with
token spans, aggregates computation, manifest hashing, validation,
and end-to-end bundle building.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ggs.output.web_bundle import (
    JoinedLine,
    ValidationResult,
    build_bundle,
    build_corpus_chunks,
    chunk_by_ang_range,
    compute_aggregates,
    compute_bundle_manifest,
    compute_token_spans,
    join_pipeline_data,
    validate_bundle,
    write_chunks,
    write_structured_chunks,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_records(
    count: int = 5,
    ang_start: int = 1,
) -> list[dict[str, Any]]:
    """Build test corpus records."""
    return [
        {
            "line_uid": f"line:{i}",
            "ang": ang_start + i,
            "gurmukhi": f"text_{i}",
            "tokens": [f"tok_{i}"],
            "meta": {
                "author": "Guru Nanak",
                "raga": "Sri",
                "shabad_uid": f"shabad:{(i // 3) + 1}",
            },
        }
        for i in range(count)
    ]


def _make_matches(line_uids: list[str]) -> list[dict[str, Any]]:
    """Build test match records."""
    return [
        {
            "line_uid": uid,
            "entity_id": "WAHEGURU",
            "matched_form": "form",
            "span": [0, 4],
        }
        for uid in line_uids
    ]


def _make_features(line_uids: list[str]) -> list[dict[str, Any]]:
    """Build test feature records."""
    return [
        {"line_uid": uid, "features": {"sanskritic": {"density": 0.5}}}
        for uid in line_uids
    ]


def _make_tags(line_uids: list[str]) -> list[dict[str, Any]]:
    """Build test tag records."""
    return [
        {
            "line_uid": uid,
            "primary_tag": "nirgun_leaning",
            "scores": {"nirgun": 0.8},
        }
        for uid in line_uids
    ]


# ---------------------------------------------------------------------------
# JoinedLine tests
# ---------------------------------------------------------------------------


class TestJoinedLine:
    """Tests for JoinedLine."""

    def test_to_dict(self) -> None:
        line = JoinedLine(
            line_uid="line:1",
            ang=1,
            gurmukhi="text",
            tokens=["tok"],
            meta={"author": "Guru Nanak"},
            matches=[{"entity_id": "WAHEGURU"}],
            features={"sanskritic": 0.5},
            tags={"primary_tag": "nirgun_leaning"},
        )
        d = line.to_dict()
        assert d["line_uid"] == "line:1"
        assert d["ang"] == 1
        assert d["gurmukhi"] == "text"
        assert d["matches"] == [{"entity_id": "WAHEGURU"}]
        assert d["tags"]["primary_tag"] == "nirgun_leaning"

    def test_defaults(self) -> None:
        line = JoinedLine(line_uid="line:1", ang=1, gurmukhi="text")
        d = line.to_dict()
        assert d["tokens"] == []
        assert d["matches"] == []
        assert d["features"] == {}
        assert d["tags"] == {}


# ---------------------------------------------------------------------------
# Join pipeline data tests
# ---------------------------------------------------------------------------


class TestJoinPipelineData:
    """Tests for join_pipeline_data."""

    def test_basic_join(self) -> None:
        records = _make_records(2)
        matches = _make_matches(["line:0"])
        features = _make_features(["line:0", "line:1"])
        tags = _make_tags(["line:0"])

        joined = join_pipeline_data(records, matches, features, tags)
        assert len(joined) == 2
        assert joined[0].line_uid == "line:0"
        assert len(joined[0].matches) == 1
        assert joined[0].features != {}
        assert joined[0].tags != {}
        assert joined[1].matches == []

    def test_records_only(self) -> None:
        records = _make_records(3)
        joined = join_pipeline_data(records)
        assert len(joined) == 3
        assert all(j.matches == [] for j in joined)

    def test_empty_records(self) -> None:
        joined = join_pipeline_data([])
        assert joined == []

    def test_preserves_corpus_order(self) -> None:
        records = [
            {"line_uid": "line:3", "ang": 3, "gurmukhi": "c"},
            {"line_uid": "line:1", "ang": 1, "gurmukhi": "a"},
            {"line_uid": "line:2", "ang": 2, "gurmukhi": "b"},
        ]
        joined = join_pipeline_data(records)
        uids = [j.line_uid for j in joined]
        assert uids == ["line:3", "line:1", "line:2"]


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------


class TestChunkByAngRange:
    """Tests for chunk_by_ang_range."""

    def test_basic_chunking(self) -> None:
        lines = [
            JoinedLine(line_uid=f"line:{i}", ang=i, gurmukhi="")
            for i in range(1, 201)
        ]
        chunks = chunk_by_ang_range(lines, chunk_size=100)
        assert len(chunks) == 2
        assert "chunk_001-100" in chunks
        assert "chunk_101-200" in chunks
        assert len(chunks["chunk_001-100"]) == 100
        assert len(chunks["chunk_101-200"]) == 100

    def test_custom_chunk_size(self) -> None:
        lines = [
            JoinedLine(line_uid=f"line:{i}", ang=i, gurmukhi="")
            for i in range(1, 51)
        ]
        chunks = chunk_by_ang_range(lines, chunk_size=25)
        assert len(chunks) == 2
        assert "chunk_001-025" in chunks
        assert "chunk_026-050" in chunks

    def test_unknown_ang(self) -> None:
        lines = [
            JoinedLine(line_uid="line:1", ang=0, gurmukhi=""),
            JoinedLine(line_uid="line:2", ang=-1, gurmukhi=""),
        ]
        chunks = chunk_by_ang_range(lines)
        assert "chunk_unknown" in chunks
        assert len(chunks["chunk_unknown"]) == 2

    def test_empty_lines(self) -> None:
        chunks = chunk_by_ang_range([])
        assert chunks == {}

    def test_chunks_contain_dicts(self) -> None:
        lines = [
            JoinedLine(line_uid="line:1", ang=1, gurmukhi="text"),
        ]
        chunks = chunk_by_ang_range(lines)
        assert isinstance(chunks["chunk_001-100"][0], dict)
        assert chunks["chunk_001-100"][0]["line_uid"] == "line:1"


class TestWriteChunks:
    """Tests for write_chunks."""

    def test_writes_files(self, tmp_path: Path) -> None:
        chunks = {
            "chunk_001-100": [
                {"line_uid": "line:1", "ang": 1},
            ],
            "chunk_101-200": [
                {"line_uid": "line:101", "ang": 101},
            ],
        }
        corpus_dir = tmp_path / "corpus"
        paths = write_chunks(chunks, corpus_dir)

        assert len(paths) == 2
        assert (corpus_dir / "chunk_001-100.json").exists()
        assert (corpus_dir / "chunk_101-200.json").exists()

        data = json.loads(
            (corpus_dir / "chunk_001-100.json").read_text(),
        )
        assert len(data) == 1
        assert data[0]["line_uid"] == "line:1"

    def test_creates_directory(self, tmp_path: Path) -> None:
        chunks = {"chunk_001-100": []}
        corpus_dir = tmp_path / "deep" / "nested" / "corpus"
        write_chunks(chunks, corpus_dir)
        assert corpus_dir.exists()


# ---------------------------------------------------------------------------
# Aggregates tests
# ---------------------------------------------------------------------------


class TestComputeAggregates:
    """Tests for compute_aggregates."""

    def test_basic_aggregates(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1",
                ang=1,
                gurmukhi="text",
                tokens=["a", "b"],
                meta={
                    "author": "Guru Nanak",
                    "shabad_uid": "shabad:1",
                },
                matches=[
                    {"entity_id": "WAHEGURU"},
                    {"entity_id": "WAHEGURU"},
                ],
                tags={"primary_tag": "nirgun_leaning"},
            ),
            JoinedLine(
                line_uid="line:2",
                ang=2,
                gurmukhi="text2",
                tokens=["c"],
                meta={
                    "author": "Kabir",
                    "shabad_uid": "shabad:2",
                },
                matches=[{"entity_id": "RAM_NARRATIVE"}],
                tags={"primary_tag": "mixed"},
            ),
        ]
        agg = compute_aggregates(lines)

        assert agg["corpus"]["total_lines"] == 2
        assert agg["corpus"]["total_tokens"] == 3
        assert agg["corpus"]["unique_entities"] == 2
        assert agg["corpus"]["unique_shabads"] == 2
        assert agg["corpus"]["ang_range"]["min"] == 1
        assert agg["corpus"]["ang_range"]["max"] == 2

    def test_top_entities(self) -> None:
        lines = [
            JoinedLine(
                line_uid=f"line:{i}",
                ang=i,
                gurmukhi="",
                matches=[{"entity_id": "WAHEGURU"}],
            )
            for i in range(10)
        ]
        agg = compute_aggregates(lines)
        assert len(agg["top_entities"]) == 1
        assert agg["top_entities"][0]["entity_id"] == "WAHEGURU"
        assert agg["top_entities"][0]["count"] == 10

    def test_entity_by_author(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1",
                ang=1,
                gurmukhi="",
                meta={"author": "Guru Nanak"},
                matches=[{"entity_id": "WAHEGURU"}],
            ),
            JoinedLine(
                line_uid="line:2",
                ang=2,
                gurmukhi="",
                meta={"author": "Kabir"},
                matches=[{"entity_id": "RAM_NARRATIVE"}],
            ),
        ]
        agg = compute_aggregates(lines)
        assert "Guru Nanak" in agg["entity_by_author"]
        assert "WAHEGURU" in agg["entity_by_author"]["Guru Nanak"]

    def test_tag_distribution(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1", ang=1, gurmukhi="",
                tags={"primary_tag": "nirgun_leaning"},
            ),
            JoinedLine(
                line_uid="line:2", ang=2, gurmukhi="",
                tags={"primary_tag": None},
            ),
            JoinedLine(
                line_uid="line:3", ang=3, gurmukhi="",
                tags={},
            ),
        ]
        agg = compute_aggregates(lines)
        assert agg["tag_distribution"]["nirgun_leaning"] == 1
        assert agg["tag_distribution"]["unclassified"] == 2

    def test_empty_lines(self) -> None:
        agg = compute_aggregates([])
        assert agg["corpus"]["total_lines"] == 0
        assert agg["corpus"]["ang_range"]["min"] == 0


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestComputeBundleManifest:
    """Tests for compute_bundle_manifest."""

    def test_computes_hashes(self, tmp_path: Path) -> None:
        f1 = tmp_path / "file1.json"
        f2 = tmp_path / "file2.json"
        f1.write_text("{}", encoding="utf-8")
        f2.write_text("{}", encoding="utf-8")

        hashes = compute_bundle_manifest(tmp_path)
        assert "file1.json" in hashes
        assert "file2.json" in hashes
        assert all(h.startswith("sha256:") for h in hashes.values())

    def test_excludes_manifest_json(self, tmp_path: Path) -> None:
        f1 = tmp_path / "data.json"
        f1.write_text("{}", encoding="utf-8")
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")

        hashes = compute_bundle_manifest(tmp_path)
        assert "manifest.json" not in hashes
        assert "data.json" in hashes

    def test_includes_subdirectories(self, tmp_path: Path) -> None:
        sub = tmp_path / "corpus"
        sub.mkdir()
        f1 = sub / "chunk.json"
        f1.write_text("{}", encoding="utf-8")

        hashes = compute_bundle_manifest(tmp_path)
        assert "corpus/chunk.json" in hashes


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidateBundle:
    """Tests for validate_bundle."""

    def test_valid_bundle(self, tmp_path: Path) -> None:
        # Set up a minimal valid bundle
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        chunk = corpus_dir / "chunk_001-100.json"
        chunk.write_text("[]", encoding="utf-8")

        agg = tmp_path / "aggregates.json"
        agg.write_text("{}", encoding="utf-8")

        # Write manifest with correct hashes
        from ggs.pipeline.manifest import file_sha256

        hashes = {
            "corpus/chunk_001-100.json": file_sha256(chunk),
            "aggregates.json": file_sha256(agg),
        }
        manifest = {"file_hashes": hashes}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest), encoding="utf-8",
        )

        result = validate_bundle(tmp_path)
        assert result.valid

    def test_missing_corpus(self, tmp_path: Path) -> None:
        agg = tmp_path / "aggregates.json"
        agg.write_text("{}", encoding="utf-8")

        result = validate_bundle(tmp_path)
        assert not result.valid
        assert any("corpus" in e for e in result.errors)

    def test_missing_aggregates(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus"
        corpus.mkdir()

        result = validate_bundle(tmp_path)
        assert not result.valid
        assert any("aggregates" in e for e in result.errors)

    def test_invalid_chunk_json(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        bad = corpus / "chunk_001-100.json"
        bad.write_text("not valid json{{{", encoding="utf-8")

        agg = tmp_path / "aggregates.json"
        agg.write_text("{}", encoding="utf-8")

        result = validate_bundle(tmp_path)
        assert not result.valid
        assert any("Invalid chunk" in e for e in result.errors)

    def test_hash_mismatch(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        chunk = corpus / "chunk_001-100.json"
        chunk.write_text("[]", encoding="utf-8")

        agg = tmp_path / "aggregates.json"
        agg.write_text("{}", encoding="utf-8")

        manifest = {
            "file_hashes": {
                "corpus/chunk_001-100.json": "sha256:wrong",
            },
        }
        mp = tmp_path / "manifest.json"
        mp.write_text(json.dumps(manifest), encoding="utf-8")

        result = validate_bundle(tmp_path)
        assert not result.valid
        assert any("Hash mismatch" in e for e in result.errors)

    def test_no_manifest_is_warning(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "chunk.json").write_text("[]", encoding="utf-8")
        (tmp_path / "aggregates.json").write_text("{}", encoding="utf-8")

        result = validate_bundle(tmp_path)
        assert result.valid  # Not an error, just a warning
        assert any("manifest" in w for w in result.warnings)

    def test_validation_result_serialization(self) -> None:
        result = ValidationResult(
            valid=False,
            errors=["error1"],
            warnings=["warning1"],
        )
        d = result.to_dict()
        assert d["valid"] is False
        assert d["errors"] == ["error1"]


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestBuildBundle:
    """Tests for build_bundle."""

    def test_basic_build(self, tmp_path: Path) -> None:
        records = _make_records(5, ang_start=1)
        matches = _make_matches(["line:0", "line:1"])
        features = _make_features(["line:0"])
        tags = _make_tags(["line:0"])

        output_dir = tmp_path / "web_bundle"
        summary = build_bundle(
            records,
            matches=matches,
            features=features,
            tags=tags,
            output_dir=output_dir,
        )

        assert summary["total_lines"] == 5
        assert (output_dir / "corpus").exists()
        assert (output_dir / "aggregates.json").exists()
        assert (output_dir / "manifest.json").exists()
        assert summary["validation"]["valid"]

    def test_no_output_dir(self) -> None:
        records = _make_records(3)
        summary = build_bundle(records)
        assert summary["total_lines"] == 3
        assert "validation" not in summary

    def test_empty_records(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "bundle"
        summary = build_bundle([], output_dir=output_dir)
        assert summary["total_lines"] == 0

    def test_records_only(self, tmp_path: Path) -> None:
        records = _make_records(10)
        output_dir = tmp_path / "bundle"
        summary = build_bundle(records, output_dir=output_dir)
        assert summary["total_lines"] == 10
        assert summary["total_chunks"] >= 1

    def test_custom_chunk_size(self, tmp_path: Path) -> None:
        records = [
            {
                "line_uid": f"line:{i}",
                "ang": i,
                "gurmukhi": f"text_{i}",
            }
            for i in range(1, 201)
        ]
        output_dir = tmp_path / "bundle"
        summary = build_bundle(
            records, output_dir=output_dir, chunk_size=50,
        )
        assert summary["total_chunks"] == 4  # 1-50, 51-100, 101-150, 151-200

    def test_manifest_hashes_correct(self, tmp_path: Path) -> None:
        records = _make_records(3)
        output_dir = tmp_path / "bundle"
        build_bundle(records, output_dir=output_dir)

        manifest_path = output_dir / "manifest.json"
        with manifest_path.open() as fh:
            manifest = json.load(fh)

        # Verify all files mentioned exist
        for rel_path in manifest["file_hashes"]:
            assert (output_dir / rel_path).exists()

    def test_aggregates_content(self, tmp_path: Path) -> None:
        records = _make_records(5)
        matches = _make_matches(["line:0", "line:1"])
        output_dir = tmp_path / "bundle"
        build_bundle(
            records, matches=matches, output_dir=output_dir,
        )

        agg_path = output_dir / "aggregates.json"
        agg = json.loads(agg_path.read_text())
        assert agg["corpus"]["total_lines"] == 5
        assert agg["corpus"]["unique_entities"] >= 1


# ---------------------------------------------------------------------------
# Token span tests (bd-9i3.2)
# ---------------------------------------------------------------------------


class TestComputeTokenSpans:
    """Tests for compute_token_spans."""

    def test_basic_spans(self) -> None:
        text = "ਹਰਿ ਨਾਮੁ ਜਪ"
        tokens = ["ਹਰਿ", "ਨਾਮੁ", "ਜਪ"]
        spans = compute_token_spans(text, tokens)
        assert len(spans) == 3
        assert spans[0] == [0, 3]
        assert spans[1] == [4, 8]
        assert spans[2] == [9, 11]

    def test_single_token(self) -> None:
        text = "ਵਾਹਿਗੁਰੂ"
        tokens = ["ਵਾਹਿਗੁਰੂ"]
        spans = compute_token_spans(text, tokens)
        assert spans == [[0, len("ਵਾਹਿਗੁਰੂ")]]

    def test_empty_tokens(self) -> None:
        spans = compute_token_spans("ਹਰਿ ਨਾਮੁ", [])
        assert spans == []

    def test_empty_text(self) -> None:
        spans = compute_token_spans("", ["ਹਰਿ"])
        assert spans == [[-1, -1]]

    def test_token_not_found(self) -> None:
        text = "ਹਰਿ ਨਾਮੁ"
        tokens = ["ਜਪ"]
        spans = compute_token_spans(text, tokens)
        assert spans == [[-1, -1]]

    def test_spans_are_ordered(self) -> None:
        text = "abc def ghi"
        tokens = ["abc", "def", "ghi"]
        spans = compute_token_spans(text, tokens)
        for i in range(len(spans) - 1):
            if spans[i][0] >= 0 and spans[i + 1][0] >= 0:
                assert spans[i][1] <= spans[i + 1][0]

    def test_ascii_text(self) -> None:
        text = "hello world test"
        tokens = ["hello", "world", "test"]
        spans = compute_token_spans(text, tokens)
        assert spans[0] == [0, 5]
        assert spans[1] == [6, 11]
        assert spans[2] == [12, 16]


# ---------------------------------------------------------------------------
# Structured chunk tests (bd-9i3.2)
# ---------------------------------------------------------------------------


class TestBuildCorpusChunks:
    """Tests for build_corpus_chunks."""

    def test_basic_structured_chunks(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1",
                ang=1,
                gurmukhi="ਹਰਿ ਨਾਮੁ",
                tokens=["ਹਰਿ", "ਨਾਮੁ"],
            ),
            JoinedLine(
                line_uid="line:2",
                ang=50,
                gurmukhi="ਸਤਿ",
                tokens=["ਸਤਿ"],
            ),
        ]
        chunks = build_corpus_chunks(lines, chunk_size=100)
        assert "chunk_001-100" in chunks
        chunk = chunks["chunk_001-100"]
        assert chunk["ang_range"] == [1, 100]
        assert chunk["total_lines"] == 2
        assert len(chunk["lines"]) == 2

    def test_includes_token_spans(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1",
                ang=1,
                gurmukhi="ਹਰਿ ਨਾਮੁ",
                tokens=["ਹਰਿ", "ਨਾਮੁ"],
            ),
        ]
        chunks = build_corpus_chunks(lines)
        line_dict = chunks["chunk_001-100"]["lines"][0]
        assert "token_spans" in line_dict
        assert line_dict["token_spans"][0] == [0, 3]
        assert line_dict["token_spans"][1] == [4, 8]

    def test_multiple_chunks(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1", ang=1, gurmukhi="a",
                tokens=["a"],
            ),
            JoinedLine(
                line_uid="line:2", ang=101, gurmukhi="b",
                tokens=["b"],
            ),
        ]
        chunks = build_corpus_chunks(lines, chunk_size=100)
        assert len(chunks) == 2
        assert "chunk_001-100" in chunks
        assert "chunk_101-200" in chunks
        assert chunks["chunk_001-100"]["ang_range"] == [1, 100]
        assert chunks["chunk_101-200"]["ang_range"] == [101, 200]

    def test_unknown_ang(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1", ang=0, gurmukhi="",
                tokens=[],
            ),
        ]
        chunks = build_corpus_chunks(lines)
        assert "chunk_unknown" in chunks
        assert chunks["chunk_unknown"]["ang_range"] == [0, 0]

    def test_empty_lines(self) -> None:
        chunks = build_corpus_chunks([])
        assert chunks == {}

    def test_preserves_inlined_data(self) -> None:
        lines = [
            JoinedLine(
                line_uid="line:1",
                ang=1,
                gurmukhi="text",
                tokens=["text"],
                meta={"author": "Guru Nanak"},
                matches=[{"entity_id": "WAHEGURU"}],
                features={"sanskritic": 0.5},
                tags={"primary_tag": "nirgun_leaning"},
            ),
        ]
        chunks = build_corpus_chunks(lines)
        line = chunks["chunk_001-100"]["lines"][0]
        assert line["meta"]["author"] == "Guru Nanak"
        assert line["matches"] == [{"entity_id": "WAHEGURU"}]
        assert line["tags"]["primary_tag"] == "nirgun_leaning"

    def test_custom_chunk_size(self) -> None:
        lines = [
            JoinedLine(
                line_uid=f"line:{i}", ang=i, gurmukhi="",
                tokens=[],
            )
            for i in range(1, 101)
        ]
        chunks = build_corpus_chunks(lines, chunk_size=50)
        assert len(chunks) == 2
        assert "chunk_001-050" in chunks
        assert "chunk_051-100" in chunks


class TestWriteStructuredChunks:
    """Tests for write_structured_chunks."""

    def test_writes_structured_files(self, tmp_path: Path) -> None:
        chunks = {
            "chunk_001-100": {
                "ang_range": [1, 100],
                "total_lines": 1,
                "lines": [
                    {"line_uid": "line:1", "ang": 1},
                ],
            },
        }
        corpus_dir = tmp_path / "corpus"
        paths = write_structured_chunks(chunks, corpus_dir)

        assert len(paths) == 1
        assert (corpus_dir / "chunk_001-100.json").exists()

        data = json.loads(
            (corpus_dir / "chunk_001-100.json").read_text(),
        )
        assert data["ang_range"] == [1, 100]
        assert data["total_lines"] == 1
        assert data["lines"][0]["line_uid"] == "line:1"

    def test_creates_directory(self, tmp_path: Path) -> None:
        chunks = {"chunk_001-100": {"ang_range": [1, 100], "lines": []}}
        corpus_dir = tmp_path / "deep" / "nested" / "corpus"
        write_structured_chunks(chunks, corpus_dir)
        assert corpus_dir.exists()
