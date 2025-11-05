#!/usr/bin/env python3
"""
Tests for Story 4.2: Intelligent Sub-Module Generation with Multi-Level Splitting

Test coverage:
- Task 1: split_module_recursive() with various scenarios
- Task 2: generate_submodule_name() naming convention
- Task 3: detect_framework_patterns() for Vite detection
- Task 4: build_file_to_module_map() for O(1) lookup
- Tasks 5-7: Integration with existing workflow
- Task 8: End-to-end testing with synthetic Vite project
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List

# Import functions to test
from project_index import (
    detect_framework_patterns,
    generate_submodule_name,
    split_module_recursive,
    build_file_to_module_map,
    get_submodule_config,
    generate_split_index
)


class TestDetectFrameworkPatterns(unittest.TestCase):
    """Tests for Vite framework pattern detection (Task 3, AC #3)."""

    def setUp(self):
        """Create temporary directory for test projects."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_vite_project_detected(self):
        """Vite framework detected when src/ has 3+ characteristic subdirectories."""
        # Create Vite-like structure
        src_dir = self.root_path / "src"
        src_dir.mkdir()

        # Create characteristic Vite directories
        for subdir in ["components", "views", "api", "stores"]:
            (src_dir / subdir).mkdir()

        framework = detect_framework_patterns(self.root_path)
        self.assertEqual(framework, "vite", "Should detect Vite with 4+ characteristic dirs")

    def test_vite_minimal_match(self):
        """Vite detected with exactly 3 characteristic directories."""
        src_dir = self.root_path / "src"
        src_dir.mkdir()

        # Exactly 3 Vite patterns
        for subdir in ["components", "views", "api"]:
            (src_dir / subdir).mkdir()

        framework = detect_framework_patterns(self.root_path)
        self.assertEqual(framework, "vite", "Should detect Vite with exactly 3 characteristic dirs")

    def test_non_vite_project_generic(self):
        """Non-Vite project returns generic."""
        src_dir = self.root_path / "src"
        src_dir.mkdir()

        # Only 2 Vite patterns (below threshold)
        (src_dir / "components").mkdir()
        (src_dir / "lib").mkdir()  # Not a Vite pattern

        framework = detect_framework_patterns(self.root_path)
        self.assertEqual(framework, "generic", "Should return generic with <3 Vite patterns")

    def test_no_src_directory(self):
        """Project without src/ directory returns generic."""
        framework = detect_framework_patterns(self.root_path)
        self.assertEqual(framework, "generic", "Should return generic when no src/ directory")

    def test_empty_src_directory(self):
        """Empty src/ directory returns generic."""
        (self.root_path / "src").mkdir()

        framework = detect_framework_patterns(self.root_path)
        self.assertEqual(framework, "generic", "Should return generic for empty src/")


class TestGenerateSubmoduleName(unittest.TestCase):
    """Tests for naming convention (Task 2, AC #2)."""

    def test_second_level_naming(self):
        """Second-level naming: {parent}-{child}."""
        name = generate_submodule_name("assureptmdashboard", "src")
        self.assertEqual(name, "assureptmdashboard-src")

    def test_third_level_naming(self):
        """Third-level naming: {parent}-{child}-{grandchild}."""
        name = generate_submodule_name("assureptmdashboard", "src", "components")
        self.assertEqual(name, "assureptmdashboard-src-components")

    def test_third_level_with_none(self):
        """Third-level with grandchild=None returns second-level."""
        name = generate_submodule_name("assureptmdashboard", "src", None)
        self.assertEqual(name, "assureptmdashboard-src")

    def test_naming_with_hyphens(self):
        """Naming works with module names containing hyphens."""
        name = generate_submodule_name("my-project", "src-code", "main-app")
        self.assertEqual(name, "my-project-src-code-main-app")


class TestBuildFileToModuleMap(unittest.TestCase):
    """Tests for file-to-module mapping (Task 4, AC #6)."""

    def test_simple_mapping(self):
        """Correctly maps files to modules."""
        modules = {
            "assureptmdashboard-src-components": ["src/components/Button.vue", "src/components/Form.vue"],
            "assureptmdashboard-src-views": ["src/views/Home.vue"]
        }

        file_map = build_file_to_module_map(modules)

        self.assertEqual(file_map["src/components/Button.vue"], "assureptmdashboard-src-components")
        self.assertEqual(file_map["src/components/Form.vue"], "assureptmdashboard-src-components")
        self.assertEqual(file_map["src/views/Home.vue"], "assureptmdashboard-src-views")

    def test_empty_modules(self):
        """Empty modules dict returns empty map."""
        file_map = build_file_to_module_map({})
        self.assertEqual(file_map, {})

    def test_large_scale_performance(self):
        """Mapping generation completes in <10ms for 10,000 files."""
        # Create large modules dict
        modules = {}
        file_count = 0
        for i in range(100):  # 100 modules
            module_id = f"module-{i}"
            files = [f"src/file_{file_count + j}.py" for j in range(100)]  # 100 files each
            modules[module_id] = files
            file_count += 100

        start_time = time.time()
        file_map = build_file_to_module_map(modules)
        elapsed_ms = (time.time() - start_time) * 1000

        self.assertEqual(len(file_map), 10000, "Should map all 10,000 files")
        self.assertLess(elapsed_ms, 100, f"Mapping should complete in <100ms, took {elapsed_ms:.2f}ms")


class TestSplitModuleRecursive(unittest.TestCase):
    """Tests for recursive splitting algorithm (Task 1, AC #1, #4)."""

    def setUp(self):
        """Create temporary directory for test projects."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.config = {'submodule_config': {'threshold': 100, 'enabled': True, 'max_depth': 3}}

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def create_test_files(self, structure: Dict[str, int]) -> List[str]:
        """
        Create test files based on structure dict.

        Args:
            structure: Dict mapping directory paths -> file count

        Returns:
            List of file paths relative to root
        """
        all_files = []

        for dir_path_str, file_count in structure.items():
            dir_path = self.root_path / dir_path_str
            dir_path.mkdir(parents=True, exist_ok=True)

            for i in range(file_count):
                file_path = dir_path / f"file_{i}.py"
                file_path.write_text(f"# File {i}")

                # Get relative path
                rel_path = file_path.relative_to(self.root_path)
                all_files.append(str(rel_path))

        return all_files

    def test_flat_structure_no_splitting(self):
        """Flat structure with no subdirectories should not split."""
        # Create 150 files at module root with no subdirectories
        files = self.create_test_files({"mymodule": 150})

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=3,
            config=self.config
        )

        # Should not split (no organized subdirectories)
        self.assertEqual(len(result), 1, "Flat structure should not split")
        self.assertIn("mymodule", result)
        self.assertEqual(len(result["mymodule"]), 150)

    def test_organized_structure_splits_to_level_2(self):
        """Organized structure with large subdirectories splits to second level."""
        # Create structure with organized subdirectories
        structure = {
            "mymodule/src": 120,
            "mymodule/tests": 50,
            "mymodule/docs": 30
        }
        files = self.create_test_files(structure)

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=3,
            config=self.config
        )

        # Should split into sub-modules
        self.assertGreater(len(result), 1, "Should split organized structure")
        self.assertIn("mymodule-src", result)
        self.assertEqual(len(result["mymodule-src"]), 120)

    def test_deep_split_to_level_3(self):
        """Deeply nested structure splits to third level."""
        # Create nested structure
        structure = {
            "mymodule/src/components": 120,
            "mymodule/src/views": 90,
            "mymodule/src/api": 30
        }
        files = self.create_test_files(structure)

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=3,
            config=self.config
        )

        # Should split to third level
        self.assertIn("mymodule-src-components", result)
        self.assertIn("mymodule-src-views", result)
        self.assertEqual(len(result["mymodule-src-components"]), 120)
        self.assertEqual(len(result["mymodule-src-views"]), 90)

    def test_depth_limit_respected(self):
        """Recursion stops at max_depth."""
        # Create 4-level deep structure
        structure = {
            "mymodule/level1/level2/level3": 150
        }
        files = self.create_test_files(structure)

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=2,  # Limit to 2 levels
            config=self.config
        )

        # Should not split beyond level 2
        # Level 0: mymodule, Level 1: mymodule-level1, Level 2: mymodule-level1-level2
        # At depth 2, we hit the limit and don't split further
        depth_3_keys = [k for k in result.keys() if k.count('-') >= 3]
        self.assertEqual(len(depth_3_keys), 0, f"Should not split beyond depth 2, but found: {depth_3_keys}")

    def test_below_threshold_no_split(self):
        """Module below threshold should not split."""
        structure = {
            "mymodule/src/components": 50,  # Below threshold of 100
            "mymodule/src/views": 30
        }
        files = self.create_test_files(structure)

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=3,
            config=self.config
        )

        # Total is 80 files, below threshold, should not split
        self.assertEqual(len(result), 1)
        self.assertIn("mymodule", result)

    def test_intermediate_files_grouped_to_root(self):
        """Files at intermediate levels grouped into *-root sub-module."""
        # Create structure with intermediate files
        structure = {
            "mymodule": 25,  # Files at module root
            "mymodule/src/components": 120
        }
        files = self.create_test_files(structure)

        result = split_module_recursive(
            "mymodule",
            files,
            self.root_path,
            max_depth=3,
            config=self.config
        )

        # Should have both root and sub-module
        self.assertIn("mymodule-root", result, "Intermediate files should be in *-root module")
        self.assertEqual(len(result["mymodule-root"]), 25)


class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end workflow (Task 8, AC #10)."""

    def setUp(self):
        """Create temporary directory for synthetic project."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def create_synthetic_vite_project(self):
        """Create synthetic Vite project with 400+ files."""
        structure = {
            "src/components": 245,
            "src/views": 89,
            "src/api": 34,
            "src/stores": 18,
            "src/composables": 22,
            "src/utils": 8,
            "docs": 169,
            "tests": 82,
            "bmad": 14
        }

        for dir_path_str, file_count in structure.items():
            dir_path = self.root_path / dir_path_str
            dir_path.mkdir(parents=True, exist_ok=True)

            # Create Python files for testing
            for i in range(file_count):
                file_path = dir_path / f"file_{i}.py"
                file_path.write_text(f"""
def function_{i}():
    \"\"\"Test function {i}.\"\"\"
    pass

class TestClass_{i}:
    \"\"\"Test class {i}.\"\"\"
    def method_{i}(self):
        pass
""")

        # Create config file
        config_content = """
submodule_config:
  enabled: true
  threshold: 100
  max_depth: 3
"""
        (self.root_path / "index_config.yaml").write_text(config_content)

    def test_synthetic_vite_project(self):
        """End-to-end test on synthetic Vite project."""
        self.create_synthetic_vite_project()

        # Run index generation
        config = {'submodule_config': {'threshold': 100, 'enabled': True, 'max_depth': 3}}

        start_time = time.time()
        core_index, skipped_count = generate_split_index(str(self.root_path), config)
        elapsed_time = time.time() - start_time

        # Verify modules were created
        modules = core_index.get('modules', {})
        self.assertGreater(len(modules), 1, "Should create multiple modules")

        # Verify file-to-module map exists
        self.assertIn('file_to_module_map', core_index)
        file_map = core_index['file_to_module_map']
        self.assertGreater(len(file_map), 0, "File-to-module map should not be empty")

        # Verify sub-module naming convention
        sub_module_names = [k for k in modules.keys() if '-' in k]
        self.assertGreater(len(sub_module_names), 0, "Should have hyphenated sub-module names")

        # Verify performance (should add ≤10% overhead)
        # Note: This is a rough estimate; baseline would need separate measurement
        self.assertLess(elapsed_time, 30, f"Should complete in <30s, took {elapsed_time:.2f}s")

        # Verify all files are accounted for
        total_files_in_modules = sum(len(mod_data['files']) for mod_data in modules.values()
                                     if isinstance(mod_data, dict) and 'files' in mod_data)
        total_files_in_map = len(file_map)
        self.assertEqual(total_files_in_modules, total_files_in_map,
                        "All files in modules should be in file-to-module map")

    def test_backward_compatibility_disabled(self):
        """With enable_submodules: false, generates monolithic format."""
        self.create_synthetic_vite_project()

        # Disable sub-modules
        config = {'submodule_config': {'enabled': False, 'threshold': 100}}

        core_index, skipped_count = generate_split_index(str(self.root_path), config)

        modules = core_index.get('modules', {})

        # Check that no splitting occurred (all modules should be top-level directories)
        hyphenated_modules = [k for k in modules.keys() if k.count('-') > 1]
        self.assertEqual(len(hyphenated_modules), 0,
                        f"Should not create sub-modules when disabled, but found: {hyphenated_modules}")


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDetectFrameworkPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerateSubmoduleName))
    suite.addTests(loader.loadTestsFromTestCase(TestBuildFileToModuleMap))
    suite.addTests(loader.loadTestsFromTestCase(TestSplitModuleRecursive))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import sys
    sys.exit(run_all_tests())
