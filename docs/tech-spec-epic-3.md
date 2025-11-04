# Epic Technical Specification: Production Readiness for Claude Code CLI

Date: 2025-11-04
Author: Ryan
Epic ID: 3
Status: Draft

---

## Overview

Epic 3 transforms the claude-code-project-index tool from a feature-rich but rough-around-the-edges solution into production-ready tooling suitable for real-world deployment. Building on Epic 1's split index architecture and Epic 2's intelligent features (tiered documentation, git temporal awareness, MCP server, relevance scoring, and impact analysis), this epic addresses the critical production-readiness gaps identified during Epic 2 retrospective.

The core focus is delivering a polished end-to-end experience: smart installation that auto-detects project size and creates optimal config presets, validated performance metrics on medium-sized projects (500+ files), comprehensive documentation with Claude Code CLI as the primary workflow, version management with update checking, and multi-tool MCP support prioritizing Claude Code > Cursor > Claude Desktop.

This epic ensures that developers can confidently deploy the tool to medium-large production codebases, knowing it will perform efficiently, integrate seamlessly with their preferred AI assistant, and provide clear guidance for troubleshooting and optimization.

## Objectives and Scope

**Primary Objectives:**

1. **Deliver Production-Grade Installation** - Create seamless installation experience with Python dependency management (requirements.txt with `mcp` and `pydantic`), smart config presets (small/medium/large), and automatic config upgrades when project size crosses preset boundaries

2. **Validate Real-World Performance** - Benchmark on 3 medium projects (500-5000 files: Python, JavaScript/TypeScript, polyglot) measuring index generation time, MCP latency, token usage, and memory consumption with documented performance characteristics

3. **Provide Comprehensive Documentation** - Create Claude Code-first documentation hierarchy (README enhancement, troubleshooting guide, best practices, migration guide, MCP setup) prioritizing Claude Code CLI > Cursor > Claude Desktop

4. **Implement Version Management** - Add version tracking, update checking on `/index` runs (with opt-out), upgrade mechanism via `install.sh --upgrade`, CHANGELOG with Epic 1-3 history, and rollback capability

5. **Enable Multi-Tool MCP Support** - Auto-detect and configure MCP server for Claude Code CLI (priority 1), Cursor IDE (priority 2), and Claude Desktop (priority 3) with validation commands and tool-specific setup documentation

**In Scope:**

- Smart installation with config presets and auto-upgrade prompts
- Performance validation suite with 3 real-world medium projects
- Documentation overhaul with Claude Code as primary workflow
- Version management system with update checking and rollback
- Multi-tool MCP configuration (Claude Code, Cursor, Claude Desktop)
- Uninstall script that removes all MCP-related files
- Installation validation tests for MCP imports
- Performance regression tests

**Out of Scope:**

- GUI/web interface (remains CLI-only)
- Real-time daemon-based index updates (Epic 2 supports manual incremental only)
- CI/CD pipeline integration automation
- Cloud/remote index storage
- Native IDE plugins beyond MCP integration
- Automated testing frameworks (Epic 2 retrospective deferred this to future work)

## System Architecture Alignment

Epic 3 maintains full alignment with the existing hook-based event-driven CLI architecture while adding production-readiness layers around the core system:

**Core Architecture Components (Unchanged):**
- Hook-based integration via `UserPromptSubmit` and `Stop` hooks in `~/.claude/settings.json`
- Split index architecture: lightweight core (`PROJECT_INDEX.json`) + detail modules (`PROJECT_INDEX.d/`)
- MCP server (`project_index_mcp.py`) providing stdio transport with 4 tools (load_core, load_module, search_files, get_file_info)
- Index generation pipeline: File Discovery → Filtering → Parsing → Call Graph → Compression → JSON Output
- Python 3.8+ standard library foundation (no external dependencies for core functionality)

**Epic 3 Architectural Additions:**

1. **Installation Layer** - New installation infrastructure sitting above core system:
   - `requirements.txt` for MCP dependencies (first external dependencies introduced in Epic 2)
   - Config preset templates in `~/.claude-code-project-index/templates/` (small.json, medium.json, large.json)
   - `.project-index.json` local config file for per-project preset tracking
   - Auto-detection logic for project size and preset recommendation

2. **Version Management Layer** - Metadata and update checking:
   - `VERSION` file in `~/.claude-code-project-index/VERSION`
   - Update checking integration in index generation flow (non-blocking)
   - `CHANGELOG.md` tracking Epic 1-3 release history
   - Rollback capability via backup mechanisms in `install.sh`

3. **Multi-Tool Configuration Layer** - MCP server registration for multiple tools:
   - Claude Code CLI: `~/.config/claude-code/mcp.json` auto-configuration
   - Cursor IDE: Tool-specific MCP config auto-detection and generation
   - Claude Desktop: `~/Library/Application Support/Claude/` (macOS) configuration
   - Single MCP server implementation serves all three tools via stdio transport

4. **Documentation Layer** - Comprehensive guides integrated with tool:
   - `docs/troubleshooting.md`, `docs/best-practices.md`, `docs/migration.md`, `docs/mcp-setup.md`
   - README enhanced with performance characteristics table and Claude Code-first workflow
   - In-tool guidance via install.sh messages and version update prompts

**Architectural Constraints Respected:**
- Maintains Python 3.8+ compatibility (Unix-like OS requirement)
- Preserves hook-based integration model (no daemon mode)
- Continues single-repository indexing only (no multi-repo)
- Respects token limits through compression (NFR002: core index ≤ 100KB for 10,000 files)
- Maintains backward compatibility with Epic 1 legacy format detection

**Integration Points:**
- `install.sh` orchestrates: Python deps → config presets → MCP registration → hook setup → validation
- `project_index.py` extended with: version checking, preset boundary detection, config upgrade prompts
- MCP server unchanged but now registered in multiple tool configurations
- Documentation references existing architecture diagrams and components

## Detailed Design

### Services and Modules

| Module/Service | Responsibilities | Inputs | Outputs | Owner |
|----------------|------------------|--------|---------|-------|
| **install.sh** (Enhanced) | Python dependency installation via requirements.txt; config preset template generation; MCP server registration for detected tools; hook setup; installation validation | None (interactive) | Configured system, MCP registrations, config templates | Installation Layer |
| **uninstall.sh** (New) | Remove MCP server from tool configurations; delete config templates; clean up installation directory | None (interactive) | Clean system state | Installation Layer |
| **requirements.txt** (New) | Declare Python dependencies: `mcp`, `pydantic` | None | Dependency manifest | Installation Layer |
| **Config Preset Templates** (New) | Three JSON templates (small/medium/large) with threshold, mode, feature flags | None | small.json, medium.json, large.json | Installation Layer |
| **project_index.py** (Extended) | Add version checking on startup; detect preset boundary crossings; prompt for config upgrades; integrate with VERSION file | Existing: file system, git metadata | Enhanced: version warnings, upgrade prompts | Core Indexer |
| **.project-index.json** (New) | Per-project config file tracking: selected preset, project file count, last upgrade check timestamp | Auto-generated on first run | Preset metadata, upgrade state | Configuration |
| **VERSION** (New) | Single-source version string (e.g., "v0.3.0") | None | Version identifier | Version Management |
| **CHANGELOG.md** (New) | Markdown changelog documenting Epic 1, 2, 3 changes with version tags and migration notes | Epic documentation | Release history | Documentation |
| **docs/troubleshooting.md** (New) | FAQ, installation validation, MCP debugging tips, error message reference | Common user issues | Troubleshooting guide | Documentation |
| **docs/best-practices.md** (New) | Feature usage guidance, config tuning, real-world patterns | Epic 1-2 features | Best practices guide | Documentation |
| **docs/migration.md** (Enhanced) | v0.1.x → v0.2.x (Epic 1), v0.2.x → v0.3.x (Epic 2), breaking changes, preset migration | Version history | Migration guide | Documentation |
| **docs/mcp-setup.md** (New) | Tool-specific MCP setup: Claude Code CLI (detailed), Cursor IDE, Claude Desktop | MCP server architecture | Multi-tool setup guide | Documentation |
| **Performance Validation Suite** (New) | Benchmark scripts for 3 medium projects; measure index generation, MCP latency, token usage, memory | Test projects | Performance metrics, regression tests | Testing |
| **MCP Validation Command** (New) | Test MCP server connection for each tool; verify tool availability | Tool configuration | Connection status | Testing |

