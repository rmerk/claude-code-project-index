# Project Overview: Claude Code Project Index

## Executive Summary

**PROJECT_INDEX** is a hook-based CLI tool that provides spatial-architectural awareness to Claude Code by automatically generating and maintaining a comprehensive project index. It extracts functions, classes, call graphs, and documentation structure to help Claude understand WHERE to place code and HOW components relate.

**Created by**: Eric Buess
**License**: MIT
**Status**: Beta Community Tool
**Version**: 0.2.0-beta

---

## Project Classification

| Attribute | Value |
|-----------|-------|
| **Repository Type** | Monolith |
| **Project Type** | CLI Tool |
| **Primary Language** | Python |
| **Architecture** | Hook-based event-driven system |
| **Dependencies** | Python 3.8+ stdlib only (optional: pyperclip, vm_client) |

---

## Key Features

### 1. Automatic Project Indexing
- Extracts functions, classes, and methods with full signatures
- Parses Python, JavaScript/TypeScript, and Shell scripts
- Builds bidirectional call graphs
- Maps markdown documentation structure
- Infers directory and file purposes

### 2. Intelligent Compression
- Progressive compression to fit within token limits
- Target sizes from 1k to 800k tokens
- Preserves most important architectural information
- Optimized dense format saves ~50% space

### 3. Hook-Based Integration
- **UserPromptSubmit hook**: Detects `-i` flag → generates index → invokes analyzer
- **Stop hook**: Auto-refreshes index after every session
- Seamless Claude Code integration

### 4. Smart Regeneration
- File change detection via hashing
- Skips regeneration if index is current
- Remembers user's preferred token size
- Fast incremental updates

### 5. Multiple Modes
- **Interactive Mode** (`-i[size]`): Generate and analyze within Claude
- **Clipboard Mode** (`-ic[size]`): Export for external AI tools
- **Manual Mode**: `/index` slash command

---

## Technology Stack Summary

### Core Technologies

| Category | Technology | Version/Details |
|----------|-----------|-----------------|
| **Language** | Python | 3.8+ required |
| **Scripting** | Bash | macOS/Linux compatible |
| **Integration** | Claude Code Hooks | UserPromptSubmit, Stop |
| **Parsing** | Regex + AST-like | Python, JS/TS, Shell |

### Standard Library Usage
- `json`, `pathlib`, `re`, `subprocess`, `hashlib`, `typing`
- No external dependencies required for core functionality

### Optional Dependencies
- `pyperclip` - Clipboard operations (graceful fallback)
- `vm_client` - VM Bridge for SSH clipboard (optional)

---

## Architecture Highlights

### Event-Driven Hook System
```
User Prompt with -i
    ↓
UserPromptSubmit Hook
    ↓
i_flag_hook.py detects flag
    ↓
Generates/refreshes PROJECT_INDEX.json
    ↓
Invokes index-analyzer subagent
    ↓
Returns analysis to main agent
```

### Index Generation Pipeline
```
1. File Discovery (git ls-files or manual walk)
2. File Filtering (gitignore-aware)
3. Language Detection
4. Parsing (functions, classes, methods)
5. Call Graph Construction
6. Documentation Mapping
7. Compression
8. JSON Output
```

### Compression Strategy
Progressive compression when size exceeds limits:
1. Reduce directory tree
2. Truncate docstrings
3. Remove docstrings
4. Remove documentation map
5. Emergency truncation (keep most important files)

---

## Repository Structure

**Type**: Monolith with bundled framework

**Primary Components**:
- `/scripts` - Core indexing engine (Python)
- `/bmad` - Optional BMad Method framework (bundled)
- `/agents` - Claude Code integration agents
- `/.claude` - Configuration and hooks
- `/docs` - Generated documentation

**Lines of Code**: ~3,047 Python LOC

---

## Quick Reference

