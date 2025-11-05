#!/usr/bin/env python3
"""
Manual test for large module detection.
Creates a synthetic project with large modules and verifies detection works.
"""

import json
import shutil
import tempfile
from pathlib import Path

def create_synthetic_project():
    """Create a synthetic project with one large module."""
    test_dir = tempfile.mkdtemp(prefix="large_module_test_")
    root = Path(test_dir)

    print(f"Creating synthetic project in: {root}")

    # Create a large module (src/ with 150 files)
    src_dir = root / "src"
    src_dir.mkdir()
    for i in range(150):
        (src_dir / f"file_{i}.py").write_text(f"# Source file {i}\ndef function_{i}():\n    pass\n")

    # Create subdirectories in src/ for logical grouping analysis
    (src_dir / "components").mkdir()
    for i in range(30):
        (src_dir / "components" / f"Component{i}.py").write_text(f"# Component {i}")

    (src_dir / "api").mkdir()
    for i in range(20):
        (src_dir / "api" / f"endpoint{i}.py").write_text(f"# API endpoint {i}")

    # Create a medium module (tests/ with 80 files)
    tests_dir = root / "tests"
    tests_dir.mkdir()
    for i in range(80):
        (tests_dir / f"test_{i}.py").write_text(f"# Test file {i}\ndef test_function_{i}():\n    assert True\n")

    # Create a small module (docs/ with 15 files)
    docs_dir = root / "docs"
    docs_dir.mkdir()
    for i in range(15):
        (docs_dir / f"doc_{i}.md").write_text(f"# Documentation {i}")

    # Create configuration to enable sub-module detection
    config_path = root / ".project-index.json"
    config = {
        "mode": "split",
        "submodule_config": {
            "enabled": True,
            "threshold": 100
        }
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    return root


def run_test():
    """Run the test."""
    import sys
    import os

    # Create synthetic project
    root = create_synthetic_project()

    try:
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(root)

        # Run project_index with verbose flag
        print("\n" + "="*60)
        print("Running project_index.py with --verbose --full")
        print("="*60 + "\n")

        import subprocess
        result = subprocess.run(
            [sys.executable, original_cwd + "/scripts/project_index.py", "--verbose", "--full"],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Check for expected output
        print("\n" + "="*60)
        print("Test Results")
        print("="*60)

        success = True

        if "Large module detected: src" not in result.stdout and "Large module detected: src" not in result.stderr:
            print("❌ FAIL: Did not detect 'src' as large module")
            success = False
        else:
            print("✅ PASS: Detected 'src' as large module")

        if ("large module(s)" in result.stdout.lower() or "large module(s)" in result.stderr.lower()):
            print("✅ PASS: Large module detection ran")
        else:
            print("❌ FAIL: Large module detection did not run")
            success = False

        # Check that small modules were not flagged
        if "Large module detected: docs" in result.stdout or "Large module detected: docs" in result.stderr:
            print("❌ FAIL: Incorrectly flagged 'docs' as large (should be skipped)")
            success = False
        else:
            print("✅ PASS: Small module 'docs' was not flagged")

        # Check index was generated
        if (root / "PROJECT_INDEX.json").exists():
            print("✅ PASS: PROJECT_INDEX.json generated")
        else:
            print("❌ FAIL: PROJECT_INDEX.json not generated")
            success = False

        print("\n" + "="*60)
        if success:
            print("✅ All tests PASSED!")
        else:
            print("❌ Some tests FAILED")
        print("="*60)

        return success

    finally:
        # Cleanup
        os.chdir(original_cwd)
        shutil.rmtree(root, ignore_errors=True)
        print(f"\nCleaned up test directory: {root}")


if __name__ == "__main__":
    import sys
    success = run_test()
    sys.exit(0 if success else 1)
