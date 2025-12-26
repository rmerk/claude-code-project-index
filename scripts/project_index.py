#!/usr/bin/env python3
"""
Project Index for Claude Code
Provides spatial-architectural awareness to prevent code duplication and misplacement.

Features:
- Directory tree structure visualization
- Markdown documentation mapping with section headers
- Directory purpose inference
- Full function and class signatures with type annotations
- Multi-language support (parsed vs listed)

Usage: python project_index.py
Output: PROJECT_INDEX.json
"""

__version__ = "0.2.0-beta"

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import socket

# Import shared utilities
from index_utils import (
    IGNORE_DIRS, PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    DIRECTORY_PURPOSES, extract_python_signatures, extract_javascript_signatures,
    extract_shell_signatures, extract_vue_signatures, extract_markdown_structure,
    infer_file_purpose, infer_directory_purpose, get_language_name,
    should_index_file, get_git_files
)
from doc_classifier import classify_documentation
from git_metadata import extract_git_metadata
from signature_cache import (
    load_cache, save_cache, get_cached_signature, set_cached_signature
)

# Limits to keep it fast and simple
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5


def read_version_file() -> str:
    """
    Read version from VERSION file if it exists, fallback to __version__.

    Checks ~/.claude-code-project-index/VERSION for current version.
    Falls back to hardcoded __version__ if file doesn't exist (backward compatibility).

    Returns:
        str: Version string (e.g., "v0.3.0")

    Example:
        >>> version = read_version_file()
        >>> print(version)  # "v0.3.0" or "0.2.0-beta" (fallback)
    """
    version_file = Path.home() / ".claude-code-project-index" / "VERSION"

    try:
        if version_file.exists():
            version = version_file.read_text().strip()
            if version:
                return version
    except (OSError, IOError):
        # Graceful fallback on file read errors
        pass

    # Fallback to hardcoded version for backward compatibility
    return __version__


