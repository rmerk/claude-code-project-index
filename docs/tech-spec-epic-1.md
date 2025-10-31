# Epic Technical Specification: Split Index Architecture

Date: 2025-10-31
Author: Ryan
Epic ID: 1
Status: Draft

---

## Overview

This epic establishes the foundational split index architecture that enables claude-code-project-index to scale from small projects to enterprise codebases with 10,000+ files. Currently, the tool generates a single monolithic PROJECT_INDEX.json file that becomes too large for AI context windows when indexing large or documentation-heavy projects. This epic solves the "you can't filter what you can't load" constraint by separating the index into a lightweight core (PROJECT_INDEX.json) containing essential metadata and navigation structure, plus detailed modules (PROJECT_INDEX.d/) that can be lazy-loaded on demand based on query relevance.

The epic delivers universal scalability benefits regardless of project size or documentation ratio, maintains backward compatibility with existing single-file indices, and provides the infrastructure foundation upon which Epic 2's intelligence features will build.

## Objectives and Scope

**In Scope:**
- Design and document split index schema (core + detail formats)
- Implement core index generation (PROJECT_INDEX.json ≤ 100KB for 10,000 files)
- Implement detail module generation (PROJECT_INDEX.d/ directory structure)
- Create lazy-loading interface for agents to request detail modules
- Update index-analyzer agent to consume split architecture intelligently
- Implement backward compatibility detection and support for legacy single-file format
- Provide migration utility to convert existing indices to split format
- Add configuration options and comprehensive documentation

**Out of Scope:**
- Tiered documentation storage (Epic 2)
- Git metadata extraction (Epic 2)
- MCP tool integration (Epic 2)
- Advanced relevance scoring beyond basic keyword matching (Epic 2)
- Incremental index updates (Epic 2)
- Impact analysis tooling (Epic 2)
- Query-responsive index generation (future)

## System Architecture Alignment

This epic extends the existing **Hook-Based Event-Driven CLI Tool** architecture without changing its fundamental integration model. The split architecture modifies the **Index Generation Pipeline** (scripts/project_index.py) and **Index Analyzer Subagent** (agents/index-analyzer.md) components while preserving the hook layer integration (i_flag_hook.py, stop_hook.py).

**Architectural Changes:**
- **Indexer Core**: Modified to generate two artifacts (core index + detail modules directory) instead of single JSON
- **Data Architecture**: Split from single PROJECT_INDEX.json → Core (PROJECT_INDEX.json) + Details (PROJECT_INDEX.d/\*.json)
- **Analysis Layer**: Enhanced to detect format, load core first, then lazy-load details based on relevance
- **Hook Layer**: No changes required (continues to invoke index generation and subagent as before)

**Constraints Maintained:**
- Python 3.12+ stdlib only (no new dependencies)
- Git-based file discovery for performance
- Progressive compression for size management
- Graceful degradation and error handling
- Non-blocking hook execution

## Detailed Design

### Services and Modules

| Module | File | Responsibility | Inputs | Outputs |
|--------|------|----------------|--------|---------|
| **Schema Designer** | `scripts/schema.py` (new) | Define and validate core/detail schemas | Schema definitions | JSON schema docs, validation functions |
| **Core Index Generator** | `scripts/project_index.py` (modified) | Generate lightweight core index | File system, git metadata | `PROJECT_INDEX.json` (≤100KB) |
| **Detail Module Generator** | `scripts/detail_generator.py` (new) | Create per-module detail files | Parsed code structures | `PROJECT_INDEX.d/*.json` files |
| **Lazy Loading Service** | `scripts/loader.py` (new) | Load detail modules on demand | Module name or file path | Detail module JSON |
| **Index Analyzer Agent** | `agents/index-analyzer.md` (modified) | Intelligent split-aware analysis | Core index, user query | Relevance-scored detail requests |
| **Migration Utility** | `scripts/migrate.py` (new) | Convert legacy → split format | Existing PROJECT_INDEX.json | Split format (core + details) |
| **Configuration Manager** | `scripts/config.py` (new) | Manage split/single-file mode | User config, project size | Index generation strategy |

### Data Models and Contracts

**Core Index Schema (PROJECT_INDEX.json)**

