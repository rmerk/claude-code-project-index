# Project Index for Claude Code

**⚠️ Beta Community Tool - Let Claude Code Fork It!** This is my personal indexing solution that I'm sharing (still in beta). I'm not maintaining this as a product. If you run into issues, have Claude Code help you fix them! Give this repo URL to Claude and ask it to fork, set up, and adapt it for your specific needs.

## Background

I created this tool for myself and talked about it in [this video](https://www.youtube.com/watch?v=JU8BwMe_BWg) and [this X post](https://x.com/EricBuess/status/1955271258939043996). People requested it, so here it is! This works alongside my [Claude Code Docs mirror](https://github.com/ericbuess/claude-code-docs) project.

I may post videos explaining how I use this project - check [my X/Twitter](https://x.com/EricBuess) for updates and explanations.

This isn't a product - just a tool that solves Claude Code's architectural blindness for me. Fork it, improve it, make it yours!

Automatically gives Claude Code architectural awareness of your codebase. Add `-i` to any prompt to generate or update a PROJECT_INDEX.json containing your project's functions, classes, and structure.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

## Usage

Just add `-i` to any Claude prompt:

```bash
claude "fix the auth bug -i"          # Auto-creates/uses index (default 50k)
claude "refactor database code -i75"  # Target ~75k tokens (if project needs it)
claude "analyze architecture -ic200"  # Export up to 200k to clipboard for external AI

# Or manually create/update the index anytime
/index
```

**Key behaviors:**
- **One-time setup**: Use `-i` once in a project and the index auto-updates forever
- **Size memory**: The number (e.g., 75) is remembered until you specify a new one
- **Auto-maintenance**: Every file change triggers automatic index updates
- **To stop indexing**: Simply delete PROJECT_INDEX.json

## What It Does

PROJECT_INDEX extracts and tracks:
- **Functions & Classes**: Full signatures with parameters and return types
- **Call Relationships**: Which functions call which others
- **File Organization**: All code files respecting .gitignore
- **Directory Structure**: Project layout with file counts

This helps Claude:
- Find the right code without searching
- Understand dependencies before making changes
- Place new code in the correct location
- Avoid creating duplicate functions

## NEW: MCP Server Support (Optional)

**⚡ Epic 2 Feature** - Expose your project index as an MCP (Model Context Protocol) server for advanced AI agent integration.

### What is MCP?

MCP (Model Context Protocol) allows AI agents to interact with your project index through standardized tool interfaces. Instead of loading the entire index, agents can query exactly what they need through dedicated tools.

### Quick Start

```bash
# Install MCP dependencies (first external dependency for this project)
pip install -r requirements.txt

# Run the MCP server
python project_index_mcp.py
```

### Available Tools

The MCP server provides 4 core tools:

1. **`project_index_load_core`** - Load lightweight core index with file tree and module references
2. **`project_index_load_module`** - Lazy-load specific detail modules (e.g., "scripts", "auth")
3. **`project_index_search_files`** - Search for files by path pattern with pagination
4. **`project_index_get_file_info`** - Get detailed information about a specific file

### Integration with Claude Desktop

Add to your Claude Desktop MCP configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "project-index": {
      "command": "python",
      "args": ["/path/to/your/project/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

### Benefits

- **Faster queries** - Load only relevant modules instead of entire index
- **Standardized interface** - Works with any MCP-compatible AI client
- **Future-proof** - Built on Anthropic's MCP protocol standard
- **Multiple output formats** - JSON for programmatic use, Markdown for readability

### Requirements

- Python 3.12+
- MCP Python SDK (`pip install mcp`)
- Pydantic v2 (auto-installed with MCP SDK)

**Note:** The MCP server is optional. Core indexing functionality remains dependency-free and uses Python stdlib only.

## Three Ways to Use

### Small Projects - Direct Reference with `@PROJECT_INDEX.json`
```bash
# Reference directly in your prompt
@PROJECT_INDEX.json what functions call authenticate_user?

# Or auto-load in every session by adding to CLAUDE.md:
# Add @PROJECT_INDEX.json to your CLAUDE.md file
```

**Best for**: Small projects where the index fits comfortably in context. Gives Claude's main agent direct awareness of your whole project structure.

### Medium Projects - Subagent Mode with `-i` flag
```bash
# Invokes specialized subagent to analyze PROJECT_INDEX.json
claude "refactor the auth system -i"   # Default up to 50k tokens
claude "find performance issues -i75"  # Target ~75k tokens for more detail
```

**Best for**: Medium to large projects where you want to preserve the main agent's context. The subagent analyzes the index separately and returns only relevant findings.

The subagent provides:
- Call graph analysis and execution paths
- Dependency mapping and impact analysis
- Dead code detection
- Strategic recommendations on where to make changes

### Large Projects - Clipboard Export with `-ic` flag
```bash
# Export to clipboard for external AI with larger contexts
claude "analyze entire codebase -ic200"  # Up to 200k tokens
claude "architecture review -ic800"      # Up to 800k tokens
```

**Best for**: Very large projects whose index won't fit in Claude's context window. Export to AI models with larger context windows:
- Gemini Pro (2M tokens)
- Claude models with 200k+ tokens
- ChatGPT
- Grok

**Note**: I'm not using this on large projects myself yet - this is inspiration/theory. Your mileage may vary. If you hit snags, have Claude Code update it to work for your specific use case!

## Token Sizing

The number after `-i` is a **maximum target**, not a guaranteed size:

- **Default**: 50k tokens (remembered per project)
- **-i mode range**: 1k to 100k maximum
- **-ic mode range**: 1k to 800k maximum for external AI
- **Actual size**: Often much smaller - only uses what the project needs
- **Compression**: Automatic to fit within limits

Examples:
- Small project with `-i200`: Might only generate 10k tokens
- Large project with `-i50`: Compresses to fit ~50k target
- Huge project with `-ic500`: Allows up to 500k if needed

The tool remembers your last `-i` size per project and targets that amount, but actual size depends on your codebase.

## Language Support

**Full parsing** (extracts functions, classes, methods):
- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Shell scripts (.sh, .bash)

**File tracking** (listing only):
- Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin, and 20+ more

## Installation Details

- **Location**: `~/.claude-code-project-index/`
- **Hooks configured**:
  - `UserPromptSubmit`: Detects -i flag
  - `Stop`: Refreshes index after session
- **Commands**: `/index` for manual creation/update
- **Agent**: `~/.claude/agents/index-analyzer.md` for deep analysis
- **Python**: Automatically finds newest 3.8+ version

## Fork & Customize

**The whole point of this tool is that Claude Code can unbobble it for you!** When you hit issues, don't wait for me - have Claude fix them immediately. This is a community tool meant to be forked and adapted.

How to customize:
1. Fork the repo or work with the installed version
2. Describe your problem to Claude Code 
3. Let Claude modify it for your exact needs
4. Share your improvements with others

Common customizations:
```bash
cd ~/.claude-code-project-index
# Then ask Claude:
# "The indexer hangs on my 5000 file project - fix it"
# "Add support for Ruby and Go files with full parsing"
# "Skip test files and node_modules even if not in .gitignore"
# "Make it work with my monorepo structure"
# "Change compression to handle my specific project better"
```

Remember: Claude Code can rewrite this entire tool in minutes to match your needs. That's the power you have - use it!

## Known Issues & Quick Fixes

**Large projects (>2000 files)**: May timeout or hang during compression
- Fix: Ask Claude "Rewrite compress_if_needed() to handle my 3000 file project"

**.claude directory**: Already fixed - now excluded from indexing

**Timeouts**: Default is 30 seconds, may be too short for huge projects
- Fix: Ask Claude "Make timeout dynamic based on file count in i_flag_hook.py"

For any issue, just describe it to Claude and let it fix the tool for you!

## Requirements

### Core Indexing (No External Dependencies)
- Python 3.8 or higher
- Claude Code with hooks support
- macOS or Linux
- git and jq (for installation)

### MCP Server (Optional - Requires External Dependencies)
- Python 3.12 or higher
- MCP Python SDK: `pip install -r requirements.txt`
- See "MCP Server Support" section above for details

## Troubleshooting

### Common Issues

**Index not creating?**
- Check Python: `python3 --version` (need 3.8+)
- Verify hooks: `cat ~/.claude/settings.json | grep i_flag_hook`
- Manual generation: `python3 ~/.claude-code-project-index/scripts/project_index.py`
- Check for errors: `python3 ~/.claude-code-project-index/scripts/project_index.py 2>&1 | tee index.log`

**-i flag not working?**
- Run installer again: `curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash`
- Check hooks are configured: `cat ~/.claude/settings.json | jq .hooks`
- Remove and reinstall if needed

**Clipboard issues?**
- Install pyperclip: `pip install pyperclip`
- SSH users: Content saved to `.clipboard_content.txt`
- For unlimited clipboard over SSH: [VM Bridge](https://github.com/ericbuess/vm-bridge)

**Index too large (>1 MB)?**
```bash
# Solution 1: Use split format (recommended for large projects)
python scripts/project_index.py --mode split

# Solution 2: Reduce threshold to trigger split mode earlier
python scripts/project_index.py --threshold 500

# Solution 3: Configure via config file
echo '{"mode": "split", "threshold": 500}' > .project-index.json
python scripts/project_index.py
```

**Module not found error with split format?**
```bash
# Verify PROJECT_INDEX.d/ directory exists
ls -la PROJECT_INDEX.d/

# Regenerate split index if corrupted
rm -rf PROJECT_INDEX.d/
python scripts/project_index.py --mode split

# Check module name format (should be: dirname.json or dirname-subdirname.json)
ls PROJECT_INDEX.d/*.json
```

**Migration failed?**
```bash
# Check backup exists
ls -la PROJECT_INDEX.json.backup-*

# Restore from backup
cp PROJECT_INDEX.json.backup-* PROJECT_INDEX.json
rm -rf PROJECT_INDEX.d/

# Try migration again with dry-run first
python scripts/project_index.py --migrate --dry-run
python scripts/project_index.py --migrate
```

**Auto-detection using wrong format?**
```bash
# Check file count (split mode triggers at >1000 files by default)
git ls-files | wc -l

# Force desired format explicitly
python scripts/project_index.py --mode split    # Force split
python scripts/project_index.py --mode single   # Force single-file

# Or configure threshold
python scripts/project_index.py --threshold 500  # Split at >500 files
```

**Configuration file not working?**
```bash
# Verify file location and name
ls -la .project-index.json

# Check JSON syntax
python3 -m json.tool .project-index.json

# Verify configuration is loaded (look for "config file" in output)
python scripts/project_index.py | grep "config file"

# CLI flags override config file
python scripts/project_index.py --mode split  # This wins over config file
```

### Performance Tuning

**Large project (>2000 files) taking too long?**
- Use split format: `--mode split`
- Skip detail generation initially: `--skip-details`
- Adjust threshold: `--threshold 500`

**Memory issues during indexing?**
- Use split format (lower memory footprint)
- Close other applications
- Process in chunks (split format automatically does this)

**Slow lazy-loading?**
- Check disk I/O (PROJECT_INDEX.d/ should be on fast storage)
- Verify module files are not corrupted: `ls -lh PROJECT_INDEX.d/`
- Regenerate if needed: `rm -rf PROJECT_INDEX.d/ && python scripts/project_index.py --mode split`

### Configuration Examples for Different Project Sizes

**Small project (<500 files):**
```json
{
  "mode": "single"
}
```

**Medium project (500-2000 files):**
```json
{
  "mode": "auto",
  "threshold": 1000
}
```

**Large project (2000-5000 files):**
```json
{
  "mode": "split",
  "threshold": 500
}
```

**Very large project (>5000 files):**
```json
{
  "mode": "split",
  "threshold": 200
}
```

### FAQ

**Q: Can I use both legacy and split formats in the same project?**
A: No, you must choose one format. However, you can migrate between them at any time with `--migrate`.

**Q: Do I need to delete the old index before changing formats?**
A: No, the indexer will detect and regenerate automatically. Use `--migrate` to preserve data during transition.

**Q: How do I know which format I'm currently using?**
A: Check for `PROJECT_INDEX.d/` directory. If it exists and `version: "2.0-split"` is in PROJECT_INDEX.json, you're using split format.

**Q: Can I commit PROJECT_INDEX.d/ to git?**
A: Yes, you can commit both PROJECT_INDEX.json and PROJECT_INDEX.d/ for team consistency. Add `.project-index.json` to configure team defaults.

**Q: Does split format work with the -i flag?**
A: Yes! The -i flag works transparently with both formats. The index-analyzer agent detects format automatically.

**Q: What happens if I delete PROJECT_INDEX.d/?**
A: Next indexer run will regenerate it if split mode is enabled. No data loss, just slower first run.

## Technical Details

The index uses a compressed format to save ~50% space:
- Minified JSON (single line) for file storage
- Short keys: `f`→files, `g`→graph, `d`→docs, `deps`→dependencies
- Compact function signatures with line numbers
- Clipboard mode (`-ic`) uses readable formatting for external AI tools

## Split Index Architecture

For projects with 1000+ files, PROJECT_INDEX automatically uses a **split architecture** that separates your index into:

### Core Index (PROJECT_INDEX.json)
- **Lightweight navigation structure** (~90 KB for 10,000 files)
- Project tree, file list, module organization
- Function/class signatures (without bodies)
- Call graph and dependency edges
- Fast to load and parse

### Detail Modules (PROJECT_INDEX.d/)
- **On-demand deep details** (loaded only when needed)
- Full function bodies and docstrings
- File-level metadata and git history
- Implementation details for code analysis
- One module per logical directory

### Benefits

**For Small Queries:**
```bash
claude "where is the login function? -i"
```
→ Uses only core index (90 KB), loads in milliseconds

**For Deep Analysis:**
```bash
claude "analyze the auth module implementation -i"
```
→ Core index + auth detail module (~200 KB), still fast

**For Exploration:**
```bash
claude "find all database queries -i"
```
→ Core index identifies relevant modules, loads only those needed

### Visual Comparison

**Single-File Format (Legacy):**
```
PROJECT_INDEX.json (2.3 MB)
├── All function signatures
├── All function bodies
├── All documentation
├── All metadata
└── Call graph and dependencies
```
*Every query loads the entire 2.3 MB*

**Split Format (v2.0):**
```
PROJECT_INDEX.json (95 KB - Core)
├── Module organization
├── Function signatures
├── Call graph structure
└── File tree

PROJECT_INDEX.d/ (2.2 MB - Details)
├── scripts.json (auth, utils functions)
├── src-api.json (API routes, handlers)
├── src-components.json (React components)
└── ... (loaded on-demand)
```
*Most queries load only 95 KB, selective queries load specific modules*

### When to Use Each Format

**Use Single-File Format (v1.0) when:**
- Project has < 1000 files
- You want maximum simplicity
- You don't need lazy-loading
- Fast enough for your workflow

**Use Split Format (v2.0) when:**
- Project has > 1000 files
- You want faster analysis times
- Memory efficiency matters
- Working with monorepos or large codebases

**Auto-detection handles this automatically** - just run `python scripts/project_index.py` and it chooses the best format for your project size.

## Tiered Documentation Storage

For documentation-heavy projects, PROJECT_INDEX uses **tiered storage** to achieve 60-80% compression by separating documentation into priority levels.

### How It Works

Documentation is classified into three tiers based on importance and access frequency:

**Critical Tier** (loaded by default):
- README files (README.md, README-*.md)
- Architecture documentation (ARCHITECTURE.md, docs/architecture/*)
- API documentation (API.md, docs/api/*)
- Security documentation (SECURITY.md)
- Contributing guidelines (CONTRIBUTING.md)

**Standard Tier** (loaded on-demand):
- Development guides (docs/development/*)
- Setup instructions (INSTALL.md, SETUP.md, docs/setup/*)
- How-to guides (docs/guides/*, docs/how-to/*)

**Archive Tier** (loaded on-demand):
- Tutorials (docs/tutorials/*)
- Changelogs (CHANGELOG.md, HISTORY.md)
- Meeting notes (docs/meetings/*)
- Archived documentation (docs/archive/*)

### Storage Strategy

**With Tiered Storage (default):**
```
PROJECT_INDEX.json (Core Index)
├── d_critical: {README.md, ARCHITECTURE.md, API.md}
└── (Standard and Archive tiers excluded)

PROJECT_INDEX.d/ (Detail Modules)
├── scripts.json
│   ├── doc_standard: {setup-guide.md}
│   └── doc_archive: {changelog.md}
└── docs.json
    ├── doc_standard: {development-guide.md}
    └── doc_archive: {tutorials/intro.md}
```

**Without Tiered Storage (small projects):**
```
PROJECT_INDEX.json (Core Index)
├── d_critical: {README.md, ARCHITECTURE.md, API.md}
├── d_standard: {setup-guide.md, development-guide.md}
└── d_archive: {changelog.md, tutorials/intro.md}
```

### Configuration

Control tiered storage behavior through `.project-index.json`:

```json
{
  "include_all_doc_tiers": false
}
```

**Options:**

- **`false` (default)** - Tiered mode for doc-heavy projects
  - Only critical tier docs in core index
  - Standard and archive tiers in detail modules
  - Achieves 60-80% compression
  - Best for projects with extensive documentation

- **`true`** - All tiers in core for small projects
  - All documentation tiers included in core index
  - No separation into detail modules
  - Simpler structure, no lazy-loading needed
  - Best for projects with minimal documentation

### Agent Usage

**Loading Critical Documentation (automatic):**
```python
# Critical docs are always available in core index
core_index = json.load(open("PROJECT_INDEX.json"))
critical_docs = core_index["d_critical"]
# {README.md: ["Section1", "Section2"], ARCHITECTURE.md: [...]}
```

**Loading Standard or Archive Tiers:**
```python
from scripts.loader import load_doc_tier

# Load standard tier from specific module
standard_docs = load_doc_tier("standard", "scripts")
# Returns standard tier docs from scripts.json only

# Load archive tier from all modules
archive_docs = load_doc_tier("archive")
# Returns archive tier docs aggregated across all modules
```

### Compression Benefits

For a project with 100 markdown files (10 critical, 40 standard, 50 archive):

**Without tiered storage:**
- Core index size: 16,381 bytes (all docs included)

**With tiered storage:**
- Core index size: 6,367 bytes (only critical docs)
- **Compression: 61.1%** (within 60-80% target)

The larger your documentation, the greater the benefit:
- 200 markdown files: ~65% compression
- 500 markdown files: ~70% compression
- 1000+ markdown files: ~75% compression

### When to Enable Tiered Storage

**Use Tiered Storage (include_all_doc_tiers: false) when:**
- Project has 50+ markdown files
- Documentation represents >30% of your project
- You want faster initial load times
- Working with extensive docs (API references, tutorials, guides)

**Use All Tiers in Core (include_all_doc_tiers: true) when:**
- Project has <20 markdown files
- Documentation is minimal
- You want maximum simplicity
- All docs are equally important

### Example Configuration

```json
{
  "mode": "split",
  "threshold": 1000,
  "include_all_doc_tiers": false
}
```

See `docs/.project-index.json.example` for complete configuration examples.

## Configuration Options

Control index generation behavior through CLI flags or a configuration file.

### Command-Line Flags

```bash
# Mode selection
python scripts/project_index.py --mode auto       # Auto-detect based on file count (default)
python scripts/project_index.py --mode split      # Force split format
python scripts/project_index.py --mode single     # Force single-file format

# Threshold customization
python scripts/project_index.py --threshold 500   # Use split mode for >500 files (default: 1000)

# Migration and utilities
python scripts/project_index.py --migrate         # Migrate existing index to split format
python scripts/project_index.py --dry-run         # Preview migration (use with --migrate)
python scripts/project_index.py --skip-details    # Generate core index only (no detail modules)
python scripts/project_index.py --version         # Show version
python scripts/project_index.py --help            # Show help message
```

### Configuration File

Create `.project-index.json` in your project root to set default options:

```json
{
  "mode": "auto",
  "threshold": 1000,
  "max_index_size": 1048576,
  "compression_level": "standard"
}
```

**Configuration Fields:**

- **`mode`** - Index generation mode
  - `"auto"` (default) - Auto-detect based on file count
  - `"split"` - Always use split format
  - `"single"` - Always use single-file format

- **`threshold`** - File count threshold for auto-detection (default: 1000)
  - Split mode triggers when file count > threshold
  - Only applies when mode is "auto"

- **`max_index_size`** - Maximum index size in bytes (default: 1048576 = 1 MB)
  - Applies to single-file format only
  - Triggers compression when exceeded

- **`compression_level`** - Compression strategy (default: "standard")
  - `"standard"` - Balance between size and readability
  - `"aggressive"` - Maximum compression (future support)

**Configuration Schema:**

The configuration file must be valid JSON. The indexer validates all fields and ignores invalid values with warnings:

```json
{
  "mode": "auto" | "split" | "single",     // Required: string, one of three values
  "threshold": 1000,                        // Required: positive integer
  "max_index_size": 1048576,               // Optional: positive integer (bytes)
  "compression_level": "standard"           // Optional: "standard" or "aggressive"
}
```

**Validation Rules:**

- Invalid `mode` values → Ignored, uses default ("auto")
- Invalid `threshold` (non-numeric or ≤ 0) → Ignored, uses default (1000)
- Corrupted JSON → Entire file ignored, uses all defaults with warning
- Missing file → No error, uses all defaults
- Extra fields → Ignored (future compatibility)

**Validation Examples:**

```bash
# Valid configuration
echo '{"mode": "split", "threshold": 500}' > .project-index.json
python scripts/project_index.py
# ✅ Uses split mode with threshold 500

# Invalid mode
echo '{"mode": "invalid"}' > .project-index.json
python scripts/project_index.py
# ⚠️  Warning: Invalid mode 'invalid' in config file, ignoring
# ✅ Uses default mode (auto)

# Invalid threshold
echo '{"threshold": "not a number"}' > .project-index.json
python scripts/project_index.py
# ⚠️  Warning: Invalid threshold 'not a number' in config file, ignoring
# ✅ Uses default threshold (1000)

# Corrupted JSON
echo '{broken json}' > .project-index.json
python scripts/project_index.py
# ⚠️  Warning: Corrupted config file: ...
# ⚠️  Falling back to defaults
# ✅ Uses all defaults (mode=auto, threshold=1000)
```

**Configuration Precedence:**

Settings are resolved in this order (highest to lowest priority):

1. **CLI flags** (`--mode`, `--threshold`) - Highest priority
2. **Configuration file** (`.project-index.json` in current directory)
3. **System defaults** (`mode=auto`, `threshold=1000`) - Lowest priority

Examples:

```bash
# Config file has "mode": "single", but CLI flag wins
python scripts/project_index.py --mode split

# Config file has "threshold": 500, but CLI flag wins
python scripts/project_index.py --threshold 2000
```

**Configuration File Location:**

The indexer searches for `.project-index.json` in the **current working directory only**. If you have nested projects with different configuration needs:

```bash
# Parent project uses single-file mode
cd /path/to/parent-project
echo '{"mode": "single"}' > .project-index.json
python scripts/project_index.py

# Child project uses split mode
cd /path/to/parent-project/child-project
echo '{"mode": "split"}' > .project-index.json
python scripts/project_index.py
```

Each directory can have its own `.project-index.json` - just run the indexer from that directory.

**Example Configurations:**

```json
// Small team project - force single-file for simplicity
{
  "mode": "single"
}

// Large monorepo - aggressive split mode
{
  "mode": "split",
  "threshold": 500
}

// Default auto-detection with custom threshold
{
  "mode": "auto",
  "threshold": 1500
}
```

**Location:** Place `.project-index.json` in your project root (same directory as PROJECT_INDEX.json)

See `docs/.project-index.json.example` for a complete example.

## Temporal Awareness

**NEW in Epic 2** - The index-analyzer agent now prioritizes recently changed files to help you focus on active development areas.

### What is Temporal Awareness?

Temporal awareness uses git metadata to automatically identify and prioritize files based on when they were last changed. This helps you:

- Quickly find recent changes without searching commit history
- Focus debugging on recently modified code
- Get faster answers when working on active features
- Understand which parts of the codebase are "hot" (actively changing)

### How It Works

**Automatic Recency Weighting:**
When you use the `-i` flag, the agent automatically gives higher priority to recently changed files:
- Files changed in last 7 days: **5x weight boost**
- Files changed in last 30 days: **2x weight boost**
- Files older than 30 days: normal weight

```bash
# Agent automatically prioritizes recent files
claude "analyze the auth system -i"
# → Agent focuses on recently changed auth files first
```

**Temporal Queries (Fast Path):**
Ask about recent changes directly - these queries use git metadata WITHOUT loading detail modules, giving you instant answers:

```bash
# Show files changed in last 7 days
claude "show recent changes -i"

# What changed recently?
claude "what changed in the last week? -i"

# Find recent updates
claude "show me what's been updated -i"
```

**Recency Information in Responses:**
The agent automatically includes when files were last changed:

```
- **File**: scripts/relevance.py 🕐 **Last changed 2 days ago**
  - `score_module()` [line 75] - Multi-signal relevance scoring
  - Introduced temporal weighting for recent files

- **File**: agents/index-analyzer.md 🕐 **Last changed 5 days ago**
  - Enhanced with temporal awareness capabilities
```

### Configuration

You can customize temporal weighting through `.project-index.json`:

```json
{
  "mode": "auto",
  "threshold": 1000,
  "temporal_weights": {
    "explicit_file_ref": 10.0,
    "temporal_recent": 5.0,
    "temporal_medium": 2.0,
    "keyword_match": 1.0
  }
}
```

**Temporal Weight Options:**
- **`explicit_file_ref`** (default: 10.0) - Files explicitly mentioned by path (highest priority)
- **`temporal_recent`** (default: 5.0) - Files changed in last 7 days
- **`temporal_medium`** (default: 2.0) - Files changed in last 30 days
- **`keyword_match`** (default: 1.0) - Files matching query keywords

**Example Customization:**

```json
{
  "temporal_weights": {
    "temporal_recent": 8.0,
    "temporal_medium": 3.0
  }
}
```

This configuration makes the agent even more aggressive about prioritizing recent changes.

### When is Temporal Awareness Most Useful?

**Debugging Production Issues:**
```bash
claude "find the bug in payment processing -i"
# → Agent prioritizes recently changed payment code
```

**Reviewing Recent Work:**
```bash
claude "show recent changes -i"
# → Instant list of files changed in last 7 days
```

**Understanding Active Features:**
```bash
claude "what's being worked on? -i"
# → Agent identifies recently modified modules
```

**Focusing Code Reviews:**
```bash
claude "analyze recent auth changes -i"
# → Agent loads and analyzes recently changed auth files
```

### Performance

Temporal queries ("show recent changes") are **extremely fast** because they:
- Use only the core index (no detail module loading)
- Filter files directly from git metadata
- Return results in milliseconds, even for large projects

Regular queries also benefit from temporal awareness:
- Relevance scoring completes in <100ms for 1,000 modules
- Recent files automatically bubble to the top of results
- No performance penalty for temporal weighting

### Requirements

Temporal awareness requires:
- Git repository (uses `git log` for metadata)
- Python 3.8+ (no external dependencies)
- Core index with git metadata (automatically included)

Files without git metadata (uncommitted changes, new files) are handled gracefully with normal priority.

## Backward Compatibility

The indexer supports two format versions to balance performance and compatibility:

### Format Versions

**Legacy Format (v1.0)** - Single-file index
- **Best for**: Projects with < 1000 files
- **Storage**: All data in PROJECT_INDEX.json
- **Performance**: Loads entire index at once
- **Status**: Fully supported, no deprecation planned

**Split Format (v2.0-split)** - Multi-file index
- **Best for**: Projects with > 1000 files
- **Storage**: Core index (PROJECT_INDEX.json) + detail modules (PROJECT_INDEX.d/)
- **Performance**: Lazy-loading for faster analysis
- **Status**: Recommended for large projects

### Auto-Detection

The system automatically detects your format:
- Checks for PROJECT_INDEX.d/ directory existence
- Validates `version` field in PROJECT_INDEX.json
- Falls back to legacy format if uncertain

### Format Selection

Control which format to use:

```bash
# Auto-detect (default) - uses split for >1000 files, legacy otherwise
python scripts/project_index.py

# Force legacy format (single-file)
python scripts/project_index.py --format=legacy

# Force split format (multi-file)
python scripts/project_index.py --format=split
```

### Migration from Legacy to Split Format

If you have an existing legacy index (v1.0) and want to migrate to the split format:

```bash
# Preview migration without making changes (dry-run)
python scripts/project_index.py --migrate --dry-run

# Automated migration (recommended)
python scripts/project_index.py --migrate
```

**Migration Options:**

- `--migrate` - Perform the migration from legacy to split format
- `--migrate --dry-run` - Preview what will happen without making any changes

**What the migration does:**

1. **Creates backup** - Saves your original index as `PROJECT_INDEX.json.backup-[timestamp]`
2. **Converts format** - Transforms single-file → split format (core + modules)
3. **Validates integrity** - Ensures zero information loss with hash validation
4. **Reports results** - Shows size comparison and module count
5. **Auto-rollback** - Restores original if any errors occur

**Migration output example:**

```
🔄 Starting migration to split format...
   📋 Step 1/6: Detecting index format...
      ✓ Detected legacy format (v1.0)
   💾 Step 2/6: Creating backup...
      ✓ Backup created: PROJECT_INDEX.json.backup-2025-11-01-123456
   📖 Step 3/6: Loading legacy index...
      ✓ Loaded legacy index (450.2 KB)
   ⚙️  Step 4/6: Generating split format...
      ✓ Generated core index (85.3 KB)
      ✓ Generated 12 detail modules (365.8 KB)
   🔍 Step 5/6: Validating migration integrity...
      ✓ File count: 847 files preserved
      ✓ Function count: 1,243 functions preserved
      ✓ Class count: 156 classes preserved
      ✓ Call graph: 2,891 edges preserved
   ✅ Migration completed successfully!

📊 Migration Summary:
   Legacy format:  450.2 KB (single file)
   Split format:   85.3 KB core + 365.8 KB modules (451.1 KB total)
   Modules:        12 detail modules created
   Backup:         PROJECT_INDEX.json.backup-2025-11-01-123456

💡 Your index is now optimized for large projects!
   • Core index stays lightweight for quick navigation
   • Detail modules load on-demand for deep analysis
```

**Large Project Support (>5000 files):**

For very large projects, the migration automatically shows detailed progress:

```
   📖 Step 3/6: Loading legacy index...
      ✓ Loaded legacy index (2.3 MB, 8,547 files)
      ℹ️  Large project detected - showing detailed progress...
   ⚙️  Step 4/6: Generating split format...
      📊 Processing 8,547 files...
      ✓ Generated core index (95.2 KB)
      ✓ Generated 45 detail modules (2.2 MB)
      📊 Created modules in PROJECT_INDEX.d/
   🔍 Step 5/6: Validating migration integrity...
      📊 Validating 8,547 files across 45 modules...
      📊 Loading module 1/45...
      📊 Loading module 11/45...
      ...
```

**Rollback if needed:**

If migration fails or you want to revert:

```bash
# Restore from the most recent backup
cp PROJECT_INDEX.json.backup-* PROJECT_INDEX.json
rm -rf PROJECT_INDEX.d/
```

**Alternative migration methods:**

```bash
# Option 1: Auto-migration (if >1000 files, auto-converts on next index generation)
python scripts/project_index.py

# Option 2: Explicitly request split format (regenerates from scratch)
python scripts/project_index.py --format=split
```

**Benefits of split format for large projects:**
- Faster analysis through lazy-loading
- Reduced memory usage
- Better performance with 1000+ files
- Modules load on-demand based on query relevance
- Core index stays under 100KB for 10,000 file projects

**When to stay on legacy format:**
- Small to medium projects (<1000 files)
- Preference for simplicity
- No performance issues with current setup

**Data integrity guarantee:** The migration process validates 100% data preservation. All files, functions, classes, call graphs, and documentation are verified to match exactly. If validation fails, the migration automatically rolls back.

The agent automatically adapts to whichever format you use - no configuration needed!

## Uninstall

```bash
~/.claude-code-project-index/uninstall.sh
```

---
Created by [Eric Buess](https://github.com/ericbuess)
- 🐦 [Twitter/X](https://x.com/EricBuess)
- 📺 [YouTube](https://www.youtube.com/@EricBuess)
- 💼 [GitHub](https://github.com/ericbuess)