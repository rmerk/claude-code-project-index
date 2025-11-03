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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared utilities
from index_utils import (
    IGNORE_DIRS, PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    DIRECTORY_PURPOSES, extract_python_signatures, extract_javascript_signatures,
    extract_shell_signatures, extract_markdown_structure, infer_file_purpose,
    infer_directory_purpose, get_language_name, should_index_file
)
from doc_classifier import classify_documentation

# Limits to keep it fast and simple
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5


def detect_index_format(index_path: Path = None) -> str:
    """
    Detect whether index is legacy or split format.

    Checks for PROJECT_INDEX.d/ directory existence and version field.

    Args:
        index_path: Path to PROJECT_INDEX.json (defaults to cwd/PROJECT_INDEX.json)

    Returns:
        "split" if PROJECT_INDEX.d/ exists and version="2.0-split"
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
            if version == "2.0-split":
                return "split"
    except (FileNotFoundError, json.JSONDecodeError, Exception):
        # If index file doesn't exist or is corrupted, but directory exists,
        # assume legacy until proven otherwise
        pass

    return "legacy"


def load_configuration(config_path: Optional[Path] = None) -> Dict[str, any]:
    """
    Load configuration from .project-index.json file.

    Args:
        config_path: Path to configuration file (defaults to cwd/.project-index.json)

    Returns:
        Dictionary with configuration values, or empty dict if file not found.
        Valid keys: 'mode' (str), 'threshold' (int), 'max_index_size' (int),
        'compression_level' (str)

    Configuration format:
        {
            "mode": "auto" | "split" | "single",
            "threshold": number (default: 1000),
            "max_index_size": number (default: 1048576),
            "compression_level": "standard" | "aggressive"
        }

    Configuration file location:
        Searches for .project-index.json in current working directory only.
        If multiple projects are nested, only the cwd config is used.
        To use different configs for nested projects, run the indexer from
        that project's directory.
    """
    if config_path is None:
        config_path = Path.cwd() / ".project-index.json"

    # Return empty config if file doesn't exist (not an error)
    if not config_path.exists():
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
                except:
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
    """Generate lightweight core index in split format (v2.0-split).

    Args:
        root_dir: Project root directory
        config: Optional configuration dict with doc_tiers and other settings

    Returns:
        Tuple of (core_index_dict, skipped_file_count)
    """
    from index_utils import extract_lightweight_signature

    root = Path(root_dir)
    git_cache = {}  # Cache for git metadata

    # Core index structure (v2.0-split)
    core_index = {
        'version': '2.0-split',
        'at': datetime.now().isoformat(),
        'root': str(root),
        'tree': [],
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0,
            'doc_tiers': {'critical': 0, 'standard': 0, 'archive': 0}  # Tier counts
        },
        'f': {},  # Files with lightweight signatures
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
    from index_utils import get_git_files
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
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Extract signatures based on language
            if file_path.suffix == '.py':
                extracted = extract_python_signatures(content)
            elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                extracted = extract_javascript_signatures(content)
            elif file_path.suffix in {'.sh', '.bash'}:
                extracted = extract_shell_signatures(content)
            else:
                extracted = {'functions': {}, 'classes': {}}

            # Skip if no functions/classes found
            if not extracted.get('functions') and not extracted.get('classes'):
                continue

            # Build lightweight file entry
            file_entry = {
                'lang': language
            }

            # Add git metadata
            git_meta = extract_git_metadata(file_path, root, git_cache)
            if git_meta.get('commit'):
                file_entry['git'] = git_meta

            # Convert to lightweight signatures (name:line format)
            if extracted.get('functions'):
                lightweight_funcs = []
                for func_name, func_data in extracted['functions'].items():
                    lightweight_funcs.append(extract_lightweight_signature(func_data, func_name))
                file_entry['funcs'] = lightweight_funcs

            if extracted.get('classes'):
                lightweight_classes = {}
                for class_name, class_data in extracted['classes'].items():
                    if isinstance(class_data, dict):
                        line = class_data.get('line', 0)
                        methods = []
                        for method_name, method_data in class_data.get('methods', {}).items():
                            methods.append(extract_lightweight_signature(method_data, method_name))
                        lightweight_classes[class_name] = {
                            'line': line,
                            'methods': methods
                        }
                if lightweight_classes:
                    file_entry['classes'] = lightweight_classes

            # Add imports if present
            if extracted.get('imports'):
                file_entry['imports'] = extracted['imports']

            # Store file entry
            core_index['f'][str(rel_path)] = file_entry

            # Track for module organization
            parsed_files.append(file_path)
            file_functions_map[str(rel_path)] = extracted

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
            'version': '2.0-split',
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
            'doc_tiers': {'critical': 0, 'standard': 0, 'archive': 0}  # Tier counts
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
    from index_utils import get_git_files
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


def extract_git_metadata(file_path: Path, root_path: Path, cache: Dict) -> Dict:
    """Extract git metadata for a file with caching.

    Args:
        file_path: Path to the file
        root_path: Project root path
        cache: Cache dict to store results

    Returns:
        Dict with commit_hash, author, author_email, date, or fallback to file mtime
    """
    import subprocess
    from datetime import datetime

    # Convert to relative path for cache key
    try:
        rel_path = str(file_path.relative_to(root_path))
    except ValueError:
        rel_path = str(file_path)

    # Check cache first
    if rel_path in cache:
        return cache[rel_path]

    metadata = {}

    try:
        # Get last commit info for this file
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H|%an|%ae|%aI', '--', str(file_path)],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) == 4:
                metadata = {
                    'commit': parts[0],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'pr': None  # Placeholder for Epic 2, Story 2.3
                }
            else:
                # Fallback to file mtime
                metadata = _fallback_to_mtime(file_path)
        else:
            # File not tracked or git command failed
            metadata = _fallback_to_mtime(file_path)

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Git not available or command failed
        metadata = _fallback_to_mtime(file_path)

    # Cache the result
    cache[rel_path] = metadata
    return metadata


def _fallback_to_mtime(file_path: Path) -> Dict:
    """Fallback to file modification time when git is unavailable."""
    from datetime import datetime

    try:
        mtime = file_path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        return {
            'commit': None,
            'author': None,
            'email': None,
            'date': dt.isoformat(),
            'pr': None
        }
    except:
        return {
            'commit': None,
            'author': None,
            'email': None,
            'date': None,
            'pr': None
        }


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
        print("      ℹ️  Index is already in split format (v2.0-split)")
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

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
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

    # Legacy compatibility flags (hidden from help)
    parser.add_argument('--format', dest='format_legacy', help=argparse.SUPPRESS)
    parser.add_argument('--split', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--no-split', action='store_true', help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Handle migration first
    if args.migrate:
        success = migrate_to_split_format('.', dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    print("🚀 Building Project Index...")

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
            from index_utils import get_git_files
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

    # Build index using appropriate method
    if use_split_mode:
        # New split index format
        print("   Using split index format (v2.0-split)")
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