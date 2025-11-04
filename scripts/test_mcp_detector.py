"""
Comprehensive test suite for MCP tool detection module.

Tests cover:
- Detection with all tools available
- Detection with partial tool availability
- Detection with no tools available
- Performance requirements (<100ms)
- Caching behavior
- Error handling and graceful degradation
- Integration with agent initialization patterns
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import mcp_detector


class TestDetectMCPTools(unittest.TestCase):
    """Test suite for detect_mcp_tools() function."""

    def setUp(self):
        """Reset detection cache before each test."""
        mcp_detector.reset_detection_cache()

    def tearDown(self):
        """Clean up after each test."""
        mcp_detector.reset_detection_cache()

    def test_all_tools_available(self):
        """
        Test detection when all MCP tools are available.

        AC: #1, #2
        Validates that capability map returns True for all tools when
        Claude Code environment is detected.
        """
        # Mock Claude Code environment detection
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            capabilities = mcp_detector.detect_mcp_tools()

            # Verify all tools detected
            self.assertIsInstance(capabilities, dict)
            self.assertIn("read", capabilities)
            self.assertIn("grep", capabilities)
            self.assertIn("git", capabilities)

            self.assertTrue(capabilities["read"], "Read tool should be available")
            self.assertTrue(capabilities["grep"], "Grep tool should be available")
            self.assertTrue(capabilities["git"], "Git tool should be available")

    def test_partial_availability_read_grep_only(self):
        """
        Test detection when only Read and Grep are available (Git missing).

        AC: #1, #2
        Note: Current implementation treats MCP tools as all-or-nothing
        (if Claude Code detected, all tools available). This test documents
        the behavior for potential future granular detection.
        """
        # In current implementation, MCP tools are detected as a bundle
        # If environment is not Claude Code, all return False
        with patch.dict(os.environ, {}, clear=True):
            capabilities = mcp_detector.detect_mcp_tools()

            # All should be False in non-Claude Code environment
            self.assertFalse(capabilities["read"])
            self.assertFalse(capabilities["grep"])
            self.assertFalse(capabilities["git"])

    def test_no_tools_available(self):
        """
        Test detection when no MCP tools are available (non-Claude Code environment).

        AC: #1, #2, #4
        Validates graceful degradation - all tools return False, no exceptions thrown.
        """
        # Clear environment to simulate non-Claude Code environment
        with patch.dict(os.environ, {}, clear=True):
            capabilities = mcp_detector.detect_mcp_tools()

            # Verify graceful degradation (all False, no crash)
            self.assertIsInstance(capabilities, dict)
            self.assertFalse(capabilities["read"], "Read should be unavailable")
            self.assertFalse(capabilities["grep"], "Grep should be unavailable")
            self.assertFalse(capabilities["git"], "Git should be unavailable")

    def test_detection_exception_handling(self):
        """
        Test that detection failures are handled gracefully without crashing.

        AC: #4
        Simulates exception during detection and verifies graceful fallback.
        """
        # Mock environment detection to raise exception
        with patch("mcp_detector._is_claude_code_environment") as mock_detect:
            mock_detect.side_effect = RuntimeError("Simulated detection failure")

            # Should not raise exception - graceful degradation
            capabilities = mcp_detector.detect_mcp_tools()

            # Verify all tools return False (safe fallback)
            self.assertFalse(capabilities["read"])
            self.assertFalse(capabilities["grep"])
            self.assertFalse(capabilities["git"])

    def test_caching_behavior(self):
        """
        Test that detection results are cached after first call.

        AC: #2
        Verifies performance optimization through result caching.
        """
        # First call should perform detection
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            first_result = mcp_detector.detect_mcp_tools()
            self.assertTrue(first_result["read"])

        # Second call should return cached results even if environment changes
        with patch.dict(os.environ, {}, clear=True):
            second_result = mcp_detector.detect_mcp_tools()
            # Should still return True (cached from first call)
            self.assertTrue(second_result["read"])
            self.assertEqual(first_result, second_result)

    def test_get_cached_capabilities(self):
        """
        Test get_cached_capabilities() function.

        AC: #2
        Validates cached result retrieval without re-detection.
        """
        # Before detection, cache should be empty
        cached = mcp_detector.get_cached_capabilities()
        self.assertIsNone(cached, "Cache should be None before first detection")

        # After detection, cache should contain results
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            mcp_detector.detect_mcp_tools()

        cached = mcp_detector.get_cached_capabilities()
        self.assertIsNotNone(cached, "Cache should exist after detection")
        self.assertIn("read", cached)
        self.assertTrue(cached["read"])

    def test_reset_detection_cache(self):
        """
        Test cache reset functionality for testing purposes.

        AC: #2
        Validates that cache can be cleared and re-detection occurs.
        """
        # Initial detection
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            first_result = mcp_detector.detect_mcp_tools()
            self.assertTrue(first_result["read"])

        # Reset cache
        mcp_detector.reset_detection_cache()

        # Verify cache is cleared
        cached = mcp_detector.get_cached_capabilities()
        self.assertIsNone(cached)

        # Re-detection should occur
        with patch.dict(os.environ, {}, clear=True):
            second_result = mcp_detector.detect_mcp_tools()
            # Should reflect new environment (all False)
            self.assertFalse(second_result["read"])

    def test_capability_map_immutability(self):
        """
        Test that returned capability maps are independent copies.

        AC: #2
        Ensures callers cannot mutate internal cache state.
        """
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            capabilities1 = mcp_detector.detect_mcp_tools()
            capabilities2 = mcp_detector.detect_mcp_tools()

            # Mutate first result
            capabilities1["read"] = False

            # Second result should be unaffected
            self.assertTrue(capabilities2["read"])

            # Cache should also be unaffected
            cached = mcp_detector.get_cached_capabilities()
            self.assertTrue(cached["read"])


class TestIsClaudeCodeEnvironment(unittest.TestCase):
    """Test suite for _is_claude_code_environment() internal function."""

    def test_claude_code_env_var(self):
        """Test detection via CLAUDE_CODE environment variable."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            result = mcp_detector._is_claude_code_environment()
            self.assertTrue(result)

    def test_claude_cli_env_var(self):
        """Test detection via CLAUDE_CLI environment variable."""
        with patch.dict(os.environ, {"CLAUDE_CLI": "true"}):
            result = mcp_detector._is_claude_code_environment()
            self.assertTrue(result)

    def test_mcp_tools_available_marker(self):
        """Test detection via MCP_TOOLS_AVAILABLE marker."""
        with patch.dict(os.environ, {"MCP_TOOLS_AVAILABLE": "yes"}):
            result = mcp_detector._is_claude_code_environment()
            self.assertTrue(result)

    def test_no_environment_markers(self):
        """Test detection returns False without environment markers."""
        with patch.dict(os.environ, {}, clear=True):
            result = mcp_detector._is_claude_code_environment()
            self.assertFalse(result)

    def test_module_import_detection(self):
        """Test detection via MCP module availability."""
        # Mock sys.modules to simulate MCP module presence
        with patch.dict(sys.modules, {"mcp": MagicMock()}):
            result = mcp_detector._is_claude_code_environment()
            # Should detect mcp module in sys.modules
            self.assertTrue(result)


