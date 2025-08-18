# Index-Aware Mode for Claude Code

## Overview

Index-Aware Mode is an intelligent code analysis system that enhances Claude Code with deep architectural understanding of your codebase. By adding the `-i` flag to any prompt, you activate a specialized subagent that uses ultrathinking to analyze your project's structure, dependencies, and relationships.

## Quick Start

1. **Installation**: The feature is automatically installed with PROJECT_INDEX
2. **Usage**: Add `-i` with optional size to any prompt:
   ```
   # Standard mode (for Claude)
   Fix the parser performance issues -i       # Default 50k tokens
   Add error handling to API calls -i75       # 75k tokens
   What functions are never called? -i100     # 100k tokens (Claude max)
   
   # Clipboard mode (for external AI like Gemini, ChatGPT)
   Redesign the architecture -ic400           # 400k tokens, copy to clipboard
   Analyze entire codebase -ic800             # 800k tokens, copy to clipboard
   ```

## How It Works

### System Architecture

```
User Prompt with -i flag
    ↓
UserPromptSubmit Hook (detects flag)
    ↓
Creates/Updates PROJECT_INDEX.json if needed
    ↓
Instructs main agent to use index-analyzer
    ↓
Index-Analyzer Subagent (ultrathinking)
    ↓
Deep code intelligence analysis
    ↓
Strategic recommendations to main agent
```

### Components

#### 1. UserPromptSubmit Hook (`scripts/index_aware_hook.py`)
- Detects `-i[number]` and `-ic[number]` flags in user prompts
- Dynamically generates index at requested size (5k-800k tokens)
- Smart regeneration: only rebuilds when files change or size differs
- Clipboard mode: copies everything for external AI models
- Auto-creates PROJECT_INDEX.json if missing
- Uses git ls-files for efficient file discovery

#### 2. Index-Analyzer Subagent (`.claude/agents/index-analyzer.md`)
- Uses ultrathinking for deep code analysis
- Reads and analyzes PROJECT_INDEX.json
- Understands call graphs and dependencies
- Provides strategic code intelligence

#### 3. Hook Configuration (`.claude/settings.json`)
- Configures UserPromptSubmit hook
- Sets 20-second timeout for index operations
- Enables automatic PROJECT_INDEX.json creation

## Features

### Dynamic Index Sizing
- **Flexible sizes**: Generate indexes from 5k to 800k tokens
- **Smart defaults**: 50k tokens if no size specified
- **Claude limit**: Automatically caps at 100k for Claude (leaves room for reasoning)
- **External AI support**: Up to 800k for Gemini, ChatGPT, Claude.ai

### Smart Caching & Regeneration
- **File change detection**: Uses git ls-files and file hashes
- **Size-aware**: Only regenerates if requested size differs
- **Metadata tracking**: Stores target vs actual size, compression ratio
- **Performance**: Caches index to avoid unnecessary rebuilds

### Clipboard Mode (`-ic`)
Perfect for leveraging AI models with larger context windows:
- **Automatic copying**: Index + instructions + prompt to clipboard
- **External AI ready**: Paste into Gemini (1M context), ChatGPT, Claude.ai
- **Fallback support**: Saves to file if clipboard unavailable
- **No subagent needed**: Everything copied for external processing

### Automatic Index Creation
If PROJECT_INDEX.json doesn't exist when you use `-i`, the system automatically creates it by:
1. Detecting project root (looks for .git or project markers)
2. Running the PROJECT_INDEX indexer
3. Creating comprehensive code analysis

### Intelligent Code Analysis
The index-analyzer subagent provides:
- **Call Graph Analysis**: Traces execution paths using `calls` and `called_by` fields
- **Dependency Mapping**: Understands import relationships and module coupling
- **Impact Analysis**: Identifies what breaks if code changes
- **Dead Code Detection**: Finds functions with no callers
- **Pattern Recognition**: Identifies architectural patterns and conventions

