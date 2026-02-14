"""Incremental caching tests (bd-tun.2).

Tests cache entry creation, load/save, invalidation,
hash computation, cache check logic, and cache update.
"""

from __future__ import annotations

from pathlib import Path

from ggs.pipeline.cache import (
    CacheEntry,
    PipelineCache,
    check_cache,
    compute_input_hashes,
    compute_output_hashes,
    update_cache,
)

# ---------------------------------------------------------------------------
# CacheEntry tests
# ---------------------------------------------------------------------------


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_to_dict(self) -> None:
        entry = CacheEntry(
            phase="lexical",
            computed_at="2025-01-01T00:00:00",
            input_hashes={"corpus": "sha256:abc"},
            output_hashes={"matches.jsonl": "sha256:xyz"},
        )
        d = entry.to_dict()
        assert d["phase"] == "lexical"
        assert d["input_hashes"]["corpus"] == "sha256:abc"

    def test_from_dict(self) -> None:
        data = {
            "phase": "structural",
            "computed_at": "2025-01-01T00:00:00",
            "input_hashes": {"config": "sha256:123"},
            "output_hashes": {"output.json": "sha256:456"},
        }
        entry = CacheEntry.from_dict(data)
        assert entry.phase == "structural"
        assert entry.input_hashes == {"config": "sha256:123"}
        assert entry.output_hashes == {"output.json": "sha256:456"}

    def test_from_dict_missing_fields(self) -> None:
        entry = CacheEntry.from_dict({})
        assert entry.phase == ""
        assert entry.input_hashes == {}

    def test_roundtrip(self) -> None:
        entry = CacheEntry(
            phase="tagging",
            computed_at="2025-06-15T12:00:00+00:00",
            input_hashes={"a": "sha256:111", "b": "sha256:222"},
            output_hashes={"c": "sha256:333"},
        )
        restored = CacheEntry.from_dict(entry.to_dict())
        assert restored.phase == entry.phase
        assert restored.input_hashes == entry.input_hashes
        assert restored.output_hashes == entry.output_hashes


# ---------------------------------------------------------------------------
# PipelineCache tests
# ---------------------------------------------------------------------------