class TestPerformance(unittest.TestCase):
    """Performance validation tests for MCP detection."""

    def setUp(self):
        """Reset cache before performance tests."""
        mcp_detector.reset_detection_cache()

    def tearDown(self):
        """Clean up after performance tests."""
        mcp_detector.reset_detection_cache()

    def test_detection_under_100ms(self):
        """
        Test that initial detection completes in <100ms.

        AC: #1, #2
        Performance requirement from tech-spec and story.
        """
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            start_time = time.time()
            mcp_detector.detect_mcp_tools()
            elapsed_ms = (time.time() - start_time) * 1000

            self.assertLess(elapsed_ms, 100,
                          f"Detection took {elapsed_ms:.2f}ms, expected <100ms")

    def test_cached_retrieval_under_10ms(self):
        """
        Test that cached result retrieval is very fast (<10ms).

        AC: #2
        Validates caching performance benefit.
        """
        # Warm up cache
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            mcp_detector.detect_mcp_tools()

        # Measure cached retrieval
        start_time = time.time()
        for _ in range(100):
            mcp_detector.detect_mcp_tools()
        elapsed_ms = (time.time() - start_time) * 1000

        avg_ms = elapsed_ms / 100
        self.assertLess(avg_ms, 10,
                       f"Cached retrieval took {avg_ms:.3f}ms average, expected <10ms")


class TestAgentIntegration(unittest.TestCase):
    """Integration tests simulating agent usage patterns."""

    def setUp(self):
        """Reset cache before integration tests."""
        mcp_detector.reset_detection_cache()

    def tearDown(self):
        """Clean up after integration tests."""
        mcp_detector.reset_detection_cache()

    def test_agent_initialization_pattern(self):
        """
        Test MCP detection in typical agent initialization flow.

        AC: #1, #3
        Simulates index-analyzer agent initialization with MCP detection.
        """
        # Simulate agent initialization
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            # Agent would call detect_mcp_tools() during initialization
            mcp_capabilities = mcp_detector.detect_mcp_tools()

            # Agent stores capability map in context
            agent_context = {
                "mcp_available": mcp_capabilities,
                "query_mode": "hybrid" if mcp_capabilities["read"] else "index-only"
            }

            # Verify agent context contains MCP capabilities
            self.assertIn("mcp_available", agent_context)
            self.assertTrue(agent_context["mcp_available"]["read"])
            self.assertEqual(agent_context["query_mode"], "hybrid")

    def test_verbose_logging_pattern(self):
        """
        Test MCP detection with verbose logging enabled.

        AC: #3
        Simulates agent logging MCP availability status.
        """
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}):
            capabilities = mcp_detector.detect_mcp_tools()

            # Agent would format and log MCP status in verbose mode
            log_message = (
                f"MCP Tools Detected: "
                f"Read={capabilities['read']}, "
                f"Grep={capabilities['grep']}, "
                f"Git={capabilities['git']}"
            )

            # Verify log message format
            self.assertIn("MCP Tools Detected:", log_message)
            self.assertIn("Read=True", log_message)
            self.assertIn("Grep=True", log_message)
            self.assertIn("Git=True", log_message)

    def test_graceful_fallback_to_index_only(self):
        """
        Test agent fallback to index-only mode when MCP unavailable.

        AC: #4
        Simulates agent graceful degradation strategy.
        """
        with patch.dict(os.environ, {}, clear=True):
            capabilities = mcp_detector.detect_mcp_tools()

            # Agent determines query strategy based on capabilities
            if capabilities["read"]:
                query_strategy = "hybrid"  # Use index + MCP Read
            else:
                query_strategy = "index-only"  # Fall back to detail modules

            # Verify fallback behavior
            self.assertEqual(query_strategy, "index-only")

            # Agent should still function (no crash/exception)
            # Verify capability map structure is valid
            self.assertIsInstance(capabilities, dict)
            self.assertIn("read", capabilities)


def run_all_tests():
    """Run all test suites and return exit code."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDetectMCPTools))
    suite.addTests(loader.loadTestsFromTestCase(TestIsClaudeCodeEnvironment))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentIntegration))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code (0 if all passed, 1 if any failures)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