```json
{
  "version": "2.0-split",
  "at": "2025-10-31T12:00:00Z",
  "root": ".",
  "tree": ["compact tree structure"],
  "stats": {
    "total_files": 3500,
    "total_modules": 25,
    "core_size_kb": 45
  },
  "modules": {
    "auth": {
      "path": "PROJECT_INDEX.d/auth.json",
      "files": ["src/auth/login.py", "src/auth/session.py"],
      "functions": 23,
      "modified": "2025-10-29T14:32:00Z"
    }
  },
  "f_signatures": {
    "src/auth/login.py": ["login:42", "validate:67"]
  },
  "imports": {
    "src/auth/login.py": ["session", "crypto"]
  },
  "g": [["login", "validate"]],
  "d_critical": {
    "README.md": ["Project Overview", "Installation"]
  }
}
```

**Detail Module Schema (PROJECT_INDEX.d/auth.json)**

```json
{
  "module_id": "auth",
  "version": "2.0-split",
  "files": {
    "src/auth/login.py": {
      "language": "python",
      "functions": [
        {
          "name": "login",
          "line": 42,
          "signature": "(user: str, pass: str) -> bool",
          "calls": ["validate", "create_session"],
          "doc": "Authenticate user and create session"
        }
      ],
      "classes": [],
      "imports": ["session", "crypto"]
    }
  },
  "call_graph_local": [["login", "validate"]],
  "doc_standard": {},
  "doc_archive": {}
}
```

**Module Reference Contract**

Modules are organized by directory structure:
- `PROJECT_INDEX.d/auth.json` - All files under src/auth/
- `PROJECT_INDEX.d/database.json` - All files under src/database/
- `PROJECT_INDEX.d/api.json` - All files under src/api/
- Flat files go into `PROJECT_INDEX.d/root.json`

**Backward Compatibility**

Legacy format detection:
```python
def is_legacy_format(index_path):
    # No PROJECT_INDEX.d/ directory = legacy
    return not (index_path.parent / "PROJECT_INDEX.d").exists()
```

### APIs and Interfaces

**Lazy-Loading API (scripts/loader.py)**

```python
def load_detail_module(module_name: str) -> dict:
    """
    Load detail module by name.

    Args:
        module_name: Module identifier (e.g., "auth", "database")

    Returns:
        Detail module JSON content

    Raises:
        FileNotFoundError: Module not found
    """
    path = f"PROJECT_INDEX.d/{module_name}.json"
    return json.load(open(path))

def load_detail_by_path(file_path: str, core_index: dict) -> dict:
    """
    Load detail module containing specific file.

    Args:
        file_path: File path (e.g., "src/auth/login.py")
        core_index: Core index with module mappings

    Returns:
        Detail module JSON content
    """
    module_name = find_module_for_file(file_path, core_index)
    return load_detail_module(module_name)

def load_multiple_modules(module_names: list[str]) -> dict:
    """Batch load multiple detail modules."""
    return {name: load_detail_module(name) for name in module_names}
```

**Migration API (scripts/migrate.py)**

```python
def migrate_to_split_format(legacy_path: str, backup: bool = True) -> tuple[str, str]:
    """
    Convert legacy single-file index to split format.

    Args:
        legacy_path: Path to PROJECT_INDEX.json (legacy format)
        backup: Create backup before migration

    Returns:
        (core_index_path, detail_dir_path)

    Side Effects:
        - Creates PROJECT_INDEX.d/ directory
        - Writes new core index
        - Optionally backs up legacy file
    """
    legacy_index = json.load(open(legacy_path))

    if backup:
        shutil.copy(legacy_path, f"{legacy_path}.backup")

    core_index = extract_core_metadata(legacy_index)
    detail_modules = split_into_modules(legacy_index)

    write_core_index(core_index, legacy_path)
    write_detail_modules(detail_modules, "PROJECT_INDEX.d")

    return (legacy_path, "PROJECT_INDEX.d")
```

**Index Generation API (scripts/project_index.py)**

```python
def generate_index(root_dir: str, mode: str = "auto") -> str:
    """
    Generate project index in split or single-file format.

    Args:
        root_dir: Project root directory
        mode: "split", "single", or "auto" (auto-detect based on size)

    Returns:
        Path to generated core index
    """
    if mode == "auto":
        file_count = count_indexable_files(root_dir)
        mode = "split" if file_count > 1000 else "single"

    if mode == "split":
        return generate_split_index(root_dir)
    else:
        return generate_single_file_index(root_dir)
```

