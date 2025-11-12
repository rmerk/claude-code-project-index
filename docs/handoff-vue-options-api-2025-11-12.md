# Developer Handoff: Vue Options API Parsing Enhancement

**From**: Winston (Architect Agent)
**To**: Developer Agent (DEV)
**Date**: 2025-11-12
**Epic**: Enhanced Intelligence & Developer Tools (Epic 2 Extension)
**Story**: 2.11 - Vue Options API Method Extraction

---

## Executive Summary

Complete architectural design for Vue Options API parsing enhancement ready for implementation. This completes the Vue parsing foundation started in session 2025-11-12, increasing coverage from 27% → ≥90%.

---

## What's Been Completed (Architecture Phase)

✅ **Technical Specification** - `docs/tech-spec-vue-options-api.md`
- Complete implementation guide (3,500+ words)
- Hour-by-hour roadmap
- All parsing patterns defined
- Integration points identified
- Edge cases documented

✅ **User Story** - `docs/stories/2-11-vue-options-api-parsing.md`
- 10 Acceptance Criteria
- Detailed task breakdown (8 sections, 50+ subtasks)
- Test strategy defined
- Success metrics specified

✅ **Code Analysis**
- Existing Vue parser analyzed (`index_utils.py:1187-1262`)
- JavaScript parser patterns reviewed
- Integration points identified (line 1248)
- Brace counting algorithm verified (enum parser pattern)

---

## What Needs to Be Done (Implementation Phase)

### Primary Deliverable
**New Function**: `extract_options_api_methods()` in `scripts/index_utils.py`

**Estimated Effort**: 2-3 hours
- Hour 1: Core method extraction
- Hour 2: Lifecycle hooks + computed properties
- Hour 3: Testing + validation

### Files to Modify
1. **`scripts/index_utils.py`**
   - Add `extract_options_api_methods()` (~150 lines, insert after line 1262)
   - Modify `extract_vue_signatures()` integration (~15 lines, line 1248)

2. **`scripts/test_vue_options_api.py`** (new file)
   - Comprehensive unit tests (~300 lines)

3. **Documentation Updates**
   - `docs/session-2025-11-12-status.md` - mark Options API complete
   - `docs/asure-project-test-report.md` - update coverage metrics

---

## Implementation Approach

### Step 1: Create Core Parser Function
```python
def extract_options_api_methods(script_content: str, all_functions: Set[str]) -> Dict[str, Dict]:
    """
    Extract methods from Vue Options API export default block.

    See tech spec section 2.2 for complete signature and behavior.
    """
    # 1. Extract export default { ... } block
    # 2. Parse methods: { ... }
    # 3. Parse lifecycle hooks
    # 4. Parse computed: { ... }
    # 5. Parse watch: { ... }
    # 6. Return unified function dict with category metadata
```

**Reference Implementation**: Tech spec sections 3.1-3.3 (parsing patterns)

### Step 2: Integration Point
**File**: `scripts/index_utils.py`
**Line**: 1248 (inside `extract_vue_signatures()`)

```python
# CURRENT (line 1248):
if script_content and script_content.strip():
    js_result = extract_javascript_signatures(script_content)
    # Merge results...

# ENHANCED (add after js_result):
    if result['vue_api'] == 'options':
        all_functions = set(js_result.get('functions', {}).keys())
        options_methods = extract_options_api_methods(script_content, all_functions)

        # Merge Options API methods
        for method_name, method_info in options_methods.items():
            if method_name not in js_result['functions']:
                js_result['functions'][method_name] = method_info
```

### Step 3: Testing Strategy
**Create**: `scripts/test_vue_options_api.py`

**Test Cases** (from tech spec section 6.1):
1. Methods with shorthand syntax
2. Lifecycle hooks extraction
3. Computed properties extraction
4. Nested braces handling
5. Mixed API styles

**Integration Test**: Run on Asure project
```bash
cd /Users/rchoi/Developer/asure/asure.ptm.portal.web.ui.new
python /Users/rchoi/Developer/claude-code-project-index/scripts/project_index.py --verbose
# Expect: 220+ Vue files parsed (up from 65)
```

---

## Key Technical Details

### Parsing Patterns (from tech spec section 3.1)

**1. Export Default Block**
```python
export_default_pattern = r'export\s+default\s*\{(.*)\}\s*$'
```

**2. Methods Object**
```python
methods_pattern = r'methods\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
```

**3. Brace Counting** (handle nested braces)
```python
brace_count = 1
for i in range(start_pos, len(content)):
    if content[i] == '{': brace_count += 1
    elif content[i] == '}': brace_count -= 1
    if brace_count == 0: break
```

**Reference**: Enum parser pattern (`index_utils.py:640-660`)

### Data Model Enhancement

**Add `category` field** to function metadata:
```python
{
    'handleClick': {
        'line': 45,
        'params': ['event'],
        'category': 'methods',  # NEW: 'methods' | 'computed' | 'lifecycle' | 'watch'
        'calls': ['submitForm']
    }
}
```

**Backward Compatible**: Existing parsers ignore category field.

---

## Test Project Details

**Location**: `/Users/rchoi/Developer/asure/asure.ptm.portal.web.ui.new`