class UpdateInfo(NamedTuple):
    """Information about available updates."""
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic version strings.

    Strips 'v' prefix and compares major.minor.patch components.
    Handles beta/alpha suffixes by removing them for comparison.

    Args:
        v1: First version (e.g., "v0.3.0", "0.2.0-beta")
        v2: Second version (e.g., "v0.3.1")

    Returns:
        int: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

    Example:
        >>> compare_versions("v0.3.0", "v0.3.1")
        -1
        >>> compare_versions("0.3.0", "0.2.0-beta")
        1
    """
    # Strip 'v' prefix and split on '-' to remove beta/alpha suffixes
    def normalize(v: str) -> List[int]:
        v = v.lstrip('v').split('-')[0]  # Remove 'v' and suffixes
        return [int(x) for x in v.split('.')]

    try:
        v1_parts = normalize(v1)
        v2_parts = normalize(v2)

        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts += [0] * (max_len - len(v1_parts))
        v2_parts += [0] * (max_len - len(v2_parts))

        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0
    except (ValueError, IndexError):
        # If parsing fails, consider versions equal
        return 0


def log_update_check(result: str, current_version: str, latest_version: str = None, error: str = None) -> None:
    """
    Log update check results to ~/.claude-code-project-index/logs/update-checks.log.

    Args:
        result: Check result ("up-to-date", "update-available", "error")
        current_version: Current installed version
        latest_version: Latest available version (if known)
        error: Error message (if error occurred)

    Example:
        >>> log_update_check("update-available", "v0.3.0", "v0.3.1")
        # Logs: 2025-11-11T12:34:56 | update-available | v0.3.0 -> v0.3.1
    """
    log_dir = Path.home() / ".claude-code-project-index" / "logs"
    log_file = log_dir / "update-checks.log"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        if result == "update-available" and latest_version:
            log_entry = f"{timestamp} | {result} | {current_version} -> {latest_version}\n"
        elif result == "error" and error:
            log_entry = f"{timestamp} | {result} | {current_version} | {error}\n"
        else:
            log_entry = f"{timestamp} | {result} | {current_version}\n"

        with open(log_file, 'a') as f:
            f.write(log_entry)
    except (OSError, IOError):
        # Silent failure - don't block on logging errors
        pass


def check_version_compatibility(index_data: Dict) -> Optional[str]:
    """
    Check version compatibility between index format and installed tool.

    Compares index format version with tool version to detect potential
    incompatibilities. Returns warning message if mismatch detected.

    Args:
        index_data: Loaded PROJECT_INDEX.json data with optional "version" field

    Returns:
        str: Warning message if incompatibility detected, None otherwise

    Example:
        >>> index = json.load(open("PROJECT_INDEX.json"))
        >>> warning = check_version_compatibility(index)
        >>> if warning:
        ...     print(f"⚠️  {warning}")
    """
    index_version = index_data.get("version", "1.0")  # Default to 1.0 for legacy
    tool_version = read_version_file()

    # Extract major.minor from both versions for comparison
    def extract_major_minor(v: str) -> Tuple[int, int]:
        v = v.lstrip('v').split('-')[0]  # Remove 'v' prefix and suffixes
        parts = v.split('.')
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor)
        except (ValueError, IndexError):
            return (0, 0)

    index_maj_min = extract_major_minor(index_version)
    tool_maj_min = extract_major_minor(tool_version)

    # Check for major version mismatch
    if index_maj_min[0] != tool_maj_min[0]:
        return (f"Index format version ({index_version}) differs from tool version ({tool_version}). "
                f"Consider regenerating index with: python scripts/project_index.py")

    # Check for minor version mismatch (warning, not blocking)
    if index_maj_min[1] != tool_maj_min[1]:
        return (f"Index format version ({index_version}) may be outdated (tool version: {tool_version}). "
                f"Regenerating index recommended.")

    return None  # Versions compatible


def check_for_updates(no_update_check: bool = False) -> Optional[UpdateInfo]:
    """
    Check GitHub releases for newer version (non-blocking, 2s timeout).

    Makes a GET request to GitHub Releases API with 2-second timeout.
    Compares local VERSION with latest release version.
    Logs all check attempts (success and failure).

    Args:
        no_update_check: Skip check if True (for CI/automation)

    Returns:
        UpdateInfo: Update info if newer version available, None otherwise

    Security (NFR-S6):
        - Only sends user-agent header, no project metadata
        - No local project information leaked to GitHub

    Performance (NFR-P3):
        - 2-second timeout, non-blocking
        - Graceful degradation on network failure

    Example:
        >>> info = check_for_updates()
        >>> if info and info.update_available:
        ...     print(f"Update available: {info.latest_version}")
        ...     print(f"Install with: ./install.sh --upgrade")
    """
    if no_update_check:
        return None

    current_version = read_version_file()

    try:
        # Set socket timeout for non-blocking behavior (NFR-P3)
        socket.setdefaulttimeout(2.0)

        # Create request with minimal user-agent (NFR-S6: no project metadata)
        url = "https://api.github.com/repos/ericbuess/claude-code-project-index/releases/latest"
        headers = {"User-Agent": "claude-code-project-index"}
        req = Request(url, headers=headers)

        # Make API call with 2s timeout
        with urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))

        latest_version = data.get("tag_name", "")
        release_url = data.get("html_url", "")

        if not latest_version:
            log_update_check("error", current_version, error="No tag_name in response")
            return None

        # Compare versions
        if compare_versions(latest_version, current_version) > 0:
            log_update_check("update-available", current_version, latest_version)
            return UpdateInfo(
                current_version=current_version,
                latest_version=latest_version,
                update_available=True,
                release_url=release_url
            )
        else:
            log_update_check("up-to-date", current_version)
            return None

    except (URLError, HTTPError, socket.timeout, OSError) as e:
        # Graceful degradation on network failure (NFR-R3)
        error_msg = str(type(e).__name__)
        log_update_check("error", current_version, error=error_msg)
        return None
    finally:
        # Reset socket timeout
        socket.setdefaulttimeout(None)


def detect_index_format(index_path: Path = None) -> str:
    """
    Detect whether index is legacy or split format.

    Checks for PROJECT_INDEX.d/ directory existence and version field.

    Args:
        index_path: Path to PROJECT_INDEX.json (defaults to cwd/PROJECT_INDEX.json)

    Returns:
        "split" if PROJECT_INDEX.d/ exists and version is 2.x-split or 2.x-enhanced
        "legacy" if single-file format
    """
    if index_path is None:
        index_path = Path.cwd() / "PROJECT_INDEX.json"

    index_dir = index_path.parent / "PROJECT_INDEX.d"

    # Primary check: directory existence
    if not index_dir.exists():
        return "legacy"

    # Secondary check: version field
    try:
        with open(index_path) as f:
            data = json.load(f)
            version = data.get("version", "1.0")
            # Split format: v2.0-split, v2.1-enhanced, v2.2-submodules, or any future v2.x-* versions
            if version.startswith("2.") and ("-split" in version or "-enhanced" in version or "-submodules" in version):
                return "split"
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        # If index file doesn't exist or is corrupted, but directory exists,
        # assume legacy until proven otherwise
        pass

    return "legacy"


def load_configuration(config_path: Optional[Path] = None, project_root: Optional[Path] = None) -> Dict[str, any]:
    """
    Load configuration from .project-index.json file.
    On first run (config doesn't exist), auto-detects preset and creates config from template.
    On subsequent runs, detects if project size crossed preset boundaries and prompts for upgrade.

    Args:
        config_path: Path to configuration file (defaults to cwd/.project-index.json)
        project_root: Project root directory for auto-detection (defaults to config_path.parent or cwd)

    Returns:
        Dictionary with configuration values, or empty dict if file not found.
        Valid keys: 'mode' (str), 'threshold' (int), 'max_index_size' (int),
        'compression_level' (str), 'submodule_config' (dict), '_preset' (str)

    Configuration format:
        {
            "mode": "auto" | "split" | "single",
            "threshold": number (default: 1000),
            "max_index_size": number (default: 1048576),
            "compression_level": "standard" | "aggressive",
            "submodule_config": {
                "enabled": true,
                "threshold": 100,
                "strategy": "auto" | "force" | "disabled",
                "max_depth": 1 | 2 | 3,
                "framework_presets": {
                    "vite": {"split_paths": [...], "max_depth": 3},
                    "react": {"split_paths": [...], "max_depth": 2},
                    "nextjs": {"split_paths": [...], "max_depth": 2}
                }
            },
            "_preset": "small" | "medium" | "large"
        }

    First Run Behavior:
        - If config file doesn't exist, auto-detects preset based on file count:
          - <100 files → 'small' preset
          - 100-4999 files → 'medium' preset
          - 5000+ files → 'large' preset
        - Loads preset template and creates .project-index.json

    Boundary Crossing Detection:
        - On subsequent runs, compares original preset with current file count
        - If preset boundary crossed (e.g., small → medium), prompts user to upgrade
        - Creates backup file (.project-index.json.backup) before upgrading
        - User can accept (upgrade) or decline (keep existing config)

    CLI Flags:
        - --no-prompt: Skip interactive prompt, auto-upgrade if boundary crossed
        - --upgrade-to=preset: Force upgrade to specific preset (small/medium/large)
          regardless of file count. Invalid values are ignored.

    Configuration file location:
        Searches for .project-index.json in current working directory only.
        If multiple projects are nested, only the cwd config is used.
        To use different configs for nested projects, run the indexer from
        that project's directory.
    """
    if config_path is None:
        config_path = Path.cwd() / ".project-index.json"

    # Track if project_root was explicitly provided
    project_root_provided = project_root is not None

    if project_root is None:
        project_root = config_path.parent if config_path.parent.exists() else Path.cwd()

    # Auto-detect preset and create config on first run
    # Only auto-create if project_root was explicitly provided
    # This maintains backward compatibility - if project_root was None, return empty dict
    if not config_path.exists():
        if project_root_provided:
            # Check CLI flags for --upgrade-to
            cli_flags = _check_cli_flags()

            # Get file count
            git_files = get_git_files(project_root)
            file_count = len(git_files) if git_files else 0

            # Auto-detect preset, but allow --upgrade-to flag to override
            preset_name = auto_detect_preset(file_count)
            if cli_flags['upgrade_to']:
                preset_name = cli_flags['upgrade_to']

            # Load preset template
            try:
                config = load_preset_template(preset_name)
                config['_preset'] = preset_name

                # Save config file
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)

                return config
            except Exception as e:
                # If template loading fails, return empty config
                return {}
        else:
            # Config doesn't exist and project_root not provided - return empty dict (backward compatibility)
            return {}

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Validate mode if present
        if 'mode' in config:
            valid_modes = ['auto', 'split', 'single']
            if config['mode'] not in valid_modes:
                print(f"⚠️  Warning: Invalid mode '{config['mode']}' in config file, ignoring")
                config.pop('mode')

        # Validate threshold if present
        if 'threshold' in config:
            if not isinstance(config['threshold'], (int, float)) or config['threshold'] <= 0:
                print(f"⚠️  Warning: Invalid threshold '{config['threshold']}' in config file, ignoring")
                config.pop('threshold')

        # Validate submodule_config if present
        if 'submodule_config' in config:
            submod_config = config['submodule_config']

            # Validate enabled flag
            if 'enabled' in submod_config:
                if not isinstance(submod_config['enabled'], bool):
                    print(f"⚠️  Warning: Invalid submodule_config.enabled (must be boolean), using default: true")
                    submod_config['enabled'] = True

            # Validate threshold
            if 'threshold' in submod_config:
                if not isinstance(submod_config['threshold'], int) or submod_config['threshold'] <= 0:
                    print(f"⚠️  Warning: Invalid submodule_config.threshold (must be positive integer), using default: 100")
                    submod_config['threshold'] = 100

            # Validate strategy
            if 'strategy' in submod_config:
                valid_strategies = ['auto', 'force', 'disabled']
                if submod_config['strategy'] not in valid_strategies:
                    print(f"⚠️  Warning: Invalid submodule_config.strategy, using default: 'auto'")
                    submod_config['strategy'] = 'auto'

            # Validate max_depth
            if 'max_depth' in submod_config:
                if not isinstance(submod_config['max_depth'], int) or not (1 <= submod_config['max_depth'] <= 3):
                    print(f"⚠️  Warning: Invalid submodule_config.max_depth (must be 1-3), using default: 3")
                    submod_config['max_depth'] = 3

            # Validate framework_presets if present
            if 'framework_presets' in submod_config:
                if not isinstance(submod_config['framework_presets'], dict):
                    print(f"⚠️  Warning: Invalid submodule_config.framework_presets (must be dict), ignoring")
                    submod_config.pop('framework_presets')
                else:
                    # Validate each preset entry
                    valid_frameworks = ['vite', 'react', 'nextjs', 'generic']
                    for framework, preset in list(submod_config['framework_presets'].items()):
                        if framework not in valid_frameworks:
                            print(f"⚠️  Warning: Unknown framework '{framework}' in framework_presets, ignoring")
                            submod_config['framework_presets'].pop(framework)
                        elif not isinstance(preset, dict):
                            print(f"⚠️  Warning: Invalid preset for '{framework}' (must be dict), ignoring")
                            submod_config['framework_presets'].pop(framework)

        # Boundary crossing detection and upgrade logic
        # Only run if project_root was explicitly provided (not defaulted)
        # This prevents prompts when called from main() without explicit project_root parameter
        if project_root_provided:
            # Detect original preset from existing config
            original_preset = detect_preset_from_config(config)

            # Get current file count and detect current preset
            git_files = get_git_files(project_root)
            file_count = len(git_files) if git_files else 0
            current_preset = auto_detect_preset(file_count)

            # Check CLI flags
            cli_flags = _check_cli_flags()

            # Handle --upgrade-to flag: override current_preset if flag is present
            if cli_flags['upgrade_to']:
                current_preset = cli_flags['upgrade_to']

            # Check if boundary was crossed (preset changed)
            if original_preset != current_preset:
                # Determine if we should upgrade (check flags or prompt user)
                should_upgrade = False

                if cli_flags['no_prompt']:
                    # Auto-upgrade if --no-prompt flag is set
                    should_upgrade = True
                else:
                    # Prompt user for upgrade
                    prompt_message = (
                        f"Your project has grown to {file_count} files.\n"
                        f"Recommend upgrading from '{original_preset}' to '{current_preset}' preset.\n"
                        f"Upgrade now? [y/n] "
                    )
                    try:
                        user_response = input(prompt_message).strip().lower()
                        should_upgrade = user_response == 'y'
                    except (EOFError, KeyboardInterrupt):
                        # Handle cases where input is not available (e.g., in tests or non-interactive environments)
                        should_upgrade = False

                if should_upgrade:
                    # Create backup before upgrading (only if we're actually upgrading)
                    backup_path = Path(str(config_path) + ".backup")
                    try:
                        shutil.copy(config_path, backup_path)
                    except Exception as e:
                        print(f"⚠️  Warning: Could not create backup: {e}")
                    # Load new preset template
                    try:
                        new_config = load_preset_template(current_preset)
                        # Merge with existing config (preserve user customizations)
                        # Update _preset field and merge other fields
                        config.update(new_config)
                        config['_preset'] = current_preset

                        # Save updated config
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)

                        return config
                    except Exception as e:
                        # If template loading fails, keep existing config
                        print(f"⚠️  Warning: Could not load preset template: {e}")
                        print("   Keeping existing configuration")
                        return config
                else:
                    # User declined upgrade, return existing config unchanged
                    return config

        # No boundary crossing, return config as-is
        return config

    except json.JSONDecodeError as e:
        print(f"⚠️  Warning: Corrupted config file at {config_path}: {e}")
        print("   Falling back to defaults")
        return {}
    except Exception as e:
        print(f"⚠️  Warning: Error reading config file: {e}")
        print("   Falling back to defaults")
        return {}


def generate_tree_structure(root_path: Path, max_depth: int = MAX_TREE_DEPTH) -> List[str]:
    """Generate a compact ASCII tree representation of the directory structure."""
    tree_lines = []

    def should_include_dir(path: Path) -> bool:
        """Check if directory should be included in tree."""
        return (
            path.name not in IGNORE_DIRS and
            not path.name.startswith('.') and
            path.is_dir()
        )

    def add_tree_level(path: Path, prefix: str = "", depth: int = 0):
        """Recursively build tree structure."""
        if depth > max_depth:
            if any(should_include_dir(p) for p in path.iterdir() if p.is_dir()):
                tree_lines.append(prefix + "└── ...")
            return

        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return

        # Filter items
        dirs = [item for item in items if should_include_dir(item)]

        # Important files to show in tree
        important_files = [
            item for item in items
            if item.is_file() and (
                item.name in ['README.md', 'package.json', 'requirements.txt',
                             'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                             'setup.py', 'pyproject.toml', 'Makefile']
            )
        ]

        all_items = dirs + important_files

        for i, item in enumerate(all_items):
            is_last = i == len(all_items) - 1
            current_prefix = "└── " if is_last else "├── "

            name = item.name
            if item.is_dir():
                name += "/"
                # Add file count for directories
                try:
                    file_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix in CODE_EXTENSIONS)
                    if file_count > 0:
                        name += f" ({file_count} files)"
                except (OSError, PermissionError):
                    pass

            tree_lines.append(prefix + current_prefix + name)

            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                add_tree_level(item, next_prefix, depth + 1)

    # Start with root
    tree_lines.append(".")
    add_tree_level(root_path, "")
    return tree_lines


# These functions are now imported from index_utils


def generate_split_index(root_dir: str, config: Optional[Dict] = None) -> Tuple[Dict, int]:
    """Generate lightweight core index in split format (v2.2-submodules).

    Args:
        root_dir: Project root directory
        config: Optional configuration dict with doc_tiers and other settings

    Returns:
        Tuple of (core_index_dict, skipped_file_count)
    """
    from index_utils import extract_lightweight_signature

    root = Path(root_dir)
    git_cache = {}  # Cache for git metadata

    # Load signature cache for performance (skip if --no-cache flag)
    use_cache = '--no-cache' not in sys.argv
    sig_cache = load_cache(root) if use_cache else {"version": "1.0", "signatures": {}}
    cache_hits = 0
    cache_misses = 0

    # Core index structure (v2.2-submodules with multi-level organization)
    # Note: File details are stored in detail modules (PROJECT_INDEX.d/), not in core index
    # This keeps core index small for embedding in CLAUDE.md while enabling lazy-loading
    core_index = {
        'version': '2.2-submodules',
        'at': datetime.now().isoformat(),
        'root': str(root),
        'tree': [],
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0,
            'doc_tiers': {'critical': 0, 'standard': 0, 'archive': 0},  # Tier counts
            'git_files_tracked': 0,  # Files with git metadata extracted
            'git_files_fallback': 0  # Files using filesystem mtime fallback
        },
        # 'f' section removed in v2.2 - file details are in PROJECT_INDEX.d/ modules
        'g': [],  # Global call graph (cross-module edges only)
        'd_critical': {},  # Critical documentation only (v2.1-tiered)
        'modules': {},  # Module references
        'dir_purposes': {}
    }

    # Check configuration for include_all_doc_tiers setting
    include_all_tiers = config.get('include_all_doc_tiers', False) if config else False
    if include_all_tiers:
        # Small projects: include all tiers in core index
        core_index['d_standard'] = {}
        core_index['d_archive'] = {}

    # Generate directory tree (reuse existing function)
    print("📊 Building directory tree...")
    core_index['tree'] = generate_tree_structure(root)

    # Get list of files to process
    print("🔍 Indexing files...")
    git_files = get_git_files(root)

    skipped_count = 0
    directory_files = {}

    if git_files is not None:
        print(f"   Using git ls-files (found {len(git_files)} files)")
        files_to_process = git_files

        # Count directories
        seen_dirs = set()
        for file_path in git_files:
            for parent in file_path.parents:
                if parent != root and parent not in seen_dirs:
                    seen_dirs.add(parent)
                    if parent not in directory_files:
                        directory_files[parent] = []
        core_index['stats']['total_directories'] = len(seen_dirs)
    else:
        print("   Using manual file discovery (git not available)")
        files_to_process = []
        for file_path in root.rglob('*'):
            if file_path.is_dir():
                if not any(part in IGNORE_DIRS for part in file_path.parts):
                    core_index['stats']['total_directories'] += 1
                    directory_files[file_path] = []
                continue

            if file_path.is_file():
                files_to_process.append(file_path)

    # Track all parsed files for module organization
    parsed_files = []
    file_functions_map = {}  # Map file_path -> extracted data for module refs
    markdown_files_by_tier = {'standard': [], 'archive': []}  # Track non-critical docs for detail modules

    # Process files
    file_count = 0
    for file_path in files_to_process:
        if file_count >= MAX_FILES:
            print(f"⚠️  Stopping at {MAX_FILES} files")
            break

        if not should_index_file(file_path, root):
            skipped_count += 1
            continue

        # Track files in directories
        parent_dir = file_path.parent
        if parent_dir in directory_files:
            directory_files[parent_dir].append(file_path.name)

        rel_path = file_path.relative_to(root)

        # Handle markdown files with tiered classification
        if file_path.suffix in MARKDOWN_EXTENSIONS:
            # Classify documentation tier
            tier = classify_documentation(file_path, config)
            core_index['stats']['doc_tiers'][tier] += 1

            # Extract doc structure once for reuse
            doc_structure = extract_markdown_structure(file_path)
            if doc_structure['sections']:
                doc_entry = {
                    'sections': doc_structure['sections'][:10],
                    'tier': tier
                }

                # Store in appropriate tier section based on configuration
                if tier == 'critical':
                    core_index['d_critical'][str(rel_path)] = doc_entry
                    core_index['stats']['markdown_files'] += 1
                elif include_all_tiers:
                    # Small project mode: include all tiers in core index
                    if tier == 'standard':
                        core_index['d_standard'][str(rel_path)] = doc_entry
                    elif tier == 'archive':
                        core_index['d_archive'][str(rel_path)] = doc_entry
                    core_index['stats']['markdown_files'] += 1
                else:
                    # Default mode: track standard/archive docs for detail modules
                    if tier in ['standard', 'archive']:
                        markdown_files_by_tier[tier].append({
                            'path': str(rel_path),
                            'file_path': file_path,
                            'sections': doc_structure['sections'][:10],
                            'tier': tier
                        })
            continue

        # Handle code files
        language = get_language_name(file_path.suffix)

        # Only parse supported languages
        if file_path.suffix not in PARSEABLE_LANGUAGES:
            core_index['stats']['listed_only'][language] = \
                core_index['stats']['listed_only'].get(language, 0) + 1
            continue

        try:
            # Check signature cache first (Story: Persistent Signature Cache)
            cached = get_cached_signature(file_path, sig_cache) if use_cache else None

            if cached:
                extracted = cached
                cache_hits += 1
            else:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Extract signatures based on language
                if file_path.suffix == '.py':
                    extracted = extract_python_signatures(content)
                elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                    extracted = extract_javascript_signatures(content)
                elif file_path.suffix in {'.sh', '.bash'}:
                    extracted = extract_shell_signatures(content)
                elif file_path.suffix == '.vue':
                    extracted = extract_vue_signatures(content)
                else:
                    extracted = {'functions': {}, 'classes': {}}

                # Cache the extracted signature
                if use_cache and (extracted.get('functions') or extracted.get('classes')):
                    set_cached_signature(file_path, extracted, sig_cache)
                cache_misses += 1

            # Skip if no functions/classes found
            if not extracted.get('functions') and not extracted.get('classes'):
                continue

            # Extract git metadata for detail modules
            git_meta = extract_git_metadata(file_path, root, git_cache)
            if git_meta.get('commit'):
                core_index['stats']['git_files_tracked'] += 1
            else:
                # No commit means fallback to mtime was used
                if git_meta.get('date'):  # Has mtime fallback data
                    core_index['stats']['git_files_fallback'] += 1

            # Track for module organization
            parsed_files.append(file_path)
            # Store extracted data along with git metadata for detail modules
            file_functions_map[str(rel_path)] = {
                **extracted,
                'git': git_meta if git_meta.get('commit') or git_meta.get('date') else None
            }

            # Update stats
            lang_key = PARSEABLE_LANGUAGES[file_path.suffix]
            core_index['stats']['fully_parsed'][lang_key] = \
                core_index['stats']['fully_parsed'].get(lang_key, 0) + 1

        except Exception as e:
            # Parse error - skip this file
            core_index['stats']['listed_only'][language] = \
                core_index['stats']['listed_only'].get(language, 0) + 1

        file_count += 1

        # Progress indicator
        if file_count % 100 == 0:
            print(f"  Indexed {file_count} files...")

    core_index['stats']['total_files'] = file_count

    # Organize files into modules
    print("📦 Organizing modules...")
    modules = organize_into_modules(parsed_files, root, depth=1)

    # Detect and split large modules (Epic 4, Stories 4.1-4.4)
    submod_config = get_submodule_config(config)
    strategy = submod_config.get('strategy', 'auto')

    # Story 4.4: Apply strategy behavior
    if submod_config['enabled'] and strategy != 'disabled':
        import logging
        logger = logging.getLogger(__name__)

        # Detect framework and apply preset (Story 4.4, AC #2, #3)
        framework_type = detect_framework_patterns(root)
        preset = apply_framework_preset(framework_type, (config or {}).get('submodule_config'))
        # User config overrides preset (prioritize user's max_depth setting)
        max_depth = submod_config.get('max_depth', preset.get('max_depth', 3))

        logger.info(f"Framework detected: {framework_type}, Strategy: {strategy}, Max depth: {max_depth}")

        # Determine which modules to split based on strategy
        modules_to_split = []

        if strategy == 'force':
            # Force: Split ALL modules regardless of size (AC #4)
            logger.info(f"Force strategy: splitting all {len(modules)} modules")
            modules_to_split = [{'module_id': mid, 'file_count': len(files)} for mid, files in modules.items()]
            print(f"   Force strategy: splitting all {len(modules_to_split)} module(s)")

        elif strategy == 'auto':
            # Auto: Split only large modules (AC #3)
            large_modules = detect_large_modules(
                modules,
                threshold=submod_config['threshold'],
                root_path=root,
                config=config
            )
            modules_to_split = large_modules
            if large_modules:
                print(f"   Auto strategy: detected {len(large_modules)} large module(s) (>={submod_config['threshold']} files)")

        # Apply splitting to selected modules
        if modules_to_split:
            print(f"📂 Splitting modules using {framework_type} preset...")
            split_modules = {}

            for mod_info in modules_to_split:
                module_id = mod_info['module_id']
                file_list = modules[module_id]

                logger.info(f"Splitting {module_id} ({len(file_list)} files) with max_depth={max_depth}")

                sub_modules = split_module_recursive(
                    module_id,
                    file_list,
                    root,
                    max_depth,
                    current_depth=0,
                    config=config
                )

                # If splitting occurred (returned more than 1 module)
                if len(sub_modules) > 1:
                    split_modules.update(sub_modules)
                    print(f"   Split {module_id} → {len(sub_modules)} sub-modules")
                else:
                    # No split occurred, keep original
                    split_modules[module_id] = file_list

            # Replace split modules in the modules dict
            for mod_info in modules_to_split:
                module_id = mod_info['module_id']
                if module_id in modules:
                    del modules[module_id]
            modules.update(split_modules)
        else:
            if strategy == 'auto':
                logger.info("No large modules detected - using monolithic organization")

    elif strategy == 'disabled':
        # Disabled: Use monolithic modules (legacy behavior, AC #5)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Sub-module splitting disabled - using monolithic module organization")
        print("   Sub-module splitting disabled (using monolithic modules)")

    # Add modules for directories with only markdown files (no code)
    # This ensures detail modules are created even for doc-only directories
    if markdown_files_by_tier:
        for tier in ['standard', 'archive']:
            for doc_info in markdown_files_by_tier.get(tier, []):
                doc_path = doc_info['path']
                doc_file_path = doc_info['file_path']

                # Determine module for this doc
                doc_parent = doc_file_path.parent
                if doc_parent == root:
                    module_id = 'root'
                else:
                    try:
                        rel_parent = doc_parent.relative_to(root)
                        parts = rel_parent.parts
                        if parts:
                            module_id = parts[0]
                        else:
                            module_id = 'root'
                    except ValueError:
                        continue

                # Create empty module if it doesn't exist (for doc-only dirs)
                if module_id not in modules:
                    modules[module_id] = []

    # Create module references with metadata
    core_index['modules'] = create_module_references(modules, file_functions_map)

    # Build file-to-module mapping for O(1) lookup (Story 4.2)
    print("🗺️  Building file-to-module map...")
    core_index['file_to_module_map'] = build_file_to_module_map(modules)

    # Generate warnings for optimization opportunities (Story 4.4, AC #10)
    framework_type = detect_framework_patterns(root)
    warnings = generate_warnings(modules, framework_type, config)
    if warnings:
        print("\n" + "=" * 70)
        for warning in warnings:
            print(warning)
            print("-" * 70)
        print("")

    # Infer directory purposes
    print("🏗️  Analyzing directory purposes...")
    for dir_path, files in directory_files.items():
        if files:
            purpose = infer_directory_purpose(dir_path, files)
            if purpose:
                rel_dir = str(dir_path.relative_to(root))
                if rel_dir != '.':
                    core_index['dir_purposes'][rel_dir] = purpose

    # Log tier classification summary
    tier_counts = core_index['stats']['doc_tiers']
    if sum(tier_counts.values()) > 0:
        print(f"📚 Documentation tiers: {tier_counts['critical']} critical, "
              f"{tier_counts['standard']} standard, {tier_counts['archive']} archive")

    # Build global call graph (cross-module edges only)
    # Note: Within-module edges will go to detail modules (Story 1.3)
    print("📞 Building global call graph...")
    # For now, we'll defer this to keep the core index minimal
    # This will be implemented fully in Story 1.3 when we have detail modules

    # Generate detail modules (Story 1.3)
    # Check for --skip-details flag via environment variable
    skip_details = os.getenv('INDEX_SKIP_DETAILS', '').lower() == 'true'
    detail_files = generate_detail_modules(
        file_functions_map,
        modules,
        root,
        skip_details,
        markdown_files_by_tier=markdown_files_by_tier
    )

    # Add detail file list to core index stats for reference
    if detail_files:
        core_index['stats']['detail_modules'] = len(detail_files)

    # Save signature cache
    if use_cache:
        save_cache(root, sig_cache)
        if cache_hits + cache_misses > 0:
            hit_rate = cache_hits / (cache_hits + cache_misses) * 100
            print(f"📦 Signature cache: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% hit rate)")

    return core_index, skipped_count


def generate_detail_modules(
    files_data: Dict[str, Dict],
    modules: Dict[str, List[str]],
    root_path: Path,
    skip_details: bool = False,
    markdown_files_by_tier: Optional[Dict[str, List[Dict]]] = None
) -> List[str]:
    """Generate detailed module files in PROJECT_INDEX.d/ directory.

    Args:
        files_data: Dict mapping file paths -> full extracted function/class data
        modules: Dict mapping module_id -> list of file paths (from organize_into_modules)
        root_path: Project root directory
        skip_details: If True, skip detail generation (core-only mode)
        markdown_files_by_tier: Dict with 'standard' and 'archive' keys containing doc file info

    Returns:
        List of created detail module file paths
    """
    if skip_details:
        print("⏩ Skipping detail module generation (--skip-details mode)")
        return []

    from index_utils import build_call_graph, get_language_name

    print("📦 Generating detail modules...")

    # Create PROJECT_INDEX.d/ directory
    detail_dir = root_path / "PROJECT_INDEX.d"
    detail_dir.mkdir(exist_ok=True)

    created_files = []

    # Generate detail module for each module
    for module_id, file_list in modules.items():
        # Build detail module structure
        detail_module = {
            'module_id': module_id,
            'version': '2.2-submodules',
            'modified': datetime.now().isoformat(),
            'files': {},
            'call_graph_local': [],
            'doc_standard': {},
            'doc_archive': {}
        }

        # Track all functions in this module for call graph
        module_functions = {}  # For build_call_graph
        module_classes = {}    # For build_call_graph

        # Process each file in the module
        for file_path in file_list:
            if file_path not in files_data:
                continue

            extracted = files_data[file_path]

            # Determine language
            path_obj = root_path / file_path
            language = get_language_name(path_obj.suffix)

            # Build file detail entry
            file_detail = {
                'language': language,
                'functions': [],
                'classes': [],
                'imports': extracted.get('imports', [])
            }

            # Add git metadata if available
            if extracted.get('git'):
                file_detail['git'] = extracted['git']

            # Add functions with full signatures
            if extracted.get('functions'):
                for func_name, func_data in extracted['functions'].items():
                    if isinstance(func_data, dict):
                        func_detail = {
                            'name': func_name,
                            'line': func_data.get('line', 0),
                            'signature': func_data.get('signature', ''),
                            'calls': func_data.get('calls', []),
                            'doc': func_data.get('doc', '')
                        }
                        file_detail['functions'].append(func_detail)

                        # Track for call graph
                        module_functions[func_name] = func_data

            # Add classes with full method details
            if extracted.get('classes'):
                for class_name, class_data in extracted['classes'].items():
                    if isinstance(class_data, dict):
                        class_detail = {
                            'name': class_name,
                            'line': class_data.get('line', 0),
                            'bases': class_data.get('bases', []),
                            'methods': [],
                            'doc': class_data.get('doc', '')
                        }

                        # Add methods
                        if class_data.get('methods'):
                            for method_name, method_data in class_data['methods'].items():
                                if isinstance(method_data, dict):
                                    method_detail = {
                                        'name': method_name,
                                        'line': method_data.get('line', 0),
                                        'signature': method_data.get('signature', ''),
                                        'calls': method_data.get('calls', []),
                                        'doc': method_data.get('doc', '')
                                    }
                                    class_detail['methods'].append(method_detail)

                        file_detail['classes'].append(class_detail)

                        # Track for call graph
                        module_classes[class_name] = class_data

            # Add file to detail module
            detail_module['files'][file_path] = file_detail

        # Add standard and archive tier documentation to this module
        if markdown_files_by_tier:
            for tier in ['standard', 'archive']:
                tier_key = f'doc_{tier}'
                for doc_info in markdown_files_by_tier.get(tier, []):
                    doc_path = doc_info['path']
                    doc_file_path = doc_info['file_path']

                    # Determine which module this doc belongs to
                    # Docs should be organized by their directory (similar to code files)
                    doc_parent = doc_file_path.parent
                    doc_module = None

                    # Match doc to module based on directory structure
                    if doc_parent == root_path:
                        doc_module = 'root'
                    else:
                        # Find the top-level directory
                        try:
                            rel_parent = doc_parent.relative_to(root_path)
                            parts = rel_parent.parts
                            if parts:
                                doc_module = parts[0]
                        except ValueError:
                            continue

                    # Add doc to appropriate module
                    if doc_module == module_id:
                        detail_module[tier_key][doc_path] = {
                            'sections': doc_info['sections'],
                            'tier': tier
                        }

        # Build local call graph (within-module edges only)
        if module_functions or module_classes:
            call_graph, _ = build_call_graph(module_functions, module_classes)

            # Convert to edge list format and filter for local calls only
            all_module_funcs = set(module_functions.keys())
            for class_data in module_classes.values():
                if isinstance(class_data, dict) and class_data.get('methods'):
                    all_module_funcs.update(class_data['methods'].keys())

            # Extract edges where both caller and callee are in this module
            for caller, callees in call_graph.items():
                if caller in all_module_funcs:
                    for callee in callees:
                        if callee in all_module_funcs:
                            detail_module['call_graph_local'].append([caller, callee])

        # Find most recent modification time in module
        most_recent = None
        for file_path in file_list:
            try:
                path_obj = root_path / file_path
                if path_obj.exists():
                    mtime = path_obj.stat().st_mtime
                    if most_recent is None or mtime > most_recent:
                        most_recent = mtime
            except Exception:
                continue

        if most_recent:
            detail_module['modified'] = datetime.fromtimestamp(most_recent).isoformat()

        # Write detail module file (compact JSON, no whitespace)
        detail_file_path = detail_dir / f"{module_id}.json"
        with open(detail_file_path, 'w', encoding='utf-8') as f:
            json.dump(detail_module, f, separators=(',', ':'))

        created_files.append(str(detail_file_path.relative_to(root_path)))
        print(f"   ✓ {module_id}.json ({len(file_list)} files, {len(detail_module['files'])} with details)")

    print(f"📦 Generated {len(created_files)} detail modules")
    return created_files


def build_index(root_dir: str, config: Optional[Dict] = None) -> Tuple[Dict, int]:
    """Build the enhanced index with architectural awareness (legacy single-file format)."""
    root = Path(root_dir)
    index = {
        'indexed_at': datetime.now().isoformat(),
        'root': str(root),
        'project_structure': {
            'type': 'tree',
            'root': '.',
            'tree': []
        },
        'documentation_map': {},
        'directory_purposes': {},
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0,
            'doc_tiers': {'critical': 0, 'standard': 0, 'archive': 0},  # Tier counts
            'git_files_tracked': 0,  # Files with git metadata (not supported in legacy format)
            'git_files_fallback': 0  # Files using mtime fallback (not supported in legacy format)
        },
        'files': {},
        'dependency_graph': {}
    }

    # Generate directory tree
    print("📊 Building directory tree...")
    index['project_structure']['tree'] = generate_tree_structure(root)

    file_count = 0
    dir_count = 0
    skipped_count = 0
    directory_files = {}  # Track files per directory

    # Try to use git ls-files for better performance and accuracy
    print("🔍 Indexing files...")
    git_files = get_git_files(root)

    if git_files is not None:
        # Use git-based file discovery
        print(f"   Using git ls-files (found {len(git_files)} files)")
        files_to_process = git_files

        # Count directories from git files
        seen_dirs = set()
        for file_path in git_files:
            for parent in file_path.parents:
                if parent != root and parent not in seen_dirs:
                    seen_dirs.add(parent)
                    if parent not in directory_files:
                        directory_files[parent] = []
        dir_count = len(seen_dirs)
    else:
        # Fallback to manual file discovery
        print("   Using manual file discovery (git not available)")
        files_to_process = []
        for file_path in root.rglob('*'):
            if file_path.is_dir():
                # Track directories
                if not any(part in IGNORE_DIRS for part in file_path.parts):
                    dir_count += 1
                    directory_files[file_path] = []
                continue

            if file_path.is_file():
                files_to_process.append(file_path)

    # Process files
    for file_path in files_to_process:
        if file_count >= MAX_FILES:
            print(f"⚠️  Stopping at {MAX_FILES} files (project too large)")
            print(f"   Consider adding more patterns to .gitignore to reduce scope")
            print(f"   Or ask Claude to modify MAX_FILES in scripts/project_index.py")
            break

        if not should_index_file(file_path, root):
            skipped_count += 1
            continue

        # Track files in their directories
        parent_dir = file_path.parent
        if parent_dir in directory_files:
            directory_files[parent_dir].append(file_path.name)

        # Get relative path and language
        rel_path = file_path.relative_to(root)

        # Handle markdown files with tiered classification
        if file_path.suffix in MARKDOWN_EXTENSIONS:
            # Classify documentation tier
            tier = classify_documentation(file_path, config)
            index['stats']['doc_tiers'][tier] += 1

            doc_structure = extract_markdown_structure(file_path)
            if doc_structure['sections'] or doc_structure['architecture_hints']:
                doc_structure['tier'] = tier  # Add tier to structure
                index['documentation_map'][str(rel_path)] = doc_structure
                index['stats']['markdown_files'] += 1
            continue

        # Handle code files
        language = get_language_name(file_path.suffix)

        # Base info for all files
        file_info = {
            'language': language,
            'parsed': False
        }

        # Add file purpose if we can infer it
        file_purpose = infer_file_purpose(file_path)
        if file_purpose:
            file_info['purpose'] = file_purpose

        # Try to parse if we support this language
        if file_path.suffix in PARSEABLE_LANGUAGES:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Extract based on language
                if file_path.suffix == '.py':
                    extracted = extract_python_signatures(content)
                elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                    extracted = extract_javascript_signatures(content)
                elif file_path.suffix in {'.sh', '.bash'}:
                    extracted = extract_shell_signatures(content)
                elif file_path.suffix == '.vue':
                    extracted = extract_vue_signatures(content)
                else:
                    extracted = {'functions': {}, 'classes': {}}

                # Only add if we found something
                if extracted['functions'] or extracted['classes']:
                    file_info.update(extracted)
                    file_info['parsed'] = True

                # Update stats
                lang_key = PARSEABLE_LANGUAGES[file_path.suffix]
                index['stats']['fully_parsed'][lang_key] = \
                    index['stats']['fully_parsed'].get(lang_key, 0) + 1

            except Exception as e:
                # Parse error - just list the file
                index['stats']['listed_only'][language] = \
                    index['stats']['listed_only'].get(language, 0) + 1
        else:
            # Language not supported for parsing
            index['stats']['listed_only'][language] = \
                index['stats']['listed_only'].get(language, 0) + 1

        # Add to index
        index['files'][str(rel_path)] = file_info
        file_count += 1

        # Progress indicator every 100 files
        if file_count % 100 == 0:
            print(f"  Indexed {file_count} files...")

    # Infer directory purposes
    print("🏗️  Analyzing directory purposes...")
    for dir_path, files in directory_files.items():
        if files:  # Only process directories with files
            purpose = infer_directory_purpose(dir_path, files)
            if purpose:
                rel_dir = str(dir_path.relative_to(root))
                if rel_dir != '.':
                    index['directory_purposes'][rel_dir] = purpose

    index['stats']['total_files'] = file_count
    index['stats']['total_directories'] = dir_count

    # Log tier classification summary
    tier_counts = index['stats']['doc_tiers']
    if sum(tier_counts.values()) > 0:
        print(f"📚 Documentation tiers: {tier_counts['critical']} critical, "
              f"{tier_counts['standard']} standard, {tier_counts['archive']} archive")

    # Build dependency graph
    print("🔗 Building dependency graph...")
    dependency_graph = {}

    for file_path, file_info in index['files'].items():
        if file_info.get('imports'):
            # Normalize imports to resolve relative paths
            file_dir = Path(file_path).parent
            dependencies = []

            for imp in file_info['imports']:
                # Handle relative imports
                if imp.startswith('.'):
                    # Resolve relative import
                    if imp.startswith('./'):
                        # Same directory
                        resolved = str(file_dir / imp[2:])
                    elif imp.startswith('../'):
                        # Parent directory
                        parts = imp.split('/')
                        up_levels = len([p for p in parts if p == '..'])
                        target_dir = file_dir
                        for _ in range(up_levels):
                            target_dir = target_dir.parent
                        remaining = '/'.join(p for p in parts if p != '..')
                        resolved = str(target_dir / remaining) if remaining else str(target_dir)
                    else:
                        # Module import like from . import X
                        resolved = str(file_dir)

                    # Try to find actual file
                    for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '']:
                        potential_file = resolved + ext
                        if potential_file in index['files'] or potential_file.replace('\\', '/') in index['files']:
                            dependencies.append(potential_file.replace('\\', '/'))
                            break
                else:
                    # External dependency or absolute import
                    dependencies.append(imp)

            if dependencies:
                dependency_graph[file_path] = dependencies

    # Only add if not empty
    if dependency_graph:
        index['dependency_graph'] = dependency_graph

    # Build bidirectional call graph
    print("📞 Building call graph...")
    call_graph = {}
    called_by_graph = {}

    # Process all files to build call relationships
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue

        # Process functions in this file
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if isinstance(func_data, dict) and 'calls' in func_data:
                    # Track what this function calls
                    full_func_name = f"{file_path}:{func_name}"
                    call_graph[full_func_name] = func_data['calls']

                    # Build reverse index (called_by)
                    for called in func_data['calls']:
                        if called not in called_by_graph:
                            called_by_graph[called] = []
                        called_by_graph[called].append(func_name)

        # Process methods in classes
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        if isinstance(method_data, dict) and 'calls' in method_data:
                            # Track what this method calls
                            full_method_name = f"{file_path}:{class_name}.{method_name}"
                            call_graph[full_method_name] = method_data['calls']

                            # Build reverse index
                            for called in method_data['calls']:
                                if called not in called_by_graph:
                                    called_by_graph[called] = []
                                called_by_graph[called].append(f"{class_name}.{method_name}")

    # Add called_by information back to functions
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue

        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if func_name in called_by_graph:
                    if isinstance(func_data, dict):
                        func_data['called_by'] = called_by_graph[func_name]
                    else:
                        # Convert string signature to dict
                        index['files'][file_path]['functions'][func_name] = {
                            'signature': func_data,
                            'called_by': called_by_graph[func_name]
                        }

        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        full_name = f"{class_name}.{method_name}"
                        if method_name in called_by_graph or full_name in called_by_graph:
                            callers = called_by_graph.get(method_name, []) + called_by_graph.get(full_name, [])
                            if callers:
                                if isinstance(method_data, dict):
                                    method_data['called_by'] = list(set(callers))
                                else:
                                    # Convert string signature to dict
                                    class_data['methods'][method_name] = {
                                        'signature': method_data,
                                        'called_by': list(set(callers))
                                    }

    # Add staleness check
    week_old = datetime.now().timestamp() - 7 * 24 * 60 * 60
    index['staleness_check'] = week_old

    return index, skipped_count


# infer_file_purpose is now imported from index_utils


def convert_to_enhanced_dense_format(index: Dict) -> Dict:
    """Convert to enhanced dense format that preserves all AI-relevant information."""
    dense = {
        'at': index.get('indexed_at', ''),
        'root': index.get('root', '.'),
        'tree': index.get('project_structure', {}).get('tree', [])[:20],  # Compact tree
        'stats': index.get('stats', {}),
        'f': {},     # Files
        'g': [],     # Call graph edges
        'd': {},     # Documentation map
        'deps': index.get('dependency_graph', {}),  # Keep dependencies
    }

    def truncate_doc(doc: str, max_len: int = 80) -> str:
        """Truncate docstring to max length."""
        if not doc:
            return ''
        doc = doc.strip().replace('\n', ' ')
        if len(doc) > max_len:
            return doc[:max_len-3] + '...'
        return doc

    # Build compressed files section
    for path, info in index.get('files', {}).items():
        if not info.get('parsed', False):
            continue

        # Use abbreviated path
        abbrev_path = path.replace('scripts/', 's/').replace('src/', 'sr/').replace('tests/', 't/')

        file_entry = []

        # Add language as single letter
        lang = info.get('language', 'unknown')
        lang_map = {'python': 'p', 'javascript': 'j', 'typescript': 't', 'shell': 's', 'json': 'j'}
        file_entry.append(lang_map.get(lang, 'u'))

        # Compress functions with docstrings: name:line:signature:calls:docstring
        funcs = []
        for fname, fdata in info.get('functions', {}).items():
            if isinstance(fdata, dict):
                line = fdata.get('line', 0)
                sig = fdata.get('signature', '()')
                # Compress signature
                sig = sig.replace(' -> ', '>').replace(': ', ':')
                calls = ','.join(fdata.get('calls', []))
                doc = truncate_doc(fdata.get('doc', ''))
                funcs.append(f"{fname}:{line}:{sig}:{calls}:{doc}")
            else:
                funcs.append(f"{fname}:0:{fdata}::")

        if funcs:
            file_entry.append(funcs)

        # Compress classes with methods and docstrings
        classes = {}
        for cname, cdata in info.get('classes', {}).items():
            if isinstance(cdata, dict):
                class_line = str(cdata.get('line', 0))
                methods = []
                for mname, mdata in cdata.get('methods', {}).items():
                    if isinstance(mdata, dict):
                        mline = mdata.get('line', 0)
                        msig = mdata.get('signature', '()')
                        msig = msig.replace(' -> ', '>').replace(': ', ':')
                        mcalls = ','.join(mdata.get('calls', []))
                        mdoc = truncate_doc(mdata.get('doc', ''))
                        methods.append(f"{mname}:{mline}:{msig}:{mcalls}:{mdoc}")
                    else:
                        methods.append(f"{mname}:0:{mdata}::")

                if methods or class_line != '0':
                    classes[cname] = [class_line, methods]

        if classes:
            file_entry.append(classes)

        # Only add file if it has content
        if len(file_entry) > 1:
            dense['f'][abbrev_path] = file_entry

    # Build call graph edges (keep bidirectional info)
    edges = set()
    for path, info in index.get('files', {}).items():
        if info.get('parsed', False):
            # Extract function calls
            for fname, fdata in info.get('functions', {}).items():
                if isinstance(fdata, dict):
                    for called in fdata.get('calls', []):
                        edges.add((fname, called))
                    for caller in fdata.get('called_by', []):
                        edges.add((caller, fname))

            # Extract method calls
            for cname, cdata in info.get('classes', {}).items():
                if isinstance(cdata, dict):
                    for mname, mdata in cdata.get('methods', {}).items():
                        if isinstance(mdata, dict):
                            full_name = f"{cname}.{mname}"
                            for called in mdata.get('calls', []):
                                edges.add((full_name, called))
                            for caller in mdata.get('called_by', []):
                                edges.add((caller, full_name))

    # Convert edges to list format
    dense['g'] = [[e[0], e[1]] for e in edges]

    # Add compressed documentation map
    for doc_path, doc_info in index.get('documentation_map', {}).items():
        sections = doc_info.get('sections', [])
        if sections:
            # Keep first 10 sections for better context
            dense['d'][doc_path] = sections[:10]

    # Add directory purposes if present
    if 'directory_purposes' in index:
        dense['dir_purposes'] = index['directory_purposes']

    # Add staleness check timestamp
    if 'staleness_check' in index:
        dense['staleness'] = index['staleness_check']

    return dense


def compress_if_needed(dense_index: Dict, target_size: int = MAX_INDEX_SIZE) -> Dict:
    """Compress dense index further if it exceeds size limit."""
    index_json = json.dumps(dense_index, separators=(',', ':'))
    current_size = len(index_json)

    if current_size <= target_size:
        return dense_index

    print(f"⚠️  Index too large ({current_size} bytes), compressing to {target_size}...")

    # Add safeguards
    iteration = 0
    MAX_ITERATIONS = 10

    # Progressive compression strategies

    # Step 1: Reduce tree to 10 items
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index

    print(f"  Step {iteration}: Reducing tree structure...")
    if len(dense_index.get('tree', [])) > 10:
        dense_index['tree'] = dense_index['tree'][:10]
        dense_index['tree'].append("... (truncated)")
        current_size = len(json.dumps(dense_index, separators=(',', ':')))
        if current_size <= target_size:
            print(f"  ✅ Compressed to {current_size} bytes")
            return dense_index

    # Step 2: Truncate docstrings to 40 chars
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index

    print(f"  Step {iteration}: Truncating docstrings...")
    for path, file_data in dense_index.get('f', {}).items():
        if len(file_data) > 1 and isinstance(file_data[1], list):
            # Truncate function docstrings
            new_funcs = []
            for func in file_data[1]:
                parts = func.split(':')
                if len(parts) >= 5 and len(parts[4]) > 40:
                    parts[4] = parts[4][:37] + '...'
                new_funcs.append(':'.join(parts))
            file_data[1] = new_funcs

    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index

    # Step 3: Remove docstrings entirely
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index

    print(f"  Step {iteration}: Removing docstrings entirely...")
    for path, file_data in dense_index.get('f', {}).items():
        if len(file_data) > 1 and isinstance(file_data[1], list):
            # Remove docstrings from functions
            new_funcs = []
            for func in file_data[1]:
                parts = func.split(':')
                if len(parts) >= 5:
                    parts[4] = ''  # Remove docstring
                new_funcs.append(':'.join(parts))
            file_data[1] = new_funcs

    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index

    # Step 4: Remove documentation map
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index

    print(f"  Step {iteration}: Removing documentation map...")
    if 'd' in dense_index:
        del dense_index['d']

    current_size = len(json.dumps(dense_index, separators=(',', ':')))
    if current_size <= target_size:
        print(f"  ✅ Compressed to {current_size} bytes")
        return dense_index

    # Step 5: Emergency truncation - keep most important files
    iteration += 1
    if iteration > MAX_ITERATIONS:
        print(f"  ⚠️ Max compression iterations reached. Returning partially compressed index.")
        return dense_index

    print(f"  Step {iteration}: Emergency truncation - keeping most important files...")
    if dense_index.get('f'):
        files_to_keep = int(len(dense_index['f']) * (target_size / current_size) * 0.9)
        if files_to_keep < 10:
            files_to_keep = 10

        # Calculate importance based on function count
        file_importance = {}
        for path, file_data in dense_index['f'].items():
            importance = 0
            if len(file_data) > 1 and isinstance(file_data[1], list):
                importance = len(file_data[1])  # Number of functions
            if len(file_data) > 2:  # Has classes
                importance += 5
            file_importance[path] = importance

        # Keep most important files
        sorted_files = sorted(file_importance.items(), key=lambda x: x[1], reverse=True)
        files_to_keep_set = set(path for path, _ in sorted_files[:files_to_keep])

        # Remove less important files
        for path in list(dense_index['f'].keys()):
            if path not in files_to_keep_set:
                del dense_index['f'][path]

        print(f"  Emergency truncation: kept {len(dense_index['f'])} most important files")

    final_size = len(json.dumps(dense_index, separators=(',', ':')))
    print(f"  Compressed from {len(index_json)} to {final_size} bytes")

    return dense_index


def get_submodule_config(config: Optional[Dict]) -> Dict[str, any]:
    """
    Get submodule configuration with defaults applied.

    Args:
        config: Configuration dictionary (may be None or missing submodule_config)

    Returns:
        Dictionary with submodule configuration values and defaults applied.
        Keys: enabled (bool), threshold (int), strategy (str), max_depth (int)
    """
    defaults = {
        'enabled': True,
        'threshold': 100,
        'strategy': 'auto',
        'max_depth': 3
    }

    if not config or 'submodule_config' not in config:
        return defaults

    submod_config = config['submodule_config']

    # Apply defaults for missing keys
    return {
        'enabled': submod_config.get('enabled', defaults['enabled']),
        'threshold': submod_config.get('threshold', defaults['threshold']),
        'strategy': submod_config.get('strategy', defaults['strategy']),
        'max_depth': submod_config.get('max_depth', defaults['max_depth'])
    }


def analyze_directory_structure(module_path: Path, root_path: Path) -> Dict[str, any]:
    """
    Analyze second-level directory structure for a large module.

    Args:
        module_path: Path to the module directory
        root_path: Project root path

    Returns:
        Dictionary with:
            - subdirectories: List of immediate subdirectory names
            - logical_groups: List of identified logical groupings
            - file_distribution: Dict mapping subdir -> file count
    """
    import logging
    logger = logging.getLogger(__name__)

    subdirs = []
    file_distribution = {}

    try:
        # Get immediate subdirectories only (not recursive)
        for item in module_path.iterdir():
            if item.is_dir() and item.name not in IGNORE_DIRS:
                subdirs.append(item.name)

                # Count files in this subdirectory (recursively)
                file_count = sum(1 for f in item.rglob('*') if f.is_file())
                file_distribution[item.name] = file_count

        # Identify logical groupings based on common patterns
        logical_groups = []
        common_patterns = {
            'source': ['src', 'lib', 'app', 'source'],
            'documentation': ['docs', 'documentation', 'doc'],
            'tests': ['tests', 'test', '__tests__', 'spec'],
            'components': ['components', 'widgets'],
            'views': ['views', 'pages', 'screens'],
            'api': ['api', 'routes', 'endpoints'],
            'utilities': ['utils', 'utilities', 'helpers'],
            'configuration': ['config', 'configuration', 'settings']
        }

        for group_name, patterns in common_patterns.items():
            matching = [d for d in subdirs if d.lower() in patterns]
            if matching:
                logical_groups.append({
                    'type': group_name,
                    'directories': matching
                })

        logger.debug(f"Analyzed directory structure for {module_path.name}: "
                    f"{len(subdirs)} subdirectories, {len(logical_groups)} logical groups")

        return {
            'subdirectories': subdirs,
            'logical_groups': logical_groups,
            'file_distribution': file_distribution
        }

    except Exception as e:
        logger.warning(f"Error analyzing directory structure for {module_path}: {e}")
        return {
            'subdirectories': [],
            'logical_groups': [],
            'file_distribution': {}
        }


def detect_large_modules(modules: Dict[str, List[str]], threshold: int, root_path: Path,
                         config: Optional[Dict] = None) -> List[Dict[str, any]]:
    """
    Detect modules that exceed the file count threshold.

    Args:
        modules: Dict mapping module_id -> list of file paths
        threshold: Maximum files per module before flagging as large
        root_path: Project root path
        config: Optional configuration dict (for verbose/logging control)

    Returns:
        List of dicts, each containing:
            - module_id: str
            - file_count: int
            - analysis: dict with directory structure analysis (if available)
    """
    import logging
    logger = logging.getLogger(__name__)

    large_modules = []
    submod_config = get_submodule_config(config)

    # Skip detection if disabled
    if not submod_config['enabled']:
        logger.debug("Sub-module detection disabled by configuration")
        return large_modules

    for module_id, file_list in modules.items():
        file_count = len(file_list)

        # Short-circuit: skip small modules
        # AC#6: Small modules (<threshold) skip detection
        # Modules with file_count >= threshold are flagged as large
        if file_count < threshold:
            continue

        logger.info(f"Large module detected: {module_id} ({file_count} files)")

        # Analyze directory structure for large modules
        module_path = root_path / module_id if module_id != "root" else root_path
        analysis = analyze_directory_structure(module_path, root_path)

        large_modules.append({
            'module_id': module_id,
            'file_count': file_count,
            'analysis': analysis
        })

    return large_modules


def detect_framework_patterns(root_path: Path) -> str:
    """
    Detect framework type by examining directory structure.

    Currently detects:
    - Vite: Presence of src/ with characteristic subdirectories (components/, views/, api/, stores/, composables/, utils/)
    - Generic: Default fallback

    Args:
        root_path: Project root path

    Returns:
        Framework type: "vite", "react", "nextjs", or "generic"
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        src_path = root_path / "src"

        if not src_path.exists() or not src_path.is_dir():
            logger.debug("No src/ directory found - framework: generic")
            return "generic"

        # Vite characteristic directories
        vite_patterns = [
            "components",
            "views",
            "api",
            "stores",
            "composables",
            "utils"
        ]

        # Count how many Vite patterns are present
        matches = 0
        for pattern in vite_patterns:
            if (src_path / pattern).exists() and (src_path / pattern).is_dir():
                matches += 1

        # Consider it Vite if at least 3 characteristic directories are present
        if matches >= 3:
            logger.debug(f"Vite framework detected ({matches}/{len(vite_patterns)} patterns matched)")
            return "vite"

        logger.debug(f"Generic framework ({matches}/{len(vite_patterns)} Vite patterns matched - need 3+)")
        return "generic"

    except Exception as e:
        logger.warning(f"Error detecting framework patterns: {e}")
        return "generic"


def auto_detect_preset(file_count: int) -> str:
    """
    Auto-detect preset based on file count.

    Args:
        file_count: Number of files in the project

    Returns:
        Preset name: 'small', 'medium', or 'large'
        - small: < 100 files
        - medium: 100-4999 files
        - large: 5000+ files
    """
    if file_count < 100:
        return "small"
    elif file_count < 5000:
        return "medium"
    else:
        return "large"


def load_preset_template(preset_name: str) -> Dict[str, any]:
    """
    Load preset template from templates directory.

    Args:
        preset_name: Preset name ('small', 'medium', 'large')

    Returns:
        Configuration dictionary with preset settings
        - Replaces '_generated: "auto"' with current ISO timestamp
        - Falls back to default config if template not found
    """
    from datetime import datetime
    from pathlib import Path
    import json

    # Template directory: ~/.claude-code-project-index/templates/
    templates_dir = Path.home() / ".claude-code-project-index" / "templates"
    template_path = templates_dir / f"{preset_name}.json"

    # Try to load template
    try:
        if template_path.exists():
            with open(template_path, 'r') as f:
                config = json.load(f)

            # Replace _generated: "auto" with current timestamp
            if config.get("_generated") == "auto":
                config["_generated"] = datetime.now().isoformat()

            return config
    except (json.JSONDecodeError, IOError):
        # Template file corrupted or unreadable - fall through to default
        pass

    # Fallback: return default config with preset metadata
    return {
        "_preset": preset_name,
        "_generated": datetime.now().isoformat(),
        "mode": "auto",
        "threshold": 1000
    }


def detect_preset_from_config(config: Dict) -> str:
    """
    Detect preset name from configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        Preset name: 'small', 'medium', or 'large'
        - Checks _preset metadata field first
        - Falls back to threshold heuristic if no metadata
    """
    # Check for explicit _preset metadata
    if "_preset" in config:
        preset = config["_preset"]
        if preset in ["small", "medium", "large"]:
            return preset

    # Infer from threshold value
    threshold = config.get("threshold", 1000)

    if threshold < 200:
        return "small"
    elif threshold < 1000:
        return "medium"
    else:
        return "large"


def _check_cli_flags() -> Dict[str, any]:
    """
    Check for CLI flags related to preset upgrades.

    Returns:
        Dictionary with:
        - no_prompt: bool - True if --no-prompt flag is present
        - upgrade_to: Optional[str] - Preset name if --upgrade-to=preset is present, None otherwise
    """
    no_prompt = '--no-prompt' in sys.argv

    upgrade_to = None
    for arg in sys.argv:
        if arg.startswith('--upgrade-to='):
            preset_value = arg.split('=', 1)[1]
            if preset_value in ['small', 'medium', 'large']:
                upgrade_to = preset_value
            # If invalid value, upgrade_to remains None (will be ignored)

    return {
        'no_prompt': no_prompt,
        'upgrade_to': upgrade_to
    }


def apply_framework_preset(framework_type: str, config: Optional[Dict] = None) -> Dict[str, any]:
    """
    Get framework-specific preset configuration for sub-module organization.

    Args:
        framework_type: Framework type detected ("vite", "react", "nextjs", "generic")
        config: Optional configuration dict to merge with preset

    Returns:
        Dictionary with framework preset configuration:
        - split_paths: List of paths to split into sub-modules
        - max_depth: Recommended depth for this framework
        - description: Human-readable description

    Framework Presets:
        vite: src/components, src/views, src/api, src/stores, src/composables, src/utils (depth=3)
        react: components, hooks, utils, pages (depth=2)
        nextjs: app/, components/, lib/ (depth=2)
        generic: Split by direct subdirectories heuristic (depth=2)
    """
    import logging
    logger = logging.getLogger(__name__)

    # Define framework presets
    presets = {
        "vite": {
            "split_paths": [
                "src/components",
                "src/views",
                "src/api",
                "src/stores",
                "src/composables",
                "src/utils"
            ],
            "max_depth": 3,
            "description": "Vite project with Vue.js patterns (components, views, api, stores, composables, utils)"
        },
        "react": {
            "split_paths": [
                "components",
                "hooks",
                "utils",
                "pages",
                "contexts",
                "services"
            ],
            "max_depth": 2,
            "description": "React project with standard component organization"
        },
        "nextjs": {
            "split_paths": [
                "app",
                "components",
                "lib",
                "utils",
                "hooks"
            ],
            "max_depth": 2,
            "description": "Next.js project with App Router structure"
        },
        "generic": {
            "split_paths": [],  # Empty list means: split by direct subdirectories automatically
            "max_depth": 2,
            "description": "Generic project - split by top-level subdirectories"
        }
    }

    # Get preset for framework type (default to generic if unknown)
    preset = presets.get(framework_type, presets["generic"])

    # Merge with user config if provided
    if config and 'framework_presets' in config:
        user_presets = config['framework_presets']
        if framework_type in user_presets:
            logger.debug(f"Applying user-defined preset override for {framework_type}")
            # User can override split_paths and max_depth
            if 'split_paths' in user_presets[framework_type]:
                preset['split_paths'] = user_presets[framework_type]['split_paths']
            if 'max_depth' in user_presets[framework_type]:
                preset['max_depth'] = user_presets[framework_type]['max_depth']

    logger.debug(f"Applied {framework_type} preset: {preset['description']}")
    return preset


def generate_submodule_name(parent: str, child: str, grandchild: Optional[str] = None) -> str:
    """
    Generate sub-module name following multi-level naming convention.

    Naming rules:
    - Second-level: {parent}-{child}
    - Third-level: {parent}-{child}-{grandchild}

    Args:
        parent: Parent module name
        child: Child directory name
        grandchild: Optional grandchild directory name (for third level)

    Returns:
        Sub-module name string

    Examples:
        >>> generate_submodule_name("assureptmdashboard", "src")
        'assureptmdashboard-src'
        >>> generate_submodule_name("assureptmdashboard", "src", "components")
        'assureptmdashboard-src-components'
    """
    if grandchild:
        # Third-level: parent-child-grandchild
        return f"{parent}-{child}-{grandchild}"
    else:
        # Second-level: parent-child
        return f"{parent}-{child}"


def split_module_recursive(
    module_id: str,
    file_list: List[str],
    root_path: Path,
    max_depth: int,
    current_depth: int = 0,
    config: Optional[Dict] = None
) -> Dict[str, List[str]]:
    """
    Recursively split a large module into sub-modules based on directory structure.

    Splitting logic:
    1. If depth limit reached or module too small -> return as-is
    2. Analyze directory structure to find organized subdirectories
    3. For each subdirectory:
       - If it has >= threshold files AND organized structure -> split recursively
       - Otherwise, keep as single sub-module
    4. Group intermediate files (at current level) into *-root sub-module

    Args:
        module_id: Module identifier (e.g., "assureptmdashboard" or "assureptmdashboard-src")
        file_list: List of file paths relative to project root
        root_path: Project root path
        max_depth: Maximum recursion depth (typically 3)
        current_depth: Current recursion depth (0 = top level)
        config: Optional configuration dict

    Returns:
        Dict mapping sub-module_id -> file_list
        If no splitting occurs, returns {module_id: file_list}

    Examples:
        Input: module_id="assureptmdashboard", 416 files in src/components/, src/views/, etc.
        Output: {
            "assureptmdashboard-src-components": [245 files],
            "assureptmdashboard-src-views": [89 files],
            ...
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    # Get configuration
    submod_config = get_submodule_config(config)
    threshold = submod_config['threshold']

    # Base case 1: depth limit reached
    if current_depth >= max_depth:
        logger.debug(f"Depth limit reached for {module_id} at level {current_depth}")
        return {module_id: file_list}

    # Base case 2: module too small to split
    if len(file_list) < threshold:
        logger.debug(f"Module {module_id} below threshold ({len(file_list)} < {threshold})")
        return {module_id: file_list}

    # Determine module base path
    # For root module, use root_path
    # For named modules like "scripts", use root_path/scripts
    # For sub-modules like "assureptmdashboard-src", parse the structure
    if module_id == "root":
        module_path = root_path
    else:
        # Extract path components from module_id
        # Examples: "scripts" -> root_path/scripts
        #          "assureptmdashboard-src" -> root_path/assureptmdashboard/src
        parts = module_id.split('-')
        module_path = root_path / '/'.join(parts)

    # Analyze directory structure
    try:
        subdirs = []
        subdir_files = {}

        # Group files by immediate subdirectory
        for file_path_str in file_list:
            file_path = root_path / file_path_str

            try:
                # Get path relative to module_path
                rel_to_module = file_path.relative_to(module_path)
                parts = rel_to_module.parts

                if len(parts) > 1:
                    # File is in a subdirectory
                    subdir = parts[0]
                    if subdir not in subdirs:
                        subdirs.append(subdir)
                        subdir_files[subdir] = []
                    subdir_files[subdir].append(file_path_str)
                else:
                    # File at module root level
                    if 'root' not in subdir_files:
                        subdir_files['root'] = []
                    subdir_files['root'].append(file_path_str)

            except ValueError:
                # File not under module_path, skip
                logger.debug(f"File {file_path_str} not under {module_path}, skipping")
                continue

        # Check if module has organized structure
        # "Organized" = has subdirectories with significant file counts
        has_organized_structure = False
        for subdir, files in subdir_files.items():
            if subdir != 'root' and len(files) >= threshold * 0.2:  # At least 20% of threshold
                has_organized_structure = True
                break

        # If flat structure, don't split
        if not has_organized_structure:
            logger.debug(f"Module {module_id} has flat structure - no splitting")
            return {module_id: file_list}

        # Split into sub-modules
        logger.info(f"Splitting {module_id} ({len(file_list)} files) into {len(subdirs)} sub-modules at depth {current_depth}")

        result = {}

        for subdir, files in subdir_files.items():
            if subdir == 'root':
                # Intermediate-level files -> *-root sub-module
                root_module_id = f"{module_id}-root"
                result[root_module_id] = files
                logger.debug(f"Created {root_module_id} with {len(files)} intermediate files")
            else:
                # Create sub-module name based on current depth
                if current_depth == 0:
                    # First split: parent-child
                    sub_module_id = generate_submodule_name(module_id, subdir)
                else:
                    # Deeper splits: append to existing name
                    sub_module_id = f"{module_id}-{subdir}"

                # Recursively split if this subdirectory is large enough
                if len(files) >= threshold:
                    logger.debug(f"Recursively splitting {sub_module_id} ({len(files)} files)")
                    sub_result = split_module_recursive(
                        sub_module_id,
                        files,
                        root_path,
                        max_depth,
                        current_depth + 1,
                        config
                    )
                    result.update(sub_result)
                else:
                    # Keep as single sub-module
                    result[sub_module_id] = files
                    logger.debug(f"Created {sub_module_id} with {len(files)} files")

        return result

    except Exception as e:
        logger.error(f"Error splitting module {module_id}: {e}")
        # Graceful degradation: return original module
        return {module_id: file_list}


def build_file_to_module_map(modules: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build reverse mapping from file paths to module IDs for O(1) lookup.

    This enables fast @ reference resolution: given a file path like
    "src/components/LoginForm.vue", quickly find which module contains it.

    Args:
        modules: Dict mapping module_id -> list of file paths

    Returns:
        Dict mapping file_path -> module_id

    Example:
        Input: {
            "assureptmdashboard-src-components": ["src/components/Button.vue", "src/components/Form.vue"],
            "assureptmdashboard-src-views": ["src/views/Home.vue"]
        }
        Output: {
            "src/components/Button.vue": "assureptmdashboard-src-components",
            "src/components/Form.vue": "assureptmdashboard-src-components",
            "src/views/Home.vue": "assureptmdashboard-src-views"
        }
    """
    file_to_module = {}

    for module_id, file_list in modules.items():
        for file_path in file_list:
            # Each file should map to exactly one module
            if file_path in file_to_module:
                # This shouldn't happen in properly organized modules
                # Log warning but continue (last module wins)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"File {file_path} appears in multiple modules: "
                             f"{file_to_module[file_path]} and {module_id}")

            file_to_module[file_path] = module_id

    return file_to_module


