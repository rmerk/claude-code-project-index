# Spike: MCP Server Implementation for Project Index

**Date**: 2025-11-03
**Author**: Ryan (with PM John)
**Epic**: Epic 2 - Enhanced Intelligence & Developer Tools
**Stories**: 2.10 (MCP Server Implementation), 2.11 (MCP Server Auto-Update)
**Status**: Completed

---

## Executive Summary

This spike investigated using the `mcp-builder` Claude Code skill to implement an MCP (Model Context Protocol) server for the project index. The spike successfully created a proof-of-concept MCP server with 4 core tools, validated the approach, and identified critical architectural decisions and dependencies required for Stories 2.10 and 2.11.

**Key Findings**:
- ✅ mcp-builder provides comprehensive guidance for MCP server development
- ✅ FastMCP (Python SDK) is well-suited for our use case
- ⚠️ **CRITICAL**: First external dependency would be introduced (breaks stdlib-only constraint)
- ✅ POC demonstrates viability of exposing index functionality as MCP tools
- ⚠️ Story 2.10 and 2.11 need significant expansion to cover full implementation

---

## What is MCP?

**Model Context Protocol (MCP)** is a protocol that enables AI agents to interact with external services and data sources through well-defined tools. Key concepts:

- **MCP Server**: Exposes tools that AI agents can invoke
- **Tools**: Executable functions with input schemas and descriptions
- **Transport**: stdio (local), HTTP (remote), or SSE (streaming)
- **Resources**: Static data endpoints (optional)
- **Prompts**: Pre-defined prompts for common tasks (optional)

---

## What is mcp-builder?

`mcp-builder` is a Claude Code skill installed in this project at `.claude/skills/mcp-builder/` that provides:

### Phase 1: Deep Research and Planning
- Agent-centric design principles
- MCP protocol documentation
- Framework documentation (Python FastMCP or Node TypeScript SDK)
- API documentation study
- Implementation planning

### Phase 2: Implementation
- Project structure setup
- Shared utilities and helpers
- Systematic tool implementation with Pydantic (Python) or Zod (TypeScript) validation
- Language-specific best practices

### Phase 3: Review and Refine
- Code quality review (DRY, composability, consistency)
- Testing and building
- Quality checklist validation

### Phase 4: Create Evaluations
- Realistic, complex evaluation questions
- Read-only, verifiable test scenarios
- XML-based evaluation format

---

## Proof-of-Concept Implementation

### Created File
`project_index_mcp.py` - MCP server exposing project index functionality

### Implemented Tools

1. **`project_index_load_core`**
   - Load the core PROJECT_INDEX.json
   - Returns file tree, module references, stats
   - Supports JSON and Markdown output

2. **`project_index_load_module`**
   - Lazy-load specific detail module
   - Returns full function/class info for module
   - Supports JSON and Markdown output

3. **`project_index_search_files`**
   - Search for files by path pattern
   - Supports wildcards and partial matches
   - Paginated results (limit/offset)

4. **`project_index_get_file_info`**
   - Get detailed info about specific file
   - Returns functions, imports, git metadata
   - Supports JSON and Markdown output

### Technical Approach

- **Framework**: FastMCP from MCP Python SDK
- **Validation**: Pydantic v2 models with Field constraints
- **Error Handling**: Consistent error formatting with actionable messages
- **Response Formats**: JSON (machine-readable) and Markdown (human-readable)
- **Tool Annotations**: Proper hints (readOnlyHint, idempotentHint, etc.)

### Code Quality Features

✅ **DRY Principle**: Shared utilities (`_load_json_file`, `_handle_error`, `_format_core_index_markdown`)
✅ **Type Hints**: Full type annotations throughout
✅ **Pydantic Validation**: All inputs validated with constraints
✅ **Async/Await**: All tool functions use async
✅ **Error Handling**: Comprehensive error handling with clear messages
✅ **Documentation**: Comprehensive docstrings with examples
✅ **Best Practices**: Follows mcp-builder Python implementation guide

---

## Key Findings

