#!/usr/bin/env python3
"""
Test suite for configuration system and mode selection.

Tests cover:
- Configuration file loading and validation
- CLI flag parsing and precedence
- Mode selection logic
- Threshold configuration
- Auto-detection behavior
- Configuration precedence (CLI > config > defaults)
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from project_index import load_configuration, main


class TestLoadConfiguration(unittest.TestCase):
    """Test configuration file loading (AC#1, #2, #3)."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_path)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    def test_load_valid_config_all_fields(self):
        """Test loading configuration with all fields present."""
        config_data = {
            "mode": "split",
            "threshold": 500,
            "max_index_size": 2097152,
            "compression_level": "aggressive"
        }
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertEqual(config['mode'], 'split')
        self.assertEqual(config['threshold'], 500)
        self.assertEqual(config['max_index_size'], 2097152)
        self.assertEqual(config['compression_level'], 'aggressive')

    def test_load_config_missing_file(self):
        """Test loading when config file doesn't exist (should return empty dict)."""
        config_path = self.test_path / ".project-index.json"
        config = load_configuration(config_path)

        self.assertEqual(config, {})

    def test_load_config_invalid_json(self):
        """Test loading corrupted JSON (should return empty dict with warning)."""
        config_path = self.test_path / ".project-index.json"
        config_path.write_text("{ invalid json }")

        config = load_configuration(config_path)

        self.assertEqual(config, {})

    def test_load_config_invalid_mode(self):
        """Test loading with invalid mode value (should remove invalid field)."""
        config_data = {"mode": "invalid_mode"}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertNotIn('mode', config)

    def test_load_config_invalid_threshold(self):
        """Test loading with invalid threshold (should remove invalid field)."""
        config_data = {"threshold": -100}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertNotIn('threshold', config)

    def test_load_config_threshold_string(self):
        """Test loading with threshold as string (should remove invalid field)."""
        config_data = {"threshold": "not a number"}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertNotIn('threshold', config)

    def test_load_config_mode_auto(self):
        """Test loading with mode='auto' (valid, should preserve)."""
        config_data = {"mode": "auto"}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertEqual(config['mode'], 'auto')

    def test_load_config_mode_single(self):
        """Test loading with mode='single' (valid, should preserve)."""
        config_data = {"mode": "single"}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertEqual(config['mode'], 'single')

    def test_load_config_partial_fields(self):
        """Test loading with only some fields present."""
        config_data = {"mode": "split"}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        config = load_configuration(config_path)

        self.assertEqual(config['mode'], 'split')
        self.assertNotIn('threshold', config)

    def test_load_config_performance(self):
        """Test configuration loading completes in <100ms (NFR)."""
        config_data = {"mode": "auto", "threshold": 1000}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        start_time = time.time()
        config = load_configuration(config_path)
        elapsed_ms = (time.time() - start_time) * 1000

        self.assertLess(elapsed_ms, 100, f"Config loading took {elapsed_ms:.1f}ms (should be <100ms)")
        self.assertEqual(config['mode'], 'auto')


class TestConfigurationPrecedence(unittest.TestCase):
    """Test configuration precedence: CLI > config file > defaults (AC#1, #2, #3)."""

    def setUp(self):
        """Create temporary directory and config file."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_path)

        # Create config file with defaults
        self.config_data = {
            "mode": "auto",
            "threshold": 500
        }
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(self.config_data))

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    @patch('sys.argv', ['project_index.py', '--mode', 'split'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    def test_cli_mode_overrides_config(self, mock_summary, mock_generate):
        """Test CLI --mode flag overrides config file mode."""
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        # Config has mode=auto, CLI has mode=split
        # CLI should win
        main()

        # Verify split mode was used
        mock_generate.assert_called_once()

    @patch('sys.argv', ['project_index.py', '--threshold', '2000'])
    @patch('project_index.build_index')
    @patch('project_index.convert_to_enhanced_dense_format')
    @patch('project_index.compress_if_needed')
    @patch('project_index.print_summary')
    @patch('index_utils.get_git_files')
    def test_cli_threshold_overrides_config(self, mock_git_files, mock_summary,
                                            mock_compress, mock_convert, mock_build):
        """Test CLI --threshold flag overrides config file threshold."""
        # Mock 1500 files (between config threshold 500 and CLI threshold 2000)
        mock_git_files.return_value = ['file' + str(i) for i in range(1500)]
        mock_build.return_value = ({'version': '1.0'}, 0)
        mock_convert.return_value = {'version': '1.0'}
        mock_compress.return_value = {'version': '1.0'}

        # Config threshold=500, CLI threshold=2000
        # With 1500 files: config would trigger split, CLI should not
        main()

        # Verify legacy mode was used (because 1500 < 2000 CLI threshold)
        mock_build.assert_called_once()

    def test_config_file_used_when_no_cli_flags(self):
        """Test config file values used when no CLI flags provided."""
        config = load_configuration()

        self.assertEqual(config['mode'], 'auto')
        self.assertEqual(config['threshold'], 500)


class TestModeSelection(unittest.TestCase):
    """Test mode selection logic (AC#1, #2, #3)."""

    def setUp(self):
        """Create temporary directory."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_path)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    @patch('sys.argv', ['project_index.py', '--mode', 'split'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    def test_mode_split_forces_split_format(self, mock_summary, mock_generate):
        """Test --mode split always generates split format (AC#2)."""
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        main()

        mock_generate.assert_called_once()

    @patch('sys.argv', ['project_index.py', '--mode', 'single'])
    @patch('project_index.build_index')
    @patch('project_index.convert_to_enhanced_dense_format')
    @patch('project_index.compress_if_needed')
    @patch('project_index.print_summary')
    def test_mode_single_forces_single_format(self, mock_summary, mock_compress,
                                              mock_convert, mock_build):
        """Test --mode single always generates single-file format (AC#1)."""
        mock_build.return_value = ({'version': '1.0'}, 0)
        mock_convert.return_value = {'version': '1.0'}
        mock_compress.return_value = {'version': '1.0'}

        main()

        mock_build.assert_called_once()

    @patch('sys.argv', ['project_index.py', '--mode', 'auto'])
    @patch('project_index.build_index')
    @patch('project_index.convert_to_enhanced_dense_format')
    @patch('project_index.compress_if_needed')
    @patch('project_index.print_summary')
    @patch('index_utils.get_git_files')
    def test_mode_auto_respects_threshold(self, mock_git_files, mock_summary,
                                          mock_compress, mock_convert, mock_build):
        """Test --mode auto uses threshold for decision (AC#3)."""
        # Mock 999 files (below default threshold of 1000)
        mock_git_files.return_value = ['file' + str(i) for i in range(999)]
        mock_build.return_value = ({'version': '1.0'}, 0)
        mock_convert.return_value = {'version': '1.0'}
        mock_compress.return_value = {'version': '1.0'}

        main()

        # Should use single-file mode
        mock_build.assert_called_once()

    @patch('sys.argv', ['project_index.py', '--mode', 'auto'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    @patch('index_utils.get_git_files')
    def test_mode_auto_triggers_split_above_threshold(self, mock_git_files,
                                                      mock_summary, mock_generate):
        """Test --mode auto triggers split when file count exceeds threshold."""
        # Mock 1001 files (above default threshold of 1000)
        mock_git_files.return_value = ['file' + str(i) for i in range(1001)]
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        main()

        # Should use split mode
        mock_generate.assert_called_once()


class TestCustomThreshold(unittest.TestCase):
    """Test custom threshold configuration (AC#3)."""

    def setUp(self):
        """Create temporary directory."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_path)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    @patch('sys.argv', ['project_index.py', '--threshold', '500'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    @patch('index_utils.get_git_files')
    def test_custom_threshold_via_cli(self, mock_git_files, mock_summary, mock_generate):
        """Test custom threshold via --threshold flag."""
        # Mock 501 files (just above custom threshold of 500)
        mock_git_files.return_value = ['file' + str(i) for i in range(501)]
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        main()

        # Should trigger split mode with custom threshold
        mock_generate.assert_called_once()

    @patch('sys.argv', ['project_index.py'])
    @patch('project_index.build_index')
    @patch('project_index.convert_to_enhanced_dense_format')
    @patch('project_index.compress_if_needed')
    @patch('project_index.print_summary')
    @patch('index_utils.get_git_files')
    def test_config_file_threshold(self, mock_git_files, mock_summary,
                                   mock_compress, mock_convert, mock_build):
        """Test custom threshold from config file."""
        # Create config with threshold=500
        config_data = {"threshold": 500}
        config_path = self.test_path / ".project-index.json"
        config_path.write_text(json.dumps(config_data))

        # Mock 499 files (below config threshold of 500)
        mock_git_files.return_value = ['file' + str(i) for i in range(499)]
        mock_build.return_value = ({'version': '1.0'}, 0)
        mock_convert.return_value = {'version': '1.0'}
        mock_compress.return_value = {'version': '1.0'}

        main()

        # Should use single-file mode
        mock_build.assert_called_once()


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with legacy flags."""

    def setUp(self):
        """Create temporary directory."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_path)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    @patch('sys.argv', ['project_index.py', '--format=split'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    def test_legacy_format_split_flag(self, mock_summary, mock_generate):
        """Test legacy --format=split flag still works."""
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        main()

        mock_generate.assert_called_once()

    @patch('sys.argv', ['project_index.py', '--split'])
    @patch('project_index.generate_split_index')
    @patch('project_index.print_summary')
    def test_legacy_split_flag(self, mock_summary, mock_generate):
        """Test legacy --split flag still works."""
        mock_generate.return_value = ({'version': '2.0-split'}, 0)

        main()

        mock_generate.assert_called_once()


def run_all_tests():
    """Run all configuration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLoadConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationPrecedence))
    suite.addTests(loader.loadTestsFromTestCase(TestModeSelection))
    suite.addTests(loader.loadTestsFromTestCase(TestCustomThreshold))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardCompatibility))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