class TestPipelineCache:
    """Tests for PipelineCache."""

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        result = cache.load_entry("lexical")
        assert result is None

    def test_save_and_load(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        entry = CacheEntry(
            phase="lexical",
            computed_at="2025-01-01T00:00:00",
            input_hashes={"corpus": "sha256:abc"},
        )
        saved_path = cache.save_entry(entry)
        assert saved_path.exists()

        loaded = cache.load_entry("lexical")
        assert loaded is not None
        assert loaded.phase == "lexical"
        assert loaded.input_hashes == {"corpus": "sha256:abc"}

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "deep" / "nested" / ".cache"
        cache = PipelineCache(cache_dir=cache_dir)
        entry = CacheEntry(phase="test")
        cache.save_entry(entry)
        assert cache_dir.exists()

    def test_invalidate(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        entry = CacheEntry(phase="lexical")
        cache.save_entry(entry)

        assert cache.invalidate("lexical")
        assert cache.load_entry("lexical") is None

    def test_invalidate_nonexistent(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        assert not cache.invalidate("nonexistent")

    def test_invalidate_all(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        cache.save_entry(CacheEntry(phase="phase1"))
        cache.save_entry(CacheEntry(phase="phase2"))
        cache.save_entry(CacheEntry(phase="phase3"))

        count = cache.invalidate_all()
        assert count == 3
        assert cache.load_entry("phase1") is None
        assert cache.load_entry("phase2") is None
        assert cache.load_entry("phase3") is None

    def test_invalidate_all_empty(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        assert cache.invalidate_all() == 0

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        bad_file = cache_dir / "bad_input_hash.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")

        cache = PipelineCache(cache_dir=cache_dir)
        result = cache.load_entry("bad")
        assert result is None


# ---------------------------------------------------------------------------
# Hash computation tests
# ---------------------------------------------------------------------------


class TestComputeHashes:
    """Tests for compute_input_hashes and compute_output_hashes."""

    def test_compute_input_hashes(self, tmp_path: Path) -> None:
        f1 = tmp_path / "config.yaml"
        f2 = tmp_path / "corpus.jsonl"
        f1.write_text("key: value", encoding="utf-8")
        f2.write_text('{"line": 1}', encoding="utf-8")

        hashes = compute_input_hashes({
            "config": f1,
            "corpus": f2,
        })
        assert "config" in hashes
        assert "corpus" in hashes
        assert hashes["config"].startswith("sha256:")
        assert hashes["corpus"].startswith("sha256:")

    def test_skips_missing_files(self, tmp_path: Path) -> None:
        hashes = compute_input_hashes({
            "missing": tmp_path / "nonexistent.txt",
        })
        assert hashes == {}

    def test_compute_output_hashes(self, tmp_path: Path) -> None:
        f1 = tmp_path / "output.jsonl"
        f1.write_text('{"result": true}', encoding="utf-8")

        hashes = compute_output_hashes({"output": f1})
        assert "output" in hashes
        assert hashes["output"].startswith("sha256:")

    def test_deterministic_hashes(self, tmp_path: Path) -> None:
        f1 = tmp_path / "stable.txt"
        f1.write_text("same content", encoding="utf-8")

        h1 = compute_input_hashes({"file": f1})
        h2 = compute_input_hashes({"file": f1})
        assert h1 == h2

    def test_different_content_different_hash(
        self, tmp_path: Path,
    ) -> None:
        f1 = tmp_path / "file.txt"
        f1.write_text("content A", encoding="utf-8")
        h1 = compute_input_hashes({"file": f1})

        f1.write_text("content B", encoding="utf-8")
        h2 = compute_input_hashes({"file": f1})

        assert h1 != h2


# ---------------------------------------------------------------------------
# Cache check tests
# ---------------------------------------------------------------------------


class TestCheckCache:
    """Tests for check_cache."""

    def test_cache_hit(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        # Create an input file and output file
        input_file = tmp_path / "input.txt"
        input_file.write_text("input data", encoding="utf-8")
        output_file = tmp_path / "output.jsonl"
        output_file.write_text("output data", encoding="utf-8")

        input_hashes = compute_input_hashes({"input": input_file})
        output_hashes = compute_output_hashes({"output": output_file})

        # Save a cache entry
        entry = CacheEntry(
            phase="test_phase",
            computed_at="2025-01-01",
            input_hashes=input_hashes,
            output_hashes=output_hashes,
        )
        cache.save_entry(entry)

        # Check cache — should be a hit
        result = check_cache(
            "test_phase",
            input_hashes,
            {"output": output_file},
            cache,
        )
        assert result.cache_hit
        assert "match" in result.reason

    def test_cache_miss_no_entry(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        result = check_cache(
            "test_phase", {}, {}, cache,
        )
        assert not result.cache_hit
        assert "no cached entry" in result.reason

    def test_cache_miss_force(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")
        # Save a valid entry
        entry = CacheEntry(
            phase="test_phase",
            input_hashes={},
            output_hashes={},
        )
        cache.save_entry(entry)

        result = check_cache(
            "test_phase", {}, {}, cache, force=True,
        )
        assert not result.cache_hit
        assert "--force" in result.reason

    def test_cache_miss_input_changed(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        entry = CacheEntry(
            phase="test_phase",
            input_hashes={"config": "sha256:old"},
        )
        cache.save_entry(entry)

        result = check_cache(
            "test_phase",
            {"config": "sha256:new"},
            {},
            cache,
        )
        assert not result.cache_hit
        assert "input hashes changed" in result.reason
        assert "config" in result.reason

    def test_cache_miss_output_missing(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        entry = CacheEntry(
            phase="test_phase",
            input_hashes={"config": "sha256:abc"},
            output_hashes={"output.jsonl": "sha256:xyz"},
        )
        cache.save_entry(entry)

        result = check_cache(
            "test_phase",
            {"config": "sha256:abc"},
            {"output.jsonl": tmp_path / "nonexistent.jsonl"},
            cache,
        )
        assert not result.cache_hit
        assert "output files missing" in result.reason

    def test_cache_miss_output_changed(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        # Create output file and cache its hash
        output_file = tmp_path / "output.jsonl"
        output_file.write_text("original", encoding="utf-8")
        output_hashes = compute_output_hashes({"output": output_file})

        entry = CacheEntry(
            phase="test_phase",
            input_hashes={},
            output_hashes=output_hashes,
        )
        cache.save_entry(entry)

        # Modify the output file
        output_file.write_text("modified", encoding="utf-8")

        result = check_cache(
            "test_phase",
            {},
            {"output": output_file},
            cache,
        )
        assert not result.cache_hit
        assert "output hashes changed" in result.reason


# ---------------------------------------------------------------------------
# Cache update tests
# ---------------------------------------------------------------------------


class TestUpdateCache:
    """Tests for update_cache."""

    def test_updates_cache(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        output_file = tmp_path / "result.jsonl"
        output_file.write_text("result data", encoding="utf-8")

        entry = update_cache(
            "test_phase",
            {"input": "sha256:abc"},
            {"result": output_file},
            cache,
        )

        assert entry.phase == "test_phase"
        assert entry.input_hashes == {"input": "sha256:abc"}
        assert "result" in entry.output_hashes
        assert entry.computed_at != ""

        # Verify it's persisted
        loaded = cache.load_entry("test_phase")
        assert loaded is not None
        assert loaded.input_hashes == entry.input_hashes

    def test_update_then_check_is_hit(self, tmp_path: Path) -> None:
        cache = PipelineCache(cache_dir=tmp_path / ".cache")

        input_file = tmp_path / "input.txt"
        input_file.write_text("data", encoding="utf-8")
        output_file = tmp_path / "output.jsonl"
        output_file.write_text("result", encoding="utf-8")

        input_hashes = compute_input_hashes({"input": input_file})

        # Update cache
        update_cache(
            "my_phase",
            input_hashes,
            {"output": output_file},
            cache,
        )

        # Check should be a hit
        result = check_cache(
            "my_phase",
            input_hashes,
            {"output": output_file},
            cache,
        )
        assert result.cache_hit
