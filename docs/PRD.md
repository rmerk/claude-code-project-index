# claude-code-project-index Product Requirements Document (PRD)

**Author:** Ryan
**Date:** 2025-11-04 (Updated with Epic 3)
**Project Level:** 2
**Target Scale:** 19-24 stories across 3 epics

---

## Goals and Background Context

### Goals

1. **Enable scalability to large codebases (10,000+ files)** without exceeding AI context limits
2. **Reduce index size by 60-80%** for documentation-heavy projects through tiered storage
3. **Implement split index architecture** with lazy-loading for on-demand detail retrieval
4. **Add temporal awareness** via git metadata to prioritize recently changed code
5. **Maintain backward compatibility** with existing single-file index format

### Background Context

The claude-code-project-index tool currently provides AI agents with architectural awareness by generating comprehensive JSON indices of codebases. While this works well for small to medium projects, analysis has revealed a critical scaling bottleneck: documentation indexing consumes 83.7% of the index size, causing the tool to fail on large codebases where the index exceeds AI context limits. This "you can't filter what you can't load" constraint means that even intelligent subagent filtering cannot help if the comprehensive index is too large to load initially.

Recent brainstorming sessions identified three key opportunities: tiered documentation storage (immediate 60-80% compression for doc-heavy projects), split index architecture with lazy-loading (enabling truly large codebase support), and git metadata integration (temporal awareness to prioritize recently changed code). These enhancements will transform the tool from a small-project utility into an enterprise-grade solution capable of handling 10,000+ file codebases while maintaining the elegant simplicity that makes it valuable today.

---

## Requirements

### Functional Requirements

**Tiered Documentation Storage:**
- **FR001:** System shall classify markdown documentation into three tiers: critical (README*, ARCHITECTURE*, API*), standard (development guides, setup docs), and archive (tutorials, changelogs, meeting notes)
- **FR002:** System shall store tiered documentation in separate index sections (d_critical, d_standard, d_archive) with default loading of critical tier only
- **FR003:** System shall provide configuration option to include all documentation tiers when needed

**Split Index Architecture:**
- **FR004:** System shall generate a lightweight core index (PROJECT_INDEX.json) containing file tree, function signatures, imports, and git metadata
- **FR005:** System shall generate detailed module indices in PROJECT_INDEX.d/ directory with per-module or per-file granularity
- **FR006:** System shall support lazy-loading of detail modules based on query relevance at runtime
- **FR007:** System shall implement relevance scoring combining explicit file references, temporal context (recent changes), and semantic keyword matching

**Git Metadata Integration:**
- **FR008:** System shall extract git metadata for each file including: last commit hash, author, commit message, date, PR number (if present), and lines changed
- **FR009:** System shall use git metadata to enable temporal awareness and recency-based prioritization

**Backward Compatibility:**
- **FR010:** System shall maintain support for legacy single-file PROJECT_INDEX.json format for existing users
- **FR011:** System shall provide migration path from single-file to split architecture format

