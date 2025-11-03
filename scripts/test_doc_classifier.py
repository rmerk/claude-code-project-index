"""
Unit tests for doc_classifier module.

Tests tiered documentation classification logic including:
- Critical tier pattern matching
- Standard tier pattern matching
- Archive tier pattern matching
- Custom tier rules from config
- Default tier fallback
- Edge cases and error handling
"""

import unittest
from pathlib import Path
import tempfile
import os
from doc_classifier import classify_documentation, TIER_RULES


class TestClassifyDocumentation(unittest.TestCase):
    """Test the classify_documentation function."""

    def test_critical_tier_patterns(self):
        """AC1: Classification logic identifies critical docs."""
        critical_files = [
            "README.md",
            "ARCHITECTURE.md",
            "API.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "docs/architecture/design.md",
            "docs/api/endpoints.md",
        ]

        for file_path in critical_files:
            with self.subTest(file=file_path):
                tier = classify_documentation(Path(file_path))
                self.assertEqual(tier, "critical",
                               f"{file_path} should be classified as critical")

    def test_standard_tier_patterns(self):
        """AC2: Classification identifies standard docs."""
        standard_files = [
            "docs/development/setup.md",
            "docs/guides/testing.md",
            "INSTALL.md",
            "SETUP.md",
            "docs/how-to/deploy.md",
            "docs/setup/local-env.md",
        ]

        for file_path in standard_files:
            with self.subTest(file=file_path):
                tier = classify_documentation(Path(file_path))
                self.assertEqual(tier, "standard",
                               f"{file_path} should be classified as standard")

    def test_archive_tier_patterns(self):
        """AC3: Classification identifies archive docs."""
        archive_files = [
            "CHANGELOG.md",
            "docs/tutorials/intro.md",
            "docs/meetings/2024-01.md",
            "docs/archive/old.md",
            "HISTORY.md",
            "docs/legacy/deprecated.md",
        ]

        for file_path in archive_files:
            with self.subTest(file=file_path):
                tier = classify_documentation(Path(file_path))
                self.assertEqual(tier, "archive",
                               f"{file_path} should be classified as archive")

    def test_default_tier_fallback(self):
        """Test default tier assignment for unmatched files."""
        unmatched_files = [
            "random.md",
            "notes.md",
            "temp.md",
            "docs/misc/random.md",
        ]

        for file_path in unmatched_files:
            with self.subTest(file=file_path):
                tier = classify_documentation(Path(file_path))
                self.assertEqual(tier, "standard",
                               f"{file_path} should default to standard tier")

    def test_custom_tier_rules_extend_defaults(self):
        """AC4: Classification rules are configurable via config file."""
        # Custom rules that extend defaults
        custom_config = {
            "doc_tiers": {
                "critical": ["CUSTOM_CRITICAL.md"],
                "standard": ["docs/custom/*"],
                "archive": ["old-*"]
            }
        }

        # Test custom critical pattern
        tier = classify_documentation(Path("CUSTOM_CRITICAL.md"), custom_config)
        self.assertEqual(tier, "critical")

        # Test custom standard pattern
        tier = classify_documentation(Path("docs/custom/guide.md"), custom_config)
        self.assertEqual(tier, "standard")

        # Test custom archive pattern
        tier = classify_documentation(Path("old-notes.md"), custom_config)
        self.assertEqual(tier, "archive")

        # Verify defaults still work
        tier = classify_documentation(Path("README.md"), custom_config)
        self.assertEqual(tier, "critical")

    def test_custom_config_invalid_format(self):
        """Test graceful handling of invalid config."""
        # Missing doc_tiers key
        config1 = {"mode": "auto"}
        tier = classify_documentation(Path("README.md"), config1)
        self.assertEqual(tier, "critical")

        # doc_tiers is not a dict
        config2 = {"doc_tiers": "invalid"}
        tier = classify_documentation(Path("README.md"), config2)
        self.assertEqual(tier, "critical")

        # doc_tiers has non-list values
        config3 = {"doc_tiers": {"critical": "not_a_list"}}
        tier = classify_documentation(Path("README.md"), config3)
        self.assertEqual(tier, "critical")

    def test_config_none(self):
        """Test classification with None config."""
        tier = classify_documentation(Path("README.md"), None)
        self.assertEqual(tier, "critical")

    def test_config_empty_dict(self):
        """Test classification with empty config dict."""
        tier = classify_documentation(Path("README.md"), {})
        self.assertEqual(tier, "critical")

    def test_path_normalization(self):
        """Test that paths are normalized for consistent matching."""
        # Test with absolute path
        with tempfile.TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir) / "README.md"
            tier = classify_documentation(abs_path)
            self.assertEqual(tier, "critical")

        # Test with relative path
        rel_path = Path("./README.md")
        tier = classify_documentation(rel_path)
        self.assertEqual(tier, "critical")

    def test_case_sensitivity(self):
        """Test that pattern matching handles case correctly."""
        # README* should match README.md (uppercase)
        tier = classify_documentation(Path("README.md"))
        self.assertEqual(tier, "critical")

        # But readme.md (lowercase) should also match due to glob pattern
        tier = classify_documentation(Path("readme.md"))
        # Path.match() is case-sensitive on Unix, case-insensitive on Windows
        # We accept either critical (if matched) or standard (default)
        self.assertIn(tier, ["critical", "standard"])

    def test_tier_rules_structure(self):
        """Test that TIER_RULES constant has expected structure."""
        self.assertIsInstance(TIER_RULES, dict)
        self.assertIn("critical", TIER_RULES)
        self.assertIn("standard", TIER_RULES)
        self.assertIn("archive", TIER_RULES)

        # Each tier should have a list of patterns
        for tier, patterns in TIER_RULES.items():
            self.assertIsInstance(patterns, list)
            self.assertGreater(len(patterns), 0)
            # All patterns should be strings
            for pattern in patterns:
                self.assertIsInstance(pattern, str)


