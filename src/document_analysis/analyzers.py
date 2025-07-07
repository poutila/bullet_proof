#!/usr/bin/env python3
"""Document discovery and content loading utilities.

This module provides functions for finding and loading documents with
comprehensive validation and security checks according to CLAUDE.md standards.
"""

import logging
from pathlib import Path

from .config import (
    DEFAULT_ENCODING,
    DEFAULT_EXCLUDE_PATTERNS,
    MARKDOWN_FILE_PATTERN,
)
from .validation import ValidationError, validate_directory_path, validate_file_path, validate_string_input

logger = logging.getLogger(__name__)


def should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """Check if path should be excluded based on patterns.

    Args:
        path: Path to check
        exclude_patterns: List of patterns to exclude

    Returns:
        True if path should be excluded, False otherwise

    Example:
        >>> should_exclude(Path("node_modules/test.md"), ["node_modules"])
        True
    """
    path_str = str(path)
    return any(pattern in path_str for pattern in exclude_patterns)


def find_active_documents(
    root_dir: str | Path | None = None,
    file_pattern: str = MARKDOWN_FILE_PATTERN,
    exclude_patterns: list[str] | None = None,
    verbose: bool = True,
) -> list[Path]:
    """Find all active documents in the project.

    Active documents are those not in excluded directories like not_in_use, .venv, etc.

    Args:
        root_dir: Root directory to search (defaults to current working directory)
        file_pattern: File pattern to match (default: "*.md")
        exclude_patterns: Patterns to exclude (defaults to DEFAULT_EXCLUDE_PATTERNS)
        verbose: Whether to log progress information

    Returns:
        List of Path objects for active documents

    Raises:
        ValidationError: If root_dir validation fails
        OSError: If directory access fails

    Example:
        >>> docs = find_active_documents(Path("."), "*.md", verbose=False)
        >>> len(docs) > 0
        True
    """
    # Validate and set root directory
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        try:
            root_dir = validate_directory_path(root_dir, must_exist=True)
        except ValidationError as e:
            logger.error(f"Invalid root directory: {e}")
            raise

    # Set default exclude patterns if not provided
    if exclude_patterns is None:
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS)

    # Validate file pattern
    try:
        file_pattern = validate_string_input(file_pattern, "file_pattern", max_length=50, pattern=r"^[\w\*\.\-]+$")
    except ValidationError as e:
        logger.error(f"Invalid file pattern: {e}")
        raise

    active_docs: list[Path] = []

    try:
        # Find all files matching pattern
        for path in root_dir.rglob(file_pattern):
            if not should_exclude(path, exclude_patterns) and path.is_file():
                try:
                    # Additional validation for each file
                    validated_path = validate_file_path(path, must_exist=True)
                    active_docs.append(validated_path)
                except ValidationError as e:
                    logger.debug(f"Skipping invalid file {path}: {e}")
                    continue

    except OSError as e:
        logger.error(f"Error accessing directory {root_dir}: {e}")
        raise

    # Sort for consistent output
    active_docs.sort()

    if verbose:
        logger.info(f"Found {len(active_docs)} active documents in {root_dir}")
        logger.info(f"Excluded patterns: {', '.join(exclude_patterns[:5])}...")

    return active_docs


def find_not_in_use_documents(root_dir: str | Path | None = None, file_pattern: str = MARKDOWN_FILE_PATTERN) -> list[Path]:
    """Find all documents in not_in_use directories.

    Args:
        root_dir: Root directory to search (defaults to current working directory)
        file_pattern: File pattern to match (default: "*.md")

    Returns:
        List of Path objects for not_in_use documents

    Raises:
        ValidationError: If input validation fails
        OSError: If directory access fails
    """
    # Validate root directory
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        try:
            root_dir = validate_directory_path(root_dir, must_exist=True)
        except ValidationError as e:
            logger.error(f"Invalid root directory: {e}")
            raise

    # Validate file pattern
    try:
        file_pattern = validate_string_input(file_pattern, "file_pattern", max_length=50, pattern=r"^[\w\*\.\-]+$")
    except ValidationError as e:
        logger.error(f"Invalid file pattern: {e}")
        raise

    not_in_use_docs: list[Path] = []

    try:
        # Find all not_in_use directories
        for not_in_use_dir in root_dir.rglob("not_in_use"):
            if not_in_use_dir.is_dir():
                for doc_path in not_in_use_dir.rglob(file_pattern):
                    if doc_path.is_file():
                        try:
                            validated_path = validate_file_path(doc_path, must_exist=True)
                            not_in_use_docs.append(validated_path)
                        except ValidationError as e:
                            logger.debug(f"Skipping invalid file {doc_path}: {e}")
                            continue

    except OSError as e:
        logger.error(f"Error accessing directory: {e}")
        raise

    # Sort for consistent output
    not_in_use_docs.sort()

    logger.info(f"Found {len(not_in_use_docs)} not_in_use documents")

    return not_in_use_docs


