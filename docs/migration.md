# Migration Guide

This guide helps you upgrade between major versions of the claude-code-project-index tool.

**Quick Navigation:**
- [Version Overview](#version-overview)
- [v0.1.x → v0.2.x (Epic 1)](#v01x--v02x-epic-1-split-index-architecture)
- [v0.2.x → v0.3.x (Epic 2)](#v02x--v03x-epic-2-intelligent-features)
- [Breaking Changes Summary](#breaking-changes-summary)

## Version Overview

| Version | Release | Key Features | Migration Complexity |
|---------|---------|--------------|---------------------|
| **v0.1.x** | Legacy | Single-file index, basic parsing | N/A (baseline) |
| **v0.2.x** | Epic 1 | Split architecture, lazy-loading | ⚠️ Medium |
| **v0.3.x** | Epic 2+ | Intelligent features, MCP server, smart presets | ✅ Low (auto-upgrade) |

## v0.1.x → v0.2.x (Epic 1): Split Index Architecture

**What changed:** Single monolithic PROJECT_INDEX.json → Core index + detail modules (PROJECT_INDEX.d/)

**Why upgrade:**
- ✅ 10-100x faster analysis on large projects (>1000 files)
- ✅ Reduced memory footprint
- ✅ Better lazy-loading for AI agents
- ✅ Foundation for Epic 2+ intelligent features

### Migration Steps

#### Automated Migration (Recommended)

```bash
# 1. Backup your current index (automatic, but verify)
ls -la PROJECT_INDEX.json
# Expected: PROJECT_INDEX.json exists

# 2. Preview migration (dry-run)
python3 ~/.claude-code-project-index/scripts/project_index.py --migrate --dry-run

# Expected output:
# 📋 Dry-run mode: No files will be modified
# Legacy index: 450.2 KB (single file)
# → Core index: 85.3 KB
# → Detail modules: 12 modules, 365.8 KB total
# ✅ Validation: 847 files, 1,243 functions preserved

# 3. Perform migration
python3 ~/.claude-code-project-index/scripts/project_index.py --migrate

# Expected output:
# 🔄 Starting migration...
# ✅ Backup created: PROJECT_INDEX.json.backup-2025-11-11-123456
# ✅ Generated core index (85.3 KB)
# ✅ Generated 12 detail modules (365.8 KB)
# ✅ Migration completed successfully!
```

#### Manual Migration (Alternative)

```bash
# Option 1: Regenerate from scratch with split format
rm PROJECT_INDEX.json
python3 ~/.claude-code-project-index/scripts/project_index.py --mode split

# Option 2: Force split format (auto-converts)
python3 ~/.claude-code-project-index/scripts/project_index.py --format=split
```

### Verification

```bash
# 1. Check version upgraded
cat PROJECT_INDEX.json | jq .version
# Expected: "2.0-split" or higher

# 2. Verify detail modules created
ls -1 PROJECT_INDEX.d/*.json | wc -l
# Expected: 1 or more module files

# 3. Validate file count
cat PROJECT_INDEX.json | jq '.stats.total_files'
git ls-files | wc -l
# Should match (within reason)

# 4. Test with Claude Code
claude "analyze architecture -i"
# Expected: Works correctly with new format
```

### Rollback (if needed)

```bash
# Restore from automatic backup
cp PROJECT_INDEX.json.backup-* PROJECT_INDEX.json
rm -rf PROJECT_INDEX.d/

# Verify rollback
cat PROJECT_INDEX.json | jq .version
# Expected: No "version" field or "1.0"
```

### Breaking Changes

#### ⚠️ File Format

**Before (v0.1.x):**
```
PROJECT_INDEX.json (all data in single file)
```

**After (v0.2.x):**
```
PROJECT_INDEX.json (lightweight core)
PROJECT_INDEX.d/
├── scripts.json
├── src.json
└── docs.json
```

**Impact:** External tools directly reading PROJECT_INDEX.json must update to use lazy-loading API

**Migration:**
```python
# Old code (v0.1.x)
with open("PROJECT_INDEX.json") as f:
    data = json.load(f)
    all_files = data["files"]

# New code (v0.2.x)
from scripts.loader import load_detail_module

# Load core for navigation
with open("PROJECT_INDEX.json") as f:
    core = json.load(f)

# Load specific modules on-demand
scripts_module = load_detail_module("scripts")
```

#### ⚠️ Configuration Format

**Before (v0.1.x):**
```bash
# No configuration file
# All settings via CLI flags
```

**After (v0.2.x):**
```json
// .project-index.json
{
  "mode": "auto",
  "threshold": 1000
}
```

**Migration:** Create `.project-index.json` or use CLI flags (backward compatible)

## v0.2.x → v0.3.x (Epic 2): Intelligent Features

**What changed:** Added MCP server, temporal awareness, relevance scoring, impact analysis, incremental updates, smart presets

**Why upgrade:**
- ✅ MCP server for AI tool integration (optional)
- ✅ Automatic prioritization of recently changed files
- ✅ Intelligent module relevance scoring
- ✅ Impact analysis for safe refactoring
- ✅ 10-100x faster incremental updates
- ✅ Zero-configuration smart presets

### Migration Steps

#### Automatic Upgrade (Recommended)

```bash
# 1. Update installation
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash

# 2. Regenerate index (auto-detects and applies smart preset)
cd /path/to/your/project
/index

# Expected output:
# ✨ Created .project-index.json with medium preset
#    1,247 files detected
#    All Epic 2 features enabled ✨
```

**That's it!** The tool automatically:
- Detects project size
- Selects appropriate preset (small/medium/large)
- Enables all Epic 2 features
- Creates `.project-index.json` with optimal config

#### Manual Configuration (Optional)

```bash
# If you want custom settings, edit .project-index.json
vim .project-index.json
```

Example configurations:

**Enable all features (medium project):**
```json
{
  "_preset": "medium",
  "mode": "auto",
  "threshold": 500,
  "include_all_doc_tiers": false,
  "relevance_scoring": {
    "enabled": true,
    "top_n": 5,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 5.0,
      "temporal_medium": 2.0,
      "semantic_keyword": 1.0
    }
  },
  "impact_analysis": {
    "enabled": true,
    "max_depth": 10,
    "include_indirect": true
  },
  "incremental": {
    "enabled": true,
    "full_threshold": 0.5
  },
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3
  }
}
```

**Minimal configuration (small project):**
```json
{
  "_preset": "small",
  "mode": "single",
  "include_all_doc_tiers": true
}
```

### Installing MCP Dependencies (Optional)

If you want to use the MCP server feature:

```bash
# Install MCP dependencies (first external dependency)
pip install -r ~/.claude-code-project-index/requirements.txt

# Configure MCP server in Claude Code (~/.claude/settings.json)
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": ["~/.claude-code-project-index/project_index_mcp.py"]
    }
  }
}

# Restart Claude Code and verify tools appear
```

**See [MCP Setup Guide](mcp-setup.md) for detailed configuration.**

### Verification

```bash
# 1. Check smart preset applied
cat .project-index.json | jq '._preset'
# Expected: "small", "medium", or "large"

# 2. Verify Epic 2 features enabled
cat .project-index.json | jq '.relevance_scoring.enabled'
# Expected: true (for medium/large presets)

# 3. Test incremental updates
echo "test" >> README.md
/index
# Expected: "Incremental update: 1 file changed, 2.1s"

# 4. Test temporal awareness
claude "show recent changes -i"
# Expected: Lists files changed in last 7 days
```

### Breaking Changes

#### ✅ Backward Compatible

**Good news:** v0.3.x is fully backward compatible with v0.2.x!

- ✅ Existing `.project-index.json` configs continue to work
- ✅ New features are opt-in (enabled by default in new projects)
- ✅ MCP server is optional (requires external dependencies)
- ✅ Core indexing remains stdlib-only (no dependencies)

#### New External Dependencies (Optional)

**MCP Server Only:**
```bash
# Required only if using MCP server
pip install mcp>=1.0.0 pydantic>=2.0.0

# Performance monitoring (optional)
pip install psutil>=5.9.0
```

**Core indexing:** Still requires zero external dependencies (Python 3.8+ stdlib)

#### Configuration Changes (Non-Breaking)

**New fields in `.project-index.json`:**
```json
{
  "_preset": "medium",              // NEW: Auto-detected preset
  "_generated": "2025-11-10...",    // NEW: Timestamp
  "relevance_scoring": {...},       // NEW: Epic 2 feature
  "impact_analysis": {...},         // NEW: Epic 2 feature
  "incremental": {...},             // NEW: Epic 2 feature
  "submodule_config": {...}         // NEW: Epic 4 feature
}
```

**Old configurations (v0.2.x) continue to work** - new fields are added with defaults.

## Breaking Changes Summary

### Epic 1 (v0.1.x → v0.2.x)

| Change | Impact | Migration |
|--------|--------|-----------|
| **File format** | ⚠️ High | Use migration tool or regenerate |
| **External tools** | ⚠️ Medium | Update to use loader.py API |
| **Configuration** | ✅ Low | CLI flags still work |

### Epic 2 (v0.2.x → v0.3.x)

| Change | Impact | Migration |
|--------|--------|-----------|
| **Smart presets** | ✅ None | Auto-applied on first run |
| **MCP dependencies** | ✅ None | Optional, core remains stdlib-only |
| **Configuration** | ✅ None | Fully backward compatible |
| **New features** | ✅ None | Opt-in, work with existing configs |

## Troubleshooting Migrations

### Migration Failed

**Error:** "Migration validation failed"

**Cause:** Data integrity check detected discrepancies

**Fix:**
```bash
# Automatic rollback occurs
# Check backup and retry
ls -la PROJECT_INDEX.json.backup-*

# Manual retry
python3 ~/.claude-code-project-index/scripts/project_index.py --migrate
```

### Missing Modules After Migration

**Error:** "Module not found: xyz"

**Fix:**
```bash
# Regenerate modules
rm -rf PROJECT_INDEX.d/
python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
```

### Config Not Applied

**Error:** Smart preset not applied on upgrade

**Fix:**
```bash
# Delete config and regenerate
rm .project-index.json
/index

# Verify preset applied
cat .project-index.json | jq '._preset'
```

### MCP Server Not Working

**Error:** "MCP tools not available"

**Fix:**
```bash
# 1. Check dependencies installed
pip list | grep -E "mcp|pydantic"

# 2. Install if missing
pip install -r ~/.claude-code-project-index/requirements.txt

# 3. Verify config path
cat ~/.claude/settings.json | jq '.mcpServers."project-index"'

# 4. Restart Claude Code
```

## Version-Specific Notes

### v0.1.x (Legacy)

- Single-file format
- No configuration files
- Basic Python parsing
- No external dependencies

### v0.2.x (Epic 1)

- Split index architecture
- Lazy-loading via loader.py
- Optional configuration file
- No external dependencies (core)

### v0.3.x (Epic 2+)

- Smart configuration presets
- Temporal awareness & relevance scoring
- Impact analysis & incremental updates
- Optional MCP server (requires dependencies)
- Zero-config for new projects

## Getting Help

If you encounter migration issues:

1. **Check error logs:**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py 2>&1 | tee migration.log
   ```

2. **Review guides:**
   - [Troubleshooting Guide](troubleshooting.md)
   - [Best Practices Guide](best-practices.md)
   - [MCP Setup Guide](mcp-setup.md)

3. **File an issue:**
   - [GitHub Issues](https://github.com/ericbuess/claude-code-project-index/issues)
   - Include: version, error log, project size

4. **Community support:**
   - This is a community tool - have Claude Code help you!
   - Fork and adapt for your specific needs

---

**Last updated:** 2025-11-11
