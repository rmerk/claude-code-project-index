"""
Unit and integration tests for Smart Configuration Presets (Story 3.1).

Tests auto-detection logic, preset loading, configuration management,
and preset boundary crossing workflows.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from project_index import (
    auto_detect_preset,
    load_preset_template,
    detect_preset_from_config,
    load_configuration
)
from index_utils import get_git_files


class TestAutoDetectPreset(unittest.TestCase):
    """Test auto_detect_preset() function (AC#2, #4)."""

    def test_small_preset_boundary(self):
        """Files <100 should return 'small'."""
        self.assertEqual(auto_detect_preset(0), "small")
        self.assertEqual(auto_detect_preset(50), "small")
        self.assertEqual(auto_detect_preset(99), "small")

    def test_medium_preset_boundary(self):
        """Files 100-4999 should return 'medium'."""
        self.assertEqual(auto_detect_preset(100), "medium")
        self.assertEqual(auto_detect_preset(500), "medium")
        self.assertEqual(auto_detect_preset(4999), "medium")

    def test_large_preset_boundary(self):
        """Files 5000+ should return 'large'."""
        self.assertEqual(auto_detect_preset(5000), "large")
        self.assertEqual(auto_detect_preset(10000), "large")


class TestLoadPresetTemplate(unittest.TestCase):
    """Test load_preset_template() function (AC#1)."""

    def setUp(self):
        """Create temporary template directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / ".claude-code-project-index" / "templates"
        self.templates_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('project_index.Path.home')
    def test_load_small_preset(self, mock_home):
        """Load small preset template successfully."""
        # Create small preset
        small_preset = {
            "_preset": "small",
            "_generated": "auto",
            "mode": "single",
            "threshold": 100
        }
        with open(self.templates_dir / "small.json", 'w') as f:
            json.dump(small_preset, f)

        # Mock Path.home() to use temp directory
        mock_home.return_value = Path(self.temp_dir)

        config = load_preset_template("small")

        self.assertEqual(config["_preset"], "small")
        self.assertEqual(config["mode"], "single")
        self.assertEqual(config["threshold"], 100)
        self.assertNotEqual(config["_generated"], "auto")  # Should be timestamp

    @patch('project_index.Path.home')
    def test_generated_timestamp_replacement(self, mock_home):
        """_generated field should be replaced with timestamp."""
        preset = {"_preset": "medium", "_generated": "auto"}
        with open(self.templates_dir / "medium.json", 'w') as f:
            json.dump(preset, f)

        mock_home.return_value = Path(self.temp_dir)

        config = load_preset_template("medium")
        self.assertIn("T", config["_generated"])  # ISO timestamp format

    @patch('project_index.Path.home')
    def test_template_not_found_fallback(self, mock_home):
        """Should gracefully fallback if template missing."""
        mock_home.return_value = Path(self.temp_dir)

        config = load_preset_template("nonexistent")

        self.assertEqual(config["_preset"], "nonexistent")
        self.assertEqual(config["mode"], "auto")
        self.assertIn("_generated", config)

    @patch('project_index.Path.home')
    def test_invalid_json_fallback(self, mock_home):
        """Should gracefully handle invalid JSON."""
        with open(self.templates_dir / "broken.json", 'w') as f:
            f.write("{invalid json")

        mock_home.return_value = Path(self.temp_dir)

        config = load_preset_template("broken")

        self.assertEqual(config["_preset"], "broken")
        self.assertIn("_generated", config)


class TestDetectPresetFromConfig(unittest.TestCase):
    """Test detect_preset_from_config() function (AC#4)."""

    def test_detect_from_metadata(self):
        """Should use _preset metadata field if present."""
        config = {"_preset": "large", "threshold": 100}
        self.assertEqual(detect_preset_from_config(config), "large")

    def test_fallback_to_threshold_small(self):
        """Should infer 'small' from low threshold."""
        config = {"threshold": 100}
        self.assertEqual(detect_preset_from_config(config), "small")

        config = {"threshold": 150}
        self.assertEqual(detect_preset_from_config(config), "small")

    def test_fallback_to_threshold_medium(self):
        """Should infer 'medium' from medium threshold."""
        config = {"threshold": 500}
        self.assertEqual(detect_preset_from_config(config), "medium")

        config = {"threshold": 750}
        self.assertEqual(detect_preset_from_config(config), "medium")

    def test_fallback_to_threshold_large(self):
        """Should infer 'large' from high threshold."""
        config = {"threshold": 1000}
        self.assertEqual(detect_preset_from_config(config), "large")

    def test_default_threshold(self):
        """Should handle missing threshold."""
        config = {}
        result = detect_preset_from_config(config)
        self.assertIn(result, ["small", "medium", "large"])


class TestLoadConfigurationFirstRun(unittest.TestCase):
    """Test load_configuration() on first run (AC#2, #3)."""

    def setUp(self):
        """Create temporary project directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".project-index.json"
        self.templates_dir = Path(self.temp_dir) / ".claude-code-project-index" / "templates"
        self.templates_dir.mkdir(parents=True)

        # Create preset templates
        for preset_name in ["small", "medium", "large"]:
            preset = {
                "_preset": preset_name,
                "_generated": "auto",
                "mode": preset_name if preset_name != "medium" else "auto",
                "threshold": 100 if preset_name == "small" else (500 if preset_name == "medium" else 1000)
            }
            with open(self.templates_dir / f"{preset_name}.json", 'w') as f:
                json.dump(preset, f)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_first_run_creates_small_preset(self, mock_home, mock_git_files):
        """First run with <100 files creates small preset."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(50)]

        with patch('builtins.input', return_value='y'):
            config = load_configuration(self.config_path, Path(self.temp_dir))

        self.assertEqual(config["_preset"], "small")
        self.assertTrue(self.config_path.exists())

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_first_run_creates_medium_preset(self, mock_home, mock_git_files):
        """First run with 100-4999 files creates medium preset."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(1000)]

        with patch('builtins.input', return_value='y'):
            config = load_configuration(self.config_path, Path(self.temp_dir))

        self.assertEqual(config["_preset"], "medium")
        self.assertTrue(self.config_path.exists())

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_first_run_creates_large_preset(self, mock_home, mock_git_files):
        """First run with 5000+ files creates large preset."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(6000)]

        with patch('builtins.input', return_value='y'):
            config = load_configuration(self.config_path, Path(self.temp_dir))

        self.assertEqual(config["_preset"], "large")
        self.assertTrue(self.config_path.exists())


class TestLoadConfigurationBoundaryCrossing(unittest.TestCase):
    """Test boundary crossing detection and upgrade prompts (AC#4, #5, #6)."""

    def setUp(self):
        """Create temporary project directory with existing config."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".project-index.json"
        self.templates_dir = Path(self.temp_dir) / ".claude-code-project-index" / "templates"
        self.templates_dir.mkdir(parents=True)

        # Create preset templates
        for preset_name in ["small", "medium", "large"]:
            preset = {
                "_preset": preset_name,
                "_generated": "auto",
                "mode": "auto",
                "threshold": 500
            }
            with open(self.templates_dir / f"{preset_name}.json", 'w') as f:
                json.dump(preset, f)

        # Create existing small preset config
        existing_config = {
            "_preset": "small",
            "_generated": "2025-01-01T00:00:00",
            "mode": "single",
            "threshold": 100
        }
        with open(self.config_path, 'w') as f:
            json.dump(existing_config, f)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    @patch('builtins.input')
    def test_boundary_crossing_user_accepts(self, mock_input, mock_home, mock_git_files):
        """User accepts upgrade when crossing from small to medium."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(500)]
        mock_input.return_value = 'y'

        config = load_configuration(self.config_path, Path(self.temp_dir))

        self.assertEqual(config["_preset"], "medium")
        self.assertTrue((Path(str(self.config_path) + ".backup")).exists())

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    @patch('builtins.input')
    def test_boundary_crossing_user_declines(self, mock_input, mock_home, mock_git_files):
        """User declines upgrade when crossing boundary."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(500)]
        mock_input.return_value = 'n'

        config = load_configuration(self.config_path, Path(self.temp_dir))

        self.assertEqual(config["_preset"], "small")  # Unchanged
        self.assertFalse((Path(str(self.config_path) + ".backup")).exists())

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_no_prompt_with_sys_argv_flag(self, mock_home, mock_git_files):
        """--no-prompt flag skips interactive prompt."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(500)]

        # Add --no-prompt to sys.argv
        sys.argv.append('--no-prompt')
        try:
            config = load_configuration(self.config_path, Path(self.temp_dir))
            self.assertEqual(config["_preset"], "medium")  # Auto-upgraded
        finally:
            sys.argv.remove('--no-prompt')


class TestCommandLineFlags(unittest.TestCase):
    """Test command-line flags (AC#7, #8)."""

    def setUp(self):
        """Create temporary project directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".project-index.json"
        self.templates_dir = Path(self.temp_dir) / ".claude-code-project-index" / "templates"
        self.templates_dir.mkdir(parents=True)

        # Create preset templates
        for preset_name in ["small", "medium", "large"]:
            preset = {
                "_preset": preset_name,
                "_generated": "auto",
                "mode": "auto",
                "threshold": 500
            }
            with open(self.templates_dir / f"{preset_name}.json", 'w') as f:
                json.dump(preset, f)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_upgrade_to_flag_forces_preset(self, mock_home, mock_git_files):
        """--upgrade-to=large forces large preset regardless of file count."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(50)]  # Small project

        # Add --upgrade-to=large to sys.argv
        sys.argv.append('--upgrade-to=large')
        try:
            config = load_configuration(self.config_path, Path(self.temp_dir))
            self.assertEqual(config["_preset"], "large")  # Forced to large despite 50 files
        finally:
            sys.argv.remove('--upgrade-to=large')

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_invalid_upgrade_to_flag(self, mock_home, mock_git_files):
        """Invalid --upgrade-to value should be ignored."""
        mock_home.return_value = Path(self.temp_dir)
        mock_git_files.return_value = [Path(f"file{i}.py") for i in range(50)]

        sys.argv.append('--upgrade-to=invalid')
        try:
            with patch('builtins.input', return_value='y'):
                config = load_configuration(self.config_path, Path(self.temp_dir))
            self.assertEqual(config["_preset"], "small")  # Falls back to auto-detection
        finally:
            sys.argv.remove('--upgrade-to=invalid')


class TestPerformance(unittest.TestCase):
    """Test performance requirements (NFR)."""

    @patch('project_index.get_git_files')
    @patch('project_index.Path.home')
    def test_preset_detection_under_5_seconds(self, mock_home, mock_git_files):
        """Preset detection should complete in <5 seconds for 10,000 files."""
        temp_dir = tempfile.mkdtemp()
        try:
            config_path = Path(temp_dir) / ".project-index.json"
            templates_dir = Path(temp_dir) / ".claude-code-project-index" / "templates"
            templates_dir.mkdir(parents=True)

            # Create template
            preset = {"_preset": "large", "_generated": "auto", "mode": "split"}
            with open(templates_dir / "large.json", 'w') as f:
                json.dump(preset, f)

            mock_home.return_value = Path(temp_dir)
            mock_git_files.return_value = [Path(f"file{i}.py") for i in range(10000)]

            start = time.time()
            with patch('builtins.input', return_value='y'):
                config = load_configuration(config_path, Path(temp_dir))
            duration = time.time() - start

            self.assertLess(duration, 5.0, f"Preset detection took {duration:.2f}s (should be <5s)")
        finally:
            shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAutoDetectPreset))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadPresetTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestDetectPresetFromConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadConfigurationFirstRun))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadConfigurationBoundaryCrossing))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandLineFlags))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
