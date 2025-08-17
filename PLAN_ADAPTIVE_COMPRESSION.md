# Adaptive Compression Strategy for PROJECT_INDEX

## Overview
This document outlines the planned improvements to the PROJECT_INDEX system, focusing on intelligent compression, adaptive scaling, and multi-tier indexing for projects of all sizes.

## Current Issues
1. **Compression Bug**: Infinite loop when index exceeds 2MB (Issue #1)
2. **Token Inefficiency**: 555 lines/15K tokens for small projects
3. **No Size Adaptation**: Same format for 10 files vs 10,000 files
4. **Limited Language Support**: Only Python, JS, Shell

## Planned Improvements

### Phase 1: Critical Bug Fixes
- Fix infinite loop in compression with iteration guards
- Implement progressive reduction strategy
- Add emergency truncation as last resort

### Phase 2: Adaptive Compression Strategy

#### Size Tiers
- **Nano** (<50 files): Full AST, everything included
- **Small** (50-200): DSL format, full signatures
- **Medium** (200-1K): Strategic sampling, key functions
- **Large** (1K-5K): Architecture focus, module indexes
- **Huge** (5K+): Executive summary, on-demand drilling

#### Token Budgets
- Nano: 50K tokens (can afford everything)
- Small: 20K tokens (full project fits)
- Medium: 10K tokens (need compression)
- Large: 5K tokens (aggressive compression)
- Huge: 2K tokens (minimal overview)

### Phase 3: Three-Tier Index System
```
PROJECT_INDEX_MINI.json (2KB) → Always loaded
    ↓
PROJECT_INDEX.json (10-50KB) → Standard detail
    ↓
Module Indexes → Drill-down capability
  - src/auth/INDEX.json
  - src/api/INDEX.json
```

### Phase 4: DSL Format
Transform verbose JSON into compact DSL for 60-70% size reduction:
```dsl
# From 100 bytes per function (JSON)
# To 30-50 bytes per function (DSL)
F:authenticate_user|(email:str,password:str)->User|Validates credentials
  >hash_password,query_database
  <login_endpoint,api_auth
```

### Phase 5: Enhanced File Discovery
- Implement `git ls-files` for proper gitignore handling
- Faster and more accurate than manual filtering
- Respects all git ignore patterns

### Phase 6: Multi-Language Support
- Integrate ast-grep for 20+ languages
- Fallback chain: ast-grep → language-specific → ripgrep → regex
- Consistent extraction across all languages

## Configuration System

### Auto-Detection
- Automatically detect project size
- Apply appropriate compression tier
- Optimize for token budget

### User Overrides
```json
{
  "compression": "auto",
  "max_tokens": 10000,
  "module_indexes": true,
  "sampling_rate": 0.6
}
```

### CLI Flags
- `--full`: Force complete index
- `--mini`: Maximum compression
- `--module=NAME`: Focus on specific module

## Expected Outcomes

| Metric | Current | Target |
|--------|---------|--------|
| Compression Success | Fails >2MB | 100% |
| Index Size (1K files) | ~500KB | <100KB |
| Token Usage | 15K | <5K |
| Languages | 3 | 20+ |
| Query Speed | 3s | <1s |

## Implementation Timeline
1. **Week 1**: Bug fixes and core improvements
2. **Week 2**: DSL format and compression
3. **Week 3**: Multi-language support
4. **Week 4**: Testing and optimization

## Key Innovations from Research
- **Roderik's Fork**: DSL format, ast-grep integration, git ls-files
- **Hybrid Intelligence**: Combine heuristics with ultrathinking
- **Query-Adaptive Loading**: Load only relevant modules
- **Progressive Degradation**: Maintain quality while reducing detail

## Success Criteria
1. 50% reduction in token usage
2. Sub-second response times
3. Support for 1000+ file projects
4. 95%+ relevance score on benchmarks
5. Easy configuration for all project sizes