### Installation
```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

### Basic Usage
```bash
# Add -i flag to any prompt
claude "fix the auth bug -i"

# Manual index generation
/index

# Clipboard export for external AI
claude "analyze codebase -ic200"
```

### Key Files
- `scripts/project_index.py` - Main indexer
- `scripts/i_flag_hook.py` - Hook integration
- `scripts/index_utils.py` - Parsing utilities
- `install.sh` - Installer
- `PROJECT_INDEX.json` - Generated output

---

## Use Cases

### 1. Prevent Code Duplication
Claude can see all existing functions before creating new ones

### 2. Correct Code Placement
Claude understands directory structure and purposes

### 3. Dependency Analysis
Call graphs show which functions depend on others

### 4. Impact Analysis
See what breaks when modifying a function

### 5. Architectural Awareness
Claude maintains consistency with existing patterns

---

## Target Audience

- **Developers** using Claude Code for software development
- **Teams** wanting AI to understand their codebase architecture
- **Individual contributors** building on existing codebases
- **Anyone** who wants to prevent AI-generated code duplication

---

## Project Philosophy

**"Fork It, Fix It, Make It Yours"**

This is a beta community tool designed to be customized by Claude Code itself:
- Hit an issue? Ask Claude to fix it
- Need a feature? Have Claude add it
- Want different behavior? Let Claude modify it

**Not a Product** - It's a tool shared for community benefit. Use Claude Code to adapt it to your exact needs.

---

## Integration Points

### With Claude Code
- Hooks configured in `~/.claude/settings.json`
- Slash commands in `~/.claude/commands/`
- Agents in `~/.claude/agents/`

### With BMad Framework (Optional)
- Complete project management workflows
- Agent-based development methodology
- Test architecture framework
- Planning and solutioning tools

### With External AI Tools
- `-ic` mode exports to clipboard
- Compatible with Gemini, ChatGPT, Grok, etc.
- Formatted for readability in external tools

---

## Getting Started

### Quick Start (3 Steps)
1. Install: `curl -fsSL <url> | bash`
2. Add `-i` to any Claude prompt
3. Claude now knows your codebase structure!

### Next Steps
- Read [Development Guide](./development-guide.md)
- Review [Code Structure](./code-structure.md)
- Check [Source Tree](./source-tree.md)
- Explore the generated `PROJECT_INDEX.json`

---

## Links to Detailed Documentation

- **[Development Guide](./development-guide.md)** - Setup, testing, deployment
- **[Code Structure](./code-structure.md)** - Code analysis and architecture
- **[Source Tree](./source-tree.md)** - Directory structure and organization
- **[README.md](../README.md)** - Main project README

---

## Project Metrics

| Metric | Value |
|--------|-------|
| **Python Files** | 4 core modules |
| **Total LOC** | ~3,047 lines |
| **Shell Scripts** | 4 utilities |
| **Supported Languages** | Python, JS/TS, Shell (parsing) + 20+ (listing) |
| **Documentation Files** | 34+ (bmad framework included) |

---

## Contact & Resources

- **Author**: [Eric Buess](https://github.com/ericbuess)
- **Twitter/X**: [@EricBuess](https://x.com/EricBuess)
- **YouTube**: [EricBuess](https://www.youtube.com/@EricBuess)
- **Repository**: [GitHub](https://github.com/ericbuess/claude-code-project-index)
- **Issues**: [Claude Code Issues](https://github.com/anthropics/claude-code/issues)

---

## Contributing

**Fork and customize!** This tool is meant to be adapted to your needs using Claude Code itself.

```bash
# Fork on GitHub
git clone https://github.com/YOUR_USERNAME/claude-code-project-index.git

# Make it yours
# Ask Claude: "Fix the timeout issue for my 5000-file project"
# Ask Claude: "Add support for Ruby with full parsing"
# Ask Claude: "Make compression work better for my monorepo"
```

**Share improvements** with the community if you'd like!
