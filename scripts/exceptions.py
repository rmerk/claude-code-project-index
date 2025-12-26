#!/usr/bin/env python3
"""
Custom exception hierarchy for project indexing operations.

Provides specific exception types for different failure scenarios,
enabling more granular error handling and better debugging.
"""


class ProjectIndexError(Exception):
    """Base exception for all project index operations.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch all project-index-related errors with
    a single except clause if desired.

    Example:
        try:
            index = generate_index(path)
        except ProjectIndexError as e:
            logger.error(f"Index operation failed: {e}")
    """
    pass


class ConfigurationError(ProjectIndexError):
    """Invalid or missing configuration.

    Raised when:
    - .project-index.json has invalid format
    - Required configuration keys are missing
    - Configuration values are out of valid range

    Example:
        if threshold < 1:
            raise ConfigurationError(
                f"module_threshold must be >= 1, got {threshold}"
            )
    """
    pass


class ParsingError(ProjectIndexError):
    """Failed to parse source file.

    Raised when:
    - File has invalid syntax that prevents parsing
    - File encoding cannot be detected/decoded
    - Parser encounters unexpected structure

    Attributes:
        file_path: Path to the file that failed to parse
        language: Language being parsed (e.g., "python", "typescript")

    Example:
        raise ParsingError(
            f"Failed to parse {file_path}: unexpected token at line 42",
            file_path=file_path,
            language="python"
        )
    """

    def __init__(self, message: str, file_path: str = None, language: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.language = language


class GitMetadataError(ProjectIndexError):
    """Failed to extract git metadata.

    Raised when:
    - Directory is not a git repository
    - Git command fails or times out
    - Git history is corrupted or inaccessible

    Example:
        raise GitMetadataError(
            f"Failed to get commit history for {file_path}: {e}"
        )
    """
    pass


class CacheError(ProjectIndexError):
    """Cache operation failed.

    Raised when:
    - Cache file is corrupted
    - Cache directory cannot be created
    - Cache write fails (disk full, permissions)

    Example:
        raise CacheError(
            f"Failed to save signature cache: {e}"
        )
    """
    pass


class ModuleNotFoundError(ProjectIndexError):
    """Detail module not found.

    Raised when:
    - Requested module doesn't exist in PROJECT_INDEX.d/
    - Module file is missing or inaccessible

    Note: This is distinct from Python's built-in ModuleNotFoundError
    which is for import errors.

    Example:
        raise ModuleNotFoundError(
            f"Module '{module_name}' not found in PROJECT_INDEX.d/"
        )
    """
    pass


class IndexValidationError(ProjectIndexError):
    """Index structure validation failed.

    Raised when:
    - PROJECT_INDEX.json has invalid structure
    - Required fields are missing from index
    - Module hashes don't match expected values

    Example:
        raise IndexValidationError(
            f"Index missing required field: 'modules'"
        )
    """
    pass
