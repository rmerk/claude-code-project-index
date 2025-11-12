# Technical Specification: Vue Options API Parsing Enhancement

**Epic**: Enhanced Intelligence & Developer Tools (Epic 2 Extension)
**Story**: Vue Options API Method Extraction
**Architect**: Winston
**Date**: 2025-11-12
**Estimated Effort**: 2-3 hours

---

## Executive Summary

Enhance Vue SFC parser to extract methods from Options API components, increasing Vue file coverage from 27% (65 files) to ~100% (246 files) on the Asure PTM Portal project.

---

## 1. Problem Statement

### Current Behavior
- **Composition API**: ✅ Fully parsed (65 files)
  - `<script setup>` blocks with top-level functions
  - Delegated to JavaScript parser successfully

- **Options API**: ❌ Not parsed (181 files)
  - `export default { methods: {...} }` object literal structure
  - JavaScript parser only extracts top-level functions
  - Methods nested inside object literals are ignored

### Impact
- 73% of Vue files not fully indexed
- Developers can't find method implementations via search
- Call graph analysis incomplete for Options API components

---

## 2. Solution Architecture

### 2.1 High-Level Design

```
Vue File (.vue)
    ↓
extract_vue_signatures() [EXISTING]
    ↓
Extract <script> section [EXISTING]
    ↓
Detect API style [EXISTING]
    ↓
┌─────────────────────────────────┐
│ Options API Detected?           │
│ (export default { ... })        │
└─────────────────────────────────┘
    ↓ YES
┌─────────────────────────────────┐
│ extract_options_api_methods()   │ ← NEW FUNCTION
│                                 │
│ 1. Parse export default block  │
│ 2. Extract methods object       │
│ 3. Extract computed object      │
│ 4. Extract lifecycle hooks      │
│ 5. Extract watch object         │
└─────────────────────────────────┘
    ↓
Merge with JavaScript parser results
    ↓
Return comprehensive function map
```

### 2.2 New Function: `extract_options_api_methods()`

**Location**: `scripts/index_utils.py` (insert after `extract_vue_signatures()`)
**Signature**:
```python
def extract_options_api_methods(script_content: str, all_functions: Set[str]) -> Dict[str, Dict]:
    """
    Extract methods from Vue Options API export default block.

    Handles:
    - methods: { ... }
    - computed: { ... }
    - watch: { ... }
    - Lifecycle hooks: created(), mounted(), etc.

    Args:
        script_content: JavaScript content from <script> section
        all_functions: Set of all function names for call graph analysis

    Returns:
        Dict mapping function names to metadata:
        {
            'handleClick': {
                'line': 45,
                'params': ['event'],
                'category': 'methods',  # or 'computed', 'lifecycle', 'watch'
                'calls': ['submitForm', 'validateInput']
            }
        }
    """
```

---

## 3. Implementation Strategy

### 3.1 Parsing Patterns

#### Pattern 1: Extract `export default` Block
```python
# Match: export default { ... }
export_default_pattern = r'export\s+default\s*\{(.*)\}\s*$'
match = re.search(export_default_pattern, script_content, re.DOTALL | re.MULTILINE)

if not match:
    return {}  # Not Options API

options_block = match.group(1)
```

#### Pattern 2: Extract `methods` Object
```python
# Match: methods: { method1() {}, method2: function() {} }
methods_pattern = r'methods\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'

# Extract individual methods with shorthand and function syntax
method_patterns = [
    r'(\w+)\s*\([^)]*\)\s*\{',           # Shorthand: methodName() {}
    r'(\w+)\s*:\s*function\s*\([^)]*\)',  # Function: methodName: function() {}
    r'(\w+)\s*:\s*async\s+function',      # Async function
    r'async\s+(\w+)\s*\(',                # Async shorthand
]
```

#### Pattern 3: Extract Lifecycle Hooks
```python
# Vue 2 lifecycle hooks (at root of export default)
lifecycle_hooks = [
    'beforeCreate', 'created',
    'beforeMount', 'mounted',
    'beforeUpdate', 'updated',
    'beforeDestroy', 'destroyed',
    'activated', 'deactivated',
    'errorCaptured'
]

# Match: created() { ... } or created: function() { ... }
for hook in lifecycle_hooks:
    pattern = rf'{hook}\s*(?:\([^)]*\)\s*\{{|:\s*function\s*\()'
    match = re.search(pattern, options_block)
    if match:
        # Extract hook implementation
```

#### Pattern 4: Extract Computed Properties
```python
# Match: computed: { fullName() {}, total: function() {} }
computed_pattern = r'computed\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
```

