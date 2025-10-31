# Epic Technical Specification: Enhanced Intelligence & Developer Tools

Date: 2025-10-31
Author: Ryan
Epic ID: 2
Status: Draft

---

## Overview

This epic builds on Epic 1's split index architecture to add intelligent features that dramatically improve index relevance, compression, and developer productivity. While Epic 1 solved the fundamental scalability challenge through core/detail separation, Epic 2 addresses three critical optimization opportunities identified in the PRD brainstorming: tiered documentation storage (60-80% compression for doc-heavy projects), git temporal awareness (prioritizing recent changes), and MCP tool integration (hybrid static/live data access).

The epic delivers smart compression that benefits documentation-heavy codebases immediately, temporal intelligence that focuses agents on active development areas, hybrid query strategies that combine pre-computed index structure with real-time MCP data sources, and developer productivity tools including impact analysis and incremental updates. These enhancements transform the tool from a scalable indexer into an intelligent code navigation system optimized for AI-assisted development workflows.

## Objectives and Scope

**In Scope:**
- Implement tiered documentation classification (critical/standard/archive tiers)
- Store tiered documentation in separate index sections with configurable loading
- Extract git metadata (commit hash, author, date, PR number, lines changed) per file
- Integrate temporal awareness into agent relevance scoring (recent changes weighted higher)
- Detect available MCP tools (Read, Grep, Git) at runtime
- Implement hybrid query strategies combining index structure with live MCP data
- Build unified relevance scoring engine (explicit references, temporal context, semantic keywords)
- Create impact analysis tooling leveraging call graph for downstream dependency analysis
- Implement incremental index updates (regenerate only changed files + dependencies)

**Out of Scope:**
- Query-responsive index generation (moonshot - future R&D)
- Hierarchical zoom levels (L0/L1/L2 architecture - needs new agent protocol)
- Risk scoring system (automated risk calculation - deferred)
- Project-type aware indexing (monorepo/microservices detection - deferred)
- Real-time daemon mode (file-watch incremental updates - deferred)
- Language-specific deep analysis (AST-level semantic understanding - beyond regex parsing)
- Multi-repository indexing (each repo independent - no cross-repo index)

## System Architecture Alignment

This epic enhances the **Index Generation Pipeline** and **Analysis Layer** established in Epic 1, while adding new intelligence capabilities that leverage both static index data and dynamic MCP integrations.

**Architectural Enhancements:**
- **Indexer Core**: Extended with git metadata extraction, tiered doc classification, and incremental update logic
- **Data Architecture**: Core index enhanced with git metadata fields; detail modules gain tiered doc sections
- **Analysis Layer**: Agent intelligence upgraded with MCP detection, hybrid query routing, and multi-signal relevance scoring
- **Parser Layer**: No changes (continues regex-based signature extraction)

**New Integration Points:**
- **MCP Tool Detection**: Runtime capability discovery for Read, Grep, Git tools
- **Git Metadata Pipeline**: Extract commit history, author, date, PR numbers via git log/blame
- **Incremental Update Engine**: Git diff-based change detection for selective regeneration

**Constraints Maintained:**
- Python 3.12+ stdlib only (no new external dependencies)
- Graceful degradation when git or MCP tools unavailable
- Backward compatibility with Epic 1's split architecture
- Non-blocking hook execution

## Detailed Design

### Services and Modules

| Module | File | Responsibility | Inputs | Outputs |
|--------|------|----------------|--------|---------|
| **Doc Classifier** | `scripts/doc_classifier.py` (new) | Classify docs into critical/standard/archive tiers | Markdown files, config rules | Tier assignments per file |
| **Doc Storage Manager** | `scripts/project_index.py` (modified) | Store docs in tiered sections | Classified docs | d_critical, d_standard, d_archive sections |
| **Git Metadata Extractor** | `scripts/git_metadata.py` (new) | Extract commit, author, date, PR info | File paths | Git metadata per file |
| **Temporal Scorer** | `scripts/relevance.py` (new) | Weight recent changes in scoring | Git metadata, query | Temporal relevance scores |
| **MCP Detector** | `scripts/mcp_detector.py` (new) | Detect available MCP tools | Runtime environment | MCP capability map |
| **Hybrid Query Router** | `agents/index-analyzer.md` (modified) | Route queries to index or MCP | Query type, MCP availability | Query execution strategy |
| **Relevance Engine** | `scripts/relevance.py` (new) | Unified multi-signal scoring | Explicit refs, temporal data, keywords | Top-N ranked modules |
| **Impact Analyzer** | `scripts/impact.py` (new) | Analyze downstream dependencies | Function name, call graph | List of callers (direct + indirect) |
| **Incremental Updater** | `scripts/incremental.py` (new) | Selective index regeneration | Git diff, existing index | Updated core + affected detail modules |

