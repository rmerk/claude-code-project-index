#!/bin/bash
set -eo pipefail

# Claude Code PROJECT_INDEX Installer
# Installs PROJECT_INDEX to ~/.claude-code-project-index

# Parse command-line flags (Story 3.4, AC #3, #9, Story 3.5 AC #5)
MODE="install"  # Default mode: install, upgrade, rollback
CONFIGURE_MCP_TOOL=""  # Manual MCP configuration: claude-code, cursor, desktop, or empty
for arg in "$@"; do
    case $arg in
        --upgrade)
            MODE="upgrade"
            ;;
        --rollback)
            MODE="rollback"
            ;;
        --configure-mcp=*)
            CONFIGURE_MCP_TOOL="${arg#*=}"
            if [[ ! "$CONFIGURE_MCP_TOOL" =~ ^(claude-code|cursor|desktop)$ ]]; then
                echo "Error: Invalid MCP tool: $CONFIGURE_MCP_TOOL"
                echo "Valid options: claude-code, cursor, desktop"
                exit 1
            fi
            ;;
        --help)
            echo "Claude Code PROJECT_INDEX Installer"
            echo "Usage: ./install.sh [--upgrade|--rollback|--configure-mcp=<tool>|--help]"
            echo ""
            echo "Options:"
            echo "  (no flags)              Install PROJECT_INDEX for the first time"
            echo "  --upgrade               Download and install the latest version from GitHub"
            echo "  --rollback              Restore the previous version from backup"
            echo "  --configure-mcp=<tool>  Manually configure MCP for specific tool"
            echo "                          (claude-code, cursor, or desktop)"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown flag: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Claude Code PROJECT_INDEX Installer"
echo "===================================="
echo ""

# Fixed installation location
INSTALL_DIR="$HOME/.claude-code-project-index"
BACKUP_DIR="$INSTALL_DIR/backups"

# Detect OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    echo "✓ Detected macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    echo "✓ Detected Linux"
else
    echo "❌ Error: Unsupported OS type: $OSTYPE"
    echo "This installer supports macOS and Linux only"
    exit 1
fi

