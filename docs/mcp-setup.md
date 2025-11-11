# MCP Configuration Guide

Model Context Protocol (MCP) server setup guide for claude-code-project-index.

**Tool Priority:** This guide covers three MCP-compatible AI tools in priority order:

1. 🥇 **Claude Code CLI** (Recommended, most detailed)
2. 🥈 **Cursor IDE** (Standard support)
3. 🥉 **Claude Desktop** (Basic support)

**Quick Navigation:**
- [Tool Comparison](#tool-comparison)
- [Auto-Configuration](#auto-configuration)
- [Prerequisites](#prerequisites)
- [Claude Code CLI Configuration](#claude-code-cli-configuration)
- [Cursor IDE Configuration](#cursor-ide-configuration)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [Validation & Testing](#validation--testing)
- [Troubleshooting](#troubleshooting)

## Tool Comparison

All three tools use the same MCP server implementation (stdio transport) for consistency:

| Feature | Claude Code CLI 🥇 | Cursor IDE 🥈 | Claude Desktop 🥉 |
|---------|-------------------|---------------|-------------------|
| **Priority** | Recommended | Standard | Basic |
| **Documentation Detail** | Most detailed | Standard | Basic |
| **Configuration Location** | `~/.config/claude-code/mcp.json` | Platform-specific* | Platform-specific* |
| **Auto-Detection** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Stdio Transport** | ✅ Supported | ✅ Supported | ✅ Supported |
| **MCP Tools Available** | 4 tools | 4 tools | 4 tools |
| **Lazy Loading** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Git Metadata** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Performance Target** | <500ms | <500ms | <500ms |

*Platform-specific paths:
- **Cursor:** macOS: `~/Library/Application Support/Cursor/User/globalStorage/mcp-config.json`, Linux: `~/.config/Cursor/User/globalStorage/mcp-config.json`
- **Claude Desktop:** macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`, Linux: `~/.config/Claude/claude_desktop_config.json`

### When to Choose Each Tool

**Claude Code CLI** is recommended because:
- ✅ Best command-line integration for development workflows
- ✅ Most comprehensive documentation and examples
- ✅ Simple cross-platform configuration path
- ✅ Primary testing target for new features

**Cursor IDE** is great when:
- ✅ You prefer IDE-integrated AI
- ✅ You want visual code editing with AI assistance
- ✅ Your workflow centers around VS Code-like experience

**Claude Desktop** works well for:
- ✅ General-purpose AI conversations about code
- ✅ Non-coding project discussions with context
- ✅ Simpler standalone app experience

### Trade-offs

| Consideration | Claude Code CLI | Cursor IDE | Claude Desktop |
|--------------|-----------------|------------|----------------|
| **Setup Complexity** | Simple | Moderate | Moderate |
| **Config Path Consistency** | ✅ Cross-platform | ⚠️ Platform-specific | ⚠️ Platform-specific |
| **Terminal Integration** | ✅ Native | ❌ External | ❌ External |
| **Code Editing** | ✅ Direct | ✅ IDE | ❌ Copy-paste |
| **Use Case** | Development | Development | General |

## Auto-Configuration

**New in v0.3.0:** The install script automatically detects and configures MCP for all three tools!

```bash
# Run installation
./install.sh

# The installer will:
# 1. Detect which AI tools are installed (Claude Code, Cursor, Claude Desktop)
# 2. Display detected tools
# 3. Offer to configure MCP for detected tools
# 4. Write MCP configuration (preserves existing servers)
# 5. Provide validation commands

# Example output:
# 🔍 Detecting MCP-compatible tools...
# ✓ Found: Claude Code CLI (~/.config/claude-code/)
# ✓ Found: Cursor IDE (~/Library/Application Support/Cursor/)
# 📋 Detected 2 tool(s): claude-code cursor
#
# Would you like to configure MCP for:
#   [a] All detected tools (recommended)
#   [s] Select specific tools
#   [n] Skip MCP configuration
```

### Manual Configuration

If auto-detection fails or you want to configure a specific tool:

```bash
# Configure specific tool
./install.sh --configure-mcp=claude-code
./install.sh --configure-mcp=cursor
./install.sh --configure-mcp=desktop
```

### Validation

After configuration, validate the MCP connection:

```bash
# Validate specific tool
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=claude-code
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=cursor
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=desktop

# Test all detected tools
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --all
```

**Exit Codes:**
- `0`: Success - MCP server connection works
- `1`: Connection failed - Tool detected but MCP not working
- `2`: Not configured - Tool not detected or config missing

## Prerequisites

### Required

- **Python 3.12+** (MCP server requirement)
- **Generated project index** (PROJECT_INDEX.json + PROJECT_INDEX.d/)
- **MCP dependencies** installed

### Installing MCP Dependencies

```bash
# Install from project directory
cd ~/.claude-code-project-index
pip install -r requirements.txt

# Verify installation
pip list | grep -E "mcp|pydantic"
# Expected:
# mcp>=1.0.0
# pydantic>=2.0.0
```

**Note:** This is the **first external dependency** for this project. Core indexing remains stdlib-only.

### Generate Project Index

```bash
# Navigate to your project
cd /path/to/your/project

# Generate index (if not already done)
/index

# Or manually
python3 ~/.claude-code-project-index/scripts/project_index.py

# Verify index created
ls -la PROJECT_INDEX.json PROJECT_INDEX.d/
```

## Claude Code CLI Configuration

**Priority: 🥇 Recommended** - Most detailed documentation and primary supported tool.

**Note:** As of v0.3.0, the `install.sh` script automatically detects and configures Claude Code CLI. The manual steps below are provided for reference or troubleshooting.

### Step 1: Verify Prerequisites

```bash
# Check Python version
python3 --version
# Need: Python 3.12+

# Check MCP dependencies
pip list | grep mcp
# Need: mcp>=1.0.0

# Check project index exists
ls PROJECT_INDEX.json
# Must exist
```

### Step 2: Configure MCP Server

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": ["~/.claude-code-project-index/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

**Important:** Use the **absolute path** to `project_index_mcp.py` in the `args` array.

**Example with explicit path:**
```json
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": ["/Users/yourname/.claude-code-project-index/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

### Step 3: Restart Claude Code

```bash
# Exit Claude Code completely
# Start Claude Code again
# MCP servers load at startup
```

### Step 4: Verify Tools Available

After restart, check that 4 tools appear in Claude Code:

1. **`project_index_load_core`** - Load core index with file tree
2. **`project_index_load_module`** - Lazy-load detail modules
3. **`project_index_search_files`** - Search files by pattern
4. **`project_index_get_file_info`** - Get file details + git metadata

### Step 5: Test MCP Tools

```bash
# In Claude Code, test with a query:
claude "Use project_index_load_core to show me the project structure"

# Expected: Tool loads core index and displays project tree
```

### Auto-Detection Behavior

The MCP server automatically:
- Detects your project root
- Loads PROJECT_INDEX.json from current directory
- Lazy-loads detail modules from PROJECT_INDEX.d/
- Returns errors with helpful next steps if files missing

### Advanced Configuration

**Custom environment variables:**
```json
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": ["~/.claude-code-project-index/project_index_mcp.py"],
      "env": {
        "PYTHONPATH": "/custom/path",
        "INDEX_VERBOSE": "1"
      }
    }
  }
}
```

**Multiple projects:**
```json
{
  "mcpServers": {
    "project-a-index": {
      "command": "python3",
      "args": ["/path/to/project-a/project_index_mcp.py"]
    },
    "project-b-index": {
      "command": "python3",
      "args": ["/path/to/project-b/project_index_mcp.py"]
    }
  }
}
```

## Cursor IDE Configuration

**Priority: 🥈 Standard support** - Standard detail level.

**Note:** As of v0.3.0, the `install.sh` script automatically detects and configures Cursor IDE. The manual steps below are provided for reference or troubleshooting.

### Step 1: Install MCP Dependencies

```bash
pip install -r ~/.claude-code-project-index/requirements.txt
```

### Step 2: Configure Cursor Settings

Add to Cursor's MCP configuration file:

**Location:** `~/.cursor/mcp_settings.json` (or equivalent - check Cursor docs)

```json
{
  "mcpServers": {
    "project-index": {
      "command": "python3",
      "args": ["/absolute/path/to/project_index_mcp.py"]
    }
  }
}
```

### Step 3: Restart Cursor

- Close Cursor completely
- Reopen Cursor
- MCP tools should be available

### Step 4: Verify

Test in Cursor:
- Open a project with a generated index
- Use AI chat to query project structure
- Verify tools respond correctly

**Note:** Cursor MCP support may vary by version. Consult [Cursor documentation](https://cursor.sh) for latest MCP integration details.

## Claude Desktop Configuration

**Priority: 🥉 Basic support** - Basic detail level.

**Note:** As of v0.3.0, the `install.sh` script automatically detects and configures Claude Desktop. The manual steps below are provided for reference or troubleshooting.

### Step 1: Install MCP Dependencies

```bash
pip install -r ~/.claude-code-project-index/requirements.txt
```

### Step 2: Locate Configuration File

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Step 3: Add MCP Server

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "project-index": {
      "command": "python",
      "args": ["/absolute/path/to/your/project/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

**Important:** Replace `/absolute/path/to/your/project/` with your actual project path.

**Example:**
```json
{
  "mcpServers": {
    "project-index": {
      "command": "python",
      "args": ["/Users/john/code/myproject/project_index_mcp.py"],
      "env": {}
    }
  }
}
```

### Step 4: Restart Claude Desktop

- Quit Claude Desktop completely
- Reopen Claude Desktop
- MCP tools should load

### Step 5: Verify

In Claude Desktop:
- Ask: "Use project_index_load_core to show project structure"
- Verify response includes project tree

**Note:** Claude Desktop MCP support is available in recent versions. Check [Claude Desktop release notes](https://anthropic.com/claude) for compatibility.

## Validation & Testing

### Quick Validation Checklist

```bash
# ✅ 1. Python version
python3 --version
# Need: 3.12+

# ✅ 2. MCP dependencies installed
pip list | grep -E "mcp|pydantic"

# ✅ 3. Project index exists
ls PROJECT_INDEX.json PROJECT_INDEX.d/

# ✅ 4. MCP server config present
cat ~/.claude/settings.json | jq '.mcpServers."project-index"'

# ✅ 5. Absolute paths used
# Check that "args" contains full path, not relative
```

### Test MCP Server Manually

```bash
# Start MCP server manually (test mode)
cd /path/to/your/project
python3 ~/.claude-code-project-index/project_index_mcp.py

# Expected: Server starts, waits for stdio input
# Ctrl+C to exit
```

### Test Tools in AI Client

**Test 1: Load core index**
```
Query: "Use project_index_load_core to show me the project structure"
Expected: Displays file tree and modules
```

**Test 2: Search files**
```
Query: "Use project_index_search_files to find all Python files"
Expected: Lists matching files with pagination
```

**Test 3: Load module**
```
Query: "Use project_index_load_module to load the scripts module"
Expected: Displays functions, classes, imports
```

**Test 4: Get file info**
```
Query: "Use project_index_get_file_info for scripts/project_index.py"
Expected: Displays file details including git metadata
```

## Troubleshooting

### Quick Diagnostic

**New in v0.3.0:** Use the validation command to diagnose MCP connection issues:

```bash
# Test specific tool
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=claude-code
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=cursor
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=desktop

# Test all detected tools
python3 ~/.claude-code-project-index/scripts/validate_mcp.py --all
```

The validation command checks:
- ✅ MCP config file exists
- ✅ project-index server configured
- ✅ Server script exists
- ✅ PROJECT_INDEX.json exists
- ✅ Connection latency

**Exit codes:**
- `0`: Success (MCP working)
- `1`: Connection failed (check troubleshooting steps)
- `2`: Not configured (run `./install.sh --configure-mcp=<tool>`)

### Tools Not Appearing

**Problem:** MCP tools don't show up after configuration

**Solutions:**

1. **Run validation command first:**
   ```bash
   python3 ~/.claude-code-project-index/scripts/validate_mcp.py --tool=claude-code
   # This will identify the specific issue
   ```

2. **Check Python version:**
   ```bash
   python3 --version
   # Must be 3.12+
   ```

3. **Verify MCP dependencies:**
   ```bash
   pip install -r ~/.claude-code-project-index/requirements.txt
   ```

4. **Check config path is absolute:**
   ```bash
   # Bad (relative path)
   "args": ["project_index_mcp.py"]

   # Good (absolute path)
   "args": ["/Users/you/.claude-code-project-index/project_index_mcp.py"]
   ```

5. **Restart AI client completely:**
   - Quit application
   - Wait 5 seconds
   - Reopen application

6. **Check server logs:**
   ```bash
   # Start manually to see errors
   python3 ~/.claude-code-project-index/project_index_mcp.py
   ```

### "Module Not Found" Errors

**Problem:** MCP tool returns "Module 'xyz' not found"

**Solutions:**

1. **Regenerate index:**
   ```bash
   cd /path/to/project
   /index
   ```

2. **Verify PROJECT_INDEX.d/ exists:**
   ```bash
   ls -la PROJECT_INDEX.d/
   # Should contain *.json module files
   ```

3. **Check available modules:**
   ```bash
   cat PROJECT_INDEX.json | jq '.modules | keys'
   ```

### Connection Timeout

**Problem:** MCP server not responding

**Solutions:**

1. **Test server manually:**
   ```bash
   cd /path/to/project
   timeout 5 python3 ~/.claude-code-project-index/project_index_mcp.py
   # Should start without errors
   ```

2. **Check PROJECT_INDEX.json exists:**
   ```bash
   ls -la PROJECT_INDEX.json
   ```

3. **Verify no Python errors:**
   ```bash
   python3 -c "import project_index_mcp; print('OK')"
   # Should print "OK"
   ```

### Slow Response (>500ms)

**Problem:** MCP tools responding slowly

**Diagnostic:**
```bash
time python3 -c "
from scripts.loader import load_detail_module
module = load_detail_module('scripts')
print('OK')
"
# Should complete in <200ms
```

**Solutions:**

1. **Use SSD storage:**
   ```bash
   df -h .
   # Ensure project is on SSD
   ```

2. **Optimize module size with sub-modules:**
   ```json
   {
     "submodule_config": {
       "enabled": true,
       "threshold": 50
     }
   }
   ```

3. **Regenerate if corrupted:**
   ```bash
   rm -rf PROJECT_INDEX.d/
   /index
   ```

## Performance Expectations

| Tool | Typical Latency | Max Latency | Purpose |
|------|----------------|-------------|---------|
| **load_core** | ~100-150ms | <500ms | Load project structure |
| **load_module** | ~150-200ms | <500ms | Load module details |
| **search_files** | ~80-100ms | <500ms | Search by path pattern |
| **get_file_info** | ~60-80ms | <500ms | Get file information |

**Factors affecting performance:**
- Project size (file count)
- Module organization (sub-modules help)
- Storage speed (SSD vs HDD)
- System load

## Best Practices

### 1. Use Absolute Paths

```json
// ✅ Good
"args": ["/Users/you/.claude-code-project-index/project_index_mcp.py"]

// ❌ Bad
"args": ["~/.claude-code-project-index/project_index_mcp.py"]
"args": ["project_index_mcp.py"]
```

### 2. Regenerate Index Regularly

```bash
# After significant code changes
/index

# Or via git hook (post-commit, post-merge)
```

### 3. Monitor Tool Performance

```bash
# Check MCP response times
# Use timing in queries to verify <500ms target
```

### 4. Use Sub-Modules for Large Projects

```json
{
  "submodule_config": {
    "enabled": true,
    "strategy": "auto",
    "threshold": 100
  }
}
```

### 5. Separate Config Per Project

```bash
# Each project can have own MCP server
# Use unique server names in config
{
  "mcpServers": {
    "projectA-index": {...},
    "projectB-index": {...}
  }
}
```

## Tool Reference

### project_index_load_core

**Purpose:** Load lightweight core index

**Parameters:**
- `response_format`: "json" | "markdown" (default: "json")
- `index_path`: Optional custom path

**Returns:**
- Project version, timestamp
- File tree structure
- Available modules
- Project statistics

### project_index_load_module

**Purpose:** Lazy-load detail module

**Parameters:**
- `module_name`: String (required)
- `response_format`: "json" | "markdown" (default: "json")
- `index_dir`: Optional custom path

**Returns:**
- Module files with functions
- Classes with methods
- Import statements
- Local call graph

### project_index_search_files

**Purpose:** Search files by pattern

**Parameters:**
- `query`: Search string (required)
- `limit`: Results limit (1-100, default: 20)
- `offset`: Results offset (default: 0)
- `index_path`: Optional custom path

**Returns:**
- Matching file paths
- Pagination metadata
- Module associations

### project_index_get_file_info

**Purpose:** Get detailed file information

**Parameters:**
- `file_path`: File path (required)
- `response_format`: "json" | "markdown" (default: "markdown")
- `index_path`: Optional custom path

**Returns:**
- Programming language
- Functions with signatures
- Classes with methods
- Import statements
- **Git metadata** (commit, author, date, recency_days)

## Getting Help

If you encounter MCP setup issues:

1. **Review guides:**
   - [Troubleshooting Guide](troubleshooting.md) - General issues
   - [Best Practices Guide](best-practices.md) - Optimization tips

2. **Check documentation:**
   - [MCP Protocol Spec](https://modelcontextprotocol.io)
   - [Claude Code Docs](https://docs.claude.com)
   - [Cursor Docs](https://cursor.sh)

3. **File an issue:**
   - [GitHub Issues](https://github.com/ericbuess/claude-code-project-index/issues)
   - Include: Python version, tool name, error logs

4. **Community support:**
   - This is a community tool!
   - Have Claude Code help you debug configuration
   - Fork and adapt for your setup

---

**Last updated:** 2025-11-11

**Related Guides:**
- [README](../README.md) - Overview and quick start
- [Troubleshooting Guide](troubleshooting.md) - Common issues
- [Best Practices Guide](best-practices.md) - Feature usage
- [Migration Guide](migration.md) - Version upgrades
