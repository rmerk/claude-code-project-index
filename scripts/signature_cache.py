#!/usr/bin/env python3
"""
Persistent signature cache for project indexing.

Caches parsed function/class signatures keyed by (file_path, mtime, size) to avoid
re-parsing unchanged files. This significantly improves performance for subsequent
index generations.

Cache location: .project-index-cache/signatures.json
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Cache format version - bump this when parser output format changes
CACHE_VERSION = "1.0"

# Default cache directory relative to project root
CACHE_DIR = ".project-index-cache"
CACHE_FILE = "signatures.json"


def get_cache_key(file_path: Path) -> str:
    """
    Generate cache key from file path, mtime, and size.

    The key is a hash of the file's path, modification time, and size.
    This ensures the cache is automatically invalidated when a file changes.

    Args:
        file_path: Path to the file

    Returns:
        16-character hex string cache key

    Raises:
        OSError: If file stats cannot be read
    """
    stat = file_path.stat()
    # Include relative path to handle same filename in different directories
    key_data = f"{file_path.resolve()}:{stat.st_mtime}:{stat.st_size}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def get_cache_path(project_root: Path) -> Path:
    """
    Get the full path to the cache file.

    Args:
        project_root: Project root directory

    Returns:
        Path to signatures.json cache file
    """
    return project_root / CACHE_DIR / CACHE_FILE


def load_cache(project_root: Path) -> Dict[str, Any]:
    """
    Load signature cache from disk.

    If the cache file doesn't exist, is corrupted, or has a different version,
    returns an empty cache structure.

    Args:
        project_root: Project root directory

    Returns:
        Cache dictionary with structure:
        {
            "version": str,
            "signatures": {cache_key: signature_dict}
        }
    """
    cache_path = get_cache_path(project_root)

    if not cache_path.exists():
        logger.debug("No cache file found, starting fresh")
        return {"version": CACHE_VERSION, "signatures": {}}

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        # Validate cache version
        if cache.get("version") != CACHE_VERSION:
            logger.info(f"Cache version mismatch (expected {CACHE_VERSION}, "
                       f"got {cache.get('version')}), starting fresh")
            return {"version": CACHE_VERSION, "signatures": {}}

        # Validate structure
        if not isinstance(cache.get("signatures"), dict):
            logger.warning("Invalid cache structure, starting fresh")
            return {"version": CACHE_VERSION, "signatures": {}}

        logger.debug(f"Loaded cache with {len(cache.get('signatures', {}))} entries")
        return cache

    except json.JSONDecodeError as e:
        logger.warning(f"Cache file corrupted ({e}), starting fresh")
        return {"version": CACHE_VERSION, "signatures": {}}
    except OSError as e:
        logger.warning(f"Failed to read cache file ({e}), starting fresh")
        return {"version": CACHE_VERSION, "signatures": {}}


def save_cache(project_root: Path, cache: Dict[str, Any]) -> bool:
    """
    Save signature cache to disk.

    Creates the cache directory if it doesn't exist.

    Args:
        project_root: Project root directory
        cache: Cache dictionary to save

    Returns:
        True if save succeeded, False otherwise
    """
    cache_path = get_cache_path(project_root)

    try:
        # Create cache directory if needed
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Write cache atomically (write to temp, then rename)
        temp_path = cache_path.with_suffix('.json.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, separators=(',', ':'))  # Compact JSON

        # Atomic rename
        temp_path.replace(cache_path)

        logger.debug(f"Saved cache with {len(cache.get('signatures', {}))} entries")
        return True

    except OSError as e:
        logger.warning(f"Failed to save cache: {e}")
        return False


def get_cached_signature(file_path: Path, cache: Dict[str, Any]) -> Optional[Dict]:
    """
    Get cached signature for a file if still valid.

    Args:
        file_path: Path to the file
        cache: Loaded cache dictionary

    Returns:
        Cached signature dictionary, or None if not cached or invalid
    """
    try:
        key = get_cache_key(file_path)
        signature = cache.get("signatures", {}).get(key)
        if signature:
            logger.debug(f"Cache hit for {file_path.name}")
        return signature
    except OSError:
        # File doesn't exist or can't read stats
        return None


def set_cached_signature(file_path: Path, signature: Dict, cache: Dict[str, Any]) -> None:
    """
    Store signature in cache.

    Args:
        file_path: Path to the file
        signature: Parsed signature dictionary
        cache: Cache dictionary to update (modified in place)
    """
    try:
        key = get_cache_key(file_path)
        cache.setdefault("signatures", {})[key] = signature
        logger.debug(f"Cached signature for {file_path.name}")
    except OSError as e:
        logger.warning(f"Failed to cache signature for {file_path}: {e}")


def clear_cache(project_root: Path) -> bool:
    """
    Clear the signature cache.

    Args:
        project_root: Project root directory

    Returns:
        True if cache was cleared, False if it didn't exist or couldn't be deleted
    """
    cache_path = get_cache_path(project_root)

    try:
        if cache_path.exists():
            cache_path.unlink()
            logger.info("Signature cache cleared")
            return True
        return False
    except OSError as e:
        logger.warning(f"Failed to clear cache: {e}")
        return False


def get_cache_stats(project_root: Path) -> Dict[str, Any]:
    """
    Get cache statistics.

    Args:
        project_root: Project root directory

    Returns:
        Dictionary with cache statistics:
        {
            "exists": bool,
            "entries": int,
            "size_bytes": int,
            "version": str
        }
    """
    cache_path = get_cache_path(project_root)

    if not cache_path.exists():
        return {"exists": False, "entries": 0, "size_bytes": 0, "version": None}

    try:
        size = cache_path.stat().st_size
        cache = load_cache(project_root)
        return {
            "exists": True,
            "entries": len(cache.get("signatures", {})),
            "size_bytes": size,
            "version": cache.get("version")
        }
    except OSError:
        return {"exists": True, "entries": 0, "size_bytes": 0, "version": None}
