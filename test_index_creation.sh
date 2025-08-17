#!/bin/bash

echo "================================================"
echo "TESTING PROJECT_INDEX.json CREATION"
echo "================================================"

# Create a temp directory for testing
TEMP_DIR=$(mktemp -d)
echo "Created temp directory: $TEMP_DIR"

# Create test files
echo "def main(): pass" > "$TEMP_DIR/test.py"
echo "# Test Project" > "$TEMP_DIR/README.md"
mkdir -p "$TEMP_DIR/.git"

echo "Created test files in $TEMP_DIR"

# Change to temp directory
cd "$TEMP_DIR"

# Run the hook with -i flag
echo ""
echo "Running hook with -i flag from $TEMP_DIR..."
echo ""

# Prepare JSON input for the hook
JSON_INPUT=$(cat <<EOF
{
  "session_id": "test-session",
  "transcript_path": "/tmp/test.jsonl",
  "cwd": "$TEMP_DIR",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Analyze the code -i"
}
EOF
)

# Run the hook
echo "$JSON_INPUT" | python3 /home/ericbuess/Projects/claude-code-project-index/scripts/index_aware_hook.py

echo ""
echo "Checking if PROJECT_INDEX.json was created..."
if [ -f "$TEMP_DIR/PROJECT_INDEX.json" ]; then
    echo "✅ PROJECT_INDEX.json was created!"
    echo "Contents preview:"
    head -20 "$TEMP_DIR/PROJECT_INDEX.json"
else
    echo "❌ PROJECT_INDEX.json was not created"
fi

# Cleanup
rm -rf "$TEMP_DIR"
echo ""
echo "Cleaned up temp directory"