### Data Models and Contracts

**Enhanced Core Index Schema (with Epic 2 additions)**

```json
{
  "version": "2.1-enhanced",
  "at": "2025-10-31T12:00:00Z",
  "root": ".",
  "tree": ["..."],
  "stats": {
    "total_files": 3500,
    "total_modules": 25,
    "core_size_kb": 45,
    "doc_compression_ratio": 0.72
  },
  "modules": {
    "auth": {
      "path": "PROJECT_INDEX.d/auth.json",
      "files": ["src/auth/login.py", "src/auth/session.py"],
      "functions": 23,
      "modified": "2025-10-29T14:32:00Z",
      "git_recent": true
    }
  },
  "f_signatures": {"src/auth/login.py": ["login:42", "validate:67"]},
  "imports": {"src/auth/login.py": ["session", "crypto"]},
  "g": [["login", "validate"]],
  "git_metadata": {
    "src/auth/login.py": {
      "commit": "a3f2b1c",
      "author": "developer@example.com",
      "date": "2025-10-29T14:32:00Z",
      "message": "Fix session timeout bug (#247)",
      "pr": "247",
      "lines_changed": 23,
      "recency_days": 2
    }
  },
  "d_critical": {
    "README.md": ["Project Overview", "Installation"],
    "ARCHITECTURE.md": ["System Architecture", "Component Design"]
  }
}
```

**Enhanced Detail Module Schema (with tiered docs)**

```json
{
  "module_id": "auth",
  "version": "2.1-enhanced",
  "files": {
    "src/auth/login.py": {
      "language": "python",
      "functions": [{
        "name": "login",
        "line": 42,
        "signature": "(user: str, pass: str) -> bool",
        "calls": ["validate", "create_session"],
        "doc": "Authenticate user and create session"
      }],
      "git_metadata": {
        "commit": "a3f2b1c",
        "author": "developer@example.com",
        "date": "2025-10-29T14:32:00Z",
        "recency_days": 2
      }
    }
  },
  "call_graph_local": [["login", "validate"]],
  "d_standard": {
    "docs/auth-guide.md": ["Authentication Flow", "Session Management"]
  },
  "d_archive": {
    "docs/auth-changelog.md": ["Version History", "Migration Notes"]
  }
}
```

**Tiered Documentation Classification Rules**

```python
TIER_RULES = {
    "critical": [
        "README*", "ARCHITECTURE*", "API*", "CONTRIBUTING*",
        "SECURITY*", "docs/architecture/*", "docs/api/*"
    ],
    "standard": [
        "docs/development/*", "docs/setup/*", "docs/guides/*",
        "INSTALL*", "SETUP*", "docs/how-to/*"
    ],
    "archive": [
        "docs/tutorials/*", "CHANGELOG*", "docs/meetings/*",
        "docs/archive/*", "docs/legacy/*", "HISTORY*"
    ]
}
```

### APIs and Interfaces

**Documentation Classification API**

```python
def classify_documentation(file_path: Path, config: dict) -> str:
    """
    Classify markdown file into tier (critical/standard/archive).

    Args:
        file_path: Path to markdown file
        config: Classification rules (TIER_RULES)

    Returns:
        Tier name: "critical", "standard", or "archive"
    """
    for tier, patterns in config.items():
        if any(file_path.match(pattern) for pattern in patterns):
            return tier
    return "standard"  # Default tier
```

