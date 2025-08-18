# Adaptive Compression Strategy for PROJECT_INDEX

## Overview
This document outlines the planned improvements to the PROJECT_INDEX system, focusing on dynamic sizing, intelligent compression, and support for both Claude and external AI models.

## Current Issues
1. **Compression Bug**: Infinite loop when index exceeds 2MB (Issue #1)
2. **Token Inefficiency**: 555 lines/15K tokens for small projects
3. **No Size Adaptation**: Same format for all project sizes
4. **Limited Language Support**: Only Python, JS, Shell

## Final Design: Single Dynamic Index

### Core Concept
- **ONE** PROJECT_INDEX.json file (not multiple tiers)
- Dynamically sized based on user request
- Smart caching to avoid unnecessary regeneration
- Support for external AI models via clipboard mode

### Flag Syntax
```bash
# Standard mode (for Claude)
-i         # Default 50k tokens
-i50       # 50k tokens
-i100      # 100k tokens (Claude max)

# Clipboard mode (for external AI)
-ic        # Default 50k + copy to clipboard
-ic400     # 400k + copy to clipboard
-ic800     # 800k + copy to clipboard (max)
```

### Size Limits
- **Minimum**: 5k tokens (below this is not useful)
- **Default**: 50k tokens (balanced)
- **Claude Max**: 100k tokens (leaves 100k for reasoning/response)
- **External Max**: 800k tokens (for Gemini, GPT-4, etc.)

### Smart Regeneration
Index regenerates only when:
1. Files have changed (detected via hash)
2. Different size requested than last time
3. Index doesn't exist

### Metadata Tracking
```json
{
  "_meta": {
    "generated_at": 1701234567.89,
    "target_size_k": 75,
    "actual_size_k": 72,
    "full_size_k": 234,
    "files_hash": "a3b4c5d6e7f8",
    "compression_ratio": "30.8%"
  }
}
```

## Phase 1: Critical Bug Fix
```python
def compress_index_if_needed(index, target_size):
    MAX_ITERATIONS = 10
    iteration = 0
    
    while measure_size(index) > target_size and iteration < MAX_ITERATIONS:
        iteration += 1
        # Progressive reduction strategies
        if remove_unparsed_files(index): continue
        if simplify_signatures(index): continue
        if remove_low_utility(index): continue
        # Emergency truncation
        truncate_to_size(index, target_size)
        break
```

## Phase 2: DSL Format
Transform verbose JSON into compact DSL for 60-70% size reduction:
```dsl
F:authenticate_user|(email:str,pwd:str)->User|32c,8cb
  >hash_password,query_database
  <login_endpoint,api_auth
```

## Phase 3: Intelligent Compression
```python
def calculate_utility_score(element):
    score = 0
    if element.is_entry_point: score += 100
    if element.is_public_api: score += 80
    if element.is_hotspot: score += 60
    if element.has_dependencies: score += 40
    if element.is_test: score -= 20
    if element.is_generated: score -= 30
    return score
```

## Phase 4: Enhanced Features

### Git Integration
- Use `git ls-files --cached --others --exclude-standard`
- Perfect gitignore handling
- Faster than manual filtering

### Multi-Language Support (via ast-grep)
- Support 20+ languages
- Fallback chain: ast-grep → language-specific → regex
- Consistent extraction

### Clipboard Mode
For external AI models with larger contexts:
```python
# Copies to clipboard:
# - User prompt
# - Subagent instructions
# - PROJECT_INDEX.json
# Ready to paste into Gemini, Claude.ai, etc.
```

## Context Allocation (Claude)
```
Total: 200k tokens
- Index: 100k max
- Reasoning: 50k
- Response: 30k
- Prompt: 10k
- Buffer: 10k
```

## Expected Outcomes

| Metric | Current | Target |
|--------|---------|--------|
| Compression Success | Fails >2MB | 100% |
| Token Usage | 15K | User-controlled |
| Cache Hit Rate | 0% | 80%+ |
| Languages | 3 | 20+ |
| External AI Support | No | Yes |

## Implementation Priority
1. **Fix compression bug** (Critical)
2. **Implement -i[size] syntax** (Core feature)
3. **Add smart caching** (Performance)
4. **DSL format** (60-70% reduction)
5. **Clipboard mode** (External AI)
6. **Git ls-files** (Better filtering)
7. **ast-grep integration** (Multi-language)

## Success Criteria
1. No infinite loops on large projects
2. User-controlled index size (5k-800k)
3. Smart caching reduces regeneration by 80%
4. Support for external AI models via clipboard
5. Clear feedback on actual vs target size