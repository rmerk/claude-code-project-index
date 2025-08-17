#!/usr/bin/env python3
"""
UserPromptSubmit hook for intelligent PROJECT_INDEX.json analysis.
Detects -i flag and orchestrates code intelligence analysis.
"""

import json
import sys
import os
import re
import subprocess
from pathlib import Path

def find_project_root():
    """Find project root by looking for .git or common project markers."""
    current = Path.cwd()
    
    # First check current directory for project markers
    if (current / '.git').exists():
        return current
    
    # Check for other project markers
    project_markers = ['package.json', 'pyproject.toml', 'setup.py', 'Cargo.toml', 'go.mod']
    for marker in project_markers:
        if (current / marker).exists():
            return current
        
    # Search up the tree for .git
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
            
    # Default to current directory
    return current

def create_index_if_missing(project_root):
    """Create PROJECT_INDEX.json if it doesn't exist."""
    index_path = project_root / 'PROJECT_INDEX.json'
    
    if index_path.exists():
        return True
        
    print(f"📍 PROJECT_INDEX.json not found. Creating index for: {project_root}", file=sys.stderr)
    
    # Try to find and run project_index.py
    # First check for local development version
    local_indexer = Path(__file__).parent / 'project_index.py'
    # Then check system installation
    system_indexer = Path.home() / '.claude-code-project-index' / 'scripts' / 'project_index.py'
    
    print(f"   Looking for indexer at: {local_indexer}", file=sys.stderr)
    print(f"   Local exists: {local_indexer.exists()}", file=sys.stderr)
    print(f"   System path: {system_indexer}", file=sys.stderr)
    print(f"   System exists: {system_indexer.exists()}", file=sys.stderr)
    
    indexer_path = None
    if local_indexer.exists():
        indexer_path = local_indexer
        print(f"   Using local indexer: {indexer_path}", file=sys.stderr)
    elif system_indexer.exists():
        indexer_path = system_indexer
        print(f"   Using system indexer: {indexer_path}", file=sys.stderr)
    
    if indexer_path:
        try:
            # Find Python command
            python_cmd_file = Path.home() / '.claude-code-project-index' / '.python_cmd'
            if python_cmd_file.exists():
                python_cmd = python_cmd_file.read_text().strip()
            else:
                python_cmd = sys.executable
                
            result = subprocess.run(
                [python_cmd, str(indexer_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ PROJECT_INDEX.json created successfully", file=sys.stderr)
                return True
            else:
                print(f"⚠️ Failed to create index: {result.stderr}", file=sys.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Index creation timed out", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠️ Error creating index: {e}", file=sys.stderr)
            return False
    else:
        print("⚠️ PROJECT_INDEX.json indexer not found. Install from: https://github.com/ericbuess/claude-code-project-index", file=sys.stderr)
        return False

def check_index_staleness(index_path):
    """Check if index is stale and suggest reindex."""
    try:
        import datetime
        
        # Check file modification time
        mtime = os.path.getmtime(index_path)
        age_days = (datetime.datetime.now().timestamp() - mtime) / 86400
        
        if age_days > 7:
            return f"📝 Note: PROJECT_INDEX.json is {int(age_days)} days old. Consider running /index to refresh it."
    except:
        pass
    
    return None

def main():
    """Process UserPromptSubmit hook for -i flag detection."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        prompt = input_data.get('prompt', '')
        
        # Check for -i flag using various patterns
        # Patterns: standalone -i, -i at end, -i in middle
        i_flag_patterns = [
            r'(?:^|\s)-i(?:\s|$)',  # -i with word boundaries
            r'--index(?:\s|$)',      # Long form --index
            r'-i\s*$'                 # -i at the very end
        ]
        
        has_i_flag = any(re.search(pattern, prompt) for pattern in i_flag_patterns)
        
        if not has_i_flag:
            # No -i flag, let prompt proceed normally
            sys.exit(0)
            
        # Found -i flag - process it
        print("🔍 Index-aware mode activated (-i flag detected)", file=sys.stderr)
        
        # Strip -i flag from prompt
        cleaned_prompt = prompt
        for pattern in i_flag_patterns:
            cleaned_prompt = re.sub(pattern, ' ', cleaned_prompt)
        cleaned_prompt = ' '.join(cleaned_prompt.split())  # Clean up whitespace
        
        # Find project root and check/create index
        project_root = find_project_root()
        index_path = project_root / 'PROJECT_INDEX.json'
        
        # Create index if missing
        if not index_path.exists():
            if not create_index_if_missing(project_root):
                # Failed to create index, but don't block the prompt
                print("⚠️ Proceeding without PROJECT_INDEX.json", file=sys.stderr)
                sys.exit(0)
        
        # Check staleness
        staleness_msg = check_index_staleness(index_path)
        if staleness_msg:
            print(staleness_msg, file=sys.stderr)
        
        # Build the context to add
        context_parts = []
        
        # Add instruction to use the index-analyzer subagent
        context_parts.append(f"""
## 🎯 Index-Aware Mode Activated

The user has requested index-aware analysis with the -i flag.

**IMPORTANT**: You MUST use the index-analyzer subagent to analyze the codebase structure before proceeding with the request.

Use it like this:
"I'll analyze the codebase structure to understand the relevant code sections for your request."

Then explicitly invoke: "Using the index-analyzer subagent to analyze PROJECT_INDEX.json..."

The subagent will provide deep code intelligence including:
- Essential code paths and dependencies
- Call graphs and impact analysis
- Architectural insights and patterns
- Strategic recommendations

Original request (without -i flag): {cleaned_prompt}

PROJECT_INDEX.json location: {index_path}
""")
        
        # Return the additional context
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": '\n'.join(context_parts)
            }
        }
        
        print(json.dumps(output))
        sys.exit(0)
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()