**Current State**:
- 777 tracked files
- 246 Vue files total
- 65 Vue files parsed (27% coverage - Composition API)
- 181 Vue files NOT parsed (73% - Options API)

**Target State**:
- 220+ Vue files parsed (≥90% coverage)
- All Options API files fully indexed

**Validation**:
```bash
# Before:
Languages with full parsing: 65 Vue files (with signatures)

# After:
Languages with full parsing: 220+ Vue files (with signatures)
```

---

## Acceptance Criteria (Story 2.11)

Must complete ALL 10 ACs before marking story DONE:

1. ✅ Extract methods from `methods: { ... }`
2. ✅ Extract lifecycle hooks (created, mounted, etc.)
3. ✅ Extract computed properties
4. ✅ Extract watchers
5. ✅ Handle nested braces correctly
6. ✅ Categorize methods by type
7. ✅ Coverage: 27% → ≥90%
8. ✅ Performance: <5ms overhead per file
9. ✅ Backward compatible (Composition API still works)
10. ✅ Call graph integration

---

## Edge Cases to Handle

**From Tech Spec Section 5**:

1. **Mixed API styles**: Component with `setup()` + `methods`
   - Extract both, categorize appropriately

2. **Arrow function methods**: `methodName: (params) => {}`
   - Add pattern: `r'(\w+)\s*:\s*\([^)]*\)\s*=>'`

3. **Async methods**: `async methodName() {}`
   - Pattern: `r'async\s+(\w+)\s*\('`

4. **Deeply nested braces**: if/for/while inside methods
   - Use brace counting algorithm

5. **Empty objects**: `methods: {}`
   - Return empty dict, no error

---

## Success Metrics

### Quantitative
- **Coverage**: 27% → ≥90% Vue files
- **File count**: 65 → 220+ Vue files with signatures
- **Performance**: <5ms per file overhead
- **Test coverage**: 100% for new code

### Qualitative
- ✅ All 181 Options API files from Asure project parsed
- ✅ No regressions in Composition API parsing
- ✅ Incremental updates work correctly
- ✅ Call graph includes Options API methods

---

## Documentation References

**Primary References** (must read before coding):
1. **Tech Spec**: `docs/tech-spec-vue-options-api.md` (complete implementation guide)
2. **User Story**: `docs/stories/2-11-vue-options-api-parsing.md` (acceptance criteria)

**Context References** (background):
3. **Session Notes**: `docs/session-2025-11-12-status.md` (why this story exists)
4. **Test Report**: `docs/asure-project-test-report.md` (current state)

**Code References** (existing patterns):
5. **Vue Parser**: `scripts/index_utils.py:1187-1262`
6. **JS Parser**: `scripts/index_utils.py:546-905` (call graph patterns)
7. **Brace Counting**: `scripts/index_utils.py:640-660` (enum parser)

---

## Recommended Workflow

### Phase 1: Setup (5 min)
```bash
cd /Users/rchoi/Developer/claude-code-project-index

# Review tech spec
cat docs/tech-spec-vue-options-api.md

# Review story
cat docs/stories/2-11-vue-options-api-parsing.md

# Open implementation file
code scripts/index_utils.py
```

### Phase 2: Implementation (2-3 hours)
Follow tech spec section 8 (Implementation Checklist):
- Hour 1: Core method extraction
- Hour 2: Lifecycle + computed
- Hour 3: Testing + validation

### Phase 3: Validation (30 min)
```bash
# Run unit tests
python -m pytest scripts/test_vue_options_api.py -v

# Run integration test on Asure project
cd /Users/rchoi/Developer/asure/asure.ptm.portal.web.ui.new
python /Users/rchoi/Developer/claude-code-project-index/scripts/project_index.py --verbose

# Verify coverage increase
# Before: 65 Vue files (27%)
# After: 220+ Vue files (≥90%)
```

---

## Questions for Developer Agent

Before starting implementation, verify understanding:

1. **Architecture**: Do you understand the integration point at line 1248?
2. **Patterns**: Are the regex patterns clear from tech spec section 3.1?
3. **Algorithm**: Is the brace counting algorithm clear from tech spec section 3.2?
4. **Testing**: Do you understand the test strategy from section 6?
5. **Validation**: Do you know how to verify success on Asure project?

---

## Post-Implementation Checklist

Before marking story DONE:
- [ ] All 10 Acceptance Criteria met
- [ ] Unit tests passing (100% coverage)
- [ ] Integration test on Asure project passing
- [ ] Coverage: 27% → ≥90% verified
- [ ] Performance: <5ms overhead measured
- [ ] No regressions in existing tests
- [ ] Documentation updated
- [ ] Code self-reviewed against tech spec

---

## Handoff Complete

**Ready for Development**: ✅
**Blockers**: None
**Dependencies**: None (all code exists, this is enhancement)
**Priority**: High (completes Vue parsing foundation)

**Next Agent**: Developer Agent (DEV)
**Recommended Model**: Claude Sonnet 4.5 (complex parsing logic)

---

**Architect Sign-off**: Winston, 2025-11-12
**Status**: Ready for implementation