**Agent Query Interface**

The index-analyzer agent accesses detail modules via:

```text
1. Load core index (always first)
2. Perform relevance scoring on core metadata
3. Request top-N modules: load_multiple_modules(["auth", "api", "database"])
4. Combine core structure + detail content in response
```

### Workflows and Sequencing

**Workflow 1: Split Index Generation**

```
1. User runs `/index` or hook triggers regeneration
2. project_index.py starts
3. Configuration determines mode (auto-detect: >1000 files → split)
4. File discovery (git ls-files or recursive walk)
5. Parse files (extract functions, classes, calls)
6. Build call graph
7. **Split logic:**
   a. Group files by directory (top-level or configurable depth)
   b. Create module metadata (file count, function count, modified date)
   c. Extract lightweight signatures for core index
   d. Generate full details for module files
8. Write core index (PROJECT_INDEX.json)
9. Write detail modules (PROJECT_INDEX.d/*.json)
10. Validate sizes (core ≤ 100KB, total ≤ original size)
11. Report completion with stats
```

**Workflow 2: Agent Lazy-Loading (Query Execution)**

```
1. User query with -i flag: "how does auth work? -i"
2. Hook invokes index-analyzer subagent
3. **Agent workflow:**
   a. Load core index (PROJECT_INDEX.json)
   b. Detect split architecture (check for modules section)
   c. Parse user query for keywords ("auth", "login", etc.)
   d. Relevance scoring on core index:
      - Keyword match in module names → high score
      - Keyword match in file paths → medium score
      - Keyword match in function names → low score
   e. Select top 3-5 relevant modules
   f. Load selected detail modules:
      load_multiple_modules(["auth", "session", "crypto"])
   g. Combine core structure + detail content
   h. Generate response with full context
4. Agent returns findings to main conversation
```

**Workflow 3: Migration from Legacy**

```
1. User runs `/index --migrate` or system detects legacy format
2. migrate.py starts
3. Load existing PROJECT_INDEX.json
4. Create backup (PROJECT_INDEX.json.backup)
5. **Extraction logic:**
   a. Split files by directory into modules
   b. Extract lightweight data for core:
      - Tree structure
      - Function/class signatures (names + lines only)
      - Imports
      - Call graph edges
      - Critical docs
   c. Extract full data for details:
      - Complete function signatures with params/returns
      - Full docstrings
      - Standard/archive documentation
      - Local call graphs per module
6. Write new core index (PROJECT_INDEX.json)
7. Create PROJECT_INDEX.d/ directory
8. Write detail modules (one per directory)
9. Validate integrity (all data preserved)
10. Report success with size comparison
```

**Workflow 4: Backward Compatibility Detection**

```
1. Agent or tool attempts to load index
2. Check for PROJECT_INDEX.d/ directory
3. **If not found (legacy format):**
   a. Load entire single-file index
   b. Log message: "Legacy format detected"
   c. Suggest migration for large projects
   d. Continue with full index in memory
4. **If found (split format):**
   a. Load core index only
   b. Enable lazy-loading mode
   c. Proceed with split architecture workflow
```

## Non-Functional Requirements

### Performance

**From PRD NFR001:**
- **Index Generation:** Must complete within 30 seconds for codebases up to 10,000 files
- **Lazy-Loading Latency:** Detail module load time must be under 500ms per module request
- **Core Index Size:** Must not exceed 100KB (~25,000 tokens) for codebases up to 10,000 files

**Additional Performance Targets:**
- **Module Organization:** Grouping files by directory must complete in O(n) time where n = file count
- **Relevance Scoring:** Keyword matching on core index must complete in <100ms
- **Migration Speed:** Legacy to split conversion must complete in <10 seconds for typical projects
- **Memory Usage:** Peak memory during index generation must not exceed 512MB for 10,000 file projects

**Performance Testing:**
- Test with 1,000, 5,000, and 10,000 file synthetic repositories
- Measure generation time, core size, and lazy-load latency
- Validate against NFR001 targets

### Security

