# Story 1.5: Update Index-Analyzer Agent

Status: done

## Story

As a developer using `-i` flag,
I want the index-analyzer agent to intelligently use split architecture,
So that I get relevant code context without manual module selection.

## Acceptance Criteria

1. Agent loads core index first and detects split architecture presence
2. Agent performs relevance scoring on core index to identify relevant modules
3. Agent lazy-loads top 3-5 relevant detail modules based on query
4. Agent provides response combining core index structure + detail module content
5. Agent logs which modules were loaded (when verbose flag used)

## Tasks / Subtasks

- [x] Update Index-Analyzer Agent Prompt (AC: #1, #2, #3, #4, #5)
  - [x] Load `agents/index-analyzer.md` and analyze current structure
  - [x] Add split architecture detection logic
  - [x] Implement relevance scoring algorithm (keyword matching)
  - [x] Add lazy-loading module selection (top 3-5)
  - [x] Add module loading logging for verbose mode
  - [x] Update agent instructions to combine core + detail content

- [x] Implement Split Architecture Detection (AC: #1)
  - [x] Check for `version` field = "2.0-split" in PROJECT_INDEX.json
  - [x] Check for `modules` section in core index
  - [x] Check for PROJECT_INDEX.d/ directory existence
  - [x] If not split format, fall back to legacy full-index loading
  - [x] Log detection result (split vs legacy)

- [x] Implement Relevance Scoring (AC: #2)
  - [x] Extract keywords from user query (noun phrases, technical terms)
  - [x] Score each module based on:
    * Module name matches keyword (weight: 10x)
    * File path contains keyword (weight: 5x)
    * Function name matches keyword (weight: 2x)
  - [x] Sort modules by relevance score (highest first)
  - [x] Handle edge case: no keyword matches (load all modules or most recent)

- [x] Implement Lazy-Loading Module Selection (AC: #3)
  - [x] Select top 3-5 modules from relevance scoring
  - [x] Use `load_multiple_modules()` from Story 1.4
  - [x] Handle partial failures gracefully (use what loads successfully)
  - [x] Configuration option for N (default: 5)
  - [x] Special case: if query mentions specific file, load that module first

- [x] Combine Core + Detail Response (AC: #4)
  - [x] Load core index structure (tree, stats, signatures)
  - [x] Load selected detail modules (full function info, call graphs)
  - [x] Merge data for response:
    * Overview from core index (tree, stats)
    * Deep analysis from detail modules (function bodies, local call graphs)
  - [x] Format response with clear sections:
    * Project Overview (from core)
    * Relevant Code Paths (from detail modules)
    * Architectural Insights (from call graph + structure)

- [x] Add Verbose Logging (AC: #5)
  - [x] Log modules loaded: "Loaded detail modules: auth, database, api"
  - [x] Log relevance scores (verbose mode only)
  - [x] Log why modules were selected (query keywords matched)
  - [x] Log fallback behavior if used (legacy format, partial failures)

- [x] Update Agent Documentation
  - [x] Add split architecture usage section to agent prompt
  - [x] Document relevance scoring algorithm
  - [x] Add examples of queries and expected module loading
  - [x] Document fallback behavior for legacy format
  - [x] Add troubleshooting section for verbose logging

- [x] Testing and Validation (All ACs)
  - [x] Test with split format index (PROJECT_INDEX.d/ present)
  - [x] Test with legacy format index (backward compatibility)
  - [x] Test relevance scoring with various queries:
    * Specific module name ("how does auth work?")
    * File path reference ("analyze src/auth/login.py")
    * General concept ("show me database code")
  - [x] Test top-N module selection (verify 3-5 modules loaded)
  - [x] Test verbose logging output
  - [x] Test response format (core + detail merge)
  - [x] Test edge cases (no matches, all modules match, partial load failures)

## Dev Notes

### Architecture Alignment

**From Tech-Spec (tech-spec-epic-1.md):**

This story implements the agent query interface and lazy-loading workflow specified in the tech spec (lines 246-298). The index-analyzer agent is modified from a single-index consumer to a split-aware intelligent loader.

**Current Agent Behavior (Legacy):**
- Load full PROJECT_INDEX.json into context
- Analyze entire index for query
- No lazy-loading (everything upfront)

**New Agent Behavior (Split Architecture):**
- Load core index first (small, always fits)
- Detect split vs legacy format
- Perform relevance scoring on core metadata
- Lazy-load top 3-5 relevant detail modules only
- Combine core structure + detail content in response

**Relevance Scoring Algorithm (from Tech-Spec lines 287-295):**

```
Query: "how does auth work?"
Keywords: ["auth", "authentication", "login"]

Scoring:
- Module "auth" → 10x (module name match)
- File "src/auth/login.py" → 5x (path match)
- Function "authenticate_user" → 2x (function name match)

Top 5 modules loaded:
1. auth (score: 50)
2. session (score: 15)
3. database (score: 10)
4. api (score: 5)
5. crypto (score: 3)

Result: load_multiple_modules(["auth", "session", "database", "api", "crypto"])
```

**Integration Points:**
- **Story 1.4 API**: Use `load_detail_module()`, `load_detail_by_path()`, `load_multiple_modules()`
- **Story 1.2 Core Index**: Read `modules` section for module metadata
- **Story 1.3 Detail Modules**: Load from PROJECT_INDEX.d/ directory
- **Story 1.6 Backward Compat**: Detect legacy format and fall back to full index load

**Performance Requirements (NFR001 from PRD):**
- Lazy-load latency must be under 500ms per module request (already satisfied by Story 1.4)
- Agent response time should not exceed current baseline (2-5 seconds typical)
- Relevance scoring must complete in <100ms (from tech-spec)

### Project Structure Notes

**Files to Modify:**
- `agents/index-analyzer.md` - Main agent prompt (existing file)

**Agent Structure:**
```markdown
# Index-Analyzer Agent

## PRIMARY DIRECTIVE
[Current ultrathinking directive - unchanged]

## SPLIT ARCHITECTURE DETECTION
1. Load PROJECT_INDEX.json
2. Check version field for "2.0-split"
3. Check for modules section
4. If split: proceed to lazy-loading workflow
5. If legacy: load full index and proceed with current behavior

## RELEVANCE SCORING
Query Analysis:
- Extract keywords from user query
- Score modules based on matches (module name, file paths, function names)
- Sort by relevance score

## LAZY-LOADING WORKFLOW
1. Select top 3-5 modules from scoring
2. Load detail modules: load_multiple_modules(module_list)
3. Handle partial failures (use successful loads)
4. Log loaded modules (verbose mode)

## RESPONSE FORMAT
[Current format enhanced with:]
- 🏗️ PROJECT OVERVIEW (from core index)
- 🧠 CODE INTELLIGENCE ANALYSIS (from detail modules)
- 🔗 ARCHITECTURAL INSIGHTS (from call graph)

## ULTRATHINKING FRAMEWORK
[Current ultrathinking - enhanced with module selection rationale]
```

**No New Files Created**: This is a modification-only story.

### Learnings from Previous Story

**From Story 1-4-lazy-loading-interface (Status: done)**

- **Lazy-Loading API Available**: All required functions implemented and tested:
  - `load_detail_module(module_name: str) -> dict` - Load by module name
  - `find_module_for_file(file_path: str, core_index: dict) -> str` - Helper to map file → module
  - `load_detail_by_path(file_path: str, core_index: dict) -> dict` - Load by file path
  - `load_multiple_modules(module_names: list[str]) -> dict` - Batch loading with graceful degradation

- **API Location**: `scripts/loader.py` (300 lines, comprehensive docstrings)

- **Error Handling Strategy**: All API functions handle errors gracefully:
  - FileNotFoundError: Module not found (clear message with expected path)
  - JSONDecodeError: Invalid JSON (re-raised with context)
  - ValueError: File not found in index, invalid module name
  - Warnings for partial batch failures (doesn't break operation)

- **Performance Validated**: <5ms per module load (100x better than 500ms requirement)

- **Backward Compatibility Handling**: Already detects legacy format (v1.0):
  - Checks for both "modules" (v2.0) and "f" (v1.0) keys
  - Provides helpful error messages directing to regeneration
  - This aligns with Story 1.6 requirements (not yet implemented)

- **Module Organization Pattern** (from Story 1.3):
  - Directory-based: `scripts/` → `PROJECT_INDEX.d/scripts.json`
  - Flat files → `PROJECT_INDEX.d/root.json`
  - Module IDs match core index `modules` section

- **Detail Module Structure**:
  ```json
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
    "call_graph_local": [["func1", "func2"]],
    "doc_standard": {},
    "doc_archive": {}
  }
  ```

- **Usage Pattern** (from Documentation):
  ```python
  # 1. Load core index
  core_index = json.load(open("PROJECT_INDEX.json"))

  # 2. Perform relevance scoring (implemented in this story)
  relevant_modules = ["scripts", "agents"]  # Based on query

  # 3. Batch load top modules
  modules = load_multiple_modules(relevant_modules)

  # 4. Use loaded details in response
  for module_name, module_data in modules.items():
      # Access module_data["files"][file_path]["functions"]
  ```

**New Patterns to REUSE:**
- Import loader.py functions: `from scripts.loader import load_multiple_modules, load_detail_by_path`
- Use batch loading for efficiency (single call for multiple modules)
- Handle partial failures gracefully (warnings, not errors)
- Check module_data structure before accessing (validate required fields exist)

**Technical Approach Lessons:**
- **Always load core index first** - Small, always fits in context
- **Batch load detail modules** - More efficient than sequential loads
- **Handle missing modules gracefully** - Some modules might not exist or fail to load
- **Log module selection rationale** - Helps debugging and user understanding
- **Version detection** - Check `version` field for "2.0-split" to detect split format

**Integration Notes:**
- Core index from Story 1.2 has `modules` dict with file mappings and metadata
- Use `modules[module_id]["files"]` list to understand module contents
- Detail modules are already created by Story 1.3 in PROJECT_INDEX.d/
- This story consumes the API from Story 1.4 (no modifications to loader.py needed)

[Source: stories/1-4-lazy-loading-interface.md#Dev-Agent-Record]

### References

- [Tech-Spec: Agent Query Interface](docs/tech-spec-epic-1.md#agent-query-interface) - Lines 246-256
- [Tech-Spec: Workflow 2 (Agent Lazy-Loading)](docs/tech-spec-epic-1.md#workflow-2-agent-lazy-loading-query-execution) - Lines 279-298
- [Tech-Spec: Lazy-Loading API](docs/tech-spec-epic-1.md#apis-and-interfaces) - Lines 154-187
- [PRD: FR007](docs/PRD.md#functional-requirements) - Relevance scoring requirement
- [PRD: FR006](docs/PRD.md#functional-requirements) - Lazy-loading support (infrastructure from Story 1.4)
- [PRD: NFR001](docs/PRD.md#non-functional-requirements) - Performance targets (<500ms lazy-load)
- [Epics: Story 1.5](docs/epics.md#story-15-update-index-analyzer-agent) - Lines 112-126
- [Architecture: Analysis Layer](docs/architecture.md#4-analysis-layer-intelligence) - Lines 125-137
- [Loader API Documentation](docs/lazy-loading-interface.md) - Complete API reference from Story 1.4

## Dev Agent Record

### Context Reference

- [Story Context XML](1-5-update-index-analyzer-agent.context.xml)

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log

**Implementation Plan:**
1. Enhanced PRIMARY DIRECTIVE section to detect split architecture (check version field)
2. Added new SPLIT ARCHITECTURE DETECTION section with decision logic
3. Added new RELEVANCE SCORING ALGORITHM section with keyword extraction and scoring
4. Added new LAZY-LOADING WORKFLOW section with module selection logic
5. Enhanced OUTPUT FORMAT to support core + detail response structure
6. Added VERBOSE LOGGING section for module loading transparency
7. Maintained all existing ultrathinking framework and analysis capabilities
8. Ensured backward compatibility with legacy format (v1.0)

**Key Technical Approach:**
- Check PROJECT_INDEX.json for "version": "2.0-split" to detect split format
- For split format: load core, score modules, lazy-load top 5
- For legacy format: fall back to current behavior (load full index)
- Use load_multiple_modules() from scripts/loader.py
- Weight scoring: module name (10x), file path (5x), function name (2x)
- Default to top 5 modules, handle partial failures gracefully

### Completion Notes List

✅ **Agent Prompt Updated Successfully** (agents/index-analyzer.md)
- Added split architecture detection logic (3 checks: version field, modules section, PROJECT_INDEX.d/ directory)
- Implemented relevance scoring algorithm with 10x/5x/2x weighting for module/file/function matches
- Documented lazy-loading workflow using load_multiple_modules() from Story 1.4
- Enhanced output format with separate templates for split (v2.0) vs legacy (v1.0) formats
- Added comprehensive verbose logging section with examples for module selection, fallback, and performance
- Updated SPECIAL CONSIDERATIONS with 12 guidelines including split architecture best practices
- Enhanced ULTRATHINKING REQUIREMENT with split architecture strategic thinking

✅ **All Acceptance Criteria Validated**
- AC#1: Split architecture detection implemented and tested (version check, modules check, directory check)
- AC#2: Relevance scoring algorithm implemented with keyword extraction and weighted scoring
- AC#3: Lazy-loading workflow uses load_multiple_modules() for top 5 modules by default
- AC#4: Response format combines core index (tree, stats) + detail modules (function bodies, call graphs)
- AC#5: Verbose logging shows loaded modules, relevance scores, selection rationale, and performance metrics

✅ **Testing Complete**
- Created test_index_analyzer_agent.py with 5 test cases covering all ACs
- All tests passed (5/5) for split architecture format
- Verified backward compatibility with legacy format (v1.0)
- Tested with both formats successfully

**Performance Metrics:**
- Agent prompt size: ~380 lines (vs 130 original) - comprehensive documentation
- Split architecture detection: 3 checks (version, modules, directory)
- Default module loading: top 5 (configurable N, max 10)
- Graceful degradation: handles partial failures, fallback to core-only analysis

**Integration Notes:**
- Uses loader API from Story 1.4 (load_multiple_modules, load_detail_by_path, load_detail_module)
- Compatible with core index from Story 1.2 (modules section, version field)
- Works with detail modules from Story 1.3 (PROJECT_INDEX.d/*.json)
- Maintains backward compatibility with legacy format (no breaking changes)

### File List

**Modified:**
- agents/index-analyzer.md - Enhanced with split architecture support (lines 1-382)

**Created:**
- scripts/test_index_analyzer_agent.py - Acceptance criteria validation tests (324 lines)
