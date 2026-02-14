"""Pre-built search index tests (bd-9i3.3).

Tests document building, token indexing, entity indexing, search
functionality, and end-to-end index generation with file output.
"""

from __future__ import annotations

import json
from pathlib import Path

from ggs.output.search_index import (
    SearchDocument,
    SearchIndex,
    build_entity_index,
    build_search_documents,
    build_search_index,
    build_token_index,
    generate_search_index,
    search_index,
)

# ---------------------------------------------------------------------------
# SearchDocument tests
# ---------------------------------------------------------------------------


class TestSearchDocument:
    """Tests for SearchDocument."""

    def test_to_dict(self) -> None:
        doc = SearchDocument(
            doc_id="line:1",
            ang=1,
            gurmukhi="ਹਰਿ ਨਾਮੁ",
            tokens=["ਹਰਿ", "ਨਾਮੁ"],
            entities=["HARI", "NAAM"],
            author="Guru Nanak",
            raga="Sri",
        )
        d = doc.to_dict()
        assert d["id"] == "line:1"
        assert d["ang"] == 1
        assert d["gurmukhi"] == "ਹਰਿ ਨਾਮੁ"
        assert d["tokens"] == "ਹਰਿ ਨਾਮੁ"  # joined
        assert d["entities"] == ["HARI", "NAAM"]
        assert d["author"] == "Guru Nanak"

    def test_to_dict_defaults(self) -> None:
        doc = SearchDocument(
            doc_id="line:1",
            ang=1,
            gurmukhi="ਹਰਿ",
        )
        d = doc.to_dict()
        assert d["tokens"] == ""
        assert d["entities"] == []
        assert d["author"] == ""
        assert d["raga"] == ""


# ---------------------------------------------------------------------------
# Token index tests
# ---------------------------------------------------------------------------


class TestBuildTokenIndex:
    """Tests for build_token_index."""

    def test_basic_index(self) -> None:
        docs = [
            SearchDocument(
                doc_id="line:1", ang=1, gurmukhi="",
                tokens=["ਹਰਿ", "ਨਾਮੁ"],
            ),
            SearchDocument(
                doc_id="line:2", ang=1, gurmukhi="",
                tokens=["ਹਰਿ", "ਜਪ"],
            ),
        ]
        index = build_token_index(docs)
        assert "ਹਰਿ" in index
        assert index["ਹਰਿ"] == ["line:1", "line:2"]
        assert index["ਨਾਮੁ"] == ["line:1"]
        assert index["ਜਪ"] == ["line:2"]

    def test_deduplicates_within_document(self) -> None:
        docs = [
            SearchDocument(
                doc_id="line:1", ang=1, gurmukhi="",
                tokens=["ਹਰਿ", "ਹਰਿ", "ਹਰਿ"],
            ),
        ]
        index = build_token_index(docs)
        assert index["ਹਰਿ"] == ["line:1"]

    def test_empty_documents(self) -> None:
        index = build_token_index([])
        assert index == {}


# ---------------------------------------------------------------------------
# Entity index tests
# ---------------------------------------------------------------------------


class TestBuildEntityIndex:
    """Tests for build_entity_index."""

    def test_basic_index(self) -> None:
        docs = [
            SearchDocument(
                doc_id="line:1", ang=1, gurmukhi="",
                entities=["HARI", "NAAM"],
            ),
            SearchDocument(
                doc_id="line:2", ang=1, gurmukhi="",
                entities=["HARI"],
            ),
        ]
        index = build_entity_index(docs)
        assert index["HARI"] == ["line:1", "line:2"]
        assert index["NAAM"] == ["line:1"]

    def test_deduplicates_within_document(self) -> None:
        docs = [
            SearchDocument(
                doc_id="line:1", ang=1, gurmukhi="",
                entities=["HARI", "HARI"],
            ),
        ]
        index = build_entity_index(docs)
        assert index["HARI"] == ["line:1"]

    def test_empty_entities(self) -> None:
        docs = [
            SearchDocument(
                doc_id="line:1", ang=1, gurmukhi="",
                entities=[],
            ),
        ]
        index = build_entity_index(docs)
        assert index == {}


