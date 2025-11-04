"""
Test Suite for Impact Analysis Module

Tests the impact analyzer's ability to traverse call graphs, detect circular
dependencies, map functions to file paths, and work with both split and
legacy index formats.

Run tests: python3 -m unittest scripts/test_impact.py -v
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.impact import (
    build_reverse_call_graph,
    analyze_impact,
    map_functions_to_paths,
    format_impact_report,
    load_call_graph_from_index
)


class TestBuildReverseCallGraph(unittest.TestCase):
    """Test reverse call graph construction"""

    def test_simple_call_graph(self):
        """Should build reverse graph from forward edges"""
        call_graph = [
            ["login", "validate"],
            ["register", "validate"],
            ["validate", "check_password"]
        ]

        reverse = build_reverse_call_graph(call_graph)

        self.assertEqual(reverse["validate"], ["login", "register"])
        self.assertEqual(reverse["check_password"], ["validate"])

    def test_empty_call_graph(self):
        """Should return empty dict for empty call graph"""
        reverse = build_reverse_call_graph([])
        self.assertEqual(reverse, {})

    def test_malformed_edges(self):
        """Should skip malformed edges gracefully"""
        call_graph = [
            ["login", "validate"],
            ["incomplete"],  # Malformed
            ["validate", "check_password"],
            []  # Empty
        ]

        reverse = build_reverse_call_graph(call_graph)

        self.assertEqual(reverse["validate"], ["login"])
        self.assertEqual(reverse["check_password"], ["validate"])

    def test_no_duplicates(self):
        """Should not create duplicate callers"""
        call_graph = [
            ["login", "validate"],
            ["login", "validate"],  # Duplicate
        ]

        reverse = build_reverse_call_graph(call_graph)

        self.assertEqual(len(reverse["validate"]), 1)
        self.assertEqual(reverse["validate"], ["login"])


class TestAnalyzeImpact(unittest.TestCase):
    """Test core impact analysis logic"""

    def setUp(self):
        """Create sample call graph for testing"""
        # Graph structure:
        # api_handler → login → validate → check_password
        # api_handler → register → validate
        self.call_graph = [
            ["api_handler", "login"],
            ["api_handler", "register"],
            ["login", "validate"],
            ["register", "validate"],
            ["validate", "check_password"]
        ]

    def test_direct_callers_only(self):
        """Should identify direct callers (depth=1)"""
        result = analyze_impact("validate", self.call_graph)

        self.assertEqual(set(result["direct_callers"]), {"login", "register"})
        self.assertEqual(result["total_affected"], 3)  # login, register, api_handler
        self.assertIn("api_handler", result["indirect_callers"])

    def test_indirect_callers(self):
        """Should traverse multiple levels for indirect callers"""
        result = analyze_impact("check_password", self.call_graph)

        self.assertEqual(result["direct_callers"], ["validate"])
        self.assertEqual(set(result["indirect_callers"]), {"login", "register", "api_handler"})
        self.assertEqual(result["total_affected"], 4)

    def test_max_depth_respected(self):
        """Should respect max_depth parameter"""
        # Create deep graph: A → B → C → D → E
        deep_graph = [
            ["A", "B"],
            ["B", "C"],
            ["C", "D"],
            ["D", "E"]
        ]

        result = analyze_impact("E", deep_graph, max_depth=2)

        # Should only reach depth 2 (D, C)
        self.assertLessEqual(result["depth_reached"], 2)
        self.assertIn("D", result["direct_callers"])
        self.assertIn("C", result["indirect_callers"])
        self.assertNotIn("A", result["indirect_callers"])

    def test_function_not_found(self):
        """Should return empty result for function not in graph"""
        result = analyze_impact("nonexistent", self.call_graph)

        self.assertEqual(result["direct_callers"], [])
        self.assertEqual(result["indirect_callers"], [])
        self.assertEqual(result["total_affected"], 0)
        self.assertIn("message", result)

    def test_empty_call_graph(self):
        """Should handle empty call graph gracefully"""
        result = analyze_impact("login", [])

        self.assertEqual(result["total_affected"], 0)
        self.assertIn("message", result)


class TestCircularDependencies(unittest.TestCase):
    """Test circular dependency detection and handling"""

    def test_simple_cycle(self):
        """Should detect simple cycle: A → B → A"""
        call_graph = [
            ["A", "B"],
            ["B", "A"]
        ]

        result = analyze_impact("A", call_graph)

        # Should visit B once without infinite loop
        self.assertEqual(result["direct_callers"], ["B"])
        self.assertEqual(result["total_affected"], 1)

    def test_complex_cycle(self):
        """Should handle complex cycle: A → B → C → A"""
        call_graph = [
            ["A", "B"],
            ["B", "C"],
            ["C", "A"],
            ["D", "A"]  # External caller
        ]

        result = analyze_impact("A", call_graph)

        # Should visit each node once:
        # Direct callers of A: D and C (depth=1)
        # Indirect: C→B (depth=2), but B→C→A creates cycle (A already visited)
        self.assertIn("B", result["indirect_callers"])
        self.assertIn("C", result["direct_callers"])
        self.assertIn("D", result["direct_callers"])
        # Total: C + D (direct) + B (indirect) = 3
        self.assertEqual(result["total_affected"], 3)

    def test_self_loop(self):
        """Should handle self-referential function"""
        call_graph = [
            ["recursive", "recursive"],
            ["caller", "recursive"]
        ]

        result = analyze_impact("recursive", call_graph)

        # Should not create infinite loop
        self.assertEqual(result["direct_callers"], ["caller"])
        self.assertEqual(result["total_affected"], 1)


class TestFilePathMapping(unittest.TestCase):
    """Test mapping functions to file paths and line numbers"""

    def setUp(self):
        """Create sample index data"""
        self.index_data = {
            "f": {
                "scripts/auth.py": {
                    "funcs": ["login:42", "validate:67", "check_password:89"]
                },
                "scripts/api.py": {
                    "funcs": ["api_handler:15", "register"]
                }
            }
        }

    def test_map_with_line_numbers(self):
        """Should map functions to file paths with line numbers"""
        functions = ["login", "validate"]
        result = map_functions_to_paths(functions, self.index_data)

        self.assertEqual(result["login"], ("scripts/auth.py", 42))
        self.assertEqual(result["validate"], ("scripts/auth.py", 67))

    def test_map_without_line_numbers(self):
        """Should handle functions without line numbers"""
        functions = ["register"]
        result = map_functions_to_paths(functions, self.index_data)

        self.assertEqual(result["register"], ("scripts/api.py", None))

    def test_function_not_in_index(self):
        """Should mark unknown functions"""
        functions = ["nonexistent"]
        result = map_functions_to_paths(functions, self.index_data)

        self.assertEqual(result["nonexistent"], ("unknown", None))

    def test_empty_index(self):
        """Should handle empty index gracefully"""
        functions = ["login"]
        result = map_functions_to_paths(functions, {"f": {}})

        self.assertEqual(result["login"], ("unknown", None))


class TestFormatImpactReport(unittest.TestCase):
    """Test impact report formatting"""

    def test_format_with_file_paths(self):
        """Should format report with file paths"""
        impact_result = {
            "function": "validate",
            "direct_callers": ["login", "register"],
            "indirect_callers": ["api_handler"],
            "depth_reached": 2,
            "total_affected": 3
        }

        index_data = {
            "f": {
                "auth.py": {
                    "funcs": ["login:42", "register:67"]
                },
                "api.py": {
                    "funcs": ["api_handler:15"]
                }
            }
        }

        report = format_impact_report(impact_result, index_data)

        self.assertIn("validate", report)
        self.assertIn("Total affected functions: 3", report)
        self.assertIn("auth.py:42 (login)", report)
        self.assertIn("api.py:15 (api_handler)", report)

    def test_format_without_file_paths(self):
        """Should format report without index data"""
        impact_result = {
            "function": "validate",
            "direct_callers": ["login"],
            "indirect_callers": [],
            "depth_reached": 1,
            "total_affected": 1
        }

        report = format_impact_report(impact_result)

        self.assertIn("validate", report)
        self.assertIn("login", report)
        # Should not have file:line format (e.g., "auth.py:42")
        self.assertNotIn(".py:", report)

    def test_format_empty_result(self):
        """Should format empty result with message"""
        impact_result = {
            "function": "nonexistent",
            "direct_callers": [],
            "indirect_callers": [],
            "depth_reached": 0,
            "total_affected": 0,
            "message": "Function 'nonexistent' not found"
        }

        report = format_impact_report(impact_result)

        self.assertIn("nonexistent", report)
        self.assertIn("not found", report)


class TestDualFormatSupport(unittest.TestCase):
    """Test integration with both split and legacy index formats"""

    def setUp(self):
        """Create temporary test directories"""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: self._cleanup())

    def _cleanup(self):
        """Clean up temp directory"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_from_split_architecture(self):
        """Should load and merge call graphs from split architecture"""
        # Create core index
        core_index = {
            "version": "2.0-split",
            "g": [["A", "B"]],
            "modules": {
                "module1": {"files": []},
                "module2": {"files": []}
            }
        }

        core_path = Path(self.test_dir) / "PROJECT_INDEX.json"
        with open(core_path, "w") as f:
            json.dump(core_index, f)

        # Create detail modules directory
        detail_dir = Path(self.test_dir) / "PROJECT_INDEX.d"
        detail_dir.mkdir()

        # Create detail module with local call graph (must include all required fields)
        module1 = {
            "module_id": "module1",
            "version": "2.0-split",
            "files": {},
            "call_graph_local": [["C", "D"]]
        }
        with open(detail_dir / "module1.json", "w") as f:
            json.dump(module1, f)

        # Patch Path.cwd() to return test directory
        with patch("pathlib.Path.cwd", return_value=Path(self.test_dir)):
            call_graph = load_call_graph_from_index()

        # Should merge core + detail graphs
        self.assertIn(["A", "B"], call_graph)
        self.assertIn(["C", "D"], call_graph)

    def test_load_from_legacy_format(self):
        """Should load call graph from legacy single-file format"""
        # Create legacy index
        legacy_index = {
            "version": "1.0",
            "g": [["A", "B"], ["C", "D"]]
        }

        legacy_path = Path(self.test_dir) / "PROJECT_INDEX.json"
        with open(legacy_path, "w") as f:
            json.dump(legacy_index, f)

        # Patch Path.cwd() to return test directory
        with patch("pathlib.Path.cwd", return_value=Path(self.test_dir)):
            call_graph = load_call_graph_from_index()

        # Should load legacy graph
        self.assertEqual(call_graph, [["A", "B"], ["C", "D"]])

    def test_integration_with_split_index(self):
        """Integration test: Analyze impact using split architecture"""
        # Create realistic split architecture
        core_index = {
            "version": "2.0-split",
            "g": [["api_handler", "login"]],
            "modules": {"auth": {"files": []}},
            "f": {
                "api.py": {"funcs": ["api_handler:15"]},
                "auth.py": {"funcs": ["login:42", "validate:67"]}
            }
        }

        core_path = Path(self.test_dir) / "PROJECT_INDEX.json"
        with open(core_path, "w") as f:
            json.dump(core_index, f)

        detail_dir = Path(self.test_dir) / "PROJECT_INDEX.d"
        detail_dir.mkdir()

        auth_module = {
            "module_id": "auth",
            "version": "2.0-split",
            "files": {},
            "call_graph_local": [["login", "validate"]]
        }
        with open(detail_dir / "auth.json", "w") as f:
            json.dump(auth_module, f)

        # Load and analyze
        with patch("pathlib.Path.cwd", return_value=Path(self.test_dir)):
            call_graph = load_call_graph_from_index()

        result = analyze_impact("validate", call_graph)

        # Should find callers across merged graphs
        self.assertIn("login", result["direct_callers"])
        self.assertIn("api_handler", result["indirect_callers"])

    def test_integration_with_legacy_index(self):
        """Integration test: Analyze impact using legacy format"""
        legacy_index = {
            "version": "1.0",
            "g": [
                ["api_handler", "login"],
                ["login", "validate"]
            ],
            "f": {
                "api.py": {"funcs": ["api_handler:15"]},
                "auth.py": {"funcs": ["login:42", "validate:67"]}
            }
        }

        legacy_path = Path(self.test_dir) / "PROJECT_INDEX.json"
        with open(legacy_path, "w") as f:
            json.dump(legacy_index, f)

        # Load and analyze
        with patch("pathlib.Path.cwd", return_value=Path(self.test_dir)):
            call_graph = load_call_graph_from_index()

        result = analyze_impact("validate", call_graph)

        # Should analyze legacy graph correctly
        self.assertIn("login", result["direct_callers"])
        self.assertIn("api_handler", result["indirect_callers"])