### 1. External Dependency Required

**Critical Architectural Decision**: This is the first external dependency for the project.

**Current State**:
- Project uses Python 3.12+ stdlib only (NO external dependencies)
- No requirements.txt, pyproject.toml, or setup.py exists
- Epic 1 and all current functionality: pure stdlib

**Required for MCP Server**:
```bash
pip install mcp
# OR
pip install git+https://github.com/modelcontextprotocol/python-sdk.git
```

**Dependencies Introduced**:
- `mcp` (MCP Python SDK)
- `pydantic` (already required by MCP SDK)
- `httpx` (for async HTTP if needed, optional)

**Decision Required**:
- Accept first external dependency for MCP functionality?
- Create requirements.txt or pyproject.toml?
- Document installation instructions?
- Consider optional dependency (MCP server as optional feature)?

### 2. mcp-builder Skill is Highly Valuable

**What It Provides**:
- Comprehensive 4-phase development process
- Language-specific implementation guides (Python/TypeScript)
- Best practices for tool design, naming, error handling
- Evaluation framework for testing
- Complete working examples

**Benefits for Stories 2.10 & 2.11**:
- Reduces implementation time (clear patterns and examples)
- Ensures best practices followed (agent-centric design)
- Provides quality checklists (validation before completion)
- Evaluation framework (comprehensive testing)

**Recommendation**: Use mcp-builder skill for Story 2.10 implementation.

### 3. Tool Design Insights

**Agent-Centric Design Principles** (from mcp-builder):

1. **Build for Workflows, Not Just API Endpoints**
   - ✅ Our tools enable complete workflows (load core → search → load module)
   - ✅ Tools compose naturally (search finds files, get_file_info provides details)

2. **Optimize for Limited Context**
   - ✅ Core index is lightweight (<100KB)
   - ✅ Lazy-loading detail modules on demand
   - ✅ Markdown format provides concise summaries
   - ⚠️ Need to implement CHARACTER_LIMIT enforcement (25K chars)

3. **Actionable Error Messages**
   - ✅ Errors suggest next steps ("Please check the path is correct")
   - ⚠️ Could improve with more specific guidance

4. **Natural Task Subdivisions**
   - ✅ Tool names reflect natural actions (load, search, get)
   - ✅ Consistent naming (project_index_* prefix)

### 4. Integration with Existing System

**Works Well With**:
- Split index architecture (Epic 1)
- Lazy-loading design
- Core/detail separation

**Natural Integration Points**:
- `scripts/loader.py` - Use existing load_detail_module logic
- `scripts/project_index.py` - Could expose generate_index as MCP tool
- `agents/index-analyzer.md` - Agent could use MCP tools instead of direct file reads

**Potential Enhancement**:
- Hybrid approach: MCP server can use same utilities as direct indexing

### 5. Testing & Validation

**mcp-builder Evaluation Framework**:
- Create 10 complex, realistic evaluation questions
- Questions must be read-only, independent, verifiable
- XML format for evaluation results

**Example Questions for Our MCP Server**:
1. "What module contains the most Python functions?"
2. "Which files in the scripts module were modified in the last 30 days?"
3. "Find all files that import 'pathlib' and list their function signatures"

**Recommendation**: Implement evaluation suite as part of Story 2.10.

### 6. Transport Options

**Three Transport Modes**:
1. **stdio** (default): Best for local CLI tools, Claude Desktop integration
2. **HTTP**: Best for remote access, multi-client scenarios
3. **SSE**: Best for real-time updates, streaming

**Recommendation**: Start with stdio transport (simplest, matches local use case).

---

## Stories 2.10 & 2.11 Expansion Required

### Current State

**Story 2.10** (from epics.md):
```
Story 2.10: MCP Server Implementation
[Not fully defined in epics.md - just listed in sprint-status.yaml]
```

**Story 2.11** (from epics.md):
```
Story 2.11: MCP Server Auto-Update
[Not fully defined in epics.md - just listed in sprint-status.yaml]
```

### Required Expansion

