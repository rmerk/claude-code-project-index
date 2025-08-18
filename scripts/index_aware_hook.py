#!/usr/bin/env python3
"""
UserPromptSubmit hook for intelligent PROJECT_INDEX.json analysis.
Detects -i[number] and -ic[number] flags for dynamic index generation.
"""

import json
import sys
import os
import re
import subprocess
import hashlib
import time
from pathlib import Path
from datetime import datetime

# Constants
DEFAULT_SIZE_K = 50  # Default 50k tokens
MIN_SIZE_K = 5       # Minimum 5k tokens
CLAUDE_MAX_K = 100   # Max 100k for Claude (leaves room for reasoning)
EXTERNAL_MAX_K = 800 # Max 800k for external AI

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

def parse_index_flag(prompt):
    """Parse -i or -ic flag with optional size."""
    # Pattern matches -i[number] or -ic[number]
    match = re.search(r'-i(c?)(\d+)?(?:\s|$)', prompt)
    
    if not match:
        return None, None, prompt
    
    clipboard_mode = match.group(1) == 'c'
    size_k = int(match.group(2)) if match.group(2) else DEFAULT_SIZE_K
    
    # Validate size limits
    if size_k < MIN_SIZE_K:
        print(f"⚠️ Minimum size is {MIN_SIZE_K}k, using {MIN_SIZE_K}k", file=sys.stderr)
        size_k = MIN_SIZE_K
    
    if not clipboard_mode and size_k > CLAUDE_MAX_K:
        print(f"⚠️ Claude max is {CLAUDE_MAX_K}k (need buffer for reasoning), using {CLAUDE_MAX_K}k", file=sys.stderr)
        size_k = CLAUDE_MAX_K
    elif clipboard_mode and size_k > EXTERNAL_MAX_K:
        print(f"⚠️ Maximum size is {EXTERNAL_MAX_K}k, using {EXTERNAL_MAX_K}k", file=sys.stderr)
        size_k = EXTERNAL_MAX_K
    
    # Clean prompt (remove flag)
    cleaned_prompt = re.sub(r'-ic?\d*\s*', '', prompt).strip()
    
    return size_k, clipboard_mode, cleaned_prompt

def calculate_files_hash(project_root):
    """Calculate hash of non-ignored files to detect changes."""
    try:
        # Use git ls-files to get non-ignored files
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            # Fallback to manual file discovery
            files = []
            for file_path in project_root.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    files.append(str(file_path.relative_to(project_root)))
        
        # Hash file paths and modification times
        hasher = hashlib.sha256()
        for file_path in sorted(files):
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    mtime = str(full_path.stat().st_mtime)
                    hasher.update(f"{file_path}:{mtime}".encode())
                except:
                    pass
        
        return hasher.hexdigest()[:16]
    except Exception as e:
        print(f"Warning: Could not calculate files hash: {e}", file=sys.stderr)
        return "unknown"

def should_regenerate_index(project_root, index_path, requested_size_k):
    """Determine if index needs regeneration."""
    if not index_path.exists():
        return True, "No index exists"
    
    try:
        # Read metadata
        with open(index_path, 'r') as f:
            index = json.load(f)
            meta = index.get('_meta', {})
        
        # Get last generation info
        last_target = meta.get('target_size_k', 0)
        last_files_hash = meta.get('files_hash', '')
        
        # Check if files changed
        current_files_hash = calculate_files_hash(project_root)
        if current_files_hash != last_files_hash and current_files_hash != "unknown":
            return True, f"Files changed since last index"
        
        # Check if different size requested
        if abs(requested_size_k - last_target) > 2:  # Allow 2k tolerance
            return True, f"Different size requested ({requested_size_k}k vs {last_target}k)"
        
        # Use existing index
        actual_k = meta.get('actual_size_k', last_target)
        return False, f"Using cached index ({actual_k}k actual, {last_target}k target)"
    
    except Exception as e:
        print(f"Warning: Could not read index metadata: {e}", file=sys.stderr)
        return True, "Could not read index metadata"

