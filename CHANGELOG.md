# Changelog

All notable changes to the Claude Code Project Index will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Version management system with `--version` flag and VERSION file
- Update checking on `/index` run with GitHub Releases API (2s timeout)
- `--no-update-check` flag for CI/automation environments
- `install.sh --upgrade` mechanism for downloading and installing latest version
- `install.sh --rollback` capability to restore previous version from backup
- Automatic backup creation before upgrades in `~/.claude-code-project-index/backups/`
- Update check logging to `~/.claude-code-project-index/logs/update-checks.log`
- Version compatibility warnings when index format mismatches tool version

## [0.3.0] - 2025-11-05 - Epic 2: Intelligent Context Features

### Added - Smart Configuration & Installation
- **Smart configuration presets** (small/medium/large) with auto-detection based on file count
- Interactive preset upgrade prompts when project crosses size boundaries
- Template-based configuration system in `~/.claude-code-project-index/templates/`
- `--upgrade-to [small|medium|large]` flag for manual preset switching
- Performance: Preset detection completes under 5 seconds for 10,000+ file projects

### Added - Intelligent Features
- **Tiered documentation classification** system (critical/standard/archive tiers)
  - Critical docs loaded in core index by default
  - Standard/archive docs available in detail modules for lazy loading
  - ~60-80% reduction in core index size while maintaining full access
- **Git metadata extraction** for all indexed files
  - Commit hash, author, date, PR number, lines changed, recency days
  - Integrated with relevance scoring for temporal awareness
  - 2s timeout per file, graceful degradation on git unavailable
- **Temporal awareness** for time-based relevance scoring
  - Recent files (0-7 days) boosted 5x in relevance
  - Medium recency (8-30 days) boosted 2x
  - Supports time-based queries like "show me files changed this week"
- **MCP server implementation** for Claude Code integration
  - 4 tools: `load_core`, `load_module`, `search_files`, `get_file_info`
  - < 500ms response time for MCP operations
  - Pydantic validation for all inputs
  - Path traversal protection
- **Relevance scoring engine** for intelligent module prioritization
  - Explicit file ref: 10x weight
  - Temporal recent: 5x for 7-day, 2x for 30-day
  - Semantic keyword: 1x baseline
  - Automatically loads top N most relevant modules
- **Impact analysis tooling** for change tracking
  - Direct and indirect caller analysis
  - Configurable depth for traversal (default: 10 levels)
  - Cycle detection for circular dependencies
  - File path mapping with line numbers
- **Incremental index updates** for faster regeneration
  - Git diff-based change detection
  - Dependency graph for affected module identification
  - Hash-based validation for integrity
  - Automatic fallback to full regeneration when needed
  - ~60-85% faster than full regeneration for small changes

### Added - MCP Tool Detection
- **Hybrid query routing** system for optimal tool selection
  - Strategy A: Structural navigation (MCP Read + Index)
  - Strategy B: Content search (MCP Grep)
  - Strategy C: Temporal queries (MCP Git + Relevance)
  - Strategy D: Fallback to index-only when MCP unavailable
- Runtime MCP capability detection with caching
- Graceful degradation when MCP tools unavailable