#### Story 2.10: MCP Server Implementation

**Needs to Define**:

1. **Scope**: Which tools to implement?
   - Core tools (POC has 4)
   - Advanced tools (impact analysis, incremental updates)
   - Admin tools (regenerate index, validate integrity)

2. **Dependency Management**:
   - How to handle first external dependency?
   - Installation instructions
   - Optional vs required?
   - Requirements.txt or pyproject.toml?

3. **Integration Points**:
   - How does MCP server relate to existing scripts/?
   - Shared utilities or duplicate logic?
   - Can existing agents use MCP tools?

4. **Configuration**:
   - How to configure MCP server (index paths, etc.)?
   - Environment variables?
   - Config file integration?

5. **Testing Strategy**:
   - Evaluation suite (mcp-builder Phase 4)
   - Unit tests for tools
   - Integration tests with Claude Code

6. **Documentation**:
   - How to install MCP SDK
   - How to run MCP server
   - How to use tools from Claude Code
   - Tool reference documentation

#### Story 2.11: MCP Server Auto-Update

**Needs to Define**:

1. **Auto-Update Mechanism**:
   - Watch for PROJECT_INDEX.json changes?
   - Reload modules on demand?
   - Notify clients of changes (MCP notification protocol)?

2. **Integration with Incremental Updates** (Story 2.9):
   - Does auto-update trigger incremental regeneration?
   - Or just reload existing index?

3. **Performance Considerations**:
   - File watching overhead
   - Reload frequency
   - Cache invalidation

4. **Configuration**:
   - Enable/disable auto-update
   - Polling interval
   - Notification preferences

**Critical Questions**:
- Is Story 2.11 actually needed for MVP?
- Could be deferred to later epic?
- MCP servers typically don't auto-reload - restart required

---

## Architectural Decisions Required

### Decision 1: Accept External Dependency?

**Options**:

**A) Accept MCP SDK as First External Dependency**
- ✅ Enables MCP server functionality (major value)
- ✅ MCP SDK is well-maintained by Anthropic
- ⚠️ Breaks stdlib-only constraint from Epic 1
- ⚠️ Requires dependency management (requirements.txt)

**B) Keep MCP Server as Optional/Separate Package**
- ✅ Core indexer remains stdlib-only
- ✅ MCP server is separate optional component
- ⚠️ More complex project structure
- ⚠️ Documentation needs to explain optionality

**C) Defer MCP Server to Future Epic**
- ✅ Maintains current stdlib-only approach
- ⚠️ Misses opportunity for MCP integration
- ⚠️ Delays value delivery

**Recommendation**: **Option A** - Accept external dependency for MCP functionality
- MCP integration is a major value-add
- Python ecosystem expects dependency management
- Time to add requirements.txt anyway (mature project)

### Decision 2: Tool Scope for Story 2.10?

**Minimal Scope** (POC-based):
- 4 core tools (load core, load module, search files, get file info)
- Basic error handling
- JSON/Markdown outputs
- stdio transport only

**Extended Scope**:
- Add impact analysis tool (leverages Story 2.8)
- Add git metadata query tools (leverages Story 2.3)
- Add incremental update trigger tool (leverages Story 2.9)
- Add validation tool (integrity checks)

**Recommendation**: **Minimal Scope for Story 2.10**
- Get MCP server working with core functionality
- Extended tools can be Story 2.12+ in future iterations
- Focus on quality over quantity

### Decision 3: Story 2.11 - Keep or Defer?

**Rationale to Defer**:
- MCP servers typically don't auto-reload (restart pattern)
- Adds complexity without major value
- Incremental updates (Story 2.9) already address fast regeneration
- Could be added later if users request it

**Recommendation**: **Defer Story 2.11 to backlog**
- Remove from Epic 2 scope
- Focus Epic 2 on Stories 2.1-2.10
- Revisit in future epic if user demand exists

---

## Impact on Tech Spec

### Changes Required to tech-spec-epic-2.md

