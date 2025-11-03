"""
Documentation Classifier Module

Classifies markdown documentation files into three tiers (critical, standard, archive)
based on glob pattern matching. Classification enables intelligent documentation loading
and prioritization in the project index.

Tiers:
- critical: Architectural and API docs essential for understanding the system
- standard: Development and setup docs for active developers (DEFAULT)
- archive: Historical and reference documentation (lowest priority)
"""

from pathlib import Path
from typing import Dict, List, Optional

# Default tier classification rules using glob patterns
TIER_RULES: Dict[str, List[str]] = {
    "critical": [
        "README*",
        "ARCHITECTURE*",
        "API*",
        "CONTRIBUTING*",
        "SECURITY*",
        "docs/architecture/*",
        "docs/api/*",
    ],
    "standard": [
        "docs/development/*",
        "docs/setup/*",
        "docs/guides/*",
        "docs/how-to/*",
        "INSTALL*",
        "SETUP*",
    ],
    "archive": [
        "docs/tutorials/*",
        "docs/meetings/*",
        "docs/archive/*",
        "docs/legacy/*",
        "CHANGELOG*",
        "HISTORY*",
    ],
}


def classify_documentation(file_path: Path, config: Optional[Dict] = None) -> str:
    """
    Classify a documentation file into a tier based on pattern matching.

    Args:
        file_path: Path to the documentation file (can be relative or absolute)
        config: Optional configuration dict containing custom 'doc_tiers' rules

    Returns:
        str: Tier name - "critical", "standard", or "archive"

    Examples:
        >>> classify_documentation(Path("README.md"))
        'critical'
        >>> classify_documentation(Path("docs/development/setup.md"))
        'standard'
        >>> classify_documentation(Path("CHANGELOG.md"))
        'archive'
        >>> classify_documentation(Path("random.md"))
        'standard'  # Default fallback
    """
    # Merge custom rules with defaults if provided
    tier_rules = TIER_RULES.copy()
    if config and isinstance(config, dict):
        custom_tiers = config.get("doc_tiers", {})
        if isinstance(custom_tiers, dict):
            # Merge custom rules with defaults (custom takes precedence)
            for tier, patterns in custom_tiers.items():
                if tier in tier_rules and isinstance(patterns, list):
                    # Extend existing tier with custom patterns (custom patterns checked first)
                    tier_rules[tier] = patterns + tier_rules[tier]
                elif isinstance(patterns, list):
                    # Add new custom tier
                    tier_rules[tier] = patterns

    # Convert to Path object if string
    if isinstance(file_path, str):
        file_path = Path(file_path)

    # Normalize path for consistent matching (use as_posix() for forward slashes)
    normalized_path = file_path.as_posix()

    # Check each tier's patterns in priority order: critical, standard, archive
    for tier in ["critical", "standard", "archive"]:
        if tier in tier_rules:
            for pattern in tier_rules[tier]:
                # Use Path.match() for glob pattern matching
                # match() matches from the right, so patterns like "README*" work correctly
                if file_path.match(pattern):
                    return tier

    # Default fallback for unmatched files
    return "standard"