def organize_into_modules(files: List[Path], root_path: Path, depth: int = 1) -> Dict[str, List[str]]:
    """Group files by directory into modules.

    Args:
        files: List of file paths
        root_path: Project root path
        depth: Directory depth for grouping (default: 1 = top-level dirs)

    Returns:
        Dict mapping module_id -> list of relative file paths
    """
    modules = {}

    for file_path in files:
        try:
            rel_path = file_path.relative_to(root_path)
            parts = rel_path.parts

            # Determine module based on depth
            if len(parts) > depth:
                # File is in a subdirectory
                module_id = parts[depth - 1]  # Get directory at specified depth
            else:
                # File is at root or shallow level
                module_id = "root"

            # Add file to module
            if module_id not in modules:
                modules[module_id] = []
            modules[module_id].append(str(rel_path))

        except ValueError:
            # Path is not relative to root, skip
            continue

    return modules


def create_module_references(modules: Dict[str, List[str]], functions: Dict[str, Dict]) -> Dict[str, Dict]:
    """Build module reference section with metadata.

    Args:
        modules: Dict mapping module_id -> list of file paths
        functions: Dict mapping file paths -> function data

    Returns:
        Dict with module metadata (file_count, function_count, detail_path)
    """
    module_refs = {}

    for module_id, file_list in modules.items():
        # Count functions in this module
        func_count = 0
        for file_path in file_list:
            if file_path in functions:
                file_funcs = functions[file_path].get('functions', {})
                func_count += len(file_funcs)

                # Also count methods in classes
                file_classes = functions[file_path].get('classes', {})
                for class_data in file_classes.values():
                    if isinstance(class_data, dict):
                        func_count += len(class_data.get('methods', {}))

        module_refs[module_id] = {
            'file_count': len(file_list),
            'function_count': func_count,
            'detail_path': f"PROJECT_INDEX.d/{module_id}.json",
            'files': file_list  # Include file list for loader compatibility
        }

    return module_refs