def load_markdown_files(path_list: list[Path], root_dir: str | Path) -> dict[str, str]:
    """Load markdown files and return their content indexed by relative path.

    Args:
        path_list: List of Path objects to load
        root_dir: Root directory for relative path calculation

    Returns:
        Dictionary mapping relative path strings to file contents

    Raises:
        ValidationError: If input validation fails

    Example:
        >>> files = load_markdown_files([Path("README.md")], Path("."))
        >>> isinstance(files, dict)
        True
    """
    # Validate root directory
    try:
        root_dir = validate_directory_path(root_dir, must_exist=True)
    except ValidationError as e:
        logger.error(f"Invalid root directory: {e}")
        raise

    files: dict[str, str] = {}

    for path in path_list:
        try:
            # Validate each path
            validated_path = validate_file_path(path, must_exist=True)

            # Calculate relative path
            try:
                rel_path = validated_path.relative_to(root_dir)
                key = str(rel_path)
            except ValueError:
                # Path is not relative to root_dir, use absolute path
                key = str(validated_path)
                logger.debug(f"Using absolute path for {validated_path}")

            # Load file content with proper encoding
            try:
                content = validated_path.read_text(encoding=DEFAULT_ENCODING, errors="strict")
                files[key] = content
                logger.debug(f"Loaded {key} ({len(content)} chars)")

            except UnicodeDecodeError as e:
                logger.warning(f"Encoding error in {validated_path}: {e}")
                # Try with error handling
                content = validated_path.read_text(encoding=DEFAULT_ENCODING, errors="replace")
                files[key] = content

        except ValidationError as e:
            logger.warning(f"Skipping invalid file {path}: {e}")
            continue
        except OSError as e:
            logger.warning(f"Failed to load {path}: {e}")
            continue

    logger.info(f"Successfully loaded {len(files)} files")
    return files


def count_documents_by_type(root_dir: str | Path | None = None) -> dict[str, int]:
    """Count different types of documents in the project.

    Args:
        root_dir: Root directory to analyze

    Returns:
        Dictionary with counts for different document categories

    Raises:
        ValidationError: If input validation fails
        OSError: If directory access fails
    """
    # Validate root directory
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        try:
            root_dir = validate_directory_path(root_dir, must_exist=True)
        except ValidationError as e:
            logger.error(f"Invalid root directory: {e}")
            raise

    try:
        # Count different document types
        active_docs = find_active_documents(root_dir, verbose=False)
        not_in_use_docs = find_not_in_use_documents(root_dir)

        # Count backup directories
        backup_count = 0
        for backup_dir in root_dir.glob("not_in_use_backup*"):
            if backup_dir.is_dir():
                backup_docs = list(backup_dir.rglob(MARKDOWN_FILE_PATTERN))
                backup_count += len(backup_docs)

        counts = {
            "active_documents": len(active_docs),
            "not_in_use_documents": len(not_in_use_docs),
            "backup_documents": backup_count,
            "total_documents": len(active_docs) + len(not_in_use_docs) + backup_count,
        }

        logger.info(
            f"Document counts - Active: {counts['active_documents']}, "
            f"Not in use: {counts['not_in_use_documents']}, "
            f"Backup: {counts['backup_documents']}"
        )

        return counts

    except (OSError, ValidationError) as e:
        logger.error(f"Error counting documents: {e}")
        raise
