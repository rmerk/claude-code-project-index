"""
Lazy-loading interface for PROJECT_INDEX detail modules.

This module provides functions to load detail modules on-demand, enabling
AI agents to request only relevant code sections based on user queries.

Performance target: <500ms latency per module request (NFR001)
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging
import warnings

# Configure logging
logger = logging.getLogger(__name__)


def load_detail_module(module_name: str, index_dir: Optional[Path] = None) -> Dict:
    """
    Load detail module by name.

    Args:
        module_name: Module identifier (e.g., "scripts", "auth", "database")
        index_dir: Optional custom directory (default: PROJECT_INDEX.d/)

    Returns:
        Detail module JSON content with structure:
        {
            "module_id": str,
            "version": "2.0-split",
            "files": {...},
            "call_graph_local": [[...]],
            "doc_standard": {},
            "doc_archive": {}
        }

    Raises:
        FileNotFoundError: Module not found in PROJECT_INDEX.d/
        json.JSONDecodeError: Invalid JSON in detail module file
        ValueError: Invalid module_name format or missing required fields

    Example:
        >>> module = load_detail_module("scripts")
        >>> print(module["module_id"])
        'scripts'
        >>> print(module["version"])
        '2.0-split'
    """
    # Validate module_name format (alphanumeric + hyphen/underscore)
    if not module_name:
        raise ValueError(
            "Invalid module_name format: module_name cannot be empty"
        )

    # Allow alphanumeric, hyphen, underscore
    if not all(c.isalnum() or c in '-_' for c in module_name):
        raise ValueError(
            f"Invalid module_name format: '{module_name}'. "
            "Only alphanumeric characters, hyphens, and underscores are allowed."
        )

    # Default to PROJECT_INDEX.d/ in current working directory
    if index_dir is None:
        index_dir = Path.cwd() / "PROJECT_INDEX.d"
    elif isinstance(index_dir, str):
        index_dir = Path(index_dir)

    # Construct path to detail module file
    module_path = index_dir / f"{module_name}.json"

    # Check if file exists
    if not module_path.exists():
        raise FileNotFoundError(
            f"Module '{module_name}' not found in PROJECT_INDEX.d/\n"
            f"Expected path: {module_path}"
        )

    # Load and parse JSON
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            module_data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in detail module '{module_name}': {e.msg}",
            e.doc,
            e.pos
        )

    # Validate JSON structure (check for required fields)
    required_fields = ["module_id", "version", "files"]
    missing_fields = [field for field in required_fields if field not in module_data]

    if missing_fields:
        raise ValueError(
            f"Detail module '{module_name}' missing required fields: {missing_fields}\n"
            f"Expected fields: {required_fields}"
        )

    return module_data


def find_module_for_file(file_path: str, core_index: Dict) -> str:
    """
    Find module containing specific file.

    Searches the core index's module mappings to determine which module
    contains the given file path. Uses O(1) file_to_module_map lookup
    when available (Story 4.3), with fallback to linear search for
    backward compatibility.

    Args:
        file_path: File path to search for (e.g., "scripts/project_index.py")
        core_index: Core index with module mappings (must contain "modules" key)

    Returns:
        Module ID containing the file

    Raises:
        ValueError: File not found in any module, or invalid core_index structure
        TypeError: Invalid input types

    Example:
        >>> core_index = {"modules": {"scripts": {"files": ["scripts/loader.py"]}}}
        >>> module_id = find_module_for_file("scripts/loader.py", core_index)
        >>> print(module_id)
        'scripts'
    """
    # Type validation
    if not isinstance(file_path, str):
        raise TypeError(f"file_path must be str, got {type(file_path).__name__}")

    if not isinstance(core_index, dict):
        raise TypeError(f"core_index must be dict, got {type(core_index).__name__}")

    # Support both split-format (v2.0) and legacy format (v1.0)
    # Split format: {"version": "2.0-split", "modules": {...}}
    # Legacy format: {"f": {...}, "version": "1.0" or no version}

    if "modules" in core_index:
        # Split-format (v2.0-split) - Story 1.2
        modules = core_index["modules"]
    elif "f" in core_index:
        # Legacy format - convert on-the-fly to module-like structure
        # In legacy format, we don't have explicit module groupings
        # Raise error with helpful message
        raise ValueError(
            "Core index is in legacy format (v1.0) which doesn't support module lookups.\n"
            "Please regenerate the index with split format using: python3 scripts/project_index.py --split\n"
            "Or use Story 1.6 (Backward Compatibility) to auto-migrate."
        )
    else:
        raise ValueError(
            "Invalid core_index structure: missing both 'modules' and 'f' keys\n"
            "Expected split format: {\"version\": \"2.0-split\", \"modules\": {...}}\n"
            "Or legacy format: {\"f\": {...}}"
        )

    if not isinstance(modules, dict):
        raise ValueError("Invalid core_index structure: 'modules' must be a dict")

    # Normalize file_path for comparison (remove leading ./ if present)
    normalized_path = file_path.lstrip('./')

    # Strategy A (Story 4.3): Try O(1) lookup via file_to_module_map first
    if "file_to_module_map" in core_index:
        file_map = core_index["file_to_module_map"]
        if isinstance(file_map, dict):
            # Try direct lookup
            if normalized_path in file_map:
                return file_map[normalized_path]

            # Try with original path if different
            if file_path != normalized_path and file_path in file_map:
                return file_map[file_path]

    # Fallback (backward compatibility): Linear search through all modules
    for module_id, module_info in modules.items():
        if not isinstance(module_info, dict):
            logger.warning(f"Skipping invalid module entry: {module_id}")
            continue

        if "files" not in module_info:
            logger.warning(f"Module '{module_id}' missing 'files' key")
            continue

        module_files = module_info["files"]

        # Handle both list and dict formats for files
        if isinstance(module_files, list):
            # Normalize paths in list for comparison
            normalized_files = [f.lstrip('./') for f in module_files]
            if normalized_path in normalized_files:
                return module_id
        elif isinstance(module_files, dict):
            # Keys are the file paths
            normalized_files = [f.lstrip('./') for f in module_files.keys()]
            if normalized_path in normalized_files:
                return module_id

    # File not found in any module
    raise ValueError(
        f"File '{file_path}' not found in core index modules\n"
        f"Searched {len(modules)} module(s): {list(modules.keys())}"
    )


def load_detail_by_path(
    file_path: str,
    core_index: Dict,
    index_dir: Optional[Path] = None
) -> Dict:
    """
    Load detail module containing specific file.

    First resolves which module contains the file using the core index,
    then loads that module's detail file.

    Args:
        file_path: File path (e.g., "scripts/project_index.py")
        core_index: Core index with module mappings
        index_dir: Optional custom directory (default: PROJECT_INDEX.d/)

    Returns:
        Detail module JSON content

    Raises:
        ValueError: File not found in any module
        FileNotFoundError: Module file not found
        json.JSONDecodeError: Invalid JSON in module file

    Example:
        >>> import json
        >>> core = json.load(open("PROJECT_INDEX.json"))
        >>> module = load_detail_by_path("scripts/project_index.py", core)
        >>> print(module["module_id"])
        'scripts'
    """
    # Find which module contains this file
    module_id = find_module_for_file(file_path, core_index)

    # Load the detail module
    return load_detail_module(module_id, index_dir)


def load_multiple_modules(
    module_names: List[str],
    index_dir: Optional[Path] = None
) -> Dict[str, Dict]:
    """
    Batch load multiple detail modules.

    Loads modules sequentially and handles partial failures gracefully.
    Missing modules are skipped with a warning, allowing the batch operation
    to complete successfully for valid modules.

    Args:
        module_names: List of module identifiers
        index_dir: Optional custom directory (default: PROJECT_INDEX.d/)

    Returns:
        Dict mapping module_name -> module_content
        Only includes successfully loaded modules
        Empty dict if all modules fail to load

    Example:
        >>> modules = load_multiple_modules(["scripts", "bmad"])
        >>> print(len(modules))
        2
        >>> print(list(modules.keys()))
        ['scripts', 'bmad']

        >>> # Handles partial failures gracefully
        >>> modules = load_multiple_modules(["scripts", "nonexistent"])
        >>> # Warning logged for "nonexistent"
        >>> print(len(modules))
        1
        >>> print(list(modules.keys()))
        ['scripts']
    """
    # Type validation
    if not isinstance(module_names, list):
        raise TypeError(
            f"module_names must be list, got {type(module_names).__name__}"
        )

    results = {}
    failed_modules = []

    # Load each module sequentially (parallel optimization deferred to Epic 2)
    for module_name in module_names:
        try:
            module_data = load_detail_module(module_name, index_dir)
            results[module_name] = module_data
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            # Log warning for partial failure but continue processing
            failed_modules.append((module_name, str(e)))
            warnings.warn(
                f"Failed to load module '{module_name}': {e}",
                UserWarning
            )
            logger.warning(f"Failed to load module '{module_name}': {e}")
            continue

    # Log summary if there were failures
    if failed_modules:
        logger.info(
            f"Batch load completed: {len(results)} succeeded, "
            f"{len(failed_modules)} failed"
        )

    return results


def load_doc_tier(
    tier: str,
    module_name: Optional[str] = None,
    index_dir: Optional[Path] = None
) -> Dict[str, Dict]:
    """
    Load documentation from specific tier (standard or archive).

    If module_name is provided, loads docs from that module only.
    If module_name is None, aggregates docs from all modules.

    Args:
        tier: Documentation tier ("standard" or "archive")
        module_name: Optional module to load from (default: all modules)
        index_dir: Optional custom directory (default: PROJECT_INDEX.d/)

    Returns:
        Dict mapping doc_path -> doc_content
        Structure: {
            "docs/guide.md": {
                "sections": ["Introduction", "Setup"],
                "tier": "standard"
            }
        }

    Raises:
        ValueError: Invalid tier name
        FileNotFoundError: Module not found (if module_name specified)

    Example:
        >>> # Load all standard docs from scripts module
        >>> docs = load_doc_tier("standard", "scripts")
        >>> print(list(docs.keys()))
        ['scripts/README.md', 'scripts/INSTALL.md']

        >>> # Load all archive docs from all modules
        >>> all_archive = load_doc_tier("archive")
        >>> print(len(all_archive))
        42
    """
    # Validate tier name
    valid_tiers = {"standard", "archive"}
    if tier not in valid_tiers:
        raise ValueError(
            f"Invalid tier '{tier}'. Must be one of: {', '.join(valid_tiers)}"
        )

    tier_key = f"doc_{tier}"

    # Default to PROJECT_INDEX.d/ in current working directory
    if index_dir is None:
        index_dir = Path.cwd() / "PROJECT_INDEX.d"
    elif isinstance(index_dir, str):
        index_dir = Path(index_dir)

    # Load from specific module
    if module_name:
        module_data = load_detail_module(module_name, index_dir)
        return module_data.get(tier_key, {})

    # Load from all modules (aggregate)
    aggregated_docs = {}

    # Find all module files in PROJECT_INDEX.d/
    if not index_dir.exists():
        raise FileNotFoundError(
            f"Index directory not found: {index_dir}\n"
            "Run project_index.py to generate the index first"
        )

    for module_file in index_dir.glob("*.json"):
        try:
            with open(module_file, 'r', encoding='utf-8') as f:
                module_data = json.load(f)

            # Extract tier docs from this module
            tier_docs = module_data.get(tier_key, {})
            aggregated_docs.update(tier_docs)
        except (json.JSONDecodeError, OSError) as e:
            # Log warning but continue processing other modules
            logger.warning(f"Failed to load module {module_file.name}: {e}")
            continue

    return aggregated_docs