**Git Metadata Extraction API**

```python
def extract_git_metadata(file_path: str) -> dict:
    """
    Extract git metadata for file.

    Returns:
        {
            "commit": "hash",
            "author": "email",
            "date": "ISO8601",
            "message": "commit message",
            "pr": "123" or None,
            "lines_changed": int,
            "recency_days": int
        }

    Fallback: Returns file system mtime if git unavailable
    """
    try:
        # git log -1 --format=%H|%ae|%aI|%s -- file_path
        # Extract PR from message regex: #(\d+)
        # git diff --numstat for lines changed
        # Calculate recency_days from commit date
        pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback to filesystem mtime
        pass
```

**Relevance Scoring API**

```python
class RelevanceScorer:
    """Unified multi-signal relevance scoring."""

    WEIGHTS = {
        "explicit_file_ref": 10.0,  # User mentions file explicitly
        "temporal_recent": 5.0,      # Changed in last 7 days
        "temporal_medium": 2.0,      # Changed in last 30 days
        "keyword_match": 1.0,        # Semantic keyword match
    }

    def score_module(self, module: dict, query: dict, git_metadata: dict) -> float:
        """Calculate relevance score for module."""
        score = 0.0

        # Explicit file references
        if any(file in query.get("explicit_files", []) for file in module["files"]):
            score += self.WEIGHTS["explicit_file_ref"]

        # Temporal scoring
        recency_days = min(
            git_metadata.get(f, {}).get("recency_days", 999)
            for f in module["files"]
        )
        if recency_days <= 7:
            score += self.WEIGHTS["temporal_recent"]
        elif recency_days <= 30:
            score += self.WEIGHTS["temporal_medium"]

        # Keyword matching
        keywords = query.get("keywords", [])
        if any(kw in module["module_id"].lower() for kw in keywords):
            score += self.WEIGHTS["keyword_match"]

        return score
```

**Impact Analysis API**

```python
def analyze_impact(function_name: str, call_graph: list, max_depth: int = 10) -> dict:
    """
    Analyze downstream impact of changing a function.

    Returns:
        {
            "direct_callers": ["func1", "func2"],
            "indirect_callers": ["func3", "func4"],
            "depth_reached": 3,
            "total_affected": 6
        }
    """
    # Build reverse call graph (who calls this function)
    # BFS traversal to find all callers
    # Return direct + indirect callers
    pass
```

**Incremental Update API**

```python
def incremental_update(last_index_path: str, project_root: str) -> tuple[str, list[str]]:
    """
    Update only changed files since last index generation.

    Process:
        1. Load existing index and extract generation timestamp
        2. Git diff to find changed files since timestamp
        3. Identify affected modules (changed files + direct dependencies)
        4. Regenerate only affected detail modules
        5. Update core index metadata
        6. Validate hash consistency

    Returns:
        (updated_index_path, updated_module_paths)
    """
    pass
```

### Workflows and Sequencing

**Workflow 1: Tiered Documentation Storage**

```
1. Index generation starts (project_index.py)
2. Markdown files discovered during file walk
3. For each markdown file:
   a. Apply classification rules (doc_classifier.classify_documentation)
   b. Assign tier: critical, standard, or archive
4. During index generation:
   a. Critical docs ’ core index (d_critical section)
   b. Standard docs ’ detail modules (d_standard section)
   c. Archive docs ’ detail modules (d_archive section)
5. Agent loads core index:
   a. Receives d_critical docs by default
   b. Can request d_standard/d_archive from detail modules if needed
6. Result: 60-80% compression for doc-heavy projects
```

**Workflow 2: Git Metadata Extraction and Temporal Awareness**

```
1. Index generation starts
2. For each file in project:
   a. Call git_metadata.extract_git_metadata(file_path)
   b. Extract: commit, author, date, message, PR, lines_changed
   c. Calculate recency_days (days since last commit)
   d. Fallback to filesystem mtime if git unavailable
3. Store git metadata in core index
4. Agent query with temporal context:
   a. Filter files by recency_days d 7
   b. Weight recent files 5x in relevance scoring
5. Result: Agent prioritizes active development areas
```