### Data Models and Contracts

**Config Preset Template Schema** (small.json, medium.json, large.json):
```json
{
  "preset_name": "medium",
  "description": "Optimized for 100-5000 file projects",
  "file_count_threshold": {
    "min": 100,
    "max": 5000
  },
  "index_config": {
    "mode": "auto",
    "split_threshold": 500,
    "tiered_docs": true,
    "include_all_doc_tiers": false
  },
  "relevance_scoring": {
    "enabled": true,
    "top_n": 5,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 1.0,
      "semantic_keyword": 1.0
    }
  },
  "incremental_updates": {
    "enabled": true
  }
}
```

**Project Config File Schema** (.project-index.json):
```json
{
  "preset": "medium",
  "project_file_count": 1247,
  "last_preset_check": "2025-11-04T10:30:00Z",
  "version_installed": "v0.3.0",
  "mcp_tools_configured": ["claude-code", "cursor"],
  "upgrade_history": [
    {
      "date": "2025-11-04T10:30:00Z",
      "from_preset": "small",
      "to_preset": "medium",
      "trigger": "file_count_threshold"
    }
  ]
}
```

**VERSION File Format**:
```
v0.3.0
```

**MCP Tool Configuration Contract** (Claude Code CLI example in ~/.config/claude-code/mcp.json):
```json
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": [
        "/Users/{user}/.claude-code-project-index/project_index_mcp.py"
      ],
      "env": {}
    }
  }
}
```

**Performance Metrics Schema**:
```json
{
  "project_name": "example-python-project",
  "project_stats": {
    "file_count": 847,
    "language": "python",
    "loc": 125000
  },
  "metrics": {
    "index_generation_full_ms": 8400,
    "index_generation_incremental_ms": 720,
    "mcp_load_core_ms": 45,
    "mcp_load_module_ms": 120,
    "mcp_search_files_ms": 35,
    "mcp_get_file_info_ms": 25,
    "token_usage_core": 11500,
    "memory_usage_mb": 145
  },
  "timestamp": "2025-11-04T10:30:00Z"
}
```

**Update Check Response Format**:
```json
{
  "current_version": "v0.3.0",
  "latest_version": "v0.3.1",
  "update_available": true,
  "release_url": "https://github.com/ericbuess/claude-code-project-index/releases/tag/v0.3.1",
  "breaking_changes": false
}
```

### APIs and Interfaces

**Command-Line Interface Extensions**:

```bash
# Version management
python3 project_index.py --version
# Output: v0.3.0

# Upgrade installation
./install.sh --upgrade
# Downloads latest version, backs up current, installs, validates

# Rollback to previous version
./install.sh --rollback
# Restores backed-up version

# Force config preset
python3 project_index.py --preset=large
# Applies large project preset regardless of auto-detection

# Uninstall with cleanup
./uninstall.sh
# Removes MCP configs, templates, installation directory

# Disable update checking
python3 project_index.py --no-update-check
# Skips GitHub release checking (for CI/automation)

# MCP connection validation
python3 scripts/validate_mcp.py --tool=claude-code
# Tests MCP server connection for specified tool
# Exit codes: 0=success, 1=connection failed, 2=tool not configured
```

**Installation Script Interface** (install.sh):

```bash
# Standard installation
./install.sh
# Interactive: detects tools, offers MCP config for all detected

# Silent mode (CI/automation)
./install.sh --no-prompt --tools=claude-code,cursor
# Non-interactive: configures specified tools only

# Upgrade from previous version
./install.sh --upgrade
# Checks GitHub for latest, downloads, installs, migrates config

# Specific tool configuration
./install.sh --configure-mcp=cursor
# Only configure MCP for Cursor IDE
```

**Project Index API Extensions** (project_index.py):

```python
# Version checking function (new)
def check_for_updates(no_update_check: bool = False) -> Optional[UpdateInfo]:
    """
    Check GitHub releases for newer version.

    Args:
        no_update_check: Skip check if True (for CI)

    Returns:
        UpdateInfo with latest version details, or None if up-to-date
    """

# Preset boundary detection (new)
def detect_preset_boundary_crossing(
    current_preset: str,
    file_count: int,
    preset_templates: Dict[str, PresetConfig]
) -> Optional[str]:
    """
    Determine if project has grown beyond current preset boundaries.

    Args:
        current_preset: Currently selected preset (small/medium/large)
        file_count: Current project file count
        preset_templates: Loaded preset configurations

    Returns:
        Recommended new preset name, or None if current preset still appropriate
    """

# Config upgrade prompt (new)
def prompt_config_upgrade(
    from_preset: str,
    to_preset: str,
    file_count: int
) -> bool:
    """
    Interactive prompt for config preset upgrade.

    Args:
        from_preset: Current preset
        to_preset: Recommended new preset
        file_count: Current file count

    Returns:
        True if user accepts upgrade, False otherwise
    """
```

**MCP Validation Interface** (scripts/validate_mcp.py):

```python
def validate_mcp_tool_connection(tool: str) -> ValidationResult:
    """
    Test MCP server connection for specified tool.

    Args:
        tool: One of ['claude-code', 'cursor', 'claude-desktop']

    Returns:
        ValidationResult with status, latency, error details
    """

class ValidationResult:
    status: str  # 'success', 'connection_failed', 'not_configured', 'tool_unknown'
    latency_ms: Optional[int]
    error_message: Optional[str]
    mcp_server_version: Optional[str]
```

**Performance Benchmarking Interface** (scripts/benchmark.py):

```python
def run_performance_benchmark(
    project_path: str,
    project_name: str,
    runs: int = 3
) -> PerformanceMetrics:
    """
    Run comprehensive performance benchmark on project.

    Measures:
    - Full index generation time
    - Incremental update time
    - MCP tool call latencies (4 tools)
    - Token usage per operation
    - Memory usage

    Args:
        project_path: Path to project to benchmark
        project_name: Identifier for benchmark results
        runs: Number of benchmark runs (median taken)

    Returns:
        PerformanceMetrics with all measurements
    """
```

### Workflows and Sequencing

**Installation Workflow (Story 3.1)**:

```
User runs: ./install.sh
↓
1. Check Python 3.8+ availability
   ├─ Found → Continue
   └─ Not found → Error with instructions
↓
2. Install Python dependencies from requirements.txt
   ├─ pip install mcp pydantic
   └─ Validate imports work
↓
3. Detect installed AI tools
   ├─ Check ~/.config/claude-code/mcp.json (Claude Code CLI)
   ├─ Check Cursor config location (Cursor IDE)
   └─ Check ~/Library/Application Support/Claude/ (Claude Desktop - macOS)
↓
4. Generate config preset templates
   ├─ Create ~/.claude-code-project-index/templates/
   ├─ Write small.json (threshold: <100 files)
   ├─ Write medium.json (threshold: 100-5000 files)
   └─ Write large.json (threshold: 5000+ files)
↓
5. Offer MCP registration for detected tools
   ├─ User selects tools to configure
   ├─ Write MCP server config to tool config files
   └─ Show validation command for each tool
↓
6. Setup hooks (existing logic)
   ├─ Configure UserPromptSubmit hook
   └─ Configure Stop hook
↓
7. Installation validation
   ├─ Test Python imports (mcp, pydantic)
   ├─ Test project_index.py execution
   └─ Display validation results
↓
Success: Show next steps, MCP validation commands
```

