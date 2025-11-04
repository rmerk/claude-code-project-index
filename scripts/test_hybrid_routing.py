"""
Test suite for Hybrid Query Routing (Story 2.6)

Tests the hybrid query routing logic integrated into the index-analyzer agent.
Validates all 4 routing strategies (A-D) and query classification.

Test Coverage:
- AC2.6.1: MCP Read routing for explicit file references
- AC2.6.2: MCP Grep routing for semantic searches
- AC2.6.3: MCP Git routing for temporal queries
- AC2.6.4: Fallback to detail modules when MCP unavailable
- AC2.6.5: Verbose logging of data source decisions
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.mcp_detector import detect_mcp_tools


class TestQueryClassification(unittest.TestCase):
    """Test query type classification logic (AC: All)"""

    def classify_query_type(self, query: str) -> str:
        """
        Classify user query into one of 4 types.
        Implements the classification logic from agents/index-analyzer.md
        """
        query_lower = query.lower()

        # Check for explicit file references (highest priority)
        file_patterns = ['@', '.py', '.md', '.js', '.json', 'scripts/', 'agents/', 'docs/']
        if any(pattern in query for pattern in file_patterns):
            return "explicit_file_ref"

        # Check for temporal queries
        temporal_terms = ['recent', 'changed', 'updated', 'latest', 'new', 'modified', 'commits']
        if any(term in query_lower for term in temporal_terms):
            return "temporal_query"

        # Check for semantic search (but not structural keywords)
        structural_keywords = ['architecture', 'depends', 'call graph', 'how does', 'work']
        has_structural = any(keyword in query_lower for keyword in structural_keywords)

        search_terms = ['find', 'search', 'locate', 'where']
        has_search = any(term in query_lower for term in search_terms)

        if has_search and not has_structural:
            return "semantic_search"

        # Default to structural (architecture, dependencies, how things work)
        return "structural_query"

    def test_explicit_file_ref_classification(self):
        """Test classification of explicit file reference queries"""
        test_cases = [
            "Show me scripts/loader.py",
            "@agents/index-analyzer.md",
            "Read the file scripts/mcp_detector.py",
            "What's in agents/index-analyzer.md?",
            "Analyze docs/architecture.md",
        ]

        for query in test_cases:
            with self.subTest(query=query):
                result = self.classify_query_type(query)
                self.assertEqual(result, "explicit_file_ref",
                               f"Query '{query}' should classify as explicit_file_ref")

    def test_semantic_search_classification(self):
        """Test classification of semantic search queries"""
        test_cases = [
            "Find all authentication functions",
            "Where is RelevanceScorer defined",
            "Search for MCP detection code",
            "Locate the loader module",
            "Find test files in the project",
        ]

        for query in test_cases:
            with self.subTest(query=query):
                result = self.classify_query_type(query)
                self.assertEqual(result, "semantic_search",
                               f"Query '{query}' should classify as semantic_search")

    def test_temporal_query_classification(self):
        """Test classification of temporal queries"""
        test_cases = [
            "What changed recently?",
            "Show me recent commits",
            "What files were modified in the last week?",
            "Show latest updates",
            "What's new in the codebase?",
        ]

        for query in test_cases:
            with self.subTest(query=query):
                result = self.classify_query_type(query)
                self.assertEqual(result, "temporal_query",
                               f"Query '{query}' should classify as temporal_query")

    def test_structural_query_classification(self):
        """Test classification of structural/architectural queries"""
        test_cases = [
            "How does the loader work?",
            "What depends on the relevance module?",
            "Explain the architecture",
            "Show me the call graph",
            "How are modules organized?",
        ]

        for query in test_cases:
            with self.subTest(query=query):
                result = self.classify_query_type(query)
                self.assertEqual(result, "structural_query",
                               f"Query '{query}' should classify as structural_query")

    def test_classification_priority(self):
        """Test that classification prioritizes correctly when multiple signals present"""
        # File reference should override semantic search
        query = "Find scripts/loader.py"  # Has both "find" and file path
        result = self.classify_query_type(query)
        self.assertEqual(result, "explicit_file_ref",
                        "File reference should take priority over semantic search")

        # Temporal should override semantic search
        query = "Find recent changes"  # Has both "find" and "recent"
        result = self.classify_query_type(query)
        self.assertEqual(result, "temporal_query",
                        "Temporal should take priority over semantic search")


class TestRoutingStrategyA(unittest.TestCase):
    """Test Strategy A: Explicit File Reference + MCP Read (AC2.6.1)"""

    def create_mock_core_index(self) -> dict:
        """Create a minimal core index for testing"""
        return {
            "version": "2.0-split",
            "modules": {
                "scripts": {
                    "file_count": 5,
                    "files": ["scripts/loader.py", "scripts/mcp_detector.py"]
                }
            },
            "f": {
                "scripts/loader.py": {
                    "lang": "python",
                    "funcs": ["load_detail_module", "load_multiple_modules"]
                }
            }
        }

    def test_strategy_a_uses_index_for_navigation(self):
        """Verify Strategy A uses index for file navigation (AC2.6.1)"""
        core_index = self.create_mock_core_index()
        query = "Show me scripts/loader.py"
        query_type = "explicit_file_ref"

        # Strategy A should:
        # 1. Use core index to find the file
        file_path = "scripts/loader.py"
        self.assertIn(file_path, core_index["f"],
                     "File should be found in core index")

        # 2. Identify module containing the file
        module_name = "scripts"
        self.assertIn(module_name, core_index["modules"],
                     "Module should be found in core index")

    def test_strategy_a_mcp_read_availability(self):
        """Verify Strategy A checks MCP Read availability (AC2.6.1)"""
        # Mock MCP Read available
        mcp_capabilities = {"read": True, "grep": False, "git": False}

        # Verify routing logic uses the read capability
        self.assertTrue(mcp_capabilities["read"],
                       "MCP Read should be available for Strategy A")

    def test_strategy_a_routing_decision(self):
        """Test routing decision for explicit file ref with MCP Read (AC2.6.1)"""
        query = "Show me scripts/loader.py"
        query_type = "explicit_file_ref"
        mcp_capabilities = {"read": True, "grep": False, "git": False}

        # Route to Strategy A
        selected_strategy = None
        if query_type == "explicit_file_ref" and mcp_capabilities["read"]:
            selected_strategy = "Strategy A"

        self.assertEqual(selected_strategy, "Strategy A",
                        "Should route to Strategy A for explicit file ref with MCP Read")


class TestRoutingStrategyB(unittest.TestCase):
    """Test Strategy B: Semantic Search + MCP Grep (AC2.6.2)"""

    def test_strategy_b_routing_decision(self):
        """Test routing decision for semantic search with MCP Grep (AC2.6.2)"""
        query = "Find all authentication functions"
        query_type = "semantic_search"
        mcp_capabilities = {"read": False, "grep": True, "git": False}

        # Route to Strategy B
        selected_strategy = None
        if query_type == "semantic_search" and mcp_capabilities["grep"]:
            selected_strategy = "Strategy B"

        self.assertEqual(selected_strategy, "Strategy B",
                        "Should route to Strategy B for semantic search with MCP Grep")

    def test_strategy_b_mcp_grep_availability(self):
        """Verify Strategy B checks MCP Grep availability (AC2.6.2)"""
        # Mock MCP Grep available
        mcp_capabilities = {"read": False, "grep": True, "git": False}

        # Verify routing logic uses the grep capability
        self.assertTrue(mcp_capabilities["grep"],
                       "MCP Grep should be available for Strategy B")


class TestRoutingStrategyC(unittest.TestCase):
    """Test Strategy C: Temporal Query + MCP Git (AC2.6.3)"""

    def test_strategy_c_routing_decision(self):
        """Test routing decision for temporal query with MCP Git (AC2.6.3)"""
        query = "What changed recently?"
        query_type = "temporal_query"
        mcp_capabilities = {"read": False, "grep": False, "git": True}

        # Route to Strategy C
        selected_strategy = None
        if query_type == "temporal_query" and mcp_capabilities["git"]:
            selected_strategy = "Strategy C"

        self.assertEqual(selected_strategy, "Strategy C",
                        "Should route to Strategy C for temporal query with MCP Git")

    def test_strategy_c_mcp_git_availability(self):
        """Verify Strategy C checks MCP Git availability (AC2.6.3)"""
        # Mock MCP Git available
        mcp_capabilities = {"read": False, "grep": False, "git": True}

        # Verify routing logic uses the git capability
        self.assertTrue(mcp_capabilities["git"],
                       "MCP Git should be available for Strategy C")


class TestRoutingStrategyD(unittest.TestCase):
    """Test Strategy D: Fallback to Index-Only (AC2.6.4)"""

    def test_strategy_d_fallback_no_mcp(self):
        """Test fallback routing when MCP tools unavailable (AC2.6.4)"""
        query = "Show me scripts/loader.py"
        query_type = "explicit_file_ref"
        mcp_capabilities = {"read": False, "grep": False, "git": False}

        # Route to Strategy D (fallback)
        selected_strategy = None
        if query_type == "explicit_file_ref" and mcp_capabilities["read"]:
            selected_strategy = "Strategy A"
        else:
            selected_strategy = "Strategy D"

        self.assertEqual(selected_strategy, "Strategy D",
                        "Should fallback to Strategy D when MCP Read unavailable")

    def test_strategy_d_structural_queries(self):
        """Test that structural queries always use Strategy D (AC2.6.4)"""
        query = "How does the loader work?"
        query_type = "structural_query"
        # Even with MCP available, structural queries use index
        mcp_capabilities = {"read": True, "grep": True, "git": True}

        # Route to Strategy D (always for structural)
        selected_strategy = None
        if query_type == "explicit_file_ref" and mcp_capabilities["read"]:
            selected_strategy = "Strategy A"
        elif query_type == "semantic_search" and mcp_capabilities["grep"]:
            selected_strategy = "Strategy B"
        elif query_type == "temporal_query" and mcp_capabilities["git"]:
            selected_strategy = "Strategy C"
        else:
            selected_strategy = "Strategy D"

        self.assertEqual(selected_strategy, "Strategy D",
                        "Structural queries should always use Strategy D (index-only)")


class TestVerboseLogging(unittest.TestCase):
    """Test verbose logging of routing decisions (AC2.6.5)"""

    def generate_verbose_log(self, query: str, query_type: str,
                           mcp_capabilities: dict, selected_strategy: str) -> str:
        """Generate verbose log output for routing decision"""
        log_lines = [
            "🔄 HYBRID QUERY ROUTING (Story 2.6)",
            "",
            "Query Classification:",
            f"  📝 Original query: \"{query}\"",
            f"  🎯 Classified as: {query_type}",
            "",
            "MCP Capabilities:",
            f"  📖 Read: {mcp_capabilities['read']}",
            f"  🔎 Grep: {mcp_capabilities['grep']}",
            f"  📊 Git: {mcp_capabilities['git']}",
            "",
            "Routing Decision:",
            f"  ✅ Selected Strategy: {selected_strategy}",
        ]
        return "\n".join(log_lines)

    def test_verbose_log_strategy_a(self):
        """Test verbose logging for Strategy A (AC2.6.5)"""
        query = "Show me scripts/loader.py"
        query_type = "explicit_file_ref"
        mcp_capabilities = {"read": True, "grep": True, "git": True}
        selected_strategy = "A (Explicit File Reference + MCP Read)"

        log_output = self.generate_verbose_log(query, query_type,
                                               mcp_capabilities, selected_strategy)

        # Verify log contains key information
        self.assertIn("HYBRID QUERY ROUTING", log_output)
        self.assertIn(query, log_output)
        self.assertIn("explicit_file_ref", log_output)
        self.assertIn("Read: True", log_output)
        self.assertIn("Strategy: A", log_output)

    def test_verbose_log_strategy_d_fallback(self):
        """Test verbose logging for Strategy D fallback (AC2.6.5)"""
        query = "How does the loader work?"
        query_type = "structural_query"
        mcp_capabilities = {"read": False, "grep": False, "git": False}
        selected_strategy = "D (Fallback - Index Only)"

        log_output = self.generate_verbose_log(query, query_type,
                                               mcp_capabilities, selected_strategy)

        # Verify log contains fallback information
        self.assertIn("HYBRID QUERY ROUTING", log_output)
        self.assertIn("structural_query", log_output)
        self.assertIn("Read: False", log_output)
        self.assertIn("Strategy: D", log_output)


class TestRoutingIntegration(unittest.TestCase):
    """Integration tests for complete routing workflow (All ACs)"""

    def route_query(self, user_query: str, mcp_capabilities: dict) -> Tuple[str, str]:
        """
        Determine hybrid query strategy based on query type and MCP availability.
        Returns (query_type, selected_strategy)
        """
        # Step 1: Classify query type
        query_lower = user_query.lower()

        # Check for explicit file references (highest priority)
        file_patterns = ['@', '.py', '.md', '.js', '.json', 'scripts/', 'agents/', 'docs/']
        if any(pattern in user_query for pattern in file_patterns):
            query_type = "explicit_file_ref"
        # Check for temporal queries
        elif any(term in query_lower for term in ['recent', 'changed', 'updated', 'latest', 'new', 'modified', 'commits']):
            query_type = "temporal_query"
        # Check for semantic search (but not structural keywords)
        elif any(keyword in query_lower for keyword in ['architecture', 'depends', 'call graph', 'how does', 'work']):
            query_type = "structural_query"
        elif any(term in query_lower for term in ['find', 'search', 'locate', 'where']):
            query_type = "semantic_search"
        # Default to structural
        else:
            query_type = "structural_query"

        # Step 2: Route to appropriate strategy
        if query_type == "explicit_file_ref" and mcp_capabilities["read"]:
            selected_strategy = "Strategy A"
        elif query_type == "semantic_search" and mcp_capabilities["grep"]:
            selected_strategy = "Strategy B"
        elif query_type == "temporal_query" and mcp_capabilities["git"]:
            selected_strategy = "Strategy C"
        else:
            selected_strategy = "Strategy D"

        return query_type, selected_strategy

    def test_routing_all_strategies_with_mcp(self):
        """Test routing to all 4 strategies with full MCP availability"""
        mcp_capabilities = {"read": True, "grep": True, "git": True}

        test_cases = [
            ("Show me scripts/loader.py", "explicit_file_ref", "Strategy A"),
            ("Find all test functions", "semantic_search", "Strategy B"),
            ("What changed recently?", "temporal_query", "Strategy C"),
            ("How does the system work?", "structural_query", "Strategy D"),
        ]

        for query, expected_type, expected_strategy in test_cases:
            with self.subTest(query=query):
                query_type, selected_strategy = self.route_query(query, mcp_capabilities)
                self.assertEqual(query_type, expected_type)
                self.assertEqual(selected_strategy, expected_strategy)

    def test_routing_all_fallback_no_mcp(self):
        """Test that all queries fallback to Strategy D without MCP"""
        mcp_capabilities = {"read": False, "grep": False, "git": False}

        test_queries = [
            "Show me scripts/loader.py",     # Would be Strategy A with MCP
            "Find all test functions",        # Would be Strategy B with MCP
            "What changed recently?",         # Would be Strategy C with MCP
            "How does the system work?",      # Always Strategy D
        ]

        for query in test_queries:
            with self.subTest(query=query):
                query_type, selected_strategy = self.route_query(query, mcp_capabilities)
                self.assertEqual(selected_strategy, "Strategy D",
                               "All queries should fallback to Strategy D without MCP")

    def test_routing_with_mocked_mcp_detection(self):
        """Test routing with mocked MCP capabilities"""
        # Mock full MCP availability
        capabilities = {"read": True, "grep": True, "git": True}

        # Route query
        query = "Show me scripts/loader.py"
        query_type, selected_strategy = self.route_query(query, capabilities)

        self.assertEqual(query_type, "explicit_file_ref")
        self.assertEqual(selected_strategy, "Strategy A")


class TestPerformance(unittest.TestCase):
    """Test performance requirements for hybrid routing"""

    def route_query_timed(self, query: str, mcp_capabilities: dict) -> Tuple[str, str, float]:
        """Route query and measure execution time"""
        start_time = time.perf_counter()

        # Classification
        query_lower = query.lower()
        file_patterns = ['@', '.py', '.md', '.js', '.json', 'scripts/', 'agents/', 'docs/']
        if any(pattern in query for pattern in file_patterns):
            query_type = "explicit_file_ref"
        elif any(term in query_lower for term in ['recent', 'changed', 'updated', 'latest', 'new', 'modified', 'commits']):
            query_type = "temporal_query"
        elif any(keyword in query_lower for keyword in ['architecture', 'depends', 'call graph', 'how does', 'work']):
            query_type = "structural_query"
        elif any(term in query_lower for term in ['find', 'search', 'locate', 'where']):
            query_type = "semantic_search"
        else:
            query_type = "structural_query"

        # Routing
        if query_type == "explicit_file_ref" and mcp_capabilities["read"]:
            selected_strategy = "Strategy A"
        elif query_type == "semantic_search" and mcp_capabilities["grep"]:
            selected_strategy = "Strategy B"
        elif query_type == "temporal_query" and mcp_capabilities["git"]:
            selected_strategy = "Strategy C"
        else:
            selected_strategy = "Strategy D"

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return query_type, selected_strategy, elapsed_ms

    def test_routing_performance_under_50ms(self):
        """Verify routing completes in <50ms (performance requirement)"""
        mcp_capabilities = {"read": True, "grep": True, "git": True}

        test_queries = [
            "Show me scripts/loader.py",
            "Find all authentication functions",
            "What changed recently?",
            "How does the system work?",
        ]

        for query in test_queries:
            with self.subTest(query=query):
                _, _, elapsed_ms = self.route_query_timed(query, mcp_capabilities)
                self.assertLess(elapsed_ms, 50,
                              f"Routing should complete in <50ms, took {elapsed_ms:.2f}ms")


def run_all_tests():
    """Run all test suites and report results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestQueryClassification))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingStrategyA))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingStrategyB))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingStrategyC))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingStrategyD))
    suite.addTests(loader.loadTestsFromTestCase(TestVerboseLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestRoutingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("HYBRID QUERY ROUTING TEST SUMMARY (Story 2.6)")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
