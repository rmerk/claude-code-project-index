"""
Unit tests for large module detection and analysis (Story 4.1).

Tests cover:
- File counting accuracy
- Configuration loading and validation
- Large module detection
- Directory structure analysis
- Short-circuit logic for small modules
- Logging and observability
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch, MagicMock

# Import functions to test
from project_index import (
    load_configuration,
    get_submodule_config,
    detect_large_modules,
    analyze_directory_structure,
    organize_into_modules
)


class TestLoadConfigurationSubmodule(unittest.TestCase):
    """Test configuration loading for submodule_config section."""

    def setUp(self):
        """Create temp directory for test configs."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up temp directory."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_valid_submodule_config(self):
        """Test loading valid submodule_config section."""
        config_path = Path(self.test_dir) / ".project-index.json"
        config_data = {
            "mode": "split",
            "submodule_config": {
                "enabled": True,
                "threshold": 150,
                "strategy": "auto",
                "max_depth": 2
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_configuration(config_path)

        self.assertIn('submodule_config', config)
        self.assertEqual(config['submodule_config']['enabled'], True)
        self.assertEqual(config['submodule_config']['threshold'], 150)
        self.assertEqual(config['submodule_config']['strategy'], 'auto')
        self.assertEqual(config['submodule_config']['max_depth'], 2)

    def test_invalid_enabled_flag(self):
        """Test invalid enabled flag defaults to True."""
        config_path = Path(self.test_dir) / ".project-index.json"
        config_data = {
            "submodule_config": {
                "enabled": "yes"  # Invalid: should be boolean
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_configuration(config_path)

        # Should default to True after validation
        self.assertEqual(config['submodule_config']['enabled'], True)

    def test_invalid_threshold(self):
        """Test invalid threshold defaults to 100."""
        config_path = Path(self.test_dir) / ".project-index.json"
        config_data = {
            "submodule_config": {
                "threshold": -50  # Invalid: must be positive
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_configuration(config_path)

        # Should default to 100 after validation
        self.assertEqual(config['submodule_config']['threshold'], 100)

    def test_invalid_strategy(self):
        """Test invalid strategy defaults to 'auto'."""
        config_path = Path(self.test_dir) / ".project-index.json"
        config_data = {
            "submodule_config": {
                "strategy": "invalid_strategy"
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_configuration(config_path)

        # Should default to 'auto' after validation
        self.assertEqual(config['submodule_config']['strategy'], 'auto')

    def test_invalid_max_depth(self):
        """Test invalid max_depth defaults to 3."""
        config_path = Path(self.test_dir) / ".project-index.json"
        config_data = {
            "submodule_config": {
                "max_depth": 5  # Invalid: must be 1-3
            }
        }
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        config = load_configuration(config_path)

        # Should default to 3 after validation
        self.assertEqual(config['submodule_config']['max_depth'], 3)


class TestGetSubmoduleConfig(unittest.TestCase):
    """Test get_submodule_config function with defaults."""

    def test_defaults_when_no_config(self):
        """Test defaults are applied when config is None."""
        config = get_submodule_config(None)

        self.assertEqual(config['enabled'], True)
        self.assertEqual(config['threshold'], 100)
        self.assertEqual(config['strategy'], 'auto')
        self.assertEqual(config['max_depth'], 3)

    def test_defaults_when_missing_submodule_config(self):
        """Test defaults are applied when submodule_config missing."""
        config = get_submodule_config({'mode': 'split'})

        self.assertEqual(config['enabled'], True)
        self.assertEqual(config['threshold'], 100)
        self.assertEqual(config['strategy'], 'auto')
        self.assertEqual(config['max_depth'], 3)

    def test_partial_config_applies_defaults(self):
        """Test partial config gets defaults for missing keys."""
        input_config = {
            'submodule_config': {
                'threshold': 200
                # enabled, strategy, max_depth missing
            }
        }

        config = get_submodule_config(input_config)

        self.assertEqual(config['enabled'], True)  # Default
        self.assertEqual(config['threshold'], 200)  # From config
        self.assertEqual(config['strategy'], 'auto')  # Default
        self.assertEqual(config['max_depth'], 3)  # Default


class TestDetectLargeModules(unittest.TestCase):
    """Test large module detection logic."""

    def setUp(self):
        """Create temp directory for test projects."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detect_single_large_module(self):
        """Test detection of a single large module."""
        # Create module with 150 files (exceeds threshold of 100)
        modules = {
            'scripts': [f'scripts/file_{i}.py' for i in range(150)],
            'docs': ['docs/README.md']
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        self.assertEqual(len(large_modules), 1)
        self.assertEqual(large_modules[0]['module_id'], 'scripts')
        self.assertEqual(large_modules[0]['file_count'], 150)

    def test_detect_multiple_large_modules(self):
        """Test detection of multiple large modules."""
        modules = {
            'src': [f'src/file_{i}.js' for i in range(200)],
            'tests': [f'tests/test_{i}.js' for i in range(120)],
            'docs': ['docs/README.md']  # Small module
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        self.assertEqual(len(large_modules), 2)
        module_ids = {m['module_id'] for m in large_modules}
        self.assertEqual(module_ids, {'src', 'tests'})

    def test_no_large_modules(self):
        """Test when no modules exceed threshold."""
        modules = {
            'scripts': [f'scripts/file_{i}.py' for i in range(50)],
            'docs': ['docs/README.md']
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        self.assertEqual(len(large_modules), 0)

    def test_edge_case_exactly_threshold(self):
        """Test module with exactly threshold files (should be flagged - boundary condition)."""
        modules = {
            'scripts': [f'scripts/file_{i}.py' for i in range(100)]
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        # Exactly 100 files should be flagged (>= threshold means large)
        self.assertEqual(len(large_modules), 1)

    def test_edge_case_one_over_threshold(self):
        """Test module with threshold + 1 files (should be flagged)."""
        modules = {
            'scripts': [f'scripts/file_{i}.py' for i in range(101)]
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        # 101 files should be flagged
        self.assertEqual(len(large_modules), 1)

    def test_detection_disabled_via_config(self):
        """Test detection is skipped when enabled=false."""
        modules = {
            'scripts': [f'scripts/file_{i}.py' for i in range(200)]
        }

        config = {
            'submodule_config': {
                'enabled': False
            }
        }

        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path, config=config)

        # Should return empty list when disabled
        self.assertEqual(len(large_modules), 0)


class TestAnalyzeDirectoryStructure(unittest.TestCase):
    """Test directory structure analysis for large modules."""

    def setUp(self):
        """Create temp directory with nested structure."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_analyze_with_logical_groups(self):
        """Test analysis identifies logical groupings."""
        # Create module with subdirectories
        module_path = self.root_path / "src"
        module_path.mkdir()

        # Create logical groupings
        (module_path / "components").mkdir()
        (module_path / "components" / "Button.js").write_text("// Button component")
        (module_path / "api").mkdir()
        (module_path / "api" / "users.js").write_text("// API endpoint")
        (module_path / "tests").mkdir()
        (module_path / "tests" / "test_api.js").write_text("// Test")

        analysis = analyze_directory_structure(module_path, self.root_path)

        self.assertEqual(len(analysis['subdirectories']), 3)
        self.assertIn('components', analysis['subdirectories'])
        self.assertIn('api', analysis['subdirectories'])
        self.assertIn('tests', analysis['subdirectories'])

        # Check logical groups were identified
        group_types = {g['type'] for g in analysis['logical_groups']}
        self.assertIn('components', group_types)
        self.assertIn('api', group_types)
        self.assertIn('tests', group_types)

    def test_analyze_flat_structure(self):
        """Test analysis handles flat directory (no subdirs)."""
        module_path = self.root_path / "scripts"
        module_path.mkdir()
        (module_path / "file1.py").write_text("# File 1")
        (module_path / "file2.py").write_text("# File 2")

        analysis = analyze_directory_structure(module_path, self.root_path)

        self.assertEqual(len(analysis['subdirectories']), 0)
        self.assertEqual(len(analysis['logical_groups']), 0)

    def test_file_distribution_counting(self):
        """Test file distribution is accurately counted."""
        module_path = self.root_path / "src"
        module_path.mkdir()

        # Create subdirectories with different file counts
        components_dir = module_path / "components"
        components_dir.mkdir()
        for i in range(5):
            (components_dir / f"Component{i}.js").write_text(f"// Component {i}")

        utils_dir = module_path / "utils"
        utils_dir.mkdir()
        for i in range(3):
            (utils_dir / f"util{i}.js").write_text(f"// Util {i}")

        analysis = analyze_directory_structure(module_path, self.root_path)

        self.assertEqual(analysis['file_distribution']['components'], 5)
        self.assertEqual(analysis['file_distribution']['utils'], 3)


class TestIntegration(unittest.TestCase):
    """Integration tests for large module detection."""

    def setUp(self):
        """Create temp directory for integration tests."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_test_project(self, structure: Dict[str, int]):
        """
        Create a test project with specified structure.

        Args:
            structure: Dict mapping directory -> file count
        """
        for dir_name, file_count in structure.items():
            dir_path = self.root_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

            for i in range(file_count):
                file_path = dir_path / f"file_{i}.py"
                file_path.write_text(f"# File {i}")

    def test_small_project(self):
        """Test detection on small project (all modules < 100 files)."""
        self.create_test_project({
            'scripts': 30,
            'docs': 10,
            'tests': 25
        })

        # Collect files
        files = list(self.root_path.rglob('*.py'))

        # Organize into modules
        modules = organize_into_modules(files, self.root_path, depth=1)

        # Detect large modules
        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        # No modules should be flagged
        self.assertEqual(len(large_modules), 0)

    def test_medium_project(self):
        """Test detection on medium project (one module > 100 files)."""
        self.create_test_project({
            'src': 150,
            'tests': 80,
            'docs': 15
        })

        files = list(self.root_path.rglob('*.py'))
        modules = organize_into_modules(files, self.root_path, depth=1)
        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        # Only 'src' should be flagged
        self.assertEqual(len(large_modules), 1)
        self.assertEqual(large_modules[0]['module_id'], 'src')

    def test_large_project(self):
        """Test detection on large project (multiple modules > 100 files)."""
        self.create_test_project({
            'src': 300,
            'tests': 200,
            'scripts': 150,
            'docs': 50
        })

        files = list(self.root_path.rglob('*.py'))
        modules = organize_into_modules(files, self.root_path, depth=1)
        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)

        # Three modules should be flagged
        self.assertEqual(len(large_modules), 3)
        flagged_modules = {m['module_id'] for m in large_modules}
        self.assertEqual(flagged_modules, {'src', 'tests', 'scripts'})


class TestPerformance(unittest.TestCase):
    """Performance tests for large module detection."""

    def setUp(self):
        """Create temp directory for performance tests."""
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detection_performance_1000_files(self):
        """Test detection completes in < 100ms for 1000-file module."""
        # Create module with 1000 files
        modules = {
            'src': [f'src/file_{i}.py' for i in range(1000)]
        }

        # Measure detection time
        start_time = time.perf_counter()
        large_modules = detect_large_modules(modules, threshold=100, root_path=self.root_path)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in < 100ms
        self.assertLess(elapsed_ms, 100, f"Detection took {elapsed_ms:.2f}ms (target: <100ms)")
        self.assertEqual(len(large_modules), 1)


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLoadConfigurationSubmodule))
    suite.addTests(loader.loadTestsFromTestCase(TestGetSubmoduleConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDetectLargeModules))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalyzeDirectoryStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
