#!/usr/bin/env python3
"""
Tests for signature_cache module.

Tests cache key generation, load/save operations, and cache invalidation.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path

from signature_cache import (
    CACHE_VERSION,
    get_cache_key,
    get_cache_path,
    load_cache,
    save_cache,
    get_cached_signature,
    set_cached_signature,
    clear_cache,
    get_cache_stats
)


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_get_cache_key_basic(self, tmp_path):
        """Test basic cache key generation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        key = get_cache_key(test_file)

        assert isinstance(key, str)
        assert len(key) == 16  # SHA256 prefix

    def test_cache_key_changes_on_modification(self, tmp_path):
        """Test that cache key changes when file is modified."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        key1 = get_cache_key(test_file)

        # Modify file
        test_file.write_text("print('world')")

        key2 = get_cache_key(test_file)

        assert key1 != key2

    def test_cache_key_same_for_unchanged_file(self, tmp_path):
        """Test that cache key is consistent for unchanged file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        key1 = get_cache_key(test_file)
        key2 = get_cache_key(test_file)

        assert key1 == key2

    def test_cache_key_different_for_different_files(self, tmp_path):
        """Test that different files have different keys."""
        file1 = tmp_path / "test1.py"
        file2 = tmp_path / "test2.py"
        file1.write_text("print('hello')")
        file2.write_text("print('hello')")  # Same content

        key1 = get_cache_key(file1)
        key2 = get_cache_key(file2)

        # Different paths should have different keys
        assert key1 != key2


class TestCacheLoadSave:
    """Test cache loading and saving."""

    def test_load_cache_empty(self, tmp_path):
        """Test loading cache when no cache exists."""
        cache = load_cache(tmp_path)

        assert cache["version"] == CACHE_VERSION
        assert cache["signatures"] == {}

    def test_save_and_load_cache(self, tmp_path):
        """Test saving and loading cache."""
        cache = {
            "version": CACHE_VERSION,
            "signatures": {
                "abc123": {"functions": {"foo": "(x, y)"}}
            }
        }

        save_cache(tmp_path, cache)
        loaded = load_cache(tmp_path)

        assert loaded == cache

    def test_cache_creates_directory(self, tmp_path):
        """Test that save_cache creates cache directory."""
        cache = {"version": CACHE_VERSION, "signatures": {}}

        result = save_cache(tmp_path, cache)

        assert result is True
        assert (tmp_path / ".project-index-cache").exists()

    def test_load_cache_version_mismatch(self, tmp_path):
        """Test that old cache versions are discarded."""
        cache_dir = tmp_path / ".project-index-cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "signatures.json"
        cache_file.write_text(json.dumps({
            "version": "0.0",  # Old version
            "signatures": {"old": "data"}
        }))

        cache = load_cache(tmp_path)

        assert cache["version"] == CACHE_VERSION
        assert cache["signatures"] == {}

    def test_load_cache_corrupted(self, tmp_path):
        """Test loading corrupted cache file."""
        cache_dir = tmp_path / ".project-index-cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "signatures.json"
        cache_file.write_text("not valid json{{{")

        cache = load_cache(tmp_path)

        assert cache["version"] == CACHE_VERSION
        assert cache["signatures"] == {}


class TestCacheOperations:
    """Test cache get/set operations."""

    def test_get_cached_signature_miss(self, tmp_path):
        """Test cache miss."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        cache = {"version": CACHE_VERSION, "signatures": {}}

        result = get_cached_signature(test_file, cache)

        assert result is None

    def test_get_cached_signature_hit(self, tmp_path):
        """Test cache hit."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        signature = {"functions": {"main": "()"}}
        cache = {"version": CACHE_VERSION, "signatures": {}}
        set_cached_signature(test_file, signature, cache)

        result = get_cached_signature(test_file, cache)

        assert result == signature

    def test_set_cached_signature(self, tmp_path):
        """Test setting cached signature."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = {"version": CACHE_VERSION, "signatures": {}}
        signature = {"functions": {"foo": "(x, y)"}}

        set_cached_signature(test_file, signature, cache)

        assert len(cache["signatures"]) == 1
        # Verify we can retrieve it
        assert get_cached_signature(test_file, cache) == signature

    def test_cache_invalidation_on_modification(self, tmp_path):
        """Test that cache is invalidated when file changes."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        cache = {"version": CACHE_VERSION, "signatures": {}}
        signature = {"functions": {"foo": "(x, y)"}}
        set_cached_signature(test_file, signature, cache)

        # Verify it's cached
        assert get_cached_signature(test_file, cache) == signature

        # Modify file
        test_file.write_text("print('world')")

        # Cache should miss now (key changed)
        assert get_cached_signature(test_file, cache) is None


class TestCacheUtilities:
    """Test cache utility functions."""

    def test_clear_cache(self, tmp_path):
        """Test clearing cache."""
        cache = {"version": CACHE_VERSION, "signatures": {"key": "value"}}
        save_cache(tmp_path, cache)

        result = clear_cache(tmp_path)

        assert result is True
        assert not (tmp_path / ".project-index-cache" / "signatures.json").exists()

    def test_clear_cache_no_file(self, tmp_path):
        """Test clearing cache when no cache exists."""
        result = clear_cache(tmp_path)

        assert result is False

    def test_get_cache_stats_empty(self, tmp_path):
        """Test cache stats when no cache exists."""
        stats = get_cache_stats(tmp_path)

        assert stats["exists"] is False
        assert stats["entries"] == 0
        assert stats["size_bytes"] == 0

    def test_get_cache_stats_with_data(self, tmp_path):
        """Test cache stats with data."""
        cache = {
            "version": CACHE_VERSION,
            "signatures": {
                "key1": {"functions": {}},
                "key2": {"functions": {}}
            }
        }
        save_cache(tmp_path, cache)

        stats = get_cache_stats(tmp_path)

        assert stats["exists"] is True
        assert stats["entries"] == 2
        assert stats["size_bytes"] > 0
        assert stats["version"] == CACHE_VERSION


class TestCachePath:
    """Test cache path generation."""

    def test_get_cache_path(self, tmp_path):
        """Test cache path generation."""
        path = get_cache_path(tmp_path)

        assert path == tmp_path / ".project-index-cache" / "signatures.json"


class TestIntegration:
    """Integration tests for cache workflow."""

    def test_full_workflow(self, tmp_path):
        """Test complete cache workflow."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("def foo(): pass")
        file2.write_text("def bar(): pass")

        # Load empty cache
        cache = load_cache(tmp_path)
        assert len(cache["signatures"]) == 0

        # Cache some signatures
        sig1 = {"functions": {"foo": "()"}}
        sig2 = {"functions": {"bar": "()"}}
        set_cached_signature(file1, sig1, cache)
        set_cached_signature(file2, sig2, cache)

        # Save cache
        save_cache(tmp_path, cache)

        # Load cache in new session
        new_cache = load_cache(tmp_path)

        # Verify signatures are preserved
        assert get_cached_signature(file1, new_cache) == sig1
        assert get_cached_signature(file2, new_cache) == sig2

        # Modify one file
        file1.write_text("def foo(x): pass")

        # file1 should miss, file2 should hit
        assert get_cached_signature(file1, new_cache) is None
        assert get_cached_signature(file2, new_cache) == sig2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
