"""
Git Metadata Extraction Module

Extracts git commit metadata (hash, author, date, PR, lines changed) for files
to enable temporal awareness and recent change tracking in the project index.

This module provides graceful fallback to filesystem modification times when
git is unavailable or files are not tracked.
"""

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def extract_git_metadata(
    file_path: Path,
    root_path: Path,
    cache: Optional[Dict] = None
) -> Dict:
    """
    Extract git metadata for a file with optional caching.

    Args:
        file_path: Path to the file (absolute or relative)
        root_path: Project root path for git commands
        cache: Optional cache dict to store results and avoid duplicate queries

    Returns:
        Dict with keys:
            - commit: str (hash) or None
            - author: str (email) or None
            - date: str (ISO8601 format) or None
            - message: str or None
            - pr: str (PR number only) or None
            - lines_changed: int or None
            - recency_days: int (days since commit/mtime to now)

    Examples:
        >>> meta = extract_git_metadata(Path("src/main.py"), Path("."))
        >>> meta['commit']
        'a3f2b1c5d8e9f0...'
        >>> meta['pr']
        '247'  # Extracted from "Fix bug (#247)" commit message
        >>> meta['recency_days']
        2  # Committed 2 days ago
    """
    # Convert paths to Path objects if needed
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if isinstance(root_path, str):
        root_path = Path(root_path)

    # Generate cache key (relative path)
    try:
        rel_path = str(file_path.relative_to(root_path))
    except ValueError:
        # file_path not under root_path
        rel_path = str(file_path)

    # Check cache first
    if cache is not None and rel_path in cache:
        return cache[rel_path]

    # Try to extract git metadata
    metadata = _extract_from_git(file_path, root_path)

    # Store in cache if provided
    if cache is not None:
        cache[rel_path] = metadata

    return metadata


def _extract_from_git(file_path: Path, root_path: Path) -> Dict:
    """
    Internal function to extract git metadata using git commands.

    Args:
        file_path: Path to the file
        root_path: Project root path

    Returns:
        Dict with git metadata or fallback to mtime
    """
    try:
        # Extract commit info: hash, author email, date, message
        # Format: %H = commit hash, %ae = author email, %aI = ISO8601 date, %s = subject
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%H|%ae|%aI|%s', '--', str(file_path)],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|', 3)  # Split on first 3 pipes only

            if len(parts) == 4:
                commit_hash = parts[0]
                author_email = parts[1]
                commit_date = parts[2]
                commit_message = parts[3]

                # Extract PR number from commit message
                pr_number = _extract_pr_number(commit_message)

                # Extract lines changed using git diff
                lines_changed = _extract_lines_changed(file_path, root_path, commit_hash)

                # Calculate recency in days
                recency_days = _calculate_recency_days(commit_date)

                return {
                    'commit': commit_hash,
                    'author': author_email,
                    'date': commit_date,
                    'message': commit_message,
                    'pr': pr_number,
                    'lines_changed': lines_changed,
                    'recency_days': recency_days
                }

        # No git history for this file or command failed
        return _fallback_to_mtime(file_path)

    except subprocess.TimeoutExpired:
        # Git command timed out
        return _fallback_to_mtime(file_path)
    except FileNotFoundError:
        # Git not installed or not found
        return _fallback_to_mtime(file_path)
    except Exception:
        # Any other error (subprocess error, parsing error, etc.)
        return _fallback_to_mtime(file_path)


def _extract_pr_number(commit_message: str) -> Optional[str]:
    """
    Extract PR/issue number from commit message.

    Looks for patterns like: #123, (#456), PR #789

    Args:
        commit_message: Git commit message

    Returns:
        PR number as string (without #) or None if not found

    Examples:
        >>> _extract_pr_number("Fix bug (#247)")
        '247'
        >>> _extract_pr_number("Update docs PR #456")
        '456'
        >>> _extract_pr_number("No PR here")
        None
    """
    if not commit_message:
        return None

    # Match patterns: #123, (#456), PR #789, etc.
    # Look for # followed by digits, optionally surrounded by parens
    match = re.search(r'#(\d+)', commit_message)
    if match:
        return match.group(1)

    return None


def _extract_lines_changed(
    file_path: Path,
    root_path: Path,
    commit_hash: str
) -> Optional[int]:
    """
    Extract lines changed (added + deleted) using git diff.

    Args:
        file_path: Path to the file
        root_path: Project root path
        commit_hash: Commit hash to check

    Returns:
        Total lines changed (added + deleted) or None if extraction fails
    """
    try:
        # First, check if this is the initial commit (has no parent)
        parent_check = subprocess.run(
            ['git', 'rev-list', '--parents', '-n', '1', commit_hash],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            timeout=5
        )

        # If output has only one hash, it's the initial commit (no parent)
        if parent_check.returncode == 0:
            parts = parent_check.stdout.strip().split()
            if len(parts) == 1:
                # Initial commit - count lines in the file at this commit
                show_result = subprocess.run(
                    ['git', 'show', f'{commit_hash}:{file_path.relative_to(root_path)}'],
                    cwd=str(root_path),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if show_result.returncode == 0:
                    lines = show_result.stdout.count('\n')
                    return lines
                return None

        # Use git diff --numstat to get lines added and deleted
        # Format: "lines_added\tlines_deleted\tfilename"
        # Compare commit with its parent (commit^)
        result = subprocess.run(
            ['git', 'diff', '--numstat', f'{commit_hash}^', commit_hash, '--', str(file_path)],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse numstat output: "5\t3\tpath/to/file.py"
            parts = result.stdout.strip().split('\t')
            if len(parts) >= 2:
                try:
                    lines_added = int(parts[0]) if parts[0] != '-' else 0
                    lines_deleted = int(parts[1]) if parts[1] != '-' else 0
                    return lines_added + lines_deleted
                except ValueError:
                    # Binary file or parse error
                    return None

        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def _calculate_recency_days(date_str: str) -> int:
    """
    Calculate days since the given date to now.

    Args:
        date_str: ISO8601 date string (e.g., "2025-10-29T14:32:00-05:00")

    Returns:
        Integer days since the date (0 if parsing fails)
    """
    try:
        # Parse ISO8601 date
        commit_date = datetime.fromisoformat(date_str)

        # Get current time in UTC
        now = datetime.now(timezone.utc)

        # Ensure commit_date is timezone-aware for comparison
        if commit_date.tzinfo is None:
            # Assume UTC if no timezone info
            commit_date = commit_date.replace(tzinfo=timezone.utc)

        # Calculate difference
        delta = now - commit_date
        return max(0, delta.days)  # Ensure non-negative

    except (ValueError, AttributeError):
        # Date parsing failed
        return 0


def _fallback_to_mtime(file_path: Path) -> Dict:
    """
    Fallback to file modification time when git is unavailable.

    Args:
        file_path: Path to the file

    Returns:
        Dict with mtime-based metadata (commit, author, message set to None)
    """
    try:
        mtime = file_path.stat().st_mtime
        mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        mtime_iso = mtime_dt.isoformat()

        # Calculate recency from mtime
        recency_days = _calculate_recency_days(mtime_iso)

        return {
            'commit': None,
            'author': None,
            'date': mtime_iso,
            'message': None,
            'pr': None,
            'lines_changed': None,
            'recency_days': recency_days
        }

    except (OSError, Exception):
        # File not accessible or other error
        return {
            'commit': None,
            'author': None,
            'date': None,
            'message': None,
            'pr': None,
            'lines_changed': None,
            'recency_days': 0
        }