# ---------------------------------------------------------------------------
# Document building tests
# ---------------------------------------------------------------------------


class TestBuildSearchDocuments:
    """Tests for build_search_documents."""

    def test_basic_build(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਹਰਿ ਨਾਮੁ",
                "tokens": ["ਹਰਿ", "ਨਾਮੁ"],
                "meta": {"author": "Guru Nanak", "raga": "Sri"},
            },
        ]
        docs = build_search_documents(records)
        assert len(docs) == 1
        assert docs[0].doc_id == "line:1"
        assert docs[0].ang == 1
        assert docs[0].gurmukhi == "ਹਰਿ ਨਾਮੁ"
        assert docs[0].tokens == ["ਹਰਿ", "ਨਾਮੁ"]
        assert docs[0].author == "Guru Nanak"

    def test_with_matches(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਹਰਿ",
                "tokens": ["ਹਰਿ"],
                "meta": {},
            },
        ]
        matches = [
            {
                "line_uid": "line:1",
                "entity_id": "HARI",
                "nested_in": None,
            },
        ]
        docs = build_search_documents(records, matches)
        assert docs[0].entities == ["HARI"]

    def test_excludes_nested_matches(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਸਤਿ ਨਾਮੁ",
                "tokens": ["ਸਤਿ", "ਨਾਮੁ"],
                "meta": {},
            },
        ]
        matches = [
            {
                "line_uid": "line:1",
                "entity_id": "SATNAM",
                "nested_in": None,
            },
            {
                "line_uid": "line:1",
                "entity_id": "NAAM",
                "nested_in": "SATNAM",
            },
        ]
        docs = build_search_documents(records, matches)
        assert "SATNAM" in docs[0].entities
        assert "NAAM" not in docs[0].entities

    def test_empty_records(self) -> None:
        docs = build_search_documents([])
        assert docs == []


# ---------------------------------------------------------------------------
# Full index build tests
# ---------------------------------------------------------------------------


class TestBuildSearchIndex:
    """Tests for build_search_index."""

    def test_basic_build(self) -> None:
        records = [
            {
                "line_uid": "line:1",
                "ang": 1,
                "gurmukhi": "ਹਰਿ ਨਾਮੁ",
                "tokens": ["ਹਰਿ", "ਨਾਮੁ"],
                "meta": {},
            },
            {
                "line_uid": "line:2",
                "ang": 2,
                "gurmukhi": "ਸਤਿ ਨਾਮੁ",
                "tokens": ["ਸਤਿ", "ਨਾਮੁ"],
                "meta": {},
            },
        ]
        index = build_search_index(records)
        assert index.metadata["total_documents"] == 2
        assert index.metadata["unique_tokens"] == 3
        assert index.metadata["ang_range"]["min"] == 1
        assert index.metadata["ang_range"]["max"] == 2

    def test_empty_records(self) -> None:
        index = build_search_index([])
        assert index.metadata["total_documents"] == 0


# ---------------------------------------------------------------------------
# SearchIndex serialization tests
# ---------------------------------------------------------------------------


class TestSearchIndexSerialization:
    """Tests for SearchIndex.to_dict."""

    def test_to_dict(self) -> None:
        index = SearchIndex(
            documents=[
                SearchDocument(
                    doc_id="line:1", ang=1, gurmukhi="ਹਰਿ",
                    tokens=["ਹਰਿ"],
                ),
            ],
            token_index={"ਹਰਿ": ["line:1"]},
            entity_index={},
            metadata={"total_documents": 1},
        )
        d = index.to_dict()
        assert "index_config" in d
        assert "documents" in d
        assert "token_index" in d
        assert "entity_index" in d
        assert "metadata" in d
        assert d["index_config"]["language"] == "gurmukhi"


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------


