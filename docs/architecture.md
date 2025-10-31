# Architecture Documentation

## System Architecture

### Architecture Type
**Hook-Based Event-Driven CLI Tool**

The system integrates with Claude Code through hooks that intercept user interactions, generating and maintaining a comprehensive project index transparently.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code                             │
│                                                              │
│  User types: "fix auth bug -i"                              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│              UserPromptSubmit Hook                           │
│         (scripts/i_flag_hook.py)                             │
│                                                              │
│  1. Detect -i flag                                           │
│  2. Parse size parameter                                     │
│  3. Check if regeneration needed (hash check)                │
│  4. Generate/refresh PROJECT_INDEX.json                      │
│  5. Invoke index-analyzer subagent                           │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│           Index Generation Pipeline                          │
│         (scripts/project_index.py)                           │
│                                                              │
│  File Discovery → Filtering → Parsing → Call Graph →        │
│  Compression → JSON Output                                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│               PROJECT_INDEX.json                             │
│                                                              │
│  - Directory tree structure                                  │
│  - Function/class signatures                                 │
│  - Bidirectional call graphs                                 │
│  - Documentation map                                         │
│  - Directory purposes                                        │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│          Index Analyzer Subagent                             │
│      (agents/index-analyzer.md)                              │
│                                                              │
│  - Deep analysis of index                                    │
│  - Code relationship analysis                                │
│  - Strategic recommendations                                 │
│  - Returns findings to main agent                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Hook Layer (Integration)

**Components**:
- `i_flag_hook.py` - UserPromptSubmit hook
- `stop_hook.py` - Stop hook

**Responsibilities**:
- Flag detection and parsing
- Smart regeneration decisions
- Subagent invocation
- Clipboard handling

**Data Flow**:
```
User Prompt → Hook Detection → Index Generation → Subagent → Response
```

---

### 2. Indexer Core (Processing)

**Components**:
- `project_index.py` - Main orchestrator
- `index_utils.py` - Parsing utilities

**Responsibilities**:
- File discovery (git-aware)
- Multi-language parsing
- Call graph construction
- Compression
- JSON serialization

**Data Flow**:
```
File System → Parser → Extractor → Graph Builder → Compressor → JSON
```

---

### 3. Parser Layer (Language Processing)

**Components**:
- `extract_python_signatures()` - Python parser
- `extract_javascript_signatures()` - JS/TS parser
- `extract_shell_signatures()` - Shell parser

**Extraction Process**:
1. Read file content
2. Regex-based pattern matching
3. Extract signatures with line numbers
4. Identify function calls
5. Build call relationships
6. Add docstrings

---

### 4. Analysis Layer (Intelligence)

**Components**:
- `index-analyzer.md` - Subagent
- Call graph analysis
- Dependency mapping

**Capabilities**:
- Execution path analysis
- Impact assessment
- Dead code detection
- Architecture insights

---

## Data Architecture

### PROJECT_INDEX.json Structure

```json
{
  "at": "2025-10-30T...",           // Timestamp
  "root": ".",                        // Project root
  "tree": [...],                      // Directory tree (compact)
  "stats": {                          // Statistics
    "total_files": 245,
    "fully_parsed": {"python": 12},
    "listed_only": {"go": 45}
  },
  "f": {                              // Files (dense format)
    "s/file.py": [
      "p",                            // Language (p=python)
      [                               // Functions
        "func:25:(args):calls:doc"
      ],
      {                               // Classes
        "Class": ["42", [...methods]]
      }
    ]
  },
  "g": [                              // Call graph (edges)
    ["caller", "callee"]
  ],
  "d": {                              // Documentation map
    "README.md": ["Header1", "Header2"]
  },
  "deps": {                           // Dependencies
    "file.py": ["module1", "module2"]
  },
  "dir_purposes": {...}              // Directory purposes
}
```

### Dense Format Optimization

**Space Savings**:
- Minified JSON (no whitespace)
- Short keys (`f`, `g`, `d` instead of `files`, `graph`, `docs`)
- Compact signatures (`:` separators)
- Path abbreviations (`s/` for `scripts/`)

**Result**: ~50% space reduction

---

## Processing Pipeline

### Phase 1: File Discovery
```python
if git_available:
    files = git ls-files  # Fast, respects .gitignore
else:
    files = recursive_walk + gitignore_filter
```

**Performance**: Git-based discovery is 10-100x faster for large repos

---

### Phase 2: Language Detection
```python
for file in files:
    extension = file.suffix
    if extension in PARSEABLE_LANGUAGES:
        language = PARSEABLE_LANGUAGES[extension]
        parse_fully(file, language)
    elif extension in CODE_EXTENSIONS:
        list_only(file)
```

---

### Phase 3: Parsing & Extraction
```python
# Python example
def extract_python_signatures(content):
    functions = extract_functions_with_regex()
    classes = extract_classes_with_regex()
    calls = build_call_relationships()
    return {functions, classes, imports}
```

---

### Phase 4: Call Graph Construction
```python
# Bidirectional graph
for function in all_functions:
    calls = identify_calls_in_body(function.body)
    call_graph[function] = calls
    for called in calls:
        called_by_graph[called].append(function)
```

