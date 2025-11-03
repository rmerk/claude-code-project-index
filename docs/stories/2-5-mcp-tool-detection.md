# Story 2.5: MCP Tool Detection

Status: ready-for-dev

## Story

As an AI agent,
I want to detect which MCP tools are available,
So that I can use live data sources when possible.

## Acceptance Criteria

1. Agent detects MCP Read, Grep, Git tools at runtime
2. Agent capability map stored (which MCP tools are available)
3. Agent logs MCP availability status when verbose flag used
4. Graceful behavior when MCP tools unavailable (use index only)
5. Documentation explains MCP integration benefits

## Tasks / Subtasks

- [ ] Implement MCP Tool Detection Module (AC: #1, #2)
  - [ ] Create `scripts/mcp_detector.py` module with MCP tool detection logic
  - [ ] Implement `detect_mcp_tools()` function to probe for Read, Grep, Git tools
  - [ ] Return capability map dict: `{"read": bool, "grep": bool, "git": bool}`
  - [ ] Handle detection failures gracefully (return False for unavailable tools)
  - [ ] Add comprehensive docstrings and type hints

- [ ] Integrate MCP Detection into Index-Analyzer Agent (AC: #1, #3, #4)
  - [ ] Modify `agents/index-analyzer.md` to import and use `mcp_detector.py`
  - [ ] Call `detect_mcp_tools()` at agent initialization
  - [ ] Store capability map as agent context variable
  - [ ] Log MCP availability status when verbose flag used
  - [ ] Gracefully fall back to index-only mode when MCP unavailable
  - [ ] Document MCP detection in agent initialization section

- [ ] Documentation and Configuration (AC: #5)
  - [ ] Update README with MCP integration benefits section
  - [ ] Explain how MCP tools enhance index functionality
  - [ ] Provide examples of hybrid index + MCP workflows
  - [ ] Document detection mechanism and capability map structure

- [ ] Testing (All ACs)
  - [ ] Unit tests for `detect_mcp_tools()` function
  - [ ] Test detection when all MCP tools available
  - [ ] Test detection when some MCP tools unavailable (partial availability)
  - [ ] Test detection when no MCP tools available (fallback mode)
  - [ ] Integration test: Agent initializes with MCP detection
  - [ ] Integration test: Agent logs MCP status in verbose mode
  - [ ] Test graceful degradation to index-only mode
  - [ ] Performance test: Detection completes in <100ms

## Dev Notes

### Architecture Alignment

**From Tech-Spec (tech-spec-epic-2.md):**

This story implements:
- **MCP Detector** (tech-spec line 69) - New module `scripts/mcp_detector.py`
- **Hybrid Query Router** (tech-spec line 70) - Enhanced index-analyzer agent initialization
- **Acceptance Criteria AC2.5.1-2.5.5** (tech-spec lines 545-549)

**MCP Detection Strategy:**

The detection mechanism probes for MCP tool availability at runtime without requiring explicit configuration. This enables agents to automatically adapt their query strategy based on available capabilities:

- **With MCP Tools**: Use index for structure/navigation + MCP for real-time data
- **Without MCP Tools**: Fall back to detail module loading from index

**MCP Tools to Detect:**
1. **Read Tool**: Load current file content (fresher than index)
2. **Grep Tool**: Live keyword search across codebase
3. **Git Tool**: Real-time git log, blame, diff operations

**Detection Approach:**
```python
def detect_mcp_tools() -> dict:
    """Detect available MCP tools."""
    capabilities = {
        "read": False,
        "grep": False,
        "git": False
    }

    # Probe for each tool (implementation-specific)
    # Return boolean map of availability

    return capabilities
```

**Integration Points:**
- **Foundation for Story 2.6**: Hybrid query strategy will consume this capability map
- **Foundation for Story 2.7**: Relevance engine will adapt based on MCP availability
- **Used by Index-Analyzer Agent**: Determines query routing strategy

### Learnings from Previous Story

**From Story 2-4-temporal-awareness-integration (Status: done)**

- **Module Creation Pattern Established**:
  - Create standalone module with single responsibility (`scripts/relevance.py` ✅)
  - Export main functions/classes for use by other components
  - Comprehensive docstrings with Args/Returns/Examples
  - Full test coverage with edge cases and performance validation
  - Use `unittest` framework with proper test isolation

- **Agent Integration Pattern**:
  - Import new module in `agents/index-analyzer.md`
  - Call module functions during agent initialization or query processing
  - Store results as agent context (capability map, scoring state, etc.)
  - Log decisions when verbose flag used
  - Graceful degradation when dependencies unavailable

- **Relevance Scoring Foundation** (from Story 2.4):
  - Multi-signal scoring with configurable weights implemented
  - Explicit file refs (10x), temporal recent (5x), temporal medium (2x), keyword match (1x)
  - Relevance engine ready for MCP hybrid extension in Story 2.6

- **Files Created in Story 2.4** (Reusable Patterns):
  - `scripts/relevance.py` - Standalone utility module with scoring logic
  - `scripts/test_relevance.py` - Comprehensive test suite (30 tests, 100% passing)
  - Pattern: Standalone utility module + test suite + agent integration

- **Performance Lessons**:
  - Detection/initialization should complete in <100ms
  - Avoid blocking operations during detection (use timeouts)
  - Cache detection results (don't re-probe on every query)
  - Log performance metrics in verbose mode

- **Configuration Pattern** (if needed):
  - `.project-index.json` can be extended with MCP-related settings
  - Example: `mcp_detection: {"enabled": true, "timeout_ms": 100}`
  - Provide sensible defaults, make behavior configurable

- **Testing Pattern to Follow**:
  - Use `unittest` with `unittest.mock` for MCP tool mocking
  - Test happy path + edge cases (partial availability, timeouts)
  - Performance validation with realistic scenarios
  - Integration tests with actual agent initialization

- **Error Handling Best Practices**:
  - Specific exception types (not bare except)
  - Graceful degradation when MCP tools unavailable
  - Default to False for undetectable tools (safe fallback)
  - Informative logging for debugging (verbose mode)

**New Capabilities from Story 2.4**:
- Relevance scoring engine ready for hybrid queries
- Temporal awareness integrated into index-analyzer agent
- Multi-signal scoring established: explicit refs, temporal, keywords
- Agent now has foundation for MCP-aware query routing

**Key Insight**: MCP detection enables hybrid intelligence - agents can combine pre-computed index structure (fast navigation) with real-time MCP data (fresh content). Detection must be fast (<100ms) and graceful (fallback to index-only).

[Source: stories/2-4-temporal-awareness-integration.md#Dev-Agent-Record]

### Project Structure Notes

**Files to Create:**
- `scripts/mcp_detector.py` - MCP tool detection module
  - `detect_mcp_tools() -> Dict[str, bool]` - Runtime detection function
  - Probe for Read, Grep, Git MCP tools
  - Return capability map: `{"read": bool, "grep": bool, "git": bool}`
  - Comprehensive docstrings and type hints

- `scripts/test_mcp_detector.py` - Test suite for MCP detection
  - Unit tests for detection logic (all available, partial, none)
  - Test timeout handling and graceful degradation
  - Performance tests (<100ms detection time)
  - Integration tests with mocked MCP environment

**Files to Modify:**
- `agents/index-analyzer.md` - Enhanced with MCP detection
  - Import `mcp_detector.py` module
  - Call `detect_mcp_tools()` at agent initialization
  - Store capability map as agent context variable
  - Log MCP availability in verbose mode
  - Document detection mechanism

- `README.md` - Documentation updates
  - Explain MCP integration benefits
  - Provide hybrid workflow examples (index + MCP)
  - Document detection mechanism
  - Clarify fallback behavior when MCP unavailable

**Dependencies:**
- Python stdlib only (no new external dependencies)
- Optional MCP tools (Read, Grep, Git) - detected at runtime
- No changes to core index generation

**Integration Points:**
- Index-analyzer agent: Consumes capability map for query routing decisions
- Future Story 2.6: Hybrid query strategy will use this detection
- Future Story 2.7: Relevance engine will adapt based on MCP availability
- MCP tools: Read, Grep, Git (if available in Claude Code environment)

**Data Flow:**

```
1. Agent initialization
2. Call detect_mcp_tools()
3. Probe for Read, Grep, Git tools
4. Return capability map: {"read": bool, "grep": bool, "git": bool}
5. Store in agent context
6. Log availability (if verbose)
7. Agent uses capability map for query routing
```

### References

- [Tech-Spec: MCP Detector](docs/tech-spec-epic-2.md#services-and-modules) - Line 69
- [Tech-Spec: MCP Integration Architecture](docs/tech-spec-epic-2.md#system-architecture-alignment) - Lines 48-52
- [Tech-Spec: Acceptance Criteria AC2.5.1-2.5.5](docs/tech-spec-epic-2.md#acceptance-criteria-authoritative) - Lines 545-549
- [Epics: Story 2.5](docs/epics.md#story-25-mcp-tool-detection) - Lines 264-278
- [PRD: Hybrid Intelligence](docs/PRD.md#user-journeys) - Agent-driven adaptive index usage
- [Story 2.4: Temporal Awareness Integration](docs/stories/2-4-temporal-awareness-integration.md) - Foundation for hybrid query routing, established module creation pattern
- [Architecture: Analysis Layer](docs/architecture.md#analysis-layer-intelligence) - Enhanced with MCP-aware intelligence

## Dev Agent Record

### Context Reference

- [Story Context XML](2-5-mcp-tool-detection.context.xml)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

**2025-11-03** - Story 2.5 Created
- Created story file for MCP tool detection implementation
- Extracted requirements from epics.md (Story 2.5, lines 264-278)
- Defined 5 acceptance criteria with corresponding tasks
- Incorporated learnings from Story 2.4: module creation pattern, agent integration, performance requirements
- Referenced tech-spec for MCP detection architecture and capability map structure
- Story status: backlog → drafted