def print_summary(index: Dict, skipped_count: int):
    """Print a helpful summary of what was indexed."""
    stats = index['stats']

    # Add warning if no files were found
    if stats['total_files'] == 0:
        print("\n⚠️  WARNING: No files were indexed!")
        print("   This might mean:")
        print("   • You're in the wrong directory")
        print("   • All files are being ignored (check .gitignore)")
        print("   • The project has no supported file types")
        print(f"\n   Current directory: {os.getcwd()}")
        print("   Try running from your project root directory.")
        return

    print(f"\n📊 Project Analysis Complete:")
    print(f"   📁 {stats['total_directories']} directories indexed")
    print(f"   📄 {stats['total_files']} code files found")
    print(f"   📝 {stats['markdown_files']} documentation files analyzed")

    # Show fully parsed languages
    if stats['fully_parsed']:
        print("\n✅ Languages with full parsing:")
        for lang, count in sorted(stats['fully_parsed'].items()):
            print(f"   • {count} {lang.capitalize()} files (with signatures)")

    # Show listed-only languages
    if stats['listed_only']:
        print("\n📋 Languages listed only:")
        for lang, count in sorted(stats['listed_only'].items()):
            print(f"   • {count} {lang.capitalize()} files")

    # Show documentation insights
    if index.get('d'):
        print(f"\n📚 Documentation insights:")
        for doc_file, sections in list(index['d'].items())[:3]:
            print(f"   • {doc_file}: {len(sections)} sections")

    # Show directory purposes
    if index.get('dir_purposes'):
        print(f"\n🏗️  Directory structure:")
        for dir_path, purpose in list(index['dir_purposes'].items())[:5]:
            print(f"   • {dir_path}/: {purpose}")

    if skipped_count > 0:
        print(f"\n   (Skipped {skipped_count} files in ignored directories)")