**First Index Generation with Preset Auto-Detection (Story 3.1)**:

```
User runs: /index (first time in project)
↓
1. Count project files
   ├─ Git-based discovery if available
   └─ Fallback to recursive walk
↓
2. Match file count to preset
   ├─ <100 files → small preset
   ├─ 100-5000 files → medium preset
   └─ >5000 files → large preset
↓
3. Load preset config from templates/
   └─ Apply threshold, mode, feature flags
↓
4. Generate index with preset config
   ├─ Apply split/single-file mode
   ├─ Apply tiered docs setting
   └─ Apply relevance scoring config
↓
5. Create .project-index.json in project root
   ├─ Record selected preset
   ├─ Record file count
   └─ Record timestamp
↓
6. Display preset selected and rationale
   └─ "Applied 'medium' preset (1,247 files detected)"
```

**Preset Boundary Crossing Workflow (Story 3.1)**:

```
User runs: /index (project has grown)
↓
1. Load .project-index.json
   └─ Get current preset, last file count
↓
2. Count current project files
↓
3. Check if crossed preset boundary
   ├─ Was 'small', now 120 files → 'medium' boundary
   └─ Was 'medium', now 5,200 files → 'large' boundary
↓
4. If boundary crossed:
   ├─ Backup .project-index.json → .project-index.json.backup
   ├─ Prompt user:
   │   "Your project has grown to 5,200 files.
   │    Recommend upgrading from 'medium' to 'large' preset.
   │    Upgrade now? [y/n]"
   ├─ If yes:
   │   ├─ Load new preset config
   │   ├─ Update .project-index.json
   │   ├─ Record upgrade in upgrade_history
   │   └─ Regenerate index with new settings
   └─ If no:
       └─ Continue with current preset (user override)
↓
5. Generate index with current/upgraded preset
```

**Version Update Check Workflow (Story 3.4)**:

```
User runs: /index (or any project_index.py command)
↓
1. Check if --no-update-check flag present
   ├─ Yes → Skip update check
   └─ No → Continue
↓
2. Read local VERSION file
   └─ current_version = "v0.3.0"
↓
3. Check GitHub releases API (non-blocking, timeout: 2s)
   ├─ Success:
   │   ├─ Get latest_version from releases
   │   ├─ Compare versions
   │   └─ If newer available:
   │       └─ Display: "Update available: v0.3.1
   │           Run: ./install.sh --upgrade"
   └─ Failure (timeout, no network):
       └─ Continue silently (no error)
↓
4. Continue with normal index generation
```

**Multi-Tool MCP Configuration Workflow (Story 3.5)**:

```
User runs: ./install.sh
↓
Tool Detection Phase:
├─ Claude Code CLI: Check ~/.config/claude-code/mcp.json
├─ Cursor IDE: Check platform-specific config path
└─ Claude Desktop: Check ~/Library/Application Support/Claude/ (macOS)
↓
Detected: [claude-code, cursor]
↓
Prompt: "Detected tools: Claude Code CLI, Cursor IDE
         Configure MCP server for: [1] Both  [2] Claude Code only  [3] Cursor only  [4] Manual"
↓
User selects: [1] Both
↓
For each selected tool:
├─ Read existing mcp.json (if exists)
├─ Add/update "project-index" server entry:
│   {
│     "command": "python3",
│     "args": ["/Users/{user}/.claude-code-project-index/project_index_mcp.py"],
│     "env": {}
│   }
├─ Write updated mcp.json
└─ Preserve other MCP servers (don't overwrite)
↓
Display validation commands:
  "Test Claude Code: python3 scripts/validate_mcp.py --tool=claude-code"
  "Test Cursor: python3 scripts/validate_mcp.py --tool=cursor"
```

**Performance Validation Workflow (Story 3.2)**:

```
Developer runs: python3 scripts/benchmark.py
↓
1. Select 3 test projects (stored in docs/benchmark-projects.md):
   ├─ Python project (500-1000 files)
   ├─ JavaScript/TypeScript project (1000-3000 files)
   └─ Polyglot project (2000-5000 files)
↓
2. For each project (3 runs, median taken):
   ├─ Measure full index generation time
   ├─ Make small change, measure incremental update time
   ├─ Start MCP server, measure:
   │   ├─ project_index_load_core latency
   │   ├─ project_index_load_module latency
   │   ├─ project_index_search_files latency
   │   └─ project_index_get_file_info latency
   ├─ Count tokens in MCP responses
   └─ Monitor memory usage (peak RSS)
↓
3. Write results to docs/performance-report.md
   └─ Include: metrics table, comparison to NFR targets, identified bottlenecks
↓
4. Create regression tests from baseline:
   └─ tests/test_performance.py with acceptable ranges (±10% of baseline)
```

## Non-Functional Requirements

### Performance

**NFR-P1: Installation Performance**
- Requirement: Complete installation (dependencies + config + MCP registration) within 60 seconds on typical hardware
- Target: Python dependency installation <30s, config generation <5s, MCP registration <10s, validation <15s
- Rationale: First-time setup should not frustrate users; 60s is acceptable for one-time operation
- Measurement: Time full `./install.sh` execution on 3 test machines (macOS, Linux Ubuntu, Linux Debian)
- Acceptance: 95th percentile under 60 seconds

**NFR-P2: Preset Detection Performance**
- Requirement: Project size detection and preset selection must complete within 5 seconds for projects up to 10,000 files
- Target: File counting <3s (git-based), preset matching <1s, config loading <1s
- Rationale: Preset detection happens on every `/index` run; must not add noticeable latency
- Measurement: Benchmark on projects of 100, 1000, 5000, 10000 files
- Acceptance: Linear time complexity O(n files), all sizes under 5s

**NFR-P3: Version Check Performance**
- Requirement: GitHub release check must not block index generation; timeout at 2 seconds
- Target: Network call <500ms typical, hard timeout 2s, fallback to local immediately on timeout
- Rationale: Update checking is convenience feature; must never delay core functionality
- Measurement: Test with simulated slow network (latency injection)
- Acceptance: Index generation proceeds immediately on timeout; no errors displayed

**NFR-P4: MCP Tool Validation Performance**
- Requirement: MCP connection validation must complete within 5 seconds per tool
- Target: Server startup <2s, test call <2s, result reporting <1s
- Rationale: Validation is diagnostic tool; 5s acceptable for troubleshooting workflow
- Measurement: Run `validate_mcp.py` for each tool type, measure total time
- Acceptance: All three tools validated within 15s total (5s each)

**NFR-P5: Benchmark Suite Performance** (From PRD NFR001)
- Requirement: Performance benchmark suite must complete within 30 minutes for 3 medium projects
- Target: 3 projects × 3 runs × (full generation + incremental + 4 MCP tools) = ~10 min per project
- Rationale: Developers need fast feedback; 30 min acceptable for thorough validation
- Measurement: Run `scripts/benchmark.py` with 3 real-world projects
- Acceptance: Total runtime under 30 minutes with comprehensive metrics collected

**NFR-P6: Documentation Load Performance**
- Requirement: All documentation files must load instantly in terminal viewers (cat, less)
- Target: Individual doc files <100KB, full docs directory <1MB
- Rationale: Documentation should be quickly accessible without IDE/browser
- Measurement: Check file sizes: `du -sh docs/*`
- Acceptance: No single doc file exceeds 100KB

