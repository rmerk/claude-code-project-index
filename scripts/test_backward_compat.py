#!/usr/bin/env python3
"""
Tests for backward compatibility detection and legacy format support.

Tests Story 1.6 Acceptance Criteria:
- AC#1: System detects legacy single-file format
- AC#3: All existing functionality works with legacy format
"""

import json
import tempfile
import unittest
from pathlib import Path
from project_index import detect_index_format


class TestDetectIndexFormat(unittest.TestCase):
    """Test format detection logic (AC#1)."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.index_path = self.test_path / "PROJECT_INDEX.json"

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_legacy_format_no_directory(self):
        """Test detection of legacy format when PROJECT_INDEX.d/ doesn't exist."""
        # Create single-file index without directory
        legacy_index = {
            "at": "2025-11-01",
            "root": ".",
            "f": {"scripts/test.py": ["p", []]},
            "g": [],
            "d": {}
        }
        with open(self.index_path, 'w') as f:
            json.dump(legacy_index, f)

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_split_format_with_directory_and_version(self):
        """Test detection of split format when both directory and version present."""
        # Create PROJECT_INDEX.d/ directory
        index_dir = self.test_path / "PROJECT_INDEX.d"
        index_dir.mkdir()

        # Create split format index with version
        split_index = {
            "version": "2.0-split",
            "at": "2025-11-01",
            "root": ".",
            "modules": {
                "scripts": ["scripts/test.py"]
            }
        }
        with open(self.index_path, 'w') as f:
            json.dump(split_index, f)

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "split")

    def test_legacy_format_with_old_version(self):
        """Test legacy detection when version is 1.0."""
        # Create directory but with old version
        index_dir = self.test_path / "PROJECT_INDEX.d"
        index_dir.mkdir()

        legacy_index = {
            "version": "1.0",
            "at": "2025-11-01",
            "root": ".",
            "f": {}
        }
        with open(self.index_path, 'w') as f:
            json.dump(legacy_index, f)

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_legacy_format_missing_version_field(self):
        """Test legacy detection when version field is missing."""
        # Create directory but no version field
        index_dir = self.test_path / "PROJECT_INDEX.d"
        index_dir.mkdir()

        index_no_version = {
            "at": "2025-11-01",
            "root": ".",
            "f": {}
        }
        with open(self.index_path, 'w') as f:
            json.dump(index_no_version, f)

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_legacy_format_empty_index_file(self):
        """Test legacy detection with empty/corrupted index file."""
        # Create empty index file
        with open(self.index_path, 'w') as f:
            f.write("")

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_legacy_format_corrupted_json(self):
        """Test legacy detection with corrupted JSON."""
        with open(self.index_path, 'w') as f:
            f.write("{invalid json")

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_legacy_format_index_file_not_exists(self):
        """Test legacy detection when index file doesn't exist."""
        # Don't create index file at all
        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "legacy")

    def test_split_format_empty_directory(self):
        """Test split detection when directory exists but is empty."""
        # Create empty PROJECT_INDEX.d/ directory
        index_dir = self.test_path / "PROJECT_INDEX.d"
        index_dir.mkdir()

        # Create split format index
        split_index = {
            "version": "2.0-split",
            "at": "2025-11-01",
            "root": ".",
            "modules": {}
        }
        with open(self.index_path, 'w') as f:
            json.dump(split_index, f)

        format_type = detect_index_format(self.index_path)
        self.assertEqual(format_type, "split")

    def test_default_path_parameter(self):
        """Test detect_index_format with default path (cwd)."""
        # This test verifies the function works with no parameters
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # Create legacy index in cwd
            legacy_index = {"at": "2025-11-01", "f": {}}
            with open(self.index_path, 'w') as f:
                json.dump(legacy_index, f)

            format_type = detect_index_format()
            self.assertEqual(format_type, "legacy")
        finally:
            os.chdir(original_cwd)

    def test_performance_under_100ms(self):
        """Test format detection completes in under 100ms (NFR)."""
        import time

        # Create split format for testing
        index_dir = self.test_path / "PROJECT_INDEX.d"
        index_dir.mkdir()

        split_index = {
            "version": "2.0-split",
            "at": "2025-11-01",
            "modules": {}
        }
        with open(self.index_path, 'w') as f:
            json.dump(split_index, f)

        # Measure performance
        start_time = time.perf_counter()
        detect_index_format(self.index_path)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in under 100ms
        self.assertLess(elapsed_ms, 100,
                       f"Format detection took {elapsed_ms:.2f}ms, expected <100ms")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
