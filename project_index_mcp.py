#!/usr/bin/env python3
'''
MCP Server for Project Index.

This server provides tools to interact with the claude-code-project-index,
enabling AI agents to navigate large codebases through lazy-loading of detail modules.
'''

from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
import json
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("project_index_mcp")

# Constants
CHARACTER_LIMIT = 25000  # Maximum response size in characters
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
        description="Maximum results to return",
        ge=1,
        le=100
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
def _load_json_file(file_path: Path) -> dict:
    '''Load and parse a JSON file.'''
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")

def _format_core_index_markdown(data: dict) -> str:
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

def _handle_error(e: Exception) -> str:
    '''Consistent error formatting across all tools.'''
    if isinstance(e, FileNotFoundError):
        return f"Error: {str(e)}. Please check the path is correct."
    elif isinstance(e, ValueError):
        return f"Error: {str(e)}"
    elif isinstance(e, json.JSONDecodeError):
        return f"Error: Invalid JSON format. {str(e)}"
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
        - Returns "Error: Module not found" if module doesn't exist
        - Returns "Error: Invalid JSON format" if module file is corrupted
    '''
    try:
        index_dir = Path(params.index_dir) if params.index_dir else DEFAULT_DETAIL_DIR
        module_path = index_dir / f"{params.module_name}.json"

        data = _load_json_file(module_path)

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"# Module: {params.module_name}", ""]
            lines.append(f"**Version**: {data.get('version', 'unknown')}")
            lines.append("")

            if 'files' in data:
                lines.append("## Files")
                for file_path, file_info in data['files'].items():
                    lines.append(f"### {file_path}")
                    lines.append(f"- Language: {file_info.get('lang', 'unknown')}")

                    if 'funcs' in file_info:
                        lines.append(f"- Functions: {len(file_info['funcs'])}")
                        for func in file_info['funcs'][:5]:  # Show first 5
                            lines.append(f"  - `{func}`")
                        if len(file_info['funcs']) > 5:
                            lines.append(f"  - ... and {len(file_info['funcs']) - 5} more")
                    lines.append("")

            return "\n".join(lines)
        else:
            return json.dumps(data, indent=2)

    except Exception as e:
        return _handle_error(e)

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
    '''Search for files in the project index by path pattern.

    This tool searches the core index for files matching a query string.
    Supports partial matches and wildcards to find relevant files quickly.

    Args:
        params (SearchFilesInput): Validated input parameters containing:
            - query (str): Search string (e.g., "login", "*.py", "src/auth")
            - index_path (Optional[str]): Path to PROJECT_INDEX.json (default: ./PROJECT_INDEX.json)
            - limit (Optional[int]): Maximum results (default: 20, max: 100)

    Returns:
        str: JSON formatted search results containing:
            - query: The search query
            - total: Total matches found
            - count: Number of results in this response
            - files: List of matching file paths with basic info

    Examples:
        - Use when: "Find all Python files related to authentication"
        - Use when: "Search for files with 'index' in the name"
        - Use when: "Locate the project_index.py file"
        - Don't use when: You need function-level search (load module first)

    Error Handling:
        - Returns empty results if no matches found
        - Returns "Error: File not found" if index doesn't exist
    '''
    try:
        index_path = Path(params.index_path) if params.index_path else DEFAULT_INDEX_PATH
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

        # Limit results
        limited_matches = matches[:params.limit]

        result = {
            "query": params.query,
            "total": len(matches),
            "count": len(limited_matches),
            "files": limited_matches,
            "has_more": len(matches) > params.limit
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return _handle_error(e)

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
    '''Get detailed information about a specific file from the index.

    This tool retrieves comprehensive information about a file including
    functions, classes, imports, and git metadata if available.

    Args:
        params (GetFileInfoInput): Validated input parameters containing:
            - file_path (str): File path (e.g., 'scripts/project_index.py')
            - index_path (Optional[str]): Path to PROJECT_INDEX.json (default: ./PROJECT_INDEX.json)
            - response_format (ResponseFormat): Output format (default: markdown)

    Returns:
        str: JSON or Markdown formatted file information containing:
            - file_path: The file path
            - language: Programming language
            - functions: List of functions with signatures
            - imports: Import statements
            - git_metadata: Commit info, author, date (if available)

    Examples:
        - Use when: "Show me details about project_index.py"
        - Use when: "What functions are in the auth/login.py file?"
        - Use when: "Get git information for a specific file"
        - Don't use when: You want to search multiple files (use project_index_search_files)

    Error Handling:
        - Returns "Error: File not found in index" if file doesn't exist
        - Returns partial info if some metadata is missing
    '''
    try:
        index_path = Path(params.index_path) if params.index_path else DEFAULT_INDEX_PATH
        data = _load_json_file(index_path)

        file_path = params.file_path
        file_info = {}

        # Look in 'f' section
        if 'f' in data and file_path in data['f']:
            file_info = data['f'][file_path]

        # Also check git metadata if available
        if 'git_metadata' in data and file_path in data['git_metadata']:
            file_info['git_metadata'] = data['git_metadata'][file_path]

        if not file_info:
            return f"Error: File '{file_path}' not found in index"

        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"# File: {file_path}", ""]
            lines.append(f"**Language**: {file_info.get('lang', 'unknown')}")
            lines.append("")

            if 'funcs' in file_info:
                lines.append("## Functions")
                for func in file_info['funcs']:
                    lines.append(f"- `{func}`")
                lines.append("")

            if 'imports' in file_info:
                lines.append("## Imports")
                for imp in file_info['imports']:
                    lines.append(f"- `{imp}`")
                lines.append("")

            if 'git_metadata' in file_info:
                git_meta = file_info['git_metadata']
                lines.append("## Git Metadata")
                lines.append(f"- Last commit: {git_meta.get('commit', 'N/A')}")
                lines.append(f"- Author: {git_meta.get('author', 'N/A')}")
                lines.append(f"- Date: {git_meta.get('date', 'N/A')}")
                lines.append("")

            return "\n".join(lines)
        else:
            return json.dumps({"file_path": file_path, **file_info}, indent=2)

    except Exception as e:
        return _handle_error(e)

if __name__ == "__main__":
    mcp.run()
