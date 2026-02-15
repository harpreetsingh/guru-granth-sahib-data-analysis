"""YAML lexicon loader with schema validation (bd-4i2.1).

Reads all lexicon YAML files, validates entries against ``_schema.yaml``,
resolves aliases, and builds data structures for the matching engine.

Usage::

    index = load_lexicon(config)
    # index.entities["ALLAH"]           -> Entity record
    # index.alias_to_entities["ਅਲਾਹੁ"] -> ["ALLAH"]
    # index.file_hashes["entities.yaml"] -> "sha256:..."
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ggs.pipeline.errors import FatalPipelineError

# ---------------------------------------------------------------------------
# Controlled vocabularies (from _schema.yaml)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset({
    "divine_name",
    "concept",
    "marker",
    "narrative",
    "place",
    "practice",
    "negation",
    "temporal",
    "ethical",
    "devotional",
    "identity",
    "scriptural",
    "oneness",
})

VALID_TRADITIONS = frozenset({
    "islamic",
    "vedantic",
    "vaishnava",
    "yogic",
    "bhakti",
    "universal",
    "sikh",
})

VALID_REGISTERS = frozenset({
    "perso_arabic",
    "sanskritic",
    "mixed",
    "neutral",
})

VALID_ALIAS_TYPES = frozenset({"exact", "prefix", "suffix"})

_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Alias:
    """A single alias entry for an entity."""

    form: str
    type: str  # exact | prefix | suffix


@dataclass(frozen=True, slots=True)
class Entity:
    """A validated lexicon entity."""

    id: str
    canonical_form: str
    aliases: tuple[Alias, ...]
    category: str
    tradition: str | None = None
    register: str | None = None
    notes: str | None = None
    polysemous: bool = False
    added_version: str | None = None
    source_file: str | None = None


@dataclass
class LexiconIndex:
    """Compiled lexicon ready for the matching engine.

    Attributes:
        entities: Mapping of entity_id to Entity.
        alias_to_entities: Mapping of surface form to entity_ids
            that share that alias.  Multiple IDs = polysemy.
        file_hashes: SHA-256 hash of each source file.
    """

    entities: dict[str, Entity] = field(default_factory=dict)
    alias_to_entities: dict[str, list[str]] = field(
        default_factory=dict,
    )
    file_hashes: dict[str, str] = field(default_factory=dict)

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def alias_count(self) -> int:
        return sum(
            len(ents) for ents in self.alias_to_entities.values()
        )

    def all_surface_forms(self) -> list[str]:
        """Return all unique surface forms in the index."""
        return sorted(self.alias_to_entities.keys())


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class LexiconValidationError(FatalPipelineError):
    """Raised when a lexicon file has structural errors."""

    def __init__(self, message: str, *, file: str = "") -> None:
        super().__init__(
            message,
            error_type="LEXICON_VALIDATION_ERROR",
            phase="lexicon",
            context={"file": file},
        )


def _validate_entity_dict(
    raw: dict[str, Any],
    *,
    file_name: str,
) -> Entity:
    """Validate a raw entity dict and return an Entity.

    Raises :class:`LexiconValidationError` on any violation.
    """
    # Required fields
    for req in ("id", "canonical_form", "aliases", "category"):
        if req not in raw:
            msg = (
                f"Entity in {file_name} missing required "
                f"field '{req}': {raw}"
            )
            raise LexiconValidationError(msg, file=file_name)

    eid = raw["id"]
    if not _ID_PATTERN.match(eid):
        msg = (
            f"Entity ID '{eid}' in {file_name} must be "
            f"UPPER_SNAKE_CASE (^[A-Z][A-Z0-9_]+$)"
        )
        raise LexiconValidationError(msg, file=file_name)

    category = raw["category"]
    if category not in VALID_CATEGORIES:
        msg = (
            f"Entity '{eid}' in {file_name} has invalid "
            f"category '{category}'. "
            f"Must be one of: {sorted(VALID_CATEGORIES)}"
        )
        raise LexiconValidationError(msg, file=file_name)

    # Optional controlled-vocabulary fields
    tradition = raw.get("tradition")
    if tradition is not None and tradition not in VALID_TRADITIONS:
        msg = (
            f"Entity '{eid}' in {file_name} has invalid "
            f"tradition '{tradition}'. "
            f"Must be one of: {sorted(VALID_TRADITIONS)}"
        )
        raise LexiconValidationError(msg, file=file_name)

    register = raw.get("register")
    if register is not None and register not in VALID_REGISTERS:
        msg = (
            f"Entity '{eid}' in {file_name} has invalid "
            f"register '{register}'. "
            f"Must be one of: {sorted(VALID_REGISTERS)}"
        )
        raise LexiconValidationError(msg, file=file_name)

    # Aliases
    raw_aliases = raw["aliases"]
    if not raw_aliases:
        msg = (
            f"Entity '{eid}' in {file_name} must have "
            f"at least one alias"
        )
        raise LexiconValidationError(msg, file=file_name)

    aliases: list[Alias] = []
    for alias_dict in raw_aliases:
        if "form" not in alias_dict or "type" not in alias_dict:
            msg = (
                f"Alias in entity '{eid}' ({file_name}) "
                f"missing 'form' or 'type': {alias_dict}"
            )
            raise LexiconValidationError(msg, file=file_name)

        alias_type = alias_dict["type"]
        if alias_type not in VALID_ALIAS_TYPES:
            msg = (
                f"Alias type '{alias_type}' in entity "
                f"'{eid}' ({file_name}) invalid. "
                f"Must be one of: {sorted(VALID_ALIAS_TYPES)}"
            )
            raise LexiconValidationError(msg, file=file_name)

        aliases.append(
            Alias(form=alias_dict["form"], type=alias_type),
        )

    return Entity(
        id=eid,
        canonical_form=raw["canonical_form"],
        aliases=tuple(aliases),
        category=category,
        tradition=tradition,
        register=register,
        notes=raw.get("notes"),
        polysemous=bool(raw.get("polysemous", False)),
        added_version=raw.get("added_version"),
        source_file=file_name,
    )


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------


def _file_sha256(path: Path) -> str:
    """Compute SHA-256 of a file for provenance tracking."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(8192):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_lexicon_file(
    path: Path,
) -> list[Entity]:
    """Load and validate a single lexicon YAML file.

    The YAML must contain an ``entities`` key with a list of entry dicts.

    Raises:
        LexiconValidationError: If any entry is invalid.
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        msg = f"Lexicon file not found: {path}"
        raise LexiconValidationError(msg, file=str(path))

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None or "entities" not in data:
        msg = (
            f"Lexicon file {path.name} must contain an "
            f"'entities' key"
        )
        raise LexiconValidationError(msg, file=path.name)

    entities: list[Entity] = []
    for raw_entity in data["entities"]:
        entity = _validate_entity_dict(
            raw_entity, file_name=path.name,
        )
        entities.append(entity)

    return entities


def load_lexicon(
    lexicon_paths: dict[str, str | Path],
    *,
    base_dir: Path | None = None,
) -> LexiconIndex:
    """Load all lexicon files and build a compiled index.

    Args:
        lexicon_paths: Mapping from label to file path, as found
            in ``config.yaml``'s ``lexicon_paths`` section.
        base_dir: Base directory to resolve relative paths against.
            If *None*, paths are treated as-is.

    Returns:
        A :class:`LexiconIndex` with validated entities, alias
        index, and file hashes.

    Raises:
        LexiconValidationError: On schema violations or ID collisions.
    """
    index = LexiconIndex()
    seen_ids: dict[str, str] = {}  # entity_id -> source file

    for _label, rel_path in lexicon_paths.items():
        path = Path(rel_path)
        if base_dir is not None:
            path = base_dir / path

        if not path.exists():
            # Skip missing optional lexicon files (e.g., polysemy.yaml
            # may not exist yet during initial development)
            continue

        # Hash the file for provenance
        index.file_hashes[path.name] = _file_sha256(path)

        # Skip files that use a different schema (e.g., polysemy.yaml
        # uses a polysemy registry format, not entity definitions)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None or "entities" not in data:
            continue

        # Load and validate
        entities = load_lexicon_file(path)

        for entity in entities:
            # Check for ID collisions across files
            if entity.id in seen_ids:
                msg = (
                    f"Duplicate entity ID '{entity.id}': "
                    f"found in both {seen_ids[entity.id]} "
                    f"and {path.name}"
                )
                raise LexiconValidationError(
                    msg, file=path.name,
                )

            seen_ids[entity.id] = path.name
            index.entities[entity.id] = entity

            # Build alias index
            for alias in entity.aliases:
                if alias.form not in index.alias_to_entities:
                    index.alias_to_entities[alias.form] = []
                index.alias_to_entities[alias.form].append(
                    entity.id,
                )

    return index
