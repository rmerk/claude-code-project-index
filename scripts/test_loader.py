"""
Unit tests for loader.py lazy-loading interface.

Tests all public functions with valid/invalid inputs, error handling,
and performance requirements (<500ms per module load).
"""

import unittest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import warnings

from loader import (
    load_detail_module,
    find_module_for_file,
    load_detail_by_path,
    load_multiple_modules
)


class TestLoadDetailModule(unittest.TestCase):
    """Test load_detail_module function."""

    def setUp(self):
        """Create temporary directory and test module files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.temp_dir.name)

        # Create valid test module
        self.valid_module = {
            "module_id": "scripts",
            "version": "2.0-split",
            "files": {
                "scripts/loader.py": {
                    "language": "python",
                    "functions": ["load_detail_module"],
                }
            },
            "call_graph_local": [],
            "doc_standard": {},
            "doc_archive": {}
        }

        with open(self.index_dir / "scripts.json", 'w') as f:
            json.dump(self.valid_module, f)

        # Create invalid JSON module
        with open(self.index_dir / "invalid.json", 'w') as f:
            f.write("{invalid json")

        # Create module missing required fields
        incomplete_module = {"module_id": "incomplete"}
        with open(self.index_dir / "incomplete.json", 'w') as f:
            json.dump(incomplete_module, f)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_load_valid_module(self):
        """Test loading a valid module returns correct data."""
        result = load_detail_module("scripts", self.index_dir)

        self.assertEqual(result["module_id"], "scripts")
        self.assertEqual(result["version"], "2.0-split")
        self.assertIn("files", result)
        self.assertIn("call_graph_local", result)

    def test_load_nonexistent_module(self):
        """Test loading nonexistent module raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError) as cm:
            load_detail_module("nonexistent", self.index_dir)

        self.assertIn("Module 'nonexistent' not found", str(cm.exception))
        self.assertIn("PROJECT_INDEX.d/", str(cm.exception))

    def test_load_invalid_json(self):
        """Test loading module with invalid JSON raises JSONDecodeError."""
        with self.assertRaises(json.JSONDecodeError) as cm:
            load_detail_module("invalid", self.index_dir)

        self.assertIn("Invalid JSON in detail module 'invalid'", str(cm.exception))

    def test_load_incomplete_module(self):
        """Test loading module missing required fields raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            load_detail_module("incomplete", self.index_dir)

        self.assertIn("missing required fields", str(cm.exception))
        self.assertIn("version", str(cm.exception))
        self.assertIn("files", str(cm.exception))

    def test_invalid_module_name_format(self):
        """Test invalid module name format raises ValueError."""
        invalid_names = [
            "module/name",  # slash not allowed
            "module name",  # space not allowed
            "module.name",  # dot not allowed
            "",  # empty not allowed
        ]

        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as cm:
                    load_detail_module(name, self.index_dir)
                self.assertIn("Invalid module_name format", str(cm.exception))

    def test_valid_module_name_formats(self):
        """Test valid module name formats are accepted."""
        valid_names = [
            "auth",
            "auth-service",
            "auth_service",
            "auth-service-v2",
            "auth_service_v2",
            "AUTH123",
        ]

        for name in valid_names:
            with self.subTest(name=name):
                # Create test file
                test_module = {
                    "module_id": name,
                    "version": "2.0-split",
                    "files": {}
                }
                with open(self.index_dir / f"{name}.json", 'w') as f:
                    json.dump(test_module, f)

                # Should not raise
                result = load_detail_module(name, self.index_dir)
                self.assertEqual(result["module_id"], name)

    def test_default_index_dir(self):
        """Test default index_dir uses PROJECT_INDEX.d/ in cwd."""
        # This test would require setting up PROJECT_INDEX.d/ in actual cwd
        # For now, just verify it uses Path.cwd()
        with patch('loader.Path.cwd') as mock_cwd:
            mock_cwd.return_value = self.index_dir.parent
            # Create PROJECT_INDEX.d/ in mocked cwd
            default_dir = self.index_dir.parent / "PROJECT_INDEX.d"
            default_dir.mkdir(exist_ok=True)

            with open(default_dir / "test.json", 'w') as f:
                json.dump(self.valid_module, f)

            result = load_detail_module("test")
            self.assertEqual(result["module_id"], "scripts")

    def test_performance_under_500ms(self):
        """Test module loading completes in under 500ms (NFR001)."""
        start_time = time.time()
        load_detail_module("scripts", self.index_dir)
        elapsed_ms = (time.time() - start_time) * 1000

        self.assertLess(
            elapsed_ms, 500,
            f"Loading took {elapsed_ms:.2f}ms, exceeds 500ms requirement"
        )


class TestFindModuleForFile(unittest.TestCase):
    """Test find_module_for_file function."""

    def setUp(self):
        """Create test core index."""
        self.core_index = {
            "modules": {
                "scripts": {
                    "files": [
                        "scripts/loader.py",
                        "scripts/project_index.py",
                        "scripts/index_utils.py"
                    ]
                },
                "agents": {
                    "files": [
                        "agents/index-analyzer.md"
                    ]
                }
            }
        }

    def test_find_existing_file(self):
        """Test finding file that exists in a module."""
        result = find_module_for_file("scripts/loader.py", self.core_index)
        self.assertEqual(result, "scripts")

        result = find_module_for_file("agents/index-analyzer.md", self.core_index)
        self.assertEqual(result, "agents")

    def test_find_file_with_leading_slash(self):
        """Test finding file with ./ prefix normalizes correctly."""
        result = find_module_for_file("./scripts/loader.py", self.core_index)
        self.assertEqual(result, "scripts")

    def test_file_not_found(self):
        """Test file not in any module raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            find_module_for_file("nonexistent/file.py", self.core_index)

        self.assertIn("File 'nonexistent/file.py' not found", str(cm.exception))
        self.assertIn("Searched 2 module(s)", str(cm.exception))

    def test_invalid_core_index_missing_modules(self):
        """Test core_index without 'modules' or 'f' keys raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            find_module_for_file("test.py", {})

        error_msg = str(cm.exception)
        # Should mention both missing keys
        self.assertIn("missing both 'modules' and 'f' keys", error_msg.lower())

    def test_invalid_core_index_type(self):
        """Test non-dict core_index raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            find_module_for_file("test.py", "not a dict")

        self.assertIn("core_index must be dict", str(cm.exception))

    def test_invalid_file_path_type(self):
        """Test non-string file_path raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            find_module_for_file(123, self.core_index)

        self.assertIn("file_path must be str", str(cm.exception))

    def test_core_index_files_as_dict(self):
        """Test handling core_index with files as dict (not list)."""
        core_index_dict_files = {
            "modules": {
                "scripts": {
                    "files": {
                        "scripts/loader.py": {"language": "python"},
                        "scripts/index_utils.py": {"language": "python"}
                    }
                }
            }
        }

        result = find_module_for_file("scripts/loader.py", core_index_dict_files)
        self.assertEqual(result, "scripts")


class TestLoadDetailByPath(unittest.TestCase):
    """Test load_detail_by_path function."""

    def setUp(self):
        """Create temporary directory and test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.temp_dir.name)

        # Create test module
        self.test_module = {
            "module_id": "scripts",
            "version": "2.0-split",
            "files": {
                "scripts/loader.py": {"language": "python"}
            },
            "call_graph_local": []
        }

        with open(self.index_dir / "scripts.json", 'w') as f:
            json.dump(self.test_module, f)

        # Create core index
        self.core_index = {
            "modules": {
                "scripts": {
                    "files": ["scripts/loader.py", "scripts/project_index.py"]
                }
            }
        }

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_load_by_valid_path(self):
        """Test loading module by valid file path."""
        result = load_detail_by_path(
            "scripts/loader.py",
            self.core_index,
            self.index_dir
        )

        self.assertEqual(result["module_id"], "scripts")
        self.assertIn("files", result)

    def test_load_by_nonexistent_path(self):
        """Test loading by nonexistent file path raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            load_detail_by_path(
                "nonexistent/file.py",
                self.core_index,
                self.index_dir
            )

        self.assertIn("File 'nonexistent/file.py' not found", str(cm.exception))

    def test_integration_with_find_module(self):
        """Test that load_detail_by_path correctly uses find_module_for_file."""
        # This is an integration test ensuring the two functions work together
        result = load_detail_by_path(
            "scripts/project_index.py",  # File exists in core index
            self.core_index,
            self.index_dir
        )

        # Should load the scripts module
        self.assertEqual(result["module_id"], "scripts")


class TestLoadMultipleModules(unittest.TestCase):
    """Test load_multiple_modules function."""

    def setUp(self):
        """Create temporary directory and test modules."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.temp_dir.name)

        # Create multiple test modules
        modules = {
            "scripts": {"module_id": "scripts", "version": "2.0-split", "files": {}},
            "agents": {"module_id": "agents", "version": "2.0-split", "files": {}},
            "bmad": {"module_id": "bmad", "version": "2.0-split", "files": {}}
        }

        for name, data in modules.items():
            with open(self.index_dir / f"{name}.json", 'w') as f:
                json.dump(data, f)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_load_all_valid_modules(self):
        """Test loading multiple valid modules."""
        result = load_multiple_modules(
            ["scripts", "agents", "bmad"],
            self.index_dir
        )

        self.assertEqual(len(result), 3)
        self.assertIn("scripts", result)
        self.assertIn("agents", result)
        self.assertIn("bmad", result)

        # Verify each module has correct structure
        for module_name, module_data in result.items():
            self.assertEqual(module_data["module_id"], module_name)
            self.assertEqual(module_data["version"], "2.0-split")

    def test_load_with_partial_failures(self):
        """Test batch loading with mixed valid/invalid modules."""
        # Suppress warnings for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            result = load_multiple_modules(
                ["scripts", "nonexistent", "agents"],
                self.index_dir
            )

        # Should return only valid modules
        self.assertEqual(len(result), 2)
        self.assertIn("scripts", result)
        self.assertIn("agents", result)
        self.assertNotIn("nonexistent", result)

    def test_load_all_invalid_modules(self):
        """Test batch loading with all invalid modules returns empty dict."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            result = load_multiple_modules(
                ["invalid1", "invalid2", "invalid3"],
                self.index_dir
            )

        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, dict)

    def test_load_empty_list(self):
        """Test loading empty list returns empty dict."""
        result = load_multiple_modules([], self.index_dir)

        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, dict)

    def test_invalid_input_type(self):
        """Test non-list input raises TypeError."""
        with self.assertRaises(TypeError) as cm:
            load_multiple_modules("not a list", self.index_dir)

        self.assertIn("module_names must be list", str(cm.exception))

    def test_warnings_for_failed_modules(self):
        """Test that warnings are issued for failed module loads."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            load_multiple_modules(
                ["scripts", "nonexistent"],
                self.index_dir
            )

            # Should have warning for nonexistent module
            self.assertEqual(len(w), 1)
            self.assertIn("nonexistent", str(w[0].message))