# Rollback function (Story 3.4, AC #9)
rollback_installation() {
    echo "🔄 Rolling back to previous version..."
    echo ""

    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo "❌ Error: No backup directory found at $BACKUP_DIR"
        echo "   Cannot rollback without a backup"
        exit 1
    fi

    # Find most recent backup
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | head -1)

    if [[ -z "$LATEST_BACKUP" ]]; then
        echo "❌ Error: No backups found in $BACKUP_DIR"
        echo "   Cannot rollback without a backup"
        exit 1
    fi

    BACKUP_PATH="$BACKUP_DIR/$LATEST_BACKUP"
    echo "📦 Found backup: $LATEST_BACKUP"

    # Remove current installation (excluding backups directory)
    echo "   Removing current installation..."
    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name 'backups' -exec rm -rf {} +

    # Restore from backup
    echo "   Restoring from backup..."
    cp -r "$BACKUP_PATH"/* "$INSTALL_DIR/"

    # Make scripts executable
    chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/scripts"/*.sh 2>/dev/null || true

    # Verify restoration
    if [[ -f "$INSTALL_DIR/scripts/project_index.py" ]]; then
        # Get restored version
        RESTORED_VERSION="unknown"
        if [[ -f "$INSTALL_DIR/VERSION" ]]; then
            RESTORED_VERSION=$(cat "$INSTALL_DIR/VERSION")
        fi

        echo ""
        echo "✅ Rollback successful!"
        echo "   Restored version: $RESTORED_VERSION"
        echo "   Backup used: $LATEST_BACKUP"
        exit 0
    else
        echo "❌ Error: Rollback failed - restored files are incomplete"
        exit 1
    fi
}

# Upgrade function (Story 3.4, AC #3)
upgrade_installation() {
    echo "⬆️  Upgrading to latest version from GitHub..."
    echo ""

    if [[ ! -d "$INSTALL_DIR" ]]; then
        echo "❌ Error: No existing installation found at $INSTALL_DIR"
        echo "   Run without --upgrade flag for first-time installation"
        exit 1
    fi

    # Get current version
    CURRENT_VERSION="unknown"
    if [[ -f "$INSTALL_DIR/VERSION" ]]; then
        CURRENT_VERSION=$(cat "$INSTALL_DIR/VERSION")
    fi
    echo "📦 Current version: $CURRENT_VERSION"

    # Create backup
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/backup-$TIMESTAMP"

    echo "   Creating backup at $BACKUP_PATH..."
    mkdir -p "$BACKUP_PATH"

    # Backup all files except backups directory itself
    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name 'backups' -exec cp -r {} "$BACKUP_PATH/" \;

    echo "   ✓ Backup created"

    # Download latest release
    echo ""
    echo "📥 Downloading latest release from GitHub..."
    TEMP_DIR=$(mktemp -d)

    if ! git clone --depth 1 https://github.com/ericbuess/claude-code-project-index.git "$TEMP_DIR" 2>/dev/null; then
        echo "❌ Error: Failed to download latest release from GitHub"
        echo "   Your current installation is unchanged"
        echo "   To rollback if needed: ./install.sh --rollback"
        exit 1
    fi

    # Get new version
    NEW_VERSION="unknown"
    if [[ -f "$TEMP_DIR/VERSION" ]]; then
        NEW_VERSION=$(cat "$TEMP_DIR/VERSION")
    fi

    echo "   ✓ Downloaded version: $NEW_VERSION"

    # Install new version (excluding .git directory and backups)
    echo ""
    echo "📦 Installing new version..."

    # Remove current installation (except backups)
    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name 'backups' -exec rm -rf {} +

    # Copy new files
    cp -r "$TEMP_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    rm -rf "$INSTALL_DIR/.git"  # Remove .git directory from install location

    # Create VERSION file if it doesn't exist (backward compatibility)
    if [[ ! -f "$INSTALL_DIR/VERSION" ]]; then
        echo "v0.3.0" > "$INSTALL_DIR/VERSION"
    fi

    # Clean up temp directory
    rm -rf "$TEMP_DIR"

    # Make scripts executable
    chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/scripts"/*.sh 2>/dev/null || true

    # Validate installation
    echo ""
    echo "✅ Validating new installation..."

    if [[ ! -f "$INSTALL_DIR/scripts/project_index.py" ]]; then
        echo "❌ Error: Validation failed - essential files missing"
        echo "   Rolling back to previous version..."
        rm -rf "$INSTALL_DIR"/*
        cp -r "$BACKUP_PATH"/* "$INSTALL_DIR/"
        echo "   ✓ Rollback complete - your installation is restored"
        exit 1
    fi

    echo "   ✓ Validation passed"
    echo ""
    echo "=========================================="
    echo "✅ Upgrade successful!"
    echo "=========================================="
    echo ""
    echo "📦 Upgraded: $CURRENT_VERSION → $NEW_VERSION"
    echo "💾 Backup available at: $BACKUP_PATH"
    echo "   (To rollback: ./install.sh --rollback)"
    echo ""
    exit 0
}

# MCP Tool Detection Functions (Story 3.5, AC #1-4)

# Detect Claude Code CLI
detect_claude_code() {
    if [[ -f ~/.config/claude-code/mcp.json ]] || [[ -d ~/.config/claude-code/ ]]; then
        return 0  # Found
    fi
    return 1  # Not found
}

# Detect Cursor IDE
detect_cursor() {
    local cursor_paths=(
        "$HOME/Library/Application Support/Cursor/"  # macOS
        "$HOME/.config/Cursor/"                      # Linux
        "$APPDATA/Cursor/"                           # Windows (if running under WSL/Git Bash)
    )
    for path in "${cursor_paths[@]}"; do
        if [[ -d "$path" ]]; then
            return 0  # Found
        fi
    done
    return 1  # Not found
}

# Detect Claude Desktop
detect_claude_desktop() {
    local desktop_paths=(
        "$HOME/Library/Application Support/Claude/"  # macOS
        "$HOME/.config/Claude/"                      # Linux
        "$APPDATA/Claude/"                           # Windows
    )
    for path in "${desktop_paths[@]}"; do
        if [[ -d "$path" ]]; then
            return 0  # Found
        fi
    done
    return 1  # Not found
}

# Get config path for detected tool
get_mcp_config_path() {
    local tool=$1
    case $tool in
        claude-code)
            echo "$HOME/.config/claude-code/mcp.json"
            ;;
        cursor)
            # Try macOS first, then Linux
            if [[ "$OS_TYPE" == "macos" ]]; then
                echo "$HOME/Library/Application Support/Cursor/User/globalStorage/mcp-config.json"
            else
                echo "$HOME/.config/Cursor/User/globalStorage/mcp-config.json"
            fi
            ;;
        desktop)
            # Try macOS first, then Linux
            if [[ "$OS_TYPE" == "macos" ]]; then
                echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            else
                echo "$HOME/.config/Claude/claude_desktop_config.json"
            fi
            ;;
    esac
}

# Handle upgrade and rollback modes
if [[ "$MODE" == "rollback" ]]; then
    rollback_installation
elif [[ "$MODE" == "upgrade" ]]; then
    upgrade_installation
fi

# Continue with normal installation for MODE="install"

# Check dependencies
echo ""
echo "Checking dependencies..."

# Check for git and jq
for cmd in git jq; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Error: $cmd is required but not installed"
        echo "Please install $cmd and try again"
        exit 1
    fi
done

# Find Python intelligently
# When running via curl | bash, BASH_SOURCE is not set
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    # Running via curl | bash - scripts won't be available yet
    SCRIPT_DIR=""
fi

if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/scripts/find_python.sh" ]]; then
    PYTHON_CMD=$(bash "$SCRIPT_DIR/scripts/find_python.sh")
else
    # Fallback to simple check if find_python.sh doesn't exist yet
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Python 3.8+ is required but not found"
        echo "Please install Python 3.8+ and try again"
        exit 1
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    exit 1
fi

echo "✓ All dependencies satisfied"

# Check if already installed
if [[ -d "$INSTALL_DIR" ]]; then
    echo ""
    echo "⚠️  Found existing installation at $INSTALL_DIR"
    
    # Check if we're running interactively or via pipe
    if [ -t 0 ]; then
        # Interactive mode - can use read
        read -p "Remove and reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    else
        # Non-interactive mode (curl | bash) - auto-reinstall
        echo "Running in non-interactive mode, removing and reinstalling..."
    fi
    
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR"
fi

# Clone or copy repository
echo ""
echo "Installing PROJECT_INDEX..."

# If we're running from the repo, copy files
# (SCRIPT_DIR already set above during Python detection)
if [[ -f "$SCRIPT_DIR/scripts/project_index.py" || -f "$SCRIPT_DIR/README.md" ]]; then
    echo "Installing from local repository..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy essential files
    cp "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts/project-index-helper.sh" "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/.gitignore" "$INSTALL_DIR/" 2>/dev/null || true
    
    # Create scripts directory and copy all scripts
    mkdir -p "$INSTALL_DIR/scripts"
    cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    cp "$SCRIPT_DIR/scripts"/*.sh "$INSTALL_DIR/scripts/" 2>/dev/null || true
    
    # Copy agent files to Claude's agents directory
    if [[ -d "$SCRIPT_DIR/agents" ]]; then
        mkdir -p "$HOME/.claude/agents"
        cp "$SCRIPT_DIR/agents"/*.md "$HOME/.claude/agents/" 2>/dev/null || true
        echo "   ✓ Agent files installed to ~/.claude/agents/"
    fi
    
    # Remove the old setup script if it was copied
    rm -f "$INSTALL_DIR/scripts/setup_hooks.py"
    
    echo "✓ Files copied to $INSTALL_DIR"
else
    # Clone from GitHub
    echo "Cloning from GitHub..."
    git clone https://github.com/ericbuess/claude-code-project-index.git "$INSTALL_DIR"
    
    # Move Python files to scripts directory
    mkdir -p "$INSTALL_DIR/scripts"
    mv "$INSTALL_DIR"/*.py "$INSTALL_DIR/scripts/" 2>/dev/null || true
    rm -f "$INSTALL_DIR/scripts/setup_hooks.py"
    
    # Copy agent files to Claude's agents directory
    if [[ -d "$INSTALL_DIR/agents" ]]; then
        mkdir -p "$HOME/.claude/agents"
        cp "$INSTALL_DIR/agents"/*.md "$HOME/.claude/agents/" 2>/dev/null || true
        echo "   ✓ Agent files installed to ~/.claude/agents/"
    fi
    
    echo "✓ Repository cloned to $INSTALL_DIR"
fi

# Create templates directory and preset files
echo ""
echo "Creating configuration templates..."
mkdir -p "$INSTALL_DIR/templates"

# Create small.json preset
cat > "$INSTALL_DIR/templates/small.json" << 'EOF'
{
  "_preset": "small",
  "_generated": "auto",
  "mode": "single",
  "threshold": 100,
  "submodule_config": {
    "enabled": false
  },
  "tiered_docs": {
    "enabled": false
  },
  "relevance_scoring": {
    "enabled": false
  },
  "impact_analysis": {
    "enabled": false
  }
}
EOF

# Create medium.json preset
cat > "$INSTALL_DIR/templates/medium.json" << 'EOF'
{
  "_preset": "medium",
  "_generated": "auto",
  "mode": "auto",
  "threshold": 500,
  "submodule_config": {
    "enabled": true,
    "threshold": 100,
    "strategy": "auto",
    "max_depth": 3
  },
  "tiered_docs": {
    "enabled": true,
    "include_all_tiers": false
  },
  "relevance_scoring": {
    "enabled": true,
    "top_n": 5,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 1.0,
      "semantic_keyword": 1.0
    },
    "temporal_windows": {
      "recent_7d": 5.0,
      "medium_30d": 2.0,
      "older_90d": 1.0
    }
  },
  "impact_analysis": {
    "enabled": true,
    "max_depth": 10,
    "include_indirect": true,
    "show_line_numbers": true
  }
}
EOF

# Create large.json preset
cat > "$INSTALL_DIR/templates/large.json" << 'EOF'
{
  "_preset": "large",
  "_generated": "auto",
  "mode": "split",
  "threshold": 1000,
  "submodule_config": {
    "enabled": true,
    "threshold": 100,
    "strategy": "auto",
    "max_depth": 3
  },
  "tiered_docs": {
    "enabled": true,
    "include_all_tiers": false
  },
  "relevance_scoring": {
    "enabled": true,
    "top_n": 3,
    "weights": {
      "explicit_file_ref": 10.0,
      "temporal_recent": 1.0,
      "semantic_keyword": 1.0
    },
    "temporal_windows": {
      "recent_7d": 5.0,
      "medium_30d": 2.0,
      "older_90d": 1.0
    }
  },
  "impact_analysis": {
    "enabled": true,
    "max_depth": 10,
    "include_indirect": true,
    "show_line_numbers": true
  }
}
EOF

echo "   ✓ Configuration templates created"

# Make scripts executable
chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/uninstall.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/project-index-helper.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/find_python.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/run_python.sh" 2>/dev/null || true

# Save the Python command for later use
echo "$PYTHON_CMD" > "$INSTALL_DIR/.python_cmd"
echo "   ✓ Python command saved: $PYTHON_CMD"

# Create /index command
echo ""
echo "Creating /index command..."
mkdir -p "$HOME/.claude/commands"
cat > "$HOME/.claude/commands/index.md" << 'EOF'
---
name: index
description: Create or update PROJECT_INDEX.json for the current project
---

# PROJECT_INDEX Command

This command creates or updates a PROJECT_INDEX.json file that gives Claude architectural awareness of your codebase.

The indexer script is located at:
`~/.claude-code-project-index/scripts/project_index.py`

## What it does

The PROJECT_INDEX creates a comprehensive map of your project including:
- Directory structure and file organization
- Function and class signatures with type annotations
- Call graphs showing what calls what
- Import dependencies
- Documentation structure
- Directory purposes

## Usage

Simply type `/index` in any project directory to create or update the index.

## About the Tool

**PROJECT_INDEX** is a community tool created by Eric Buess that helps Claude Code understand your project structure better. 

- **GitHub**: https://github.com/ericbuess/claude-code-project-index
- **Purpose**: Prevents code duplication, ensures proper file placement, maintains architectural consistency
- **Philosophy**: Fork and customize for your needs - Claude can modify it instantly

## How to Use the Index

After running `/index`, you can:
1. Reference it directly: `@PROJECT_INDEX.json what functions call authenticate_user?`
2. Use with -i flag: `refactor the auth system -i`
3. Add to CLAUDE.md for auto-loading: `@PROJECT_INDEX.json`

## Implementation

When you run `/index`, Claude will:
1. Check if PROJECT_INDEX is installed at ~/.claude-code-project-index
2. Run the indexer script at ~/.claude-code-project-index/scripts/project_index.py to create/update PROJECT_INDEX.json
3. Provide feedback on what was indexed
4. The index is then available as PROJECT_INDEX.json

## Troubleshooting

If the index is too large for your project, ask Claude:
"The indexer creates too large an index. Please modify it to only index src/ and lib/ directories"

For other issues, the tool is designed to be customized - just describe your problem to Claude!
EOF
echo "✓ Created /index command"

# Update hooks in settings.json
echo ""
echo "Configuring hooks..."

SETTINGS_FILE="$HOME/.claude/settings.json"

# Ensure settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "{}" > "$SETTINGS_FILE"
fi

# Create a backup
cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"

# Update hooks using jq - removes old PROJECT_INDEX hooks and adds new ones
jq '
  # Initialize hooks if not present
  if .hooks == null then .hooks = {} else . end |
  
  # Initialize UserPromptSubmit if not present (for index-aware mode)
  if .hooks.UserPromptSubmit == null then .hooks.UserPromptSubmit = [] else . end |
  
  # Filter out any existing PROJECT_INDEX UserPromptSubmit hooks, then add the new one
  .hooks.UserPromptSubmit = ([.hooks.UserPromptSubmit[] | select(
    all(.hooks[]?.command // ""; 
      contains("i_flag_hook.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("project_index") | not)
  )] + [{
    "hooks": [{
      "type": "command",
      "command": "'"$HOME"'/.claude-code-project-index/scripts/run_python.sh '"$HOME"'/.claude-code-project-index/scripts/i_flag_hook.py",
      "timeout": 20
    }]
  }]) |
  
  # Initialize Stop if not present
  if .hooks.Stop == null then .hooks.Stop = [] else . end |
  
  # Filter out any existing PROJECT_INDEX Stop hooks, then add the new one
  .hooks.Stop = ([.hooks.Stop[] | select(
    all(.hooks[]?.command // ""; 
      contains("stop_hook.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("reindex_if_needed.py") | not) and
    all(.hooks[]?.command // ""; 
      contains("project_index") | not)
  )] + [{
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "'"$HOME"'/.claude-code-project-index/scripts/run_python.sh '"$HOME"'/.claude-code-project-index/scripts/stop_hook.py",
      "timeout": 10
    }]
  }])
' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

echo "✓ Hooks configured in settings.json"

# Test installation
echo ""
echo "Testing installation..."
if $PYTHON_CMD "$INSTALL_DIR/scripts/project_index.py" --version 2>/dev/null | grep -q "PROJECT_INDEX"; then
    echo "✓ Installation test passed"
else
    echo "⚠️  Version check failed, but installation completed"
    echo "   You can still use /index command normally"
fi

# MCP Tool Detection and Configuration (Story 3.5, AC #1-5)
echo ""
echo "=========================================="
echo "🔍 Detecting MCP-compatible tools..."
echo "=========================================="
echo ""

DETECTED_TOOLS=()

if [[ -n "$CONFIGURE_MCP_TOOL" ]]; then
    # Manual configuration mode (AC #5)
    echo "📝 Manual configuration mode: $CONFIGURE_MCP_TOOL"
    DETECTED_TOOLS=("$CONFIGURE_MCP_TOOL")
else
    # Auto-detection mode (AC #1-4)
    if detect_claude_code; then
        DETECTED_TOOLS+=("claude-code")
        echo "✓ Found: Claude Code CLI (~/.config/claude-code/)"
    fi

    if detect_cursor; then
        DETECTED_TOOLS+=("cursor")
        if [[ "$OS_TYPE" == "macos" ]]; then
            echo "✓ Found: Cursor IDE (~/Library/Application Support/Cursor/)"
        else
            echo "✓ Found: Cursor IDE (~/.config/Cursor/)"
        fi
    fi

    if detect_claude_desktop; then
        DETECTED_TOOLS+=("desktop")
        if [[ "$OS_TYPE" == "macos" ]]; then
            echo "✓ Found: Claude Desktop (~/Library/Application Support/Claude/)"
        else
            echo "✓ Found: Claude Desktop (~/.config/Claude/)"
        fi
    fi
fi

if [[ ${#DETECTED_TOOLS[@]} -eq 0 ]]; then
    echo "ℹ️  No MCP-compatible tools detected"
    echo ""
    echo "📝 Manual Configuration:"
    echo "   To configure MCP for a specific tool, run:"
    echo "   ./install.sh --configure-mcp=claude-code"
    echo "   ./install.sh --configure-mcp=cursor"
    echo "   ./install.sh --configure-mcp=desktop"
    echo ""
    echo "   See docs/mcp-setup.md for detailed instructions"
else
    echo ""
    echo "📋 Detected ${#DETECTED_TOOLS[@]} tool(s): ${DETECTED_TOOLS[*]}"
    echo ""

    # Interactive tool selection if multiple tools detected and running interactively
    SELECTED_TOOLS=("${DETECTED_TOOLS[@]}")  # Default: configure all detected tools

    if [[ ${#DETECTED_TOOLS[@]} -gt 1 ]] && [ -t 0 ] && [[ -z "$CONFIGURE_MCP_TOOL" ]]; then
        echo "Would you like to configure MCP for:"
        echo "  [a] All detected tools (recommended)"
        echo "  [s] Select specific tools"
        echo "  [n] Skip MCP configuration"
        read -p "Choice (a/s/n): " -n 1 -r MCP_CHOICE
        echo ""
        echo ""

        case $MCP_CHOICE in
            [Ss])
                SELECTED_TOOLS=()
                for tool in "${DETECTED_TOOLS[@]}"; do
                    read -p "Configure MCP for $tool? (y/N): " -n 1 -r
                    echo ""
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        SELECTED_TOOLS+=("$tool")
                    fi
                done
                ;;
            [Nn])
                SELECTED_TOOLS=()
                echo "Skipping MCP configuration"
                ;;
            *)
                echo "Configuring all detected tools"
                ;;
        esac
    fi

    # Configure selected tools (Story 3.5, AC #1-3, #8)
    if [[ ${#SELECTED_TOOLS[@]} -gt 0 ]]; then
        echo "🔧 Configuring MCP server for selected tools..."
        echo ""

        for tool in "${SELECTED_TOOLS[@]}"; do
            CONFIG_PATH=$(get_mcp_config_path "$tool")
            CONFIG_DIR=$(dirname "$CONFIG_PATH")

            echo "   Configuring $tool..."
            echo "   Config path: $CONFIG_PATH"

            # Create config directory if it doesn't exist
            mkdir -p "$CONFIG_DIR"

            # Backup existing config if it exists (Story 3.4 pattern)
            if [[ -f "$CONFIG_PATH" ]]; then
                BACKUP_PATH="$INSTALL_DIR/backups/mcp-configs"
                mkdir -p "$BACKUP_PATH"
                TIMESTAMP=$(date +%Y%m%d-%H%M%S)
                cp "$CONFIG_PATH" "$BACKUP_PATH/${tool}-mcp-backup-$TIMESTAMP.json"
                echo "   ✓ Backed up existing config to backups/mcp-configs/"
            fi

            # Create or update MCP configuration (non-destructive, AC #8)
            MCP_SERVER_COMMAND="$PYTHON_CMD"
            MCP_SERVER_ARGS="[\"$INSTALL_DIR/project_index_mcp.py\"]"

            if [[ -f "$CONFIG_PATH" ]]; then
                # Update existing config, preserving other servers
                jq --arg cmd "$MCP_SERVER_COMMAND" \
                   --argjson args "$MCP_SERVER_ARGS" \
                   '.mcpServers."project-index" = {"command": $cmd, "args": $args, "env": {}}' \
                   "$CONFIG_PATH" > "${CONFIG_PATH}.tmp" && mv "${CONFIG_PATH}.tmp" "$CONFIG_PATH"
                echo "   ✓ Updated MCP configuration (existing servers preserved)"
            else
                # Create new config file
                cat > "$CONFIG_PATH" << EOF
{
  "mcpServers": {
    "project-index": {
      "command": "$MCP_SERVER_COMMAND",
      "args": $MCP_SERVER_ARGS,
      "env": {}
    }
  }
}
EOF
                echo "   ✓ Created MCP configuration"
            fi
        done

        echo ""
        echo "✅ MCP configuration complete for: ${SELECTED_TOOLS[*]}"
        echo ""
        echo "📝 Next steps:"
        echo "   1. Restart your AI tool(s) to load the MCP server"
        echo "   2. Verify connection: python3 $INSTALL_DIR/scripts/validate_mcp.py --tool=<tool-name>"
        echo "   3. See docs/mcp-setup.md for usage instructions"
    fi
fi

echo ""
echo "=========================================="
echo "✅ PROJECT_INDEX installed successfully!"
echo "=========================================="
echo ""
echo "📁 Installation location: $INSTALL_DIR"
echo ""
echo "📝 Manual cleanup needed:"
echo "   Please remove these old files from ~/.claude/scripts/ if they exist:"
echo "   • project_index.py"
echo "   • update_index.py"
echo "   • reindex_if_needed.py"
echo "   • index_utils.py"
echo "   • detect_external_changes.py"
echo ""
echo "🚀 Usage:"
echo "   • Add -i flag to any prompt for index-aware mode (e.g., 'fix auth bug -i')"
echo "   • Use -ic flag to export to clipboard for large context AI models"
echo "   • Reference with @PROJECT_INDEX.json when you need architectural awareness"
echo "   • The index is created automatically when you use -i flag"
echo ""
echo "📚 For more information, see: $INSTALL_DIR/README.md"