**Workflow 3: Hybrid Query Strategy with MCP Integration**

```
1. Agent receives user query with -i flag
2. MCP detection: Runtime check for Read, Grep, Git tools
3. Load core index (always first)
4. Analyze query type and route:

   Scenario A: Explicit File Refs + MCP Read
   - Use MCP Read for actual source files
   - Use core index for dependency discovery

   Scenario B: Semantic Query + MCP Grep
   - Use core index for navigation
   - Use MCP Grep for keyword search
   - Combine results

   Scenario C: Temporal Query + MCP Git
   - Use MCP Git for real-time commits
   - Use core index for context

   Scenario D: No MCP (Fallback)
   - Use detail modules from index

5. Result: Hybrid intelligence (structure + live data)
```

**Workflow 4: Impact Analysis**

```
1. Developer query: "What depends on function X?"
2. Agent loads core index and call graph
3. Call impact.analyze_impact("function_X", call_graph)
4. BFS traversal: direct + indirect callers
5. Return formatted impact report with file paths
6. Result: Developer understands refactoring impact
```

**Workflow 5: Incremental Index Update**

```
1. Developer triggers regeneration
2. Check for existing PROJECT_INDEX.json
3. Git diff to find changes since last generation
4. Identify affected modules
5. Regenerate only affected modules
6. Update core index metadata
7. Validate consistency
8. Report: "3 files changed, 2 modules updated in 2s"
9. Result: Fast updates for large codebases
```

## Non-Functional Requirements

### Performance

**From PRD NFR001 (continued from Epic 1):**
- **Tiered Doc Loading:** Critical docs load immediately; standard/archive on-demand <100ms
- **Git Metadata Extraction:** Add <5 seconds to index generation
- **MCP Detection:** Runtime capability check <50ms
- **Relevance Scoring:** Multi-signal scoring completes in <100ms
- **Impact Analysis:** BFS traversal for 10,000 function call graph <500ms
- **Incremental Update:** Update 10 changed files + dependencies in <10 seconds

**Performance Testing:**
- Doc-heavy project: 500+ markdown files, verify 60-80% compression
- Large history: 10,000+ commits repo
- Incremental updates: 10, 50, 100 changed files

### Security

**Git Metadata Privacy:**
- Author emails require proper handling
- PR numbers may be sensitive (configurable option to exclude)
- Commit messages summarized only (no full storage)

**MCP Tool Security:**
- MCP tools run in user's security context
- No credential passing or token management
- Agent respects MCP tool permissions

**Incremental Update Safety:**
- Hash validation prevents corruption
- Automatic fallback to full regeneration if inconsistency detected
- Atomic updates only

### Reliability/Availability

**Graceful Degradation:**
- Git unavailable ’ fall back to filesystem mtime
- MCP tools unavailable ’ use detail modules from index
- Tiered doc classification fails ’ default to "standard" tier
- Impact analysis on invalid function ’ return empty result
- Incremental update validation fails ’ trigger full regeneration

**Backward Compatibility:**
- Epic 2 format (v2.1) backward compatible with Epic 1 (v2.0)
- Agents detect version field and adapt
- Legacy clients ignore new fields

**Data Integrity:**
- Incremental updates preserve 100% consistency
- Git metadata extraction failures don't block index generation
- MCP detection failures don't break agent operation

### Observability

**Logging Requirements:**
- **Info Level:** Doc compression ratio, git extraction stats, MCP capabilities, relevance scores, incremental stats
- **Debug Level:** Doc tier assignments, git metadata per file, score breakdowns, MCP routing decisions
- **Warning Level:** Git unavailable, MCP detection failed, incremental triggered full regen
- **Error Level:** Git timeout, classification error, scoring failure, incremental corruption

**Metrics to Track:**
- Doc compression ratio (percentage saved)
- Git metadata extraction time and coverage
- MCP tool availability rate
- Relevance scoring accuracy
- Incremental update hit rate
- Impact analysis query time

## Dependencies and Integrations