class TestIntegrationWithRealProject(unittest.TestCase):
    """Integration tests using actual PROJECT_INDEX.d/ from Story 1.3."""

    def setUp(self):
        """Check if real PROJECT_INDEX.d/ exists."""
        self.project_root = Path.cwd()
        self.index_dir = self.project_root / "PROJECT_INDEX.d"
        self.core_index_path = self.project_root / "PROJECT_INDEX.json"

        self.has_split_index = (
            self.index_dir.exists() and
            self.core_index_path.exists()
        )

    @unittest.skipUnless(
        Path.cwd().joinpath("PROJECT_INDEX.d").exists(),
        "PROJECT_INDEX.d/ not found - run Story 1.3 first"
    )
    def test_load_real_scripts_module(self):
        """Test loading actual scripts module generated by Story 1.3."""
        result = load_detail_module("scripts", self.index_dir)

        self.assertEqual(result["module_id"], "scripts")
        self.assertEqual(result["version"], "2.0-split")
        self.assertIn("files", result)
        self.assertGreater(len(result["files"]), 0)

    @unittest.skipUnless(
        Path.cwd().joinpath("PROJECT_INDEX.json").exists(),
        "PROJECT_INDEX.json not found"
    )
    def test_load_by_real_file_path(self):
        """Test loading module by real file path from project.

        Note: If PROJECT_INDEX.json is in legacy format, this will raise
        a helpful error directing the user to regenerate with --split flag.
        """
        with open(self.core_index_path) as f:
            core_index = json.load(f)

        # Check if this is split format or legacy format
        if "modules" in core_index:
            # Split format - should work
            result = load_detail_by_path(
                "scripts/project_index.py",
                core_index,
                self.index_dir
            )
            self.assertEqual(result["module_id"], "scripts")
        else:
            # Legacy format - should raise helpful error
            with self.assertRaises(ValueError) as cm:
                load_detail_by_path(
                    "scripts/project_index.py",
                    core_index,
                    self.index_dir
                )
            self.assertIn("legacy format", str(cm.exception).lower())
            self.assertIn("--split", str(cm.exception))

    @unittest.skipUnless(
        Path.cwd().joinpath("PROJECT_INDEX.d").exists(),
        "PROJECT_INDEX.d/ not found"
    )
    def test_batch_load_real_modules(self):
        """Test batch loading real modules from project."""
        # Get list of actual modules
        module_files = list(self.index_dir.glob("*.json"))
        module_names = [f.stem for f in module_files]

        if len(module_names) > 0:
            result = load_multiple_modules(module_names, self.index_dir)

            self.assertEqual(len(result), len(module_names))
            for name in module_names:
                self.assertIn(name, result)


if __name__ == '__main__':
    unittest.main()
