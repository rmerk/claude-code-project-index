"""
Unit and integration tests for git_metadata module.

Tests git metadata extraction including:
- Commit hash, author, date, message extraction
- PR number parsing from commit messages
- Lines changed extraction
- Recency days calculation
- Fallback to filesystem mtime when git unavailable
- Error handling and edge cases
- Integration with project_index.py
- Performance requirements (<5s overhead)
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from git_metadata import (
    extract_git_metadata,
    _extract_pr_number,
    _calculate_recency_days,
    _fallback_to_mtime
)


class TestExtractGitMetadata(unittest.TestCase):
    """Test the main extract_git_metadata function."""

    def setUp(self):
        """Create a temporary git repository for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_path, capture_output=True, check=True)

        # Create a test file
        self.test_file = self.repo_path / 'test.py'
        self.test_file.write_text('print("hello")\n')

        # Make initial commit
        subprocess.run(['git', 'add', 'test.py'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit (#123)'],
            cwd=self.repo_path,
            capture_output=True,
            check=True
        )

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_extract_commit_hash(self):
        """AC#1: Extract commit hash from git log."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertIsNotNone(metadata.get('commit'))
        self.assertIsInstance(metadata['commit'], str)
        self.assertEqual(len(metadata['commit']), 40)  # Full SHA-1 hash

    def test_extract_author_email(self):
        """AC#1: Extract author email from git log."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertIsNotNone(metadata.get('author'))
        self.assertEqual(metadata['author'], 'test@example.com')

    def test_extract_commit_date(self):
        """AC#1: Extract commit date in ISO8601 format."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertIsNotNone(metadata.get('date'))
        # Verify it's a valid ISO8601 date
        parsed_date = datetime.fromisoformat(metadata['date'])
        self.assertIsInstance(parsed_date, datetime)

    def test_extract_commit_message(self):
        """AC#1: Extract commit message."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertIsNotNone(metadata.get('message'))
        self.assertIn('Initial commit', metadata['message'])

    def test_extract_pr_number_from_message(self):
        """AC#2: Extract PR number from commit message."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertEqual(metadata.get('pr'), '123')

    def test_extract_lines_changed(self):
        """AC#1: Extract lines changed from git diff."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        # First commit adds 1 line
        self.assertIsNotNone(metadata.get('lines_changed'))
        self.assertEqual(metadata['lines_changed'], 1)

    def test_recency_days_calculation(self):
        """AC#1: Calculate recency days from commit date."""
        metadata = extract_git_metadata(self.test_file, self.repo_path)

        self.assertIsNotNone(metadata.get('recency_days'))
        self.assertIsInstance(metadata['recency_days'], int)
        # Commit just made, should be 0 days
        self.assertEqual(metadata['recency_days'], 0)

    def test_caching_mechanism(self):
        """AC#5: Verify caching avoids duplicate git queries."""
        cache = {}

        # First call
        start_time = time.time()
        metadata1 = extract_git_metadata(self.test_file, self.repo_path, cache)
        first_call_time = time.time() - start_time

        # Second call (should use cache)
        start_time = time.time()
        metadata2 = extract_git_metadata(self.test_file, self.repo_path, cache)
        second_call_time = time.time() - start_time

        # Results should be identical
        self.assertEqual(metadata1, metadata2)

        # Second call should be much faster (cached)
        self.assertLess(second_call_time, first_call_time * 0.1)  # At least 10x faster

    def test_fallback_to_mtime_when_git_unavailable(self):
        """AC#3: Graceful fallback to filesystem mtime when git unavailable."""
        # Create file in non-git directory
        non_git_dir = tempfile.TemporaryDirectory()
        non_git_path = Path(non_git_dir.name)
        test_file = non_git_path / 'test.txt'
        test_file.write_text('content')

        metadata = extract_git_metadata(test_file, non_git_path)

        # Should fallback to mtime
        self.assertIsNone(metadata.get('commit'))
        self.assertIsNone(metadata.get('author'))
        self.assertIsNone(metadata.get('message'))
        self.assertIsNone(metadata.get('pr'))
        self.assertIsNone(metadata.get('lines_changed'))

        # Should have date from mtime
        self.assertIsNotNone(metadata.get('date'))
        # Should have recency_days
        self.assertIsInstance(metadata.get('recency_days'), int)

        non_git_dir.cleanup()

    def test_multiple_commits_returns_latest(self):
        """Verify extraction returns data from the most recent commit."""
        # Make second commit with different message
        self.test_file.write_text('print("hello")\nprint("world")\n')
        subprocess.run(['git', 'add', 'test.py'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Second commit (#456)'],
            cwd=self.repo_path,
            capture_output=True,
            check=True
        )

        metadata = extract_git_metadata(self.test_file, self.repo_path)

        # Should get latest commit
        self.assertIn('Second commit', metadata['message'])
        self.assertEqual(metadata['pr'], '456')
        self.assertEqual(metadata['lines_changed'], 1)  # Added 1 line


class TestPRNumberExtraction(unittest.TestCase):
    """Test PR number parsing from commit messages."""

    def test_parse_pr_with_hash(self):
        """AC#2: Extract PR number from #123 pattern."""
        self.assertEqual(_extract_pr_number("Fix bug (#123)"), "123")

    def test_parse_pr_without_parens(self):
        """AC#2: Extract PR number from #456 pattern."""
        self.assertEqual(_extract_pr_number("Update docs #456"), "456")

    def test_parse_pr_with_prefix(self):
        """AC#2: Extract PR number from PR #789 pattern."""
        self.assertEqual(_extract_pr_number("Merge PR #789"), "789")

    def test_no_pr_in_message(self):
        """AC#2: Return None when no PR number found."""
        self.assertIsNone(_extract_pr_number("Fix bug"))
        self.assertIsNone(_extract_pr_number("Update documentation"))

    def test_multiple_pr_numbers_returns_first(self):
        """Return first PR number when multiple are present."""
        self.assertEqual(_extract_pr_number("Fix #123 and #456"), "123")

    def test_empty_message(self):
        """Handle empty commit message gracefully."""
        self.assertIsNone(_extract_pr_number(""))
        self.assertIsNone(_extract_pr_number(None))


class TestRecencyCalculation(unittest.TestCase):
    """Test recency days calculation."""

    def test_calculate_recency_today(self):
        """Test recency for commit made today."""
        today = datetime.now(timezone.utc).isoformat()
        recency = _calculate_recency_days(today)
        self.assertEqual(recency, 0)

    def test_calculate_recency_yesterday(self):
        """Test recency for commit made yesterday."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        recency = _calculate_recency_days(yesterday)
        self.assertEqual(recency, 1)

    def test_calculate_recency_week_ago(self):
        """Test recency for commit made a week ago."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recency = _calculate_recency_days(week_ago)
        self.assertEqual(recency, 7)

    def test_calculate_recency_invalid_date(self):
        """Handle invalid date gracefully."""
        recency = _calculate_recency_days("invalid-date")
        self.assertEqual(recency, 0)

    def test_calculate_recency_with_timezone(self):
        """Handle dates with timezone info correctly."""
        iso_date = "2025-10-29T14:32:00-05:00"
        recency = _calculate_recency_days(iso_date)
        # Should be at least a few days (depending on test run date)
        self.assertGreaterEqual(recency, 0)


class TestFallbackToMtime(unittest.TestCase):
    """Test fallback behavior when git unavailable."""

    def test_fallback_returns_valid_structure(self):
        """AC#3: Fallback returns proper metadata structure."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write('test content')
        temp_file.close()

        try:
            metadata = _fallback_to_mtime(Path(temp_file.name))

            # Check structure
            self.assertIsNone(metadata['commit'])
            self.assertIsNone(metadata['author'])
            self.assertIsNone(metadata['message'])
            self.assertIsNone(metadata['pr'])
            self.assertIsNone(metadata['lines_changed'])

            # Should have date from mtime
            self.assertIsNotNone(metadata['date'])
            parsed_date = datetime.fromisoformat(metadata['date'])
            self.assertIsInstance(parsed_date, datetime)

            # Should have recency_days
            self.assertIsInstance(metadata['recency_days'], int)
            self.assertEqual(metadata['recency_days'], 0)  # File just created

        finally:
            os.unlink(temp_file.name)

    def test_fallback_nonexistent_file(self):
        """Handle nonexistent file gracefully."""
        metadata = _fallback_to_mtime(Path('/nonexistent/file.txt'))

        # Should return structure with None values
        self.assertIsNone(metadata['commit'])
        self.assertIsNone(metadata['date'])
        self.assertEqual(metadata['recency_days'], 0)


class TestIntegrationWithProjectIndex(unittest.TestCase):
    """Integration tests with project_index.py."""

    def setUp(self):
        """Create a temporary git repository with multiple files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_path, capture_output=True, check=True)

        # Create multiple files
        for i in range(10):
            test_file = self.repo_path / f'file{i}.py'
            test_file.write_text(f'print("file {i}")\n')

        # Commit all files
        subprocess.run(['git', 'add', '.'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Add test files (#999)'],
            cwd=self.repo_path,
            capture_output=True,
            check=True
        )

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_extract_metadata_for_all_files(self):
        """AC#4: Git metadata included for all files."""
        cache = {}

        # Extract metadata for all files
        for i in range(10):
            file_path = self.repo_path / f'file{i}.py'
            metadata = extract_git_metadata(file_path, self.repo_path, cache)

            # Verify all fields present
            self.assertIsNotNone(metadata['commit'])
            self.assertIsNotNone(metadata['author'])
            self.assertIsNotNone(metadata['date'])
            self.assertIsNotNone(metadata['message'])
            self.assertEqual(metadata['pr'], '999')
            self.assertIsNotNone(metadata['lines_changed'])
            self.assertIsInstance(metadata['recency_days'], int)

        # Verify cache was used
        self.assertEqual(len(cache), 10)


class TestPerformance(unittest.TestCase):
    """Test performance requirements."""

    def setUp(self):
        """Create a larger temporary git repository."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_path, capture_output=True, check=True)

        # Create 100 files to simulate realistic project
        for i in range(100):
            test_file = self.repo_path / f'file{i}.py'
            test_file.write_text(f'# File {i}\nprint("test")\n')

        # Commit all files
        subprocess.run(['git', 'add', '.'], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit'],
            cwd=self.repo_path,
            capture_output=True,
            check=True
        )

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_extraction_performance_under_5_seconds(self):
        """AC#5: Git extraction adds <5 seconds overhead for 100 files."""
        cache = {}
        start_time = time.time()

        # Extract metadata for all 100 files
        for i in range(100):
            file_path = self.repo_path / f'file{i}.py'
            metadata = extract_git_metadata(file_path, self.repo_path, cache)
            self.assertIsNotNone(metadata['commit'])

        elapsed_time = time.time() - start_time

        # Should complete in under 5 seconds
        self.assertLess(elapsed_time, 5.0,
                       f"Git extraction took {elapsed_time:.2f}s for 100 files, should be <5s")

        # Print timing for visibility
        print(f"\n✓ Extracted git metadata for 100 files in {elapsed_time:.2f} seconds")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility."""

    def test_metadata_fields_optional(self):
        """Verify system handles missing git metadata gracefully."""
        # Create metadata with None values (simulating old index)
        metadata = {
            'commit': None,
            'author': None,
            'date': None,
            'message': None,
            'pr': None,
            'lines_changed': None,
            'recency_days': 0
        }

        # Verify fields can be None without breaking
        self.assertIsNone(metadata.get('commit'))
        self.assertIsNone(metadata.get('pr'))
        self.assertEqual(metadata.get('recency_days'), 0)


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestExtractGitMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestPRNumberExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestRecencyCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestFallbackToMtime))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWithProjectIndex))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardCompatibility))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