### Security

**NFR-S1: Dependency Security**
- Requirement: All Python dependencies (`mcp`, `pydantic`) must be from trusted PyPI sources with no known critical vulnerabilities
- Control: Pin dependency versions in requirements.txt; document security update process
- Validation: Check dependencies against CVE databases before release
- Rationale: First external dependencies introduced; must maintain tool's security posture
- Acceptance: Zero critical CVEs in pinned dependencies at release time

**NFR-S2: Installation Script Safety**
- Requirement: `install.sh` must not execute arbitrary network-fetched code without explicit user consent
- Control: Download files, verify checksums, prompt before execution
- Protection: No `curl | bash` patterns; all scripts reviewed before execution
- Rationale: Installation scripts have elevated privilege; must prevent supply-chain attacks
- Acceptance: Code review confirms no remote code execution without verification

**NFR-S3: Configuration File Security**
- Requirement: Config files (.project-index.json, preset templates) must not contain sensitive data or credentials
- Control: JSON schemas exclude credential fields; documentation warns against credential storage
- Validation: Automated checks in config loading code reject any "password", "token", "secret" keys
- Rationale: Config files may be committed to version control accidentally
- Acceptance: Config parser rejects files containing credential-like fields

**NFR-S4: MCP Server Isolation**
- Requirement: MCP server must only access project files within indexed repository; no system-wide access
- Control: MCP tools operate within project root; path validation prevents directory traversal
- Validation: Security tests attempt path traversal attacks (e.g., "../../etc/passwd")
- Rationale: MCP server has read access to filesystem; must respect boundaries
- Acceptance: All path traversal attempts blocked with clear error messages

**NFR-S5: Update Mechanism Security**
- Requirement: `install.sh --upgrade` must verify downloaded files before installation
- Control: Download from official GitHub releases only (HTTPS); verify file integrity if checksums provided
- Protection: Backup current version before replacing; rollback on verification failure
- Rationale: Update mechanism is potential attack vector; must validate authenticity
- Acceptance: Failed checksum verification aborts upgrade with rollback

**NFR-S6: Version Information Disclosure**
- Requirement: Version checking must not leak sensitive project information to GitHub API
- Control: API calls contain only version string query; no project names, paths, or file counts
- Privacy: Respect --no-update-check flag for privacy-conscious users
- Rationale: Some users work on confidential projects; minimize data exposure
- Acceptance: Network traffic inspection shows only version query, no project metadata

### Reliability/Availability

**NFR-R1: Installation Failure Recovery**
- Requirement: Partial installation failures must not leave system in broken state
- Strategy: Transactional installation phases; rollback on failure
- Recovery: Each phase validates before proceeding; failed phase triggers cleanup of prior phases
- Example: If MCP registration fails, hooks are still configured; tool remains functional without MCP
- Acceptance: System remains in consistent state even if installation interrupted

**NFR-R2: Preset Upgrade Reliability**
- Requirement: Preset boundary crossing upgrades must preserve all existing configuration
- Strategy: Backup .project-index.json before upgrade; merge new preset with user customizations
- Rollback: User can revert to previous preset via backup file
- Validation: Automated tests verify no config loss during preset transitions
- Acceptance: Zero data loss across all preset upgrade scenarios

**NFR-R3: Version Update Availability**
- Requirement: Version update check failures must not impact core functionality
- Strategy: Non-blocking network calls with 2s timeout; graceful degradation on failure
- Degradation: No update info displayed, but index generation proceeds normally
- Error handling: Network failures logged to debug file, not shown to user
- Acceptance: Core operations work identically whether update check succeeds or fails

**NFR-R4: Multi-Tool MCP Resilience**
- Requirement: MCP configuration for one tool must not break configurations for other tools
- Strategy: Tool-specific config files modified independently; validation before writing
- Protection: Read existing mcp.json, preserve other servers, add/update project-index only
- Recovery: Backup created before modification; restore on invalid JSON
- Acceptance: Corrupting one tool's config does not affect other tools

**NFR-R5: Documentation Availability**
- Requirement: All documentation must be available offline; no network dependencies
- Strategy: All docs shipped with tool; embedded in installation directory
- Access: Accessible via file:// URLs, cat, less, or any text viewer
- Fallback: If docs directory missing, tool provides inline help via --help flag
- Acceptance: Full documentation accessible without internet connection

**NFR-R6: Backward Compatibility Assurance**
- Requirement: Upgrades from v0.2.x (Epic 2) must preserve all existing functionality
- Strategy: Legacy format detection maintained; migration is optional, not required
- Testing: Regression test suite validates v0.2.x indices still work with v0.3.0 code
- Documentation: Migration guide clearly explains breaking changes (if any) with workarounds
- Acceptance: All Epic 2 features work identically in Epic 3 for non-upgraded projects

### Observability

**NFR-O1: Installation Logging**
- Requirement: Installation process must log all major steps and decisions to installation log
- Location: ~/.claude-code-project-index/logs/install-{timestamp}.log
- Content: Python version detected, dependencies installed, tools detected, MCP configs written, validation results
- Retention: Keep last 10 installation logs; rotate older logs
- Purpose: Troubleshooting installation issues without verbose terminal output
- Acceptance: Complete audit trail of installation available in log file

**NFR-O2: Preset Decision Logging**
- Requirement: Preset selection and boundary crossing decisions must be logged and displayed to user
- Display: "Applied 'medium' preset (1,247 files detected)" shown during index generation
- Log: .project-index.json records preset, file count, timestamp for each decision
- History: upgrade_history array tracks all preset transitions with rationale
- Purpose: Users understand why certain optimizations applied; troubleshooting config issues
- Acceptance: Clear explanation shown for every preset decision; history retained

**NFR-O3: Version Check Observability**
- Requirement: Update check results (success/failure/update-available) must be logged
- Location: ~/.claude-code-project-index/logs/update-checks.log (append-only)
- Content: Timestamp, current version, latest version, check result, action taken
- Visibility: User sees update notification only if newer version available; failures silent
- Debug: --verbose flag shows update check details in terminal
- Acceptance: Update check history available for troubleshooting without annoying users

**NFR-O4: MCP Validation Reporting**
- Requirement: MCP connection validation must provide detailed diagnostic information
- Output: Exit code (0=success, 1=fail, 2=not-configured) + human-readable message
- Details: Tool name, config path checked, connection attempt result, latency, error message
- Example: "✓ Claude Code CLI connected (42ms) | MCP server version v0.3.0"
- Debug: --verbose shows MCP request/response for deep troubleshooting
- Acceptance: Users can diagnose MCP issues independently using validation tool

**NFR-O5: Performance Metrics Visibility**
- Requirement: Benchmark results must be human-readable and machine-parseable
- Format: Markdown table in docs/performance-report.md + JSON in docs/performance-metrics.json
- Content: Project name, stats, all measured metrics, comparison to NFR targets, pass/fail status
- Visualization: ASCII bar charts showing metric distributions across 3 test projects
- CI Integration: JSON format enables automated performance regression detection
- Acceptance: Performance report clearly shows which NFRs met and which need optimization

**NFR-O6: Error Message Quality**
- Requirement: All error messages must include clear problem description + actionable next step
- Template: "[COMPONENT] Error: {description}. Try: {suggested_action} or see: {doc_link}"
- Examples:
  - "Installation failed: pip not found. Try: Install Python 3.8+ or see: docs/troubleshooting.md#python-not-found"
  - "MCP validation failed: Connection timeout. Try: Restart tool or see: docs/mcp-setup.md#troubleshooting"
