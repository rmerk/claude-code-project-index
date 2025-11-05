# Epic Technical Specification: Intelligent Sub-Module Organization

Date: 2025-11-04
Author: Ryan
Epic ID: 4
Status: Draft

---

## Overview

Epic 4 addresses a critical limitation in the current split index architecture: large top-level directories create monolithic modules that defeat the purpose of lazy-loading. When a project like `assureptmdashboard` has a deeply nested structure (`src/components/`, `src/views/`, `src/api/`), all files currently get grouped into a single `assureptmdashboard` module. This forces agents to load 400+ files even when querying a specific component.

This epic enhances the module organization logic from Epic 1 to intelligently split large modules into granular multi-level sub-modules (up to 3 levels deep) based on project structure and framework patterns. By detecting common framework layouts (Vite, React, Next.js) and applying recursive splitting, agents can lazy-load only the specific subdirectory they need—loading ~50 component files instead of ~416 src files, achieving a 70%+ reduction in context overhead for targeted queries.

## Objectives and Scope

**In Scope:**

- **Large Module Detection:** Analyze module size and identify candidates for sub-module splitting (configurable threshold, default: 100 files per module)
- **Multi-Level Sub-Module Generation:** Split large modules up to 3 levels deep using naming convention `parent-child-grandchild` (e.g., `assureptmdashboard-src-components.json`)
- **Framework-Aware Splitting:** Auto-detect and optimize for common patterns (Vite: `src/components/`, `src/views/`, `src/api/`; React; Next.js)
- **Enhanced Relevance Scoring:** Update agent intelligence to score fine-grained sub-modules independently with keyword-to-module mapping (e.g., "component" → boost `src-components` score)
- **File-to-Module Mapping:** Maintain O(1) lookup in core index for @ reference resolution (`@src/components/LoginForm.vue` → `assureptmdashboard-src-components` module)
- **Configuration and Migration:** Provide control over splitting behavior with framework presets and migration path from monolithic modules

**Out of Scope:**

- Changes to core index schema (uses existing Epic 1 infrastructure)
- Runtime module merging or dynamic reorganization (split configuration applies at index generation time only)
- Framework detection beyond directory structure patterns (no package.json parsing or AST analysis)
- Sub-module splitting below 3 levels deep (maximum depth: parent-child-grandchild)

## System Architecture Alignment

This epic builds directly on **Epic 1's split index architecture** (core index + detail modules in `PROJECT_INDEX.d/`). The core/detail separation remains unchanged; Epic 4 enhances the *organization* of detail modules by introducing multi-level granularity.

**Architectural Alignment:**

- **Core Index (PROJECT_INDEX.json):** Enhanced `modules` section includes file-to-module mapping for all files across all sub-modules, enabling fast @ reference resolution
- **Detail Modules (PROJECT_INDEX.d/):** Instead of one large `assureptmdashboard.json`, generates multiple fine-grained modules: `assureptmdashboard-src-components.json`, `assureptmdashboard-src-views.json`, etc.
- **Lazy-Loading Interface (Epic 1 Story 1.4):** No changes—agents request modules by name; they now have more granular module names to request
- **Relevance Scoring (Epic 2 Story 2.7):** Enhanced to score multi-level sub-modules independently and map keywords to module types
- **MCP Integration (Epic 2 Story 2.10):** Unaffected—MCP tools operate on file paths, core index provides module mapping for context retrieval

**Constraint Alignment:**

- Maintains backward compatibility with monolithic module organization (configurable via `enable_submodules: false`)
- Works with both split and single-file index formats
- No changes to MCP server API or tool interfaces
- Performance target: Sub-module detection and generation adds <10% to index generation time

## Detailed Design

### Services and Modules

Epic 4 enhances existing modules in `scripts/` without introducing new services:

| Module | Responsibilities | Key Changes |
|--------|-----------------|-------------|
| **scripts/project_index.py** | Main index generation orchestrator | Enhanced `organize_into_modules()` to support multi-level splitting; new `detect_large_modules()` function; new `detect_framework_patterns()` function |
| **scripts/index_utils.py** | File parsing and gitignore handling | No changes required (reused as-is) |
| **scripts/loader.py** | Detail module lazy-loading | Enhanced `find_module_for_file()` to support file-to-module lookup with multi-level modules |
| **scripts/relevance.py** | Relevance scoring engine (Epic 2) | Enhanced `RelevanceScorer.score_module()` to support keyword-to-module-type mapping; new `_boost_by_keywords()` function |
| **scripts/doc_classifier.py** | Documentation tiering (Epic 2) | No changes required |
| **scripts/git_metadata.py** | Git metadata extraction (Epic 2) | No changes required |

**New Functions:**

- **`detect_large_modules(modules, threshold)`** - Analyzes module file counts and returns list of modules exceeding threshold
- **`detect_framework_patterns(root_path)`** - Detects framework type (vite, react, nextjs, generic) by examining directory structure
- **`split_module_recursive(module_id, file_list, root_path, max_depth, current_depth, config)`** - Recursively splits a module into sub-modules up to max_depth levels
- **`build_file_to_module_map(modules)`** - Creates O(1) lookup dictionary: `{file_path: module_id}` for @ reference resolution
- **`apply_framework_preset(framework_type, config)`** - Returns splitting rules for detected framework

### Data Models and Contracts

**Core Index Schema Enhancement (PROJECT_INDEX.json):**

