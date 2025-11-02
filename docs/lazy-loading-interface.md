# Lazy-Loading Interface

Usage guide for the PROJECT_INDEX detail module loader interface.

## Overview

The lazy-loading interface enables AI agents to load only relevant code sections on-demand, rather than loading the entire codebase index upfront. This improves performance and reduces token usage for large projects.

**Performance Target:** <500ms latency per module request (NFR001)

## Prerequisites

1. Project must have split-format index generated:
   ```bash
   python3 scripts/project_index.py --split
   ```

2. This creates:
   - `PROJECT_INDEX.json` - Core index with module references
   - `PROJECT_INDEX.d/` - Directory containing detail modules

## API Functions

### Load Module by Name

**Function:** `load_detail_module(module_name, index_dir=None)`

Load a detail module by its module ID.

**Parameters:**
- `module_name` (str): Module identifier (e.g., "scripts", "auth", "database")
- `index_dir` (Path, optional): Custom directory path. Defaults to `PROJECT_INDEX.d/`

**Returns:**
- `dict`: Detail module JSON content with structure:
  ```python
  {
      "module_id": "scripts",
      "version": "2.0-split",
      "files": {
          "scripts/loader.py": {
              "language": "python",
              "functions": [...],
              "classes": [...],
              "imports": [...]
          }
      },
      "call_graph_local": [[...]]
  }
  ```

**Raises:**
- `FileNotFoundError`: Module not found in PROJECT_INDEX.d/
- `json.JSONDecodeError`: Invalid JSON in detail module file
- `ValueError`: Invalid module_name format or missing required fields

**Example:**
```python
from scripts.loader import load_detail_module

# Load scripts module
module = load_detail_module("scripts")
print(f"Module ID: {module['module_id']}")
print(f"Files: {len(module['files'])}")

# Iterate through functions
for file_path, file_data in module['files'].items():
    for func in file_data.get('functions', []):
        print(f"  {file_path}: {func}")
```

**Valid Module Name Format:**
- Alphanumeric characters (a-z, A-Z, 0-9)
- Hyphens (-) and underscores (_)
- Examples: `auth`, `auth-service`, `auth_service_v2`

---

### Load Module by File Path

**Function:** `load_detail_by_path(file_path, core_index, index_dir=None)`

Load the detail module containing a specific file.

**Parameters:**
- `file_path` (str): File path to search for (e.g., "scripts/project_index.py")
- `core_index` (dict): Core index with module mappings (from PROJECT_INDEX.json)
- `index_dir` (Path, optional): Custom directory path. Defaults to `PROJECT_INDEX.d/`

**Returns:**
- `dict`: Detail module JSON content (same structure as `load_detail_module`)

**Raises:**
- `ValueError`: File not found in any module, or legacy format index
- `FileNotFoundError`: Module file not found
- `json.JSONDecodeError`: Invalid JSON in module file

**Example:**
```python
import json
from scripts.loader import load_detail_by_path

# Load core index
with open("PROJECT_INDEX.json") as f:
    core_index = json.load(f)

# Find and load module containing specific file
module = load_detail_by_path("scripts/loader.py", core_index)
print(f"File 'scripts/loader.py' is in module: {module['module_id']}")

# Access the file's details
file_details = module['files']['scripts/loader.py']
print(f"Language: {file_details['language']}")
print(f"Functions: {file_details['functions']}")
```

---

### Batch Load Multiple Modules

**Function:** `load_multiple_modules(module_names, index_dir=None)`

Batch load multiple detail modules in one call. Handles partial failures gracefully.

**Parameters:**
- `module_names` (List[str]): List of module identifiers
- `index_dir` (Path, optional): Custom directory path. Defaults to `PROJECT_INDEX.d/`

**Returns:**
- `dict`: Mapping of module_name → module_content
  - Only includes successfully loaded modules
  - Empty dict if all modules fail to load

