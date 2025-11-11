# Troubleshooting Guide

This guide helps you resolve common issues when using the claude-code-project-index tool.

**Quick Navigation:**
- [Installation Issues](#installation-issues)
- [Index Generation Problems](#index-generation-problems)
- [MCP Server Issues](#mcp-server-issues)
- [Performance Problems](#performance-problems)
- [Error Reference](#error-reference)
- [Validation Commands](#validation-commands)

## Installation Issues

### Installation Script Fails

**Problem:** `install.sh` exits with errors

**Solutions:**

1. **Check Python version:**
   ```bash
   python3 --version
   # Need Python 3.8 or higher
   ```

2. **Verify git is installed:**
   ```bash
   git --version
   # Git required for installation
   ```

3. **Check jq is installed:**
   ```bash
   jq --version
   # jq required for JSON manipulation in install.sh
   ```

4. **Install missing dependencies:**
   ```bash
   # macOS
   brew install git jq

   # Linux (Ubuntu/Debian)
   sudo apt-get install git jq
   ```

### Hooks Not Configured

**Problem:** `-i` flag doesn't trigger index generation

**Check hook configuration:**
```bash
cat ~/.claude/settings.json | jq .hooks
```

**Expected output:**
```json
{
  "hooks": {
    "UserPromptSubmit": "python3 ~/.claude-code-project-index/scripts/i_flag_hook.py",
    "Stop": "python3 ~/.claude-code-project-index/scripts/stop_hook.py"
  }
}
```

**Fix:**
```bash
# Re-run installer to fix hooks
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

### Permission Denied Errors

**Problem:** Cannot execute scripts

**Fix:**
```bash
chmod +x ~/.claude-code-project-index/install.sh
chmod +x ~/.claude-code-project-index/uninstall.sh
chmod +x ~/.claude-code-project-index/scripts/*.py
```

## Index Generation Problems

### Index Not Creating

**Problem:** PROJECT_INDEX.json not generated

**Diagnostic steps:**

1. **Manual generation test:**
   ```bash
   cd /path/to/your/project
   python3 ~/.claude-code-project-index/scripts/project_index.py
   ```

2. **Check for errors:**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py 2>&1 | tee index-debug.log
   ```

3. **Verify git repository:**
   ```bash
   git status
   # Must be run in a git repository
   ```

4. **Check file permissions:**
   ```bash
   ls -la PROJECT_INDEX.json
   # Ensure you have write permissions
   ```

### Index Generation Hangs

**Problem:** Script runs but never completes

**Causes and solutions:**

1. **Large project timeout:**
   ```bash
   # Increase timeout in i_flag_hook.py (default: 30 seconds)
   # Or use split format for better performance
   echo '{"mode": "split", "threshold": 500}' > .project-index.json
   python3 ~/.claude-code-project-index/scripts/project_index.py
   ```

2. **Too many files (>5000):**
   ```bash
   # Use large preset
   python3 ~/.claude-code-project-index/scripts/project_index.py --upgrade-to=large
   ```

3. **Memory issues:**
   ```bash
   # Check available memory
   free -h  # Linux
   vm_stat  # macOS

   # Use split format to reduce memory footprint
   python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
   ```

### Index Too Large (>1 MB)

**Problem:** PROJECT_INDEX.json exceeds 1 MB

**Solutions:**

1. **Use split format (recommended):**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
   ```

2. **Reduce threshold to trigger split earlier:**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py --threshold 500
   ```

3. **Configure via config file:**
   ```bash
   echo '{"mode": "split", "threshold": 500}' > .project-index.json
   python3 ~/.claude-code-project-index/scripts/project_index.py
   ```

## MCP Server Issues

### MCP Tools Don't Appear in Claude Code

**Problem:** MCP server configured but tools not available

**Diagnostic steps:**

1. **Check Python version for MCP server:**
   ```bash
   python3 --version
   # MCP server requires Python 3.12+
   ```

2. **Verify MCP dependencies installed:**
   ```bash
   pip list | grep mcp
   pip list | grep pydantic
   # Should see: mcp>=1.0.0, pydantic>=2.0.0
   ```

3. **Install MCP dependencies if missing:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Check Claude Code config:**
   ```bash
   cat ~/.claude/settings.json | jq .mcpServers
   ```

5. **Test MCP server manually:**
   ```bash
   cd /path/to/your/project
   python3 project_index_mcp.py
   # Should start without errors
   ```

6. **Restart Claude Code:**
   ```bash
   # MCP servers load at startup - restart Claude Code after config changes
   ```

### MCP Server Connection Errors

**Problem:** "MCP server not responding" or connection timeout

**Solutions:**

1. **Verify absolute paths in config:**
   ```json
   {
     "mcpServers": {
       "project-index": {
         "command": "python3",
         "args": ["/Users/you/.claude-code-project-index/project_index_mcp.py"]
       }
     }
   }
   ```

2. **Check project index exists:**
   ```bash
   ls -la PROJECT_INDEX.json PROJECT_INDEX.d/
   # Must have generated index first with /index
   ```

3. **Test Python import:**
   ```bash
   cd ~/.claude-code-project-index
   python3 -c "import project_index_mcp; print('OK')"
   ```

### "Module Not Found" Errors in MCP

**Problem:** MCP tool returns "Module 'xyz' not found"

**Solutions:**

1. **List available modules:**
   ```bash
   # Use project_index_load_core tool to see module list
   # Or check directly:
   ls -1 PROJECT_INDEX.d/*.json
   ```

2. **Regenerate index:**
   ```bash
   /index
   # Regenerates both core and detail modules
   ```

3. **Verify split format:**
   ```bash
   cat PROJECT_INDEX.json | jq .version
   # Should show "2.0-split" or higher
   ```

### Slow MCP Response (>500ms)

**Problem:** MCP tools taking longer than expected

**Diagnostic:**
```bash
time python3 -c "
from scripts.loader import load_detail_module
import json
start = __import__('time').time()
module = load_detail_module('scripts')
print(f'Loaded in {(__import__(\"time\").time() - start)*1000:.0f}ms')
"
```

**Solutions:**

1. **Check disk I/O:**
   ```bash
   # Ensure PROJECT_INDEX.d/ is on fast storage (SSD)
   df -h .
   ```

2. **Verify module files not corrupted:**
   ```bash
   ls -lh PROJECT_INDEX.d/
   # All *.json files should have reasonable sizes
   ```

3. **Regenerate if needed:**
   ```bash
   rm -rf PROJECT_INDEX.d/
   python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
   ```

## Performance Problems

### Index Generation Too Slow

**Problem:** Index generation takes longer than expected

**Performance targets:**
- Small (<200 files): 1-2 seconds
- Medium (200-1000 files): 3-10 seconds
- Large (1000-5000 files): 10-30 seconds

**Diagnostic:**
```bash
time python3 ~/.claude-code-project-index/scripts/project_index.py
```

**Solutions:**

1. **Use split format for large projects:**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
   ```

2. **Check file count:**
   ```bash
   git ls-files | wc -l
   # If >1000 files, split format recommended
   ```

3. **Skip details initially (faster):**
   ```bash
   python3 ~/.claude-code-project-index/scripts/project_index.py --skip-details
   ```

### Incremental Updates Not Working

**Problem:** Index regenerates fully every time instead of incrementally

**Check incremental mode:**
```bash
# Look for "Incremental update" in output
python3 ~/.claude-code-project-index/scripts/project_index.py | grep -i incremental
```

**Requirements for incremental mode:**
- ✅ Existing PROJECT_INDEX.json
- ✅ Git repository available
- ✅ Split index format (v2.0-split or v2.1-enhanced)

**Force full regeneration if needed:**
```bash
python3 ~/.claude-code-project-index/scripts/project_index.py --full
```

### Auto-Detection Using Wrong Format

**Problem:** Indexer chooses single-file when you want split (or vice versa)

**Check file count:**
```bash
git ls-files | wc -l
# Split mode triggers at >1000 files by default
```

**Force desired format:**
```bash
# Force split format
python3 ~/.claude-code-project-index/scripts/project_index.py --mode split

# Force single-file format
python3 ~/.claude-code-project-index/scripts/project_index.py --mode single
```

**Configure threshold:**
```bash
# Split at >500 files instead of >1000
python3 ~/.claude-code-project-index/scripts/project_index.py --threshold 500
```

## Error Reference

### Common Error Messages

#### "Error: Python 3.8+ required"

**Cause:** Python version too old

**Fix:**
```bash
# Check version
python3 --version

# Install newer Python (macOS)
brew install python@3.12

# Update PATH if needed
which python3
```

#### "Error: Not a git repository"

**Cause:** Running indexer outside a git repository

**Fix:**
```bash
cd /path/to/your/project
git status
# If not a git repo, initialize one:
git init
```

#### "Error: File not found: PROJECT_INDEX.json"

**Cause:** MCP server trying to load index that doesn't exist

**Fix:**
```bash
# Generate index first
/index
# Or manually:
python3 ~/.claude-code-project-index/scripts/project_index.py
```

#### "Error: Invalid JSON in config file"

**Cause:** Syntax error in `.project-index.json`

**Fix:**
```bash
# Validate JSON syntax
python3 -m json.tool .project-index.json

# Fix syntax errors or delete and regenerate
rm .project-index.json
python3 ~/.claude-code-project-index/scripts/project_index.py
```

#### "Warning: Hash validation failed"

**Cause:** Index files may be corrupted

**Fix:**
```bash
# Automatic recovery - tool will regenerate
python3 ~/.claude-code-project-index/scripts/project_index.py
# Hash validation failure triggers full regeneration
```

#### "Error: Module hash mismatch"

**Cause:** Detail module file manually modified or corrupted

**Fix:**
```bash
# Regenerate specific module or full index
rm -rf PROJECT_INDEX.d/
python3 ~/.claude-code-project-index/scripts/project_index.py --mode split
```

## Validation Commands

### Installation Validation

```bash
# 1. Check Python version
python3 --version
# Expected: 3.8.0 or higher

# 2. Verify installation directory
ls -la ~/.claude-code-project-index/
# Expected: scripts/, install.sh, uninstall.sh, requirements.txt

# 3. Check hooks configured
cat ~/.claude/settings.json | jq .hooks
# Expected: UserPromptSubmit and Stop hooks present

# 4. Verify /index command available
# In Claude Code:
# /index
# Expected: PROJECT_INDEX.json generated
```

### Index Validation

```bash
# 1. Check index file exists
ls -la PROJECT_INDEX.json

# 2. Validate JSON structure
python3 -m json.tool PROJECT_INDEX.json > /dev/null && echo "✅ Valid JSON"

# 3. Check version field
cat PROJECT_INDEX.json | jq .version
# Expected: "2.0-split", "2.1-enhanced", or "2.2-submodules"

# 4. Verify detail modules (split format)
ls -1 PROJECT_INDEX.d/*.json | wc -l
# Expected: 1 or more module files

# 5. Check file count matches
cat PROJECT_INDEX.json | jq '.stats.total_files'
git ls-files | wc -l
# Should be similar (index excludes .gitignored files)
```

### MCP Server Validation

```bash
# 1. Check MCP dependencies
pip list | grep -E "mcp|pydantic"
# Expected: mcp>=1.0.0, pydantic>=2.0.0

# 2. Test MCP server startup
cd /path/to/project
timeout 5 python3 project_index_mcp.py &
sleep 2
ps aux | grep project_index_mcp
killall python3
# Expected: Process starts without errors

# 3. Verify config path is absolute
cat ~/.claude/settings.json | jq '.mcpServers."project-index".args[0]'
# Expected: Absolute path like "/Users/you/..."

# 4. Check MCP tools load (in Claude Code)
# After restart, tools should appear:
# - project_index_load_core
# - project_index_load_module
# - project_index_search_files
# - project_index_get_file_info
```

### Hook Validation

```bash
# 1. Check hook scripts exist
ls -la ~/.claude-code-project-index/scripts/i_flag_hook.py
ls -la ~/.claude-code-project-index/scripts/stop_hook.py

# 2. Test hooks manually
cd /path/to/project
python3 ~/.claude-code-project-index/scripts/i_flag_hook.py -i
# Expected: Generates or updates PROJECT_INDEX.json

# 3. Verify hook permissions
ls -l ~/.claude-code-project-index/scripts/*.py
# Expected: Executable permissions (not strictly required but helpful)
```

## Getting Further Help

If you're still experiencing issues after following this guide:

1. **Check for existing issues:**
   - [GitHub Issues](https://github.com/ericbuess/claude-code-project-index/issues)

2. **Create detailed bug report with:**
   - Python version (`python3 --version`)
   - Project size (`git ls-files | wc -l`)
   - Index format (`cat PROJECT_INDEX.json | jq .version`)
   - Full error output (`python3 scripts/project_index.py 2>&1 | tee error.log`)
   - Operating system and version

3. **Review related documentation:**
   - [Best Practices Guide](best-practices.md)
   - [MCP Setup Guide](mcp-setup.md)
   - [Migration Guide](migration.md)

4. **Community tool philosophy:**
   - This is a community tool meant to be forked and adapted
   - Have Claude Code help you fix issues specific to your setup
   - Share your improvements with the community!

---

**Last updated:** 2025-11-11