**File Access Controls:**
- Respect .gitignore patterns (inherited from current architecture)
- Exclude sensitive directories (.git, node_modules, .env files)
- Read-only file access (no writes except to PROJECT_INDEX.json and PROJECT_INDEX.d/)

**No Code Execution:**
- Pure parsing, no eval() or exec() calls
- Regex-based extraction only
- No network access (all processing local)

**Data Privacy:**
- Index contains code structure only (no secrets, credentials, or sensitive data)
- Backup files (.backup) preserve original permissions
- No telemetry or external reporting

**Migration Safety:**
- Always create backup before migration
- Validate integrity after migration
- Rollback capability if validation fails

### Reliability/Availability

**Graceful Degradation (inherited from current architecture):**
- Parse errors on individual files → Skip file, continue indexing
- Missing detail module → Log warning, continue with partial data
- Legacy format detection failure → Default to attempting full load
- Module grouping errors → Fall back to single-file mode

**Backward Compatibility Guarantee:**
- Existing single-file indices continue to work without modification
- No breaking changes to PROJECT_INDEX.json structure for legacy mode
- Migration is optional, not required

**Data Integrity:**
- Migration preserves 100% of data from legacy format (zero information loss)
- Hash validation after split generation to ensure consistency
- Atomic writes (temp file + rename) to prevent corruption

**Recovery:**
- Backup files enable rollback from failed migrations
- Core index + detail modules can be regenerated from source at any time
- No persistent state dependencies (stateless indexing)

### Observability

**Logging Requirements:**
- **Info Level:** Mode selection (split vs single-file), file counts, module counts, generation time
- **Debug Level:** Module grouping decisions, relevance scores, detail module loads
- **Warning Level:** Legacy format detected, migration suggested, missing modules
- **Error Level:** Parse failures, file access errors, integrity validation failures

**Metrics to Track:**
- Core index size (KB and token estimate)
- Detail module count and average size
- Generation time breakdown (discovery, parsing, splitting, writing)
- Lazy-load request counts and latency per module
- Migration success/failure rate

**User Feedback:**
- Progress indicators during index generation (every 100 files)
- Summary output: "Generated split index: 45KB core + 25 modules (12MB total) in 8s"
- Verbose flag (`-v`) enables detailed logging for debugging
- Agent logs which modules were loaded when verbose mode enabled

## Dependencies and Integrations

**Python Standard Library Only (No External Dependencies)**

This epic maintains the project's core principle of zero external dependencies. All functionality uses Python 3.12+ standard library:

| Stdlib Module | Usage | Version Required |
|---------------|-------|------------------|
| `json` | Index serialization/deserialization | Python 3.12+ |
| `pathlib` | File path operations | Python 3.12+ |
| `shutil` | Backup file operations (migration) | Python 3.12+ |
| `os` | File system operations | Python 3.12+ |
| `re` | Regex parsing (inherited) | Python 3.12+ |
| `subprocess` | Git command execution (inherited) | Python 3.12+ |
| `hashlib` | Hash validation (inherited) | Python 3.12+ |

**System Dependencies:**
- **Python 3.12+** - Required runtime
- **Git** (optional) - For fast file discovery and metadata extraction (graceful fallback if unavailable)
- **Unix-like OS** - macOS/Linux (Bash scripts for installation)

**Claude Code Integration:**
- **Hook System** - UserPromptSubmit and Stop hooks (no changes to integration)
- **Slash Commands** - `/index` command (enhanced with `--migrate` flag)
- **Subagent System** - index-analyzer.md (modified to support split architecture)

**File System Contract:**
- **Read Access:** Project files for indexing
- **Write Access:**
  - `PROJECT_INDEX.json` (core index)
  - `PROJECT_INDEX.d/` directory and contents (detail modules)
  - `PROJECT_INDEX.json.backup` (migration backups)

**No External Services:**
- No network calls
- No cloud dependencies
- No telemetry or analytics
- Pure local filesystem operations

## Acceptance Criteria (Authoritative)

**AC1.1:** Core index schema documented (file tree, function signatures, imports, git metadata structure)
**AC1.2:** Detail module schema documented (per-module detailed function/class info)
**AC1.3:** Schema includes version field for future compatibility
**AC1.4:** JSON examples provided for both core and detail formats
**AC1.5:** Schema supports all existing index features (functions, classes, call graph, docs)

