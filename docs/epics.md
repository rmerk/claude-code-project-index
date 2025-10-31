# claude-code-project-index - Epic Breakdown

**Author:** Ryan
**Date:** 2025-10-31
**Project Level:** 2
**Target Scale:** 14-19 stories across 2 epics

---

## Overview

This document provides the detailed epic breakdown for claude-code-project-index, expanding on the high-level epic list in the [PRD](./PRD.md).

Each epic includes:

- Expanded goal and value proposition
- Complete story breakdown with user stories
- Acceptance criteria for each story
- Story sequencing and dependencies

**Epic Sequencing Principles:**
- Epic 1 establishes foundational infrastructure and split architecture
- Epic 2 builds on Epic 1's infrastructure to add intelligent features
- Stories within epics are vertically sliced and sequentially ordered
- No forward dependencies - each story builds only on previous work

---

## Epic 1: Split Index Architecture

**Expanded Goal:**

Enable claude-code-project-index to scale to large codebases (10,000+ files) by implementing a split architecture that separates lightweight core metadata from detailed module information. This epic delivers the foundational infrastructure that all projects need - regardless of size or documentation ratio - through core/detail separation, lazy-loading capabilities, and backward compatibility to ensure smooth migration for existing users.

**Value Delivery:**

- Universal scalability (benefits all project sizes)
- Core index remains under 100KB for 10,000 file codebases
- Agents can navigate large codebases without context overflow
- Existing users experience zero breaking changes

**Story Breakdown:**

**Story 1.1: Design Split Index Schema**

As a developer,
I want a well-defined schema for core and detail index formats,
So that the split architecture has a solid foundation and clear contracts.

**Acceptance Criteria:**
1. Core index schema documented (file tree, function signatures, imports, git metadata structure)
2. Detail module schema documented (per-module detailed function/class info)
3. Schema includes version field for future compatibility
4. JSON examples provided for both core and detail formats
5. Schema supports all existing index features (functions, classes, call graph, docs)

**Prerequisites:** None (foundation story)

---

**Story 1.2: Generate Core Index**

As a developer,
I want the indexer to generate a lightweight core index,
So that agents can load project overview without hitting context limits.

**Acceptance Criteria:**
1. `PROJECT_INDEX.json` generated with file tree, function/class names (no bodies), imports
2. Core index includes git metadata (last commit, author, date) per file
3. Core index size stays under 100KB for test project (current ~3,500 files)
4. Core index includes references to detail module locations
5. Existing single-file generation still works (backward compat maintained)

**Prerequisites:** Story 1.1 (schema defined)

---

**Story 1.3: Generate Detail Modules**

As a developer,
I want the indexer to create detail modules with full code information,
So that agents can lazy-load deep details only when needed.

**Acceptance Criteria:**
1. `PROJECT_INDEX.d/` directory created with per-module detail files
2. Detail modules include full function/class signatures, call graphs, documentation
3. Detail modules organized by directory structure (e.g., `auth.json`, `database.json`)
4. Detail module references match core index module IDs
5. Total detail module size + core index ≤ original single-file index size

**Prerequisites:** Story 1.2 (core index generation)

---

**Story 1.4: Lazy-Loading Interface**

As an AI agent,
I want a clear interface to request specific detail modules,
So that I can load only relevant code sections based on user queries.

**Acceptance Criteria:**
1. Agent can request detail module by module name (e.g., "auth", "database")
2. Agent can request detail module by file path (e.g., "src/auth/login.py")
3. Interface returns module content or clear error if not found
4. Interface supports batch requests (load multiple modules in one call)
5. Documentation explains how agents should use the interface

**Prerequisites:** Story 1.3 (detail modules exist)

---

**Story 1.5: Update Index-Analyzer Agent**

As a developer using `-i` flag,
I want the index-analyzer agent to intelligently use split architecture,
So that I get relevant code context without manual module selection.

**Acceptance Criteria:**
1. Agent loads core index first and detects split architecture presence
2. Agent performs relevance scoring on core index to identify relevant modules
3. Agent lazy-loads top 3-5 relevant detail modules based on query
4. Agent provides response combining core index structure + detail module content
5. Agent logs which modules were loaded (when verbose flag used)

