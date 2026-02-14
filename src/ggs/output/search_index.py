"""Pre-built search index generation (bd-9i3.3).

Builds a client-side search index from the corpus that enables Gurmukhi
text search in the webapp without a server. The index is pre-built at
pipeline time and loaded by the client on first search interaction.

The index format is a JSON structure compatible with MiniSearch:
  - ``documents``: Array of document descriptors with id, fields
  - ``index_config``: Tokenization and field configuration
  - ``metadata``: Index statistics (doc count, build time, etc.)

Size budget: <5MB compressed for the full 1430-ang corpus.

Gurmukhi-specific considerations:
  - Tokenization matches corpus tokenizer (whitespace + Unicode normalization)
  - Searches work with normalized Gurmukhi forms
  - Index includes entity matches for entity-aware search

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

_console = Console()


# ---------------------------------------------------------------------------
# Index document
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SearchDocument:
    """A single document in the search index.

    Attributes:
        doc_id: Unique document identifier (line_uid).
        ang: Ang number.
        gurmukhi: Full Gurmukhi text of the line.
        tokens: Tokenized form for search matching.
        entities: Entity IDs matched on this line.
        author: Author attribution (if known).
        raga: Raga section (if known).
    """

    doc_id: str
    ang: int
    gurmukhi: str
    tokens: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    author: str = ""
    raga: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.doc_id,
            "ang": self.ang,
            "gurmukhi": self.gurmukhi,
            "tokens": " ".join(self.tokens),
            "entities": self.entities,
            "author": self.author,
            "raga": self.raga,
        }


# ---------------------------------------------------------------------------
# Token index (inverted index)
# ---------------------------------------------------------------------------


def build_token_index(
    documents: list[SearchDocument],
) -> dict[str, list[str]]:
    """Build an inverted index from tokens to document IDs.

    Args:
        documents: All search documents.

    Returns:
        Mapping from token to list of document IDs containing that token.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for doc in documents:
        seen: set[str] = set()
        for token in doc.tokens:
            if token not in seen:
                index[token].append(doc.doc_id)
                seen.add(token)
    return dict(index)


def build_entity_index(
    documents: list[SearchDocument],
) -> dict[str, list[str]]:
    """Build an inverted index from entity IDs to document IDs.

    Args:
        documents: All search documents.

    Returns:
        Mapping from entity_id to list of document IDs.
    """
    index: dict[str, list[str]] = defaultdict(list)
    for doc in documents:
        seen: set[str] = set()
        for entity_id in doc.entities:
            if entity_id not in seen:
                index[entity_id].append(doc.doc_id)
                seen.add(entity_id)
    return dict(index)


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SearchIndex:
    """Pre-built search index for the webapp.

    Attributes:
        documents: All indexed documents.
        token_index: Inverted index from tokens to doc IDs.
        entity_index: Inverted index from entity IDs to doc IDs.
        metadata: Index statistics.
    """

    documents: list[SearchDocument] = field(default_factory=list)
    token_index: dict[str, list[str]] = field(default_factory=dict)
    entity_index: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_config": {
                "fields": ["gurmukhi", "tokens", "entities"],
                "store_fields": ["ang", "gurmukhi", "author", "raga"],
                "tokenizer": "whitespace",
                "language": "gurmukhi",
            },
            "documents": [doc.to_dict() for doc in self.documents],
            "token_index": self.token_index,
            "entity_index": self.entity_index,
            "metadata": self.metadata,
        }


def build_search_documents(
    records: list[dict[str, Any]],
    matches: list[dict[str, Any]] | None = None,
) -> list[SearchDocument]:
    """Build search documents from corpus records and optional matches.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: Optional match records for entity indexing.

    Returns:
        List of SearchDocument instances.
    """
    # Index matches by line_uid
    entities_by_line: dict[str, set[str]] = defaultdict(set)
    if matches:
        for m in matches:
            if m.get("nested_in") is None:
                entities_by_line[m.get("line_uid", "")].add(
                    m.get("entity_id", ""),
                )

    documents: list[SearchDocument] = []
    for rec in records:
        line_uid = rec.get("line_uid", "")
        ang = rec.get("ang", 0)
        gurmukhi = rec.get("gurmukhi", "")
        tokens = rec.get("tokens", [])
        author = rec.get("meta", {}).get("author", "")
        raga = rec.get("meta", {}).get("raga", "")

        entities = sorted(entities_by_line.get(line_uid, set()))

        documents.append(
            SearchDocument(
                doc_id=line_uid,
                ang=ang,
                gurmukhi=gurmukhi,
                tokens=tokens,
                entities=entities,
                author=author or "",
                raga=raga or "",
            ),
        )

    return documents


