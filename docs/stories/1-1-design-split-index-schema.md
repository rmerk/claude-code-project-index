# Story 1.1: Design Split Index Schema

Status: ready-for-dev

## Story

As a developer,
I want a well-defined schema for core and detail index formats,
So that the split architecture has a solid foundation and clear contracts.

## Acceptance Criteria

1. Core index schema documented (file tree, function signatures, imports, git metadata structure)
2. Detail module schema documented (per-module detailed function/class info)
3. Schema includes version field for future compatibility
4. JSON examples provided for both core and detail formats
5. Schema supports all existing index features (functions, classes, call graph, docs)

## Tasks / Subtasks

- [ ] Define Core Index Schema (AC: #1, #3)
  - [ ] Document tree structure format (compact ASCII representation)
  - [ ] Document function/class signature format (lightweight, names + line numbers only)
  - [ ] Document imports structure
  - [ ] Document git metadata fields (commit hash, author, date, PR number placeholder)
  - [ ] Add version field (e.g., "2.0-split")
  - [ ] Document module reference structure (module_id → PROJECT_INDEX.d/ path mapping)

- [ ] Define Detail Module Schema (AC: #2, #3)
  - [ ] Document per-file detailed structure (full function signatures with params/returns/calls)
  - [ ] Document class structure with methods
  - [ ] Document local call graph format (within-module edges)
  - [ ] Document documentation tiers placeholders (d_standard, d_archive for Epic 2)
  - [ ] Add module_id and version fields

- [ ] Create JSON Schema Examples (AC: #4)
  - [ ] Provide example core index JSON (PROJECT_INDEX.json)
  - [ ] Provide example detail module JSON (PROJECT_INDEX.d/auth.json)
  - [ ] Include realistic data (auth module with login/session functions)
  - [ ] Show module reference links between core and detail

- [ ] Verify Feature Completeness (AC: #5)
  - [ ] Map all existing single-file index features to split format
  - [ ] Verify functions and classes are preserved (signatures in core, full in details)
  - [ ] Verify call graph is preserved (global in core, local in details)
  - [ ] Verify documentation map is preserved (critical in core, others in details)
  - [ ] Document what goes in core vs. what goes in details (clear separation)

- [ ] Create Schema Documentation File (AC: #1, #2)
  - [ ] Write `docs/split-index-schema.md` with complete schema specification
  - [ ] Include rationale for core vs. detail separation
  - [ ] Document size targets (core ≤100KB for 10,000 files)
  - [ ] Add migration notes (how legacy format maps to split format)

## Dev Notes

### Architecture Alignment

**From Tech-Spec (tech-spec-epic-1.md):**

This story implements the foundational schema definition that all subsequent stories in Epic 1 depend on. The schema must balance completeness (supporting all existing features) with performance (keeping core index under 100KB for large projects).

**Core Index Contents:**
- Directory tree (compact ASCII format - inherited from existing system)
- Function/class signatures (lightweight: name + line number only, no parameters or bodies)
- Imports (file-level dependencies)
- Git metadata placeholders (will be populated in Epic 2, Story 2.3)
- Module references (mapping to PROJECT_INDEX.d/ files)
- Critical documentation only (README*, ARCHITECTURE*, API*)
- Global call graph (cross-module function call edges)
- Version field: "2.0-split"

**Detail Module Contents:**
- Full function signatures (name, line, parameters, return type, calls, docstring)
- Complete class definitions (methods, inheritance)
- Local call graph (within-module edges)
- Documentation tiers (d_standard, d_archive - infrastructure for Epic 2, Story 2.2)
- Module metadata (module_id, file list, modified date)
- Version field: "2.0-split"

**Key Principle:** Core index provides "fast navigation and structure," detail modules provide "deep implementation context."

**Module Organization Strategy (from Tech-Spec):**
- Group files by top-level directory (e.g., `src/auth/` → `PROJECT_INDEX.d/auth.json`)
- Flat files go into `PROJECT_INDEX.d/root.json`
- Configurable depth for monorepos (default: depth 1)

### Project Structure Notes

**Target Files for Schema Documentation:**
- Primary: `docs/split-index-schema.md` (new file to create)
- Examples embedded in tech-spec: `docs/tech-spec-epic-1.md` (lines 70-130) - use as reference
- Existing single-file format reference: `PROJECT_INDEX.json` (current format to preserve)

**Schema Validation Approach:**
No formal JSON Schema validation initially - document contracts clearly in markdown. Future story could add programmatic validation if needed.

**Size Budget Constraints (from NFR001, NFR002):**
- Core index: ≤100KB (~25,000 tokens) for 10,000 file projects
- This requires aggressive optimization:
  - Tree structure: Compact ASCII (inherited, already optimal)
  - Signatures: Name + line only (no params/docs)
  - Call graph: Store edges only, not adjacency lists
  - Docs: Critical tier only in core

**Backward Compatibility Note:**
- Legacy format (version "1.0" or no version field) remains supported
- Split format uses version "2.0-split"
- Version field enables future format evolution

### Learnings from Previous Story

First story in epic - no predecessor context.

### References

- [Tech-Spec: Data Models and Contracts](docs/tech-spec-epic-1.md#data-models-and-contracts) - Lines 68-149
- [Tech-Spec: Module Reference Contract](docs/tech-spec-epic-1.md#module-reference-contract) - Lines 132-147
- [Architecture: Data Architecture](docs/architecture.md#data-architecture) - Current single-file format reference
- [PRD: FR004, FR005](docs/PRD.md#functional-requirements) - Requirements for core and detail indices
- [Epics: Story 1.1](docs/epics.md#story-11-design-split-index-schema) - Lines 44-58

## Dev Agent Record

### Context Reference

- [Story Context XML](1-1-design-split-index-schema.context.xml)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
