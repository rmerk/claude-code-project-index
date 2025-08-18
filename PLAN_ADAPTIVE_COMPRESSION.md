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

### Purpose
The subagent reads the entire index and uses ultrathinking to identify exactly which files need editing. Focus is on **accuracy**, not speed - Claude reasoning takes seconds anyway, so optimization should prioritize returning the right files over fast heuristics.

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
1. Non-ignored files have changed (detected via hash of file paths + mtimes)
2. Different size requested than last time
3. Index doesn't exist

Regeneration happens in the UserPromptSubmit hook when -i flag is detected.

### Metadata Tracking
```json
{
  "_meta": {
    "generated_at": 1701234567.89,
    "target_size_k": 75,      // What user requested
    "actual_size_k": 72,       // What was achieved after compression
    "full_size_k": 234,        // Uncompressed size
    "files_hash": "a3b4c5d6", // Hash of non-ignored file paths + mtimes
    "compression_ratio": "30.8%"
  }
}
```

Note: actual_size_k may differ from target_size_k due to compression granularity.

## Phase 1: Critical Bug Fix
```python
def compress_index_if_needed(index, target_size):
    MAX_ITERATIONS = 10  # Prevents infinite loop (Issue #1)
    iteration = 0
    
    while measure_size(index) > target_size and iteration < MAX_ITERATIONS:
        iteration += 1
        # Progressive reduction strategies
        if remove_unparsed_files(index): continue
        if simplify_signatures(index): continue
        if remove_low_utility(index): continue
        # Emergency truncation as last resort
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
- Used for both file discovery and hash calculation

### Multi-Language Support (via ast-grep)
- Support 20+ languages
- Fallback chain: ast-grep → language-specific → regex
- Consistent extraction

### Clipboard Mode
For external AI models with larger contexts:
```python
# Copies to clipboard (using pyperclip):
# - User prompt (cleaned, without -ic flag)
# - Subagent instructions from index-analyzer.md
# - PROJECT_INDEX.json at requested size
# Ready to paste into Gemini, Claude.ai, ChatGPT, etc.

# Falls back to .clipboard_content.txt if pyperclip unavailable
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
1. **Fix compression bug** (Critical - prevents data loss)
2. **Implement -i[size] syntax** (Core feature)
3. **Add smart caching** (Avoid unnecessary regeneration)
4. **DSL format** (60-70% size reduction)
5. **Clipboard mode** (Enable external AI models)
6. **Git ls-files** (Proper gitignore handling)
7. **ast-grep integration** (Multi-language support)

## Success Criteria
1. No infinite loops on large projects
2. User-controlled index size (5k-800k)
3. Smart caching reduces regeneration by 80%
4. Support for external AI models via clipboard
5. Clear feedback on actual vs target size