#### Pattern 5: Extract Watchers
```python
# Match: watch: { userName(newVal, oldVal) {}, ... }
watch_pattern = r'watch\s*:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
```

### 3.2 Nested Brace Counting Algorithm

**Challenge**: Options API uses deeply nested braces:
```javascript
export default {
  methods: {
    handleClick() {
      if (condition) {
        // nested braces
      }
    }
  }
}
```

**Solution**: Brace-counting algorithm (similar to existing enum parser, line 640-660):
```python
def extract_object_content(content: str, start_pos: int) -> tuple[str, int]:
    """Extract content of { ... } block handling nested braces."""
    brace_count = 1
    end_pos = start_pos

    for i in range(start_pos, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = i
                break

    return content[start_pos:end_pos], end_pos
```

### 3.3 Integration with Existing Parser

**Modify `extract_vue_signatures()` at line 1248:**

```python
# BEFORE (current):
if script_content and script_content.strip():
    js_result = extract_javascript_signatures(script_content)
    # Merge results...

# AFTER (enhanced):
if script_content and script_content.strip():
    # First, run standard JS parser (handles composition API)
    js_result = extract_javascript_signatures(script_content)

    # If Options API detected, extract methods from export default
    if result['vue_api'] == 'options':
        all_functions = set(js_result.get('functions', {}).keys())
        options_methods = extract_options_api_methods(script_content, all_functions)

        # Merge Options API methods into functions dict
        for method_name, method_info in options_methods.items():
            if method_name not in js_result['functions']:
                js_result['functions'][method_name] = method_info

    # Merge all results
    result['imports'] = js_result.get('imports', [])
    result['functions'] = js_result.get('functions', {})
    # ... rest of merge
```

---

## 4. Data Model

### 4.1 Enhanced Function Metadata

Add `category` field to distinguish method types:

```python
{
    'handleClick': {
        'line': 45,
        'params': ['event'],
        'returns': None,
        'async': False,
        'category': 'methods',  # NEW: 'methods' | 'computed' | 'lifecycle' | 'watch'
        'calls': ['submitForm', 'validateInput']
    },
    'fullName': {
        'line': 78,
        'params': [],
        'category': 'computed',  # Computed property
        'calls': ['this.firstName', 'this.lastName']
    },
    'mounted': {
        'line': 12,
        'params': [],
        'category': 'lifecycle',  # Lifecycle hook
        'calls': ['this.fetchData']
    }
}
```

### 4.2 Backward Compatibility

- Functions without `category` field → assumed to be regular functions
- Legacy parsers ignore `category` field
- No schema version bump required (optional metadata)

---

## 5. Edge Cases & Handling

### 5.1 Mixed API Styles
**Scenario**: Vue 2 component with both Options API and Composition API
```javascript
export default {
  setup() {  // Composition API
    const count = ref(0)
  },
  methods: {  // Options API
    increment() { ... }
  }
}
```
**Handling**: Extract both. `setup()` detected as regular function, `methods` extracted via Options API parser.

### 5.2 Arrow Function Methods
**Scenario**:
```javascript
methods: {
  handleClick: (event) => { ... }  // Arrow function
}
```
**Handling**: Add arrow function pattern:
```python
r'(\w+)\s*:\s*\([^)]*\)\s*=>'
```

### 5.3 Async Methods
**Scenario**:
```javascript
methods: {
  async fetchData() { ... }
}
```
**Handling**: Already covered by `async\s+(\w+)\s*\(` pattern

### 5.4 Destructured Parameters
**Scenario**:
```javascript
methods: {
  handleUpdate({ id, name }) { ... }
}
```
**Handling**: Parameter extraction may show `{ id, name }` as single param. Acceptable for first iteration.

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Create**: `scripts/test_vue_options_api.py`

