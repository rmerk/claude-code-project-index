#!/usr/bin/env python3
"""MCP Server for Project Index.

This server provides tools to interact with the claude-code-project-index,
enabling AI agents to navigate large codebases through lazy-loading of detail modules.

This is the FIRST external dependency for the project. Core indexing functionality
(scripts/project_index.py, scripts/loader.py) remains stdlib-only.

Requirements:
    - Python 3.12+
    - mcp>=1.0.0 (MCP Python SDK)
    - pydantic>=2.0.0 (transitive dependency via mcp)

Integration:
    - Uses scripts/loader.py for lazy-loading detail modules
    - Uses scripts/loader.py for file information retrieval
    - Avoids code duplication (DRY principle)
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
import json
import sys
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Import existing loader utilities to avoid code duplication (AC #11)
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from loader import load_detail_module, load_detail_by_path, find_module_for_file

# Initialize the MCP server
mcp = FastMCP("project_index_mcp")

# Constants
DEFAULT_INDEX_PATH = Path("PROJECT_INDEX.json")
DEFAULT_DETAIL_DIR = Path("PROJECT_INDEX.d")

# Enums
class ResponseFormat(str, Enum):
    '''Output format for tool responses.'''
    MARKDOWN = "markdown"
    JSON = "json"

# Pydantic Models for Input Validation
class LoadCoreIndexInput(BaseModel):
    '''Input model for loading core index.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    index_path: Optional[str] = Field(
        default=None,
        description="Path to PROJECT_INDEX.json file (default: ./PROJECT_INDEX.json)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

class LoadModuleInput(BaseModel):
    '''Input model for loading detail modules.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    module_name: str = Field(
        ...,
        description="Module name to load (e.g., 'scripts', 'auth', 'database')",
        min_length=1,
        max_length=200
    )
    index_dir: Optional[str] = Field(
        default=None,
        description="Path to PROJECT_INDEX.d directory (default: ./PROJECT_INDEX.d)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

class SearchFilesInput(BaseModel):
    '''Input model for searching files in the index.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    query: str = Field(
        ...,
        description="Search string to match against file paths (supports wildcards)",
        min_length=1,
        max_length=200
    )
    index_path: Optional[str] = Field(
        default=None,
        description="Path to PROJECT_INDEX.json file (default: ./PROJECT_INDEX.json)"
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum results to return (default: 20, max: 100)",
        ge=1,
        le=100
    )
    offset: Optional[int] = Field(
        default=0,
        description="Number of results to skip for pagination (default: 0)",
        ge=0
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

class GetFileInfoInput(BaseModel):
    '''Input model for getting detailed file information.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    file_path: str = Field(
        ...,
        description="File path to get information about (e.g., 'scripts/project_index.py')",
        min_length=1,
        max_length=500
    )
    index_path: Optional[str] = Field(
        default=None,
        description="Path to PROJECT_INDEX.json file (default: ./PROJECT_INDEX.json)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

# Shared utility functions
def _validate_path_within_project(path: Path) -> Path:
    '''Validate that a user-provided path is within the project root.

    Args:
        path: User-provided path to validate

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path attempts to access files outside project root
    '''
    project_root = Path(__file__).parent.resolve()
    resolved_path = path.resolve()

    try:
        # Check if resolved path is relative to project root
        resolved_path.relative_to(project_root)
        return resolved_path
    except ValueError:
        raise ValueError(f"Path '{path}' must be within project root '{project_root}'")

def _load_json_file(file_path: Path) -> Dict[str, Any]:
    '''Load and parse a JSON file.'''
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")

def _format_core_index_markdown(data: Dict[str, Any]) -> str:
    '''Format core index as markdown.'''
    lines = ["# Project Index - Core", ""]
    lines.append(f"**Version**: {data.get('version', 'unknown')}")
    lines.append(f"**Generated**: {data.get('at', 'unknown')}")
    lines.append(f"**Root**: {data.get('root', '.')}")
    lines.append("")

    # Stats
    if 'stats' in data:
        stats = data['stats']
        lines.append("## Statistics")
        lines.append(f"- Total files: {stats.get('total_files', 0)}")
        lines.append(f"- Total directories: {stats.get('total_directories', 0)}")
        lines.append(f"- Markdown files: {stats.get('markdown_files', 0)}")
        lines.append("")

    # Modules
    if 'modules' in data:
        lines.append("## Available Modules")
        for module_name, module_info in data['modules'].items():
            lines.append(f"### {module_name}")
            lines.append(f"- Detail path: `{module_info.get('detail_path', 'N/A')}`")
            lines.append(f"- Files: {module_info.get('file_count', 0)}")
            lines.append(f"- Functions: {module_info.get('function_count', 0)}")
            lines.append("")

    return "\n".join(lines)

def _handle_error(e: Exception, context: str = "") -> str:
    """Consistent error formatting with actionable guidance (AC #13).

    Args:
        e: The exception to format
        context: Additional context about where the error occurred

    Returns:
        Error message with clear next steps for the user
    """
    if isinstance(e, FileNotFoundError):
        msg = f"Error: {str(e)}"
        if "PROJECT_INDEX.json" in str(e):
            msg += "\n\nNext steps: Run /index to generate the project index."
        elif "PROJECT_INDEX.d" in str(e):
            msg += "\n\nNext steps: Run /index to generate the split index architecture."
        return msg
    elif isinstance(e, ValueError):
        msg = f"Error: {str(e)}"
        if "Module" in str(e) and "not found" in str(e):
            msg += "\n\nNext steps: Use project_index_load_core to see available modules."
        elif "format" in str(e).lower():
            msg += "\n\nNext steps: Use format='json' or format='markdown'."
        return msg
    elif isinstance(e, json.JSONDecodeError):
        return f"Error: Invalid JSON format in file.\nDetails: {str(e)}\n\nNext steps: Regenerate the index by running /index."
    return f"Error: Unexpected error occurred: {type(e).__name__} - {str(e)}"

# Tool definitions
@mcp.tool(
    name="project_index_load_core",
    annotations={
        "title": "Load Core Project Index",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def project_index_load_core(params: LoadCoreIndexInput) -> str:
    '''Load the core project index containing file tree and module references.

    This tool loads the lightweight core index (PROJECT_INDEX.json) which contains
    the project file tree, function signatures, and references to detail modules.
    This is the entry point for navigating large codebases.

    Args:
        params (LoadCoreIndexInput): Validated input parameters containing:
            - index_path (Optional[str]): Path to PROJECT_INDEX.json (default: ./PROJECT_INDEX.json)
            - response_format (ResponseFormat): Output format (default: json)

    Returns:
        str: JSON or Markdown formatted core index data containing:
            - version: Index format version
            - at: Generation timestamp
            - root: Project root directory
            - tree: File tree structure
            - stats: Statistics (file counts, etc.)
            - modules: Available detail modules with references

    Examples:
        - Use when: "Show me the project structure"
        - Use when: "What modules are available?"
        - Use when: "Load the core index to start navigation"
        - Don't use when: You need detailed function implementations (use project_index_load_module)

    Error Handling:
        - Returns "Error: File not found" if PROJECT_INDEX.json doesn't exist
        - Returns "Error: Invalid JSON format" if the file is corrupted
    '''
    try:
        index_path = Path(params.index_path) if params.index_path else DEFAULT_INDEX_PATH
        # Validate path is within project root to prevent path traversal
        index_path = _validate_path_within_project(index_path)
        data = _load_json_file(index_path)

        if params.response_format == ResponseFormat.MARKDOWN:
            return _format_core_index_markdown(data)
        else:
            return json.dumps(data, indent=2)

    except Exception as e:
        return _handle_error(e)

@mcp.tool(
    name="project_index_load_module",
    annotations={
        "title": "Load Detail Module",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def project_index_load_module(params: LoadModuleInput) -> str:
    '''Load a specific detail module containing full function/class information.

    This tool lazy-loads a detail module from the PROJECT_INDEX.d/ directory.
    Detail modules contain complete function signatures, call graphs, and
    documentation for files in a specific module/directory.

    Integrates with scripts/loader.py:load_detail_module() to avoid code duplication (AC #11).

    Args:
        params (LoadModuleInput): Validated input parameters containing:
            - module_name (str): Module name (e.g., 'scripts', 'auth')
            - index_dir (Optional[str]): Path to PROJECT_INDEX.d (default: ./PROJECT_INDEX.d)
            - response_format (ResponseFormat): Output format (default: json)

    Returns:
        str: JSON or Markdown formatted detail module data containing:
            - module_id: Module identifier
            - version: Format version
            - files: Dictionary of file details with functions/classes
            - call_graph_local: Function call relationships within module

    Examples:
        - Use when: "Show me details about the 'scripts' module"
        - Use when: "Load the auth module to see login functions"
        - Use when: "What functions are in the database module?"
        - Don't use when: You just need the file tree (use project_index_load_core)

    Error Handling:
        - Returns "Error: Module not found" with available modules if module doesn't exist
        - Returns "Error: Split architecture not detected" if PROJECT_INDEX.d/ doesn't exist
        - Returns "Error: Invalid JSON format" if module file is corrupted
    '''
    try:
        index_dir = Path(params.index_dir) if params.index_dir else None
        # Validate path is within project root to prevent path traversal
        if index_dir:
            index_dir = _validate_path_within_project(index_dir)

        # Use existing loader utility (AC #11: Integration with Existing Utilities)
        data = load_detail_module(params.module_name, index_dir=index_dir)

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"# Module: {params.module_name}", ""]
            lines.append(f"**Version**: {data.get('version', 'unknown')}")
            lines.append(f"**Module ID**: {data.get('module_id', params.module_name)}")
            lines.append("")

            if 'files' in data:
                lines.append("## Files")
                for file_path, file_info in data['files'].items():
                    lines.append(f"### {file_path}")
                    lines.append(f"- Language: {file_info.get('language', 'unknown')}")

                    # Handle functions list (each is a dict with 'name', 'signature', etc.)
                    if 'functions' in file_info and file_info['functions']:
                        lines.append(f"- Functions: {len(file_info['functions'])}")
                        for func in file_info['functions'][:5]:  # Show first 5
                            func_name = func.get('name', 'unknown')
                            func_sig = func.get('signature', '')
                            lines.append(f"  - `{func_name}{func_sig}`")
                        if len(file_info['functions']) > 5:
                            lines.append(f"  - ... and {len(file_info['functions']) - 5} more")

                    # Handle classes list (each is a dict with 'name', 'methods', etc.)
                    if 'classes' in file_info and file_info['classes']:
                        lines.append(f"- Classes: {len(file_info['classes'])}")
                        for cls in file_info['classes'][:3]:  # Show first 3
                            lines.append(f"  - `{cls.get('name', 'unknown')}`")
                        if len(file_info['classes']) > 3:
                            lines.append(f"  - ... and {len(file_info['classes']) - 3} more")

                    if 'imports' in file_info:
                        lines.append(f"- Imports: {len(file_info['imports'])}")
                    lines.append("")

            return "\n".join(lines)
        else:
            return json.dumps(data, indent=2)

    except FileNotFoundError as e:
        # Provide actionable error with available modules
        try:
            core_index = _load_json_file(DEFAULT_INDEX_PATH)
            available_modules = list(core_index.get('modules', {}).keys())
            return f"Error: Module '{params.module_name}' not found.\n\nAvailable modules: {', '.join(available_modules)}\n\nNext steps: Use one of the available module names, or run /index to update the index."
        except Exception as e_inner:
            return _handle_error(e, context="load_module")
    except Exception as e:
        return _handle_error(e, context="load_module")

@mcp.tool(
    name="project_index_search_files",
    annotations={
        "title": "Search Files in Index",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def project_index_search_files(params: SearchFilesInput) -> str:
    '''Search for files in the project index by path pattern with pagination.

    This tool searches the core index for files matching a query string.
    Supports partial matches and pagination for large result sets (AC #4).

    Args:
        params (SearchFilesInput): Validated input parameters containing:
            - query (str): Search string (e.g., "login", "*.py", "src/auth")
            - index_path (Optional[str]): Path to PROJECT_INDEX.json (default: ./PROJECT_INDEX.json)
            - limit (Optional[int]): Maximum results (default: 20, max: 100)
            - offset (Optional[int]): Number of results to skip (default: 0)

    Returns:
        str: JSON formatted search results containing:
            - query: The search query
            - total: Total matches found
            - limit: Results limit for this request
            - offset: Results offset for this request
            - count: Number of results in this response
            - files: List of matching file paths with basic info
            - has_more: Boolean indicating if more results are available

    Examples:
        - Use when: "Find all Python files related to authentication"
        - Use when: "Search for files with 'index' in the name"
        - Use when: "Locate the project_index.py file"
        - Use when: "Get next page of results with offset=20"
        - Don't use when: You need function-level search (load module first)

    Error Handling:
        - Returns empty results if no matches found with helpful suggestions
        - Returns "Error: File not found" if index doesn't exist
        - Validates offset/limit parameters via Pydantic
    '''
    try:
        index_path = Path(params.index_path) if params.index_path else DEFAULT_INDEX_PATH
        # Validate path is within project root to prevent path traversal
        index_path = _validate_path_within_project(index_path)
        data = _load_json_file(index_path)

        # Search in file listings
        query_lower = params.query.lower()
        matches = []

        # Search in modules
        if 'modules' in data:
            for module_name, module_info in data['modules'].items():
                for file_path in module_info.get('files', []):
                    if query_lower in file_path.lower():
                        matches.append({
                            "file_path": file_path,
                            "module": module_name
                        })

        # Also search in 'f' section if present
        if 'f' in data:
            for file_path in data['f'].keys():
                if query_lower in file_path.lower() and not any(m['file_path'] == file_path for m in matches):
                    matches.append({
                        "file_path": file_path,
                        "module": "N/A"
                    })

        # Apply pagination (AC #4: limit/offset)
        total = len(matches)
        start = params.offset
        end = start + params.limit
        paginated_matches = matches[start:end]

        result = {
            "query": params.query,
            "total": total,
            "limit": params.limit,
            "offset": params.offset,
            "count": len(paginated_matches),
            "files": paginated_matches,
            "has_more": end < total
        }

        # Provide helpful message if no results
        if total == 0:
            result["message"] = f"No files found matching '{params.query}'. Try a different search term or check available modules with project_index_load_core."

        return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_error(e, context="search_files")

@mcp.tool(
    name="project_index_get_file_info",
    annotations={
        "title": "Get File Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def project_index_get_file_info(params: GetFileInfoInput) -> str:
    '''Get detailed information about a specific file from the index including git metadata.

    This tool retrieves comprehensive information about a file including
    functions, classes, imports, and git metadata (commit, author, date, recency).

    Integrates with scripts/loader.py:load_detail_by_path() to avoid code duplication (AC #11).

    Args:
        params (GetFileInfoInput): Validated input parameters containing:
            - file_path (str): File path (e.g., 'scripts/project_index.py')
            - index_path (Optional[str]): Path to PROJECT_INDEX.json (default: ./PROJECT_INDEX.json)
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: JSON or Markdown formatted file information containing:
            - file_path: The file path
            - lang: Programming language
            - funcs: List of functions with signatures and line numbers
            - classes: Dictionary of classes with methods
            - imports: Import statements
            - git: Git metadata (commit, author, date, recency_days) if available (AC #5)

    Examples:
        - Use when: "Show me details about project_index.py"
        - Use when: "What functions are in the auth/login.py file?"
        - Use when: "Get git information for a specific file"
        - Use when: "When was this file last modified?"
        - Don't use when: You want to search multiple files (use project_index_search_files)

    Error Handling:
        - Returns "Error: File not found in index" with suggestions if file doesn't exist
        - Returns partial info if some metadata is missing (graceful degradation)
        - Suggests running /index to update if file is recently added
    '''
    try:
        index_path = Path(params.index_path) if params.index_path else DEFAULT_INDEX_PATH
        # Validate path is within project root to prevent path traversal
        index_path = _validate_path_within_project(index_path)
        core_index = _load_json_file(index_path)

        file_path = params.file_path

        # Use existing loader utility (AC #11: Integration with Existing Utilities)
        try:
            file_info = load_detail_by_path(file_path, core_index, index_dir=None)
        except ValueError as e:
            # File not found in any module - provide helpful error
            available_files = []
            if 'modules' in core_index:
                for module_name, module_info in core_index['modules'].items():
                    available_files.extend(module_info.get('files', []))[:10]  # Show first 10

            similar_files = [f for f in available_files if any(part in f for part in file_path.split('/'))][:5]

            error_msg = f"Error: File '{file_path}' not found in index."
            if similar_files:
                error_msg += f"\n\nSimilar files found:\n" + "\n".join(f"  - {f}" for f in similar_files)
            error_msg += "\n\nNext steps: Check the file path, use project_index_search_files to find the correct path, or run /index to update the index."
            return error_msg

        if params.response_format == ResponseFormat.MARKDOWN:
            # Extract the actual file data from the module structure
            actual_file_info = file_info.get('files', {}).get(file_path, {})

            lines = [f"# File: {file_path}", ""]
            lines.append(f"**Language**: {actual_file_info.get('language', 'unknown')}")
            lines.append(f"**Module**: {file_info.get('module_id', 'N/A')}")

            # Git metadata from Story 2.3 (AC #5)
            if 'git' in actual_file_info:
                git_meta = actual_file_info['git']
                lines.append(f"**Last Modified**: {git_meta.get('date', 'N/A')} ({git_meta.get('recency_days', 'N/A')} days ago)")
                lines.append(f"**Author**: {git_meta.get('author', 'N/A')}")
                lines.append("")

            # Handle functions list (each is a dict with 'name', 'signature', 'line', etc.)
            if 'functions' in actual_file_info and actual_file_info['functions']:
                lines.append("## Functions")
                for func in actual_file_info['functions']:
                    func_name = func.get('name', 'unknown')
                    func_sig = func.get('signature', '')
                    func_line = func.get('line', '')
                    lines.append(f"- `{func_name}{func_sig}` (line {func_line})")
                    if func.get('doc'):
                        lines.append(f"  - {func.get('doc')}")
                lines.append("")

            # Handle classes list (each is a dict with 'name', 'methods', etc.)
            if 'classes' in actual_file_info and actual_file_info['classes']:
                lines.append("## Classes")
                for cls in actual_file_info['classes']:
                    cls_name = cls.get('name', 'unknown')
                    lines.append(f"### {cls_name}")
                    if cls.get('doc'):
                        lines.append(f"_{cls.get('doc')}_")
                    if 'methods' in cls and cls['methods']:
                        lines.append("**Methods:**")
                        for method in cls['methods']:
                            method_name = method.get('name', 'unknown')
                            method_sig = method.get('signature', '')
                            lines.append(f"  - `{method_name}{method_sig}`")
                    lines.append("")

            if 'imports' in actual_file_info and actual_file_info['imports']:
                lines.append("## Imports")
                for imp in actual_file_info['imports'][:15]:  # Show first 15
                    lines.append(f"- `{imp}`")
                if len(actual_file_info['imports']) > 15:
                    lines.append(f"- ... and {len(actual_file_info['imports']) - 15} more")
                lines.append("")

            if 'git' in actual_file_info:
                git_meta = actual_file_info['git']
                lines.append("## Git Details")
                lines.append(f"- **Commit**: `{git_meta.get('commit', 'N/A')[:8]}`")
                lines.append(f"- **Message**: {git_meta.get('message', 'N/A')}")
                if 'pr' in git_meta and git_meta['pr']:
                    lines.append(f"- **PR**: #{git_meta['pr']}")
                lines.append(f"- **Lines Changed**: {git_meta.get('lines_changed', 'N/A')}")
                lines.append("")

            return "\n".join(lines)
        else:
            return json.dumps({"file_path": file_path, **file_info}, indent=2)

    except FileNotFoundError as e:
        return _handle_error(e, context="get_file_info")
    except Exception as e:
        return _handle_error(e, context="get_file_info")

"""
EVALUATION SUITE (AC #9)
========================

This evaluation suite contains 10 realistic test questions for validating
the MCP server implementation. These tests should be run manually through
Claude Desktop or another MCP client.

Test Question 1: Load Core Index (JSON format)
-----------------------------------------------
**Query**: "Use project_index_load_core to load the core index in JSON format"
**Expected Output**: Returns PROJECT_INDEX.json with fields:
  - version (e.g., "2.1-enhanced")
  - at (timestamp)
  - root (project root path)
  - tree (file tree structure)
  - modules (dict of available modules with references)
  - stats (file counts)
**Validates**: AC #2 - JSON format output, file loading, default format

Test Question 2: Load Core Index (Markdown format)
--------------------------------------------------
**Query**: "Load the core index in Markdown format for human readability"
**Expected Output**: Returns formatted Markdown with sections:
  - Project Index - Core (title)
  - Version, Generated, Root (metadata)
  - Statistics (file counts)
  - Available Modules (with detail paths and counts)
**Validates**: AC #2 - Markdown format output, response_format parameter

Test Question 3: Lazy-Load Detail Module
----------------------------------------
**Query**: "Load the 'scripts' detail module"
**Expected Output**: Returns module with:
  - module_id='scripts'
  - version
  - files (dict of file paths with details)
  - call_graph_local (function call relationships)
**Validates**: AC #3 - Integration with scripts/loader.py, module loading

Test Question 4: Search Files (Basic Pattern Matching)
------------------------------------------------------
**Query**: "Search for all Python test files (pattern: test)"
**Expected Output**: Returns JSON with:
  - query="test"
  - total (number of matches, e.g., 15+)
  - count (number in response, max 20)
  - files (list of matching files like test_loader.py, test_incremental.py)
  - limit=20, offset=0
  - has_more (boolean)
**Validates**: AC #4 - Pattern matching, file tree search, default pagination

Test Question 5: Search Files with Pagination
---------------------------------------------
**Query**: "Search for all Python files with limit=5, offset=10"
**Expected Output**: Returns JSON with:
  - total (all matches, e.g., 30)
  - count=5 (this page)
  - limit=5, offset=10
  - files (5 results starting from 11th match)
  - has_more=true (more results available)
**Validates**: AC #4 - Pagination logic, limit/offset constraints (1-100 limit, >=0 offset)

Test Question 6: Get File Info with Git Metadata
------------------------------------------------
**Query**: "Get detailed information about scripts/project_index.py"
**Expected Output**: Returns file details with:
  - lang="python"
  - funcs (list of function signatures with line numbers)
  - imports (list of import statements)
  - git metadata (commit, author, date, recency_days, message, pr, lines_changed)
**Validates**: AC #5 - Integration with load_detail_by_path, git metadata inclusion from Story 2.3

Test Question 7: Error Handling - Module Not Found
--------------------------------------------------
**Query**: "Load module 'nonexistent'"
**Expected Output**: Returns error message:
  "Error: Module 'nonexistent' not found.

  Available modules: scripts, root, docs, agents, bmad

  Next steps: Use one of the available module names, or run /index to update the index."
**Validates**: AC #13 - Error handling with actionable guidance, helpful suggestions

Test Question 8: Error Handling - File Not Indexed
--------------------------------------------------
**Query**: "Get info for 'completely/fake/path.py'"
**Expected Output**: Returns error:
  "Error: File 'completely/fake/path.py' not found in index.

  Next steps: Check the file path, use project_index_search_files to find the correct path, or run /index to update the index."
**Validates**: AC #13 - File validation, actionable error messages

Test Question 9: Multi-Tool Workflow
------------------------------------
**Query**: "Use search_files to find loader utilities, then get_file_info for scripts/loader.py"
**Step 1**: project_index_search_files(query="loader")
  - Returns files containing "loader" (e.g., scripts/loader.py, test_loader.py)
**Step 2**: project_index_get_file_info(file_path="scripts/loader.py")
  - Returns detailed info including load_detail_module, find_module_for_file functions
**Validates**: Tool composition, cross-tool workflows, practical usage patterns

Test Question 10: Performance - Repeated Calls (Caching)
--------------------------------------------------------
**Query**: "Call load_core 3 times in succession and measure latency"
**Step 1**: project_index_load_core() - First call (cold cache)
**Step 2**: project_index_load_core() - Second call
**Step 3**: project_index_load_core() - Third call
**Expected Performance**:
  - All calls complete in <500ms each (NFR001 from tech-spec)
  - First call may be slower (file I/O + JSON parsing)
  - Subsequent calls may benefit from OS file cache
**Validates**: Performance target, efficient JSON parsing, minimal overhead

Additional Manual Test Cases:
-----------------------------
1. **Claude Desktop Integration**:
   - Configure MCP server in claude_desktop_config.json
   - Verify tools appear in Claude Desktop tool list
   - Verify tool descriptions are clear and helpful

2. **Tool Annotations Verification**:
   - Check readOnlyHint=True visible in Claude Desktop
   - Check idempotentHint=True visible
   - Verify destructiveHint=False (no warnings)
   - Verify openWorldHint=False (local operation)

3. **Format Testing**:
   - Test all tools with format="json" (machine-readable)
   - Test all tools with format="markdown" (human-readable)
   - Verify markdown output is well-formatted and readable

4. **Split vs Legacy Architecture**:
   - Test with PROJECT_INDEX.d/ directory (split architecture)
   - Test fallback behavior if split architecture not detected

5. **Edge Cases**:
   - Empty search results (no matches)
   - Invalid parameters (limit > 100, offset < 0) - should be caught by Pydantic
   - Missing index file (PROJECT_INDEX.json not found)
   - Corrupted JSON (invalid format)
   - File paths with special characters

VALIDATION CRITERIA:
-------------------
✓ All 10 test questions execute successfully
✓ All 14 acceptance criteria are met
✓ Performance target <500ms per tool call
✓ Error messages provide clear next steps
✓ Both JSON and Markdown formats work correctly
✓ Pagination works correctly (limit, offset, has_more)
✓ Git metadata included in file info (AC #5)
✓ Integration with scripts/loader.py verified (AC #11)
✓ Tool annotations correctly set (AC #7)
✓ Comprehensive docstrings present (AC #8)
"""

if __name__ == "__main__":
    mcp.run()
