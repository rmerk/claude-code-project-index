# Project Documentation Index

**Generated**: 2025-10-30
**Project**: claude-code-project-index
**Type**: CLI Tool (Python)

---

## Project Overview

**Claude Code Project Index** is a hook-based CLI tool that provides architectural awareness to Claude Code by automatically generating and maintaining comprehensive project indices.

- **Repository Type**: Monolith
- **Primary Language**: Python 3.8+
- **Architecture**: Hook-based event-driven system
- **Status**: Beta Community Tool

---

## Quick Reference

| Category | Details |
|----------|---------|
| **Tech Stack** | Python 3.8+, Bash scripts |
| **Entry Point** | `scripts/project_index.py` |
| **Architecture Pattern** | Hook-based CLI |
| **Lines of Code** | ~3,047 Python LOC |

---

## Generated Documentation

### Core Documentation
- **[Project Overview](./project-overview.md)** - Executive summary, features, architecture highlights
- **[Architecture](./architecture.md)** - System architecture, data flow, design decisions
- **[Code Structure](./code-structure.md)** - Module breakdown, entry points, dependencies
- **[Source Tree](./source-tree.md)** - Annotated directory structure with explanations
- **[Development Guide](./development-guide.md)** - Setup, testing, deployment, troubleshooting

### Existing Documentation
- **[README.md](../README.md)** - Main project README with installation and usage
- **[CLAUDE.md](../CLAUDE.md)** - Claude Code project instructions
- **[LICENSE](../LICENSE)** - MIT License

### BMad Framework Documentation
The project includes the BMad Method framework (optional):
- **[BMM Overview](../bmad/bmm/README.md)** - BMad Method Module overview
- **[Test Architecture](../bmad/bmm/testarch/README.md)** - Test architecture guide
- **[Workflows Guide](../bmad/bmm/workflows/README.md)** - Complete workflows documentation

---

## Getting Started

### Installation
```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

### Basic Usage
```bash
# Add -i flag to any Claude prompt
claude "fix the auth bug -i"

# Generate index manually
/index

# Export for external AI
claude "analyze codebase -ic200"
```

### First Steps
1. Read [Project Overview](./project-overview.md) for high-level understanding
2. Review [Development Guide](./development-guide.md) for setup
3. Check [Code Structure](./code-structure.md) to understand the codebase
4. Explore [Architecture](./architecture.md) for technical details

---

## Documentation Map

### For Users
Start here if you're using the tool:
1. **[README.md](../README.md)** - Quick start guide
2. **[Project Overview](./project-overview.md)** - Feature overview
3. **[Development Guide](./development-guide.md)** - Installation and troubleshooting

### For Developers
Start here if you're contributing or customizing:
1. **[Code Structure](./code-structure.md)** - Code organization
2. **[Architecture](./architecture.md)** - Technical architecture
3. **[Source Tree](./source-tree.md)** - Directory structure
4. **[Development Guide](./development-guide.md)** - Development workflow

### For Understanding the Codebase
Best sequence for deep understanding:
1. **[Project Overview](./project-overview.md)** - What and why
2. **[Architecture](./architecture.md)** - How it works
3. **[Code Structure](./code-structure.md)** - Implementation details
4. **[Source Tree](./source-tree.md)** - File organization

---

## Key Features

### Automatic Project Indexing
- Extracts functions, classes, methods with signatures
- Parses Python, JS/TS, Shell scripts
- Builds bidirectional call graphs
- Maps markdown documentation
- Infers directory/file purposes

### Intelligent Compression
- Progressive compression strategies
- 1k to 800k token targets
- Preserves critical architecture info
- ~50% space savings via dense format

### Seamless Integration
- Hook-based (UserPromptSubmit, Stop)
- `-i` flag detection
- Auto-refresh after sessions
- Slash command: `/index`

---

## Project Structure

```
claude-code-project-index/
├── scripts/              # Core indexing engine
│   ├── project_index.py  # Main entry point
│   ├── index_utils.py    # Parsing utilities
│   ├── i_flag_hook.py    # Hook integration
│   └── stop_hook.py      # Auto-refresh
├── bmad/                 # BMad Method framework (optional)
├── agents/               # Claude Code agents
├── .claude/              # Configuration
├── docs/                 # This documentation
└── *.sh                  # Installation scripts
```

See [Source Tree](./source-tree.md) for detailed structure.

---

## Entry Points

| File | Purpose | How to Run |
|------|---------|-----------|
| `project_index.py` | Generate index | `python3 scripts/project_index.py` |
| `i_flag_hook.py` | Hook for -i flag | Automatic (UserPromptSubmit) |
| `stop_hook.py` | Auto-refresh | Automatic (Stop hook) |
| `install.sh` | Install tool | `bash install.sh` |
| `/index` command | Manual generation | Type `/index` in Claude |

---

## Technology Stack

### Core Technologies
- **Python 3.8+** - Main implementation language
- **Bash** - Installation and utilities
- **Git** - File discovery (optional, falls back)
- **JSON** - Output format

### Standard Library Only
No external dependencies required:
- `json`, `pathlib`, `re`, `subprocess`, `hashlib`, `typing`

### Optional Dependencies
- `pyperclip` - Clipboard operations (graceful fallback)
- `vm_client` - VM Bridge for SSH (optional)

---

## Common Tasks

### Using the Tool
```bash
# In any project, add -i to your prompt
claude "refactor the auth system -i"

