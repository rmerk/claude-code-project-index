# Development Guide

## Prerequisites

### Required
- **Python**: 3.8 or higher
- **Operating System**: macOS or Linux
- **Git**: For repository operations
- **jq**: For JSON processing during installation

### Checking Your Environment
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check git
git --version

# Check jq
jq --version
```

---

## Installation

### Quick Install (User)
```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

**What This Does**:
1. Installs to `~/.claude-code-project-index/`
2. Configures Claude Code hooks
3. Creates `/index` slash command
4. Installs `index-analyzer` agent

### Manual Installation (Development)
```bash
# Clone repository
git clone https://github.com/ericbuess/claude-code-project-index.git
cd claude-code-project-index

# Run installer
./install.sh

# Or run directly without installing
python3 scripts/project_index.py
```

---

## Environment Setup

### Python Version Selection
The tool automatically finds the newest Python 3.8+ version. To override:

```bash
# Set preferred Python command
export PYTHON_CMD=python3.11

# Then run install or indexer
./install.sh
```

### Optional Dependencies
```bash
# For clipboard functionality (optional)
pip install pyperclip

# For VM Bridge clipboard over SSH (optional)
pip install vm-client
```

**Note**: Both are optional - the tool gracefully falls back to file export if missing.

---

## Local Development

### Project Structure
```
scripts/
├── project_index.py    # Main indexer
├── index_utils.py      # Parsing utilities
├── i_flag_hook.py      # Hook for -i flag
├── stop_hook.py        # Auto-refresh hook
└── *.sh                # Shell utilities
```

### Running Locally
```bash
# Generate index in current directory
python3 scripts/project_index.py

# Test hook script
python3 scripts/i_flag_hook.py '{"prompt": "test -i50"}'

# Test stop hook
python3 scripts/stop_hook.py
```

### Testing Changes
1. Make changes to `scripts/*.py`
2. Run `python3 scripts/project_index.py` to test
3. Check `PROJECT_INDEX.json` output
4. Verify with Claude Code: `-i` flag in prompt

---

## Build Process

**Note**: This is a direct-use tool with no build step.

- No compilation required
- No bundling needed
- No transpilation
- Just Python scripts

---

## Testing

### Current Testing Strategy
- **Type**: Real-world beta testing
- **Approach**: Community users provide feedback
- **Quality**: Error handling and graceful degradation

### Manual Testing Checklist
- [ ] Index generation works
- [ ] Compression works for large projects
- [ ] Hook integration works
- [ ] Python detection works
- [ ] Clipboard modes work
- [ ] Auto-refresh works

### Testing a Specific Project
```bash
cd /path/to/your/project
python3 ~/.claude-code-project-index/scripts/project_index.py
cat PROJECT_INDEX.json | jq '.stats'
```

---

## Common Development Tasks

### Adding Language Support
1. Edit `index_utils.py`
2. Add extension to `PARSEABLE_LANGUAGES`
3. Implement `extract_<language>_signatures()` function
4. Test with sample files

### Modifying Compression
1. Edit `compress_if_needed()` in `project_index.py`
2. Adjust compression strategies
3. Test with large projects

### Changing Index Size Limits
```python
# In project_index.py
MAX_FILES = 10000  # Max files to index
MAX_INDEX_SIZE = 1024 * 1024  # 1MB compressed
```

---

## Deployment

### User Installation
Users install via:
```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

### Update Existing Installation
```bash
# Uninstall old version
~/.claude-code-project-index/uninstall.sh

# Reinstall latest
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

### CI/CD
**Note**: No CI/CD currently configured. This is a beta community tool.

---

## Configuration

### Hook Configuration
Located in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": ["python3", "~/.claude-code-project-index/scripts/i_flag_hook.py"]
      }
    ],
    "Stop": [
      {
        "command": ["python3", "~/.claude-code-project-index/scripts/stop_hook.py"]
      }
    ]
  }
}
```

### Slash Command
Located in `~/.claude/commands/index.md`:

```markdown
# /index

python3 ~/.claude-code-project-index/scripts/project_index.py
```

---

## Troubleshooting

### Index Not Creating
```bash
# Check Python
python3 --version

# Verify hooks
cat ~/.claude/settings.json | grep i_flag_hook

# Manual generation
python3 ~/.claude-code-project-index/scripts/project_index.py
```

### -i Flag Not Working
1. Run installer again: `./install.sh`
2. Check hooks are configured
3. Restart Claude Code
4. Try manual: `/index`

### Large Project Timeouts
```python
# Edit scripts/project_index.py
MAX_FILES = 5000  # Reduce if needed

# Or edit scripts/i_flag_hook.py timeout
timeout=60  # Increase from 30
```

### Python Version Issues
```bash
# Find Python versions
which -a python3

# Set specific version
export PYTHON_CMD=python3.11

# Reinstall
./install.sh
```

---

## Performance Tips

### For Large Projects
1. Use `.gitignore` to exclude unnecessary files
2. Reduce `MAX_FILES` in `project_index.py`
3. Use lower token targets: `-i25` instead of `-i100`
4. Consider excluding test directories

### Optimize Index Size
- Use `-i` mode for analysis (max 100k)
- Use `-ic` mode only for external AI
- Smaller targets generate faster

---

## Contributing

### Fork and Customize
This tool is designed to be forked:
```bash
# Fork on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/claude-code-project-index.git
cd claude-code-project-index

# Make changes
# Test locally
# Ask Claude Code to help you improve it
```

### Common Customizations
- Add support for new languages
- Adjust compression strategies
- Modify hook behavior
- Add new features

**Philosophy**: Have Claude Code help you unbobble and customize this tool for your needs!

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `PYTHON_CMD` | Override Python command | Auto-detected |
| `INDEX_TARGET_SIZE_K` | Set target token size | 50k |

---

## File Locations

| Path | Purpose |
|------|---------|
| `~/.claude-code-project-index/` | Installation directory |
| `~/.claude/settings.json` | Hook configuration |
| `~/.claude/commands/index.md` | Slash command |
| `~/.claude/agents/index-analyzer.md` | Analysis subagent |
| `PROJECT_INDEX.json` | Generated index (in project root) |

---

## Getting Help

- **Issues**: https://github.com/anthropics/claude-code/issues
- **Customization**: Ask Claude Code to modify the tool for you
- **Philosophy**: This is a community tool - fork it, fix it, make it yours!