**Behavior:**
- Loads modules sequentially
- Skips missing modules with warning (doesn't fail entire operation)
- Logs warnings for partial failures
- Returns all successfully loaded modules

**Example:**
```python
from scripts.loader import load_multiple_modules

# Load multiple modules at once
modules = load_multiple_modules(["scripts", "agents", "bmad"])

print(f"Loaded {len(modules)} modules")
for module_name, module_data in modules.items():
    print(f"\n{module_name}:")
    print(f"  Files: {len(module_data['files'])}")
    print(f"  Version: {module_data['version']}")
```

**Handling Partial Failures:**
```python
import warnings

# Suppress warnings for production use
with warnings.catch_warnings():
    warnings.simplefilter("ignore")

    # This will load valid modules and skip invalid ones
    modules = load_multiple_modules(["scripts", "nonexistent", "agents"])
    # Result: {"scripts": {...}, "agents": {...}}
    # "nonexistent" is skipped with warning
```

---

### Find Module for File (Helper)

**Function:** `find_module_for_file(file_path, core_index)`

Helper function to find which module contains a specific file.

**Parameters:**
- `file_path` (str): File path to search for
- `core_index` (dict): Core index with module mappings

**Returns:**
- `str`: Module ID containing the file

**Raises:**
- `ValueError`: File not found in any module
- `TypeError`: Invalid input types

**Example:**
```python
import json
from scripts.loader import find_module_for_file

with open("PROJECT_INDEX.json") as f:
    core_index = json.load(f)

# Find which module contains a file
module_id = find_module_for_file("scripts/loader.py", core_index)
print(f"File is in module: {module_id}")  # Output: scripts
```

---

## Agent Workflow Pattern

Recommended workflow for AI agents using lazy-loading:

```python
import json
from pathlib import Path
from scripts.loader import load_multiple_modules

# 1. Load core index
core_index_path = Path("PROJECT_INDEX.json")
with open(core_index_path) as f:
    core_index = json.load(f)

# 2. Perform relevance scoring
# (Keyword matching, semantic search, etc.)
user_query = "authentication and login"
relevant_modules = ["auth", "database"]  # Based on query analysis

# 3. Batch load top-N relevant modules
modules = load_multiple_modules(relevant_modules)

# 4. Use loaded details in response
print(f"Found {len(modules)} relevant modules for query: '{user_query}'")

for module_name, module_data in modules.items():
    print(f"\n=== {module_name} ===")
    for file_path, file_data in module_data["files"].items():
        print(f"File: {file_path}")
        print(f"  Functions: {len(file_data.get('functions', []))}")

        # Show function signatures
        for func in file_data.get('functions', [])[:3]:  # Top 3
            print(f"    - {func}")
```

---

## Error Handling

### Legacy Format Index

If the core index is in legacy format (v1.0), `find_module_for_file` and `load_detail_by_path` will raise a helpful error:

```python
ValueError: Core index is in legacy format (v1.0) which doesn't support module lookups.
Please regenerate the index with split format using: python3 scripts/project_index.py --split
Or use Story 1.6 (Backward Compatibility) to auto-migrate.
```

**Solution:**
```bash
python3 scripts/project_index.py --split
```

### Module Not Found

```python
FileNotFoundError: Module 'auth' not found in PROJECT_INDEX.d/
Expected path: /path/to/PROJECT_INDEX.d/auth.json
```

**Common Causes:**
- Module name typo
- Detail modules not generated yet
- Wrong index_dir path

**Solution:**
- Check module name spelling
- Regenerate index: `python3 scripts/project_index.py --split`
- Verify PROJECT_INDEX.d/ exists

### Invalid JSON

```python
json.JSONDecodeError: Invalid JSON in detail module 'scripts': ...
```

**Common Causes:**
- Corrupted module file
- Manual editing broke JSON syntax

**Solution:**
- Regenerate index: `python3 scripts/project_index.py --split`

---

## Performance Considerations

**Target:** <500ms per module request (NFR001)

**Optimization Tips:**

1. **Use Batch Loading** for multiple modules:
   ```python
   # Good - Single call
   modules = load_multiple_modules(["auth", "database", "api"])

   # Avoid - Multiple calls
   auth = load_detail_module("auth")
   database = load_detail_module("database")
   api = load_detail_module("api")
   ```

2. **Cache Core Index** instead of re-reading:
   ```python
   # Load once at startup
   with open("PROJECT_INDEX.json") as f:
       core_index = json.load(f)

   # Reuse for multiple queries
   module1 = load_detail_by_path("file1.py", core_index)
   module2 = load_detail_by_path("file2.py", core_index)
   ```

3. **Limit Module Count** for agent responses:
   ```python
   # Load top 5 most relevant modules
   top_modules = relevance_scoring(query)[:5]
   modules = load_multiple_modules(top_modules)
   ```

---

## Integration Examples

### Example 1: Code Search Agent

```python
import json
from scripts.loader import load_detail_by_path

def search_function(function_name, core_index_path="PROJECT_INDEX.json"):
    """Search for a function across all modules."""
    with open(core_index_path) as f:
        core_index = json.load(f)

    results = []

    # Search through all modules
    for module_id, module_info in core_index.get("modules", {}).items():
        for file_path in module_info.get("files", []):
            module = load_detail_by_path(file_path, core_index)

            # Check each file in the module
            for filepath, filedata in module["files"].items():
                for func in filedata.get("functions", []):
                    if function_name in func:
                        results.append({
                            "module": module_id,
                            "file": filepath,
                            "function": func
                        })

    return results

# Usage
results = search_function("load_detail")
for r in results:
    print(f"{r['file']}:{r['function']}")
```

### Example 2: Documentation Generator

```python
from scripts.loader import load_multiple_modules

def generate_api_docs(module_names):
    """Generate API documentation for specified modules."""
    modules = load_multiple_modules(module_names)

    docs = []
    for module_name, module_data in modules.items():
        docs.append(f"# Module: {module_name}\n")

        for file_path, file_data in module_data["files"].items():
            docs.append(f"\n## File: {file_path}\n")

            # Document public functions
            for func in file_data.get("functions", []):
                docs.append(f"- `{func}`\n")

    return "\n".join(docs)

# Usage
api_docs = generate_api_docs(["scripts", "agents"])
print(api_docs)
```

---

## Backward Compatibility

**Current Status:**

- ✅ Split format (v2.0-split) fully supported
- ⚠️ Legacy format (v1.0) raises helpful error with migration instructions
- 🔜 Story 1.6 will add automatic migration from legacy to split format

**Migration Path:**

If you have an existing legacy index:

```bash
# Option 1: Regenerate with split format
python3 scripts/project_index.py --split

# Option 2: Wait for Story 1.6 (auto-migration)
# Coming soon: Automatic detection and migration
```

---

## Troubleshooting

### Issue: "Module not found" but file exists

**Check:**
```bash
ls PROJECT_INDEX.d/
# Verify module file exists
```

**Solution:**
```bash
# Regenerate index
python3 scripts/project_index.py --split
```

### Issue: Performance slower than 500ms

**Diagnosis:**
```python
import time
from scripts.loader import load_detail_module

start = time.time()
module = load_detail_module("large_module")
elapsed_ms = (time.time() - start) * 1000
print(f"Load time: {elapsed_ms:.2f}ms")
```

**Common Causes:**
- Very large module files (>1MB JSON)
- Slow disk I/O
- Network filesystem latency

**Solution:**
- Split large modules into smaller ones (future enhancement)
- Use SSD storage
- Cache loaded modules in memory

---

## See Also

- [Split Index Schema](split-index-schema.md) - Detail module format specification
- [Tech Spec Epic 1](tech-spec-epic-1.md) - Architecture and design decisions
- [PRD](PRD.md) - Product requirements and performance targets
- Story 1.5: Update Index-Analyzer Agent - First consumer of this API
- Story 1.6: Backward Compatibility - Auto-migration from legacy format
