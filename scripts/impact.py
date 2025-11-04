"""
Impact Analysis Module

Analyzes downstream dependencies using call graph data to identify which
functions will be affected by changes to a target function.

This module implements BFS traversal on reverse call graphs to find direct
and indirect callers, supporting safe refactoring decisions.

Usage:
    from scripts.impact import analyze_impact

    call_graph = [["login", "validate"], ["validate", "check_password"]]
    result = analyze_impact("check_password", call_graph, max_depth=10)
    print(f"Total affected: {result['total_affected']}")
"""

from collections import deque, defaultdict
from typing import Dict, List, Tuple, Any, Set, Optional
import json
from pathlib import Path


def build_reverse_call_graph(call_graph: List[List[str]]) -> Dict[str, List[str]]:
    """
    Build reverse call graph from edge list.

    Converts forward call graph (A calls B) to reverse graph (B is called by A)
    for efficient upstream dependency analysis.

    Args:
        call_graph: List of [caller, callee] edges

    Returns:
        Dictionary mapping callees to their list of callers

    Example:
        >>> call_graph = [["login", "validate"], ["validate", "check"]]
        >>> reverse = build_reverse_call_graph(call_graph)
        >>> reverse["validate"]
        ["login"]
        >>> reverse["check"]
        ["validate"]
    """
    reverse_graph: Dict[str, List[str]] = defaultdict(list)

    for edge in call_graph:
        if len(edge) != 2:
            # Skip malformed edges
            continue

        caller, callee = edge[0], edge[1]

        # Build reverse mapping: callee → list of callers
        if caller not in reverse_graph[callee]:
            reverse_graph[callee].append(caller)

    return dict(reverse_graph)


def analyze_impact(
    function_name: str,
    call_graph: List[List[str]],
    max_depth: int = 10
) -> Dict[str, Any]:
    """
    Analyze downstream impact of changing a function.

    Uses BFS traversal on reverse call graph to find all functions that
    directly or indirectly depend on the target function. Handles circular
    dependencies gracefully.

    Args:
        function_name: Target function to analyze
        call_graph: List of [caller, callee] edges
        max_depth: Maximum traversal depth (default: 10)

    Returns:
        Dictionary with keys:
        - direct_callers: List of functions that directly call target (depth=1)
        - indirect_callers: List of functions that indirectly call target (depth>1)
        - depth_reached: Maximum depth traversed
        - total_affected: Total number of affected functions
        - function: Original function name queried

    Example:
        >>> call_graph = [
        ...     ["login", "validate"],
        ...     ["register", "validate"],
        ...     ["api_handler", "login"]
        ... ]
        >>> result = analyze_impact("validate", call_graph)
        >>> result['direct_callers']
        ['login', 'register']
        >>> result['total_affected']
        3  # login, register, api_handler
    """
    # Handle edge cases
    if not call_graph:
        return {
            "function": function_name,
            "direct_callers": [],
            "indirect_callers": [],
            "depth_reached": 0,
            "total_affected": 0,
            "message": "Empty call graph - no dependencies to analyze"
        }

    # Build reverse call graph for efficient upstream traversal
    reverse_graph = build_reverse_call_graph(call_graph)

    # Check if function exists in call graph
    if function_name not in reverse_graph:
        return {
            "function": function_name,
            "direct_callers": [],
            "indirect_callers": [],
            "depth_reached": 0,
            "total_affected": 0,
            "message": f"Function '{function_name}' not found in call graph or has no callers"
        }

    # BFS traversal with cycle detection
    queue: deque = deque([(function_name, 0)])  # (function, depth)
    visited: Set[str] = {function_name}
    direct_callers: List[str] = []
    indirect_callers: List[str] = []
    max_depth_reached = 0

    while queue:
        current_func, current_depth = queue.popleft()

        # Get callers of current function
        if current_func in reverse_graph:
            for caller in reverse_graph[current_func]:
                # Skip if already visited (cycle detection)
                if caller in visited:
                    continue

                next_depth = current_depth + 1

                # Stop if max depth exceeded
                if next_depth > max_depth:
                    continue

                visited.add(caller)
                max_depth_reached = max(max_depth_reached, next_depth)

                # Categorize as direct (depth=1) or indirect (depth>1)
                if next_depth == 1:
                    direct_callers.append(caller)
                else:
                    indirect_callers.append(caller)

                # Add to queue for further traversal
                queue.append((caller, next_depth))

    total_affected = len(direct_callers) + len(indirect_callers)

    return {
        "function": function_name,
        "direct_callers": sorted(direct_callers),
        "indirect_callers": sorted(indirect_callers),
        "depth_reached": max_depth_reached,
        "total_affected": total_affected
    }