class TestSearchIndex:
    """Tests for search_index."""

    def test_single_token_search(self) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ ਨਾਮੁ", "tokens": ["ਹਰਿ", "ਨਾਮੁ"],
                "meta": {},
            },
            {
                "line_uid": "line:2", "ang": 2,
                "gurmukhi": "ਸਤਿ ਨਾਮੁ", "tokens": ["ਸਤਿ", "ਨਾਮੁ"],
                "meta": {},
            },
        ]
        index = build_search_index(records)
        results = search_index(index, "ਨਾਮੁ")
        assert len(results) == 2

    def test_multi_token_search_and_logic(self) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ ਨਾਮੁ", "tokens": ["ਹਰਿ", "ਨਾਮੁ"],
                "meta": {},
            },
            {
                "line_uid": "line:2", "ang": 2,
                "gurmukhi": "ਸਤਿ ਨਾਮੁ", "tokens": ["ਸਤਿ", "ਨਾਮੁ"],
                "meta": {},
            },
        ]
        index = build_search_index(records)
        results = search_index(index, "ਹਰਿ ਨਾਮੁ")
        assert len(results) == 1
        assert results[0]["id"] == "line:1"

    def test_no_results(self) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ", "tokens": ["ਹਰਿ"],
                "meta": {},
            },
        ]
        index = build_search_index(records)
        results = search_index(index, "ਅਲਾਹੁ")
        assert results == []

    def test_empty_query(self) -> None:
        index = build_search_index([])
        results = search_index(index, "")
        assert results == []

    def test_max_results(self) -> None:
        records = [
            {
                "line_uid": f"line:{i}", "ang": i,
                "gurmukhi": "ਹਰਿ", "tokens": ["ਹਰਿ"],
                "meta": {},
            }
            for i in range(100)
        ]
        index = build_search_index(records)
        results = search_index(index, "ਹਰਿ", max_results=10)
        assert len(results) == 10

    def test_sorted_by_ang(self) -> None:
        records = [
            {
                "line_uid": "line:50", "ang": 50,
                "gurmukhi": "ਹਰਿ", "tokens": ["ਹਰਿ"],
                "meta": {},
            },
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ", "tokens": ["ਹਰਿ"],
                "meta": {},
            },
        ]
        index = build_search_index(records)
        results = search_index(index, "ਹਰਿ")
        assert results[0]["ang"] == 1
        assert results[1]["ang"] == 50


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


class TestGenerateSearchIndex:
    """Tests for generate_search_index."""

    def test_generates_index(self) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ ਨਾਮੁ",
                "tokens": ["ਹਰਿ", "ਨਾਮੁ"],
                "meta": {},
            },
        ]
        index = generate_search_index(records)
        assert index.metadata["total_documents"] == 1

    def test_writes_to_file(self, tmp_path: Path) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ",
                "tokens": ["ਹਰਿ"],
                "meta": {},
            },
        ]
        output = tmp_path / "search_index.json"
        generate_search_index(records, output_path=output)
        assert output.exists()

        data = json.loads(output.read_text())
        assert "documents" in data
        assert "token_index" in data
        assert "metadata" in data

    def test_with_matches(self, tmp_path: Path) -> None:
        records = [
            {
                "line_uid": "line:1", "ang": 1,
                "gurmukhi": "ਹਰਿ",
                "tokens": ["ਹਰਿ"],
                "meta": {},
            },
        ]
        matches = [
            {
                "line_uid": "line:1",
                "entity_id": "HARI",
                "nested_in": None,
            },
        ]
        index = generate_search_index(records, matches)
        assert "HARI" in index.entity_index
        assert "HARI" in index.documents[0].entities

    def test_empty_corpus(self) -> None:
        index = generate_search_index([])
        assert index.metadata["total_documents"] == 0