```python
class TestVueOptionsAPIExtraction(unittest.TestCase):

    def test_extract_methods_shorthand(self):
        """Test extraction of shorthand methods."""
        content = """
        export default {
          methods: {
            handleClick(event) {
              console.log(event)
            },
            submitForm() {
              return true
            }
          }
        }
        """
        result = extract_vue_signatures(content)
        self.assertIn('handleClick', result['functions'])
        self.assertIn('submitForm', result['functions'])
        self.assertEqual(result['functions']['handleClick']['category'], 'methods')

    def test_extract_lifecycle_hooks(self):
        """Test extraction of lifecycle hooks."""
        content = """
        export default {
          created() {
            this.fetchData()
          },
          mounted() {
            console.log('Mounted')
          }
        }
        """
        result = extract_vue_signatures(content)
        self.assertIn('created', result['functions'])
        self.assertIn('mounted', result['functions'])
        self.assertEqual(result['functions']['created']['category'], 'lifecycle')

    def test_extract_computed_properties(self):
        """Test extraction of computed properties."""
        content = """
        export default {
          computed: {
            fullName() {
              return this.firstName + ' ' + this.lastName
            }
          }
        }
        """
        result = extract_vue_signatures(content)
        self.assertIn('fullName', result['functions'])
        self.assertEqual(result['functions']['fullName']['category'], 'computed')

    def test_nested_braces_handling(self):
        """Test proper handling of nested braces in methods."""
        content = """
        export default {
          methods: {
            complexMethod() {
              if (condition) {
                for (let i = 0; i < 10; i++) {
                  console.log({ nested: true })
                }
              }
            }
          }
        }
        """
        result = extract_vue_signatures(content)
        self.assertIn('complexMethod', result['functions'])
```

### 6.2 Integration Tests

**Test on Asure Project**:
```bash
cd /Users/rchoi/Developer/asure/asure.ptm.portal.web.ui.new
python /Users/rchoi/Developer/claude-code-project-index/scripts/project_index.py --verbose

# Expected results:
# - Languages with full parsing: 181+ Vue files (up from 65)
# - Coverage: ~100% (up from 27%)
```

### 6.3 Regression Tests

- ✅ Composition API files still parse correctly
- ✅ Non-Vue JavaScript files unaffected
- ✅ Call graph generation still works
- ✅ Incremental updates detect Vue file changes

---

## 7. Performance Considerations

### 7.1 Regex Complexity
- Nested brace counting: O(n) where n = script length
- Multiple regex patterns: ~5-8 patterns per file
- **Impact**: Minimal (Vue files average 200-500 lines)

### 7.2 Benchmarks
- **Target**: <5ms per Vue file for Options API extraction
- **Measured**: Current JS parsing is ~2ms per file
- **Acceptable**: 2-4ms additional overhead for Options API

---

## 8. Implementation Checklist

### Phase 1: Core Implementation (1-1.5 hours)
- [ ] Create `extract_options_api_methods()` function
- [ ] Implement `export default` block extraction
- [ ] Implement `methods:` object parsing
- [ ] Implement lifecycle hook extraction
- [ ] Implement nested brace counting helper
- [ ] Add call graph analysis for extracted methods
- [ ] Integrate with `extract_vue_signatures()`

### Phase 2: Extended Features (0.5-1 hour)
- [ ] Implement `computed:` property extraction
- [ ] Implement `watch:` object extraction
- [ ] Handle arrow function methods
- [ ] Add `category` metadata field

### Phase 3: Testing (0.5 hour)
- [ ] Create unit tests (`test_vue_options_api.py`)
- [ ] Run integration tests on Asure project
- [ ] Verify coverage increases from 27% → ~100%
- [ ] Performance benchmarking

---

## 9. Acceptance Criteria

### AC1: Method Extraction
- ✅ Extract methods from `methods: { ... }` object
- ✅ Support shorthand syntax: `methodName() {}`
- ✅ Support function syntax: `methodName: function() {}`
- ✅ Support async methods

### AC2: Lifecycle Hook Extraction
- ✅ Extract all 11 Vue lifecycle hooks (created, mounted, etc.)
- ✅ Categorize as `category: 'lifecycle'`
- ✅ Include in function index

### AC3: Computed Property Extraction
- ✅ Extract computed properties from `computed: { ... }`
- ✅ Categorize as `category: 'computed'`

### AC4: Nested Brace Handling
- ✅ Correctly parse methods with deeply nested braces
- ✅ Handle if/for/while blocks inside methods

### AC5: Coverage Improvement
- ✅ Increase Vue file coverage from 27% to ≥90% on Asure project
- ✅ 181 Options API files fully parsed

### AC6: Backward Compatibility
- ✅ Composition API files still parse correctly
- ✅ No regression in JavaScript/TypeScript parsing
- ✅ Incremental updates work correctly

### AC7: Performance
- ✅ Options API extraction adds <5ms per file
- ✅ Full index regeneration completes in <10 seconds for 777 files

---

## 10. Implementation Roadmap

### Hour 1: Core Method Extraction
1. **0:00-0:15** - Create `extract_options_api_methods()` skeleton
2. **0:15-0:30** - Implement `export default` block extraction with brace counting
3. **0:30-0:50** - Implement `methods:` object parsing with regex patterns
4. **0:50-1:00** - Test on sample Options API component