def map_functions_to_paths(
    functions: List[str],
    index_data: Dict[str, Any]
) -> Dict[str, Tuple[str, Optional[int]]]:
    """
    Map function names to file paths and line numbers.

    Args:
        functions: List of function names to map
        index_data: Core index or detail module data with 'f' field

    Returns:
        Dictionary mapping function names to (file_path, line_number) tuples

    Example:
        >>> functions = ["login", "validate"]
        >>> index_data = {"f": {"auth.py": {"funcs": ["login:42", "validate:67"]}}}
        >>> map_functions_to_paths(functions, index_data)
        {"login": ("auth.py", 42), "validate": ("auth.py", 67)}
    """
    function_map: Dict[str, Tuple[str, Optional[int]]] = {}

    # Extract file data from index
    files_data = index_data.get("f", {})

    for func_name in functions:
        found = False

        # Search through all files
        for file_path, file_info in files_data.items():
            if not isinstance(file_info, dict):
                continue

            # Check functions list
            funcs = file_info.get("funcs", [])
            for func_sig in funcs:
                # Parse function signature (e.g., "login:42" or "login")
                if ":" in func_sig:
                    name, line_str = func_sig.split(":", 1)
                    try:
                        line_num = int(line_str)
                    except ValueError:
                        line_num = None
                else:
                    name = func_sig
                    line_num = None

                if name == func_name:
                    function_map[func_name] = (file_path, line_num)
                    found = True
                    break

            if found:
                break

        # If not found in files, mark as unknown
        if not found:
            function_map[func_name] = ("unknown", None)

    return function_map


def format_impact_report(
    impact_result: Dict[str, Any],
    index_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format impact analysis result as human-readable report.

    Args:
        impact_result: Result from analyze_impact()
        index_data: Optional index data for file path mapping

    Returns:
        Formatted report string
    """
    func = impact_result["function"]
    direct = impact_result["direct_callers"]
    indirect = impact_result["indirect_callers"]
    total = impact_result["total_affected"]
    depth = impact_result["depth_reached"]

    lines = []
    lines.append(f"Impact Analysis: {func}")
    lines.append("=" * (17 + len(func)))

    if "message" in impact_result:
        lines.append(f"\n{impact_result['message']}")
        return "\n".join(lines)

    lines.append(f"\nTotal affected functions: {total}")
    lines.append(f"Maximum depth traversed: {depth}")

    # Map to file paths if index provided
    path_map = None
    if index_data:
        all_funcs = direct + indirect
        path_map = map_functions_to_paths(all_funcs, index_data)

    # Direct callers
    lines.append(f"\nDirect callers ({len(direct)}):")
    if direct:
        for caller in direct:
            if path_map and caller in path_map:
                file_path, line_num = path_map[caller]
                if line_num:
                    lines.append(f"  - {file_path}:{line_num} ({caller})")
                else:
                    lines.append(f"  - {file_path} ({caller})")
            else:
                lines.append(f"  - {caller}")
    else:
        lines.append("  (none)")

    # Indirect callers
    lines.append(f"\nIndirect callers ({len(indirect)}):")
    if indirect:
        for caller in indirect:
            if path_map and caller in path_map:
                file_path, line_num = path_map[caller]
                if line_num:
                    lines.append(f"  - {file_path}:{line_num} ({caller})")
                else:
                    lines.append(f"  - {file_path} ({caller})")
            else:
                lines.append(f"  - {caller}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def load_call_graph_from_index(index_path: Optional[Path] = None) -> List[List[str]]:
    """
    Load call graph from PROJECT_INDEX.json or split architecture.

    Args:
        index_path: Optional path to index directory (defaults to PROJECT_INDEX.d/)

    Returns:
        Merged call graph as edge list
    """
    # Import here to avoid circular dependency
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from loader import load_detail_module
    except ImportError:
        # Fallback if loader not available
        load_detail_module = None

    # Determine paths
    if index_path is None:
        index_path = Path.cwd() / "PROJECT_INDEX.d"

    call_graph = []
    core_index = {}

    # Try loading from split architecture first
    core_path = Path.cwd() / "PROJECT_INDEX.json"
    if core_path.exists():
        with open(core_path) as f:
            core_index = json.load(f)
            call_graph.extend(core_index.get("g", []))

    # Check if split architecture exists
    if index_path.exists() and index_path.is_dir() and load_detail_module:
        # Load detail modules and merge call graphs
        modules = core_index.get("modules", {})
        for module_name in modules.keys():
            try:
                detail_module = load_detail_module(module_name, index_path)
                local_graph = detail_module.get("call_graph_local", [])
                call_graph.extend(local_graph)
            except Exception:
                # Skip modules that fail to load
                continue

    return call_graph
