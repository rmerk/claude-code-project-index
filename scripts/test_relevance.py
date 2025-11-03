"""
Unit and integration tests for relevance.py module.

Tests temporal filtering, relevance scoring, and integration with
the index-analyzer agent for temporal awareness capabilities.

Run tests:
    python3 -m unittest scripts/test_relevance.py -v
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts import relevance


class TestFilterFilesByRecency(unittest.TestCase):
    """Test temporal filtering by recency threshold."""

    def test_filter_files_by_7_day_window(self):
        """Verify 7-day filtering returns only recent files."""
        files = ["scripts/main.py", "scripts/old.py", "scripts/ancient.py"]
        git_metadata = {
            "scripts/main.py": {"recency_days": 2},
            "scripts/old.py": {"recency_days": 45},
            "scripts/ancient.py": {"recency_days": 120}
        }

        result = relevance.filter_files_by_recency(files, 7, git_metadata)

        self.assertEqual(len(result), 1)
        self.assertIn("scripts/main.py", result)
        self.assertNotIn("scripts/old.py", result)
        self.assertNotIn("scripts/ancient.py", result)

    def test_filter_files_by_30_day_window(self):
        """Verify 30-day filtering includes medium-aged files."""
        files = ["scripts/recent.py", "scripts/medium.py", "scripts/old.py"]
        git_metadata = {
            "scripts/recent.py": {"recency_days": 5},
            "scripts/medium.py": {"recency_days": 28},
            "scripts/old.py": {"recency_days": 60}
        }

        result = relevance.filter_files_by_recency(files, 30, git_metadata)

        self.assertEqual(len(result), 2)
        self.assertIn("scripts/recent.py", result)
        self.assertIn("scripts/medium.py", result)
        self.assertNotIn("scripts/old.py", result)

    def test_filter_files_by_90_day_window(self):
        """Verify 90-day filtering includes all but very old files."""
        files = ["scripts/a.py", "scripts/b.py", "scripts/c.py"]
        git_metadata = {
            "scripts/a.py": {"recency_days": 10},
            "scripts/b.py": {"recency_days": 80},
            "scripts/c.py": {"recency_days": 150}
        }

        result = relevance.filter_files_by_recency(files, 90, git_metadata)

        self.assertEqual(len(result), 2)
        self.assertIn("scripts/a.py", result)
        self.assertIn("scripts/b.py", result)
        self.assertNotIn("scripts/c.py", result)

    def test_filter_handles_missing_git_metadata(self):
        """Files without git metadata are excluded from results."""
        files = ["scripts/tracked.py", "scripts/untracked.py"]
        git_metadata = {
            "scripts/tracked.py": {"recency_days": 5}
            # scripts/untracked.py has no metadata
        }

        result = relevance.filter_files_by_recency(files, 7, git_metadata)

        self.assertEqual(len(result), 1)
        self.assertIn("scripts/tracked.py", result)
        self.assertNotIn("scripts/untracked.py", result)

    def test_filter_empty_results(self):
        """No files match threshold returns empty list."""
        files = ["scripts/old.py", "scripts/ancient.py"]
        git_metadata = {
            "scripts/old.py": {"recency_days": 45},
            "scripts/ancient.py": {"recency_days": 120}
        }

        result = relevance.filter_files_by_recency(files, 7, git_metadata)

        self.assertEqual(len(result), 0)

    def test_filter_empty_input_files(self):
        """Empty file list returns empty result."""
        result = relevance.filter_files_by_recency([], 7, {})
        self.assertEqual(len(result), 0)

    def test_filter_empty_git_metadata(self):
        """Empty git metadata returns empty result."""
        files = ["scripts/main.py"]
        result = relevance.filter_files_by_recency(files, 7, {})
        self.assertEqual(len(result), 0)

    def test_filter_handles_path_normalization(self):
        """Filter handles leading ./ in file paths."""
        files = ["./scripts/main.py", "scripts/other.py"]
        git_metadata = {
            "scripts/main.py": {"recency_days": 2},
            "scripts/other.py": {"recency_days": 5}
        }

        result = relevance.filter_files_by_recency(files, 7, git_metadata)

        self.assertEqual(len(result), 2)
        self.assertIn("./scripts/main.py", result)
        self.assertIn("scripts/other.py", result)

    def test_filter_boundary_conditions(self):
        """Test exact boundary at threshold (7 days exactly)."""
        files = ["scripts/exact.py", "scripts/just_over.py"]
        git_metadata = {
            "scripts/exact.py": {"recency_days": 7},
            "scripts/just_over.py": {"recency_days": 8}
        }

        result = relevance.filter_files_by_recency(files, 7, git_metadata)

        self.assertEqual(len(result), 1)
        self.assertIn("scripts/exact.py", result)
        self.assertNotIn("scripts/just_over.py", result)


class TestRelevanceScorer(unittest.TestCase):
    """Test multi-signal relevance scoring engine."""

    def setUp(self):
        """Initialize scorer with default weights."""
        self.scorer = relevance.RelevanceScorer()

    def test_explicit_file_ref_highest_score(self):
        """Explicit file references receive 10x weight (highest priority)."""
        module = {"files": ["auth/login.py"]}
        query = {
            "text": "",
            "explicit_refs": ["auth/login.py"]
        }
        git_metadata = {}

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive explicit_file_ref weight (10.0)
        self.assertEqual(score, 10.0)

    def test_temporal_recent_7day_5x_weight(self):
        """Files changed in last 7 days get 5x weight."""
        module = {"files": ["scripts/recent.py"]}
        query = {
            "text": "",
            "explicit_refs": []
        }
        git_metadata = {
            "scripts/recent.py": {"recency_days": 3}
        }

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive temporal_recent weight (5.0)
        self.assertEqual(score, 5.0)

    def test_temporal_medium_30day_2x_weight(self):
        """Files changed in last 30 days (but not 7) get 2x weight."""
        module = {"files": ["scripts/medium.py"]}
        query = {
            "text": "",
            "explicit_refs": []
        }
        git_metadata = {
            "scripts/medium.py": {"recency_days": 20}
        }

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive temporal_medium weight (2.0)
        self.assertEqual(score, 2.0)

    def test_keyword_match_1x_weight(self):
        """Keyword matches get 1x weight."""
        module = {"files": ["auth/login.py"]}
        query = {
            "text": "auth",
            "explicit_refs": []
        }
        git_metadata = {}

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive keyword_match weight (1.0)
        self.assertEqual(score, 1.0)

    def test_combined_scoring_all_signals(self):
        """Multiple signals combine correctly."""
        module = {"files": ["auth/login.py"]}
        query = {
            "text": "auth login",
            "explicit_refs": ["auth/login.py"]
        }
        git_metadata = {
            "auth/login.py": {"recency_days": 2}
        }

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive: explicit (10.0) + temporal_recent (5.0) + keyword (1.0) = 16.0
        self.assertEqual(score, 16.0)

    def test_no_temporal_boost_for_old_files(self):
        """Files older than 30 days receive no temporal boost."""
        module = {"files": ["scripts/old.py"]}
        query = {
            "text": "",
            "explicit_refs": []
        }
        git_metadata = {
            "scripts/old.py": {"recency_days": 60}
        }

        score = self.scorer.score_module(module, query, git_metadata)

        # Should receive no temporal score
        self.assertEqual(score, 0.0)

    def test_score_module_empty_module(self):
        """Empty module returns score of 0."""
        module = {"files": []}
        query = {"text": "test", "explicit_refs": []}
        score = self.scorer.score_module(module, query, {})
        self.assertEqual(score, 0.0)

    def test_score_module_missing_files_key(self):
        """Module without 'files' key returns score of 0."""
        module = {"other_key": "value"}
        query = {"text": "test", "explicit_refs": []}
        score = self.scorer.score_module(module, query, {})
        self.assertEqual(score, 0.0)

    def test_score_multiple_files_in_module(self):
        """Score accumulates across multiple files in module."""
        module = {
            "files": ["auth/login.py", "auth/logout.py", "auth/session.py"]
        }
        query = {
            "text": "auth",
            "explicit_refs": ["auth/login.py"]
        }
        git_metadata = {
            "auth/login.py": {"recency_days": 2},
            "auth/logout.py": {"recency_days": 5}
        }

        score = self.scorer.score_module(module, query, git_metadata)

        # login: explicit (10) + temporal_recent (5) + keyword (1) = 16
        # logout: temporal_recent (5) + keyword (1) = 6  (but keyword only once per file)
        # session: keyword (1)
        # Total should be: 10 + 5 + 1 (login) + 5 (logout temporal) + 0 (logout keyword already counted for "auth")
        # Actually keyword matching counts once per file, so:
        # login: 10 + 5 + 1 = 16
        # logout: 5 + 0 = 5 (keyword already matched for auth in login)
        # Wait, re-reading code: keyword matching checks if ANY query term in file path, counts once per file
        # So: login matches "auth" = +1, logout matches "auth" = +1, session matches "auth" = +1
        # login: explicit(10) + temporal(5) + keyword(1) = 16
        # logout: temporal(5) + keyword(1) = 6
        # session: keyword(1) = 1
        # Total = 16 + 6 + 1 = 23
        self.assertEqual(score, 23.0)


class TestRelevanceScorerConfiguration(unittest.TestCase):
    """Test configurable temporal weights."""

    def test_load_default_weights(self):
        """Default weights used when no config provided."""
        scorer = relevance.RelevanceScorer()
        self.assertEqual(scorer.weights["explicit_file_ref"], 10.0)
        self.assertEqual(scorer.weights["temporal_recent"], 5.0)
        self.assertEqual(scorer.weights["temporal_medium"], 2.0)
        self.assertEqual(scorer.weights["keyword_match"], 1.0)

    def test_load_custom_weights_from_config(self):
        """Custom weights override defaults."""
        config = {
            "temporal_weights": {
                "temporal_recent": 8.0,
                "temporal_medium": 3.0
            }
        }
        scorer = relevance.RelevanceScorer(config=config)

        self.assertEqual(scorer.weights["temporal_recent"], 8.0)
        self.assertEqual(scorer.weights["temporal_medium"], 3.0)
        # Other weights should remain default
        self.assertEqual(scorer.weights["explicit_file_ref"], 10.0)
        self.assertEqual(scorer.weights["keyword_match"], 1.0)

    def test_invalid_config_falls_back_to_defaults(self):
        """Invalid config gracefully falls back to defaults."""
        config = {"temporal_weights": "invalid_not_a_dict"}
        scorer = relevance.RelevanceScorer(config=config)

        # Should use defaults
        self.assertEqual(scorer.weights["temporal_recent"], 5.0)

    def test_empty_config(self):
        """Empty config uses defaults."""
        scorer = relevance.RelevanceScorer(config={})
        self.assertEqual(scorer.weights["temporal_recent"], 5.0)

    def test_custom_weights_affect_scoring(self):
        """Custom weights actually affect score calculation."""
        config = {
            "temporal_weights": {
                "temporal_recent": 10.0  # Double the default
            }
        }
        scorer = relevance.RelevanceScorer(config=config)

        module = {"files": ["scripts/recent.py"]}
        query = {"text": "", "explicit_refs": []}
        git_metadata = {"scripts/recent.py": {"recency_days": 3}}

        score = scorer.score_module(module, query, git_metadata)

        # Should use custom weight (10.0) instead of default (5.0)
        self.assertEqual(score, 10.0)


class TestScoreAllModules(unittest.TestCase):
    """Test scoring and sorting of multiple modules."""

    def setUp(self):
        """Initialize scorer."""
        self.scorer = relevance.RelevanceScorer()

    def test_score_all_modules_sorts_by_relevance(self):
        """Modules are sorted by score descending (highest first)."""
        modules = {
            "low_score": {"files": ["old/file.py"]},
            "high_score": {"files": ["recent/file.py"]},
            "medium_score": {"files": ["medium/file.py"]}
        }
        query = {"text": "", "explicit_refs": []}
        git_metadata = {
            "recent/file.py": {"recency_days": 3},     # 5.0 score
            "medium/file.py": {"recency_days": 20},    # 2.0 score
            "old/file.py": {"recency_days": 60}        # 0.0 score
        }

        scored = self.scorer.score_all_modules(modules, query, git_metadata)

        # Should be sorted: high_score (5.0), medium_score (2.0), low_score excluded (0.0)
        self.assertEqual(len(scored), 2)
        self.assertEqual(scored[0][0], "high_score")
        self.assertEqual(scored[0][1], 5.0)
        self.assertEqual(scored[1][0], "medium_score")
        self.assertEqual(scored[1][1], 2.0)

    def test_score_all_modules_excludes_zero_scores(self):
        """Modules with zero score are excluded from results."""
        modules = {
            "relevant": {"files": ["scripts/relevant.py"]},
            "irrelevant": {"files": ["old/irrelevant.py"]}
        }
        query = {"text": "scripts", "explicit_refs": []}
        git_metadata = {}

        scored = self.scorer.score_all_modules(modules, query, git_metadata)

        # Only "relevant" should be included (keyword match)
        self.assertEqual(len(scored), 1)
        self.assertEqual(scored[0][0], "relevant")

    def test_score_all_modules_empty_input(self):
        """Empty modules dict returns empty list."""
        scored = self.scorer.score_all_modules({}, {"text": "", "explicit_refs": []}, {})
        self.assertEqual(len(scored), 0)


class TestPerformance(unittest.TestCase):
    """Performance validation tests."""

    def test_scoring_1000_modules_under_100ms(self):
        """Scoring 1,000 modules completes in <100ms (AC requirement)."""
        scorer = relevance.RelevanceScorer()

        # Create 1,000 modules with 5 files each
        modules = {}
        git_metadata = {}
        for i in range(1000):
            module_name = f"module_{i}"
            files = [f"src/module_{i}/file_{j}.py" for j in range(5)]
            modules[module_name] = {"files": files}

            # Add git metadata for half the files
            for j in range(0, 5, 2):
                file_path = f"src/module_{i}/file_{j}.py"
                git_metadata[file_path] = {"recency_days": (i % 90) + 1}

        query = {
            "text": "module test",
            "explicit_refs": ["src/module_500/file_0.py"]
        }

        # Measure scoring time
        start_time = time.perf_counter()
        scored = scorer.score_all_modules(modules, query, git_metadata)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Verify performance requirement
        self.assertLess(elapsed_ms, 100.0,
                       f"Scoring took {elapsed_ms:.2f}ms, expected <100ms")

        # Verify results are reasonable
        self.assertGreater(len(scored), 0, "Should have some scored modules")

    def test_filtering_10000_files_under_1s(self):
        """Filtering 10,000 files completes in <1 second."""
        # Create 10,000 files
        files = [f"src/file_{i}.py" for i in range(10000)]
        git_metadata = {
            f"src/file_{i}.py": {"recency_days": (i % 100)}
            for i in range(10000)
        }

        # Measure filtering time
        start_time = time.perf_counter()
        result = relevance.filter_files_by_recency(files, 7, git_metadata)
        end_time = time.perf_counter()

        elapsed_s = end_time - start_time

        # Verify performance
        self.assertLess(elapsed_s, 1.0,
                       f"Filtering took {elapsed_s:.3f}s, expected <1s")

        # Verify correctness (should have ~700 files within 7 days)
        self.assertGreater(len(result), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests with core index structure."""

    def test_end_to_end_temporal_query(self):
        """Full workflow from temporal query to scored results."""
        # Simulate core index structure
        modules = {
            "scripts": {
                "files": ["scripts/main.py", "scripts/util.py"],
                "file_count": 2
            },
            "agents": {
                "files": ["agents/index-analyzer.md"],
                "file_count": 1
            }
        }

        git_metadata = {
            "scripts/main.py": {"recency_days": 2, "commit": "abc123"},
            "scripts/util.py": {"recency_days": 45, "commit": "def456"},
            "agents/index-analyzer.md": {"recency_days": 5, "commit": "ghi789"}
        }

        # Temporal query: "show recent changes"
        query = {
            "text": "recent changes",
            "explicit_refs": [],
            "temporal_filter": True
        }

        # Step 1: Filter files by recency (7 days)
        all_files = []
        for module_data in modules.values():
            all_files.extend(module_data["files"])

        recent_files = relevance.filter_files_by_recency(all_files, 7, git_metadata)

        # Should return only files changed in last 7 days
        self.assertEqual(len(recent_files), 2)
        self.assertIn("scripts/main.py", recent_files)
        self.assertIn("agents/index-analyzer.md", recent_files)
        self.assertNotIn("scripts/util.py", recent_files)

        # Step 2: Score modules for relevance
        scorer = relevance.RelevanceScorer()
        scored_modules = scorer.score_all_modules(modules, query, git_metadata)

        # Both scripts and agents should have scores due to temporal recent files
        self.assertGreater(len(scored_modules), 0)

    def test_integration_with_real_structure(self):
        """Test with realistic PROJECT_INDEX.json structure."""
        # Load actual PROJECT_INDEX.json if available
        index_path = Path(__file__).parent.parent / "PROJECT_INDEX.json"

        if not index_path.exists():
            self.skipTest("PROJECT_INDEX.json not found for integration test")

        with open(index_path, 'r') as f:
            core_index = json.load(f)

        # Verify version supports git metadata
        version = core_index.get("version", "")
        self.assertIn("2.1", version, "Core index should be v2.1-enhanced")

        # Extract modules and git metadata
        modules = core_index.get("modules", {})
        file_metadata = core_index.get("f", {})

        # Build git_metadata dict
        git_metadata = {}
        for file_path, file_data in file_metadata.items():
            if "git" in file_data:
                git_metadata[file_path] = file_data["git"]

        # Run relevance scoring
        scorer = relevance.RelevanceScorer()
        query = {"text": "test", "explicit_refs": []}

        scored = scorer.score_all_modules(modules, query, git_metadata)

        # Verify integration works (should have some scored modules)
        # Not asserting specific counts as index content varies
        self.assertIsInstance(scored, list)


def run_all_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFilterFilesByRecency))
    suite.addTests(loader.loadTestsFromTestCase(TestRelevanceScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestRelevanceScorerConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestScoreAllModules))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
