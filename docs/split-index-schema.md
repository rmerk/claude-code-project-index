# Split Index Schema Documentation

**Version:** 2.0-split
**Status:** Design Specification
**Epic:** 1 - Split Index Architecture
**Last Updated:** 2025-10-31

## Table of Contents

1. [Overview](#overview)
2. [Design Rationale](#design-rationale)
3. [Core Index Schema](#core-index-schema)
4. [Detail Module Schema](#detail-module-schema)
5. [JSON Examples](#json-examples)
6. [Feature Mapping](#feature-mapping)
7. [Size Budget and Optimization](#size-budget-and-optimization)
8. [Module Organization Strategy](#module-organization-strategy)
9. [Backward Compatibility](#backward-compatibility)
10. [Migration Notes](#migration-notes)

---

## Overview

The Split Index Architecture separates project metadata into two layers:

1. **Core Index** (`PROJECT_INDEX.json`) - Lightweight, always-loaded navigation structure
2. **Detail Modules** (`PROJECT_INDEX.d/*.json`) - Detailed implementation context, lazy-loaded on demand

### Goals

- **Scalability**: Support codebases up to 10,000 files while keeping core index under 100KB (~25,000 tokens)
- **Performance**: Enable fast initial navigation without loading full implementation details
- **Completeness**: Preserve all existing index features without information loss
- **Compatibility**: Support both legacy (v1.0) and split (v2.0) formats

### Key Metrics (Real-World Validation)

Analysis of 670-file project (95.7KB legacy format):
- Core index: **15.9KB** (16.6%)
- Detail modules: **79.9KB** (83.4%)
- **Compression: 83.4%** (exceeds 60-80% goal)

Size breakdown (legacy format):
- Function signatures + bodies: **57.8%**
- Dependencies: **29.5%**
- Call graph: **9.3%**
- Documentation: **1.7%**
- Tree structure: **0.9%**

---

## Design Rationale

### Core vs. Detail Separation

**Core Index Contains:**
- Directory tree (navigation)
- Lightweight function signatures (name + line number only)
- Module references (lazy-loading map)
- Global call graph (cross-module relationships)
- Critical documentation (README*, ARCHITECTURE*, API*)
- Import structure (file-level dependencies)
- Git metadata placeholders (future: Epic 2, Story 2.3)

**Detail Modules Contain:**
- Full function signatures (params, return types, docstrings)
- Complete class definitions with methods
- Local call graph (within-module relationships)
- Standard and archived documentation
- File-level implementation details

### Why This Split?

1. **Size Reduction**: Full signatures and dependencies consume 87.3% of index size
2. **Lazy Loading**: Most queries only need navigation context, not full implementation details
3. **Relevance**: AI agents can load details for only the modules they need
4. **Performance**: Fast initial index load enables quick project orientation

---

## Core Index Schema

### Format Version: 2.0-split

```typescript
interface CoreIndex {
  version: "2.0-split"  // Format identifier
  at: string            // ISO 8601 timestamp
  root: string          // Project root path
  tree: string[]        // Compact ASCII directory structure
  stats: Stats          // Project statistics
  modules: ModuleMap    // Module references for lazy loading
  f_signatures: SignatureMap  // Lightweight function/class signatures
  imports: ImportMap    // File-level dependency graph
  g: CallGraphEdge[]    // Global cross-module call graph
  d_critical: DocMap    // Critical documentation only
}

interface Stats {
  total_files: number
  total_modules: number
  core_size_kb: number
  fully_parsed: Record<string, number>  // e.g., {"python": 45, "javascript": 32}
  listed_only: Record<string, number>   // e.g., {"json": 12, "shell": 8}
  markdown_files: number
}

interface ModuleMap {
  [module_id: string]: ModuleReference
}

interface ModuleReference {
  path: string          // Relative path to detail module (e.g., "PROJECT_INDEX.d/auth.json")
  files: string[]       // List of files in this module
  functions: number     // Total function count
  classes: number       // Total class count
  modified: string      // ISO 8601 timestamp of most recent file change
}

interface SignatureMap {
  [file_path: string]: string[]  // Array of "name:line" signatures
}

interface ImportMap {
  [file_path: string]: string[]  // Array of imported module names
}

type CallGraphEdge = [string, string]  // [caller, callee] function name pairs

interface DocMap {
  [file_path: string]: string[]  // Array of markdown header titles
}
```

### Field Specifications

#### `version`
- **Type**: String literal `"2.0-split"`
- **Purpose**: Format identifier for split architecture
- **Legacy**: Absent or `"1.0"` indicates legacy single-file format

#### `at`
- **Type**: ISO 8601 datetime string
- **Example**: `"2025-10-31T10:27:20.809940"`
- **Purpose**: Index generation timestamp

#### `root`
- **Type**: String (path)
- **Example**: `"."` or `"/Users/dev/myproject"`
- **Purpose**: Project root directory

#### `tree`
- **Type**: Array of strings
- **Format**: Compact ASCII tree representation
- **Characters**: `├──`, `└──`, `│`, `(N files)` annotations
- **Size**: Typically <1% of total index size (highly optimized)

**Example:**
```json
"tree": [
  ".",
  "├── src/",
  "│   ├── auth/ (5 files)",
  "│   │   ├── login.py",
  "│   │   └── session.py",
  "│   └── database/",
  "└── docs/"
]
```

#### `stats`
- **Purpose**: Project-level statistics for quick insights
- **Fields**:
  - `total_files`: Count of all indexed files
  - `total_modules`: Number of detail modules generated
  - `core_size_kb`: Core index size in KB (monitoring for 100KB limit)
  - `fully_parsed`: File counts by language (functions/classes extracted)
  - `listed_only`: File counts by type (listed but not parsed)
  - `markdown_files`: Total markdown file count

#### `modules`
- **Purpose**: Directory mapping for lazy-loading detail modules
- **Key**: module_id (directory name or "root" for flat files)
- **Value**: Module reference with path, file list, counts, and timestamp

**Example:**
```json
"modules": {
  "auth": {
    "path": "PROJECT_INDEX.d/auth.json",
    "files": ["src/auth/login.py", "src/auth/session.py"],
    "functions": 23,
    "classes": 2,
    "modified": "2025-10-29T14:32:00Z"
  },
  "root": {
    "path": "PROJECT_INDEX.d/root.json",
    "files": ["config.py", "main.py"],
    "functions": 8,
    "classes": 0,
    "modified": "2025-10-30T09:15:00Z"
  }
}
```

#### `f_signatures`
- **Purpose**: Lightweight function/class signatures for quick navigation
- **Format**: `"name:line:parent:type"`
  - `name`: Function or class name
  - `line`: Line number where defined
  - `parent`: Parent class name (if method) or empty
  - `type`: `f` (function), `c` (class), `m` (method)

**Note**: Parameters, return types, and docstrings are in detail modules only.

**Example:**
```json
"f_signatures": {
  "src/auth/login.py": [
    "login:42::f",
    "validate:67::f",
    "User:15::c",
    "get_user:22:User:m"
  ]
}
```

#### `imports`
- **Purpose**: File-level dependency graph
- **Format**: File path → array of imported module names
- **Note**: Moved from legacy deps field for clarity
- **Design Decision**: See "Dependencies Placement Decision" below

**Example:**
```json
"imports": {
  "src/auth/login.py": ["session", "crypto", "database.user"],
  "src/auth/session.py": ["crypto", "utils.time"]
}
```

**⚠️ DEPENDENCIES PLACEMENT DECISION**

Real-world validation reveals dependencies are **29.7% of legacy index size** - the second-largest component after functions. This creates a critical design decision:

**Option 1: Dependencies in CORE** (recommended, implemented in this schema)
- Core size: ~60 KB for 670-file project (36.6% compression)
- ✅ Fast dependency queries without loading detail modules
- ✅ Enable quick "what imports this?" searches
- ✅ Better developer/AI experience for code exploration
- ⚠️ Less aggressive compression

**Option 2: Dependencies in DETAIL only** (alternative for very large projects)
- Core size: ~32 KB for 670-file project (66.3% compression)
- ✅ Maximum compression (matches 83.4% goal in context)
- ✅ Better for very large codebases (>5,000 files)
- ⚠️ Dependency queries require loading detail modules

**Recommendation**: Start with Option 1, make configurable via `--deps-in-detail` flag for projects approaching 100 KB core limit.

See [Split Index Schema Validation](split-index-schema-validation.md) for detailed real-world analysis.

#### `g` (global call graph)
- **Purpose**: Cross-module function call relationships
- **Format**: Array of `[caller, callee]` tuples
- **Scope**: Only cross-module calls (within-module calls in detail modules)
- **Size**: ~9.3% of legacy index (acceptable for core)

**Example:**
```json
"g": [
  ["login", "validate"],
  ["login", "create_session"],
  ["authenticate_api", "login"],
  ["check_permission", "get_user_role"]
]
```

#### `d_critical`
- **Purpose**: Critical documentation for project orientation
- **Scope**: README*, ARCHITECTURE*, API* files only
- **Format**: File path → array of markdown headers

**Example:**
```json
"d_critical": {
  "README.md": [
    "Project Index for Claude Code",
    "Installation",
    "Usage",
    "Configuration"
  ],
  "ARCHITECTURE.md": [
    "System Architecture",
    "Data Flow",
    "Component Overview"
  ]
}
```

---

## Detail Module Schema

### Format Version: 2.0-split

```typescript
interface DetailModule {
  module_id: string     // Module identifier (directory name or "root")
  version: "2.0-split"  // Format identifier
  modified: string      // ISO 8601 timestamp
  files: FileDetailMap  // Per-file detailed content
  call_graph_local: CallGraphEdge[]  // Within-module call relationships
  doc_standard: DocMap  // Standard documentation (non-critical md files)
  doc_archive: DocMap   // Archived/legacy documentation
}

interface FileDetailMap {
  [file_path: string]: FileDetail
}

interface FileDetail {
  language: string      // Language identifier (e.g., "python", "javascript")
  functions: FunctionDetail[]
  classes: ClassDetail[]
  imports: string[]     // Module dependencies for this file
}

interface FunctionDetail {
  name: string
  line: number
  signature: string     // Full signature with params and return type
  calls: string[]       // Functions called by this function
  doc: string           // Docstring or comment
  category?: string     // Optional: Function category for Vue Options API ('methods' | 'computed' | 'lifecycle' | 'watch')
}

interface ClassDetail {
  name: string
  line: number
  bases: string[]       // Parent class names
  methods: MethodDetail[]
  doc: string
}

interface MethodDetail {
  name: string
  line: number
  signature: string
  calls: string[]
  doc: string
}
```

### Field Specifications

#### `module_id`
- **Type**: String
- **Format**: Directory name (e.g., "auth", "database") or "root" for flat files
- **Purpose**: Identifier matching core index modules map

#### `version`
- **Type**: String literal `"2.0-split"`
- **Purpose**: Format identifier (same as core index)

#### `modified`
- **Type**: ISO 8601 datetime string
- **Purpose**: Timestamp of most recently modified file in module

#### `files`
- **Purpose**: Detailed implementation information per file
- **Key**: File path (relative to project root)
- **Value**: Complete function/class definitions with full signatures

#### `category` (Function Metadata Field)
- **Type**: Optional string
- **Purpose**: Categorizes Vue Options API methods by their role in component lifecycle
- **Scope**: Only present for Vue Options API functions (not Composition API or other languages)
- **Values**:
  - `'methods'` - Functions defined in `methods: { ... }` block
  - `'computed'` - Computed properties defined in `computed: { ... }` block
  - `'lifecycle'` - Vue lifecycle hooks (created, mounted, beforeDestroy, etc.)
  - `'watch'` - Watchers defined in `watch: { ... }` block
- **Added**: Epic 2 Extension (Story 2.11 - Vue Options API Method Extraction)
- **Backward Compatibility**: Optional field, omitted for non-Vue files and Composition API

**Example Usage**:
```json
{
  "files": {
    "src/components/UserProfile.vue": {
      "functions": [
        {
          "name": "fetchData",
          "line": 42,
          "category": "methods",
          "signature": "() => Promise<void>"
        },
        {
          "name": "fullName",
          "line": 18,
          "category": "computed",
          "signature": "() => string"
        },
        {
          "name": "created",
          "line": 55,
          "category": "lifecycle",
          "signature": "() => void"
        }
      ]
    }
  }
}
```

#### `call_graph_local`
- **Purpose**: Function call relationships within this module
- **Format**: Same as core index `g` field (array of tuples)
- **Scope**: Only intra-module calls

#### `doc_standard` and `doc_archive`
- **Purpose**: Documentation tier separation (infrastructure for Epic 2)
- **Standard**: Regular documentation files
- **Archive**: Legacy or deprecated documentation
- **Format**: Same as core index documentation maps

---

## JSON Examples

### Example 1: Core Index (Small Project)

```json
{
  "version": "2.0-split",
  "at": "2025-10-31T10:27:20.809940",
  "root": ".",
  "tree": [
    ".",
    "├── src/",
    "│   ├── auth/ (2 files)",
    "│   │   ├── login.py",
    "│   │   └── session.py",
    "│   └── database/ (3 files)",
    "├── tests/",
    "└── README.md"
  ],
  "stats": {
    "total_files": 12,
    "total_modules": 3,
    "core_size_kb": 8,
    "fully_parsed": {
      "python": 5,
      "javascript": 0
    },
    "listed_only": {
      "json": 2,
      "yaml": 1
    },
    "markdown_files": 4
  },
  "modules": {
    "auth": {
      "path": "PROJECT_INDEX.d/auth.json",
      "files": ["src/auth/login.py", "src/auth/session.py"],
      "functions": 8,
      "classes": 2,
      "modified": "2025-10-29T14:32:00Z"
    },
    "database": {
      "path": "PROJECT_INDEX.d/database.json",
      "files": [
        "src/database/connection.py",
        "src/database/models.py",
        "src/database/queries.py"
      ],
      "functions": 15,
      "classes": 4,
      "modified": "2025-10-30T09:15:00Z"
    },
    "root": {
      "path": "PROJECT_INDEX.d/root.json",
      "files": ["config.py", "main.py"],
      "functions": 3,
      "classes": 0,
      "modified": "2025-10-31T08:00:00Z"
    }
  },
  "f_signatures": {
    "src/auth/login.py": [
      "login:42::f",
      "validate_credentials:67::f",
      "User:15::c",
      "authenticate:22:User:m"
    ],
    "src/auth/session.py": [
      "create_session:10::f",
      "destroy_session:25::f",
      "Session:5::c"
    ],
    "src/database/connection.py": [
      "connect:8::f",
      "disconnect:20::f",
      "DatabaseConnection:3::c"
    ]
  },
  "imports": {
    "src/auth/login.py": ["session", "crypto", "database.models"],
    "src/auth/session.py": ["crypto", "utils.time"],
    "src/database/connection.py": ["os", "sys"]
  },
  "g": [
    ["login", "validate_credentials"],
    ["login", "create_session"],
    ["validate_credentials", "User.authenticate"],
    ["create_session", "connect"]
  ],
  "d_critical": {
    "README.md": [
      "Project Index for Claude Code",
      "Quick Install",
      "Usage",
      "What It Does"
    ]
  }
}
```

### Example 2: Detail Module (auth.json)

```json
{
  "module_id": "auth",
  "version": "2.0-split",
  "modified": "2025-10-29T14:32:00Z",
  "files": {
    "src/auth/login.py": {
      "language": "python",
      "functions": [
        {
          "name": "login",
          "line": 42,
          "signature": "(username: str, password: str, remember: bool = False) -> SessionToken | None",
          "calls": ["validate_credentials", "create_session"],
          "doc": "Authenticate user and create session. Returns SessionToken on success, None on failure."
        },
        {
          "name": "validate_credentials",
          "line": 67,
          "signature": "(username: str, password: str) -> bool",
          "calls": ["User.authenticate", "hash_password"],
          "doc": "Validate username/password pair against database. Uses bcrypt hashing."
        }
      ],
      "classes": [
        {
          "name": "User",
          "line": 15,
          "bases": ["BaseModel"],
          "methods": [
            {
              "name": "authenticate",
              "line": 22,
              "signature": "(self, password: str) -> bool",
              "calls": ["hash_password", "compare_hash"],
              "doc": "Authenticate user instance with provided password"
            },
            {
              "name": "create",
              "line": 30,
              "signature": "(cls, username: str, password: str) -> User",
              "calls": ["hash_password", "database.insert"],
              "doc": "Create new user in database with hashed password"
            }
          ],
          "doc": "User model representing authenticated system users"
        }
      ],
      "imports": ["session", "crypto", "database.models"]
    },
    "src/auth/session.py": {
      "language": "python",
      "functions": [
        {
          "name": "create_session",
          "line": 10,
          "signature": "(user_id: int, ip_address: str) -> SessionToken",
          "calls": ["generate_token", "store_session", "connect"],
          "doc": "Create new session for authenticated user"
        },
        {
          "name": "destroy_session",
          "line": 25,
          "signature": "(token: SessionToken) -> bool",
          "calls": ["delete_session", "connect"],
          "doc": "Invalidate session and remove from storage"
        }
      ],
      "classes": [
        {
          "name": "Session",
          "line": 5,
          "bases": [],
          "methods": [
            {
              "name": "is_valid",
              "line": 7,
              "signature": "(self) -> bool",
              "calls": ["check_expiry"],
              "doc": "Check if session is still valid (not expired)"
            }
          ],
          "doc": "Session data container with validation methods"
        }
      ],
      "imports": ["crypto", "utils.time"]
    }
  },
  "call_graph_local": [
    ["login", "validate_credentials"],
    ["validate_credentials", "User.authenticate"],
    ["User.authenticate", "hash_password"],
    ["User.create", "hash_password"]
  ],
  "doc_standard": {},
  "doc_archive": {}
}
```

---

## Feature Mapping

### Legacy Format → Split Format Mapping

This table ensures **zero information loss** during migration from legacy (v1.0) to split (v2.0) format.

| Legacy Field | Core Index Field | Detail Module Field | Notes |
|--------------|------------------|---------------------|-------|
| `at` | `at` | - | Timestamp preserved in core |
| `root` | `root` | - | Project root in core |
| `tree` | `tree` | - | Unchanged, already optimal |
| `stats.total_files` | `stats.total_files` | - | Aggregate count in core |
| `stats.fully_parsed` | `stats.fully_parsed` | - | Language breakdown in core |
| `stats.listed_only` | `stats.listed_only` | - | Non-parsed file counts in core |
| `stats.markdown_files` | `stats.markdown_files` | - | Documentation count in core |
| `f.<file>` (full) | `f_signatures.<file>` (light) | `files.<file>.functions` (full) | **Split**: Names+lines in core, full signatures in detail |
| `f.<file>` (classes) | `f_signatures.<file>` (light) | `files.<file>.classes` (full) | **Split**: Names+lines in core, methods in detail |
| `g` (all edges) | `g` (cross-module) | `call_graph_local` (within-module) | **Split**: Global calls in core, local calls in detail |
| `d` (all docs) | `d_critical` (README*, ARCH*) | `doc_standard`, `doc_archive` | **Split by tier**: Critical in core, rest in detail |
| `deps.<file>` | `imports.<file>` | `files.<file>.imports` | **Renamed + Duplicated**: File-level in core, same in detail for convenience |
| `dir_purposes` | (removed) | - | Deprecated field, not migrated |
| (no field) | `version` | `version` | **New**: Format identifier "2.0-split" |
| (no field) | `modules` | - | **New**: Module reference map for lazy loading |
| (no field) | `stats.total_modules` | - | **New**: Module count |
| (no field) | `stats.core_size_kb` | - | **New**: Size monitoring |
| (no field) | - | `module_id` | **New**: Module identifier |
| (no field) | - | `modified` | **New**: Module timestamp |

### Feature Completeness Verification

✅ **Functions preserved**:
- Legacy: Full signature in single file
- Split: Lightweight signature in core, full signature in detail

✅ **Classes preserved**:
- Legacy: Full class with methods in single file
- Split: Name+line in core, full definition with methods in detail

✅ **Call graph preserved**:
- Legacy: All edges in `g` array
- Split: Cross-module edges in core `g`, within-module edges in detail `call_graph_local`

✅ **Documentation preserved**:
- Legacy: All docs in `d` map
- Split: Critical docs in core `d_critical`, others in detail `doc_standard`/`doc_archive`

✅ **Dependencies preserved**:
- Legacy: `deps` field with file-level imports
- Split: Same data in core `imports` (renamed for clarity)

✅ **Tree structure preserved**:
- Format unchanged (already optimal at <1% size)

---

## Size Budget and Optimization

### Target: Core Index ≤ 100KB for 10,000 Files

#### Optimization Strategies

**1. Function Signatures (57.8% of legacy size)**
- **Legacy**: Full signatures with params, return types, docstrings
- **Split**: Name + line number only in core (e.g., `"login:42::f"`)
- **Savings**: ~95% reduction (full details moved to detail modules)

**2. Dependencies (29.5% of legacy size)**
- **Strategy**: Keep minimal imports list in core for navigation
- **Detail**: Full dependency analysis in detail modules
- **Trade-off**: Some duplication but enables quick dependency queries

**3. Call Graph (9.3% of legacy size)**
- **Keep in core**: Cross-module relationships essential for navigation
- **Move to detail**: Within-module call edges (local context)

**4. Documentation (1.7% of legacy size)**
- **Core**: Only critical docs (README*, ARCHITECTURE*, API*)
- **Detail**: All other markdown files in tier structure

**5. Tree Structure (0.9% of legacy size)**
- **No change**: Already highly optimized with compact ASCII format

#### Real-World Validation

**Baseline**: 670-file project, 95.7KB legacy index (33,474 tokens)

**After split**:
- Core: 15.9KB (5,563 tokens) - **83.4% reduction**
- Detail modules: 79.9KB (distributed across modules)

**Extrapolation to 10,000 files**:
- Estimated core size: ~237KB (670 files) → 23.7KB (10,000 files linear scaling)
- **Well under 100KB target** ✅

#### Monitoring

Core index includes `stats.core_size_kb` field to track size during generation and warn if approaching 100KB limit.

---

## Module Organization Strategy

### Directory-Based Grouping

**Principle**: Group files by top-level directory into logical modules

**Rules**:
1. Files under same top-level directory → same module
2. Flat files (no parent directory) → `root` module
3. Configurable depth for monorepos (default: 1)

**Example**:

```
Project structure:
├── src/
│   ├── auth/
│   │   ├── login.py
│   │   └── session.py
│   ├── database/
│   │   ├── connection.py
│   │   └── models.py
│   └── api/
│       └── routes.py
├── config.py
└── main.py

Module mapping:
- auth → PROJECT_INDEX.d/auth.json (src/auth/*.py)
- database → PROJECT_INDEX.d/database.json (src/database/*.py)
- api → PROJECT_INDEX.d/api.json (src/api/*.py)
- root → PROJECT_INDEX.d/root.json (config.py, main.py)
```

### Module Naming

- **Alphanumeric**: module_id uses directory name directly
- **Collision handling**: If multiple directories have same name at different depths, use path-based naming (e.g., `src-utils`, `lib-utils`)
- **Reserved**: "root" is reserved for flat files

### Module Size Targets

- **Optimal**: 20-50 files per module
- **Maximum**: 200 files per module (can be split further if needed)
- **Minimum**: 1 file per module (acceptable for large files)

---

## Backward Compatibility

### Format Detection

**Legacy format indicators**:
1. No `version` field OR `version` is `"1.0"`
2. No `PROJECT_INDEX.d/` directory present
3. Presence of `f` field with full signatures (not `f_signatures`)

**Split format indicators**:
1. `version` field equals `"2.0-split"`
2. `PROJECT_INDEX.d/` directory exists
3. `modules` field present in core index

### Detection Algorithm

```python
def detect_format_version(project_root: Path) -> str:
    """
    Detect index format version.

    Returns:
        "2.0-split": Split format with detail modules
        "1.0": Legacy single-file format
        "none": No index exists
    """
    index_path = project_root / "PROJECT_INDEX.json"
    detail_dir = project_root / "PROJECT_INDEX.d"

    if not index_path.exists():
        return "none"

    with open(index_path) as f:
        index = json.load(f)

    # Check version field
    version = index.get("version", "1.0")
    if version == "2.0-split":
        return "2.0-split"

    # Check for split architecture artifacts
    if detail_dir.exists() and detail_dir.is_dir():
        return "2.0-split"

    # Default to legacy
    return "1.0"
```

### Dual-Format Support

Tools consuming the index should support both formats:

```python
class IndexLoader:
    def load(self, project_root: Path) -> Index:
        version = detect_format_version(project_root)

        if version == "2.0-split":
            return self.load_split_format(project_root)
        elif version == "1.0":
            return self.load_legacy_format(project_root)
        else:
            raise FileNotFoundError("No project index found")

    def load_split_format(self, project_root: Path) -> SplitIndex:
        # Load core index
        core = json.load(open(project_root / "PROJECT_INDEX.json"))
        # Detail modules loaded on-demand
        return SplitIndex(core, project_root / "PROJECT_INDEX.d")

    def load_legacy_format(self, project_root: Path) -> LegacyIndex:
        # Load single-file index
        data = json.load(open(project_root / "PROJECT_INDEX.json"))
        return LegacyIndex(data)
```

---

## Migration Notes

### Converting Legacy → Split Format

**High-level process**:
1. Read legacy `PROJECT_INDEX.json`
2. Extract core fields (tree, stats, critical docs)
3. Generate lightweight signatures from full function data
4. Group files into modules by directory
5. Create detail modules with full implementation data
6. Write core index with module references
7. Write each detail module JSON file

**Example migration logic**:

```python
def migrate_to_split_format(legacy_index: dict, output_dir: Path):
    """Convert legacy single-file index to split format."""

    # Initialize core index structure
    core = {
        "version": "2.0-split",
        "at": legacy_index["at"],
        "root": legacy_index["root"],
        "tree": legacy_index["tree"],
        "stats": {
            **legacy_index["stats"],
            "total_modules": 0,
            "core_size_kb": 0
        },
        "modules": {},
        "f_signatures": {},
        "imports": {},
        "g": [],
        "d_critical": {}
    }

    # Group files by directory into modules
    modules = group_files_by_directory(legacy_index["f"])

    # Process each module
    for module_id, files in modules.items():
        # Create lightweight signatures for core
        for file_path, file_data in files.items():
            core["f_signatures"][file_path] = extract_lightweight_signatures(file_data)

        # Create detail module
        detail_module = create_detail_module(module_id, files, legacy_index)

        # Write detail module file
        detail_path = output_dir / "PROJECT_INDEX.d" / f"{module_id}.json"
        write_json(detail_path, detail_module)

        # Add module reference to core
        core["modules"][module_id] = {
            "path": f"PROJECT_INDEX.d/{module_id}.json",
            "files": list(files.keys()),
            "functions": count_functions(files),
            "classes": count_classes(files),
            "modified": get_latest_modification(files)
        }

    # Migrate imports (rename from deps)
    core["imports"] = legacy_index.get("deps", {})

    # Split call graph (cross-module in core, within-module in details)
    core["g"] = extract_cross_module_calls(legacy_index["g"], modules)

    # Split documentation (critical in core, rest in details)
    core["d_critical"] = extract_critical_docs(legacy_index.get("d", {}))

    # Write core index
    write_json(output_dir / "PROJECT_INDEX.json", core)
```

### Key Considerations

1. **Preserve timestamps**: Keep original `at` timestamp during migration
2. **Maintain call graph**: Ensure all edges preserved (split between core and detail)
3. **Document critical docs**: Programmatically identify README*, ARCHITECTURE*, API* files
4. **Module naming**: Handle edge cases (name collisions, special characters)
5. **Validation**: Verify no information loss by comparing function counts, file counts, etc.

---

## Appendix: Dense Format Optimization

Both core and detail modules use **dense format** for further space reduction:

### Short Key Names
- `f` instead of `files`
- `g` instead of `call_graph`
- `d` instead of `documentation`

### Compact Signatures
- Use colon separators: `"name:line:parent:type"`
- Single-character type codes: `f` (function), `c` (class), `m` (method)

### Example Comparison

**Verbose format** (not used):
```json
{
  "file": "src/auth/login.py",
  "functions": [
    {
      "name": "login",
      "line_number": 42,
      "parent_class": null,
      "type": "function"
    }
  ]
}
```

**Dense format** (used):
```json
{
  "f_signatures": {
    "src/auth/login.py": ["login:42::f"]
  }
}
```

**Space savings**: ~70% for signature data

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0-split | 2025-10-31 | Initial split architecture schema design |
| 1.0 | 2025-10-29 | Legacy single-file format (implicit version) |

---

## Related Documentation

- [Epic 1 Technical Specification](tech-spec-epic-1.md) - Implementation details
- [Architecture Documentation](architecture.md) - System architecture
- [PRD Functional Requirements](PRD.md#functional-requirements) - Product requirements (FR004, FR005)
- [PRD Non-Functional Requirements](PRD.md#non-functional-requirements) - Size constraints (NFR002)