- Review: All error messages code-reviewed for clarity and helpfulness
- Acceptance: Zero error messages that just say "Error" without guidance

## Dependencies and Integrations

**Python Dependencies (requirements.txt):**

| Dependency | Version Constraint | Purpose | Introduced In | Critical? |
|------------|-------------------|---------|---------------|-----------|
| `mcp` | `>=0.1.0,<1.0.0` | MCP (Model Context Protocol) Python SDK for building MCP server | Epic 2 (Story 2.10) | Yes - Required for MCP server functionality |
| `pydantic` | `>=2.0.0,<3.0.0` | Input validation and data modeling for MCP tool parameters | Epic 2 (Story 2.10) | Yes - Required for MCP server input validation |

**Rationale for External Dependencies:**
- Epic 1 maintained zero external dependencies (Python stdlib only)
- Epic 2 introduced first external dependencies for MCP server implementation
- Decision: MCP is industry-standard protocol; implementing from scratch would duplicate significant work
- Trade-off: Added installation complexity vs. powerful standardized integration with AI tools

**System Dependencies:**

| Dependency | Version | Required? | Fallback Behavior |
|------------|---------|-----------|-------------------|
| Python | 3.8+ | Yes | Installation fails with error message |
| pip | (bundled with Python) | Yes | Installation fails; suggests manual install |
| Git | 2.0+ | No | Falls back to filesystem walk for file discovery |
| Bash | 4.0+ | Yes (Unix-like OS) | N/A - Installation scripts require bash |
| curl/wget | Any | No | Used for update downloads; manual download fallback |

**Tool Integrations:**

**1. Claude Code CLI Integration**
- **Integration Type:** MCP server registration in `~/.config/claude-code/mcp.json`
- **Configuration Format:**
  ```json
  {
    "mcpServers": {
      "project-index": {
        "command": "python3",
        "args": ["/Users/{user}/.claude-code-project-index/project_index_mcp.py"],
        "env": {}
      }
    }
  }
  ```
- **Transport:** stdio (standard input/output)
- **Bidirectional:** No - Client (Claude Code) calls server (project-index) only
- **Auto-Detection:** Check for `~/.config/claude-code/mcp.json` or `~/.config/claude-code/` directory
- **Priority:** Primary tool (most detailed documentation)

**2. Cursor IDE Integration**
- **Integration Type:** MCP server registration in Cursor-specific config location
- **Platform Variations:**
  - macOS: `~/Library/Application Support/Cursor/User/globalStorage/mcp-config.json`
  - Linux: `~/.config/Cursor/User/globalStorage/mcp-config.json`
  - Windows: `%APPDATA%\Cursor\User\globalStorage\mcp-config.json`
- **Configuration Format:** Same stdio transport as Claude Code CLI
- **Auto-Detection:** Check platform-specific paths during installation
- **Priority:** Secondary tool (standard documentation)

**3. Claude Desktop Integration**
- **Integration Type:** MCP server registration in Claude Desktop config
- **Platform Variations:**
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- **Configuration Format:** Same stdio transport as Claude Code CLI
- **Auto-Detection:** Check platform-specific paths during installation
- **Priority:** Tertiary tool (basic documentation)

**4. GitHub Releases API Integration**
- **Integration Type:** Read-only API calls for version checking
- **Endpoint:** `https://api.github.com/repos/ericbuess/claude-code-project-index/releases/latest`
- **Authentication:** None (public repository, rate-limited to 60 req/hour)
- **Timeout:** 2 seconds hard timeout
- **Error Handling:** Graceful degradation on network failure, timeout, or rate limiting
- **Privacy:** No project data sent; only version query
- **Opt-Out:** `--no-update-check` flag disables all network calls

**Integration Points Summary:**

```
┌─────────────────────────────────────────────┐
│   AI Assistant Tools (Claude Code/Cursor)   │
│                                             │
│   MCP Client calls stdio MCP server         │
└────────────────┬────────────────────────────┘
                 │ stdio transport
                 │ (JSON-RPC 2.0)
                 ↓
┌─────────────────────────────────────────────┐
│   project_index_mcp.py (MCP Server)         │
│                                             │
│   Dependencies: mcp, pydantic               │
│   Tools: load_core, load_module,            │
│          search_files, get_file_info        │
└────────────────┬────────────────────────────┘
                 │ Python imports
                 ↓
┌─────────────────────────────────────────────┐
│   scripts/loader.py, scripts/project_index.py│
│                                             │
│   Core index generation + lazy-loading      │
└────────────────┬────────────────────────────┘
                 │ File system access
                 ↓
┌─────────────────────────────────────────────┐
│   PROJECT_INDEX.json + PROJECT_INDEX.d/     │
│                                             │
│   Split index architecture (Epic 1)         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│   GitHub Releases API (Optional)            │
│                                             │
│   Version check integration                 │
└────────────────┬────────────────────────────┘
                 │ HTTPS REST API
                 │ (non-blocking)
                 ↓
┌─────────────────────────────────────────────┐
│   project_index.py --version check          │
│                                             │
│   2s timeout, graceful degradation          │
└─────────────────────────────────────────────┘
```

**Version Constraints Rationale:**

| Constraint | Rationale |
|------------|-----------|
| `mcp >=0.1.0,<1.0.0` | Pin to 0.x series; major version 1.0 may have breaking changes |
| `pydantic >=2.0.0,<3.0.0` | Use Pydantic v2 features; v3 would be breaking change |
| Python 3.8+ | Minimum for type hints, dataclasses, pathlib maturity |
| Git 2.0+ | Modern git commands (ls-files with options) |

**Dependency Update Strategy:**
1. Monitor security advisories for `mcp` and `pydantic`
2. Test updates in development environment before pinning new versions
3. Document breaking changes in CHANGELOG.md
4. Provide migration guide if dependency updates require code changes
5. Pin specific versions in requirements.txt for reproducibility

**Integration Testing Requirements:**
- Validate MCP server works with all three AI tools (Claude Code, Cursor, Claude Desktop)
- Test version checking with simulated GitHub API responses (success, timeout, rate-limited)
- Verify graceful fallback when git unavailable
- Confirm tool continues working if Python dependencies fail to import (MCP features disabled)

## Acceptance Criteria (Authoritative)

**Story 3.1: Installation Integration with Smart Config Presets**

1. `install.sh` installs Python dependencies from `requirements.txt` (including `mcp` and `pydantic`)
2. `project_index_mcp.py` copied to installation directory with correct permissions
3. Three config templates created in `~/.claude-code-project-index/templates/`:
   - `small.json` (<100 files, threshold: 100, single-file mode)
   - `medium.json` (100-5000 files, threshold: 500, split mode, tiered docs, relevance scoring enabled)
   - `large.json` (5000+ files, threshold: 1000, aggressive optimization)
4. First `/index` run auto-detects project size and creates `.project-index.json` with preset metadata
5. Subsequent `/index` runs detect if project crossed preset boundaries and prompt user for config upgrade
6. Backup created (`.project-index.json.backup`) before any automatic config changes
7. Support `--upgrade-to=preset` flag for manual preset upgrades
8. Support `--no-prompt` flag for CI/automation environments
9. `uninstall.sh` removes all MCP-related files and config templates
10. Installation validation test verifies MCP imports work correctly

**Story 3.2: Performance Validation on Medium Projects**

1. Benchmark 3 real-world medium projects (500-5000 files each):
   - One Python project
   - One JavaScript/TypeScript project
   - One polyglot project (multiple languages)
2. Measure and document:
   - Index generation time (full and incremental)
   - MCP tool call latency (load_core, load_module, search_files, get_file_info)
   - Token usage per MCP tool call
   - Memory usage during indexing and MCP serving