def generate_index_at_size(project_root, target_size_k):
    """Generate index at specific token size."""
    print(f"🎯 Generating {target_size_k}k token index...", file=sys.stderr)
    
    # Find indexer script
    local_indexer = Path(__file__).parent / 'project_index.py'
    system_indexer = Path.home() / '.claude-code-project-index' / 'scripts' / 'project_index.py'
    
    indexer_path = local_indexer if local_indexer.exists() else system_indexer
    
    if not indexer_path.exists():
        print("⚠️ PROJECT_INDEX.json indexer not found", file=sys.stderr)
        return False
    
    try:
        # Find Python command
        python_cmd_file = Path.home() / '.claude-code-project-index' / '.python_cmd'
        if python_cmd_file.exists():
            python_cmd = python_cmd_file.read_text().strip()
        else:
            python_cmd = sys.executable
        
        # Pass target size as environment variable
        env = os.environ.copy()
        env['INDEX_TARGET_SIZE_K'] = str(target_size_k)
        
        result = subprocess.run(
            [python_cmd, str(indexer_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode == 0:
            # Update metadata with target size and hash
            index_path = project_root / 'PROJECT_INDEX.json'
            if index_path.exists():
                with open(index_path, 'r') as f:
                    index = json.load(f)
                
                # Measure actual size
                index_str = json.dumps(index, indent=2)
                actual_tokens = len(index_str) // 4  # Rough estimate: 4 chars = 1 token
                actual_size_k = actual_tokens // 1000
                
                # Add/update metadata
                if '_meta' not in index:
                    index['_meta'] = {}
                
                index['_meta'].update({
                    'generated_at': time.time(),
                    'target_size_k': target_size_k,
                    'actual_size_k': actual_size_k,
                    'files_hash': calculate_files_hash(project_root),
                    'compression_ratio': f"{(actual_size_k/target_size_k)*100:.1f}%" if target_size_k > 0 else "N/A"
                })
                
                # Save updated index
                with open(index_path, 'w') as f:
                    json.dump(index, f, indent=2)
                
                print(f"✅ Created PROJECT_INDEX.json ({actual_size_k}k actual, {target_size_k}k target)", file=sys.stderr)
                return True
            else:
                print("⚠️ Index file not created", file=sys.stderr)
                return False
        else:
            print(f"⚠️ Failed to create index: {result.stderr}", file=sys.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Index creation timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️ Error creating index: {e}", file=sys.stderr)
        return False

def copy_to_clipboard(prompt, index_path):
    """Copy prompt, instructions, and index to clipboard for external AI."""
    try:
        # Load subagent instructions
        agents_dir = Path(__file__).parent.parent / '.claude' / 'agents'
        if not agents_dir.exists():
            agents_dir = Path.home() / '.claude-code-project-index' / '.claude' / 'agents'
        
        analyzer_path = agents_dir / 'index-analyzer.md'
        if analyzer_path.exists():
            with open(analyzer_path, 'r') as f:
                instructions = f.read()
        else:
            instructions = "Analyze the PROJECT_INDEX.json to identify relevant code sections."
        
        # Load index
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Build clipboard content
        clipboard_content = f"""# Index-Aware Analysis Request

## User Prompt
{prompt}

## Analysis Instructions
{instructions}

## PROJECT_INDEX.json
{json.dumps(index, indent=2)}

## Expected Response Format
Provide code intelligence analysis including:
- Essential code paths and files
- Call graphs and dependencies
- Architectural insights
- Strategic recommendations for the task
"""
        
        # Try to copy to clipboard
        try:
            import pyperclip
            pyperclip.copy(clipboard_content)
            print(f"✅ Copied to clipboard: {len(clipboard_content)} chars", file=sys.stderr)
            print(f"📋 Ready to paste into Gemini, Claude.ai, ChatGPT, or other AI", file=sys.stderr)
        except ImportError:
            # Fallback for systems without pyperclip
            fallback_path = Path.cwd() / '.clipboard_content.txt'
            with open(fallback_path, 'w') as f:
                f.write(clipboard_content)
            print(f"✅ Saved to {fallback_path} (copy manually)", file=sys.stderr)
        
        return True
    except Exception as e:
        print(f"⚠️ Error preparing clipboard content: {e}", file=sys.stderr)
        return False

def main():
    """Process UserPromptSubmit hook for -i and -ic flag detection."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        prompt = input_data.get('prompt', '')
        
        # Parse flag
        size_k, clipboard_mode, cleaned_prompt = parse_index_flag(prompt)
        
        if size_k is None:
            # No index flag, let prompt proceed normally
            sys.exit(0)
        
        # Find project root
        project_root = find_project_root()
        index_path = project_root / 'PROJECT_INDEX.json'
        
        # Check if regeneration needed
        should_regen, reason = should_regenerate_index(project_root, index_path, size_k)
        
        if should_regen:
            print(f"🔄 Regenerating index: {reason}", file=sys.stderr)
            if not generate_index_at_size(project_root, size_k):
                print("⚠️ Proceeding without PROJECT_INDEX.json", file=sys.stderr)
                sys.exit(0)
        else:
            print(f"✅ {reason}", file=sys.stderr)
        
        # Handle clipboard mode
        if clipboard_mode:
            if copy_to_clipboard(cleaned_prompt, index_path):
                # Tell user it's ready, no subagent needed
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": f"""
📋 Clipboard Mode Activated

Index and instructions copied to clipboard ({size_k}k tokens).
Paste into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

No subagent will be invoked - the clipboard contains everything needed.
Original request: {cleaned_prompt}
"""
                    }
                }
            else:
                sys.exit(0)
        else:
            # Standard mode - prepare for subagent
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"""
## 🎯 Index-Aware Mode Activated

Generated/loaded {size_k}k token index.

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
"""
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