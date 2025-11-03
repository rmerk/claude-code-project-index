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

        # Load custom weights from config if provided
        if config and "temporal_weights" in config:
            custom_weights = config["temporal_weights"]
            if isinstance(custom_weights, dict):
                self.weights.update(custom_weights)

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
        for module_name, module_data in modules.items():
            score = self.score_module(module_data, query, git_metadata)
            if score > 0:
                scored.append((module_name, score))

        # Sort by score descending (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