---

### Phase 5: Compression
Progressive strategies applied when size exceeds limits:
1. Reduce tree depth
2. Truncate docstrings (80 → 40 chars)
3. Remove docstrings
4. Remove documentation map
5. Keep only N most important files (by function count)

---

## Integration Architecture

### Claude Code Hook System

**Configured in**: `~/.claude/settings.json`

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"command": ["python3", "path/to/i_flag_hook.py"]}
    ],
    "Stop": [
      {"command": ["python3", "path/to/stop_hook.py"]}
    ]
  }
}
```

---

### Slash Command Integration

**Location**: `~/.claude/commands/index.md`

**Behavior**: Direct execution of `project_index.py`

---

### Subagent Integration

**Location**: `~/.claude/agents/index-analyzer.md`

**Invocation**: Automatic when using `-i` flag

**Context**: Receives PROJECT_INDEX.json + user prompt

---

## Scalability Considerations

### File Limits
- **MAX_FILES**: 10,000 (hard limit)
- **Recommendation**: Use .gitignore for large repos
- **Bypass**: Modify constant if needed

### Size Limits
- **MAX_INDEX_SIZE**: 1MB default
- **Dynamic**: Based on token target (-i size)
- **Compression**: Automatic when exceeding limits

### Performance
- **Git-based discovery**: O(files in repo)
- **Parsing**: O(lines of code)
- **Compression**: O(iterations × file count)

---

## Deployment Architecture

### Installation Target
```
~/.claude-code-project-index/
├── scripts/           # Core Python scripts
├── agents/            # Subagent definitions
└── .python_cmd        # Cached Python command
```

### Configuration Target
```
~/.claude/
├── settings.json      # Hooks configured here
├── commands/index.md  # Slash command
└── agents/index-analyzer.md
```

---

## Security Considerations

### File Access
- **Respects**: .gitignore patterns
- **Excludes**: .git, node_modules, sensitive directories
- **Reads**: Only files git would track

### Execution
- **No eval()**: Pure parsing, no code execution
- **No network**: All processing local
- **No sensitive data**: Index contains structure only

---

## Error Handling Strategy

### Graceful Degradation
- Parse errors → Skip file, continue
- Timeout → Return partial index
- Missing dependencies → Fallback behavior
- Hook errors → Warn user, don't block workflow

### User Feedback
- Progress indicators (every 100 files)
- Warning messages (non-blocking)
- Error messages (with suggestions)

---

## Extension Points

### Adding Language Support
1. Add extension to `PARSEABLE_LANGUAGES`
2. Implement `extract_<lang>_signatures()`
3. Register in `build_index()` parser selection

### Custom Compression
1. Modify `compress_if_needed()` strategies
2. Add new compression step
3. Adjust size thresholds

### Hook Customization
1. Modify flag detection regex
2. Add new modes (beyond -i and -ic)
3. Custom subagent routing

---

## Testing Strategy

**Philosophy**: Real-world beta testing

**Approach**:
- Community users provide feedback
- Claude Code helps users fix issues
- Fork-and-customize model

**Quality Measures**:
- Error handling throughout
- Graceful fallbacks
- Non-blocking failures

---

## Future Architecture Considerations

**Potential Enhancements**:
- Incremental updates (delta indexing)
- Parallel parsing for large repos
- Language servers integration
- AST-based parsing (more accurate)
- Index caching and invalidation
- Multi-repo support

---

## Design Principles

1. **Simplicity**: No external dependencies required
2. **Performance**: Git-based discovery, progressive compression
3. **Reliability**: Graceful degradation, non-blocking errors
4. **Extensibility**: Easy to add languages and features
5. **Transparency**: Auto-maintains, user barely notices
6. **Customizability**: Fork it, fix it, make it yours

---

## Technology Decisions

| Decision | Rationale |
|----------|-----------|
| **Python 3.8+** | Widely available, excellent string processing |
| **Stdlib only** | No dependency hell, works everywhere |
| **Regex parsing** | Fast, good enough for signatures |
| **Hook-based** | Seamless integration with Claude Code |
| **JSON output** | Universal, easy to parse, compressible |
| **Git integration** | Fast file discovery, respects .gitignore |
| **Progressive compression** | Adaptive to project size |

---

## Architectural Constraints

1. **Python 3.8+ required** - Not compatible with Python 2
2. **Unix-like OS** - macOS/Linux only (Bash scripts)
3. **Claude Code integration** - Designed for hook system
4. **Token limits** - Compression required for large projects
5. **No AST parsing** - Regex-based for simplicity

---

## Performance Characteristics

| Operation | Complexity | Typical Time |
|-----------|------------|--------------|
| File discovery (git) | O(n files) | <1s for 1000 files |
| Parsing | O(LOC) | ~0.1s per 1000 LOC |
| Call graph | O(functions) | <1s for 500 functions |
| Compression | O(iterations) | 1-5s worst case |
| **Total** | **O(files + LOC)** | **2-30s typical** |