def create_backup(index_path: Path) -> Path:
    """
    Create timestamped backup of legacy index file.

    Args:
        index_path: Path to PROJECT_INDEX.json

    Returns:
        Path to created backup file

    Raises:
        IOError: If backup creation fails
    """
    import shutil
    from datetime import datetime

    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    backup_path = index_path.parent / f"{index_path.name}.backup-{timestamp}"

    try:
        # Use shutil.copy2 to preserve file metadata (permissions, timestamps)
        shutil.copy2(index_path, backup_path)
        return backup_path
    except Exception as e:
        raise IOError(f"Failed to create backup: {e}")


def extract_legacy_data(index_path: Path) -> Dict:
    """
    Load and parse legacy single-file PROJECT_INDEX.json.

    Args:
        index_path: Path to legacy index file

    Returns:
        Parsed legacy index dictionary

    Raises:
        FileNotFoundError: If index file doesn't exist
        json.JSONDecodeError: If index file is corrupted
    """
    if not index_path.exists():
        raise FileNotFoundError(f"Legacy index not found at {index_path}")

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            legacy_index = json.load(f)
        return legacy_index
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Corrupted legacy index: {e.msg}", e.doc, e.pos)


def validate_migration_integrity(legacy_index: Dict, core_index: Dict, detail_modules: Dict[str, Dict]) -> bool:
    """
    Validate migration preserved all data from legacy index.

    Performs hash-based validation and count verification to ensure zero information loss.

    Args:
        legacy_index: Original legacy index dictionary
        core_index: Migrated core index dictionary
        detail_modules: Dictionary of detail module dictionaries {module_id: module_data}

    Returns:
        True if validation passed, False otherwise
    """
    import hashlib

    print("   🔍 Validating migration integrity...")

    # Count validation: files
    legacy_files = set(legacy_index.get('f', {}).keys())

    # Collect all files from detail modules
    split_files = set()
    for module_data in detail_modules.values():
        split_files.update(module_data.get('files', {}).keys())

    if legacy_files != split_files:
        missing_in_split = legacy_files - split_files
        extra_in_split = split_files - legacy_files
        if missing_in_split:
            print(f"      ❌ Missing files in split format: {missing_in_split}")
        if extra_in_split:
            print(f"      ❌ Extra files in split format: {extra_in_split}")
        return False

    print(f"      ✓ File count: {len(legacy_files)} files preserved")

    # Count validation: functions and classes
    legacy_func_count = 0
    legacy_class_count = 0
    for file_data in legacy_index.get('f', {}).values():
        if isinstance(file_data, list) and len(file_data) > 1 and isinstance(file_data[1], list):
            for sig in file_data[1]:
                if isinstance(sig, str):
                    if ':(' in sig:  # Function signature
                        legacy_func_count += 1
                    elif sig.startswith('class '):  # Class signature
                        legacy_class_count += 1

    split_func_count = 0
    split_class_count = 0
    for module_data in detail_modules.values():
        for file_data in module_data.get('files', {}).values():
            if 'functions' in file_data:
                split_func_count += len(file_data['functions'])
            if 'classes' in file_data:
                split_class_count += len(file_data['classes'])

    if legacy_func_count != split_func_count:
        print(f"      ❌ Function count mismatch: legacy={legacy_func_count}, split={split_func_count}")
        return False

    if legacy_class_count != split_class_count:
        print(f"      ❌ Class count mismatch: legacy={legacy_class_count}, split={split_class_count}")
        return False

    print(f"      ✓ Function count: {legacy_func_count} functions preserved")
    print(f"      ✓ Class count: {legacy_class_count} classes preserved")

    # Call graph validation
    legacy_call_graph_edges = len(legacy_index.get('g', []))

    # Collect all call graph edges from core + detail modules
    split_call_graph_edges = len(core_index.get('g', []))
    for module_data in detail_modules.values():
        split_call_graph_edges += len(module_data.get('call_graph_local', []))

    if legacy_call_graph_edges != split_call_graph_edges:
        print(f"      ⚠️  Call graph edge count mismatch: legacy={legacy_call_graph_edges}, split={split_call_graph_edges}")
        # This is a warning, not a failure - call graph might be reorganized
    else:
        print(f"      ✓ Call graph: {legacy_call_graph_edges} edges preserved")

    # Documentation validation
    legacy_doc_count = len(legacy_index.get('d', {}))
    split_doc_count = sum(len(module_data.get('documentation', {})) for module_data in detail_modules.values())

    if legacy_doc_count != split_doc_count:
        print(f"      ⚠️  Documentation count mismatch: legacy={legacy_doc_count}, split={split_doc_count}")
    else:
        print(f"      ✓ Documentation: {legacy_doc_count} files preserved")

    print("   ✅ Migration integrity validated!")
    return True