```json
{
  "version": "2.2-submodules",
  "modules": {
    "assureptmdashboard-src-components": {
      "file_count": 245,
      "function_count": 1203,
      "detail_path": "PROJECT_INDEX.d/assureptmdashboard-src-components.json",
      "files": ["src/components/LoginForm.vue", "src/components/Button.vue", ...]
    },
    "assureptmdashboard-src-views": {
      "file_count": 89,
      "function_count": 456,
      "detail_path": "PROJECT_INDEX.d/assureptmdashboard-src-views.json",
      "files": ["src/views/Dashboard.vue", ...]
    }
  },
  "file_to_module_map": {
    "src/components/LoginForm.vue": "assureptmdashboard-src-components",
    "src/views/Dashboard.vue": "assureptmdashboard-src-views",
    "src/api/auth.ts": "assureptmdashboard-src-api"
  }
}
```

**Configuration Schema (.project-index.json):**

```json
{
  "mode": "split",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3,
    "framework_presets": {
      "vite": {
        "enabled": true,
        "split_paths": [
          "src/components",
          "src/views",
          "src/api",
          "src/stores",
          "src/composables",
          "src/utils"
        ]
      }
    }
  }
}
```

**Detail Module Schema (No Changes):**

Detail modules (`PROJECT_INDEX.d/assureptmdashboard-src-components.json`) maintain the existing Epic 1 schema with full function/class signatures, call graphs, and documentation.

### APIs and Interfaces

**Enhanced Functions (Python API):**

```python
# scripts/project_index.py

def organize_into_modules(
    files: List[Path],
    root_path: Path,
    config: Dict
) -> Dict[str, List[str]]:
    """
    Group files into modules with optional multi-level sub-module splitting.

    Args:
        files: List of file paths to organize
        root_path: Project root path
        config: Configuration dict with submodule_config section

    Returns:
        Dict mapping module_id -> list of file paths

    Behavior:
        - If submodule_config.enabled=false: Uses monolithic organization (Epic 1)
        - If submodule_config.enabled=true: Applies multi-level splitting based on strategy
        - strategy="auto": Detects framework and applies preset if matched
        - strategy="force": Always splits regardless of size
        - strategy="disabled": Same as enabled=false
    """

def split_module_recursive(
    module_id: str,
    file_list: List[str],
    root_path: Path,
    max_depth: int,
    current_depth: int,
    config: Dict
) -> Dict[str, List[str]]:
    """
    Recursively split a module into sub-modules based on directory structure.

    Returns:
        Dict with sub-module_id -> file_list entries

    Example:
        Input: module_id="assureptmdashboard", 416 files
        Output: {
            "assureptmdashboard-src-components": [245 files],
            "assureptmdashboard-src-views": [89 files],
            "assureptmdashboard-src-api": [34 files],
            ...
        }
    """

def build_file_to_module_map(modules: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Build reverse lookup: file_path -> module_id.

    Used by agents for @ reference resolution.
    """
```

**Enhanced Loader API (scripts/loader.py):**

```python
def find_module_for_file(file_path: str, core_index: Dict) -> Optional[str]:
    """
    Find which module contains a given file path.

    Enhanced to support:
    1. O(1) lookup via core_index["file_to_module_map"]
    2. Fallback to linear search in modules["files"] for backward compat
    3. Handles both monolithic and multi-level sub-module structures

    Returns:
        module_id if found, None otherwise
    """
```

**Enhanced Relevance Scoring (scripts/relevance.py):**

```python
class RelevanceScorer:
    def __init__(self, config: Dict):
        """
        Initializes with keyword-to-module-type mappings:

        self.keyword_boosts = {
            "component|vue component": ["*-components"],
            "view|page|route": ["*-views"],
            "api|endpoint|service": ["*-api"],
            "store|state|vuex|pinia": ["*-stores"],
            "composable|hook": ["*-composables"],
            "util|helper": ["*-utils"],
            "test|spec": ["*-tests"]
        }
        """

    def score_module(self, module_id: str, query: str, git_metadata: Dict) -> float:
        """
        Score a module for relevance to query.

        Enhanced to:
        1. Parse multi-level module names (parent-child-grandchild)
        2. Apply keyword boosts based on module type (components, views, api, etc.)
        3. Apply temporal boosts for recent changes
        4. Combine with existing explicit file ref and semantic scoring
        """
```

### Workflows and Sequencing

**Index Generation Workflow (Enhanced):**

```
1. Load Configuration
   ├─ Read .project-index.json
   ├─ Detect framework type (Vite/React/Next.js/generic)
   └─ Apply framework preset if strategy="auto" and match found

2. Scan Files (Unchanged)
   ├─ Traverse directory tree
   ├─ Apply .gitignore rules
   └─ Parse files for functions/classes

3. Organize into Modules (ENHANCED)
   ├─ Group files by top-level directory
   ├─ Detect large modules (>threshold files)
   ├─ For each large module:
   │  ├─ Analyze subdirectory structure
   │  ├─ Apply splitting rules (framework preset or generic)
   │  └─ Recursively split to max_depth levels
   └─ Build file-to-module mapping

4. Generate Detail Modules
   ├─ For each module/sub-module:
   │  ├─ Extract full function signatures, call graphs
   │  └─ Write to PROJECT_INDEX.d/{module_id}.json
   └─ (Unchanged from Epic 1)

5. Generate Core Index (ENHANCED)
   ├─ Include lightweight file tree
   ├─ Include module references with file lists
   ├─ Include file-to-module mapping (NEW)
   └─ Write PROJECT_INDEX.json

6. Print Summary
   └─ Report: "Split {parent_module} → {n} sub-modules"
```