1. **Dependencies Section** (NEW):
   ```
   External Dependencies (NEW in Epic 2):
   - mcp (MCP Python SDK) - Required for Story 2.10
   - pydantic (via MCP SDK) - Input validation for MCP tools
   ```

2. **Story 2.10 Section** (EXPAND):
   - Full tool catalog
   - Implementation approach using mcp-builder
   - Installation and configuration
   - Testing strategy with evaluation framework

3. **Story 2.11 Section** (UPDATE):
   - Mark as DEFERRED
   - Rationale for deferral
   - Move to backlog

4. **Architecture Diagram** (UPDATE):
   - Add MCP Server layer
   - Show integration with existing indexer
   - Show MCP client (Claude Code) interaction

---

## Recommendations

### For Story 2.10 Implementation

1. **Use mcp-builder skill throughout implementation**
   - Follow 4-phase process
   - Use Python implementation guide
   - Create evaluation suite (Phase 4)

2. **Start with minimal tool set**
   - 4 core tools from POC
   - Focus on quality and testing
   - Extend in future stories if needed

3. **Create proper dependency management**
   - Add requirements.txt
   - Document installation process
   - Consider pyproject.toml for modern Python packaging

4. **Leverage existing code**
   - Import and use `scripts/loader.py`
   - Import and use `scripts/project_index.py`
   - Don't duplicate logic - compose utilities

5. **Implement comprehensive testing**
   - Unit tests for each tool
   - Evaluation suite (10 questions minimum)
   - Integration test with Claude Code

### For Story 2.11

**Recommendation: DEFER to backlog**
- Not essential for Epic 2 MVP
- Adds complexity without proportional value
- Can be added later if user demand exists
- Focus resources on Stories 2.1-2.10

### For Epic 2 Overall

1. **Update epics.md**
   - Fully define Story 2.10 with POC insights
   - Remove or mark Story 2.11 as deferred
   - Add new stories if needed (e.g., 2.12: Extended MCP Tools)

2. **Update tech-spec-epic-2.md**
   - Add dependencies section
   - Expand MCP server architecture
   - Update integration points
   - Add testing strategy

3. **Create requirements.txt**
   - Start with clean dependency list
   - Use specific versions for reproducibility
   - Document why each dependency exists

---

## Next Steps

1. ✅ Complete spike documentation (this file)
2. ⬜ Expand Story 2.10 in epics.md
3. ⬜ Update Story 2.11 in epics.md (mark deferred)
4. ⬜ Update tech-spec-epic-2.md with MCP architecture
5. ⬜ Create requirements.txt with MCP SDK
6. ⬜ Review and approve architectural decisions with stakeholders

---

## Appendix: MCP Server POC Code Structure

```
project_index_mcp.py (496 lines)
├── Imports (FastMCP, Pydantic, stdlib)
├── Constants (CHARACTER_LIMIT, paths)
├── Enums (ResponseFormat)
├── Pydantic Models (4 input models)
│   ├── LoadCoreIndexInput
│   ├── LoadModuleInput
│   ├── SearchFilesInput
│   └── GetFileInfoInput
├── Shared Utilities (3 functions)
│   ├── _load_json_file
│   ├── _format_core_index_markdown
│   └── _handle_error
└── Tools (4 MCP tools)
    ├── @mcp.tool project_index_load_core
    ├── @mcp.tool project_index_load_module
    ├── @mcp.tool project_index_search_files
    └── @mcp.tool project_index_get_file_info
```

**Lines of Code**: 496 (including docstrings and type hints)
**Functions**: 4 tools + 3 utilities = 7 total
**Pydantic Models**: 4 input validation models
**External Dependencies**: mcp, pydantic

---

## References

- mcp-builder skill: `.claude/skills/mcp-builder/SKILL.md`
- Python implementation guide: `.claude/skills/mcp-builder/reference/python_mcp_server.md`
- MCP best practices: `.claude/skills/mcp-builder/reference/mcp_best_practices.md`
- POC code: `project_index_mcp.py`
- MCP protocol: https://modelcontextprotocol.io/
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