3. Identify and fix any performance bottlenecks discovered
4. Document performance characteristics in README (expected times per project size)
5. Create performance regression tests to catch future degradation
6. Validate incremental update performance (should be <10% of full generation time)

**Story 3.3: Comprehensive Documentation with Claude Code Focus**

1. **README.md enhanced with:**
   - Quick start section (Claude Code workflow first)
   - Performance characteristics table (project size → expected times)
   - Smart config presets explanation
   - MCP server setup (Claude Code > Cursor > Claude Desktop order)
2. **Troubleshooting guide created (`docs/troubleshooting.md`):**
   - FAQ with common issues and solutions
   - Installation validation steps
   - MCP server debugging tips
   - Clear error message reference
3. **Best practices guide created (`docs/best-practices.md`):**
   - When to use which features (tiered docs, relevance scoring, incremental updates)
   - Configuration tuning guidance (thresholds, weights)
   - Real-world usage patterns
4. **Migration guide enhanced (`docs/migration.md`):**
   - v0.1.x → v0.2.x upgrade path (Epic 1)
   - v0.2.x → v0.3.x upgrade path (Epic 2)
   - Breaking changes clearly highlighted
5. **MCP configuration guide created (`docs/mcp-setup.md`):**
   - Claude Code CLI configuration (primary, most detailed)
   - Cursor IDE configuration (secondary)
   - Claude Desktop configuration (tertiary)
   - Auto-detection behavior documented

**Story 3.4: Version Management System**

1. `--version` flag displays current version (e.g., `v0.3.0`)
2. Version stored in `~/.claude-code-project-index/VERSION` file
3. `install.sh --upgrade` mechanism downloads and installs latest version
4. Update checking on `/index` run (checks GitHub releases, shows message if newer version available)
5. Update checking respects `--no-update-check` flag for CI/automation
6. `CHANGELOG.md` created with all Epic 1, 2, 3 changes documented
7. Breaking changes clearly marked in CHANGELOG with migration notes
8. Version compatibility warnings when index format mismatches installed version
9. Rollback capability: `install.sh --rollback` restores previous version from backup
10. Release tagging process documented for maintainers

**Story 3.5: Multi-Tool MCP Support**

1. **Claude Code CLI configuration (Priority 1):**
   - Auto-detect `~/.config/claude-code/mcp.json` during install
   - Generate correct stdio transport configuration
   - Test MCP server with Claude Code CLI environment
   - Document Claude Code-specific setup steps (most detailed)
2. **Cursor IDE configuration (Priority 2):**
   - Auto-detect Cursor config location during install
   - Generate Cursor-compatible MCP configuration
   - Test MCP server with Cursor IDE
   - Document Cursor-specific setup steps
3. **Claude Desktop configuration (Priority 3):**
   - Auto-detect `~/Library/Application Support/Claude/` (macOS) during install
   - Generate Claude Desktop-compatible configuration
   - Test MCP server with Claude Desktop
   - Document Desktop-specific setup steps
4. `install.sh` detects all three tools and offers configuration for detected tools
5. Manual configuration option for tools not auto-detected
6. Validation command to test MCP server connection for each tool
7. Documentation explains differences and trade-offs between tools
8. All three tools use same MCP server implementation (stdio transport)

## Traceability Mapping

| AC ID | Acceptance Criteria | Spec Section(s) | Component(s)/API(s) | Test Idea |
|-------|-------------------|----------------|---------------------|-----------|
| **Story 3.1: Installation Integration** |
| 3.1.1 | Install Python dependencies from requirements.txt | Dependencies & Integrations | install.sh, requirements.txt (mcp, pydantic) | Execute install.sh, verify `pip list` shows mcp>=1.0.0, pydantic>=2.0.0 |
| 3.1.2 | Copy project_index_mcp.py with correct permissions | Services & Modules | install.sh, project_index_mcp.py | Check file exists at ~/.claude-code-project-index/, verify executable bit set |
| 3.1.3 | Create three config preset templates | Data Models & Contracts, Services & Modules | Config Preset Templates (small/medium/large.json) | Verify 3 JSON files created in templates/, validate against schema |
| 3.1.4 | Auto-detect project size on first run | Workflows & Sequencing | project_index.py (preset detection), .project-index.json | Run /index in test projects (50, 500, 5000 files), verify correct preset selected |
| 3.1.5 | Detect preset boundary crossing | Workflows & Sequencing | detect_preset_boundary_crossing(), prompt_config_upgrade() | Simulate project growth (add files), run /index, verify upgrade prompt appears |
| 3.1.6 | Backup created before config changes | NFR-R2 (Reliability) | .project-index.json.backup | Trigger preset upgrade, verify backup file created with timestamp |
| 3.1.7 | Support --upgrade-to=preset flag | APIs & Interfaces | project_index.py CLI | Run `project_index.py --upgrade-to=large`, verify preset applied |
| 3.1.8 | Support --no-prompt flag | APIs & Interfaces | project_index.py CLI | Run `project_index.py --no-prompt`, verify no interactive prompts shown |
| 3.1.9 | uninstall.sh removes MCP files | Services & Modules | uninstall.sh | Run uninstall.sh, verify MCP configs removed from all tool configs |
| 3.1.10 | Installation validation for MCP imports | NFR-O1 (Observability) | install.sh validation phase | Install, check logs for "mcp import: OK", "pydantic import: OK" |
| **Story 3.2: Performance Validation** |
| 3.2.1 | Benchmark 3 medium projects (Python, JS, polyglot) | Services & Modules | scripts/benchmark.py | Run benchmark suite, verify 3 projects tested with different languages |
| 3.2.2 | Measure index generation, MCP latency, tokens, memory | Data Models & Contracts (Performance Metrics) | PerformanceMetrics schema | Check docs/performance-metrics.json contains all required fields |
| 3.2.3 | Identify and fix performance bottlenecks | NFR-P5 (Performance) | Benchmark suite analysis | Review performance-report.md for identified bottlenecks and fixes applied |
| 3.2.4 | Document performance characteristics in README | Services & Modules | README.md | Verify README contains table: project size → expected generation time |
| 3.2.5 | Create performance regression tests | Services & Modules | tests/test_performance.py | Run regression tests, verify baseline comparisons with ±10% tolerance |
| 3.2.6 | Incremental update <10% of full generation time | NFR-P2 (Performance) | project_index.py (incremental updates) | Measure full vs incremental, verify ratio < 0.1 |
| **Story 3.3: Comprehensive Documentation** |
| 3.3.1 | README.md enhanced (quick start, perf table, presets, MCP setup) | Services & Modules | README.md | Review README sections, verify Claude Code workflow appears first |
| 3.3.2 | Troubleshooting guide created | Services & Modules | docs/troubleshooting.md | Open troubleshooting.md, verify FAQ, validation steps, MCP debugging present |
| 3.3.3 | Best practices guide created | Services & Modules | docs/best-practices.md | Check best-practices.md for feature usage guidance, config tuning |
| 3.3.4 | Migration guide enhanced (v0.1→v0.2→v0.3) | Services & Modules | docs/migration.md | Verify migration.md documents all 3 epic upgrades with breaking changes |
| 3.3.5 | MCP setup guide created | Services & Modules | docs/mcp-setup.md | Verify mcp-setup.md covers all 3 tools (Claude Code > Cursor > Desktop) |
| **Story 3.4: Version Management** |
| 3.4.1 | --version flag displays version | APIs & Interfaces | project_index.py --version | Run `project_index.py --version`, verify output "v0.3.0" |
| 3.4.2 | Version stored in VERSION file | Services & Modules | VERSION file | Check ~/.claude-code-project-index/VERSION contains "v0.3.0" |
| 3.4.3 | install.sh --upgrade downloads latest | APIs & Interfaces, Workflows | install.sh --upgrade | Mock GitHub API, run upgrade, verify download + install sequence |
| 3.4.4 | Update checking on /index run | Workflows & Sequencing, NFR-P3 | check_for_updates() in project_index.py | Run /index, mock GitHub API response, verify update notification shown |
| 3.4.5 | Respect --no-update-check flag | APIs & Interfaces, NFR-S6 | project_index.py --no-update-check | Run with flag, verify no network calls (packet capture) |
| 3.4.6 | CHANGELOG.md with Epic 1-3 changes | Services & Modules | CHANGELOG.md | Review CHANGELOG.md, verify sections for v0.1.x, v0.2.x, v0.3.x |
| 3.4.7 | Breaking changes marked with migration notes | Services & Modules | CHANGELOG.md | Search CHANGELOG for "BREAKING" markers, verify migration guidance present |
| 3.4.8 | Version compatibility warnings | NFR-O1 (Observability) | project_index.py version validation | Load old index format, verify warning: "Index version mismatch" |
| 3.4.9 | Rollback capability via install.sh | APIs & Interfaces, NFR-R3 | install.sh --rollback | Upgrade, then rollback, verify previous version restored |
| 3.4.10 | Release tagging process documented | Services & Modules | CHANGELOG.md or docs/ | Check for release process documentation (git tagging, GitHub release) |
| **Story 3.5: Multi-Tool MCP Support** |
| 3.5.1 | Claude Code CLI auto-detect and configure | Tool Integrations, Workflows | install.sh tool detection | Run install on system with Claude Code, verify MCP config written to ~/.config/claude-code/mcp.json |
| 3.5.2 | Cursor IDE auto-detect and configure | Tool Integrations, Workflows | install.sh tool detection | Run install on system with Cursor, verify MCP config written to Cursor config path |
| 3.5.3 | Claude Desktop auto-detect and configure | Tool Integrations, Workflows | install.sh tool detection | Run install on macOS with Claude Desktop, verify config at ~/Library/.../claude_desktop_config.json |
| 3.5.4 | Detect all three tools during install | Workflows & Sequencing | install.sh multi-tool detection | Mock all 3 tool configs present, verify install offers configuration for all |
| 3.5.5 | Manual configuration option | APIs & Interfaces | install.sh --configure-mcp=<tool> | Run `install.sh --configure-mcp=cursor` on system without auto-detected Cursor |
| 3.5.6 | Validation command tests connections | Services & Modules, NFR-O4 | scripts/validate_mcp.py | Run `validate_mcp.py --tool=claude-code`, verify exit code 0 and latency shown |
| 3.5.7 | Documentation explains tool differences | Services & Modules | docs/mcp-setup.md | Review mcp-setup.md for comparison table of Claude Code vs Cursor vs Desktop |
| 3.5.8 | All tools use same stdio MCP server | Tool Integrations | project_index_mcp.py | Verify all 3 tool configs reference same python3 project_index_mcp.py command |