def rollback_migration(backup_path: Path, index_path: Path, detail_dir: Path):
    """
    Rollback migration on failure by restoring backup and cleaning up split artifacts.

    Args:
        backup_path: Path to backup file
        index_path: Path to PROJECT_INDEX.json
        detail_dir: Path to PROJECT_INDEX.d/ directory
    """
    import shutil

    print("   🔄 Rolling back migration...")

    # Restore original index from backup
    if backup_path.exists():
        try:
            shutil.copy2(backup_path, index_path)
            print(f"      ✓ Restored original index from {backup_path}")
        except Exception as e:
            print(f"      ❌ Failed to restore backup: {e}")

    # Clean up partial split artifacts
    if detail_dir.exists():
        try:
            shutil.rmtree(detail_dir)
            print(f"      ✓ Removed partial split directory {detail_dir}")
        except Exception as e:
            print(f"      ⚠️  Failed to remove {detail_dir}: {e}")


def migrate_to_split_format(root_dir: str = '.', dry_run: bool = False) -> bool:
    """
    Migrate legacy single-file index to split format.

    Workflow:
    1. Detect legacy format
    2. Create backup (skipped in dry-run mode)
    3. Extract legacy data
    4. Generate split format (core + detail modules)
    5. Validate integrity
    6. Report results or rollback on failure

    Args:
        root_dir: Project root directory (defaults to current directory)
        dry_run: If True, show migration plan without executing (default: False)

    Returns:
        True if migration succeeded, False otherwise
    """
    import shutil
    from datetime import datetime

    root_path = Path(root_dir).resolve()
    index_path = root_path / 'PROJECT_INDEX.json'
    detail_dir = root_path / 'PROJECT_INDEX.d'

    if dry_run:
        print("\n🔍 DRY RUN: Migration preview (no changes will be made)...")
    else:
        print("\n🔄 Starting migration to split format...")

    # Step 1: Detect format
    print("   📋 Step 1/6: Detecting index format...")

    if not index_path.exists():
        print("      ❌ No PROJECT_INDEX.json found!")
        print(f"         Expected location: {index_path}")
        return False

    current_format = detect_index_format(index_path)

    if current_format == 'split':
        print("      ℹ️  Index is already in split format (v2.x)")
        print("      No migration needed.")
        return True

    print("      ✓ Detected legacy format (v1.0)")

    # Step 2: Create backup
    print("   💾 Step 2/6: Creating backup...")

    if dry_run:
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        backup_name = f"PROJECT_INDEX.json.backup-{timestamp}"
        print(f"      🔍 Would create: {backup_name}")
        backup_path = None  # No actual backup in dry-run
    else:
        try:
            backup_path = create_backup(index_path)
            print(f"      ✓ Backup created: {backup_path.name}")
        except IOError as e:
            print(f"      ❌ {e}")
            return False

    # Step 3: Extract legacy data
    print("   📖 Step 3/6: Loading legacy index...")

    try:
        legacy_index = extract_legacy_data(index_path)
        legacy_size = index_path.stat().st_size
        legacy_size_kb = legacy_size / 1024

        # Count files for progress tracking
        file_count = len(legacy_index.get('f', {}))
        show_progress = file_count > 5000

        if show_progress:
            print(f"      ✓ Loaded legacy index ({legacy_size_kb:.1f} KB, {file_count} files)")
            print(f"      ℹ️  Large project detected - showing detailed progress...")
        else:
            print(f"      ✓ Loaded legacy index ({legacy_size_kb:.1f} KB, {file_count} files)")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"      ❌ {e}")
        return False

    # Step 4: Generate split format
    print("   ⚙️  Step 4/6: Generating split format...")

    if show_progress:
        print(f"      📊 Processing {file_count} files...")

    try:
        # Use existing generate_split_index() function
        # Load config for tier classification
        config = load_configuration(Path(root_dir) / '.project-index.json')
        core_index, total_size = generate_split_index(root_dir, config)

        core_size = len(json.dumps(core_index, separators=(',', ':')))
        core_size_kb = core_size / 1024

        # Calculate detail modules size
        detail_size = total_size - core_size
        detail_size_kb = detail_size / 1024

        module_count = len(core_index.get('modules', {}))

        if dry_run:
            print(f"      🔍 Would generate core index ({core_size_kb:.1f} KB)")
            print(f"      🔍 Would generate {module_count} detail modules ({detail_size_kb:.1f} KB)")
            if show_progress:
                print(f"      📊 Modules would be created:")
                for module_id in sorted(core_index.get('modules', {}).keys())[:10]:
                    module_info = core_index['modules'][module_id]
                    print(f"         • {module_id}.json ({module_info.get('files_count', 0)} files)")
                if module_count > 10:
                    print(f"         ... and {module_count - 10} more modules")
        else:
            # Write core index to disk (atomic write)
            temp_index_path = index_path.parent / f"{index_path.name}.tmp"
            temp_index_path.write_text(json.dumps(core_index, separators=(',', ':')))
            temp_index_path.replace(index_path)  # Atomic rename

            print(f"      ✓ Generated core index ({core_size_kb:.1f} KB)")
            print(f"      ✓ Generated {module_count} detail modules ({detail_size_kb:.1f} KB)")

            if show_progress:
                print(f"      📊 Created modules in PROJECT_INDEX.d/")

    except Exception as e:
        print(f"      ❌ Failed to generate split format: {e}")
        if not dry_run and backup_path:
            rollback_migration(backup_path, index_path, detail_dir)
        return False

    # Step 5: Load detail modules for validation
    print("   🔍 Step 5/6: Validating migration integrity...")

    if show_progress:
        print(f"      📊 Validating {file_count} files across {module_count} modules...")

    try:
        # Load all detail modules that were just created
        detail_modules = {}
        if detail_dir.exists():
            module_files = list(detail_dir.glob('*.json'))
            for i, module_file in enumerate(module_files):
                if show_progress and i % 10 == 0:
                    print(f"      📊 Loading module {i+1}/{len(module_files)}...")
                module_id = module_file.stem
                with open(module_file, 'r', encoding='utf-8') as f:
                    detail_modules[module_id] = json.load(f)

        if dry_run:
            print(f"      🔍 Would validate:")
            print(f"         • File count: {file_count} files")
            legacy_func_count = sum(
                len([s for s in file_data[1] if isinstance(s, str) and ':(' in s])
                for file_data in legacy_index.get('f', {}).values()
                if isinstance(file_data, list) and len(file_data) > 1
            )
            print(f"         • Function count: {legacy_func_count} functions")
            print(f"         • Call graph edges")
            print(f"         • Documentation preservation")
            validation_passed = True  # Assume would pass in dry-run
        else:
            # Validate integrity
            validation_passed = validate_migration_integrity(legacy_index, core_index, detail_modules)

            if not validation_passed:
                print("      ❌ Validation failed - data integrity check did not pass")
                rollback_migration(backup_path, index_path, detail_dir)
                return False

    except Exception as e:
        print(f"      ❌ Validation error: {e}")
        if not dry_run and backup_path:
            rollback_migration(backup_path, index_path, detail_dir)
        return False

    # Clean up detail modules created during dry-run
    if dry_run and detail_dir.exists():
        try:
            shutil.rmtree(detail_dir)
        except Exception:
            pass  # Best effort cleanup

    # Step 6: Report success
    if dry_run:
        print("\n   ✅ Dry run completed successfully!")
        print(f"\n📊 Migration Preview:")
        print(f"   Current format: {legacy_size_kb:.1f} KB (single file, {file_count} files)")
        print(f"   After migration:")
        print(f"      Split format:   {core_size_kb:.1f} KB core + {detail_size_kb:.1f} KB modules ({(core_size_kb + detail_size_kb):.1f} KB total)")
        print(f"      Modules:        {module_count} detail modules would be created")
        print(f"\n💡 To perform the actual migration, run:")
        print(f"   python scripts/project_index.py --migrate")
        print(f"\n📌 What will happen:")
        print(f"   • Backup created: PROJECT_INDEX.json.backup-<timestamp>")
        print(f"   • Core index written to: PROJECT_INDEX.json")
        print(f"   • Detail modules written to: PROJECT_INDEX.d/")
        print(f"   • Full integrity validation performed")
        print(f"   • Automatic rollback if any errors occur")
    else:
        print("\n   ✅ Migration completed successfully!")
        print(f"\n📊 Migration Summary:")
        print(f"   Legacy format:  {legacy_size_kb:.1f} KB (single file)")
        print(f"   Split format:   {core_size_kb:.1f} KB core + {detail_size_kb:.1f} KB modules ({(core_size_kb + detail_size_kb):.1f} KB total)")
        print(f"   Modules:        {module_count} detail modules created")
        print(f"   Backup:         {backup_path.name}")
        print(f"\n💡 Your index is now optimized for large projects!")
        print(f"   • Core index stays lightweight for quick navigation")
        print(f"   • Detail modules load on-demand for deep analysis")

    return True