# Or manually generate
/index

# Check the generated index
cat PROJECT_INDEX.json | jq '.stats'
```

### Developing
```bash
# Clone repository
git clone <repo-url>
cd claude-code-project-index

# Run locally
python3 scripts/project_index.py

# Test changes
python3 scripts/i_flag_hook.py '{"prompt": "test -i50"}'
```

### Customizing
```bash
# Fork repository
# Ask Claude Code:
claude "Add support for Ruby parsing"
claude "Fix timeout for my 5000-file project"
claude "Change compression to preserve more docstrings"
```

---

## Integration with Claude Code

### Hooks Configured
1. **UserPromptSubmit** → Detects `-i` flag → Generates index → Invokes analyzer
2. **Stop** → Auto-refreshes index after session

### Files Modified
- `~/.claude/settings.json` - Hook configuration
- `~/.claude/commands/index.md` - Slash command
- `~/.claude/agents/index-analyzer.md` - Analysis subagent

### Installation Location
- `~/.claude-code-project-index/` - Tool installation
- `PROJECT_INDEX.json` - Generated in each project root

---

## BMad Framework (Optional)

This project bundles the BMad Method framework for optional use:

### What is BMad?
Complete project management and development workflow system with:
- Agent-based development (PM, SM, Architect, Developer, etc.)
- Full SDLC workflows (Analysis, Planning, Solutioning, Implementation)
- Test architecture framework
- Document generation workflows

### BMad Documentation
- [BMM README](../bmad/bmm/README.md) - Overview
- [Workflows](../bmad/bmm/workflows/README.md) - Complete workflow guide
- [Test Architecture](../bmad/bmm/testarch/README.md) - Testing framework

### Is BMad Required?
**No.** The core PROJECT_INDEX tool works independently. BMad is bundled as an optional feature.

---

## Troubleshooting

### Common Issues

**Index not creating?**
1. Check Python: `python3 --version`
2. Verify hooks: `cat ~/.claude/settings.json | grep i_flag_hook`
3. Manual test: `python3 ~/.claude-code-project-index/scripts/project_index.py`

**-i flag not working?**
1. Reinstall: `./install.sh`
2. Restart Claude Code
3. Try manual: `/index`

**Large project timeouts?**
- Reduce MAX_FILES in `project_index.py`
- Use lower token targets: `-i25`
- Improve .gitignore patterns

See [Development Guide](./development-guide.md#troubleshooting) for more.

---

## Links & Resources

### Official Resources
- **GitHub Repository**: [ericbuess/claude-code-project-index](https://github.com/ericbuess/claude-code-project-index)
- **Claude Code Issues**: [github.com/anthropics/claude-code/issues](https://github.com/anthropics/claude-code/issues)

### Author
- **Eric Buess**
- Twitter/X: [@EricBuess](https://x.com/EricBuess)
- YouTube: [EricBuess](https://www.youtube.com/@EricBuess)
- GitHub: [ericbuess](https://github.com/ericbuess)

### Related Projects
- [Claude Code Docs Mirror](https://github.com/ericbuess/claude-code-docs)
- [VM Bridge](https://github.com/ericbuess/vm-bridge) (SSH clipboard)

---

## Contributing

**Philosophy**: Fork it, fix it, make it yours!

This is a **community tool** designed to be customized:
1. Fork the repository
2. Ask Claude Code to modify it for your needs
3. Share improvements (optional)

**Common Customizations**:
- Add new language support
- Adjust compression strategies
- Modify hook behavior
- Add features

**Remember**: Claude Code can rewrite this tool to match your exact needs!

---

## License

MIT License - See [LICENSE](../LICENSE) file

---

## Document Generation

This documentation was generated by the BMad `document-project` workflow with exhaustive scanning.

**Scan Details**:
- **Mode**: Initial scan (exhaustive)
- **Files Analyzed**: All Python and shell scripts
- **Documentation Generated**: 2025-10-30
- **Project Root**: `/Users/rchoi/Developer/claude-code-project-index`

---

## Next Steps

### If You're New Here
1. Read [Project Overview](./project-overview.md)
2. Install the tool (see above)
3. Try it with `-i` in any prompt

### If You're Developing
1. Review [Architecture](./architecture.md)
2. Check [Code Structure](./code-structure.md)
3. Read [Development Guide](./development-guide.md)

### If You're Customizing
1. Fork the repository
2. Ask Claude: "Help me customize this for [your need]"
3. Let Claude modify the code for you

---

**Welcome to PROJECT_INDEX! 🚀**

*Give Claude architectural awareness of your codebase*
