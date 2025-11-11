"""
Comprehensive test suite for MCP server (project_index_mcp.py).

Tests cover:
- All 4 tools with valid/invalid inputs
- Pydantic validation (limit >100, offset <0, invalid format)
- Error handling paths (FileNotFoundError, JSONDecodeError, ValueError)
- JSON vs Markdown formatting
- Integration with loader utilities
- Path traversal validation
- Type annotations and code quality

Story: 2-10-mcp-server-implementation
ACs Tested: #1-14 (all acceptance criteria)

Requirements:
- Python 3.12+
- pydantic>=2.0.0
- mcp>=1.0.0

To run tests:
    # Option 1: With virtual environment (recommended)
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python scripts/test_mcp_server.py

    # Option 2: With system Python (if dependencies installed)
    python3 scripts/test_mcp_server.py

Note: MCP server is optional functionality. Core indexing (scripts/project_index.py,
scripts/loader.py) remains stdlib-only and has separate tests that don't require
external dependencies.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Handle optional pydantic dependency
try:
    from pydantic import ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    ValidationError = Exception  # Fallback for type hints

# Add parent and scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Try to import MCP module - skip tests if dependencies not available
try:
    import project_index_mcp as mcp_module
    from project_index_mcp import (
        LoadCoreIndexInput,
        LoadModuleInput,
        SearchFilesInput,
        GetFileInfoInput,
        ResponseFormat,
        _load_json_file,
        _format_core_index_markdown,
        _validate_path_within_project,
        _handle_error,
        project_index_load_core,
        project_index_load_module,
        project_index_search_files,
        project_index_get_file_info,
    )
    MCP_MODULE_AVAILABLE = True
except ImportError as e:
    MCP_MODULE_AVAILABLE = False
    MCP_IMPORT_ERROR = str(e)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestPydanticModels(unittest.TestCase):
    """Test Pydantic model validation (AC #6)."""

    def test_load_core_index_input_defaults(self):
        """
        Test LoadCoreIndexInput with default values.

        AC: #6
        """
        model = LoadCoreIndexInput()
        self.assertIsNone(model.index_path)
        self.assertEqual(model.response_format, ResponseFormat.JSON)

    def test_load_core_index_input_markdown_format(self):
        """
        Test LoadCoreIndexInput with markdown format.

        AC: #6
        """
        model = LoadCoreIndexInput(response_format=ResponseFormat.MARKDOWN)
        self.assertEqual(model.response_format, ResponseFormat.MARKDOWN)

    def test_load_module_input_required_fields(self):
        """
        Test LoadModuleInput requires module_name.

        AC: #6
        """
        with self.assertRaises(ValidationError):
            LoadModuleInput()  # Missing required module_name

    def test_load_module_input_min_length_validation(self):
        """
        Test LoadModuleInput validates min_length=1 for module_name.

        AC: #6
        """
        with self.assertRaises(ValidationError):
            LoadModuleInput(module_name="")  # Empty string

    def test_load_module_input_max_length_validation(self):
        """
        Test LoadModuleInput validates max_length=200 for module_name.

        AC: #6
        """
        with self.assertRaises(ValidationError):
            LoadModuleInput(module_name="a" * 201)  # Too long

    def test_search_files_input_limit_validation(self):
        """
        Test SearchFilesInput validates limit range (1-100).

        AC: #6
        """
        # Test limit < 1
        with self.assertRaises(ValidationError):
            SearchFilesInput(query="test", limit=0)

        # Test limit > 100
        with self.assertRaises(ValidationError):
            SearchFilesInput(query="test", limit=101)

        # Test valid limit
        model = SearchFilesInput(query="test", limit=50)
        self.assertEqual(model.limit, 50)

    def test_search_files_input_offset_validation(self):
        """
        Test SearchFilesInput validates offset >= 0.

        AC: #6
        """
        # Test offset < 0
        with self.assertRaises(ValidationError):
            SearchFilesInput(query="test", offset=-1)

        # Test valid offset
        model = SearchFilesInput(query="test", offset=20)
        self.assertEqual(model.offset, 20)

    def test_search_files_input_query_required(self):
        """
        Test SearchFilesInput requires query field.

        AC: #6
        """
        with self.assertRaises(ValidationError):
            SearchFilesInput()  # Missing required query

    def test_get_file_info_input_required_fields(self):
        """
        Test GetFileInfoInput requires file_path.

        AC: #6
        """
        with self.assertRaises(ValidationError):
            GetFileInfoInput()  # Missing required file_path


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestPathTraversalValidation(unittest.TestCase):
    """Test path traversal validation (Security)."""

    def test_validate_path_within_project_valid(self):
        """
        Test path validation accepts paths within project root.

        Security enhancement from code review.
        """
        project_root = Path(__file__).parent.parent.resolve()
        valid_path = project_root / "PROJECT_INDEX.json"
        validated = _validate_path_within_project(valid_path)
        self.assertTrue(validated.is_absolute())

    def test_validate_path_within_project_traversal_attack(self):
        """
        Test path validation rejects path traversal attempts.

        Security enhancement from code review.
        """
        traversal_path = Path("../../../etc/passwd")
        with self.assertRaises(ValueError) as ctx:
            _validate_path_within_project(traversal_path)
        self.assertIn("must be within project root", str(ctx.exception))


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestLoadCoreIndexTool(unittest.IsolatedAsyncioTestCase):
    """Test project_index_load_core tool (AC #2)."""

    def setUp(self):
        """Create temporary test index for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_index = Path(self.temp_dir) / "PROJECT_INDEX.json"
        self.test_data = {
            "version": "2.1-enhanced",
            "at": "2025-11-03",
            "root": ".",
            "modules": {
                "scripts": {
                    "detail_path": "PROJECT_INDEX.d/scripts.json",
                    "file_count": 23,
                    "function_count": 384
                }
            },
            "stats": {
                "total_files": 24,
                "total_directories": 97,
                "markdown_files": 32
            }
        }
        with open(self.test_index, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_load_core_index_json_format(self):
        """
        Test loading core index in JSON format.

        AC: #2
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = LoadCoreIndexInput(
                index_path=str(self.test_index),
                response_format=ResponseFormat.JSON
            )
            result = await project_index_load_core(params)
            data = json.loads(result)
            self.assertEqual(data["version"], "2.1-enhanced")
            self.assertIn("modules", data)

    async def test_load_core_index_markdown_format(self):
        """
        Test loading core index in Markdown format.

        AC: #2
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = LoadCoreIndexInput(
                index_path=str(self.test_index),
                response_format=ResponseFormat.MARKDOWN
            )
            result = await project_index_load_core(params)
            self.assertIn("# Project Index - Core", result)
            self.assertIn("**Version**: 2.1-enhanced", result)
            self.assertIn("## Statistics", result)

    async def test_load_core_index_file_not_found(self):
        """
        Test error handling when index file doesn't exist.

        AC: #13
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = LoadCoreIndexInput(
                index_path=str(Path(self.temp_dir) / "nonexistent.json")
            )
            result = await project_index_load_core(params)
            self.assertIn("Error:", result)
            self.assertIn("File not found", result)

    async def test_load_core_index_invalid_json(self):
        """
        Test error handling for corrupted JSON.

        AC: #13
        """
        bad_json_file = Path(self.temp_dir) / "bad.json"
        with open(bad_json_file, 'w') as f:
            f.write("{invalid json")

        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = LoadCoreIndexInput(index_path=str(bad_json_file))
            result = await project_index_load_core(params)
            self.assertIn("Error:", result)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestLoadModuleTool(unittest.IsolatedAsyncioTestCase):
    """Test project_index_load_module tool (AC #3)."""

    def setUp(self):
        """Create temporary test module for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_module_dir = Path(self.temp_dir) / "PROJECT_INDEX.d"
        self.test_module_dir.mkdir()

        # Create test module
        self.test_module_data = {
            "version": "2.1-enhanced",
            "module_id": "scripts",
            "files": {
                "scripts/test.py": {
                    "lang": "python",
                    "funcs": ["test_function_1", "test_function_2"]
                }
            }
        }
        with open(self.test_module_dir / "scripts.json", 'w') as f:
            json.dump(self.test_module_data, f)

        # Create core index for error messages
        self.core_index_path = Path(self.temp_dir) / "PROJECT_INDEX.json"
        core_data = {
            "modules": {
                "scripts": {"detail_path": "PROJECT_INDEX.d/scripts.json"}
            }
        }
        with open(self.core_index_path, 'w') as f:
            json.dump(core_data, f)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_load_module_json_format(self):
        """
        Test loading module in JSON format using loader utility.

        AC: #3, #11
        """
        # Patch the loader utility
        with patch('project_index_mcp.load_detail_module') as mock_load:
            mock_load.return_value = self.test_module_data

            params = LoadModuleInput(
                module_name="scripts",
                response_format=ResponseFormat.JSON
            )
            result = await project_index_load_module(params)
            data = json.loads(result)
            self.assertEqual(data["module_id"], "scripts")
            self.assertIn("files", data)

    async def test_load_module_markdown_format(self):
        """
        Test loading module in Markdown format.

        AC: #3
        """
        with patch('project_index_mcp.load_detail_module') as mock_load:
            mock_load.return_value = self.test_module_data

            params = LoadModuleInput(
                module_name="scripts",
                response_format=ResponseFormat.MARKDOWN
            )
            result = await project_index_load_module(params)
            self.assertIn("# Module: scripts", result)
            self.assertIn("scripts/test.py", result)

    async def test_load_module_not_found(self):
        """
        Test error handling when module doesn't exist.

        AC: #13
        """
        with patch('project_index_mcp.load_detail_module') as mock_load:
            mock_load.side_effect = FileNotFoundError("Module not found")
            with patch('project_index_mcp._load_json_file') as mock_core:
                mock_core.return_value = {"modules": {"scripts": {}}}

                params = LoadModuleInput(module_name="nonexistent")
                result = await project_index_load_module(params)
                self.assertIn("Error: Module 'nonexistent' not found", result)
                self.assertIn("Available modules:", result)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestSearchFilesTool(unittest.IsolatedAsyncioTestCase):
    """Test project_index_search_files tool (AC #4)."""

    def setUp(self):
        """Create temporary test index for search."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_index = Path(self.temp_dir) / "PROJECT_INDEX.json"
        self.test_data = {
            "modules": {
                "scripts": {
                    "files": [
                        "scripts/test_mcp_server.py",
                        "scripts/test_loader.py",
                        "scripts/project_index.py",
                        "scripts/mcp_detector.py"
                    ]
                },
                "docs": {
                    "files": [
                        "docs/README.md",
                        "docs/stories/2-10-mcp-server-implementation.md"
                    ]
                }
            }
        }
        with open(self.test_index, 'w') as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_search_files_basic_query(self):
        """
        Test basic file search with pagination.

        AC: #4
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = SearchFilesInput(
                query="test",
                index_path=str(self.test_index)
            )
            result = await project_index_search_files(params)
            data = json.loads(result)
            self.assertIn("files", data)
            self.assertIn("total", data)
            self.assertGreater(data["total"], 0)

    async def test_search_files_with_pagination(self):
        """
        Test file search with limit and offset.

        AC: #4
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = SearchFilesInput(
                query="scripts",
                index_path=str(self.test_index),
                limit=2,
                offset=1
            )
            result = await project_index_search_files(params)
            data = json.loads(result)
            self.assertEqual(data["limit"], 2)
            self.assertEqual(data["offset"], 1)
            self.assertLessEqual(len(data["files"]), 2)

    async def test_search_files_empty_results(self):
        """
        Test search with no matches returns helpful message.

        AC: #13
        """
        with patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            params = SearchFilesInput(
                query="nonexistent_pattern",
                index_path=str(self.test_index)
            )
            result = await project_index_search_files(params)
            self.assertIn("No files found matching", result)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestGetFileInfoTool(unittest.IsolatedAsyncioTestCase):
    """Test project_index_get_file_info tool (AC #5)."""

    def setUp(self):
        """Create temporary test index and module for file info."""
        self.temp_dir = tempfile.mkdtemp()
        self.core_index_path = Path(self.temp_dir) / "PROJECT_INDEX.json"
        core_data = {
            "modules": {
                "scripts": {
                    "detail_path": "PROJECT_INDEX.d/scripts.json",
                    "files": ["scripts/test.py"]
                }
            }
        }
        with open(self.core_index_path, 'w') as f:
            json.dump(core_data, f)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_get_file_info_json_format(self):
        """
        Test getting file info in JSON format with git metadata.

        AC: #5
        """
        mock_file_info = {
            "lang": "python",
            "funcs": ["function_1", "function_2"],
            "git": {
                "commit": "abc123",
                "author": "test@example.com",
                "date": "2025-11-03",
                "recency_days": 0
            }
        }

        with patch('project_index_mcp.load_detail_by_path') as mock_load, \
             patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            mock_load.return_value = mock_file_info

            params = GetFileInfoInput(
                file_path="scripts/test.py",
                index_path=str(self.core_index_path),
                response_format=ResponseFormat.JSON
            )
            result = await project_index_get_file_info(params)
            data = json.loads(result)
            self.assertIn("funcs", data)
            self.assertIn("git", data)

    async def test_get_file_info_markdown_format(self):
        """
        Test getting file info in Markdown format.

        AC: #5
        """
        # Mock file_info structure matches what load_detail_by_path returns
        mock_file_info = {
            "module_id": "scripts",
            "files": {
                "scripts/test.py": {
                    "language": "python",
                    "functions": [
                        {"name": "function_1", "signature": "()", "line": 10}
                    ],
                    "git": {"commit": "abc123", "author": "test@example.com"}
                }
            }
        }

        with patch('project_index_mcp.load_detail_by_path') as mock_load, \
             patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            mock_load.return_value = mock_file_info

            params = GetFileInfoInput(
                file_path="scripts/test.py",
                index_path=str(self.core_index_path),
                response_format=ResponseFormat.MARKDOWN
            )
            result = await project_index_get_file_info(params)
            self.assertIn("# File: scripts/test.py", result)
            self.assertIn("function_1", result)

    async def test_get_file_info_not_found(self):
        """
        Test error handling when file not found in index.

        AC: #13
        """
        with patch('project_index_mcp.load_detail_by_path') as mock_load, \
             patch('project_index_mcp._load_json_file') as mock_core, \
             patch('project_index_mcp._validate_path_within_project', side_effect=lambda p: p.resolve()):
            mock_load.side_effect = ValueError("File not found")
            mock_core.return_value = {"modules": {}}

            params = GetFileInfoInput(
                file_path="nonexistent.py",
                index_path=str(self.core_index_path)
            )
            result = await project_index_get_file_info(params)
            self.assertIn("Error: File 'nonexistent.py' not found", result)
            self.assertIn("Next steps:", result)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions (_load_json_file, _format_core_index_markdown, etc.)."""

    def setUp(self):
        """Create temporary test files."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_json_file_success(self):
        """Test successful JSON file loading."""
        test_file = Path(self.temp_dir) / "test.json"
        test_data = {"key": "value"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        result = _load_json_file(test_file)
        self.assertEqual(result["key"], "value")

    def test_load_json_file_not_found(self):
        """Test FileNotFoundError is raised for missing file."""
        with self.assertRaises(FileNotFoundError):
            _load_json_file(Path(self.temp_dir) / "nonexistent.json")

    def test_load_json_file_invalid_json(self):
        """Test ValueError is raised for invalid JSON."""
        test_file = Path(self.temp_dir) / "bad.json"
        with open(test_file, 'w') as f:
            f.write("{invalid json")

        with self.assertRaises(ValueError):
            _load_json_file(test_file)

    def test_format_core_index_markdown(self):
        """Test markdown formatting of core index."""
        data = {
            "version": "2.1",
            "at": "2025-11-03",
            "root": ".",
            "stats": {
                "total_files": 10,
                "total_directories": 5,
                "markdown_files": 3
            },
            "modules": {
                "scripts": {
                    "detail_path": "PROJECT_INDEX.d/scripts.json",
                    "file_count": 10,
                    "function_count": 50
                }
            }
        }

        result = _format_core_index_markdown(data)
        self.assertIn("# Project Index - Core", result)
        self.assertIn("**Version**: 2.1", result)
        self.assertIn("## Statistics", result)
        self.assertIn("Total files: 10", result)
        self.assertIn("## Available Modules", result)
        self.assertIn("### scripts", result)

    def test_handle_error_formatting(self):
        """Test error message formatting with actionable guidance."""
        error = FileNotFoundError("Test file not found")
        result = _handle_error(error, context="test_context")
        self.assertIn("Error:", result)
        self.assertIn("Next steps:", result)


@unittest.skipUnless(MCP_MODULE_AVAILABLE, f"MCP module not available: {MCP_IMPORT_ERROR if not MCP_MODULE_AVAILABLE else ''}")
class TestTypeAnnotations(unittest.TestCase):
    """Test type annotations are correctly specified (Code Review)."""

    def test_load_json_file_return_type(self):
        """Test _load_json_file has correct return type annotation."""
        import inspect
        sig = inspect.signature(_load_json_file)
        # The return annotation should be Dict[str, Any]
        self.assertIn("Dict", str(sig.return_annotation))

    def test_format_core_index_markdown_param_type(self):
        """Test _format_core_index_markdown has correct parameter type."""
        import inspect
        sig = inspect.signature(_format_core_index_markdown)
        params = sig.parameters
        # The data parameter should be Dict[str, Any]
        self.assertIn("Dict", str(params['data'].annotation))


def run_all_tests():
    """Run all test suites and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPydanticModels))
    suite.addTests(loader.loadTestsFromTestCase(TestPathTraversalValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadCoreIndexTool))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadModuleTool))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchFilesTool))
    suite.addTests(loader.loadTestsFromTestCase(TestGetFileInfoTool))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestTypeAnnotations))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