**AC2.1:** `PROJECT_INDEX.json` generated with file tree, function/class names (no bodies), imports
**AC2.2:** Core index includes git metadata (last commit, author, date) per file
**AC2.3:** Core index size stays under 100KB for test project (current ~3,500 files)
**AC2.4:** Core index includes references to detail module locations
**AC2.5:** Existing single-file generation still works (backward compat maintained)

**AC3.1:** `PROJECT_INDEX.d/` directory created with per-module detail files
**AC3.2:** Detail modules include full function/class signatures, call graphs, documentation
**AC3.3:** Detail modules organized by directory structure (e.g., `auth.json`, `database.json`)
**AC3.4:** Detail module references match core index module IDs
**AC3.5:** Total detail module size + core index ≤ original single-file index size

**AC4.1:** Agent can request detail module by module name (e.g., "auth", "database")
**AC4.2:** Agent can request detail module by file path (e.g., "src/auth/login.py")
**AC4.3:** Interface returns module content or clear error if not found
**AC4.4:** Interface supports batch requests (load multiple modules in one call)
**AC4.5:** Documentation explains how agents should use the interface

**AC5.1:** Agent loads core index first and detects split architecture presence
**AC5.2:** Agent performs relevance scoring on core index to identify relevant modules
**AC5.3:** Agent lazy-loads top 3-5 relevant detail modules based on query
**AC5.4:** Agent provides response combining core index structure + detail module content
**AC5.5:** Agent logs which modules were loaded (when verbose flag used)

**AC6.1:** System detects legacy single-file format (no PROJECT_INDEX.d/ directory)
**AC6.2:** Agent loads full single-file index when split architecture not detected
**AC6.3:** All existing functionality works with legacy format (no regressions)
**AC6.4:** Clear message informs user that legacy format is in use
**AC6.5:** System suggests migration to split format for large projects

**AC7.1:** Command `/index --migrate` converts single-file → split format
**AC7.2:** Migration preserves all existing index data (no information loss)
**AC7.3:** Migration creates backup of original single-file index
**AC7.4:** Migration validates split index after creation (integrity check)
**AC7.5:** Clear success/failure messages with rollback option if migration fails

**AC8.1:** Configuration option to force single-file mode (for small projects)
**AC8.2:** Configuration option to force split mode (for large projects)
**AC8.3:** Auto-detection threshold configurable (default: >1000 files → split mode)
**AC8.4:** README updated with split architecture explanation and benefits
**AC8.5:** Migration guide and troubleshooting documentation added

## Traceability Mapping

| AC | Spec Section | Component(s) | Test Idea |
|----|--------------|--------------|-----------|
| AC1.1-1.5 | Data Models (Schema) | schema.py | Validate schema docs exist, include all fields, have examples |
| AC2.1-2.5 | Data Models (Core Index), APIs (Generation) | project_index.py | Generate core for test project, measure size, verify structure |
| AC3.1-3.5 | Data Models (Detail Modules), APIs (Generation) | detail_generator.py | Generate details, verify directory created, validate references |
| AC4.1-4.5 | APIs (Lazy-Loading) | loader.py | Unit test load_detail_module, load_by_path, batch loading |
| AC5.1-5.5 | APIs (Agent Query), Workflows (Lazy-Loading) | index-analyzer.md | Integration test with sample queries, verify module selection |
| AC6.1-6.5 | Workflows (Backward Compat), APIs (Generation) | project_index.py, index-analyzer.md | Test with legacy index, verify full functionality, check messages |
| AC7.1-7.5 | APIs (Migration), Workflows (Migration) | migrate.py | Test migration on real index, verify data preservation, rollback |
| AC8.1-8.5 | APIs (Configuration), Data Models (Config) | config.py, README.md | Test mode selection, verify docs updated, check thresholds |

**Traceability to PRD Requirements:**

