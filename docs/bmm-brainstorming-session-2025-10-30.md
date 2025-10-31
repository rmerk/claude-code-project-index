# Brainstorming Session Results

**Session Date:** 2025-10-30
**Facilitator:** Brainstorming Facilitator
**Participant:** Ryan

## Executive Summary

**Topic:** Improving claude-code-project-index performance and usability for large codebases

**Session Goals:**
- Identify scalability challenges and bottlenecks
- Generate solutions for handling large codebases efficiently
- Explore technical approaches for compression and indexing at scale
- Consider UX improvements for large project contexts
- Address performance, memory, and token budget constraints

**Techniques Used:**
1. Five Whys (Deep Analysis) - Root cause investigation
2. First Principles Thinking (Creative) - Rebuilding from fundamental truths
3. SCAMPER Method (Structured) - Systematic improvement generation
4. Resource Constraints (Structured) - Extreme limits reveal essentials

**Total Ideas Generated:** 14 concrete ideas across immediate, future, and moonshot categories

### Key Themes Identified:

**The Scale Problem:** Documentation bloat (83.7%) prevents large codebase indexing

**The Root Constraint:** "You can't filter what you can't load" - comprehensive indices become too large for context limits

**The Solution Pattern:** Split architecture + tiered data + query-time relevance + temporal awareness

**The Paradigm Shift:** From "index everything, filter later" to "understand intent, load relevant subset"

## Technique Sessions

### Technique 1: Five Whys (Deep Analysis)

**Question 1:** Why does the index consume too much context for AI agents to properly leverage?

**Analysis Performed:** Analyzed actual PROJECT_INDEX.json to identify space consumers

**BREAKTHROUGH FINDING:**
```
📊 Size Breakdown (47KB total / ~12K tokens):
  1. Documentation (d): 83.7% (9,905 tokens) ⚠️ MAJOR BLOAT
  2. Functions (f): 8.8% (1,044 tokens)
  3. Call graph (g): 2.3% (274 tokens)
  4. Tree structure: 2.2% (264 tokens)
  5. Everything else: 3% (354 tokens)

📚 Documentation details:
  - 158 markdown files indexed
  - Each file contributes ~250 bytes of header structure
```

**Key Insight:** The documentation indexing (markdown headers) consumes **83.7%** of the index! For large codebases with extensive documentation, this would explode the context budget.

---

**Question 2:** Why does the indexer include ALL markdown documentation headers?

**README Review Findings:**

The tool's stated purpose (from README):
> "PROJECT_INDEX extracts and tracks:
> - Functions & Classes: Full signatures with parameters and return types
> - Call Relationships: Which functions call which others
> - File Organization: All code files respecting .gitignore
> - Directory Structure: Project layout with file counts"

**KEY OBSERVATION:** Documentation headers are NOT listed as a primary feature! The focus is on CODE structure (functions, classes, calls, file org).

**Insight:** The `d` (docs) section exists in the format, but appears to be a secondary feature. The tool was designed for CODE-heavy projects, not doc-heavy ones.

**This project's unique situation:**
- Only 11 code files (Python/Shell)
- But 158 markdown files (mostly from bundled BMad framework)
- Documentation dominates because BMad framework docs are included
- The indexer treats bundled framework docs the same as project docs

**Root Cause Hypothesis:** The documentation indexing wasn't designed to scale for projects with extensive documentation frameworks bundled in. It assumes docs are supplementary to code, not the dominant content.

---

**Question 3:** Why does documentation become a problem for large codebases?

**User Insight:** The indexer should be more selective about WHICH docs matter for architectural awareness.

**Key Realization:** Not all documentation has equal value for understanding code architecture!

**Documentation value hierarchy:**

**HIGH VALUE** (critical for architectural awareness):
- README.md (project overview)
- ARCHITECTURE.md / architecture/ (system design)
- API documentation (interfaces, contracts)
- CONTRIBUTING.md (development patterns)
- Technical design docs

**MEDIUM VALUE** (helpful but not essential):
- Development guides
- Setup/installation docs
- Troubleshooting guides

