# Project Index for Claude Code

**⚠️ Beta Community Tool - Let Claude Code Fork It!** This is my personal indexing solution that I'm sharing (still in beta). I'm not maintaining this as a product. If you run into issues, have Claude Code help you fix them! Give this repo URL to Claude and ask it to fork, set up, and adapt it for your specific needs.

## Background

I created this tool for myself and talked about it in [this video](https://www.youtube.com/watch?v=JU8BwMe_BWg) and [this X post](https://x.com/EricBuess/status/1955271258939043996). People requested it, so here it is! This works alongside my [Claude Code Docs mirror](https://github.com/ericbuess/claude-code-docs) project.

I may post videos explaining how I use this project - check [my X/Twitter](https://x.com/EricBuess) for updates and explanations.

This isn't a product - just a tool that solves Claude Code's architectural blindness for me. Fork it, improve it, make it yours!

Automatically gives Claude Code architectural awareness of your codebase. Add `-i` to any prompt to generate or update a PROJECT_INDEX.json containing your project's functions, classes, and structure.

## Quick Start

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

The installer automatically:
- Detects your Python version (3.8+ required)
- Installs scripts to `~/.claude-code-project-index/`
- Configures Claude Code hooks (`UserPromptSubmit`, `Stop`)
- Adds `/index` command for manual index generation

### Basic Usage with Claude Code CLI

Just add `-i` to any Claude Code prompt:

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

### Performance Characteristics

Based on real-world benchmarks on Apple Silicon (M-series), Python 3.12:

| Project Size | Files | Full Generation | Incremental Update | Use Case |
|--------------|-------|-----------------|-------------------|----------|
| **Small** | < 200 | 1-2 seconds | <1 second | Personal projects, utilities |
| **Medium** | 200-1000 | 3-10 seconds | <1 second | Team projects, web apps |
| **Large** | 1000-5000 | 10-30 seconds | <2 seconds | Enterprise codebases |
| **Very Large** | 5000+ | 30-60 seconds | <5 seconds | Monorepos |

**Real example** (this project, 200 files): 1.37s full generation, <1s incremental updates

**MCP Tool Latency:** All tools respond in <200ms typically, <500ms maximum

📊 Detailed metrics: [`docs/performance-report.md`](docs/performance-report.md) | [`docs/performance-metrics.json`](docs/performance-metrics.json)

### Smart Configuration Presets

**Zero configuration required!** On first run, the indexer automatically:

1. **Detects your project size** (counts files via git)
2. **Selects optimal preset:**
   - **Small** (<100 files): Single-file format, minimal config
   - **Medium** (100-4999 files): Split at 500 files, all Epic 2 features enabled
   - **Large** (5000+ files): Aggressive splitting, optimized for performance
3. **Creates `.project-index.json`** with the right settings
4. **Tracks upgrades** as your project grows

```bash
# First run in your project
/index
# ✨ Created .project-index.json with medium preset (1,247 files detected)
```

When your project crosses size boundaries, you'll be prompted to upgrade (with automatic backups).

**Manual configuration:** You can customize any setting in `.project-index.json` after creation. See [Configuration Options](#configuration-options) below.

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

## MCP Server Setup (Optional)

**⚡ Epic 2/3 Feature** - Expose your project index as an MCP (Model Context Protocol) server for advanced AI agent integration.

### What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that standardizes how AI applications provide context to LLMs. Think of MCP like a USB-C port for AI applications - it allows AI agents to interact with your project index through standardized tool interfaces instead of loading the entire index.

### Multi-Tool Support (New in v0.3.0!)

**✨ Auto-configuration:** The `install.sh` script now automatically detects and configures MCP for all three tools!

This project supports **three MCP-compatible tools** with the following priority:

1. **🥇 Claude Code CLI** (Recommended, most detailed documentation)
2. **🥈 Cursor IDE** (Standard support)
3. **🥉 Claude Desktop** (Basic support)

### Auto-Configuration

```bash
# Run installation
./install.sh

# The installer will:
# ✅ Auto-detect which AI tools are installed
# ✅ Offer to configure MCP for detected tools
# ✅ Write MCP configs (preserves existing servers)
# ✅ Provide validation commands

# Manual configuration (if auto-detection fails)
./install.sh --configure-mcp=claude-code
./install.sh --configure-mcp=cursor
./install.sh --configure-mcp=desktop
```

### Validation

```bash
# Validate MCP connection
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=claude-code
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --all
```

**For detailed setup instructions and troubleshooting**, see [`docs/mcp-setup.md`](docs/mcp-setup.md).

### Manual Setup for Claude Code CLI (If Needed)

```bash
# 1. Install MCP dependencies (first external dependency for this project)
pip install -r requirements.txt

# 2. Add MCP server to Claude Code config (~/.claude/settings.json)
{
  "mcpServers": {
    "project-index": {
      "command": "python",
      "args": ["~/.claude-code-project-index/project_index_mcp.py"]
    }
  }
}

# 3. Restart Claude Code and verify the 4 tools appear
# Tools: project_index_load_core, project_index_load_module,
#        project_index_search_files, project_index_get_file_info
```

### Available MCP Tools

The MCP server provides 4 core tools:

1. **`project_index_load_core`** - Load lightweight core index with file tree and module references
2. **`project_index_load_module`** - Lazy-load specific detail modules (e.g., "scripts", "auth")
3. **`project_index_search_files`** - Search for files by path pattern with pagination
4. **`project_index_get_file_info`** - Get detailed information about a specific file

### Other Tool Integrations

**Cursor IDE and Claude Desktop** are also supported. For complete setup instructions:
- **Cursor IDE setup**: See [`docs/mcp-setup.md#cursor-ide-configuration`](docs/mcp-setup.md#cursor-ide-configuration)
- **Claude Desktop setup**: See [`docs/mcp-setup.md#claude-desktop-configuration`](docs/mcp-setup.md#claude-desktop-configuration)

Quick example for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

**Note:** Claude Code CLI is the primary supported tool with the most detailed documentation and testing.

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

### MCP Tool Detection & Hybrid Intelligence

**⚡ Story 2.5 Feature** - The index-analyzer agent now automatically detects when MCP tools (Read, Grep, Git) are available in your environment and adapts its query strategy accordingly.

#### What is Hybrid Intelligence?

The index-analyzer agent combines two complementary data sources:

1. **Pre-computed Index** (PROJECT_INDEX.json):
   - Fast architectural awareness (dependencies, call graphs, structure)
   - Historical snapshots (git metadata, function signatures)
   - Organized by logical modules for efficient navigation
   - Best for: Structural queries, understanding relationships, finding relevant code sections

2. **Real-time MCP Tools** (when available):
   - Fresh file content (Read tool - current state, not snapshot)
   - Live keyword search (Grep tool - find patterns across codebase)
   - Real-time git operations (Git tool - log, blame, diff)
   - Best for: Explicit file requests, semantic search, temporal queries

#### How Detection Works

The agent automatically detects MCP tool availability at initialization:

```python
from scripts.mcp_detector import detect_mcp_tools

# Performed once at agent startup (results cached)
mcp_capabilities = detect_mcp_tools()
# Returns: {"read": bool, "grep": bool, "git": bool}
```

Detection is:
- **Non-blocking**: Completes in <100ms (typically <10ms for cached results)
- **Graceful**: No exceptions thrown, defaults to False if tools unavailable
- **Cached**: First detection is cached, subsequent queries have zero overhead
- **Environment-based**: Detects Claude Code environment markers without subprocess calls

#### Hybrid Query Routing (Story 2.6)

**⚡ New Feature** - The index-analyzer agent now implements intelligent query routing that combines index structure with real-time MCP tools for optimal results.

##### Query Classification

The agent classifies your query into one of 4 types to determine the optimal routing strategy:

1. **Explicit File Reference**: Queries that mention specific files
   - Patterns: `@filename`, `"in path/to/file"`, `"show me file.py"`
   - Examples: `"Show me scripts/loader.py"`, `"@agents/index-analyzer.md"`

2. **Semantic Search**: Queries looking for keywords or patterns
   - Patterns: `"find all X"`, `"search for Y"`, `"where is Z defined"`
   - Examples: `"Find all authentication functions"`, `"Where is RelevanceScorer defined"`

3. **Temporal Query**: Queries about recent changes or git history
   - Patterns: `"recent changes"`, `"what changed"`, `"show updates"`, `"latest commits"`
   - Examples: `"What changed in the last week?"`, `"Show recent commits to auth module"`

4. **Structural Query**: Queries about architecture and relationships
   - Patterns: `"how does X work"`, `"what depends on Y"`, `"call graph for Z"`
   - Examples: `"How does the loader work?"`, `"What depends on relevance module?"`

##### Routing Strategies

Based on query classification and MCP availability, the agent selects one of 4 strategies:

| Strategy | Query Type | MCP Requirements | Data Sources | Use Case |
|----------|-----------|-----------------|--------------|----------|
| **A** | Explicit file ref | Read available | Index (navigation) + MCP Read (content) | Get fresh file content with index context |
| **B** | Semantic search | Grep available | Index (structure) + MCP Grep (search) | Live keyword search with module organization |
| **C** | Temporal query | Git available | MCP Git (commits) + Index (context) | Real-time git data with architectural context |
| **D** | Any (fallback) | None required | Index detail modules only | Complete functionality without MCP |

**Note**: Structural queries *always* use Strategy D (index-only) because the index is the authoritative source for architectural relationships - MCP tools don't provide dependency/call graph data.

##### Routing Examples

```
Query: "Show me scripts/loader.py"
Classification: explicit_file_ref
MCP Status: Read=True
Selected Strategy: A
Data Flow:
  1. Use index to locate file in "scripts" module
  2. Use MCP Read to fetch current file content
  3. Combine: Index metadata + fresh content from MCP
```

```
Query: "Find all test functions"
Classification: semantic_search
MCP Status: Grep=True
Selected Strategy: B
Data Flow:
  1. Use index to understand project module structure
  2. Use MCP Grep to search for "test" keyword across files
  3. Combine: Index organization + real-time search results
```

```
Query: "What changed recently?"
Classification: temporal_query
MCP Status: Git=True
Selected Strategy: C
Data Flow:
  1. Use MCP Git to get latest commit history
  2. Use index to map changes to affected modules
  3. Combine: Fresh git data + structural context
```

```
Query: "How does the loader work?" (or any query when MCP unavailable)
Classification: structural_query (or MCP tools absent)
MCP Status: Any
Selected Strategy: D (Fallback)
Data Flow:
  1. Perform relevance scoring on modules from index
  2. Lazy-load top 5 relevant detail modules
  3. Analyze structure from index data only
```

#### Verbose Mode Logging

When verbose flag is enabled, the agent logs both MCP detection and routing decisions:

**MCP Detection Status:**
```
🔧 MCP Tools Detected: Read=True, Grep=True, Git=True
   Query strategy: Hybrid (index + MCP)
```

**Query Routing Decision (Story 2.6):**
```
🔄 HYBRID QUERY ROUTING

Query Classification:
  📝 Original query: "Show me scripts/loader.py"
  🎯 Classified as: explicit_file_ref
  🔍 Key indicators: File path pattern detected

MCP Capabilities:
  📖 Read: True
  🔎 Grep: True
  📊 Git: True

Routing Decision:
  ✅ Selected Strategy: A (Explicit File Reference + MCP Read)
  📌 Rationale: Explicit file reference detected, MCP Read available

Data Sources:
  📦 Index: File navigation, module context, relationships
  🔧 MCP Read: Current file content (real-time)

Execution Plan:
  1. Locate file in core index modules
  2. Use MCP Read to fetch current content
  3. Combine index metadata with fresh content
```

**Fallback Mode Logging:**
```
🔄 HYBRID QUERY ROUTING

Query Classification:
  📝 Original query: "How does the loader work?"
  🎯 Classified as: structural_query
  🔍 Key indicators: Architecture/structure analysis

MCP Capabilities:
  📖 Read: False
  🔎 Grep: False
  📊 Git: False

Routing Decision:
  ✅ Selected Strategy: D (Fallback - Index Only)
  📌 Rationale: Structural query requires index data, MCP not needed

Data Sources:
  📦 Index: Detail modules, call graphs, dependencies

Execution Plan:
  1. Perform relevance scoring on modules
  2. Lazy-load top 5 relevant detail modules
  3. Analyze structure from index data
```

#### Benefits of Hybrid Intelligence

- **Best of both worlds**: Combine index structure with real-time data
- **Automatic adaptation**: Agent seamlessly switches strategies based on available tools
- **No configuration required**: Detection happens automatically at runtime
- **Graceful degradation**: Full functionality preserved in index-only mode
- **Performance optimization**: Cache detection results for zero overhead

#### When MCP Tools Are Available

**Claude Code Environment**: When running inside Claude Code, MCP tools (Read, Grep, Git) are typically available and the agent automatically uses hybrid mode.

**Standalone/CI Environment**: When running tests or scripts outside Claude Code, MCP tools are unavailable and the agent gracefully falls back to index-only mode.

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
- **Vue Single-File Components (.vue)** - Both Composition API and Options API
- Shell scripts (.sh, .bash)

**File tracking** (listing only):
- Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin, and 20+ more

### Vue Options API Support

**NEW in v0.3.1** - Enhanced Vue parsing now extracts methods from Options API components in addition to Composition API support.

The indexer automatically detects and parses both Vue API styles:

**Composition API** (existing support):
```vue
<script setup>
import { ref, computed } from 'vue'

const count = ref(0)
const doubled = computed(() => count.value * 2)
function increment() { count.value++ }
</script>
```

**Options API** (new support):
```vue
<script>
export default {
  data() {
    return { count: 0 }
  },
  computed: {
    doubled() { return this.count * 2 }
  },
  methods: {
    increment() { this.count++ }
  },
  created() {
    console.log('Component created')
  }
}
</script>
```

**Extracted from Options API components:**
- ✅ **Methods** (`methods: { ... }`) - Categorized as `category: 'methods'`
- ✅ **Computed properties** (`computed: { ... }`) - Categorized as `category: 'computed'`
- ✅ **Lifecycle hooks** (created, mounted, etc.) - Categorized as `category: 'lifecycle'`
- ✅ **Watchers** (`watch: { ... }`) - Categorized as `category: 'watch'`

**Query examples:**
```bash
# Find all Vue methods
claude "show me all Vue component methods -i"

# Find lifecycle hooks
claude "which components use created hook? -i"

# Analyze computed properties
claude "analyze all computed properties -i"
```

**Performance:** <2ms overhead per Vue file (tested on 246-file Vue project)

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

**📖 For comprehensive troubleshooting**, see [`docs/troubleshooting.md`](docs/troubleshooting.md) with:
- FAQ with 15+ common issues and solutions
- Installation validation steps
- MCP server debugging tips
- Error message reference table

### Quick Fixes

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

## Multi-Level Sub-Module Configuration

**NEW in Epic 4** - Fine-grained control over sub-module organization with framework-specific presets for Vite, React, and Next.js projects.

### What are Multi-Level Sub-Modules?

Multi-level sub-modules allow large modules to be split into hierarchical organization (parent → child → grandchild) for better navigation and faster lazy-loading. This is especially valuable for framework-based projects with predictable directory patterns.

**Example - Vite Project Structure:**

```
Without sub-modules (monolithic):
├── src (850 files) ← Single large module

With multi-level sub-modules:
├── src-components (120 files)
├── src-views (85 files)
├── src-api (45 files)
├── src-stores (30 files)
├── src-composables (25 files)
├── src-utils (15 files)
```

**Benefits:**
- **Faster queries**: Load only `src-components` instead of all 850 files
- **Better organization**: Framework-specific patterns (components, views, api, etc.)
- **Lazy-loading**: Agent loads sub-modules on-demand based on query relevance
- **Performance**: 70%+ file reduction for targeted queries

### Framework Presets

The indexer includes built-in presets for popular frameworks:

**Vite (Vue.js) - 3 levels:**
```
Detects: src/components/, src/views/, src/api/, src/stores/, src/composables/, src/utils/
Depth: 3 levels (parent-child-grandchild)
Example: "src" → "src-components" → "src-components-auth"
```

**React - 2 levels:**
```
Detects: components/, hooks/, utils/, pages/, contexts/, services/
Depth: 2 levels (parent-child)
Example: "src" → "src-components"
```

**Next.js - 2 levels:**
```
Detects: app/, components/, lib/, utils/, hooks/
Depth: 2 levels (parent-child)
Example: "project" → "project-app"
```

**Generic - 2 levels:**
```
Applies to: All projects without specific framework patterns
Depth: 2 levels (split by direct subdirectories)
Example: "docs" → "docs-guides"
```

### Configuration Schema

Add `submodule_config` section to `.project-index.json`:

```json
{
  "mode": "auto",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3,
    "framework_presets": {
      "vite": {
        "split_paths": ["src/components", "src/views", "src/api"],
        "max_depth": 3
      }
    }
  }
}
```

**Configuration Fields:**

- **`enabled`** (boolean, default: `true`)
  - Enable/disable sub-module splitting
  - `true`: Sub-modules generated based on strategy
  - `false`: Uses monolithic module organization (legacy behavior)

- **`strategy`** (string, default: `"auto"`)
  - `"auto"`: Detect framework → apply preset if >threshold, else skip
  - `"force"`: Always split modules regardless of size
  - `"disabled"`: Use monolithic modules (same as enabled:false)

- **`threshold`** (integer, default: `100`)
  - Minimum file count to trigger splitting in "auto" strategy
  - Ignored in "force" strategy (always splits)
  - Conservative default ensures only large modules split

- **`max_depth`** (integer, default: `3` for Vite, `2` for others)
  - Maximum splitting depth
  - `1`: Top-level only (no sub-modules) - `"src"`
  - `2`: Parent-child - `"src-components"`
  - `3`: Parent-child-grandchild - `"src-components-auth"`

- **`framework_presets`** (object, optional)
  - Override built-in framework presets
  - Keys: `"vite"`, `"react"`, `"nextjs"`, `"generic"`
  - Values: `{ "split_paths": [...], "max_depth": N }`

### Strategy Modes

**Auto Strategy (Recommended):**

```json
{
  "submodule_config": {
    "strategy": "auto",
    "threshold": 100
  }
}
```

- Detects framework automatically (Vite, React, Next.js, Generic)
- Applies framework preset if module has >100 files
- Skips splitting for well-organized small modules
- **Best for**: Most projects - balances performance and simplicity

**Force Strategy:**

```json
{
  "submodule_config": {
    "strategy": "force"
  }
}
```

- Always splits modules regardless of size
- Useful for enforcing consistent organization
- **Best for**: Projects with strict module organization requirements

**Disabled Strategy:**

```json
{
  "submodule_config": {
    "strategy": "disabled"
  }
}
```

- Uses monolithic modules (legacy behavior)
- No sub-module splitting
- **Best for**: Small projects or when simplicity is preferred

### Analyzing Module Structure

Use the `--analyze-modules` flag to preview module organization without modifying files:

```bash
python scripts/project_index.py --analyze-modules
```

**Output example:**

```
======================================================================
📊 MODULE STRUCTURE ANALYSIS (Read-Only)
======================================================================

🔍 Detected Framework: vite
   Description: Vite project with Vue.js patterns (components, views, api, stores, composables, utils)
   Recommended max_depth: 3

⚙️  Current Configuration:
   Strategy: auto
   Threshold: 100 files
   Max depth: 3 levels

📦 Module Analysis:
   Total modules: 8
   Large modules (>=100 files): 1

🌳 Current Module Structure:
⚠️  src: 850 files
   docs: 45 files
   scripts: 30 files
   tests: 120 files

🔮 Potential Sub-Module Structure (if index were generated):
   Strategy 'auto' would split 1 module(s):

   src (850 files) →
      ├─ src-components: 285 files
      ├─ src-views: 125 files
      ├─ src-api: 95 files
      ├─ src-stores: 65 files
      ├─ src-composables: 45 files
      ├─ src-utils: 35 files
      └─ src (remaining): 200 files

💡 Suggested Configuration (.project-index.json):
```json
{
  "mode": "auto",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3
  }
}
```

✅ Analysis complete (no files modified)
======================================================================
```

**Analysis is read-only** - No files are modified. Safe to run anytime.

### Configuration Migration

The indexer automatically creates default configuration on first run:

1. Detects framework (Vite, React, Next.js, Generic)
2. Applies appropriate preset (max_depth, patterns)
3. Creates `.project-index.json` with detected settings
4. **Regenerating index with updated config reorganizes modules automatically**

**Migration example:**

```bash
# First run - no config exists
$ python scripts/project_index.py
✨ Created .project-index.json with vite preset
🚀 Building Project Index...
   Framework detected: vite, Strategy: auto, Max depth: 3
   Auto strategy: detected 1 large module(s) (>=100 files)
📂 Splitting modules using vite preset...
   Split src → 6 sub-modules

# Update config to force mode
$ echo '{"submodule_config": {"strategy": "force"}}' > .project-index.json

# Regenerate - applies new config
$ python scripts/project_index.py
🚀 Building Project Index...
   Force strategy: splitting all 8 modules
📂 Splitting modules using vite preset...
   Split docs → 3 sub-modules
   Split scripts → 2 sub-modules
   ...
```

### Warning System

The indexer warns about optimization opportunities:

**Large Module Warning (>200 files):**

```
======================================================================
⚠️  Large module detected: 'src' has 850 files (>200)
   Consider enabling sub-module splitting for better performance.
   Add to .project-index.json:
   {
     "submodule_config": {
       "enabled": true,
       "strategy": "auto",
       "threshold": 100
     }
   }
----------------------------------------------------------------------
```

**Framework Detected but Disabled:**

```
======================================================================
⚠️  Vite framework detected but sub-module splitting is disabled
   This project could benefit from framework-specific organization.
   Add to .project-index.json:
   {
     "submodule_config": {
       "enabled": true,
       "strategy": "auto"
     }
   }
----------------------------------------------------------------------
```

### Example Configurations

**Vite Project (3-level splitting):**

```json
{
  "mode": "auto",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 3
  }
}
```

**React Project (2-level splitting):**

```json
{
  "mode": "auto",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100,
    "max_depth": 2
  }
}
```

**Custom Framework Preset:**

```json
{
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 50,
    "max_depth": 2,
    "framework_presets": {
      "vite": {
        "split_paths": [
          "src/components",
          "src/pages",
          "src/services",
          "src/utils"
        ],
        "max_depth": 2
      }
    }
  }
}
```

**Force Small Modules:**

```json
{
  "submodule_config": {
    "enabled": true,
    "strategy": "force",
    "max_depth": 2
  }
}
```

### Performance Validation

Multi-level sub-modules are tested for performance:

- **Sub-module splitting overhead**: <2 seconds (well under 10% of total time)
- **File-to-module lookup**: O(1) via hash map (<10ms)
- **Relevance scoring**: <100ms for 1,000 modules
- **Analysis flag**: <500ms for 1,000-file project

All acceptance criteria validated in comprehensive test suite (85/85 tests passing).

### When to Use Sub-Modules

**Use sub-modules when:**
- Module has >100 files
- Framework-specific patterns detected (Vite, React, Next.js)
- Working on targeted features (components, API routes, etc.)
- Want faster query response times

**Skip sub-modules when:**
- Module has <100 files (well-organized)
- Prefer simplicity over optimization
- No framework patterns detected
- Legacy project with flat structure

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

## Impact Analysis

**NEW in v2.1**: Understand what breaks if you change a function.

### What is Impact Analysis?

Impact analysis uses the call graph to identify all functions that depend on a target function. This enables safe refactoring by showing exactly which code will be affected by your changes.

**Query examples:**
- "What depends on the `validate` function?"
- "Who calls `check_password`?"
- "Impact of changing `login`?"
- "What breaks if I refactor `api_handler`?"

### How It Works

The impact analyzer performs BFS (breadth-first search) traversal on the reverse call graph:

```
1. Build reverse call graph: callee → [callers]
2. Start at target function
3. Find all direct callers (depth=1)
4. Traverse indirect callers (depth=2+)
5. Track visited functions to handle circular dependencies
6. Map results to file paths and line numbers
```

**Example:**

```
Call graph:  api_handler → login → validate → check_password

Query: "What depends on validate?"

Result:
  Direct callers (2):
    - scripts/auth.py:42 (login)
    - scripts/auth.py:67 (register)

  Indirect callers (2):
    - scripts/api.py:15 (api_handler)
    - scripts/middleware.py:89 (auth_middleware)

  Total affected: 4 functions
```

### Configuration

Configure impact analysis in `bmad/bmm/config.yaml`:

```yaml
impact_analysis:
  enabled: true
  max_depth: 10           # Maximum traversal depth
  include_indirect: true  # Include indirect callers
  show_line_numbers: true # Show file:line in reports
```

### Usage

**Via index-analyzer agent** (recommended):
```
"What depends on the validate function?"
```

**Direct API usage:**
```python
from scripts.impact import analyze_impact, load_call_graph_from_index

# Load call graph (works with both split and legacy indices)
call_graph = load_call_graph_from_index()

# Analyze impact
result = analyze_impact("validate", call_graph, max_depth=10)

# Result structure:
# {
#   "function": "validate",
#   "direct_callers": ["login", "register"],
#   "indirect_callers": ["api_handler"],
#   "depth_reached": 2,
#   "total_affected": 3
# }
```

### Circular Dependency Handling

The impact analyzer gracefully handles circular dependencies:

```
Example: A → B → C → A (cycle)

The algorithm:
1. Marks A as visited
2. Finds B as direct caller of A
3. Finds C as indirect caller (via B)
4. Detects C→A creates cycle (A already visited)
5. Stops traversal, returns B and C

Result: No infinite loop, all callers identified once
```

### Performance

Impact analysis is highly performant:
- **10,000 function graph**: <500ms
- **Complexity**: O(V + E) where V=functions, E=edges
- **BFS traversal**: Linear time in graph size

Tested in `scripts/test_impact.py` with synthetic large graphs.

### Integration with Relevance Scoring

Combine impact analysis with temporal awareness for intelligent refactoring decisions:

- **High-impact + recent changes**: "Function X has 15 callers and was modified 3 days ago"
- **Low-impact + isolated**: Safe to refactor aggressively
- **High-impact + frequently called**: Requires comprehensive test coverage

This creates a powerful workflow: identify high-impact functions, understand their temporal context, make informed refactoring decisions.

### Requirements

Impact analysis requires:
- Call graph data (automatically generated in PROJECT_INDEX.json)
- Python 3.8+ (uses stdlib collections.deque for BFS)
- No external dependencies

Works seamlessly with both split architecture (v2.0-split) and legacy format (v1.0).

## Incremental Updates

**NEW in v2.1**: Update only changed files for 10-100x faster regeneration on large codebases.

### What are Incremental Updates?

Incremental updates selectively regenerate only affected modules instead of reprocessing the entire project. This dramatically speeds up index regeneration after making changes to your codebase.

**Performance gains:**
- **10 changed files**: ~2 seconds (vs 15 seconds full regeneration)
- **100 changed files**: ~8 seconds (vs 2+ minutes full regeneration)
- **1000+ file project**: 10-100x speedup depending on change size

### How It Works

Incremental updates use git history and dependency analysis to minimize work:

```
1. Load existing PROJECT_INDEX.json and extract timestamp
2. Detect changed files via: git log --since=<timestamp> + git status
3. Map changed files to their containing detail modules
4. Build dependency graph from import statements
5. Identify affected modules (changed + dependencies)
6. Regenerate only affected detail modules
7. Update core index metadata (timestamps, hashes, stats)
8. Validate hash consistency (fallback to full if corrupted)
```

**Example:**

```
Project: 5,000 files, 25 modules
Change: Modified 3 files in scripts/ module

Incremental update:
  Detected: 3 changed files (git log)
  Affected modules: scripts (direct), utils (dependency)
  Regenerated: 2 modules (95 files)
  Time: 2.3 seconds

Full regeneration would take: 45 seconds
Speedup: 19.5x
```

### Auto-Detection

The indexer automatically chooses incremental or full regeneration:

**Incremental mode used when:**
- ✅ Existing PROJECT_INDEX.json found
- ✅ Git repository available (can detect changes)
- ✅ Split index format (v2.0-split or v2.1-enhanced)

**Full regeneration used when:**
- ❌ No existing index (first run)
- ❌ Git unavailable (can't detect changes)
- ❌ Legacy single-file format (no module granularity)
- ⚠️ User requested with `--full` flag

### Usage

**Automatic (recommended):**
```bash
python scripts/project_index.py
# Auto-detects incremental mode if possible
```

**Explicit incremental:**
```bash
python scripts/project_index.py --incremental
# Forces incremental mode (fails if not possible)
```

**Force full regeneration:**
```bash
python scripts/project_index.py --full
# Skips incremental, always does full regeneration
```

### Hash-Based Validation

Every incremental update validates integrity using SHA256 hashes:

```
1. Compute hash for each regenerated detail module
2. Store hashes in core index (module_hashes field)
3. Validate all hashes match module files
4. If mismatch detected → automatic fallback to full regeneration
```

**Hash storage in PROJECT_INDEX.json:**
```json
{
  "version": "2.1-enhanced",
  "at": "2025-11-03T19:20:15.123456",
  "module_hashes": {
    "scripts": "sha256:a3f2b1c4d5e6f7a8b9c0d1e2f3a4b5c6...",
    "utils": "sha256:d7e4f9a1b2c3d4e5f6a7b8c9d0e1f2a3...",
    "docs": "sha256:c8b5e2d9f1a3c4b5e6f7a8b9c0d1e2f3..."
  }
}
```

This ensures index consistency even if files are manually modified or corrupted.

### Configuration

Configure incremental updates in `.project-index.json` (optional):

```json
{
  "mode": "auto",
  "incremental": {
    "enabled": true,
    "full_threshold": 0.5
  }
}
```

**Options:**
- `enabled`: Enable/disable incremental updates (default: true)
- `full_threshold`: Trigger full regen if >N% files changed (default: 0.5 = 50%)

### Dependency Analysis

Incremental updates use bidirectional dependency analysis:

**Forward dependencies** (imports):
```python
# utils/helper.py imports scripts/core.py
# If scripts/core.py changes → utils module also regenerated
```

**Reverse dependencies** (call graph):
```python
# api/handler.py calls scripts/validate()
# If scripts/validate() changes → api module also regenerated
```

This ensures consistency: all modules depending on changed code are updated.

### Edge Cases

**Case 1: No changes detected**
```bash
$ python scripts/project_index.py
✓ No changes detected since last index generation
Index is up to date
```

**Case 2: Git unavailable (fallback)**
```bash
$ python scripts/project_index.py
⚠️  Incremental update failed: Git not available
   Falling back to full regeneration...
```

**Case 3: Hash validation failure (auto-recovery)**
```bash
$ python scripts/project_index.py
⚠️  Hash validation failed - index may be corrupted
   Triggering full regeneration for consistency...
```

### Performance Characteristics

| Changed Files | Incremental Time | Full Regen Time | Speedup |
|--------------|------------------|-----------------|---------|
| 1-10 files   | ~2 seconds       | ~15 seconds     | 7.5x    |
| 10-50 files  | ~4 seconds       | ~30 seconds     | 7.5x    |
| 50-100 files | ~8 seconds       | 1-2 minutes     | 10x     |
| 100+ files   | <10 seconds*     | 2-5 minutes     | 15-30x  |

*Performance tested in `scripts/test_incremental.py` with real git repositories.

### Requirements

Incremental updates require:
- Split index format (v2.0-split or v2.1-enhanced)
- Git repository with commit history
- Python 3.8+ (uses stdlib subprocess, hashlib)
- No external dependencies

Legacy single-file format automatically falls back to full regeneration.

### Integration with Story Context Workflow

Incremental updates work seamlessly with BMM workflows:

```bash
# After implementing a story with dev-story workflow
$ python scripts/project_index.py
Auto-detected incremental mode
Regenerated 3 modules in 2.1s

# Index is now up to date for next story-context generation
$ /bmad:bmm:workflows:story-context
# Uses fresh incremental index for context assembly
```

This creates a fast feedback loop: implement → incremental update → generate context → implement next story.

## MCP Server Support (Optional)

The project index can be exposed as an MCP (Model Context Protocol) server, enabling AI agents to navigate and query large codebases through standardized tool interfaces.

**Note**: The MCP server is an **optional enhancement**. Core indexing functionality (`scripts/project_index.py`, `scripts/loader.py`) remains Python stdlib-only and does NOT require external dependencies.

### What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that standardizes how AI applications provide context to LLMs. Think of MCP like a USB-C port for AI applications.

### Quick Start

1. **Install MCP dependencies** (first external dependency for this project):

```bash
pip install -r requirements.txt
```

This installs:
- `mcp>=1.0.0` - MCP Python SDK
- `pydantic>=2.0` - Input validation (transitive dependency)

2. **Configure Claude Desktop** (or another MCP client):

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "project-index": {
      "command": "python",
      "args": ["/absolute/path/to/project/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

3. **Restart Claude Desktop** and verify the 4 tools appear:
   - `project_index_load_core` - Load core index with file tree
   - `project_index_load_module` - Lazy-load detail modules
   - `project_index_search_files` - Search files by pattern
   - `project_index_get_file_info` - Get file details with git metadata

### Available Tools

**Tool 1: project_index_load_core**

Load the lightweight core index containing project structure and module references.

```python
# JSON format (default, machine-readable)
project_index_load_core(response_format="json")

# Markdown format (human-readable)
project_index_load_core(response_format="markdown")
```

Returns:
- Project version and generation timestamp
- File tree structure
- Available modules with file counts
- Project statistics

**Tool 2: project_index_load_module**

Lazy-load a specific detail module with full function/class information.

```python
# Load scripts module in JSON format
project_index_load_module(module_name="scripts", response_format="json")

# Load in Markdown format for readability
project_index_load_module(module_name="scripts", response_format="markdown")
```

Returns:
- Module version and ID
- Files with function signatures
- Classes with methods
- Import statements
- Local call graph

**Tool 3: project_index_search_files**

Search for files matching a pattern with pagination support.

```python
# Basic search (default: limit=20, offset=0)
project_index_search_files(query="test")

# Paginated search
project_index_search_files(query="*.py", limit=10, offset=20)
```

Returns:
- Matching file paths
- Pagination metadata (total, limit, offset, has_more)
- Module associations

**Tool 4: project_index_get_file_info**

Get detailed information about a specific file including git metadata.

```python
# Get file info in Markdown format (default)
project_index_get_file_info(file_path="scripts/project_index.py", response_format="markdown")

# Get in JSON format
project_index_get_file_info(file_path="scripts/loader.py", response_format="json")
```

Returns:
- Programming language
- Functions with signatures and line numbers
- Classes with methods
- Import statements
- **Git metadata** (commit, author, date, recency_days, message, PR, lines changed)

### Input Validation

All tools use Pydantic v2 models for input validation:

**LoadCoreIndexInput**:
- `response_format`: "json" | "markdown" (default: "json")
- `index_path`: Optional custom path to PROJECT_INDEX.json

**LoadModuleInput**:
- `module_name`: String (required, 1-200 chars)
- `response_format`: "json" | "markdown" (default: "json")
- `index_dir`: Optional custom path to PROJECT_INDEX.d/

**SearchFilesInput**:
- `query`: Search string (required, 1-200 chars)
- `limit`: Results limit (1-100, default: 20)
- `offset`: Results offset (>=0, default: 0)
- `index_path`: Optional custom path to PROJECT_INDEX.json

**GetFileInfoInput**:
- `file_path`: File path (required, 1-500 chars)
- `response_format`: "json" | "markdown" (default: "markdown")
- `index_path`: Optional custom path to PROJECT_INDEX.json

### Error Handling

The MCP server provides actionable error messages with clear next steps:

**Module not found**:
```
Error: Module 'nonexistent' not found.

Available modules: scripts, root, docs, agents, bmad

Next steps: Use one of the available module names, or run /index to update the index.
```

**File not indexed**:
```
Error: File 'path/to/file.py' not found in index.

Next steps: Check the file path, use project_index_search_files to find the correct path, or run /index to update the index.
```

**Index not generated**:
```
Error: File not found: PROJECT_INDEX.json

Next steps: Run /index to generate the project index.
```

### Performance

The MCP server is optimized for fast response times:

- **Tool invocation latency**: <500ms per call (target)
- **Core index loading**: ~100ms (file read + JSON parse)
- **Detail module loading**: ~200ms (file read + JSON parse)
- **File search**: ~300ms (scan + filter + pagination)
- **File info retrieval**: ~300ms (module lookup + data extraction)

Performance benefits from:
- Efficient JSON parsing (stdlib `json` module)
- Lazy-loading (only load modules when needed)
- OS file caching (repeated calls faster)
- Minimal data transformations

### Architecture

The MCP server integrates with existing utilities to avoid code duplication:

```
Claude Desktop / AI Client
         ↓
  (stdio transport)
         ↓
project_index_mcp.py (FastMCP Server)
  ├─ Tool 1: project_index_load_core
  │    → Loads PROJECT_INDEX.json directly
  ├─ Tool 2: project_index_load_module
  │    → Uses scripts/loader.py:load_detail_module()
  ├─ Tool 3: project_index_search_files
  │    → Searches core index file tree
  └─ Tool 4: project_index_get_file_info
       → Uses scripts/loader.py:load_detail_by_path()
         ↓
Existing Utilities
  - scripts/loader.py (lazy-loading)
  - PROJECT_INDEX.json (core index)
  - PROJECT_INDEX.d/ (detail modules)
```

**Design Principles**:
- **Read-only**: All tools are non-destructive (readOnlyHint=true)
- **Idempotent**: Repeated calls produce same results (idempotentHint=true)
- **Stateless**: No session state required
- **DRY**: Reuses existing loader utilities
- **Stdio transport**: Local Claude Desktop integration (not HTTP)

### Requirements

- **Python 3.12+** (project uses Python 3.12+ stdlib features)
- **MCP SDK**: `mcp>=1.0.0`
- **Pydantic**: `pydantic>=2.0.0` (transitive dependency)
- **Index files**: PROJECT_INDEX.json and PROJECT_INDEX.d/ (generate with `/index`)

### Troubleshooting

**Tools don't appear in Claude Desktop**:
- Check `claude_desktop_config.json` path is absolute
- Restart Claude Desktop after config changes
- Verify `python project_index_mcp.py` runs without errors
- Check Python version: `python --version` (must be 3.12+)

**"Module not found" errors**:
- Run `/index` to generate split index architecture
- Verify PROJECT_INDEX.d/ directory exists
- Check module name spelling (use `project_index_load_core` to list modules)

**"File not found in index" errors**:
- Run `/index` to update the index
- Verify file path is relative to project root
- Use `project_index_search_files` to find correct path

**Slow performance (>500ms)**:
- Check index file size (large indexes may exceed target)
- Verify SSD storage (HDD will be slower)
- Consider splitting large modules for better lazy-loading

### References

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [mcp-builder skill](.claude/skills/mcp-builder) - Implementation guide
- [Pydantic Documentation](https://docs.pydantic.dev/)

**More details:** See [Smart Configuration Presets](#smart-configuration-presets) in the Quick Start section above.

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