### Hour 2: Lifecycle & Computed
1. **1:00-1:20** - Implement lifecycle hook extraction
2. **1:20-1:40** - Implement computed property extraction
3. **1:40-2:00** - Integrate with `extract_vue_signatures()` and test

### Hour 3: Testing & Validation
1. **2:00-2:20** - Create unit tests
2. **2:20-2:40** - Run integration tests on Asure project
3. **2:40-3:00** - Performance benchmarking and documentation updates

---

## 11. Risks & Mitigation

### Risk 1: Regex Complexity
**Risk**: Regex patterns may not capture all method syntax variations
**Likelihood**: Medium
**Mitigation**:
- Test on real Asure codebase (181 files)
- Fallback to logging unparsed patterns
- Incremental improvement based on real data

### Risk 2: Performance Degradation
**Risk**: Additional parsing may slow down index generation
**Likelihood**: Low
**Impact**: Low (target <5ms overhead acceptable)
**Mitigation**:
- Benchmark on 777-file project
- Only run Options API parser when detected
- Use compiled regex patterns

### Risk 3: Breaking Changes
**Risk**: New parser logic breaks existing functionality
**Likelihood**: Low
**Mitigation**:
- Comprehensive unit tests
- Integration tests on Asure project
- Gradual rollout (test on single file first)

---

## 12. Success Metrics

### Quantitative
- **Coverage**: 27% → ≥90% Vue files fully parsed
- **File Count**: 65 → 220+ Vue files with signatures
- **Performance**: <5ms additional overhead per Vue file
- **Test Coverage**: 100% code coverage for new functions

### Qualitative
- ✅ Developers can search for Options API methods
- ✅ Call graph includes Options API components
- ✅ Incremental updates work seamlessly
- ✅ No regressions in existing parsing

---

## 13. Next Steps After Implementation

### Short-Term (Next Session)
1. **Vue Template Parsing** - Extract component props, emits, slots from `<template>`
2. **Watch Object Enhancement** - Parse complex watchers with deep/immediate options
3. **Mixins Support** - Track imported mixins and their methods

### Long-Term (Future Epics)
1. **Vue 3 Composition API Enhancements** - Parse `defineProps()`, `defineEmits()`
2. **Component Hierarchy Mapping** - Track parent-child component relationships
3. **Pinia Store Integration** - Parse Pinia stores and actions

---

## Appendix A: Reference Implementation Patterns

### Existing Brace Counting (Enum Parser, line 640-660)
```python
# Extract enums (TypeScript)
enum_pattern = r'(?:export\s+)?enum\s+(\w+)\s*{'
enum_matches = list(re.finditer(enum_pattern, content))
for match in enum_matches:
    enum_name = match.group(1)
    start_pos = match.end()
    brace_count = 1
    end_pos = start_pos
    for i in range(start_pos, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_pos = i
                break
```

### Call Graph Extraction (JavaScript Parser, line 104-132)
```python
def extract_function_calls_javascript(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from JavaScript code body."""
    calls = set()
    for func_name in all_functions:
        pattern = rf'\b{func_name}\s*\('
        if re.search(pattern, body):
            calls.add(func_name)
    return list(calls)
```

---

## Appendix B: Sample Vue Files from Asure Project

### Options API Example (Not Currently Parsed)
```vue
<template>
  <div>{{ fullName }}</div>
</template>

<script lang="ts">
export default {
  data() {
    return {
      firstName: 'John',
      lastName: 'Doe'
    }
  },
  computed: {
    fullName() {
      return `${this.firstName} ${this.lastName}`
    }
  },
  methods: {
    handleClick(event: MouseEvent) {
      this.submitForm()
    },
    async submitForm() {
      await this.validateInput()
    },
    validateInput() {
      return true
    }
  },
  created() {
    this.fetchData()
  }
}
</script>
```

**Expected Extraction**:
```json
{
  "functions": {
    "fullName": {"line": 11, "category": "computed", "params": []},
    "handleClick": {"line": 16, "category": "methods", "params": ["event"], "calls": ["submitForm"]},
    "submitForm": {"line": 19, "category": "methods", "params": [], "async": true, "calls": ["validateInput"]},
    "validateInput": {"line": 22, "category": "methods", "params": []},
    "created": {"line": 26, "category": "lifecycle", "params": [], "calls": ["fetchData"]}
  }
}
```

---

**End of Technical Specification**