**Python Standard Library (No New Dependencies)**

| Stdlib Module | New Usage in Epic 2 | Version Required |
|---------------|---------------------|------------------|
| `subprocess` | Git metadata extraction (git log, git diff) | Python 3.12+ |
| `datetime` | Timestamp parsing, recency calculation | Python 3.12+ |
| `collections.defaultdict` | Call graph traversal (impact analysis) | Python 3.12+ |
| `collections.deque` | BFS queue (impact analysis) | Python 3.12+ |
| `re` | PR number extraction, doc pattern matching | Python 3.12+ |

**System Dependencies:**
- **Git** (optional but recommended) - For metadata extraction and incremental updates
  - Commands used: `git log`, `git diff`, `git ls-files`
  - Graceful fallback: filesystem mtime if unavailable

**MCP Tool Integration (New):**
- **MCP Read Tool** - For loading current file content
- **MCP Grep Tool** - For live keyword search
- **MCP Git Tool** - For real-time git operations
- **Integration Pattern:** Runtime detection ’ capability-based routing ’ graceful fallback

**Claude Code Integration (Enhanced):**
- **Subagent System** - index-analyzer.md enhanced with:
  - MCP detection logic
  - Hybrid query routing
  - Multi-signal relevance scoring
  - Impact analysis invocation

## Acceptance Criteria (Authoritative)

**Story 2.1: Tiered Documentation Classification**
- **AC2.1.1:** Classification logic identifies critical docs (README*, ARCHITECTURE*, API*, CONTRIBUTING*)
- **AC2.1.2:** Classification identifies standard docs (development guides, setup docs)
- **AC2.1.3:** Classification identifies archive docs (tutorials, changelogs, meeting notes)
- **AC2.1.4:** Classification rules are configurable via config file
- **AC2.1.5:** Classification results logged during index generation (verbose mode)

**Story 2.2: Tiered Documentation Storage**
- **AC2.2.1:** Core index contains only `d_critical` tier by default
- **AC2.2.2:** Detail modules contain `d_standard` and `d_archive` tiers
- **AC2.2.3:** Configuration option to include all tiers in core index (small projects)
- **AC2.2.4:** Agent loads critical docs by default, can request other tiers if needed
- **AC2.2.5:** Doc-heavy test project shows 60-80% reduction in default index size

**Story 2.3: Git Metadata Extraction**
- **AC2.3.1:** Git metadata extracted: last commit hash, author, commit message, date, lines changed
- **AC2.3.2:** PR number extracted from commit message if present (e.g., "#247" in message)
- **AC2.3.3:** Graceful fallback to file system timestamps when git unavailable
- **AC2.3.4:** Git metadata included in core index for all files
- **AC2.3.5:** Performance: git extraction adds <5 seconds to index generation

**Story 2.4: Temporal Awareness Integration**
- **AC2.4.1:** Agent identifies files changed in last 7/30/90 days from git metadata
- **AC2.4.2:** Relevance scoring weights recent files higher in query results
- **AC2.4.3:** Query "show recent changes" uses git metadata without loading detail modules
- **AC2.4.4:** Agent mentions recency in responses ("auth/login.py changed 2 days ago")
- **AC2.4.5:** Temporal weighting configurable (default: 7-day window = 5x weight)

**Story 2.5: MCP Tool Detection**
- **AC2.5.1:** Agent detects MCP Read, Grep, Git tools at runtime
- **AC2.5.2:** Agent capability map stored (which MCP tools are available)
- **AC2.5.3:** Agent logs MCP availability status when verbose flag used
- **AC2.5.4:** Graceful behavior when MCP tools unavailable (use index only)
- **AC2.5.5:** Documentation explains MCP integration benefits

**Story 2.6: Hybrid Query Strategy**
- **AC2.6.1:** With MCP Read: Agent uses index for navigation, MCP for current file content
- **AC2.6.2:** With MCP Grep: Agent uses index for structure, MCP for live keyword search
- **AC2.6.3:** With MCP Git: Agent uses MCP for real-time git data, index for architectural context
- **AC2.6.4:** Without MCP: Agent uses detail modules from index (fallback behavior)
- **AC2.6.5:** Agent explains which data sources were used (verbose mode)

