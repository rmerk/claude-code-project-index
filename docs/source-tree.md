# Source Tree Analysis

## Project Root Structure

```
claude-code-project-index/
├── scripts/                # Core indexing engine (Python)
│   ├── project_index.py    # Main entry point - generates PROJECT_INDEX.json
│   ├── index_utils.py      # Shared parsing utilities (Python/JS/Shell)
│   ├── i_flag_hook.py      # UserPromptSubmit hook for -i flag detection
│   ├── stop_hook.py        # Stop hook for auto-refresh
│   ├── find_python.sh      # Python version detection utility
│   └── run_python.sh       # Python execution wrapper
│
├── bmad/                   # BMad Method framework (optional, bundled)
│   ├── core/               # Core framework components
│   │   ├── agents/         # Core agent definitions
│   │   ├── tasks/          # Reusable task definitions (workflow.xml, etc.)
│   │   ├── tools/          # Framework tools
│   │   └── workflows/      # Core workflows (brainstorming, etc.)
│   │
│   ├── bmm/                # BMad Method Module - project management workflows
│   │   ├── agents/         # BMM-specific agents (PM, SM, Architect, etc.)
│   │   ├── workflows/      # Complete project workflow system
│   │   │   ├── 1-analysis/ # Analysis phase workflows
│   │   │   ├── 2-plan-workflows/ # Planning workflows (PRD, UX, etc.)
│   │   │   ├── 3-solutioning/  # Architecture and solutioning
│   │   │   ├── 4-implementation/ # Development workflows
│   │   │   └── testarch/   # Test architecture workflows
│   │   ├── tasks/          # Reusable BMM tasks
│   │   ├── teams/          # Team configuration
│   │   └── testarch/       # Test architecture knowledge base
│   │
│   ├── _cfg/               # Configuration files
│   │   ├── agents/         # Agent configurations for IDEs
│   │   └── ides/           # IDE-specific configurations
│   │
│   └── docs/               # BMad framework documentation
│
├── agents/                 # Agent definitions for Claude Code
│   └── index-analyzer.md   # Subagent for deep index analysis
│
├── .claude/                # Claude Code configuration
│   ├── agents/             # Additional agents
│   └── commands/           # Slash commands (/index, etc.)
│
├── .claude-code-ericbuess/ # User-specific Claude Code context
│
├── .cursor/                # Cursor IDE configuration
│   └── rules/              # IDE-specific rules
│
├── docs/                   # Generated project documentation
│   └── stories/            # User stories (if using BMad workflows)
│
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── README.md               # Project documentation
├── CLAUDE.md               # Claude Code project instructions
├── LICENSE                 # MIT License
└── PROJECT_INDEX.json      # Generated project index (if created)
```

---

## Critical Directories Explained

### `/scripts` - Core Indexing Engine
**Purpose**: Contains the main Python indexing logic
**Key Files**:
- `project_index.py` - Orchestrates index generation, compression, call graph building
- `index_utils.py` - Language parsers, file filtering, directory inference
- `i_flag_hook.py` - Hook integration for Claude Code
- `stop_hook.py` - Auto-refresh after sessions
- `find_python.sh` - Automatic Python version detection

**Entry Points**:
- CLI: `python3 scripts/project_index.py`
- Hook: Automatic via `-i` flag or session end

---

### `/bmad` - BMad Method Framework (Bundled)
**Purpose**: Complete project management framework (optional feature)
**Structure**:
- `core/` - Framework core (agents, tasks, workflows)
- `bmm/` - BMad Method Module for full SDLC workflows
- `_cfg/` - Configuration for IDE integrations
- `docs/` - Framework documentation

**Note**: This is a bundled framework that provides project management workflows. Not required for basic indexing functionality.

---

### `/agents` - Claude Code Agents
**Purpose**: Specialized AI agents for index analysis
**Key Files**:
- `index-analyzer.md` - Deep analysis subagent invoked by `-i` flag

**Invocation**: Automatically called when using `-i` flag

---

### `/.claude` - Claude Code Integration
**Purpose**: Claude Code configuration and slash commands
**Contents**:
- `/commands` - Slash command definitions (`/index`)
- `/agents` - Additional agent definitions

**Installation**: Configured by `install.sh`

---

### `/docs` - Generated Documentation
**Purpose**: Output folder for generated project documentation
**Generated Files** (from document-project workflow):
- `index.md` - Master documentation index
- `project-overview.md` - High-level project summary
- `source-tree.md` - This file - annotated directory structure
- `code-structure.md` - Code analysis and architecture
- And more...

**Stories Subfolder**: User stories if using BMad workflows

---

## File Organization Patterns

### Configuration Files
- `.gitignore` - Git ignore patterns
- `CLAUDE.md` - Project-level instructions for Claude Code
- `PROJECT_INDEX.json` - Generated index (gitignored)

### Documentation Files
- `README.md` - Main project README
- `LICENSE` - MIT License
- `docs/` - Generated documentation folder

### Installation Files
- `install.sh` - Bash installer for macOS/Linux
- `uninstall.sh` - Complete removal script

---

## Integration Points

### Claude Code Hooks
**Location**: `~/.claude/settings.json`

**Configured Hooks**:
1. **UserPromptSubmit** → `scripts/i_flag_hook.py`
   - Detects `-i` or `-ic` flags in user prompts
   - Generates/refreshes PROJECT_INDEX.json
   - Invokes index-analyzer subagent

2. **Stop** → `scripts/stop_hook.py`
   - Runs after every Claude Code session
   - Auto-refreshes PROJECT_INDEX.json if it exists

### Installation Directory
**Location**: `~/.claude-code-project-index/`
**Contents**: Copy of all scripts and agents
**Python Cache**: `~/.claude-code-project-index/.python_cmd`

---

## Shared Code Patterns

### Python Utilities (`index_utils.py`)
- Language parsers (Python, JS/TS, Shell)
- File purpose inference
- Directory purpose inference
- Gitignore pattern matching
- Call graph construction

### Hook Infrastructure
- Project root detection
- File change hashing
- Smart regeneration (skip if current)
- Clipboard integration (multiple fallbacks)

---

## Multi-Part Structure

This project is a **monolith** with supplementary framework:

1. **Core Tool** (`/scripts`) - The main PROJECT_INDEX CLI tool
2. **BMad Framework** (`/bmad`) - Optional bundled project management framework
3. **Integration Layer** (`/agents`, `/.claude`) - Claude Code integration

**How They Relate**:
- Core tool (`scripts/`) is standalone and fully functional
- BMad framework provides optional project workflows
- Integration layer connects both to Claude Code

---

## Development Workflow

**Local Development**:
1. Clone repository
2. Run `./install.sh` to install
3. Make changes to `scripts/*.py`
4. Test with `python3 scripts/project_index.py`
5. Uninstall with `./uninstall.sh` if needed

**User Installation**:
```bash
curl -fsSL https://raw.githubusercontent.com/ericbuess/claude-code-project-index/main/install.sh | bash
```

---

## Important Notes

- **No node_modules**: This is a Python tool, no Node.js dependencies
- **No virtual environment required**: Uses system Python 3.8+
- **Gitignore aware**: Automatically excludes ignored files
- **Hook-based**: Seamless integration with Claude Code