**Agent Query Workflow (Enhanced):**

```
1. Agent Loads Core Index
   └─ Detects split architecture + sub-module organization

2. Query Analysis
   ├─ Parse for explicit file references (@src/components/Form.vue)
   ├─ Extract keywords ("component", "API", "store", etc.)
   └─ Check git metadata for temporal context

3. Module Resolution (ENHANCED)
   ├─ If @ reference: Use file_to_module_map for O(1) lookup
   ├─ If keywords: Apply keyword-to-module-type boosting
   ├─ If temporal: Boost recent modules
   └─ Rank all modules by combined score

4. Lazy-Load Top Modules
   ├─ Load top N scored sub-modules (default N=5)
   ├─ With MCP: Use MCP Read for file content, module for context
   └─ Without MCP: Use indexed data from loaded modules

5. Generate Response
   └─ Combine structural info (core) + detailed info (loaded modules)
```

## Non-Functional Requirements

### Performance

**Target:** Sub-module splitting adds ≤10% to index generation time

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Large Module Detection** | <100ms per module | Simple file counting operation; should be near-instantaneous |
| **Framework Pattern Detection** | <500ms per project | Directory structure analysis only (no file parsing); one-time cost per index generation |
| **Sub-Module Splitting** | <2s for 1000 files | Reorganizing file lists into sub-modules; O(n) operation where n=file count |
| **File-to-Module Map Generation** | <500ms for 10,000 files | Dictionary building; O(n) operation |
| **Overall Impact** | ≤10% of total index time | For a 30s index generation (10,000 files), sub-module logic adds ≤3s |

**Query Performance Targets:**

| Operation | Target | Current (Epic 1) | Improvement |
|-----------|--------|------------------|-------------|
| **@ Reference Resolution** | <10ms | ~100ms (linear search) | 10x faster (O(1) lookup via file_to_module_map) |
| **Module Relevance Scoring** | <50ms per module | ~30ms per module | Slight increase due to keyword boosting (~20ms overhead acceptable) |
| **Context Loading for Targeted Query** | Load ~50 files | Load ~400 files | 70%+ reduction in loaded content |

**Validation:** Story 4.1 includes performance logging; Story 4.3 measures query performance improvement on real Vite project.

### Security

**No New Security Concerns Introduced**

Epic 4 operates entirely on local filesystem data and does not introduce network communication, user input parsing, or credential handling. Security posture remains unchanged from Epic 1.

**Inherited Security Properties:**

- **File Access:** Respects existing .gitignore patterns; never accesses files outside project root
- **Path Traversal:** Uses `Path.resolve()` to prevent directory traversal attacks
- **Configuration Parsing:** JSON config parsing uses standard library (no eval or unsafe deserialization)
- **Data Integrity:** File-to-module mapping built from validated file lists (no user-controlled injection points)

**Configuration Validation:**

- `submodule_config.threshold`: Must be positive integer (validated at load time)
- `submodule_config.max_depth`: Must be 1-3 (validated at load time)
- `submodule_config.strategy`: Must be one of ["auto", "force", "disabled"] (validated at load time)
- Invalid config values → log warning and fallback to safe defaults

### Reliability/Availability

**Graceful Degradation Scenarios:**

1. **Framework Detection Failure**
   - **Scenario:** Pattern detection fails to identify framework (corrupted directory structure, unusual layout)
   - **Behavior:** Falls back to generic splitting heuristic (split by direct subdirectories)
   - **Impact:** Sub-modules still generated, but may not be optimally organized

2. **Configuration Errors**
   - **Scenario:** Invalid `submodule_config` in .project-index.json
   - **Behavior:** Log warning, fallback to default config (threshold=100, strategy=auto, max_depth=3)
   - **Impact:** Index generation continues successfully with defaults

3. **Sub-Module Splitting Errors**
   - **Scenario:** Splitting logic encounters unexpected directory structure (e.g., circular symlinks, inaccessible paths)
   - **Behavior:** Skip problematic module, log error, continue with remaining modules
   - **Impact:** Partial sub-module organization (some modules split, others remain monolithic)

4. **Backward Compatibility**
   - **Scenario:** Older agents/tools load index with new file_to_module_map field
   - **Behavior:** Unknown fields ignored by older parsers; modules["files"] arrays still present for fallback
   - **Impact:** Zero impact—backward compatible by design

**Error Recovery:**

- All splitting logic wrapped in try/catch with per-module error isolation
- Index generation never fails completely due to sub-module errors (degrades to monolithic modules)
- Validation step (Story 4.1) verifies generated sub-modules before writing to disk

### Observability

**Logging and Monitoring:**

| Event | Log Level | Information Captured | Trigger |
|-------|-----------|---------------------|---------|
| **Framework Detection** | INFO | Detected framework type (vite/react/nextjs/generic) | Always (when verbose flag enabled) |
| **Large Module Identified** | INFO | Module name, file count, threshold exceeded | When module exceeds threshold |
| **Sub-Module Split** | INFO | Parent module → list of sub-modules (with file counts) | After successful splitting |
| **File-to-Module Map Built** | DEBUG | Total entries, sample mappings | Always (when verbose flag enabled) |
| **Configuration Applied** | INFO | Strategy, threshold, max_depth, preset name | At index generation start |
| **Splitting Error** | WARN | Module name, error message, fallback behavior | When splitting fails |
| **Performance Metrics** | INFO | Time spent in detection, splitting, map building | Always (summary at end) |

