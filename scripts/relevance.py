"""
Temporal awareness and relevance scoring module for PROJECT_INDEX.

This module provides temporal filtering and multi-signal relevance scoring
to help the index-analyzer agent prioritize recently changed files and
identify the most relevant modules for a given query.

Key Components:
- filter_files_by_recency: Filter files by recency threshold (7/30/90 days)
- RelevanceScorer: Multi-signal scoring engine combining explicit refs,
  temporal context, and keyword matching

Author: BMad - Story 2.4: Temporal Awareness Integration
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json


def filter_files_by_recency(
    files: List[str],
    days: int,
    git_metadata: Dict[str, Any]
) -> List[str]:
    """
    Filter files by recency threshold.

    Returns files that have been changed within the specified number of days.
    Files without git metadata are excluded from results (can be handled
    separately with lower priority).

    Args:
        files: List of file paths to filter
        days: Recency threshold in days (e.g., 7, 30, 90)
        git_metadata: Dictionary mapping file paths to git metadata dicts.
                     Each metadata dict should contain 'recency_days' field.

    Returns:
        List of file paths that were changed within the specified time window.
        Files are returned in the same order as input (no sorting by recency).

    Examples:
        >>> metadata = {
        ...     "scripts/main.py": {"recency_days": 2},
        ...     "scripts/old.py": {"recency_days": 45}
        ... }
        >>> filter_files_by_recency(["scripts/main.py", "scripts/old.py"], 7, metadata)
        ['scripts/main.py']

        >>> filter_files_by_recency(["scripts/main.py", "scripts/old.py"], 90, metadata)
        ['scripts/main.py', 'scripts/old.py']
    """
    if not files:
        return []

    if not git_metadata:
        return []

    filtered = []
    for file_path in files:
        # Normalize file path for comparison (remove leading ./ if present)
        normalized_path = file_path.lstrip("./")

        # Check if file has git metadata
        if normalized_path not in git_metadata:
            # Skip files without git metadata (they'll be handled with low priority)
            continue

        metadata = git_metadata[normalized_path]

        # Check if recency_days field exists
        if "recency_days" not in metadata:
            continue

        # Filter by recency threshold
        if metadata["recency_days"] <= days:
            filtered.append(file_path)

    return filtered


class RelevanceScorer:
    """
    Multi-signal relevance scoring engine for module prioritization.

    Combines multiple signals to score module relevance:
    - Explicit file references (10x weight): User @mentions or direct refs
    - Temporal context (5x/2x weight): Recent changes (7d=5x, 30d=2x)
    - Keyword matching (1x weight): Semantic/text matching

    Weights are configurable via .project-index.json or custom config dict.

    Usage:
        scorer = RelevanceScorer()
        query = {"text": "show recent changes", "explicit_refs": []}
        score = scorer.score_module(module, query, git_metadata)
    """

    # Default scoring weights
    DEFAULT_WEIGHTS = {
        "explicit_file_ref": 10.0,  # User @mentions file
        "temporal_recent": 5.0,      # Changed in last 7 days
        "temporal_medium": 2.0,      # Changed in last 30 days
        "keyword_match": 1.0,        # Semantic match
    }

    # Keyword-to-module-type mapping (Story 4.3)
    # Maps query keywords to module type patterns they should boost
    DEFAULT_KEYWORD_BOOSTS = {
        "component": ["components"],
        "vue component": ["components"],
        "react component": ["components"],
        "view": ["views"],
        "page": ["views"],
        "route": ["views"],
        "api": ["api"],
        "endpoint": ["api"],
        "service": ["api"],
        "store": ["stores"],
        "state": ["stores"],
        "vuex": ["stores"],
        "pinia": ["stores"],
        "redux": ["stores"],
        "composable": ["composables"],
        "hook": ["composables"],
        "util": ["utils"],
        "helper": ["utils"],
        "test": ["tests", "test"],
        "spec": ["tests", "test"]
    }

    # Keyword boost multiplier (applied when keyword matches module type)
    KEYWORD_BOOST_MULTIPLIER = 2.0  # 2x boost for keyword matches

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize RelevanceScorer with optional custom weights.

        Args:
            config: Optional configuration dict. Can contain 'temporal_weights'
                   key with weight overrides. If None, defaults are used.

        Examples:
            >>> scorer = RelevanceScorer()  # Use defaults
            >>> custom_config = {"temporal_weights": {"temporal_recent": 8.0}}
            >>> scorer = RelevanceScorer(config=custom_config)  # Custom weights
        """
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.keyword_boosts = self.DEFAULT_KEYWORD_BOOSTS.copy()
        self.boost_multiplier = self.KEYWORD_BOOST_MULTIPLIER

        # Load custom weights from config if provided
        if config and "temporal_weights" in config:
            custom_weights = config["temporal_weights"]
            if isinstance(custom_weights, dict):
                self.weights.update(custom_weights)

        # Load custom keyword boosts from config if provided
        if config and "keyword_boosts" in config:
            custom_boosts = config["keyword_boosts"]
            if isinstance(custom_boosts, dict):
                self.keyword_boosts.update(custom_boosts)

        # Load custom boost multiplier if provided
        if config and "boost_multiplier" in config:
            multiplier = config["boost_multiplier"]
            if isinstance(multiplier, (int, float)) and multiplier > 0:
                self.boost_multiplier = float(multiplier)

    def _parse_module_name(self, module_id: str) -> Dict[str, str]:
        """
        Parse multi-level module name into components.

        Splits module ID on "-" to extract parent, child, and grandchild components.
        Supports three organizational levels:
        - Monolithic: "project"
        - Two-level: "project-src"
        - Three-level: "project-src-components"

        Args:
            module_id: Module identifier string (e.g., "assureptmdashboard-src-components")

        Returns:
            Dict with module name components:
            {
                "parent": str,           # Always present (first component)
                "child": Optional[str],  # Present for 2+ level splits
                "grandchild": Optional[str]  # Present for 3-level splits
            }

        Examples:
            >>> scorer = RelevanceScorer()
            >>> scorer._parse_module_name("assureptmdashboard")
            {'parent': 'assureptmdashboard'}
            >>> scorer._parse_module_name("assureptmdashboard-src")
            {'parent': 'assureptmdashboard', 'child': 'src'}
            >>> scorer._parse_module_name("assureptmdashboard-src-components")
            {'parent': 'assureptmdashboard', 'child': 'src', 'grandchild': 'components'}
        """
        parts = module_id.split("-")
        result = {"parent": parts[0]}

        if len(parts) >= 2:
            result["child"] = parts[1]

        if len(parts) >= 3:
            # Join remaining parts for grandchild (handles cases like "src-components-forms")
            result["grandchild"] = "-".join(parts[2:])

        return result

    def _detect_module_type(self, module_id: str) -> str:
        """
        Detect module type from module name components.

        Analyzes the parsed module name (especially child/grandchild components)
        to determine the module type. Used for keyword-based score boosting.

        Args:
            module_id: Module identifier (e.g., "project-src-components")

        Returns:
            Module type string: "components", "views", "api", "stores",
            "composables", "utils", "tests", or "generic"

        Examples:
            >>> scorer = RelevanceScorer()
            >>> scorer._detect_module_type("project-src-components")
            'components'
            >>> scorer._detect_module_type("project-src-api")
            'api'
            >>> scorer._detect_module_type("project-tests")
            'tests'
            >>> scorer._detect_module_type("scripts")
            'generic'
        """
        # Parse module name to get components
        parsed = self._parse_module_name(module_id)

        # Check grandchild first (most specific), then child, then parent
        components_to_check = []
        if "grandchild" in parsed:
            components_to_check.append(parsed["grandchild"])
        if "child" in parsed:
            components_to_check.append(parsed["child"])
        components_to_check.append(parsed["parent"])

        # Module type patterns (in priority order - check full word boundaries)
        type_patterns = [
            ("components", ["component"]),  # Will match "component" or "components"
            ("views", ["view", "page", "route"]),
            ("api", ["api", "service", "endpoint"]),
            ("stores", ["store", "state", "vuex", "pinia", "redux"]),
            ("composables", ["composable", "hook"]),
            ("utils", ["util", "helper", "lib"]),
            ("tests", ["test", "spec", "__tests__"])
        ]

        # Check each component against type patterns
        for component in components_to_check:
            component_lower = component.lower()
            for type_name, patterns in type_patterns:
                for pattern in patterns:
                    if pattern in component_lower:
                        return type_name

        return "generic"

    def _boost_by_keywords(
        self,
        base_score: float,
        module_id: str,
        query_text: str
    ) -> float:
        """
        Apply keyword-based score boosting for module type matching.

        If query contains keywords that match the module's type (e.g., "component"
        keyword for a "components" module), apply a multiplier boost to the base score.

        Args:
            base_score: Base relevance score before keyword boosting
            module_id: Module identifier (e.g., "project-src-components")
            query_text: Query text to extract keywords from

        Returns:
            Boosted score if keyword matches module type, else base_score unchanged

        Examples:
            >>> scorer = RelevanceScorer()
            >>> # Query "fix component" should boost "project-src-components" module
            >>> scorer._boost_by_keywords(10.0, "project-src-components", "fix component")
            20.0  # 2x boost applied
            >>> # Query "api endpoint" should boost "project-src-api" module
            >>> scorer._boost_by_keywords(10.0, "project-src-api", "api endpoint")
            20.0
            >>> # Non-matching query doesn't boost
            >>> scorer._boost_by_keywords(10.0, "project-src-components", "database query")
            10.0  # No boost
        """
        if not query_text or base_score == 0:
            return base_score

        # Detect module type
        module_type = self._detect_module_type(module_id)

        if module_type == "generic":
            return base_score

        # Normalize query text for matching
        query_lower = query_text.lower()

        # Check if any keywords in query match this module type
        for keyword, module_types in self.keyword_boosts.items():
            if keyword in query_lower and module_type in module_types:
                # Apply boost multiplier
                return base_score * self.boost_multiplier

        return base_score

    def score_module(
        self,
        module: Dict[str, Any],
        query: Dict[str, Any],
        git_metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate relevance score for a module based on multi-signal analysis.

        Args:
            module: Module dict from PROJECT_INDEX.d/ containing:
                   - 'files': List of file paths in module
                   - Optional: 'function_count', 'file_count', etc.
            query: Query dict containing:
                  - 'text': Query text for keyword matching
                  - 'explicit_refs': List of explicitly referenced file paths
                  - Optional: 'temporal_filter': Bool indicating temporal query
            git_metadata: Dict mapping file paths to git metadata dicts
                         with 'recency_days' field

        Returns:
            Combined relevance score (float). Higher scores = more relevant.
            Scores are additive across all signals.

        Examples:
            >>> module = {"files": ["auth/login.py", "auth/logout.py"]}
            >>> query = {"text": "authentication", "explicit_refs": ["auth/login.py"]}
            >>> metadata = {"auth/login.py": {"recency_days": 2}}
            >>> score = scorer.score_module(module, query, metadata)
            >>> score > 10.0  # Explicit ref (10x) + temporal (5x) + keyword (1x)
            True
        """
        if not module or "files" not in module:
            return 0.0

        total_score = 0.0
        module_files = module.get("files", [])
        query_text = query.get("text", "").lower()
        explicit_refs = query.get("explicit_refs", [])

        # Normalize explicit refs for comparison
        normalized_refs = [ref.lstrip("./") for ref in explicit_refs]

        for file_path in module_files:
            normalized_path = file_path.lstrip("./")

            # Signal 1: Explicit file reference (highest priority)
            if normalized_path in normalized_refs:
                total_score += self.weights["explicit_file_ref"]

            # Signal 2: Temporal context (high priority for recent changes)
            if normalized_path in git_metadata:
                metadata = git_metadata[normalized_path]
                if "recency_days" in metadata:
                    recency = metadata["recency_days"]
                    if recency <= 7:
                        total_score += self.weights["temporal_recent"]
                    elif recency <= 30:
                        total_score += self.weights["temporal_medium"]
                    # Files older than 30 days get no temporal boost

            # Signal 3: Keyword matching (medium priority)
            if query_text:
                # Simple keyword matching: check if query text appears in file path
                file_path_lower = normalized_path.lower()
                query_terms = query_text.split()
                for term in query_terms:
                    if term in file_path_lower:
                        total_score += self.weights["keyword_match"]
                        break  # Only count once per file

        return total_score

    def score_all_modules(
        self,
        modules: Dict[str, Dict[str, Any]],
        query: Dict[str, Any],
        git_metadata: Dict[str, Any]
    ) -> List[tuple[str, float]]:
        """
        Score all modules and return sorted by relevance (highest first).

        Applies keyword boosting based on module type matching query keywords.

        Args:
            modules: Dict mapping module names to module dicts
            query: Query dict (see score_module for structure)
            git_metadata: Git metadata dict (see score_module)

        Returns:
            List of (module_name, score) tuples sorted by score descending.
            Only modules with score > 0 are included.

        Examples:
            >>> modules = {
            ...     "scripts": {"files": ["scripts/main.py"]},
            ...     "agents": {"files": ["agents/index.md"]}
            ... }
            >>> query = {"text": "scripts", "explicit_refs": []}
            >>> scored = scorer.score_all_modules(modules, query, {})
            >>> len(scored) > 0
            True
        """
        scored = []
        query_text = query.get("text", "")

        for module_name, module_data in modules.items():
            # Calculate base score from file-level signals
            base_score = self.score_module(module_data, query, git_metadata)

            # Apply keyword boosting based on module type (Story 4.3)
            final_score = self._boost_by_keywords(base_score, module_name, query_text)

            if final_score > 0:
                scored.append((module_name, final_score))

        # Sort by score descending (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
