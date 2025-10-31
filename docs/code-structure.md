# Code Structure Analysis

## Overview

**Total Python Code**: ~3,047 lines across 4 main modules
**Architecture**: Hook-based CLI tool with modular utilities
**Entry Points**: `project_index.py` (main), hook scripts for Claude Code integration

---

## Core Modules

### 1. project_index.py (Entry Point)
**Purpose**: Main indexer that generates PROJECT_INDEX.json with project structure

**Key Functions**:
- `generate_tree_structure(root_path)` - Creates ASCII tree visualization
- `build_index(root_dir)` - Main orchestrator for index generation
- `convert_to_enhanced_dense_format(index)` - Compresses index to dense format
- `compress_if_needed(dense_index, target_size)` - Progressive compression to fit size limits
- `main()` - CLI entry point

**Features**:
- Extracts functions, classes, and methods with signatures
- Builds call graphs (bidirectional)
- Parses Python, JavaScript/TypeScript, and Shell scripts
- Infers directory purposes
- Maps markdown documentation
- Gitignore-aware file discovery

**Limits**:
- MAX_FILES: 10,000
- MAX_INDEX_SIZE: 1MB (compressed)
- MAX_TREE_DEPTH: 5 levels

---

### 2. index_utils.py (Shared Utilities)
**Purpose**: Common functionality for parsing and analysis

**Key Functions**:
- `extract_python_signatures(content)` - Parse Python functions/classes
- `extract_javascript_signatures(content)` - Parse JS/TS functions/classes
- `extract_shell_signatures(content)` - Parse shell functions
- `extract_markdown_structure(file_path)` - Extract headers from markdown
- `infer_file_purpose(file_path)` - Determine file purpose from name/location
- `infer_directory_purpose(path, files)` - Determine directory purpose
- `should_index_file(path, root_path)` - Gitignore-aware file filtering
- `get_git_files(root_path)` - Fast file discovery via git ls-files

**Language Support**:
- **Full Parsing**: Python (.py), JavaScript/TypeScript (.js, .ts, .jsx, .tsx), Shell (.sh, .bash)
- **Listing Only**: Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin, and 20+ more

**Ignore Patterns**:
- `.git`, `node_modules`, `__pycache__`, `.venv`, `build`, `dist`, `.next`, `target`
- `.claude` directory (Claude Code configuration)

---

### 3. i_flag_hook.py (UserPromptSubmit Hook)
**Purpose**: Detects `-i` and `-ic` flags in user prompts to trigger index generation

**Key Functions**:
- `find_project_root()` - Locate project root via .git or manifest files
- `get_last_interactive_size()` - Remember user's last `-i` size preference
- `parse_index_flag(prompt)` - Extract flag and size from prompt
- `calculate_files_hash(project_root)` - Detect file changes for smart regeneration
- `should_regenerate_index(project_root, index_path, size)` - Skip if index is current
- `generate_index_at_size(project_root, target_size_k, clipboard_mode)` - Generate index
- `copy_to_clipboard(prompt, index_path)` - Handle `-ic` clipboard export
- `main()` - Hook entry point

**Modes**:
- **Interactive Mode** (`-i[size]`): Generate index and invoke subagent for analysis
- **Clipboard Mode** (`-ic[size]`): Export to clipboard for external AI (Gemini, ChatGPT, etc.)

**Size Limits**:
- Default: 50k tokens (remembered per project)
- `-i` mode: 1k to 100k tokens max
- `-ic` mode: 1k to 800k tokens max

**Smart Features**:
- File change detection via hash comparison
- Skips regeneration if index is current
- Remembers user's last size preference
- Graceful fallback for clipboard (pyperclip, vm_client, file export)

---

### 4. stop_hook.py (Stop Hook)
**Purpose**: Auto-refresh index after every Claude Code session

**Key Functions**:
- `main()` - Regenerate index if PROJECT_INDEX.json exists

**Behavior**:
- Searches up directory tree for PROJECT_INDEX.json
- Finds Python command automatically
- Runs indexer silently with 10-second timeout
- Non-blocking - warns on errors but doesn't interrupt workflow

---

## Installation Scripts

### install.sh (Bash)
- Detects OS (macOS/Linux)
- Finds newest Python 3.8+ version via `find_python.sh`
- Installs to `~/.claude-code-project-index/`
- Configures hooks in `~/.claude/settings.json`
- Creates `/index` slash command
- Installs `index-analyzer` agent

### uninstall.sh (Bash)
- Removes installation directory
- Removes hooks from settings
- Removes slash command and agent
- Preserves PROJECT_INDEX.json files in user projects

### find_python.sh (Bash)
- Searches for Python 3.8+ installations
- Checks virtual environments first
- Scans common Homebrew/system paths
- Selects newest available version
- Respects PYTHON_CMD environment variable override

---

## Configuration Management

**Hook Integration**:
- **UserPromptSubmit**: Detects `-i` flag → generates index → invokes subagent
- **Stop**: Auto-refreshes index after session ends

**Environment Variables**:
- `PYTHON_CMD`: Override Python command selection
- `INDEX_TARGET_SIZE_K`: Set target token size for generation

**State Files**:
- `~/.claude-code-project-index/.python_cmd`: Cached Python command
- `PROJECT_INDEX.json`: Generated index (in project root)
- `.clipboard_content.txt`: Fallback for SSH clipboard mode

---

## Shared Utilities and Helpers

**Directory Inference**:
- Recognizes 20+ common directory patterns (auth, models, api, tests, etc.)
- Infers purpose from contained files

**File Purpose Inference**:
- Routes, controllers, models, config, tests, middleware
- Based on filename patterns and location

**Call Graph Analysis**:
- Bidirectional call relationships
- Tracks `calls` and `called_by` for every function
- Enables impact analysis and dependency tracing

**Compression Strategies** (progressive):
1. Reduce tree to 10 items
2. Truncate docstrings to 40 chars
3. Remove docstrings entirely
4. Remove documentation map
5. Emergency truncation - keep most important files

---

## Testing Strategy

**Current Status**: No formal test suite found
**Testing Approach**: Beta community tool - relies on real-world usage and user feedback
**Quality Assurance**: Error handling and graceful degradation built into all modules

---

## Entry Points Summary

| File | Purpose | Invocation |
|------|---------|------------|
| `project_index.py` | Generate index | `python3 project_index.py` or `/index` |
| `i_flag_hook.py` | Hook for `-i` flag | Automatic via UserPromptSubmit |
| `stop_hook.py` | Auto-refresh | Automatic on session end |
| `install.sh` | Install tool | `bash install.sh` |
| `uninstall.sh` | Remove tool | `bash uninstall.sh` |

---

## Dependencies

**Standard Library Only**:
- json, os, re, sys, subprocess, hashlib, time, pathlib, datetime, typing, fnmatch

**Optional**:
- `pyperclip` - Clipboard operations (graceful fallback)
- `vm_client` / `vm_client_network` - VM Bridge for SSH clipboard (optional)

**No Package Manager**: Direct-use tool, no pip/poetry/setup.py required