class TestIntegrationWithRealFiles(unittest.TestCase):
    """Integration tests with actual file system."""

    def test_with_temporary_files(self):
        """Test classification with actual files in temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create README.md
            readme = tmpdir_path / "README.md"
            readme.write_text("# Project README")
            tier = classify_documentation(readme)
            self.assertEqual(tier, "critical")

            # Create docs/development/ structure
            dev_dir = tmpdir_path / "docs" / "development"
            dev_dir.mkdir(parents=True)
            guide = dev_dir / "guide.md"
            guide.write_text("# Development Guide")
            tier = classify_documentation(guide)
            self.assertEqual(tier, "standard")

            # Create CHANGELOG.md
            changelog = tmpdir_path / "CHANGELOG.md"
            changelog.write_text("# Changelog")
            tier = classify_documentation(changelog)
            self.assertEqual(tier, "archive")

    def test_relative_to_cwd(self):
        """Test classification of files relative to current working directory."""
        # Save current directory
        original_cwd = os.getcwd()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create a README.md in the temp directory
                Path("README.md").write_text("# Test")

                # Classify using relative path
                tier = classify_documentation(Path("README.md"))
                self.assertEqual(tier, "critical")

        finally:
            os.chdir(original_cwd)

    def test_classification_performance(self):
        """Test that classification is fast (< 1ms per file)."""
        import time

        test_files = [
            "README.md",
            "docs/development/setup.md",
            "CHANGELOG.md",
            "random.md",
        ] * 25  # 100 files total

        start = time.time()
        for file_path in test_files:
            classify_documentation(Path(file_path))
        elapsed = time.time() - start

        # Should be very fast (< 100ms for 100 files)
        self.assertLess(elapsed, 0.1,
                       f"Classification too slow: {elapsed:.3f}s for {len(test_files)} files")


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestClassifyDocumentation))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWithRealFiles))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