**Documentation-Code Linking:**
- **FR012:** System shall automatically associate documentation files with related code modules based on path proximity and naming patterns (e.g., docs/auth.md → src/auth/*)

**Lazy-Loading and Error Handling:**
- **FR013:** System shall provide query interface for agents to request specific detail modules by module name or file path
- **FR014:** System shall handle git-unavailable scenarios gracefully, falling back to file system timestamps when git metadata cannot be extracted
- **FR015:** System shall support incremental index regeneration, updating only modified files and their direct dependencies

### Non-Functional Requirements

- **NFR001:** **Performance** - Index generation shall complete within 30 seconds for codebases up to 10,000 files. Lazy-loading of detail modules shall have latency under 500ms per module request.

- **NFR002:** **Scalability** - Core index size shall not exceed 100KB (approximately 25,000 tokens) for codebases up to 10,000 files, ensuring compatibility with AI agent context limits.

- **NFR003:** **Maintainability** - Index format shall be human-readable JSON with clear schema documentation, enabling debugging and third-party tool integration.

---

## User Journeys

**Primary Use Case: Agent-Driven Adaptive Index Usage**

**Actor:** Developer working on a codebase (medium-to-large scale)

**Journey:**

1. **Initial Setup**
   - Developer runs `/index` command in their project
   - System scans and generates: core index (PROJECT_INDEX.json) + detail modules (PROJECT_INDEX.d/)
   - Applies tiered documentation storage and split architecture based on detection
   - Index created: 3,500 files indexed, split across core + 25 detail modules

2. **Agent Intelligence - Explicit File Reference**
   - Developer asks: **"@src/auth/login.py @src/auth/session.py fix the session timeout bug"**
   - **Agent loads core index** (45KB → ~11,000 tokens)
   - **Agent detects:** Explicit file references provided by user
   - **Agent checks:** MCP tools available?
   - **If MCP available:**
     - Uses MCP Read tool to load actual source files directly (fresher than index)
     - Uses core index for dependency discovery (what imports login.py?)
     - Uses MCP Git tools for real-time git blame/log on those specific files
   - **If MCP not available:**
     - Loads detail modules for specified files from PROJECT_INDEX.d/
     - Uses pre-indexed git metadata from detail modules
   - Agent provides focused response with deep context

3. **Agent Intelligence - General Question**
   - Developer asks: **"How does the authentication system work? -i"**
   - **Agent loads core index**
   - **Agent detects:** No explicit files, semantic query only
   - **Agent checks:** MCP tools available?
   - **If MCP available:**
     - Uses core index to identify auth/ directory modules (navigation)
     - Uses MCP Grep tool to search for "authenticate", "login", "session" across codebase
     - Combines index structure + live MCP search results for comprehensive view
     - Uses MCP Read for top 3-5 most relevant files found
   - **If MCP not available:**
     - Relevance scoring on core index → identifies auth modules
     - Loads detail modules from PROJECT_INDEX.d/
   - Agent provides architectural overview

4. **Agent Intelligence - Temporal Question**
   - Developer asks: **"Show me what changed in the last week"**
   - **Agent loads core index**
   - **Agent detects:** Temporal query
   - **Agent checks:** MCP tools available?
   - **If MCP available:**
     - Uses MCP Git tool: `git log --since="1 week ago" --stat`
     - Gets real-time commit data (more current than index)
     - Uses core index to provide architectural context for changed files
   - **If MCP not available:**
     - Uses git metadata from core index only
   - Returns commit history with context

5. **Agent Intelligence - Hybrid Strategy (Best of Both)**
   - Developer asks: **"Find all API endpoints and show me which ones changed recently"**
   - **Agent strategy with MCP:**
     - **Index:** Use core index for fast structural navigation (find API routes)
     - **MCP Grep:** Search for route decorators, endpoint patterns dynamically
     - **MCP Git:** Get real-time change data for discovered endpoints
     - **Combine:** Index provides structure, MCP provides freshness
   - **Outcome:** Agent leverages pre-built index for speed + MCP for real-time accuracy

6. **Agent Intelligence - Small Project Fallback**
   - (Alternative scenario: 200 file project, single-file index)
   - Agent loads core index, detects: no PROJECT_INDEX.d/ directory
   - **With MCP:** Uses index for navigation, MCP Read for actual content
   - **Without MCP:** Loads full single-file index (fits in context)

7. **Outcome**
   - **Agent uses four relevance signals:**
     1. **Explicit context** (file references) → MCP Read if available, else detail modules
     2. **Semantic context** (keywords) → MCP Grep if available, else index search
     3. **Temporal context** (git metadata) → MCP Git if available, else indexed metadata
     4. **Structural context** (dependencies, architecture) → Always uses index (pre-computed relationships)
   - **Hybrid intelligence:** Index provides architectural awareness, MCP provides real-time data
   - Agent automatically detects MCP availability and adapts strategy

**Key Intelligence:** The **index-analyzer agent** treats the index as a **fast architectural map** and MCP tools as **real-time data sources**. When both are available, it combines them: index for navigation/structure, MCP for current content/metadata. When MCP unavailable, it relies on pre-built detail modules.

---

## UX Design Principles

1. **Progressive Disclosure** - Show minimal output by default, provide verbose flags for details
2. **Graceful Degradation** - Work well without MCP tools, better with them
3. **Clear Feedback** - Inform users about index strategy chosen (split vs single-file, tiered docs applied)
4. **Fast Defaults** - Optimize for speed in common cases (core index only), allow deeper queries when needed

---

## User Interface Design Goals

**Platform & Interface:**
- Primary interface: CLI commands (`/index`, `-i` flag)
- Secondary interface: JSON index files (human-readable for debugging)
- Agent interface: index-analyzer agent with adaptive query routing

**Key Interaction Patterns:**
- Silent success (index generation completes with summary)
- Informative errors (clear messages when git unavailable, paths invalid)
- Progress indicators for large codebases (show file count processed)

**Design Constraints:**
- Must work in terminal environments (no GUI)
- JSON output must remain backward compatible
- Agent behavior should be transparent (log decisions when verbose flag used)

---

## Epic List

**Epic 1: Split Index Architecture**
- Goal: Enable large codebase support (10,000+ files) through split index architecture with core/detail separation, lazy-loading, and backward compatibility
- Estimated stories: 7-9 stories
- Value: Universal scalability solution that benefits all projects regardless of size or documentation ratio
- Key deliverables:
  - Core index (PROJECT_INDEX.json) with lightweight metadata
  - Detail modules (PROJECT_INDEX.d/) with per-module granularity
  - Lazy-loading interface for agents
  - Backward compatibility and migration path
  - Basic agent updates to consume split format

**Epic 2: Enhanced Intelligence & Developer Tools**
- Goal: Add intelligent features that optimize index relevance through tiered documentation, git temporal awareness, MCP integration, adaptive agent behavior, and impact analysis tooling
- Estimated stories: 7-10 stories
- Value: Builds on Epic 1's infrastructure to add smart compression, query optimization, and developer productivity tools
- Key deliverables:
  - Tiered documentation storage (60-80% compression for doc-heavy projects)
  - Git metadata extraction and temporal awareness
  - MCP tool integration for hybrid index+live data
  - Advanced agent intelligence (relevance scoring, adaptive strategies)
  - Incremental index updates
  - Impact analysis tooling (downstream dependency analysis via call graph)

**Epic 3: Production Readiness for Claude Code CLI**
- Goal: Deliver production-grade installation, upgrade experience, and comprehensive documentation for real-world Claude Code CLI usage
- Estimated stories: 5 stories (7-12 days)
- Value: Transforms Epic 2's features into production-ready tooling with validated performance, multi-IDE support, and complete documentation
- Key deliverables:
  - Smart installation with config presets and auto-upgrade prompts
  - Performance validation on medium projects (500+ files)
  - Comprehensive documentation (Claude Code-first approach)
  - Version management system with update checking
  - Multi-tool MCP support (Claude Code > Cursor > Claude Desktop)

**Total: 3 epics, 19-24 stories** (solidly Level 2, touching Level 3)

> **Note:** Detailed epic breakdown with full story specifications is available in [epics.md](./epics.md)

---

## Out of Scope

**Deferred to Future Releases:**
- **Query-responsive index generation** - Dynamic index creation at query-time (identified as "moonshot" in brainstorming - requires significant R&D)
- **Hierarchical zoom levels** - Multi-level progressive detail loading (L0/L1/L2 architecture - needs new agent protocol)
- **Risk scoring system** - Automated risk calculation combining complexity + size + recency metrics
- **Project-type aware indexing** - Detection and adaptation for monorepo, microservices, library patterns

**Explicitly Not Supported:**
- **GUI/Web interface** - Remains CLI-only tool
- **Real-time index updates** - Incremental updates on file save (daemon mode) - Epic 2 supports manual incremental updates only
- **Language-specific deep analysis** - Advanced semantic analysis beyond signatures (AST-level code understanding)
- **Cloud/remote index storage** - All indices remain local filesystem only
- **Multi-repository indexing** - Each repository maintains independent index (monorepo support within single repo only)

**Integration Boundaries:**
- **LSP (Language Server Protocol) integration** - Not building LSP server; index remains supplementary tool
- **IDE plugins** - No native IDE integrations (users access via Claude Code CLI)
- **CI/CD automation** - No automatic index regeneration in pipelines (users trigger manually)