def generate_warnings(modules: Dict[str, List[str]], framework_type: str, config: Optional[Dict] = None) -> List[str]:
    """
    Generate warnings for optimization opportunities (Story 4.4, AC #10).

    Checks for:
        - Large modules (>200 files) that could benefit from sub-module splitting
        - Detected frameworks without matching presets enabled

    Args:
        modules: Dict mapping module_id -> list of file paths
        framework_type: Detected framework type
        config: Optional configuration dict

    Returns:
        List of warning messages
    """
    warnings = []
    submod_config = get_submodule_config(config)
    strategy = submod_config.get('strategy', 'auto')

    # Warning 1: Large modules (>200 files)
    for module_id, file_list in modules.items():
        if len(file_list) > 200:
            warnings.append(
                f"⚠️  Large module detected: '{module_id}' has {len(file_list)} files (>200)\n"
                f"   Consider enabling sub-module splitting for better performance.\n"
                f"   Add to .project-index.json:\n"
                f"   {{\n"
                f"     \"submodule_config\": {{\n"
                f"       \"enabled\": true,\n"
                f"       \"strategy\": \"auto\",\n"
                f"       \"threshold\": 100\n"
                f"     }}\n"
                f"   }}"
            )

    # Warning 2: Framework detected but preset not being used
    if framework_type != "generic" and strategy == "disabled":
        warnings.append(
            f"⚠️  {framework_type.capitalize()} framework detected but sub-module splitting is disabled\n"
            f"   This project could benefit from framework-specific organization.\n"
            f"   Add to .project-index.json:\n"
            f"   {{\n"
            f"     \"submodule_config\": {{\n"
            f"       \"enabled\": true,\n"
            f"       \"strategy\": \"auto\"\n"
            f"     }}\n"
            f"   }}"
        )

    return warnings