**Story 2.7: Relevance Scoring Engine**
- **AC2.7.1:** Explicit file references receive highest score (weight: 10x)
- **AC2.7.2:** Temporal context (recent changes) receives high score (weight: 5x for 7 days, 2x for 30 days)
- **AC2.7.3:** Semantic keyword matching receives medium score (weight: 1x)
- **AC2.7.4:** Scoring algorithm documented and configurable
- **AC2.7.5:** Agent loads top-N scored modules (N configurable, default: 5)

**Story 2.8: Impact Analysis Tooling**
- **AC2.8.1:** Query "what depends on <function>" shows all callers from call graph
- **AC2.8.2:** Impact analysis traverses multiple levels (direct + indirect callers)
- **AC2.8.3:** Impact report includes file paths and line numbers
- **AC2.8.4:** Works with both single-file and split architecture indices
- **AC2.8.5:** Documentation includes impact analysis usage examples

**Story 2.9: Incremental Index Updates**
- **AC2.9.1:** Detect changed files via git diff since last index generation
- **AC2.9.2:** Regenerate detail modules only for changed files + direct dependencies
- **AC2.9.3:** Update core index with new metadata for affected files
- **AC2.9.4:** Hash-based validation ensures index consistency after incremental update
- **AC2.9.5:** Full regeneration option available (`/index --full`)

## Traceability Mapping

| AC | Spec Section | Component(s) | Test Idea |
|----|--------------|--------------|-----------|
| AC2.1.1-2.1.5 | Data Models (Tiering), APIs (Classification) | doc_classifier.py | Unit test classification with sample docs |
| AC2.2.1-2.2.5 | Data Models (Enhanced Index), APIs (Storage) | project_index.py | Generate index, measure compression |
| AC2.3.1-2.3.5 | Data Models (Git Metadata), APIs (Extraction) | git_metadata.py | Extract from test repo, verify fields |
| AC2.4.1-2.4.5 | APIs (Temporal Scorer), Workflows (Temporal) | relevance.py | Query recent changes, verify weighting |
| AC2.5.1-2.5.5 | APIs (MCP Detection) | mcp_detector.py | Mock MCP, test detection |
| AC2.6.1-2.6.5 | Workflows (Hybrid Query) | index-analyzer.md | Integration test with/without MCP |
| AC2.7.1-2.7.5 | APIs (Relevance Engine) | relevance.py | Unit test scoring variations |
| AC2.8.1-2.8.5 | APIs (Impact Analysis) | impact.py | Test with sample call graph |
| AC2.9.1-2.9.5 | APIs (Incremental), Workflows (Incremental) | incremental.py | Change files, verify selective regen |

**Traceability to PRD Requirements:**

| PRD Requirement | Related ACs | Implementation |
|-----------------|-------------|----------------|
| FR001: Tiered doc classification | AC2.1.1-2.1.5 | doc_classifier.py |
| FR002: Tiered storage sections | AC2.2.1-2.2.5 | project_index.py |
| FR008: Git metadata extraction | AC2.3.1-2.3.5 | git_metadata.py |
| FR009: Temporal awareness | AC2.4.1-2.4.5 | relevance.py |
| FR015: Incremental updates | AC2.9.1-2.9.5 | incremental.py |
| NFR001: Performance | AC2.3.5, AC2.2.5 | <5s git extraction, 60-80% compression |

## Risks, Assumptions, Open Questions

**Risks:**

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| R8 | Git metadata extraction fails on large repos (10,000+ commits) | Medium | Medium | Implement timeout (5s), fallback to filesystem, cache results |
| R9 | Tiered doc classification rules don't match user expectations | Medium | Low | Make rules fully configurable, provide override mechanism |
| R10 | MCP tool detection produces false positives/negatives | Medium | Medium | Conservative detection (default: unavailable), allow manual override |
| R11 | Hybrid query routing adds latency vs pure index approach | Low | Medium | Profile MCP tool calls, implement caching, parallel requests |
| R12 | Relevance scoring misses obvious matches | Medium | Medium | Expand to fuzzy matching, multiple scoring strategies |
| R13 | Incremental update validation too strict | Low | Low | Tune validation thresholds, log details for debugging |
| R14 | Impact analysis exceeds memory limits on massive call graphs | Low | Medium | Implement depth limit, result truncation, streaming output |