**LOW VALUE** (for architectural understanding):
- Tutorials and how-to guides
- Workflow documentation (like BMad workflows)
- User guides
- Marketing/promotional content
- Changelogs and release notes
- Meeting notes, ADRs (may be numerous)

**Current Problem:** The indexer treats ALL markdown files equally, indexing workflow guides and tutorials with the same priority as architecture documentation.

**For large codebases:** If you have 500 markdown files, maybe only 5-10 are architecturally critical, but all 500 consume context.

---

**Question 4:** Why does the indexer lack selectivity about which documentation matters?

**User Insight:** The concept of "architectural relevance" is subjective and context-dependent.

**Deep Root Cause Identified:**

**Architectural relevance varies by:**
1. **Project type** - A web app cares about API docs; a library cares about usage examples
2. **Development phase** - New features need design docs; maintenance needs troubleshooting guides
3. **User intent** - "Fix auth bug" needs different docs than "understand system design"
4. **Team conventions** - Some teams put everything in wikis, others in /docs, others in code comments
5. **Codebase maturity** - Startups have sparse docs; enterprises have thousands of pages

**The Challenge:** What's "architecturally relevant" for YOUR codebase in YOUR context can't be determined by filename patterns or directory structure alone.

**Example from this project:**
- `bmad/` docs are NOT relevant to understanding the indexer's architecture
- But for someone working on BMad integration, they WOULD be relevant
- The same file has different value depending on what you're trying to accomplish

**Key Insight:** A one-size-fits-all approach to documentation indexing will always fail at scale because relevance is contextual.

---

**Question 5:** Why can't relevance be determined at usage time?

**Critical Architecture Review from README:**

The tool has THREE usage modes:
1. **Small projects**: `@PROJECT_INDEX.json` - Main agent loads entire index
2. **Medium projects**: `-i` flag - **Subagent analyzes index and returns only relevant findings**
3. **Large projects**: `-ic` flag - Export to external AI with massive context

**KEY REALIZATION:** The subagent mode DOES filter at query time! It:
- Loads the comprehensive index
- Analyzes based on user's prompt
- Returns ONLY relevant findings to main agent

**But here's the REAL problem:**

**The subagent still needs to LOAD and PROCESS the entire comprehensive index.**

If the index is bloated with docs:
- Small project (12k tokens) → ✅ Works in all modes
- Medium project with docs (50k tokens) → ⚠️ Subagent can handle it with `-i50`
- Large project with extensive docs (500k tokens) → ❌ Exceeds even `-i100` maximum

**ROOT CAUSE IDENTIFIED:**

The fundamental problem isn't about predicting relevance - it's that **the comprehensive index itself becomes too large for even the filtering subagent to consume**.

The bottleneck happens BEFORE filtering:
1. Index gets generated with all docs → 500k tokens
2. User tries `-i100` (max for subagent mode)
3. Index is 500k, but subagent can only handle 100k
4. **System fails before filtering even begins**

**The time-gap isn't the problem - it's the RAW SIZE of the pre-filtering index.**

---

**Five Whys Summary - Root Cause Chain:**

1. **Why consume too much context?** → Documentation section is 83.7% of index
2. **Why include all docs?** → Tool designed for code-heavy projects, not doc-heavy ones
3. **Why is this a problem for large codebases?** → Need selectivity - not all docs are equally valuable
4. **Why lack selectivity?** → Architectural relevance is subjective and context-dependent
5. **Why is that the core issue?** → **Even with query-time filtering via subagent, the comprehensive index must first be loaded - and at scale, the index itself becomes too large to load**

**The Ultimate Constraint:** You can't filter what you can't load. The index must be consumable by the subagent BEFORE intelligent filtering can happen.

---

### Technique 2: First Principles Thinking (Creative)

**Goal:** Strip away assumptions about how project indexing "should" work and rebuild from fundamental truths.

**Question:** What's the MINIMUM information an AI needs for architectural awareness?

**User's First Principles Reduction:**

> "It needs to understand the problem and understand code."

**BREAKTHROUGH INSIGHT:**

This reveals TWO distinct needs:
1. **Understand the problem** - USER INTENT and CONTEXT (what are they trying to do?)
2. **Understand code** - RELEVANT CODE for that specific problem