| PRD Requirement | Related ACs | Implementation |
|-----------------|-------------|----------------|
| FR004: Generate lightweight core index | AC2.1-2.5 | project_index.py - core generation logic |
| FR005: Generate detailed module indices | AC3.1-3.5 | detail_generator.py - module splitting |
| FR006: Support lazy-loading | AC4.1-4.5, AC5.1-5.5 | loader.py + index-analyzer.md |
| FR007: Relevance scoring | AC5.2 | index-analyzer.md - keyword matching |
| FR010: Legacy format support | AC6.1-6.5 | Backward compat detection |
| FR011: Migration path | AC7.1-7.5 | migrate.py |
| FR013: Query interface | AC4.1-4.5 | loader.py API |
| NFR001: Performance targets | AC2.3, AC4.3 | Size/latency validation |
| NFR002: Scalability (100KB core) | AC2.3 | Core index compression |
| NFR003: Maintainability (JSON, docs) | AC1.1-1.5, AC8.4-8.5 | Schema docs, README updates |

## Risks, Assumptions, Open Questions

**Risks:**

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| R1 | Core index exceeds 100KB for 10,000 file projects | Medium | High | Implement aggressive compression, test early with synthetic repos, adjust module granularity |
| R2 | Module grouping heuristic creates too many small modules | Medium | Medium | Make grouping strategy configurable, allow depth adjustment |
| R3 | Lazy-loading latency exceeds 500ms | Low | Medium | Profile I/O operations, use caching, optimize JSON parsing |
| R4 | Migration fails to preserve data integrity | Low | Critical | Extensive validation, backup required, rollback mechanism |
| R5 | Backward compatibility breaks existing workflows | Low | Critical | Comprehensive regression testing with legacy indices |
| R6 | Agent relevance scoring misses obvious modules | Medium | Medium | Implement multiple scoring strategies, allow user override |
| R7 | Windows path compatibility issues (PROJECT_INDEX.d/) | Medium | Medium | Test on Windows (future), document Unix-only constraint |

**Assumptions:**

- A1: Directory-based module organization is intuitive and effective for most projects
- A2: Top-level directories adequately represent architectural modules in typical codebases
- A3: Keyword-based relevance scoring is sufficient for MVP (Epic 2 will enhance)
- A4: 1,000 file threshold is appropriate for split vs single-file decision
- A5: Users will accept automatic migration suggestions for large projects
- A6: Detail module loading latency is dominated by disk I/O, not JSON parsing
- A7: Python 3.12+ availability is acceptable constraint for target users

**Open Questions:**

- Q1: Should module organization be configurable (e.g., group by depth 2 instead of depth 1)?
- Q2: How to handle monorepos with multiple distinct projects in subdirectories?
- Q3: Should we cache loaded detail modules in memory during agent session?
- Q4: What's the right default for "top N modules" to lazy-load (current: 3-5)?
- Q5: Should migration be automatic on first use of split-capable version, or manual only?
- Q6: How to handle projects with flat file structure (no meaningful directories)?
- Q7: Should detail modules support multiple formats (JSON, MessagePack, etc.) for size optimization?

## Test Strategy Summary

**Test Levels:**

**Unit Tests:**
- `schema.py`: Schema validation functions
- `loader.py`: load_detail_module(), load_by_path(), batch loading
- `migrate.py`: Data extraction, module splitting, validation logic
- `config.py`: Mode selection, threshold detection

**Integration Tests:**
- End-to-end split index generation on test repository
- Agent lazy-loading workflow with real queries
- Migration from real legacy index to split format
- Backward compatibility with existing indices

**Performance Tests:**
- Synthetic repositories: 1,000, 5,000, 10,000 files
- Measure: generation time, core size, lazy-load latency
- Validate against NFR001 targets (<30s generation, <500ms load, <100KB core)

**Regression Tests:**
- Verify all existing functionality works with legacy format
- Compare single-file vs split output for consistency
- Test all existing index features preserved

**Test Frameworks:**
- Python `unittest` or `pytest` (stdlib preferred)
- Manual testing for agent interaction
- Bash scripts for install/integration testing

**Coverage Targets:**
- Unit tests: 80%+ code coverage
- Integration tests: All workflows (4 workflows documented)
- Performance tests: All NFR targets validated
- Edge cases: Empty projects, single file, flat structure, deep nesting

**Test Data:**
- Current project (claude-code-project-index) as real-world brownfield test
- Synthetic repos with controlled file counts and structures
- Legacy PROJECT_INDEX.json samples from existing deployments

**Acceptance Testing:**
- Validate all 40 ACs (AC1.1 through AC8.5)
- User acceptance: Test with beta users on real projects
- Migration testing: Validate on existing user indices
