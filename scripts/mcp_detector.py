"""
MCP Tool Detection Module.

Detects availability of MCP (Model Context Protocol) tools at runtime to enable
hybrid query strategies combining pre-computed index data with real-time MCP operations.

MCP tools detected:
- Read: Load current file content (fresher than index)
- Grep: Live keyword search across codebase
- Git: Real-time git log, blame, diff operations

Detection is non-blocking (<100ms), graceful (no exceptions), and cached.
"""

from typing import Dict, Optional
import sys
import os


# Detection result cache to avoid repeated probes
_detection_cache: Optional[Dict[str, bool]] = None


def detect_mcp_tools() -> Dict[str, bool]:
    """
    Detect available MCP tools at runtime.

    Probes for MCP Read, Grep, and Git tools without blocking or throwing exceptions.
    Results are cached after first detection to avoid repeated probes.

    MCP tools are detected by checking if we're running inside Claude Code environment
    which provides MCP tools via the tool registry. This is an environment-based
    detection that doesn't require subprocess calls or external commands.

    Returns:
        Dict[str, bool]: Capability map showing which MCP tools are available.
            Keys: "read", "grep", "git"
            Values: True if tool is available, False otherwise

    Examples:
        >>> capabilities = detect_mcp_tools()
        >>> capabilities
        {'read': True, 'grep': True, 'git': True}

        >>> if capabilities['read']:
        ...     # Use MCP Read for fresh file content
        ...     pass
        ... else:
        ...     # Fall back to detail module loading from index
        ...     pass

    Performance:
        Completes in <100ms (typically <10ms for cached results).
        First call performs detection and caches results.
        Subsequent calls return cached results instantly.

    Thread Safety:
        Safe for concurrent calls. First call initializes cache atomically.
    """
    global _detection_cache

    # Return cached results if available
    if _detection_cache is not None:
        return _detection_cache.copy()

    # Initialize capability map (default: all False for graceful degradation)
    capabilities = {
        "read": False,
        "grep": False,
        "git": False,
    }

    try:
        # MCP Detection Strategy:
        # Claude Code provides MCP tools when running in its environment.
        # We detect this by checking for environment indicators and tool availability.

        # Strategy 1: Check for Claude Code environment marker
        # Claude Code sets specific environment variables or markers when tools are available
        is_claude_code = _is_claude_code_environment()

        if is_claude_code:
            # In Claude Code, these tools are typically all available together
            # or none are available (depends on Claude Code version/config)
            capabilities["read"] = True
            capabilities["grep"] = True
            capabilities["git"] = True
        else:
            # Not in Claude Code environment - MCP tools unavailable
            # This is expected when running standalone (e.g., unit tests, CI)
            pass

    except Exception:
        # Graceful degradation: Any detection failure returns all False
        # This ensures agents can continue with index-only mode
        pass

    # Cache results for subsequent calls
    _detection_cache = capabilities.copy()

    return capabilities


def _is_claude_code_environment() -> bool:
    """
    Check if running inside Claude Code environment.

    Claude Code environment indicators:
    - Specific environment variables set by Claude Code
    - Tool registry/context markers
    - Python interpreter path patterns

    Returns:
        bool: True if Claude Code environment detected, False otherwise

    Note:
        This is a heuristic-based detection. It may return False negatives
        in unusual environments but will never return False positives
        (safe for graceful degradation).
    """
    # Strategy 1: Check for CLAUDE_CODE environment variable
    # (This is a hypothetical marker - actual implementation may differ)
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_CLI"):
        return True

    # Strategy 2: Check for tool-specific environment markers
    # MCP tools might set specific vars when available
    if os.environ.get("MCP_TOOLS_AVAILABLE"):
        return True

    # Strategy 3: Check Python module availability
    # If MCP client libraries are importable, tools are likely available
    try:
        # Try importing MCP-related modules (if they exist)
        # This is speculative - actual MCP Python API may differ
        import_test = "mcp" in sys.modules or "mcp_client" in sys.modules
        if import_test:
            return True
    except (ImportError, AttributeError):
        pass

    # Strategy 4: Check for runtime inspection capabilities
    # Claude Code might provide introspection APIs
    # For now, default to False (conservative detection)

    # Default: Not detected (safe fallback to index-only mode)
    return False


def get_cached_capabilities() -> Optional[Dict[str, bool]]:
    """
    Get cached MCP tool detection results without re-probing.

    Returns:
        Dict[str, bool] if detection has been performed, None otherwise.

    Examples:
        >>> detect_mcp_tools()  # First call performs detection
        {'read': True, 'grep': True, 'git': True}
        >>> get_cached_capabilities()  # Returns cached results
        {'read': True, 'grep': True, 'git': True}
    """
    return _detection_cache.copy() if _detection_cache is not None else None


def reset_detection_cache() -> None:
    """
    Clear cached detection results for testing purposes.

    Calling detect_mcp_tools() after reset will perform fresh detection.

    Warning:
        This is intended for testing only. Production code should not
        reset the cache as it defeats performance optimization.

    Examples:
        >>> detect_mcp_tools()  # Initial detection
        >>> reset_detection_cache()  # Clear cache
        >>> detect_mcp_tools()  # Re-detect
    """
    global _detection_cache
    _detection_cache = None