class TestPerformance(unittest.TestCase):
    """Test performance requirements"""

    def test_large_call_graph_performance(self):
        """Should analyze 10,000 function graph in <500ms"""
        # Generate synthetic large call graph
        # Structure: 10,000 functions in a tree (parent calls 2 children)
        call_graph = []
        num_functions = 10000

        for i in range(num_functions // 2):
            parent = f"func_{i}"
            left_child = f"func_{2*i + 1}"
            right_child = f"func_{2*i + 2}"

            if 2*i + 1 < num_functions:
                call_graph.append([parent, left_child])
            if 2*i + 2 < num_functions:
                call_graph.append([parent, right_child])

        # Analyze leaf node (worst case: traverse entire tree)
        target = f"func_{num_functions - 1}"

        start_time = time.time()
        result = analyze_impact(target, call_graph, max_depth=20)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        # Verify performance requirement
        self.assertLess(elapsed, 500, f"Impact analysis took {elapsed:.2f}ms (required: <500ms)")
        self.assertGreater(result["total_affected"], 0)

    def test_deep_traversal_performance(self):
        """Should handle deep traversal efficiently"""
        # Create linear chain: A → B → C → ... (depth 100)
        call_graph = []
        depth = 100

        for i in range(depth - 1):
            call_graph.append([f"func_{i}", f"func_{i+1}"])

        start_time = time.time()
        result = analyze_impact(f"func_{depth-1}", call_graph, max_depth=depth)
        elapsed = (time.time() - start_time) * 1000

        # Should complete quickly even with deep traversal
        self.assertLess(elapsed, 100)
        self.assertEqual(result["total_affected"], depth - 1)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_isolated_function(self):
        """Should handle function with no callers"""
        call_graph = [
            ["A", "B"],
            ["C", "D"]  # Isolated from A-B
        ]

        result = analyze_impact("D", call_graph)

        self.assertEqual(result["direct_callers"], ["C"])
        self.assertEqual(result["indirect_callers"], [])
        self.assertEqual(result["total_affected"], 1)

    def test_multiple_paths_to_same_caller(self):
        """Should deduplicate callers reached via multiple paths"""
        # Diamond: A → B → D, A → C → D
        call_graph = [
            ["A", "B"],
            ["A", "C"],
            ["B", "D"],
            ["C", "D"]
        ]

        result = analyze_impact("D", call_graph)

        # Should count A once, not twice
        self.assertEqual(set(result["direct_callers"]), {"B", "C"})
        self.assertEqual(result["indirect_callers"], ["A"])
        self.assertEqual(result["total_affected"], 3)

    def test_zero_max_depth(self):
        """Should handle max_depth=0 (no traversal)"""
        call_graph = [["A", "B"]]

        result = analyze_impact("B", call_graph, max_depth=0)

        self.assertEqual(result["direct_callers"], [])
        self.assertEqual(result["total_affected"], 0)


def run_all_tests():
    """Run all tests and print summary"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print(f"{'='*70}")

    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1)