**Prerequisites:** Story 1.4 (lazy-loading interface available)

---

**Story 1.6: Backward Compatibility Detection**

As an existing user,
I want the system to work with my existing single-file index,
So that I can upgrade without breaking my workflow.

**Acceptance Criteria:**
1. System detects legacy single-file format (no PROJECT_INDEX.d/ directory)
2. Agent loads full single-file index when split architecture not detected
3. All existing functionality works with legacy format (no regressions)
4. Clear message informs user that legacy format is in use
5. System suggests migration to split format for large projects

**Prerequisites:** Story 1.5 (agent supports split format)

---

**Story 1.7: Migration Utility**

As an existing user,
I want a simple command to migrate my index to split architecture,
So that I can benefit from the new scalability without manual work.

**Acceptance Criteria:**
1. Command `/index --migrate` converts single-file → split format
2. Migration preserves all existing index data (no information loss)
3. Migration creates backup of original single-file index
4. Migration validates split index after creation (integrity check)
5. Clear success/failure messages with rollback option if migration fails

**Prerequisites:** Story 1.6 (both formats supported)

---

**Story 1.8: Configuration and Documentation**

As a developer,
I want control over index generation mode and clear documentation,
So that I can choose the right approach for my project size.

**Acceptance Criteria:**
1. Configuration option to force single-file mode (for small projects)
2. Configuration option to force split mode (for large projects)
3. Auto-detection threshold configurable (default: >1000 files → split mode)
4. README updated with split architecture explanation and benefits
5. Migration guide and troubleshooting documentation added

**Prerequisites:** Story 1.7 (migration utility exists)

---

## Epic 2: Enhanced Intelligence & Developer Tools

**Expanded Goal:**

Build on Epic 1's split architecture to add intelligent features that optimize index relevance and improve developer productivity. This includes tiered documentation storage (60-80% compression for doc-heavy projects), git temporal awareness for prioritizing recent changes, MCP tool integration for hybrid static/live data access, advanced agent intelligence with adaptive query strategies, and impact analysis tooling for understanding code dependencies.

**Value Delivery:**

- Dramatic compression for documentation-heavy projects
- Temporal awareness prioritizes recent/relevant code
- Hybrid intelligence (pre-built index + live MCP data)
- Developer productivity tools (impact analysis)
- Incremental updates reduce regeneration time

**Story Breakdown:**

**Story 2.1: Tiered Documentation Classification**

As a developer,
I want the indexer to automatically classify documentation by importance,
So that critical architectural docs are prioritized over tutorials and changelogs.

**Acceptance Criteria:**
1. Classification logic identifies critical docs (README*, ARCHITECTURE*, API*, CONTRIBUTING*)
2. Classification identifies standard docs (development guides, setup docs)
3. Classification identifies archive docs (tutorials, changelogs, meeting notes)
4. Classification rules are configurable via config file
5. Classification results logged during index generation (verbose mode)