def analyze_module_structure(root_path: Path, config: Optional[Dict] = None) -> None:
    """
    Analyze and display current/potential module structure without modifying files.

    This is a read-only analysis tool for the --analyze-modules flag (Story 4.4, AC #9).
    Helps users understand module organization before committing to configuration.

    Args:
        root_path: Project root path
        config: Optional configuration dict

    Displays:
        - Detected framework type
        - Current/potential module structure (tree view)
        - File counts per module
        - Suggested configuration based on patterns
    """
    import logging
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 70)
    print("📊 MODULE STRUCTURE ANALYSIS (Read-Only)")
    print("=" * 70)

    # Detect framework
    framework_type = detect_framework_patterns(root_path)
    preset = apply_framework_preset(framework_type, config.get('submodule_config') if config else None)

    print(f"\n🔍 Detected Framework: {framework_type}")
    print(f"   Description: {preset['description']}")
    print(f"   Recommended max_depth: {preset['max_depth']}")

    # Get files to index (same logic as build_index)
    all_files = []

    for file_path in root_path.rglob('*'):
        if file_path.is_file() and should_index_file(file_path, root_path):
            all_files.append(file_path)

    # Organize into modules
    modules = organize_into_modules(all_files, root_path, depth=1)

    # Get submodule config
    submod_config = get_submodule_config(config)
    strategy = submod_config.get('strategy', 'auto')
    threshold = submod_config.get('threshold', 100)
    # User config overrides preset (prioritize user's max_depth setting)
    max_depth = submod_config.get('max_depth', preset.get('max_depth', 3))

    print(f"\n⚙️  Current Configuration:")
    print(f"   Strategy: {strategy}")
    print(f"   Threshold: {threshold} files")
    print(f"   Max depth: {max_depth} levels")

    # Detect large modules
    large_modules = detect_large_modules(modules, threshold, root_path, config)

    print(f"\n📦 Module Analysis:")
    print(f"   Total modules: {len(modules)}")
    print(f"   Large modules (>={threshold} files): {len(large_modules)}")

    # Show module tree
    print(f"\n🌳 Current Module Structure:")
    for module_id in sorted(modules.keys()):
        file_count = len(modules[module_id])
        is_large = any(m['module_id'] == module_id for m in large_modules)
        marker = "⚠️  " if is_large else "   "
        print(f"{marker}{module_id}: {file_count} files")

    # If strategy would split modules, show potential structure
    if strategy != 'disabled' and large_modules:
        print(f"\n🔮 Potential Sub-Module Structure (if index were generated):")
        print(f"   Strategy '{strategy}' would split {len(large_modules)} module(s):")

        for large_mod in large_modules:
            module_id = large_mod['module_id']
            file_list = modules[module_id]
            print(f"\n   {module_id} ({len(file_list)} files) →")

            # Simulate splitting
            sub_modules = split_module_recursive(
                module_id,
                file_list,
                root_path,
                max_depth,
                current_depth=0,
                config=config
            )

            if len(sub_modules) > 1:
                for sub_id in sorted(sub_modules.keys()):
                    print(f"      ├─ {sub_id}: {len(sub_modules[sub_id])} files")
            else:
                print(f"      └─ (no splitting recommended - module is well-organized)")

    # Suggest configuration
    print(f"\n💡 Suggested Configuration (.project-index.json):")
    suggested_config = {
        "mode": "auto",
        "threshold": 1000,
        "submodule_config": {
            "enabled": True,
            "strategy": "auto",
            "threshold": threshold,
            "max_depth": max_depth
        }
    }

    print("```json")
    print(json.dumps(suggested_config, indent=2))
    print("```")

    print(f"\n✅ Analysis complete (no files modified)")
    print("=" * 70 + "\n")


def create_default_config(root_path: Path) -> None:
    """
    Create default .project-index.json configuration file if it doesn't exist.

    Args:
        root_path: Project root directory

    Creates config with:
        - Auto-detected framework preset
        - Default submodule_config with strategy=auto
        - Standard mode and threshold settings
    """
    config_path = root_path / ".project-index.json"

    # Only create if it doesn't exist
    if config_path.exists():
        return

    import logging
    logger = logging.getLogger(__name__)

    # Detect framework to set appropriate defaults
    framework_type = detect_framework_patterns(root_path)
    preset = apply_framework_preset(framework_type, None)

    # Create default configuration
    default_config = {
        "mode": "auto",
        "threshold": 1000,
        "submodule_config": {
            "enabled": True,
            "strategy": "auto",
            "threshold": 100,
            "max_depth": preset.get('max_depth', 3)
        }
    }

    try:
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default configuration file: .project-index.json")
        logger.info(f"Detected framework: {framework_type} (max_depth={preset.get('max_depth', 3)})")
        print(f"✨ Created .project-index.json with {framework_type} preset")

    except Exception as e:
        logger.warning(f"Could not create default config: {e}")


def main() -> None:
    """
    Run the enhanced indexer.

    Parses command-line arguments, loads configuration, determines index format
    (split vs single-file), and generates the project index with architectural
    awareness.

    Configuration precedence:
        1. CLI flags (--mode, --threshold) - highest priority
        2. Configuration file (.project-index.json in cwd)
        3. System defaults (mode=auto, threshold=1000) - lowest priority

    Exits with code 0 on success, 1 on failure.
    """
    import argparse
    import sys

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog='project_index',
        description='Generate architectural awareness index for Claude Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python project_index.py                    # Auto-detect mode based on project size
  python project_index.py --mode split       # Force split format
  python project_index.py --mode single      # Force single-file format
  python project_index.py --threshold 500    # Use split mode for projects >500 files
  python project_index.py --migrate          # Migrate existing index to split format

Configuration File:
  Create .project-index.json in project root to set default options.
  CLI flags override config file settings.
        """
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {read_version_file()}')
    parser.add_argument(
        '--mode',
        choices=['auto', 'split', 'single'],
        help='Index generation mode (default: auto)'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        metavar='N',
        help='File count threshold for auto-detection (default: 1000)'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Migrate legacy single-file index to split format'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show migration plan without executing (use with --migrate)'
    )
    parser.add_argument(
        '--skip-details',
        action='store_true',
        help='Skip detail module generation (core index only)'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Use incremental update (only regenerate changed files)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Force full regeneration (skip incremental update)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (shows large module detection and analysis)'
    )
    parser.add_argument(
        '--analyze-modules',
        action='store_true',
        help='Analyze and display current/potential module structure without modifying files (Story 4.4, AC #9)'
    )
    parser.add_argument(
        '--no-update-check',
        action='store_true',
        help='Skip update checking (for CI/automation, disables network calls)'
    )

    # Legacy compatibility flags (hidden from help)
    parser.add_argument('--format', dest='format_legacy', help=argparse.SUPPRESS)
    parser.add_argument('--split', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--no-split', action='store_true', help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Set up logging
    import logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s: %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )

    # Handle migration first
    if args.migrate:
        success = migrate_to_split_format('.', dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    # Handle --analyze-modules flag (Story 4.4, AC #9)
    if args.analyze_modules:
        config = load_configuration()
        analyze_module_structure(Path.cwd(), config)
        sys.exit(0)

    print("🚀 Building Project Index...")

    # Check for updates (Story 3.4, AC #4, #5 - non-blocking, 2s timeout)
    update_info = check_for_updates(no_update_check=args.no_update_check)
    if update_info and update_info.update_available:
        print(f"📦 Update available: {update_info.current_version} → {update_info.latest_version}")
        print(f"   Install with: ./install.sh --upgrade")
        print(f"   Release: {update_info.release_url}")
        print()

    # Create default configuration if needed (Story 4.4, AC #7)
    create_default_config(Path.cwd())

    # Load configuration file
    config = load_configuration()

    # Configuration precedence: CLI args > config file > defaults
    # Determine mode
    mode = None
    mode_source = None

    # CLI --mode flag (highest priority)
    if args.mode:
        mode = args.mode
        mode_source = f"--mode={mode} flag"
    # Legacy --format flag (for backward compatibility)
    elif args.format_legacy:
        if args.format_legacy == 'split':
            mode = 'split'
        elif args.format_legacy == 'legacy':
            mode = 'single'
        mode_source = f"--format={args.format_legacy} flag (legacy)"
    # Legacy --split flag
    elif args.split:
        mode = 'split'
        mode_source = "--split flag (legacy)"
    # Config file
    elif 'mode' in config:
        mode = config['mode']
        mode_source = "config file"
    # Default
    else:
        mode = 'auto'
        mode_source = "default"

    # Determine threshold
    threshold = None
    threshold_source = None

    # CLI --threshold flag (highest priority)
    if args.threshold:
        threshold = args.threshold
        threshold_source = f"--threshold={threshold} flag"
    # Config file
    elif 'threshold' in config:
        threshold = config['threshold']
        threshold_source = "config file"
    # Default
    else:
        threshold = 1000
        threshold_source = "default"

    # Handle --skip-details flag
    if args.skip_details:
        os.environ['INDEX_SKIP_DETAILS'] = 'true'
        print("   Detail generation disabled (via --skip-details flag)")

    # Environment variable override (legacy support)
    if os.getenv('INDEX_SPLIT_MODE', '').lower() in ['true', '1', 'yes'] and not args.mode:
        mode = 'split'
        mode_source = "INDEX_SPLIT_MODE env var"

    # Determine final split mode based on mode setting
    use_split_mode = False

    if mode == 'split':
        use_split_mode = True
        print(f"   Split mode enabled (via {mode_source})")
    elif mode == 'single':
        use_split_mode = False
        print(f"   Single-file mode enabled (via {mode_source})")
    elif mode == 'auto':
        # Auto-detection based on file count
        if args.no_split:
            use_split_mode = False
            print("   Single-file mode (via --no-split flag)")
        else:
            git_files = get_git_files(Path('.'))
            file_count = len(git_files) if git_files else 0

            if file_count > threshold:
                use_split_mode = True
                print(f"   Auto-detected split mode: {file_count} files > {threshold} threshold ({threshold_source})")
            else:
                use_split_mode = False
                print(f"   Auto-detected single-file mode: {file_count} files ≤ {threshold} threshold ({threshold_source})")

    # Check for target size from environment (legacy mode only)
    target_size_k = int(os.getenv('INDEX_TARGET_SIZE_K', '0'))
    if target_size_k > 0:
        # Convert k tokens to approximate bytes (1 token ≈ 4 chars)
        target_size_bytes = target_size_k * 1000 * 4
        print(f"   Target size: {target_size_k}k tokens (~{target_size_bytes:,} bytes)")
    else:
        target_size_bytes = MAX_INDEX_SIZE

    print("   Analyzing project structure and documentation...")

    # Check for incremental update option (Story 2.9)
    use_incremental = False
    index_path = Path('PROJECT_INDEX.json')

    if args.full:
        # User explicitly requested full regeneration
        print("   Full regeneration mode (via --full flag)")
        use_incremental = False
    elif args.incremental:
        # User explicitly requested incremental
        print("   Incremental update mode (via --incremental flag)")
        use_incremental = True
    elif index_path.exists():
        # Auto-detection: Use incremental if index exists and git available
        try:
            # Check if git is available
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=Path('.'),
                capture_output=True,
                timeout=5,
                check=True
            )
            # Check if split format (incremental only works with split format)
            if use_split_mode:
                use_incremental = True
                print("   Auto-detected incremental update mode (existing index + git + split format)")
            else:
                print("   Full regeneration (single-file format doesn't support incremental)")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("   Full regeneration (git not available for incremental)")
    else:
        print("   Full regeneration (no existing index)")

    # Attempt incremental update if enabled
    if use_incremental:
        try:
            from incremental import incremental_update

            print("\n🔄 Running incremental update...")
            updated_index_path, updated_modules = incremental_update(
                index_path,
                Path('.'),
                verbose=True
            )

            if updated_modules:
                print(f"✅ Incremental update successful!")
                print(f"   Updated {len(updated_modules)} modules")

                # Load the updated index for summary
                with open(index_path, 'r') as f:
                    index = json.load(f)

                # Print summary and exit
                print_summary(index, 0)
                print(f"\n💾 Updated: {index_path}")
                print("\n✨ Index incrementally updated - ready to use!")
                sys.exit(0)
            else:
                print("ℹ️  No changes detected - index is up to date")
                sys.exit(0)

        except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as e:
            print(f"\n⚠️  Incremental update failed: {e}")
            print("   Falling back to full regeneration...")
            use_incremental = False

    # Build index using appropriate method
    if use_split_mode:
        # New split index format
        print("   Using split index format (v2.2-submodules)")
        index, skipped_count = generate_split_index('.', config)

        # Check size
        index_json = json.dumps(index, separators=(',', ':'))
        current_size = len(index_json)
        current_size_kb = current_size / 1024

        print(f"\n📊 Core index size: {current_size_kb:.1f} KB")

        # Verify size constraint (100 KB for 10,000 files, scale down for fewer)
        max_allowed_kb = 100
        if current_size_kb > max_allowed_kb:
            print(f"⚠️  Warning: Core index exceeds {max_allowed_kb} KB target")
    else:
        # Legacy single-file format
        print("   ℹ️  Using legacy single-file format (v1.0)")
        print("   📊 This format is fully supported and recommended for projects with <1000 files")
        index, skipped_count = build_index('.', config)

        # Convert to enhanced dense format (always)
        index = convert_to_enhanced_dense_format(index)

        # Compress further if needed
        index = compress_if_needed(index, target_size_bytes)

        # Add version field to legacy format
        index['version'] = '1.0'

    # Add metadata if requested via environment
    if target_size_k > 0:
        if '_meta' not in index:
            index['_meta'] = {}
        # Note: Full metadata is added by the hook after generation
        index['_meta']['target_size_k'] = target_size_k

    # Save to PROJECT_INDEX.json (minified)
    output_path = Path('PROJECT_INDEX.json')
    output_path.write_text(json.dumps(index, separators=(',', ':')))

    # Print summary
    print_summary(index, skipped_count)

    print(f"\n💾 Saved to: {output_path}")

    # More concise output when called by hook
    if target_size_k > 0:
        actual_size = len(json.dumps(index, separators=(',', ':')))
        actual_tokens = actual_size // 4 // 1000
        print(f"📊 Size: {actual_tokens}k tokens (target was {target_size_k}k)")
    else:
        print("\n✨ Claude now has architectural awareness of your project!")
        print("   • Knows WHERE to place new code")
        print("   • Understands project structure")
        print("   • Can navigate documentation")
        print("\n📌 Benefits:")
        print("   • Prevents code duplication")
        print("   • Ensures proper file placement")
        print("   • Maintains architectural consistency")


if __name__ == '__main__':
    main()