### Changed
- ⚠️ **BREAKING**: Index format version updated from `1.0` to `2.2-submodules`
  - Core index (`PROJECT_INDEX.json`) now contains lightweight file tree and module references
  - Detail modules moved to `PROJECT_INDEX.d/*.json` for lazy loading
  - **Migration**: Run `python scripts/project_index.py --migrate` to convert legacy format
  - See [migration.md](docs/migration.md#v01x-to-v02x) for details
- ⚠️ **BREAKING**: Configuration file structure extended with new fields
  - Added `tiered_docs`, `relevance_scoring`, `impact_analysis` sections
  - Old configs still work but miss new features
  - **Migration**: Delete `.project-index.json` to auto-generate new format, or manually add new sections
- Performance optimized: Index generation now 1.37s for 32 files (was ~3-5s in v0.1.x)
- MCP operations complete in <500ms (lazy loading benefit)

### Fixed
- Memory usage reduced by ~60-80% through tiered documentation and lazy loading
- Large project handling improved through smart presets and incremental updates
- Update checking non-blocking with 2s timeout (no performance impact)

### Security
- Update checking only sends user-agent header, no project metadata leaked (NFR-S6)
- Path traversal protection in MCP server
- Input validation for all MCP tool parameters

## [0.2.0] - 2025-11-02 - Epic 1: Split Index Architecture

### Added - Core Architecture
- **Split index architecture** for scalability
  - Core index (`PROJECT_INDEX.json`) contains file tree and module references
  - Detail modules (`PROJECT_INDEX.d/*.json`) contain function signatures and call graphs
  - Lazy loading interface for on-demand module access
  - ~80-90% reduction in initial load size for large projects
- **Backward compatibility detection** for legacy `PROJECT_INDEX.json` format
  - Automatic format detection based on `PROJECT_INDEX.d/` directory existence
  - Seamless fallback to single-file format for small projects (<1000 files)
- **Migration utility** for converting legacy indexes to split format
  - `--migrate` flag with dry-run support
  - Backup creation before migration
  - Integrity validation with automatic rollback on failure
  - File and function count verification
- **Configuration system** for index generation control
  - `.project-index.json` configuration file support
  - Mode selection: `auto` (default), `split`, `single`
  - Customizable file count threshold for auto-detection
  - CLI flags override config file settings

### Added - Developer Experience
- **Lazy loading Python module** (`scripts/loader.py`) for efficient index access
  - `load_detail_module(module_name)` - Load specific detail module
  - `find_module_for_file(file_path)` - O(1) file-to-module lookup
  - `load_detail_by_path(file_path)` - Load file details by path
  - `load_multiple_modules([names])` - Batch module loading
  - < 500ms load time per module, < 100ms for core index
- **Enhanced index-analyzer agent** with split architecture awareness
  - Automatic detection of index format
  - Relevance scoring for module prioritization
  - Lazy loading recommendations
  - Module structure analysis

### Changed
- ⚠️ **BREAKING**: Index format version changed from `1.0` to `2.0-split`
  - Single `PROJECT_INDEX.json` split into core + detail modules
  - **Migration**: Run `python scripts/project_index.py --migrate` to convert
  - Legacy format still supported for projects <1000 files
  - See [migration.md](docs/migration.md#v01x-to-v02x) for details
- File organization: Python scripts consolidated in `scripts/` directory
- Configuration precedence: CLI flags > config file > defaults

### Performance
- Index generation: ~80-90% faster initial load for large projects (lazy loading benefit)
- Memory usage: ~80-90% reduction for large projects (only load needed modules)
- Module load time: <500ms per module, <100ms for core index

## [0.1.0] - 2025-08-15 - Initial Release

### Added - Foundation
- **Single-file index generation** (`PROJECT_INDEX.json`)
  - Directory tree structure with depth limit (5 levels)
  - File metadata: language, size, line count
  - Directory purpose inference
- **Multi-language parsing**
  - Python: Full signature extraction with type annotations
  - JavaScript/TypeScript: Function and class signatures
  - Shell: Function definitions
  - Markdown: Section headers and structure
- **Call graph generation**
  - Function-level dependency tracking
  - Import statement extraction
  - Cross-file reference mapping
- **Documentation mapping**
  - Markdown file indexing
  - Section header extraction
  - Directory-level documentation grouping
- **Hook-based integration**
  - `-i` flag for index-aware mode via UserPromptSubmit hook
  - `-ic` flag for clipboard export
  - Automatic reindexing on Stop hook (external changes)
- **Installation system**
  - `install.sh` for automated setup
  - `/index` command for Claude Code
  - Hook configuration in `~/.claude/settings.json`

### Performance
- Index generation: ~3-5s for projects up to 1000 files
- Maximum supported: 10,000 files (1MB index size limit)

---

## Version History Summary

- **v0.1.x** (Aug 2025): Initial release with single-file index, multi-language parsing, hook integration
- **v0.2.x** (Nov 2025 - Epic 1): Split architecture, lazy loading, migration utility, configuration system
- **v0.3.x** (Nov 2025 - Epic 2): Intelligent features (git metadata, tiered docs, MCP server, relevance scoring, impact analysis, incremental updates)

## Release Tagging Process

For maintainers creating new releases:

1. **Update VERSION file**:
   ```bash
   echo "v0.X.Y" > VERSION
   ```

2. **Update CHANGELOG.md**:
   - Move changes from `[Unreleased]` to new version section
   - Add release date: `## [0.X.Y] - YYYY-MM-DD - Epic X: Name`
   - Mark breaking changes with ⚠️ and migration notes

3. **Create git tag**:
   ```bash
   git add VERSION CHANGELOG.md
   git commit -m "Release v0.X.Y"
   git tag -a v0.X.Y -m "Release v0.X.Y: Epic X Summary"
   git push origin main --tags
   ```

4. **Create GitHub Release**:
   - Go to https://github.com/ericbuess/claude-code-project-index/releases/new
   - Select tag `v0.X.Y`
   - Title: `v0.X.Y - Epic X: Name`
   - Description: Copy relevant CHANGELOG section
   - Attach any release artifacts if needed
   - Publish release

5. **Verify update checking**:
   ```bash
   python scripts/project_index.py --mode single
   # Should show update notification
   ```

## Migration Notes

For detailed migration instructions between versions, see [migration.md](docs/migration.md).

### Quick Migration References

- **v0.1.x → v0.2.x** (Epic 1): [Split Architecture Migration](docs/migration.md#v01x-to-v02x)
  - Run: `python scripts/project_index.py --migrate`
  - Breaking: Index format changed to split architecture
  - Backup created automatically before migration

- **v0.2.x → v0.3.x** (Epic 2): [Intelligent Features Migration](docs/migration.md#v02x-to-v03x)
  - No migration required - backward compatible
  - New features enabled via configuration
  - Smart presets auto-selected based on project size