## Risks, Assumptions, Open Questions

**RISK-1: External Dependency Introduction**
- **Type:** Risk
- **Description:** First external dependencies (mcp, pydantic) increase installation complexity and potential for version conflicts
- **Impact:** High - Installation failures could prevent users from adopting tool
- **Probability:** Medium - PyPI package conflicts are common in Python ecosystem
- **Mitigation:**
  - Pin specific version ranges in requirements.txt (>=X.Y.Z,<X+1.0.0)
  - Test installation on clean systems (macOS, Linux Ubuntu, Linux Debian)
  - Provide troubleshooting guide for common pip issues
  - Make MCP features optional: core tool works without mcp/pydantic (degrades to index-only mode)
- **Owner:** Story 3.1

**RISK-2: Multi-Tool Config Fragility**
- **Type:** Risk
- **Description:** MCP config file formats may differ across tools (Claude Code, Cursor, Claude Desktop) or change with tool updates
- **Impact:** High - Broken MCP configs render tool less useful
- **Probability:** Medium - Tool vendors may change config formats without notice
- **Mitigation:**
  - Version-specific config templates for each tool
  - Validation command (validate_mcp.py) detects config issues early
  - Fallback to manual configuration if auto-detection fails
  - Document config format for each tool version tested
- **Owner:** Story 3.5

**RISK-3: GitHub API Rate Limiting**
- **Type:** Risk
- **Description:** Unauthenticated GitHub API calls limited to 60 requests/hour; high-frequency users may hit limits
- **Impact:** Low - Version checking is convenience feature, not critical
- **Probability:** Low - Most users won't run /index > 60 times/hour
- **Mitigation:**
  - 2-second timeout ensures quick fallback
  - Graceful degradation: tool works without version checking
  - --no-update-check flag for users who hit limits
  - Consider caching update check results (e.g., check once per day)
- **Owner:** Story 3.4

**RISK-4: Performance Regression in Real-World Projects**
- **Type:** Risk
- **Description:** Benchmarking on 3 test projects may not catch performance issues in user's specific codebase patterns
- **Impact:** Medium - Slow index generation frustrates users
- **Probability:** Medium - Real-world projects have diverse characteristics
- **Mitigation:**
  - Select diverse test projects (Python, JS, polyglot)
  - Create performance regression tests with acceptable ranges
  - Encourage community to report performance issues
  - Document performance characteristics clearly (users know what to expect)
- **Owner:** Story 3.2

**RISK-5: Documentation Staleness**
- **Type:** Risk
- **Description:** Documentation (README, troubleshooting, mcp-setup) may become outdated as tools evolve
- **Impact:** Medium - Users struggle with installation/configuration
- **Probability:** High - Tool ecosystem changes rapidly
- **Mitigation:**
  - Date-stamp all documentation
  - Include "last verified" dates for tool-specific instructions
  - Community contributions to update docs (GitHub issues/PRs)
  - Quarterly review of documentation accuracy
- **Owner:** Story 3.3

**ASSUMPTION-1: Bash Availability**
- **Type:** Assumption
- **Description:** Assuming Bash 4.0+ is available on target systems (Unix-like OS)
- **Validation:** Test installation on macOS (bash 3.2), Linux Ubuntu (bash 5.x), Linux Debian
- **Impact if Invalid:** Installation scripts fail; users must manually configure
- **Mitigation Plan:** Consider POSIX-compliant shell scripts or Python-based installer

**ASSUMPTION-2: Internet Connectivity**
- **Type:** Assumption
- **Description:** Assuming internet access during installation for pip dependencies and update checking
- **Validation:** Test offline installation scenarios
- **Impact if Invalid:** Installation fails; update checking fails
- **Mitigation Plan:** Document offline installation (pre-download wheels); --no-update-check flag

**ASSUMPTION-3: User Permissions**
- **Type:** Assumption
- **Description:** Assuming users have write permissions to ~/.claude-code-project-index/ and tool config directories
- **Validation:** Test installation as non-admin user on locked-down systems
- **Impact if Invalid:** Installation fails with permission errors
- **Mitigation Plan:** Clear error messages suggesting `sudo` or alternative install paths

**ASSUMPTION-4: MCP Stability**
- **Type:** Assumption
- **Description:** Assuming MCP protocol and Python SDK are stable (currently 1.0+)
- **Validation:** Monitor MCP SDK releases for breaking changes
- **Impact if Invalid:** MCP server breaks with SDK updates
- **Mitigation Plan:** Pin mcp version tightly; test updates before upgrading pins