**Example Log Output:**

```
📊 Sub-Module Organization:
   🔍 Framework detected: Vite
   📂 Large modules found: 2 (assureptmdashboard, docs)

   Splitting assureptmdashboard (416 files) → 9 sub-modules:
     ├─ assureptmdashboard-src-components (245 files)
     ├─ assureptmdashboard-src-views (89 files)
     ├─ assureptmdashboard-src-api (34 files)
     ├─ assureptmdashboard-src-stores (18 files)
     ├─ assureptmdashboard-src-composables (22 files)
     ├─ assureptmdashboard-src-utils (8 files)
     └─ ...

   ⏱️ Sub-module logic: 2.3s (7.6% of total)
   🗺️ File-to-module map: 416 entries built in 0.3s
```

**Metrics for Monitoring:**

- **Split Ratio:** (# sub-modules generated) / (# original modules) - tracks adoption of splitting
- **Average Module Size:** Mean file count per module before/after splitting - validates size reduction
- **Query Performance:** Time to resolve @ references before/after O(1) map - validates speedup
- **Framework Match Rate:** % of projects where framework correctly detected - quality metric

**Debugging Support:**

- `--analyze-modules` flag (Story 4.4) outputs detailed module structure analysis without modifying index
- `--verbose` flag enables DEBUG-level logging for all sub-module operations
- Generated index includes metadata: `"submodule_strategy_applied": "vite"` for troubleshooting

## Dependencies and Integrations

**No New External Dependencies**

Epic 4 maintains the dependency-free design of Epic 1's core indexing functionality. All sub-module organization logic uses Python 3.12+ standard library only.

### Runtime Dependencies

| Dependency | Version | Purpose | Required By |
|-----------|---------|---------|-------------|
| **Python** | 3.12+ | Core runtime | All scripts |
| **mcp** | ≥1.0.0 | MCP server (Epic 2) | project_index_mcp.py (optional) |
| **pydantic** | ≥2.0.0 | Input validation for MCP tools | project_index_mcp.py (optional) |

**Note:** Core indexing (scripts/project_index.py, scripts/loader.py, scripts/relevance.py) remains stdlib-only. MCP server is optional enhancement.

### Standard Library Modules Used

```python
# New or enhanced usage in Epic 4:
from pathlib import Path          # File path operations, directory traversal
from typing import Dict, List     # Type hints
import json                       # Config parsing, index generation
import re                         # Framework pattern detection
import logging                    # Observability logging

# Unchanged from Epic 1/2:
import os                         # Environment, filesystem
import datetime                   # Timestamps
import subprocess                 # Git command execution
```

### Integration Points

**1. Epic 1 Integration - Split Index Architecture**

- **Integration Type:** Direct enhancement
- **Interface:** Enhances `organize_into_modules()` function in scripts/project_index.py
- **Data Flow:**
  - Input: File list from Epic 1's scan phase
  - Output: Organized modules (now with multi-level sub-modules)
- **Compatibility:** 100% backward compatible via `submodule_config.enabled=false`

**2. Epic 2 Integration - Relevance Scoring Engine**

- **Integration Type:** Extension
- **Interface:** Enhances `RelevanceScorer.score_module()` in scripts/relevance.py
- **Data Flow:**
  - Input: Module IDs (now includes multi-level names like `parent-child-grandchild`)
  - Output: Relevance scores (now includes keyword-to-module-type boosting)
- **Compatibility:** Graceful degradation—works with monolithic modules if sub-modules not present

**3. Epic 2 Integration - MCP Server**

- **Integration Type:** Passive (no changes to MCP server)
- **Interface:** MCP tools load modules by name from core index
- **Data Flow:**
  - MCP tools see more granular module names in core index
  - `project_index_load_module("assureptmdashboard-src-components")` loads fine-grained sub-module
  - No API changes required
- **Compatibility:** MCP server works identically with monolithic or sub-module organization

**4. Configuration System Integration**

- **Integration Type:** Extension
- **Interface:** Adds `submodule_config` section to .project-index.json (Epic 1's config format)
- **Data Flow:**
  - load_configuration() reads submodule_config (if present, else defaults)
  - Configuration passed to organize_into_modules()
- **Compatibility:** Older config files without submodule_config use defaults (enabled=true, strategy=auto)

### External System Dependencies

**Git (Optional, Inherited from Epic 2):**

- **Purpose:** Framework detection may check for common framework files (.vite/config, package.json presence)
- **Behavior if Unavailable:** Falls back to directory structure analysis only (no functionality loss)
- **Version:** Any version (uses basic `ls` equivalent via pathlib)

**File System Requirements:**

- **Permissions:** Read access to project root and all subdirectories
- **Symbolic Links:** Resolved automatically by Path.resolve() (no special handling needed)
- **Case Sensitivity:** Preserves filesystem case (important for macOS/Windows compatibility)

### Upgrade/Migration Path

**From Epic 1 (Monolithic Modules):**

1. User regenerates index after Epic 4 deployment (`/index` command)
2. Configuration auto-detects: if no .project-index.json exists, creates with `submodule_config.enabled=true`
3. Large modules automatically split using detected framework preset
4. Existing agents/tools continue working (backward compatible)

**From Epic 2 (Monolithic Modules + MCP):**

1. Same as Epic 1 upgrade path
2. MCP server automatically sees new sub-module names in core index
3. No MCP server restart required (stateless server design)

**No Breaking Changes:**

- Core index schema extended (new field: `file_to_module_map`), not replaced
- Detail module schema unchanged
- MCP tool APIs unchanged
- Agents using `loader.py` continue working via fallback path

## Acceptance Criteria (Authoritative)

**Epic-Level Success Criteria:**

1. **AC-E4.1:** Large modules (>100 files) are automatically detected and split into multi-level sub-modules up to 3 levels deep
2. **AC-E4.2:** Framework patterns (Vite, React, Next.js) are automatically detected and optimal splitting rules applied
3. **AC-E4.3:** File-to-module mapping enables O(1) lookup for @ reference resolution (<10ms, down from ~100ms)
4. **AC-E4.4:** Agent queries for specific module types (components, views, API) load only relevant sub-modules (70%+ reduction in loaded files for Vite projects)
5. **AC-E4.5:** Sub-module organization is fully configurable with framework presets and per-directory control
6. **AC-E4.6:** Backward compatibility maintained: agents work with both monolithic and sub-module organization
7. **AC-E4.7:** Performance impact ≤10% of total index generation time
8. **AC-E4.8:** Configuration migration path allows smooth upgrade from monolithic to sub-module organization

**Story-Level Acceptance Criteria (from epics.md):**

**Story 4.1: Large Module Detection and Analysis**

- **AC-4.1.1:** Indexer analyzes each top-level directory module and counts total files
- **AC-4.1.2:** Large module threshold configurable (default: 100 files per module)
- **AC-4.1.3:** For modules exceeding threshold, analyze second-level directory structure
- **AC-4.1.4:** Detection logic identifies logical groupings (src/, docs/, tests/, etc.)
- **AC-4.1.5:** Analysis results logged when verbose flag enabled
- **AC-4.1.6:** Small modules (<100 files) skip sub-module detection (no unnecessary splitting)
- **AC-4.1.7:** Configuration option to disable sub-module splitting: `"enable_submodules": false`

**Story 4.2: Intelligent Sub-Module Generation with Multi-Level Splitting**

- **AC-4.2.1:** When module exceeds threshold, analyze directory tree up to 3 levels deep
- **AC-4.2.2:** Multi-level naming convention implemented: second-level `{parent}-{child}`, third-level `{parent}-{child}-{grandchild}`
- **AC-4.2.3:** Vite project patterns auto-detected: `src/components/`, `src/views/`, `src/api/`, `src/stores/`, `src/composables/`, `src/utils/`
- **AC-4.2.4:** Splitting rules applied: if `src/` has >100 files AND organized subdirectories → split to third level
- **AC-4.2.5:** Each sub-module stored in `PROJECT_INDEX.d/` with complete detail information
- **AC-4.2.6:** Core index includes file-to-module mapping in modules section with file lists for all sub-modules
- **AC-4.2.7:** Files at intermediate levels grouped logically (e.g., `src/*.ts` files → `parent-src-root.json`)
- **AC-4.2.8:** Sub-module generation preserves all existing metadata (git, functions, imports)
- **AC-4.2.9:** Original monolithic module format still generated for projects with `enable_submodules: false`
- **AC-4.2.10:** Example Vite project splits into expected structure (9-12 sub-modules)

**Story 4.3: Enhanced Relevance Scoring for Multi-Level Sub-Modules**

- **AC-4.3.1:** Relevance scoring algorithm scores multi-level sub-modules independently
- **AC-4.3.2:** Granular query matching implemented:
  - "fix LoginForm component" → scores `*-src-components` highest
  - "API endpoint for users" → scores `*-src-api` highest
  - "store mutations" → scores `*-src-stores` highest
  - "show me test coverage" → scores `*-tests` highest
- **AC-4.3.3:** Keyword-to-module mapping implemented with 7 keyword categories (component, view, api, store, composable, util, test)
- **AC-4.3.4:** Direct file reference handling: Core index file-to-module mapping enables O(1) lookup for @ references
- **AC-4.3.5:** Multiple @ references load multiple sub-modules correctly
- **AC-4.3.6:** Temporal scoring works with fine-grained sub-modules (recent changes in components don't boost views/api)
- **AC-4.3.7:** Performance improvement measurable: 70%+ reduction in loaded file count for component-specific queries
- **AC-4.3.8:** Backward compatible: relevance scoring works with monolithic, two-level, and three-level sub-module structures

**Story 4.4: Configuration and Migration for Multi-Level Sub-Modules**

- **AC-4.4.1:** Configuration option in `.project-index.json` includes: `submodule_strategy`, `submodule_threshold`, `submodule_max_depth`, `submodule_patterns`
- **AC-4.4.2:** Built-in framework presets implemented: vite, react, nextjs, generic
- **AC-4.4.3:** Strategy "auto" applies framework preset if detected, else generic
- **AC-4.4.4:** Strategy "force" always generates sub-modules regardless of size
- **AC-4.4.5:** Strategy "disabled" uses monolithic modules (legacy behavior)
- **AC-4.4.6:** `submodule_max_depth` controls splitting depth (1-3 levels)
- **AC-4.4.7:** Migration path: regenerating index with new config automatically reorganizes modules
- **AC-4.4.8:** Documentation explains multi-level sub-module configuration with Vite examples
- **AC-4.4.9:** `--analyze-modules` flag shows current structure, file counts, and suggested configuration
- **AC-4.4.10:** Warning system alerts for modules >200 files and detected frameworks without presets enabled

## Traceability Mapping

| Acceptance Criterion | Spec Section | Component/Function | Test Idea |
|---------------------|--------------|-------------------|-----------|
| **AC-E4.1** | Detailed Design: Services and Modules | `detect_large_modules()`, `split_module_recursive()` | Unit test: verify modules >100 files trigger splitting |
| **AC-E4.2** | Detailed Design: APIs and Interfaces | `detect_framework_patterns()`, `apply_framework_preset()` | Integration test: verify Vite project applies vite preset |
| **AC-E4.3** | NFR: Performance | `build_file_to_module_map()`, enhanced `find_module_for_file()` | Performance test: measure @ reference lookup time (<10ms) |
| **AC-E4.4** | Detailed Design: Workflows | Enhanced `RelevanceScorer.score_module()` with keyword boosting | Integration test: query "fix component" loads only src-components module |
| **AC-E4.5** | Detailed Design: Data Models | Configuration schema in .project-index.json | Unit test: validate config parsing and preset application |
| **AC-E4.6** | NFR: Reliability | Backward compatibility handling in loader.py | Integration test: old agents load new index format successfully |
| **AC-E4.7** | NFR: Performance | Sub-module logic performance metrics | Performance test: measure overhead % of total index time |
| **AC-E4.8** | Dependencies and Integrations: Upgrade Path | Configuration auto-detection and migration | Integration test: upgrade from Epic 1 → Epic 4 preserves data |
| **AC-4.1.1** | Detailed Design: Services | `detect_large_modules()` counting files per module | Unit test: count files correctly across nested structures |
| **AC-4.1.2** | Detailed Design: Data Models | `submodule_config.threshold` configuration field | Unit test: verify threshold is configurable and respected |
| **AC-4.1.3** | Detailed Design: Workflows | Directory structure analysis in `split_module_recursive()` | Unit test: verify second-level directory identification |
| **AC-4.1.4** | Detailed Design: Services | Pattern detection logic in `detect_large_modules()` | Unit test: identify src/, docs/, tests/ correctly |
| **AC-4.1.5** | NFR: Observability | Logging statements in detection phase | Manual test: verify verbose flag shows analysis results |
| **AC-4.1.6** | Detailed Design: Workflows | Short-circuit logic in `organize_into_modules()` | Unit test: modules <100 files skip splitting |
| **AC-4.1.7** | Detailed Design: Data Models | `submodule_config.enabled` configuration field | Unit test: verify disable flag bypasses all splitting |
| **AC-4.2.1** | Detailed Design: APIs | `split_module_recursive()` with max_depth parameter | Unit test: verify recursion depth respects max_depth=3 |
| **AC-4.2.2** | Detailed Design: Data Models | Module naming convention in core index | Unit test: verify naming `parent-child-grandchild` format |
| **AC-4.2.3** | Detailed Design: Services | `detect_framework_patterns()` Vite detection | Unit test: detect Vite by src/components, src/views presence |
| **AC-4.2.4** | Detailed Design: Workflows | Splitting rules logic in `split_module_recursive()` | Unit test: verify conditional third-level splitting |
| **AC-4.2.5** | Detailed Design: Data Models | Detail module generation unchanged from Epic 1 | Integration test: verify sub-module JSON has full signatures |
| **AC-4.2.6** | Detailed Design: Data Models | Core index schema with file-to-module mapping | Unit test: verify modules section includes files arrays |
| **AC-4.2.7** | Detailed Design: Workflows | Intermediate file handling in `split_module_recursive()` | Unit test: verify root-level files grouped into `*-root` module |
| **AC-4.2.8** | Detailed Design: Services | Metadata preservation in module organization | Integration test: verify git metadata present in sub-modules |
| **AC-4.2.9** | NFR: Reliability | Backward compatibility with monolithic format | Integration test: verify `enable_submodules: false` works |
| **AC-4.2.10** | Detailed Design: Workflows | Example output validation | Integration test: run on real Vite project, verify split count |
| **AC-4.3.1** | Detailed Design: APIs | Enhanced `RelevanceScorer.score_module()` | Unit test: score sub-modules independently from parent |
| **AC-4.3.2** | Detailed Design: APIs | Keyword-to-module-type mapping logic | Unit test: verify query keywords map to correct module types |
| **AC-4.3.3** | Detailed Design: APIs | `self.keyword_boosts` dictionary in RelevanceScorer | Unit test: verify 7 keyword categories implemented |
| **AC-4.3.4** | Detailed Design: APIs | Enhanced `find_module_for_file()` with O(1) lookup | Unit test: verify @ reference resolves in <10ms |
| **AC-4.3.5** | Detailed Design: Workflows | Multiple @ reference handling in agent query workflow | Integration test: verify `@file1 @file2` loads both modules |
| **AC-4.3.6** | Detailed Design: APIs | Temporal scoring isolation per sub-module | Unit test: verify recent component change doesn't boost views |
| **AC-4.3.7** | NFR: Performance | Query performance comparison metric | Performance test: measure file count loaded before/after |
| **AC-4.3.8** | NFR: Reliability | Graceful degradation with monolithic modules | Integration test: scoring works on legacy index format |
| **AC-4.4.1** | Detailed Design: Data Models | Configuration schema definition | Unit test: validate JSON schema for submodule_config |
| **AC-4.4.2** | Detailed Design: Services | Framework preset implementations | Unit test: verify vite, react, nextjs presets exist and valid |
| **AC-4.4.3** | Detailed Design: Workflows | Strategy "auto" logic | Integration test: verify auto-detection applies correct preset |
| **AC-4.4.4** | Detailed Design: Data Models | Strategy "force" configuration | Unit test: verify force strategy splits even small modules |
| **AC-4.4.5** | Detailed Design: Data Models | Strategy "disabled" configuration | Unit test: verify disabled strategy uses monolithic format |
| **AC-4.4.6** | Detailed Design: Data Models | `submodule_max_depth` configuration field | Unit test: verify depth limits enforced (1-3) |
| **AC-4.4.7** | Dependencies and Integrations: Upgrade Path | Index regeneration with new config | Integration test: verify regeneration reorganizes modules |
| **AC-4.4.8** | Detailed Design: Documentation requirement | README/docs updates | Manual test: review documentation for Vite examples |
| **AC-4.4.9** | NFR: Observability | `--analyze-modules` flag implementation | Integration test: verify flag outputs expected analysis |
| **AC-4.4.10** | NFR: Observability | Warning system implementation | Integration test: verify warnings appear for large modules |

## Risks, Assumptions, Open Questions

### Risks

**RISK-1: Framework Detection False Positives/Negatives**
- **Description:** Pattern detection may incorrectly identify framework type or fail to detect framework
- **Impact:** Medium - Results in suboptimal sub-module organization (e.g., Vite project treated as generic)
- **Likelihood:** Low - Detection uses conservative patterns (presence of characteristic directories)
- **Mitigation:**
  - Provide `--analyze-modules` flag for manual verification before applying
  - Allow manual override via `submodule_patterns.custom` config
  - Falls back to generic splitting (still functional, just less optimized)

**RISK-2: Performance Degradation on Very Large Projects**
- **Description:** Sub-module splitting logic may add >10% overhead on projects with 50,000+ files
- **Impact:** Medium - Slower index generation may frustrate users on very large codebases
- **Likelihood:** Low - Algorithm is O(n) with small constants; tested up to 10,000 files
- **Mitigation:**
  - Story 4.1 includes performance benchmarking on large projects
  - Provide `submodule_config.enabled=false` escape hatch
  - Profile and optimize if needed after benchmarking

**RISK-3: Backward Compatibility Edge Cases**
- **Description:** Older agents or custom tools may not handle new index format gracefully
- **Impact:** Medium - Users with custom tooling may experience breakage
- **Likelihood:** Low - New fields are additive; modules["files"] arrays preserved for fallback
- **Mitigation:**
  - Comprehensive backward compatibility testing (Story 4.3 AC-4.3.8)
  - Document migration path and potential breaking changes
  - Provide rollback mechanism (regenerate with `enable_submodules: false`)

**RISK-4: Complex Project Structures Not Covered by Presets**
- **Description:** Some projects may have unique structures that don't match framework presets or generic heuristics
- **Impact:** Low - Sub-modules generated but not optimally organized
- **Likelihood:** Medium - Monorepos and custom build systems have varied structures
- **Mitigation:**
  - Provide flexible `submodule_patterns.custom` configuration for per-project tuning
  - Generic fallback splits by any subdirectory structure
  - Users can disable and use monolithic if needed

### Assumptions

**ASSUMPTION-1: Directory Structure Reflects Logical Organization**
- **Details:** Assumes developers organize code into meaningful directories (components/, views/, api/)
- **Validation:** Story 4.2 tests on real-world Vite/React/Next.js projects
- **Impact if False:** Sub-modules may not align with developer mental model, but still reduce context size

**ASSUMPTION-2: Framework Patterns Remain Stable**
- **Details:** Assumes Vite, React, Next.js continue using current directory conventions
- **Validation:** Framework presets based on official documentation and common practices as of 2025
- **Impact if False:** May need to update presets in future releases; custom config provides override

**ASSUMPTION-3: 100 Files is Appropriate Default Threshold**
- **Details:** Assumes modules with >100 files benefit from splitting; <100 don't need it
- **Validation:** Story 4.1 tests threshold on various project sizes
- **Impact if False:** Threshold is configurable; users can adjust via `submodule_config.threshold`

**ASSUMPTION-4: O(1) Lookup Provides Meaningful Speedup**
- **Details:** Assumes file-to-module map lookup (dictionary) is significantly faster than linear search
- **Validation:** Story 4.3 performance testing measures before/after with real @ references
- **Impact if False:** Still provides correct functionality; performance gain may be marginal on small projects

**ASSUMPTION-5: Agents Will Use File-to-Module Map**
- **Details:** Assumes agents are updated to use new file_to_module_map field for @ reference resolution
- **Validation:** Story 4.3 updates index-analyzer agent to use new field
- **Impact if False:** Agents fall back to linear search in modules["files"] arrays (backward compatible but slower)

### Open Questions

**QUESTION-1: Should We Support Custom Naming Conventions?**
- **Context:** Current naming uses `parent-child-grandchild`; some projects may prefer `parent/child/grandchild` or `parent.child.grandchild`
- **Proposed Answer:** No for MVP (Story 4.2); naming convention is internal to index; users see file paths, not module IDs
- **Decision Needed By:** Story 4.2 implementation
- **Stakeholder:** Development team

**QUESTION-2: Should Framework Detection Check package.json?**
- **Context:** Could improve detection accuracy by reading `"dependencies": {"vite": "..."}`
- **Proposed Answer:** No for MVP (Story 4.1); keep detection simple (directory structure only); parsing package.json adds complexity and external file dependency
- **Decision Needed By:** Story 4.1 implementation
- **Stakeholder:** Development team

**QUESTION-3: Should We Auto-Migrate Existing Configurations?**
- **Context:** When user regenerates index, should we automatically add `submodule_config` to their .project-index.json?
- **Proposed Answer:** Yes (Story 4.4); write `submodule_config` section with detected settings on first post-Epic 4 index generation; include comment explaining new feature
- **Decision Needed By:** Story 4.4 implementation
- **Stakeholder:** Product/UX decision

**QUESTION-4: What Happens with Symlinked Directories?**
- **Context:** How should splitting handle symlinks pointing to external directories?
- **Proposed Answer:** Path.resolve() will follow symlinks; files in symlinked dirs treated same as regular files; may cross module boundaries
- **Decision Needed By:** Story 4.1 implementation (edge case handling)
- **Stakeholder:** Development team

## Test Strategy Summary

### Test Levels and Coverage

**Unit Tests (Story-Specific):**

| Story | Test Focus | Key Test Cases | Coverage Target |
|-------|------------|----------------|-----------------|
| **4.1** | Large module detection logic | Threshold edge cases, counting accuracy, config validation | 95% line coverage |
| **4.2** | Sub-module splitting algorithm | Recursive splitting, naming convention, framework patterns | 90% line coverage |
| **4.3** | Relevance scoring enhancements | Keyword mapping, O(1) lookup, scoring weights | 95% line coverage |
| **4.4** | Configuration parsing and migration | Config validation, preset application, defaults | 95% line coverage |

**Integration Tests (Cross-Story):**

1. **End-to-End Index Generation:** Generate index on real Vite project, verify sub-modules created correctly
2. **Agent Query Workflow:** Simulate agent query with @ references, verify correct sub-module loaded
3. **Backward Compatibility:** Load Epic 4 index with Epic 1 agent, verify fallback path works
4. **Framework Detection Flow:** Test auto-detection on multiple project types (Vite, React, Next.js, generic)
5. **Configuration Migration:** Regenerate index with new config, verify modules reorganized correctly

**Performance Tests:**

1. **Sub-Module Overhead:** Measure index generation time before/after Epic 4 on 1000, 5000, 10000 file projects
2. **File-to-Module Lookup:** Benchmark @ reference resolution time (target: <10ms, 10x improvement)
3. **Query Performance:** Measure context size loaded for "fix component" query before/after (target: 70%+ reduction)

**Acceptance Tests (Per AC):**

- All 47 acceptance criteria (8 epic-level + 39 story-level) mapped to specific test cases in traceability matrix
- Each AC has corresponding unit, integration, or performance test
- Manual tests only for observability/logging verification (AC-4.1.5, AC-4.4.8)

### Test Data and Fixtures

**Synthetic Test Projects:**

- **Small Project:** 50 files, flat structure (no splitting expected)
- **Medium Vite Project:** 400 files with `src/components/`, `src/views/`, `src/api/` (split into 8-10 sub-modules)
- **Large Generic Project:** 1000 files, mixed structure (generic splitting heuristic)
- **Edge Case Project:** Unusual structure with deep nesting, symlinks, scattered files

**Real-World Test Projects (Integration):**

- Clone public Vite project from GitHub (e.g., `vitejs/vite-plugin-vue` examples)
- Clone public React project with conventional structure
- Clone Next.js starter template

### Test Frameworks and Tools

```python
# Unit Testing
import unittest                    # Standard Python unit testing
from unittest.mock import Mock     # Mocking filesystem, config

# Performance Testing
import time                        # Timing measurements
import cProfile                    # Profiling for bottleneck identification

# Integration Testing
import tempfile                    # Temporary test fixtures
import shutil                      # Cleanup
```

### Critical Path Testing

**Priority 1 (Must Pass for Epic Acceptance):**

1. Large module detection correctly identifies modules >threshold (AC-4.1.1, AC-4.1.2)
2. Sub-module splitting generates correct naming convention (AC-4.2.2)
3. File-to-module map enables O(1) lookup (AC-4.3.4)
4. Backward compatibility preserved with monolithic modules (AC-4.3.8, AC-E4.6)
5. Performance impact ≤10% on representative project (AC-E4.7)

**Priority 2 (Should Pass for Quality):**

6. Framework detection identifies Vite/React/Next.js correctly (AC-4.2.3, AC-E4.2)
7. Keyword-to-module boosting works for 7 categories (AC-4.3.3)
8. Configuration validation enforces constraints (AC-4.4.1 through AC-4.4.6)
9. Query performance shows 70%+ reduction on component query (AC-E4.4, AC-4.3.7)

**Priority 3 (Nice to Have):**

10. Logging and observability features (AC-4.1.5, AC-4.4.9, AC-4.4.10)
11. Documentation completeness (AC-4.4.8)

### Test Execution Plan

**Per-Story Testing:**
- Developer runs unit tests locally before committing (each story)
- CI/CD runs full unit test suite on every commit
- Integration tests run on PR creation

**Epic-Level Testing:**
- Full integration test suite runs after Story 4.4 complete
- Performance benchmarking on dedicated hardware (avoid noise)
- Real-world project testing on 3 public projects
- Backward compatibility validation with Epic 1/2 indices

**Acceptance Criteria Sign-Off:**
- Each AC validated with specific test case (see traceability matrix)
- Test results documented in story completion notes
- Performance metrics captured and compared against targets