**Assumptions:**

- A8: Critical/standard/archive tier classification aligns with typical project docs
- A9: Git metadata extraction performance acceptable for repos up to 100,000 commits
- A10: MCP tool availability can be reliably detected at runtime
- A11: Hybrid query latency acceptable to users (< 1 second total)
- A12: Keyword-based relevance scoring sufficient until fuzzy matching added
- A13: Incremental updates worthwhile optimization vs always full regeneration
- A14: Impact analysis depth of 10 levels sufficient for typical call graphs
- A15: Users prefer automatic MCP integration vs manual tool selection

**Open Questions:**

- Q8: Should tiered doc classification support user-defined custom tiers?
- Q9: How to handle git submodules (separate metadata extraction per submodule)?
- Q10: Should MCP tool preferences be persisted?
- Q11: What's the right balance between MCP freshness and index speed?
- Q12: Should incremental updates be triggered automatically on file save (daemon mode)?
- Q13: How to handle git repos with multiple branches (which branch for metadata)?
- Q14: Should impact analysis support filtering by module/directory (scoped impact)?
- Q15: Should relevance scoring weights be ML-trained based on user behavior (future)?

## Test Strategy Summary

**Test Levels:**

**Unit Tests:**
- `doc_classifier.py`: Tiering logic with various doc patterns
- `git_metadata.py`: Metadata extraction with mocked git commands
- `mcp_detector.py`: MCP detection with mocked tool availability
- `relevance.py`: Multi-signal scoring with sample queries
- `impact.py`: Call graph traversal with synthetic graphs
- `incremental.py`: Change detection and selective regeneration logic

**Integration Tests:**
- End-to-end tiered doc storage: Generate index, verify compression ratio
- Git metadata extraction on real repository: Verify all fields populated
- Hybrid query workflow: Test with MCP tools mocked and real
- Impact analysis on real codebase: Verify caller detection accuracy
- Incremental update on real changes: Make changes, verify selective regen

**Performance Tests:**
- **Doc-heavy project:** 500+ markdown files, measure compression (target: 60-80%)
- **Large git history:** 10,000+ commits, measure extraction time (target: <5s)
- **Relevance scoring:** 1,000 modules, measure scoring time (target: <100ms)
- **Impact analysis:** 10,000 function call graph, measure traversal (target: <500ms)
- **Incremental update:** 100 changed files, measure update time (target: <10s)

**Regression Tests:**
- Verify Epic 1 functionality still works with Epic 2 enhancements
- Test backward compatibility with v2.0-split format
- Verify graceful degradation when git unavailable
- Test fallback behavior when MCP tools unavailable

**Test Frameworks:**
- Python `unittest` or `pytest` (stdlib preferred)
- Mock libraries for git commands and MCP tools (`unittest.mock`)
- Integration tests with real git repositories (test fixtures)
- Performance benchmarking with `time` and custom profiling

**Coverage Targets:**
- Unit tests: 80%+ code coverage for new modules
- Integration tests: All 5 workflows documented
- Performance tests: All NFR targets validated
- Edge cases: Git unavailable, no MCP tools, empty projects, massive call graphs

**Test Data:**
- **Doc-heavy project:** Create synthetic project with 500 markdown files
- **Git history project:** Use real open-source repo with 10,000+ commits
- **Call graph project:** Generate synthetic Python project with deep call chains
- **MCP mock environment:** Simulate MCP tool availability for hybrid query testing

**Acceptance Testing:**
- Validate all 45 ACs (AC2.1.1 through AC2.9.5)
- User acceptance: Beta test with documentation-heavy projects (compression validation)
- Performance validation: Benchmark against NFR001 extended targets
- Integration validation: Verify MCP tool integration with Claude Code environment