**QUESTION-1: Preset Customization**
- **Type:** Open Question
- **Description:** Should users be able to customize preset templates beyond the provided small/medium/large?
- **Options:**
  1. Allow editing JSON templates directly (simple, risky if invalid JSON)
  2. Provide CLI commands for safe preset customization
  3. Lock presets, only allow selecting from provided templates
- **Decision Needed By:** Story 3.1 implementation
- **Recommendation:** Start with option 3 (lock presets), add customization in future story if users request it

**QUESTION-2: Windows Support**
- **Type:** Open Question
- **Description:** Should Epic 3 support Windows, or remain Unix-like OS only?
- **Considerations:**
  - Bash scripts would need PowerShell equivalents or Python rewrites
  - Path handling differences (/ vs \\, ~/ vs %USERPROFILE%)
  - Testing burden increases significantly
- **Decision Needed By:** Story 3.1 (installation) and 3.5 (multi-tool config)
- **Recommendation:** Defer Windows support to Epic 4; document Unix-only requirement clearly

**QUESTION-3: Automatic Update Installation**
- **Type:** Open Question
- **Description:** Should `install.sh --upgrade` automatically install updates, or only download and prompt?
- **Options:**
  1. Auto-install (convenient, risky if breaking changes)
  2. Download + prompt user to review CHANGELOG before installing
- **Decision Needed By:** Story 3.4 implementation
- **Recommendation:** Option 2 (download + prompt) for safety; users can review changes before committing

**QUESTION-4: Telemetry/Analytics**
- **Type:** Open Question
- **Description:** Should the tool collect anonymous usage data (project sizes, feature usage) to guide future development?
- **Considerations:**
  - Privacy concerns (users work on confidential projects)
  - Value for prioritizing features
  - Complexity of implementing opt-in/opt-out
- **Decision Needed By:** Not blocking Epic 3
- **Recommendation:** Defer to future epic; focus on production readiness first

## Test Strategy Summary

**Testing Philosophy:**
Epic 3 focuses on production readiness, requiring rigorous testing of installation, configuration, performance, and documentation accuracy. Testing approach combines automated validation, manual verification, and real-world usage scenarios.

**Test Levels:**

**1. Unit Testing**
- **Scope:** Individual functions (preset detection, version checking, config parsing)
- **Tools:** Python unittest framework (existing in codebase)
- **Coverage Target:** 80% for new code (preset logic, version management, MCP validation)
- **Examples:**
  - `test_detect_preset_boundary_crossing()` - Verify preset upgrade logic
  - `test_check_for_updates()` - Mock GitHub API responses (success, timeout, 404)
  - `test_validate_mcp_tool_connection()` - Mock MCP server responses

**2. Integration Testing**
- **Scope:** Multi-component workflows (installation, preset upgrades, MCP configuration)
- **Approach:** Scripted test scenarios on clean VMs or containers
- **Test Cases:**
  - Install on clean system → Verify all components present
  - Run /index on 50, 500, 5000 file projects → Verify correct preset selected
  - Trigger preset boundary crossing → Verify backup created, prompt shown
  - Configure MCP for Claude Code → Run validate_mcp.py → Verify connection
- **Platforms:** macOS 13+, Ubuntu 22.04, Debian 11

**3. Performance Testing**
- **Scope:** Story 3.2 benchmark suite + regression tests
- **Methodology:**
  - 3 real-world medium projects (500-5000 files)
  - 3 benchmark runs per project (median taken)
  - Measure: index generation (full/incremental), MCP latency, tokens, memory
- **Acceptance:** All measurements within NFR targets (see NFR-P1 through NFR-P6)
- **Regression:** Baseline established; future runs must stay within ±10%
- **Automation:** `scripts/benchmark.py` generates JSON metrics for CI integration

**4. Documentation Testing**
- **Scope:** All documentation (README, troubleshooting, best-practices, migration, mcp-setup)
- **Method:** Manual review + automated link checking + user walkthroughs
- **Validation:**
  - Follow installation steps exactly as written → Verify success
  - Attempt documented troubleshooting steps for common issues → Verify resolution
  - Follow MCP setup for each tool (Claude Code, Cursor, Desktop) → Verify working
- **Coverage:** 100% of documented procedures must be executable

**5. Compatibility Testing**
- **Scope:** Multi-tool MCP support (Claude Code, Cursor, Claude Desktop)
- **Approach:** Test on actual installations of each tool
- **Test Matrix:**
  | Tool | Platform | Version | Status |
  |------|----------|---------|--------|
  | Claude Code CLI | macOS, Linux | Latest | Required |
  | Cursor IDE | macOS, Linux | Latest | Required |
  | Claude Desktop | macOS | Latest | Required |
- **Validation:** MCP server successfully serves requests from each tool

**6. Backward Compatibility Testing**
- **Scope:** Upgrades from v0.2.x (Epic 2) to v0.3.0 (Epic 3)
- **Approach:**
  - Generate v0.2.x index in test project
  - Upgrade to v0.3.0
  - Verify: index still loads, features still work, no data loss
- **Coverage:** All Epic 1-2 features must remain functional

**Test Execution Strategy:**

**Pre-Development:**
- Review acceptance criteria for each story
- Write failing tests first (TDD approach for critical logic)

**During Development:**
- Run unit tests continuously
- Manual smoke testing on macOS (primary dev platform)

**Pre-Story Completion:**
- All unit tests passing
- Integration tests for story passing
- Manual verification of acceptance criteria

**Pre-Epic Completion:**
- Full performance benchmark suite passing
- All documentation reviewed and tested
- Compatibility testing on all platforms/tools
- Backward compatibility validated

**Post-Epic (Release Candidate):**
- Community beta testing (5-10 users)
- Real-world usage feedback
- Performance validation on diverse codebases

**Test Data:**

**Small Project (50 files):**
- Purpose: Verify small preset selection
- Content: Minimal Python/JS project

**Medium Python Project (500-1000 files):**
- Purpose: Performance baseline, preset boundary testing
- Source: Real open-source Python project (e.g., Flask)

**Medium JS/TS Project (1000-3000 files):**
- Purpose: Multi-language performance validation
- Source: Real open-source TypeScript project (e.g., VS Code extension)

**Large Polyglot Project (2000-5000 files):**
- Purpose: Large preset validation, stress testing
- Source: Real monorepo with Python/JS/Go (e.g., monorepo example)

**Test Automation:**

```bash
# Unit tests
python3 -m unittest discover tests/

# Integration tests
./tests/integration/test_installation.sh
./tests/integration/test_preset_detection.sh
./tests/integration/test_mcp_configuration.sh

# Performance tests
python3 scripts/benchmark.py --projects=docs/benchmark-projects.json

# Backward compatibility tests
./tests/compatibility/test_v02_to_v03_upgrade.sh
```

**Success Criteria:**
- ✅ All unit tests passing (80% coverage for new code)
- ✅ All integration tests passing on 3 platforms
- ✅ Performance benchmarks meet NFR targets
- ✅ All documentation procedures verified executable
- ✅ MCP server works with all 3 tools (Claude Code, Cursor, Desktop)
- ✅ Backward compatibility confirmed (v0.2.x → v0.3.0)
- ✅ Zero critical bugs identified in beta testing

**Risk-Based Testing Prioritization:**
1. **Critical:** Installation, preset detection, MCP configuration (highest user impact)
2. **High:** Performance validation, version management (user experience)
3. **Medium:** Documentation accuracy, multi-tool support (usability)
4. **Low:** Edge cases, cosmetic issues (polish)

**Test Exit Criteria:**
- All critical and high priority tests passing
- No blocker or critical severity bugs open
- Performance regression tests establish baseline
- Documentation walkthroughs complete successfully
- At least 3 beta users report successful installation and usage