def build_search_index(
    records: list[dict[str, Any]],
    matches: list[dict[str, Any]] | None = None,
) -> SearchIndex:
    """Build the complete search index from corpus records.

    Args:
        records: Corpus record dicts.
        matches: Optional match records for entity-aware search.

    Returns:
        A :class:`SearchIndex` instance.
    """
    documents = build_search_documents(records, matches)
    token_index = build_token_index(documents)
    entity_index = build_entity_index(documents)

    unique_tokens = len(token_index)
    unique_entities = len(entity_index)

    metadata = {
        "total_documents": len(documents),
        "unique_tokens": unique_tokens,
        "unique_entities": unique_entities,
        "ang_range": {
            "min": min((d.ang for d in documents), default=0),
            "max": max((d.ang for d in documents), default=0),
        },
    }

    return SearchIndex(
        documents=documents,
        token_index=token_index,
        entity_index=entity_index,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Search (basic query support)
# ---------------------------------------------------------------------------


def search_index(
    index: SearchIndex,
    query: str,
    *,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """Search the index for matching documents.

    Tokenizes the query using whitespace splitting (matching corpus
    tokenization) and returns documents containing all query tokens.

    Args:
        index: The pre-built search index.
        query: Search query string (Gurmukhi text).
        max_results: Maximum number of results to return.

    Returns:
        List of matching document dicts, sorted by ang number.
    """
    query_tokens = query.split()
    if not query_tokens:
        return []

    # Find documents containing all query tokens (AND logic)
    doc_sets: list[set[str]] = []
    for token in query_tokens:
        doc_ids = index.token_index.get(token, [])
        doc_sets.append(set(doc_ids))

    if not doc_sets:
        return []

    # Intersection of all token result sets
    matching_ids = doc_sets[0]
    for s in doc_sets[1:]:
        matching_ids &= s

    if not matching_ids:
        return []

    # Build doc_id -> document lookup
    doc_by_id = {doc.doc_id: doc for doc in index.documents}

    results = [
        doc_by_id[doc_id].to_dict()
        for doc_id in matching_ids
        if doc_id in doc_by_id
    ]

    # Sort by ang number
    results.sort(key=lambda r: r.get("ang", 0))

    return results[:max_results]


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def generate_search_index(
    records: list[dict[str, Any]],
    matches: list[dict[str, Any]] | None = None,
    *,
    output_path: Path | None = None,
) -> SearchIndex:
    """Build and optionally write the search index.

    Args:
        records: Corpus record dicts (from ggs_lines.jsonl).
        matches: Optional match records for entity-aware search.
        output_path: If provided, write the index JSON to this path.

    Returns:
        The built :class:`SearchIndex`.
    """
    t0 = time.monotonic()

    _console.print(
        "\n[bold]Building search index "
        f"from {len(records)} lines...[/bold]\n",
    )

    index = build_search_index(records, matches)

    _console.print(
        f"  {index.metadata['total_documents']} documents indexed",
    )
    _console.print(
        f"  {index.metadata['unique_tokens']} unique tokens",
    )
    _console.print(
        f"  {index.metadata['unique_entities']} unique entities",
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(
                index.to_dict(), fh,
                ensure_ascii=False,
            )
        size_kb = output_path.stat().st_size / 1024
        _console.print(
            f"  Written to {output_path} ({size_kb:.1f} KB)",
        )

    elapsed = time.monotonic() - t0
    _console.print(f"  Completed in {elapsed:.2f}s")

    return index