**Current Architecture Assumption (WRONG):**
- Build a comprehensive index of EVERYTHING
- Load entire index into AI
- AI filters for relevance

**First Principles Architecture (RIGHT):**
- Start with the PROBLEM (user's prompt/intent)
- Find RELEVANT code for that problem
- Only load what matters

**Key Realization:** The current approach assumes "index first, filter later." But first principles says "understand problem first, find relevant code second."

**Paradigm Shift:**
- FROM: "Here's everything in the codebase, now find what you need"
- TO: "Here's what you're trying to do, let me find the relevant parts"

**Analogy:**
- Current: Giving someone the entire library and saying "find the book you need"
- First Principles: Asking "what are you researching?" then handing them the 3 relevant books

---

**Critical Addition - Temporal Dimension:**

**User Insight:** "It needs to understand recent changes as often changes are what introduce bugs."

**PROFOUND REALIZATION:**

The AI needs THREE things, not two:
1. **Understand the problem** - User intent
2. **Understand the code** - Relevant code structure
3. **Understand what changed recently** - Temporal context

**Why This Changes Everything:**

**Fundamental truth about software development:**
- 80% of bugs come from recent changes
- Recent code is most likely to be relevant to current work
- Code that hasn't changed in 2 years is stable (probably not the problem)

**Current indexing problem:**
- Treats 10-year-old stable code the same as yesterday's changes
- No temporal weighting
- No recency awareness

**First Principles Solution with Temporal Awareness:**

**The "Recency Layer":**
- Recent changes (last 7 days) → HIGH PRIORITY, index fully
- Medium changes (last 30 days) → MEDIUM PRIORITY, index signatures
- Stable code (90+ days) → LOW PRIORITY, index names only
- Ancient code (1+ year unchanged) → MINIMAL, file tree only

**Implications:**
- For a 100k-file codebase, maybe only 200 files changed this month
- Index those 200 deeply, summarize the rest
- Dramatically reduces index size while capturing what matters most

**Query-time Intelligence:**
"fix the auth bug -i" →
1. Check recent changes to auth-related files
2. Load detailed index for recently-changed auth code
3. Lightweight reference to stable auth infrastructure

**Revolutionary Insight:** Time-based prioritization could solve the scale problem naturally!

---

**Critical Use Case - Explicit File References:**

**User Question:** "What happens if the user references files and doesn't just query a question?"

**Examples:**
```bash
@src/auth/login.py fix the bug in this file
Review changes in database.py and user.py
Refactor @components/Header.tsx
```

**KEY INSIGHT:** When users explicitly reference files, they're providing DIRECT CONTEXT. No guessing needed!

**This reveals FOUR types of relevance, not three:**

1. **Explicit Context** - User directly references files → HIGHEST PRIORITY
2. **Temporal Context** - Recent changes → HIGH PRIORITY
3. **Semantic Context** - Keywords in prompt match code → MEDIUM PRIORITY
4. **Structural Context** - Dependencies/relationships → LOWER PRIORITY

**First Principles Question This Raises:**

**If the user tells you exactly which files matter, why do you need a comprehensive index at all?**

**Possible answer:**
- Explicit files are the STARTING POINT
- But AI needs to understand their DEPENDENCIES
- "Fix bug in login.py" → Need to see what login.py calls, what calls it, types it uses, etc.

**New Architecture Implication - "Expansion from Seed":**

When user references specific files:
1. Load those files FULLY (explicit context)
2. Expand to DIRECT DEPENDENCIES (imports, callers, callees)
3. Add RECENT CHANGES to related files (temporal)
4. Skip everything else

**Example:**
```
User: "@auth/login.py fix the session timeout bug"

System loads:
- auth/login.py [EXPLICIT] - full detail
- auth/session.py [DEPENDENCY] - login.py imports it
- auth/middleware.py [CALLER] - calls login functions
- auth/config.py [RECENT + RELATED] - changed 2 days ago
- Skip: 9,995 other files
```

**Result:** Load maybe 5-10 files deeply instead of entire codebase!

**Breakthrough Realization:** User intent can be EXPLICIT (file references), IMPLICIT (prompt keywords), or TEMPORAL (recent changes). The system should leverage ALL THREE signals, with explicit being strongest.

---

### Technique 3: SCAMPER Method (Structured)

**Goal:** Systematically iterate on the existing indexer using seven creative lenses to generate concrete improvements.

**SCAMPER Framework:**
- **S**ubstitute - Replace components with alternatives
- **C**ombine - Merge features or data
- **A**dapt - Adjust for different contexts
- **M**odify - Change size, shape, attributes
- **P**ut to other uses - Repurpose existing features
- **E**liminate - Remove unnecessary parts
- **R**everse - Flip processes or assumptions

---

**S - SUBSTITUTE (Replace components):**

**Selected Ideas:**

✅ **Idea 1: Tiered Documentation Storage**
- Replace flat `d` section with `d_critical`, `d_standard`, `d_archive`
- Auto-classify based on filename patterns (README, ARCHITECTURE → critical)
- Load levels progressively based on need
- **Impact:** Massive size reduction for doc-heavy projects

✅ **Idea 3: Git Blame Metadata** ⭐
- Replace simple timestamps with rich git context
- Add: last-modified-by, commit message, PR number, branch
- Enable questions like "What changed in the auth PR?" or "Show me Bob's recent work"
- **Impact:** Transforms static snapshot into living development history
- **Benefit:** AI can understand not just WHAT changed but WHY and WHO

**Git Metadata Structure:**
```json
"f": {
  "src/auth.py": {
    "modified": "2025-10-29T14:32:00Z",
    "last_commit": "abc123",
    "commit_msg": "Fix session timeout bug",
    "author": "ryan",
    "pr": "#247",
    "lines_changed": 23
  }
}
```

---

**C - COMBINE (Merge features/data):**

✅ **Idea 4: Git History + Call Graph**
- Track which functions change together over time
- Identify architectural coupling patterns
- "These 5 functions always change together → they're a cohesive module"
- **Impact:** Surface hidden architectural boundaries

✅ **Idea 5: Risk Scoring (Size + Complexity + Recency)** ⭐
- Combine multiple signals into unified risk metric
- `risk = (file_size * cyclomatic_complexity * recency_weight) / test_coverage`
- Prioritize high-risk code in index
- **Impact:** AI focuses on the most likely problem areas first

✅ **Idea 6: Documentation-Code Proximity Linking**
- Auto-associate docs with related code
- `docs/auth.md` → linked to `src/auth/*` files
- Only load docs when their associated code is relevant
- **Impact:** Contextual documentation without bloat

---

**E - ELIMINATE (Remove unnecessary parts):**

✅ **Idea 9: Eliminate Duplicate Information** ⭐
- Current problem: Same function name appears in `f`, `g`, `d`
- Solution: Normalize to ID-based references
- Store each fact once, reference by pointer
- **Impact:** 30-40% compression without losing information

**Example transformation:**
```json
// BEFORE (redundant)
"f": {
  "auth.py": ["login:42:(user,pass):bool", ...]
},
"g": [["login", "validate_user"], ...]

// AFTER (normalized)
"symbols": {
  "s1": {"name": "login", "line": 42, "sig": "(user,pass):bool", "file": "auth.py"}
},
"f": {"auth.py": ["s1", ...]},
"g": [["s1", "s2"], ...]
```

---

**A - ADAPT (Adjust for different contexts):**

✅ **Idea 10: Project-Type Aware Indexing** ⭐
- Detect project type (monorepo, microservices, library, web app)
- Adapt what gets prioritized in index
- **Monorepo:** Separate indices per sub-project, cross-references
- **Microservices:** Emphasize API contracts, service boundaries
- **Library:** Focus on public API, minimize internal implementation
- **Web app:** Routes, components, state management first
- **Impact:** Right information for the right project type

---

**M - MODIFY (Change size, shape, attributes):**

✅ **Idea 12: Incremental Updates** ⭐⭐
- Stop regenerating entire index on every file change
- Update only changed file + direct dependencies
- Track change delta in git
- **Impact:** 100x faster for large codebases, real-time updates possible
- **Technical:** Hash-based change detection, dependency graph caching

✅ **Idea 13: Split Index Architecture** ⭐⭐⭐
- Core index: `PROJECT_INDEX.json` (lightweight lookup)
- Detail store: `PROJECT_INDEX.d/` directory with per-file or per-module details
- Load detail files lazily based on relevance
- **Impact:** Fundamentally solves the scale problem
- **Structure:**
```
PROJECT_INDEX.json          (5-10k tokens - always loaded)
PROJECT_INDEX.d/
  auth.json                 (detailed auth module index)
  database.json             (detailed database index)
  api.json                  (API layer details)
  ...
```

---

**P - PUT TO OTHER USES (Repurpose):**

✅ **Idea 14: Impact Analysis Tool**
- Repurpose call graph for "what breaks if I change this?"
- Show downstream dependencies before modifications
- "Changing this function affects 12 callers across 5 files"
- **Impact:** Reduces breaking changes, improves developer confidence
- **Use cases:**
  - Pre-commit impact check
  - Refactoring safety analysis
  - API deprecation planning

---

### Technique 4: Resource Constraints (Structured)

**Goal:** Force brutal prioritization by imposing extreme limits. Constraints breed innovation.

---

**Constraint 3: AI agent only has 5,000 tokens total context** ⭐

**The Challenge:** 5k tokens must cover:
- User's prompt (~200 tokens)
- Conversation history (~500 tokens)
- Index (~4,300 tokens maximum!)
- Response generation space

**This forces the question: What's the MINIMUM viable architectural awareness?**

**Solutions that emerge:**

**Solution A: Ultra-Compressed Symbol Table**
```json
{
  "symbols": {
    "auth": ["login:42", "logout:67", "validate:89"],
    "db": ["connect:23", "query:45", "close:78"],
    "api": ["get_user:12", "create:34"]
  },
  "recent": ["auth/login.py", "api/users.py"],
  "entry": ["main.py:run"]
}
```
Just names, line numbers, recency. Nothing else.
**Size:** ~500 bytes for 1000 functions

**Solution B: Query-Responsive Meta-Index**
Don't load ANY index by default. Instead:
- User: "fix auth bug -i"
- System: Searches for "auth" → identifies 3 files
- Returns mini-index of just those 3 files
- **Paradigm shift:** Index is GENERATED at query time, not pre-built

**Solution C: Hierarchical Zoom**
```json
{
  "L0": "5 modules: auth, db, api, ui, utils",
  "L1_auth": "7 files in auth/, 23 functions",
  "L2_auth_login": "Full detail for login.py"
}
```
AI loads L0 (tiny), asks for more detail as needed
User never sees the complexity

**KEY INSIGHT FROM CONSTRAINT:**

**With only 5k tokens, you CANNOT have comprehensive architectural awareness.**

This proves that the entire concept of "load everything" is fundamentally broken for large codebases.

**The only viable approach is:**
1. Start with minimal metadata (file tree, module names)
2. Use user intent to identify relevant subset
3. Load ONLY that subset in detail
4. Dynamically expand if needed

**This constraint reveals the truth: Split architecture (Idea 13) isn't just nice-to-have, it's ESSENTIAL for scale.**

{{technique_sessions}}

## Idea Categorization

### Immediate Opportunities

_Ideas ready to implement now - quick wins with clear benefit_

**1. Eliminate Duplicate Information (Idea 9)**
- Normalize function/class references to ID-based pointers
- Store each fact once, reference everywhere
- **Impact:** 30-40% compression immediately
- **Effort:** Medium (refactor storage format)
- **Risk:** Low (doesn't change functionality)

**2. Tiered Documentation Storage (Idea 1)**
- Split docs into `d_critical`, `d_standard`, `d_archive`
- Auto-classify by filename patterns (README, ARCHITECTURE → critical)
- Load only critical tier by default
- **Impact:** Solves the 83.7% doc bloat for this project
- **Effort:** Low (add classification logic)
- **Risk:** Low (docs are optional anyway)

**3. Git Blame Metadata (Idea 3)**
- Add commit message, author, PR number to file metadata
- Already using git - just extract more info
- **Impact:** Rich temporal context for debugging
- **Effort:** Low (git log parsing)
- **Risk:** Low (additive feature)

**4. Documentation-Code Proximity Linking (Idea 6)**
- Associate docs with their related code modules
- `docs/auth.md` → linked to `src/auth/*`
- **Impact:** Load docs only when code is relevant
- **Effort:** Low (pattern matching)
- **Risk:** Low (improves existing feature)

### Future Innovations

_Ideas requiring development/research - bigger architectural changes_

**5. Split Index Architecture (Idea 13)** ⭐⭐⭐ CRITICAL
- Core index: `PROJECT_INDEX.json` (lightweight)
- Detail store: `PROJECT_INDEX.d/` directory (per-module)
- Lazy load details based on relevance
- **Impact:** Fundamentally solves scale problem
- **Effort:** High (major architecture change)
- **Risk:** Medium (affects all index consumers)
- **Priority:** Should be next major version

**6. Incremental Updates (Idea 12)**
- Update only changed files + dependencies
- Hash-based change detection
- **Impact:** 100x faster for large codebases
- **Effort:** Medium-High (caching layer needed)
- **Risk:** Medium (must maintain consistency)

**7. Risk Scoring System (Idea 5)**
- Combine file size + complexity + recency + test coverage
- Prioritize high-risk files in index
- **Impact:** AI focuses on likely problem areas
- **Effort:** Medium (metrics extraction)
- **Risk:** Low (additive feature)

**8. Project-Type Aware Indexing (Idea 10)**
- Detect project type (monorepo, microservices, library, web app)
- Adapt indexing strategy per type
- **Impact:** Right information for right context
- **Effort:** Medium (detection + type-specific logic)
- **Risk:** Medium (needs tuning per type)

**9. Impact Analysis Tool (Idea 14)**
- Repurpose call graph for "what breaks if I change this?"
- Show downstream dependencies
- **Impact:** Safer refactoring, fewer breaks
- **Effort:** Low-Medium (leverage existing call graph)
- **Risk:** Low (read-only analysis)

**10. Git History + Call Graph Combo (Idea 4)**
- Track which functions change together over time
- Surface architectural coupling patterns
- **Impact:** Identify hidden module boundaries
- **Effort:** Medium (git history analysis)
- **Risk:** Low (analytical feature)

### Moonshots

_Ambitious, transformative concepts - require rethinking fundamentals_

**11. Query-Responsive Index Generation** ⭐⭐⭐ PARADIGM SHIFT
- No pre-built comprehensive index
- Generate mini-index at query time based on prompt
- "fix auth bug -i" → analyze only auth files dynamically
- **Impact:** Zero bloat, always relevant, infinite scale
- **Effort:** Very High (complete rewrite)
- **Risk:** High (unproven approach)
- **Research needed:** Performance, accuracy, edge cases

**12. Temporal/Recency-Based Architecture**
- Layer index by recency: hot (7 days), warm (30 days), cold (stable)
- Recent code gets full detail, ancient code minimal
- **Impact:** Natural prioritization aligned with development reality
- **Effort:** High (requires git integration, tiering logic)
- **Risk:** Medium (must handle all git scenarios)

**13. Hierarchical Zoom Levels**
- L0: Module overview (tiny)
- L1: File list per module
- L2: Full detail per file
- AI loads progressively as needed
- **Impact:** Solves 5k token constraint elegantly
- **Effort:** Very High (new query protocol)
- **Risk:** High (requires AI agent changes)

**14. Intent-First Architecture** (from First Principles)
- Understand problem → find relevant code → load details
- Not: load everything → filter for relevance
- Combines explicit file refs + temporal + semantic signals
- **Impact:** Fundamental paradigm shift
- **Effort:** Very High (complete reconceptualization)
- **Risk:** Very High (requires proving concept)

### Insights and Learnings

_Key realizations from the session_

**1. The Fundamental Constraint: "You can't filter what you can't load"**
- Root cause analysis revealed that even with smart filtering, if the comprehensive index exceeds context limits, the system fails BEFORE filtering begins
- This proved that split/lazy architecture isn't optional—it's mathematically necessary

**2. Three Dimensions of Relevance (not one)**
- **Explicit Context:** User directly references files → highest signal
- **Temporal Context:** Recent changes indicate active work areas → high probability relevance
- **Semantic Context:** Keywords in prompt match code → medium signal
- Current indexer only uses semantic (keywords), missing the other two powerful signals

**3. Documentation is 83.7% of the problem (for this project)**
- Analysis showed docs dominate the index, not code
- Tool designed for code-heavy projects breaks down with doc-heavy projects
- Reveals need for tiered/selective doc indexing

**4. Architectural Relevance is Contextual**
- What matters depends on: project type, user intent, development phase, team conventions
- No one-size-fits-all approach works at scale
- Need adaptive/query-responsive strategies

**5. Time is a Natural Filter**
- 80% of bugs come from recent changes
- Recency provides objective prioritization without predicting intent
- Stable code (unchanged for months) can be indexed minimally

**6. Paradigm Shift: Intent-First vs Index-First**
- Current: Build comprehensive index → Load → Filter → Use
- Better: Understand intent → Find relevant subset → Index → Use
- Reverses the flow to avoid building bloated comprehensive indices

**7. Split Architecture is Non-Negotiable for Scale**
- Lightweight core index (always loaded) + detailed modules (lazy-loaded)
- Proven essential by the 5k token constraint exercise
- Separates lookup/navigation from detailed analysis

## Action Planning

### Top 3 Priority Ideas

#### #1 Priority: Tiered Documentation Storage

- **Rationale:** Solves the immediate 83.7% documentation bloat problem for this project and any doc-heavy codebase. Quick win with massive impact. Low risk since documentation is already a secondary feature.

- **Next steps:**
  1. Add doc classification logic to `index_utils.py::extract_markdown_structure()`
  2. Define patterns for critical docs (README*, ARCHITECTURE*, CONTRIBUTING*, API*, docs/index*)
  3. Modify index format to use `d_critical`, `d_standard`, `d_archive` instead of flat `d`
  4. Update compression logic to prioritize/load only `d_critical` by default
  5. Add flag to include all tiers if needed (e.g., `-i-all-docs`)
  6. Test on this project (should drop from 12k to ~3k tokens)

- **Resources needed:**
  - Modify: `scripts/index_utils.py` (markdown extraction)
  - Modify: `scripts/project_index.py` (format and compression)
  - Update: index-analyzer agent to handle tiered format
  - Testing on multiple doc-heavy projects

- **Timeline:** 1-2 days for implementation, half day for testing

---

#### #2 Priority: Split Index Architecture

- **Rationale:** This is the foundational architecture change that enables scaling to truly large codebases (10k+ files). While higher effort, it unlocks all future enhancements and solves the scale problem permanently. Should be the next major version.

- **Next steps:**
  1. Design core index schema (file tree, function names, imports, git metadata - minimal)
  2. Design detail module format (per-file or per-module JSON files)
  3. Create `PROJECT_INDEX.d/` directory structure
  4. Implement lazy-loading mechanism in index-analyzer agent
  5. Add query-time relevance scoring (explicit + temporal + semantic)
  6. Implement "expansion from seed" - load file → load dependencies → load recent related
  7. Maintain backward compatibility with current single-file format
  8. Performance testing on large repos (5k-10k files)

- **Resources needed:**
  - Major refactor of `scripts/project_index.py`
  - New module: relevance scoring and lazy loading
  - Update: `agents/index-analyzer.md` for split index consumption
  - Update: hooks to handle split format
  - Testing across small/medium/large projects
  - Documentation updates

- **Timeline:** 1-2 weeks for core implementation, 1 week for testing and refinement

---

#### #3 Priority: Git Blame Metadata

- **Rationale:** Quick win that adds powerful temporal context. Enables understanding not just WHAT changed but WHY and WHO. Foundation for recency-based features. Low risk, high value.

- **Next steps:**
  1. Add git metadata extraction to `project_index.py::build_index()`
  2. Use `git log --format` to get: commit hash, author, date, message, PR number (if in message)
  3. Add `lines_changed` from `git diff --stat`
  4. Update index format to include git metadata per file
  5. Add to index-analyzer agent prompts: "Recent changes by [author] in [file]"
  6. Consider adding "show recent work by author" query capability
  7. Handle edge cases: new files, untracked files, non-git repos

- **Resources needed:**
  - Modify: `scripts/project_index.py` (git log parsing)
  - Add: Git metadata extraction utilities
  - Update: index format documentation
  - Update: index-analyzer agent to surface git context
  - Testing with various git histories

- **Timeline:** 1 day for implementation, half day for testing

## Reflection and Follow-up

### What Worked Well

**1. Five Whys Deep Dive**
- Starting with data analysis (the 83.7% finding) grounded the entire session in reality
- Each "why" layer revealed deeper architectural truths
- Reached bedrock: "You can't filter what you can't load"

**2. First Principles Thinking**
- Your insight "it needs to understand the problem and understand code" cut through complexity
- Adding temporal dimension (recent changes) was a game-changer
- Questioning explicit file references revealed the "expansion from seed" pattern

**3. SCAMPER Systematic Iteration**
- Generated 14 concrete, actionable ideas
- Mixing quick wins (tiered docs) with strategic changes (split architecture)
- All grounded in the root cause analysis

**4. Resource Constraints (5k token limit)**
- Proved split architecture is mathematically necessary, not just nice-to-have
- Made the abstract concrete

### Areas for Further Exploration

**1. Query-Responsive Index Generation (Moonshot #11)**
- How would performance compare to pre-built indices?
- What's the latency/accuracy tradeoff?
- Could this work with massive 100k+ file codebases?

**2. Risk Scoring Implementation Details**
- How to calculate complexity metrics efficiently?
- What weights for each factor (size, complexity, recency, coverage)?
- How to visualize risk scores for developers?

**3. Project Type Detection**
- How to reliably detect monorepo vs microservices vs library?
- What heuristics work across languages/frameworks?
- How to handle hybrid projects?

**4. Incremental Update Mechanism**
- Dependency graph invalidation strategies
- Hash-based change detection edge cases
- How to handle large refactorings that touch 1000+ files?

### Recommended Follow-up Techniques

**For implementation planning:**
- **Story Mapping:** Break down the top 3 priorities into development stories
- **Assumption Testing:** Validate that split architecture actually solves scale (prototype with a 10k file repo)
- **Technical Spike:** Build proof-of-concept for tiered docs to validate 83.7% → ~20% compression

**For future enhancements:**
- **Mind Mapping:** Visualize relationships between all 14 ideas (dependencies, synergies)
- **Reverse Engineering:** Study how other tools (ctags, LSP servers, Sourcegraph) handle scale
- **User Journey Mapping:** Map developer workflows to understand when they need what level of detail

### Questions That Emerged

**1. Performance Questions:**
- What's the actual performance of lazy-loading detail files vs loading comprehensive index?
- How much overhead does query-time relevance scoring add?
- Can incremental updates keep up with high-velocity teams (100+ commits/day)?

**2. UX Questions:**
- How do developers discover that tiered docs exist?
- When split architecture lazy-loads, should users see loading indicators?
- How to handle cases where the AI needs more context mid-conversation?

**3. Edge Cases:**
- How does this work for non-git projects?
- What about monorepos with 50+ sub-projects?
- How to handle generated code (should it be indexed at all)?

**4. Adoption Questions:**
- How to migrate existing users from single-file to split architecture?
- Should there be a flag to force old behavior?
- How to communicate the benefits without overwhelming users?

### Next Session Planning

- **Suggested topics:**
  - **Implementation Planning:** Detailed technical design for split index architecture
  - **Prototype Review:** After implementing tiered docs, analyze results and iterate
  - **Scale Testing:** Test with real large codebases (React, Linux kernel, Chromium)
  - **Integration Patterns:** How should other tools consume the new index format?

- **Recommended timeframe:**
  - After implementing Priority #1 (Tiered Docs) - 1 week out
  - Before starting Priority #2 (Split Architecture) - for detailed design session

- **Preparation needed:**
  - Implement and test tiered documentation storage
  - Gather performance metrics from current indexer on large repos
  - Collect user feedback on current pain points
  - Review how LSP (Language Server Protocol) handles similar problems

---

_Session facilitated using the BMAD CIS brainstorming framework_