### Strategic Recommendations
For each request, the subagent provides:
- Essential files to read first
- Complete call chains to understand
- Safe modification points
- Refactoring opportunities
- Testing requirements

## Usage Examples

### Performance Optimization
```
User: Make the indexing faster -i

Subagent analyzes:
- Current performance bottlenecks
- Redundant operations
- I/O patterns
- Caching opportunities
```

### Feature Development
```
User: Add support for Ruby files -i

Subagent identifies:
- Current parser architecture
- Pattern for adding languages
- Where parsers live
- Integration points
```

### Debugging
```
User: Why does the hook fail? -i

Subagent traces:
- Execution path
- Error handling
- Logging points
- Failure modes
```

### Code Cleanup
```
User: Find all dead code -i

Subagent finds:
- Functions with no callers
- Unused imports
- Redundant code
- Safe removal candidates
```

## Testing

The system includes comprehensive tests:

### Test Files
- `test_hook.py` - Tests -i flag detection in various positions
- `test_auto_create.py` - Tests automatic PROJECT_INDEX.json creation
- `test_subagent.py` - Tests subagent configuration and integration
- `test_error_handling.py` - Tests error cases and edge conditions

### Running Tests
```bash
# Test -i flag detection
python3 test_hook.py

# Test auto-creation
python3 test_auto_create.py

# Test subagent
python3 test_subagent.py

# Test error handling
python3 test_error_handling.py

# Quick validation
./test_index_creation.sh
```

## Configuration

### Customizing the Subagent
Edit `.claude/agents/index-analyzer.md` to:
- Adjust ultrathinking focus areas
- Modify output format
- Add domain-specific analysis
- Change tool permissions

### Adjusting Hook Behavior
Edit `scripts/index_aware_hook.py` to:
- Change flag pattern (default: `-i` or `--index`)
- Modify timeout values
- Customize error messages
- Add additional checks

### Settings Configuration
Edit `.claude/settings.json` to:
- Change hook timeout (default: 20 seconds)
- Add additional hooks
- Modify hook ordering

## Benefits

### Speed & Efficiency
- **90% fewer search commands** - Direct navigation to relevant code
- **Instant analysis** - No blind searching through files
- **Automatic indexing** - PROJECT_INDEX.json created on demand

### Intelligence & Accuracy
- **Deep understanding** - Ultrathinking provides insights algorithms can't
- **Contextual awareness** - Understands intent, not just keywords
- **Relationship mapping** - Sees connections between code sections

### Safety & Reliability
- **Impact analysis** - Know what breaks before changing
- **Pattern consistency** - Maintain architectural integrity
- **Dead code detection** - Clean up with confidence

## Troubleshooting

### -i Flag Not Detected
- Check hook is configured: `/hooks` command
- Verify settings.json exists in `.claude/`
- Ensure hook script is executable

### PROJECT_INDEX.json Not Created
- Verify indexer is installed
- Check Python is available
- Ensure write permissions in project directory

### Subagent Not Invoked
- Check subagent exists in `.claude/agents/`
- Verify hook adds proper context
- Ensure main agent sees the instruction

## Architecture Details

### Flag Detection Patterns
The hook detects these patterns:
- `-i` with word boundaries
- `--index` long form
- Flag at beginning, middle, or end of prompt

### Project Root Detection
Searches for these markers:
1. `.git` directory
2. `package.json`, `pyproject.toml`, `setup.py`
3. `Cargo.toml`, `go.mod`
4. Falls back to current directory

### Index Creation Process
1. Finds Python command (saved or system)
2. Locates project_index.py script
3. Runs indexer with 30-second timeout
4. Verifies JSON creation

## Future Enhancements

Potential improvements:
- Cache index for faster repeated queries
- Add more language parsers
- Support for monorepos
- Custom ranking algorithms
- Visual dependency graphs

## Contributing

To enhance this feature:
1. Fork the repository
2. Modify the subagent or hook
3. Add tests for new functionality
4. Submit improvements back to community

## License

Part of the PROJECT_INDEX tool under MIT License