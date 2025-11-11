# Best Practices Guide

This guide helps you get the most out of the claude-code-project-index tool by understanding when and how to use its features effectively.

**Quick Navigation:**
- [Feature Usage Guidance](#feature-usage-guidance)
- [Configuration Tuning](#configuration-tuning)
- [Real-World Usage Patterns](#real-world-usage-patterns)
- [Performance Optimization](#performance-optimization)
- [Project-Specific Recommendations](#project-specific-recommendations)

## Feature Usage Guidance

### Tiered Documentation Storage

**What it does:** Separates documentation into three tiers (critical, standard, archive) to achieve 60-80% compression by loading only critical docs by default.

**When to use:**
- ✅ Project has 50+ markdown files
- ✅ Documentation represents >30% of your project
- ✅ You want faster initial load times
- ✅ Working with extensive docs (API references, tutorials, guides)

**When to skip:**
- ❌ Project has <20 markdown files
- ❌ Documentation is minimal
- ❌ All docs are equally important
- ❌ You prefer maximum simplicity

**Configuration:**

```json
{
  "include_all_doc_tiers": false
}
```

- **`false`** (default) - Tiered mode for doc-heavy projects
  - Only critical tier docs in core index
  - Standard and archive tiers in detail modules
  - Achieves 60-80% compression

- **`true`** - All tiers in core for small projects
  - All documentation tiers included in core index
  - No separation into detail modules
  - Simpler structure, no lazy-loading needed

**Example - Documentation-Heavy Project:**

```bash
# Your project structure
docs/
├── README.md (critical - always loaded)
├── API.md (critical - always loaded)
├── ARCHITECTURE.md (critical - always loaded)
├── guides/ (standard - loaded on-demand)
│   ├── setup.md
│   └── deployment.md
└── tutorials/ (archive - loaded on-demand)
    ├── intro.md
    └── advanced.md

# With tiered storage
$ cat PROJECT_INDEX.json | jq '.d_critical | keys'
["README.md", "API.md", "ARCHITECTURE.md"]

# Core index: 6.4 KB (61% compression vs 16.4 KB without tiering)
```

**Loading additional tiers programmatically:**

```python
from scripts.loader import load_doc_tier

# Load standard tier from specific module
standard_docs = load_doc_tier("standard", "docs")

# Load archive tier from all modules
archive_docs = load_doc_tier("archive")
```

### Relevance Scoring and Temporal Awareness

**What it does:** Automatically prioritizes recently changed files and relevant modules based on your query, reducing the amount of code the AI agent needs to analyze.

**When to use:**
- ✅ Active development on specific features
- ✅ Debugging recent changes
- ✅ Large projects (>1000 files)
- ✅ You want faster, more focused AI responses

**How it works:**

1. **Temporal weighting** (automatic):
   - Files changed in last 7 days: **5x weight boost**
   - Files changed in last 30 days: **2x weight boost**
   - Files older than 30 days: normal weight

2. **Relevance signals** (combined):
   - **Explicit file reference** (10.0x): Direct file path mentions
   - **Temporal recent** (5.0x): Recently changed files
   - **Semantic keyword** (1.0x): Keyword matches in file/module names
   - **Structural** (1.0x): Architectural relationships

**Configuration tuning:**

```json
{
  "relevance_scoring": {
    "enabled": true,
    "top_n": 5,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 5.0,
      "temporal_medium": 2.0,
      "semantic_keyword": 1.0
    }
  }
}
```

**Tuning recommendations:**

- **Aggressive temporal focus** (debugging recent changes):
  ```json
  {
    "weights": {
      "temporal_recent": 8.0,
      "temporal_medium": 3.0
    }
  }
  ```

- **Balanced exploration** (learning unfamiliar codebase):
  ```json
  {
    "weights": {
      "explicit_file_ref": 10.0,
      "semantic_keyword": 2.0,
      "temporal_recent": 3.0
    }
  }
  ```

- **Top N tuning:**
  - **top_n: 3** - Faster, more focused (large projects)
  - **top_n: 5** - Balanced (default, most projects)
  - **top_n: 10** - Comprehensive (small projects or thorough analysis)

**Example - Debugging Recent Bug:**

```bash
# Query: "Why is authentication failing?"
#
# Relevance scoring automatically prioritizes:
# 1. src/auth.py (changed 2 days ago, contains "auth" keyword)
# 2. src/api/login.py (changed 1 week ago, related module)
# 3. tests/test_auth.py (changed 3 days ago, test context)
#
# Files changed 6 months ago are deprioritized unless explicitly mentioned
```

### Impact Analysis

**What it does:** Uses the call graph to identify all functions that depend on a target function, enabling safe refactoring.

**When to use:**
- ✅ Refactoring existing functions
- ✅ Understanding dependencies before changes
- ✅ Assessing blast radius of modifications
- ✅ Code review and risk assessment

**Configuration:**

```yaml
# In bmad/bmm/config.yaml or equivalent
impact_analysis:
  enabled: true
  max_depth: 10           # Maximum traversal depth
  include_indirect: true  # Include indirect callers
  show_line_numbers: true # Show file:line in reports
```

**Usage patterns:**

1. **Before refactoring:**
   ```
   Query: "What depends on the validate function?"

   Response:
   - Direct callers (2):
     - scripts/auth.py:42 (login)
     - scripts/auth.py:67 (register)

   - Indirect callers (2):
     - scripts/api.py:15 (api_handler)
     - scripts/middleware.py:89 (auth_middleware)

   Total affected: 4 functions
   ```

2. **Risk assessment:**
   - **High-impact functions** (>10 callers): Require comprehensive test coverage
   - **Medium-impact functions** (3-10 callers): Test critical paths
   - **Low-impact functions** (1-2 callers): Standard testing

3. **Combined with temporal awareness:**
   - High-impact + recently changed = High risk, test thoroughly
   - Low-impact + isolated = Safe to refactor aggressively

**Example - Safe Refactoring Decision:**

```bash
# Query: "Impact of changing parse_config function?"
#
# Result:
# - Direct callers: 2 (low impact)
# - Last changed: 6 months ago (stable)
# - Test coverage: 100% (verified)
#
# Decision: Safe to refactor with standard testing
```

### Incremental Updates

**What it does:** Selectively regenerates only changed modules instead of reprocessing the entire project, providing 10-100x speedup.

**When to use:**
- ✅ Active development (frequent file changes)
- ✅ Large projects (>1000 files)
- ✅ CI/CD pipelines (fast regeneration needed)
- ✅ Hook-based workflows (auto-updates on save)

**When to use full regeneration:**
- ❌ First run (no existing index)
- ❌ Major restructuring (many files moved/renamed)
- ❌ After git operations (branch switch, rebase)
- ❌ Suspected index corruption

**Performance characteristics:**

| Changed Files | Incremental Time | Full Regen Time | Speedup |
|--------------|------------------|-----------------|---------|
| 1-10 files   | ~2 seconds       | ~15 seconds     | 7.5x    |
| 10-50 files  | ~4 seconds       | ~30 seconds     | 7.5x    |
| 50-100 files | ~8 seconds       | 1-2 minutes     | 10x     |
| 100+ files   | <10 seconds      | 2-5 minutes     | 15-30x  |

**Automatic mode (recommended):**

```bash
# Auto-detects and uses incremental if possible
python scripts/project_index.py
```

**Force full regeneration:**

```bash
# Use when index seems stale or after major refactoring
python scripts/project_index.py --full
```

**Configuration:**

```json
{
  "incremental": {
    "enabled": true,
    "full_threshold": 0.5
  }
}
```

- **full_threshold**: Trigger full regen if >N% files changed (default: 0.5 = 50%)

**Example - Active Development Workflow:**

```bash
# Implement feature
$ vim src/auth.py src/api/login.py

# Save and commit
$ git add src/auth.py src/api/login.py
$ git commit -m "Add 2FA support"

# Regenerate index (incremental automatically used)
$ /index
# Detected: 2 changed files
# Regenerated: auth module (15 files)
# Time: 2.1 seconds (vs 18 seconds full regeneration)
```

### Sub-Module Organization (Multi-Level)

**What it does:** Splits large modules into hierarchical sub-modules for better navigation and faster lazy-loading.

**When to use:**
- ✅ Module has >100 files
- ✅ Framework-specific patterns detected (Vite, React, Next.js)
- ✅ Working on targeted features (components, API routes, etc.)
- ✅ Want faster query response times

**When to skip:**
- ❌ Module has <100 files (well-organized)
- ❌ Prefer simplicity over optimization
- ❌ No framework patterns detected
- ❌ Legacy project with flat structure

**Framework presets:**

- **Vite** (3-level splitting): `src` → `src-components` → `src-components-auth`
- **React** (2-level splitting): `src` → `src-components`
- **Next.js** (2-level splitting): `project` → `project-app`
- **Generic** (2-level splitting): `docs` → `docs-guides`

**Configuration:**

```json
{
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3
  }
}
```

**Strategy modes:**

1. **auto** (recommended): Apply preset if module >threshold files
2. **force**: Always split regardless of size
3. **disabled**: Use monolithic modules

**Example - Vite Project:**

```bash
# Before sub-modules (monolithic)
$ ls PROJECT_INDEX.d/
src.json (850 files)

# After sub-modules (organized)
$ ls PROJECT_INDEX.d/
src-components.json (120 files)
src-views.json (85 files)
src-api.json (45 files)
src-stores.json (30 files)
src-composables.json (25 files)
src-utils.json (15 files)

# Query: "Fix login component"
# Agent loads: src-components.json (120 files)
# vs loading entire src.json (850 files)
# → 86% file reduction, much faster response
```

## Configuration Tuning

### Project Size-Based Recommendations

**Small Projects (<100 files):**

```json
{
  "mode": "single",
  "include_all_doc_tiers": true,
  "relevance_scoring": {
    "top_n": 10
  }
}
```

- Single-file format for simplicity
- All docs in core (no tiering)
- Load more modules (top_n: 10) since project is small

**Medium Projects (100-1000 files):**

```json
{
  "mode": "auto",
  "threshold": 500,
  "include_all_doc_tiers": false,
  "relevance_scoring": {
    "enabled": true,
    "top_n": 5
  },
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100
  }
}
```

- Auto-detect format (splits at 500 files)
- Tiered docs for faster loading
- Balanced relevance scoring (top 5)
- Sub-modules for large directories

**Large Projects (1000-5000 files):**

```json
{
  "mode": "split",
  "threshold": 500,
  "include_all_doc_tiers": false,
  "relevance_scoring": {
    "enabled": true,
    "top_n": 3,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 8.0
    }
  },
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3
  },
  "incremental": {
    "enabled": true
  }
}
```

- Force split format
- Aggressive tiering and sub-modules
- Focused relevance (top 3, higher temporal weight)
- Incremental updates critical

**Very Large Projects (5000+ files):**

```json
{
  "mode": "split",
  "threshold": 200,
  "include_all_doc_tiers": false,
  "relevance_scoring": {
    "enabled": true,
    "top_n": 3,
    "weights": {
      "temporal_recent": 10.0
    }
  },
  "submodule_config": {
    "enabled": true,
    "strategy": "force",
    "threshold": 50,
    "max_depth": 3
  },
  "incremental": {
    "enabled": true,
    "full_threshold": 0.3
  }
}
```

- Very aggressive splitting (threshold: 200)
- Force sub-modules even for small directories
- Maximum temporal focus
- Lower incremental threshold (trigger full regen at 30% changes)

### Workflow-Specific Tuning

**Active Feature Development:**

```json
{
  "relevance_scoring": {
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 8.0,
      "semantic_keyword": 2.0
    }
  },
  "incremental": {
    "enabled": true
  }
}
```

- High temporal weight (focus on recent changes)
- Incremental updates for fast iteration

**Code Review:**

```json
{
  "relevance_scoring": {
    "top_n": 5,
    "weights": {
      "temporal_recent": 5.0,
      "semantic_keyword": 2.0
    }
  },
  "impact_analysis": {
    "enabled": true,
    "include_indirect": true
  }
}
```

- Balanced relevance
- Impact analysis to understand dependencies

**Learning Unfamiliar Codebase:**

```json
{
  "relevance_scoring": {
    "top_n": 10,
    "weights": {
      "semantic_keyword": 3.0,
      "temporal_recent": 1.0
    }
  }
}
```

- Load more modules (top_n: 10)
- Prioritize keyword matches over recency
- Lower temporal weight (explore all areas)

**Debugging Production Issues:**

```json
{
  "relevance_scoring": {
    "top_n": 3,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 10.0
    }
  },
  "incremental": {
    "enabled": true
  }
}
```

- Focused search (top_n: 3)
- Maximum temporal weight (recent changes likely culprit)
- Fast incremental updates

## Real-World Usage Patterns

### Pattern 1: Daily Feature Development

```bash
# Morning: Start work on new feature
$ claude "Plan authentication refactoring -i"
# Relevance scoring loads: auth module, api module, test module

# Afternoon: Implement changes
$ vim src/auth.py src/api/login.py
$ claude "Review my auth changes -i"
# Incremental update (2 files changed, 2.1s)
# Temporal awareness prioritizes recently edited files

# End of day: Commit
$ git add . && git commit -m "Refactor auth"
$ /index  # Incremental update for tomorrow
```

**Configuration:**
- Incremental updates: enabled
- Temporal recent weight: 8.0 (high)
- Top N: 5 (balanced)

### Pattern 2: Debugging Production Bug

```bash
# Bug report: "Login failing for some users"
$ claude "Why is authentication failing? -i"
# Agent automatically:
# 1. Loads auth-related modules (relevance)
# 2. Prioritizes recently changed auth files (temporal)
# 3. Analyzes dependencies (impact)

# Found issue in auth.py:42
$ vim src/auth.py
$ claude "Test my fix -i"
# Incremental update (1 file, 1.8s)

# Verify dependencies
$ claude "What depends on validate_session? -i"
# Impact analysis shows 8 callers - test them all
```

**Configuration:**
- Temporal recent weight: 10.0 (maximum focus on recent changes)
- Impact analysis: enabled
- Top N: 3 (focused)

### Pattern 3: Code Review

```bash
# Review teammate's PR
$ git checkout feature/payment-integration
$ /index  # Generate index for branch

$ claude "Review the payment integration changes -i"
# Agent:
# 1. Identifies recently changed files (temporal)
# 2. Analyzes dependencies (impact)
# 3. Loads relevant test modules
# 4. Provides focused review

$ claude "What will break if we change process_payment? -i"
# Impact analysis: 12 direct callers, 5 indirect
```

**Configuration:**
- Impact analysis: enabled, include_indirect: true
- Temporal medium weight: 2.0 (recent but not obsessive)
- Top N: 5 (comprehensive)

### Pattern 4: Learning New Codebase

```bash
# Day 1: High-level overview
$ claude "Explain the architecture -i"
# Structural query → loads core index, architectural docs

# Day 2: Explore specific area
$ claude "How does the API layer work? -i"
# Semantic search → loads api module, related tests

# Day 3: Deep dive
$ claude "Show me all authentication flows -i"
# Combined: semantic (auth) + structural (flows)
```

**Configuration:**
- Semantic keyword weight: 3.0 (high for exploration)
- Temporal recent weight: 1.0 (low - explore all code)
- Top N: 10 (comprehensive)

### Pattern 5: CI/CD Integration

```bash
# .github/workflows/update-index.yml
name: Update Project Index
on: [push]
jobs:
  update-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Generate Index
        run: |
          python scripts/project_index.py --no-prompt
      - name: Commit Index
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add PROJECT_INDEX.json PROJECT_INDEX.d/
          git commit -m "Update project index" || exit 0
          git push
```

**Configuration:**
- `--no-prompt` flag (skip interactive prompts)
- Incremental updates: enabled (fast CI runs)

## Performance Optimization

### Reducing Index Generation Time

1. **Use split format for large projects:**
   ```bash
   python scripts/project_index.py --mode split
   ```

2. **Lower sub-module threshold:**
   ```json
   {
     "submodule_config": {
       "threshold": 50
     }
   }
   ```

3. **Optimize git operations:**
   ```bash
   # Git metadata extraction can be slow for large repos
   # Consider disabling for CI if not needed
   git config core.fsmonitor true  # macOS/Linux
   ```

4. **Use incremental updates:**
   ```json
   {
     "incremental": {
       "enabled": true
     }
   }
   ```

### Reducing MCP Response Time

1. **Limit module size with sub-modules:**
   ```json
   {
     "submodule_config": {
       "strategy": "force",
       "threshold": 50
     }
   }
   ```

2. **Use SSD storage:**
   ```bash
   # Ensure PROJECT_INDEX.d/ is on fast storage
   df -h .
   ```

3. **Tune relevance scoring (load fewer modules):**
   ```json
   {
     "relevance_scoring": {
       "top_n": 3
     }
   }
   ```

### Reducing Memory Usage

1. **Use split format:**
   - Single-file loads entire index into memory
   - Split format lazy-loads modules on-demand

2. **Enable tiered documentation:**
   ```json
   {
     "include_all_doc_tiers": false
   }
   ```

3. **Use sub-modules:**
   - Reduces size of individual modules loaded into memory

## Project-Specific Recommendations

### Monorepo Projects

```json
{
  "mode": "split",
  "threshold": 200,
  "submodule_config": {
    "enabled": true,
    "strategy": "force",
    "max_depth": 3
  },
  "relevance_scoring": {
    "top_n": 3
  }
}
```

- Aggressive splitting for multiple sub-projects
- Force sub-modules to organize by project/feature
- Focus relevance (top_n: 3) to avoid cross-project noise

### Documentation-Heavy Projects

```json
{
  "include_all_doc_tiers": false,
  "relevance_scoring": {
    "weights": {
      "semantic_keyword": 3.0
    }
  }
}
```

- Tiered docs critical for performance
- High semantic weight (keyword matching in doc titles)

### Rapid Iteration Projects

```json
{
  "incremental": {
    "enabled": true
  },
  "relevance_scoring": {
    "weights": {
      "temporal_recent": 10.0
    }
  }
}
```

- Incremental updates essential
- Maximum temporal focus (always prioritize latest changes)

### Legacy Codebases

```json
{
  "mode": "single",
  "submodule_config": {
    "enabled": false
  },
  "relevance_scoring": {
    "top_n": 10
  }
}
```

- Simple configuration for flat structures
- Load more modules (old code lacks clear organization)
- Skip sub-modules (likely flat directory structure)

---

**Last updated:** 2025-11-11

**Related Guides:**
- [Troubleshooting Guide](troubleshooting.md) - Resolve issues
- [MCP Setup Guide](mcp-setup.md) - Configure MCP server
- [Migration Guide](migration.md) - Upgrade between versions