**Prerequisites:** None (builds on Epic 1's infrastructure)

---

**Story 2.2: Tiered Documentation Storage**

As a developer,
I want documentation stored in separate tiers in the index,
So that I get 60-80% compression for doc-heavy projects.

**Acceptance Criteria:**
1. Core index contains only `d_critical` tier by default
2. Detail modules contain `d_standard` and `d_archive` tiers
3. Configuration option to include all tiers in core index (small projects)
4. Agent loads critical docs by default, can request other tiers if needed
5. Doc-heavy test project shows 60-80% reduction in default index size

**Prerequisites:** Story 2.1 (classification logic exists)

---

**Story 2.3: Git Metadata Extraction**

As a developer,
I want git metadata (commit, author, date, PR) extracted for each file,
So that the system understands temporal context and recent changes.

**Acceptance Criteria:**
1. Git metadata extracted: last commit hash, author, commit message, date, lines changed
2. PR number extracted from commit message if present (e.g., "#247" in message)
3. Graceful fallback to file system timestamps when git unavailable
4. Git metadata included in core index for all files
5. Performance: git extraction adds <5 seconds to index generation

**Prerequisites:** None (extends Epic 1's core index)

---

**Story 2.4: Temporal Awareness Integration**

As a developer,
I want the agent to prioritize recently changed files,
So that debugging and context retrieval focus on active development areas.

**Acceptance Criteria:**
1. Agent identifies files changed in last 7/30/90 days from git metadata
2. Relevance scoring weights recent files higher in query results
3. Query "show recent changes" uses git metadata without loading detail modules
4. Agent mentions recency in responses ("auth/login.py changed 2 days ago")
5. Temporal weighting configurable (default: 7-day window = 2x weight)

**Prerequisites:** Story 2.3 (git metadata available)

---

**Story 2.5: MCP Tool Detection**

As an AI agent,
I want to detect which MCP tools are available,
So that I can use live data sources when possible.

**Acceptance Criteria:**
1. Agent detects MCP Read, Grep, Git tools at runtime
2. Agent capability map stored (which MCP tools are available)
3. Agent logs MCP availability status when verbose flag used
4. Graceful behavior when MCP tools unavailable (use index only)
5. Documentation explains MCP integration benefits

**Prerequisites:** None (agent enhancement)

---

**Story 2.6: Hybrid Query Strategy**

As a developer,
I want the agent to intelligently combine index and MCP data,
So that I get pre-computed structure plus real-time content.

**Acceptance Criteria:**
1. With MCP Read: Agent uses index for navigation, MCP for current file content
2. With MCP Grep: Agent uses index for structure, MCP for live keyword search
3. With MCP Git: Agent uses MCP for real-time git data, index for architectural context
4. Without MCP: Agent uses detail modules from index (fallback behavior)
5. Agent explains which data sources were used (verbose mode)

**Prerequisites:** Story 2.5 (MCP detection available)

---

**Story 2.7: Relevance Scoring Engine**

As an AI agent,
I want a unified relevance scoring system,
So that I load the most relevant modules regardless of query type.

**Acceptance Criteria:**
1. Explicit file references receive highest score (weight: 10x)
2. Temporal context (recent changes) receives high score (weight: 2-5x)
3. Semantic keyword matching receives medium score (weight: 1x)
4. Scoring algorithm documented and configurable
5. Agent loads top-N scored modules (N configurable, default: 5)

**Prerequisites:** Story 2.4 (temporal awareness), Story 2.6 (query strategies)

---

**Story 2.8: Impact Analysis Tooling**

As a developer,
I want to understand what breaks if I change a function,
So that I can refactor safely and predict downstream impacts.

**Acceptance Criteria:**
1. Query "what depends on <function>" shows all callers from call graph
2. Impact analysis traverses multiple levels (direct + indirect callers)
3. Impact report includes file paths and line numbers
4. Works with both single-file and split architecture indices
5. Documentation includes impact analysis usage examples

**Prerequisites:** Epic 1 complete (call graph in core index)

---

**Story 2.9: Incremental Index Updates**

As a developer,
I want to update only changed files in the index,
So that regeneration is fast for large codebases.

**Acceptance Criteria:**
1. Detect changed files via git diff since last index generation
2. Regenerate detail modules only for changed files + direct dependencies
3. Update core index with new metadata for affected files
4. Hash-based validation ensures index consistency after incremental update
5. Full regeneration option available (`/index --full`)

**Prerequisites:** Story 2.3 (git metadata), Epic 1 complete (split architecture)

---

## Story Guidelines Reference

**Story Format:**

```
**Story [EPIC.N]: [Story Title]**

As a [user type],
I want [goal/desire],
So that [benefit/value].

**Acceptance Criteria:**
1. [Specific testable criterion]
2. [Another specific criterion]
3. [etc.]

**Prerequisites:** [Dependencies on previous stories, if any]
```

**Story Requirements:**

- **Vertical slices** - Complete, testable functionality delivery
- **Sequential ordering** - Logical progression within epic
- **No forward dependencies** - Only depend on previous work
- **AI-agent sized** - Completable in 2-4 hour focused session
- **Value-focused** - Integrate technical enablers into value-delivering stories

---

**For implementation:** Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown.
