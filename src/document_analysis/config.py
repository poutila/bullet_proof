#!/usr/bin/env python3
"""Configuration settings for Document Analyzer.

This module centralizes all configuration values to comply with CLAUDE.md
requirements against hardcoded values and magic numbers.
"""

from pathlib import Path
from typing import Any, Final

# File system limits
MAX_FILE_PATH_LENGTH: Final[int] = 255
MAX_FILE_SIZE_MB: Final[int] = 50
DEFAULT_ENCODING: Final[str] = "utf-8"

# Analysis thresholds
SIMILARITY_THRESHOLD_HIGH: Final[float] = 0.95
SIMILARITY_THRESHOLD_MEDIUM: Final[float] = 0.85
SIMILARITY_THRESHOLD_LOW: Final[float] = 0.75
DUPLICATE_THRESHOLD: Final[int] = 85
MIN_CONTENT_LENGTH: Final[int] = 20

# Markdown analysis
MARKDOWN_VALID_EXTENSIONS: Final[frozenset[str]] = frozenset([".md", ".markdown"])
MAX_HEADING_LEVEL: Final[int] = 6
MIN_HEADING_LEVEL: Final[int] = 1
MAX_LINK_LENGTH: Final[int] = 2048

# Pattern matching
DEFAULT_EXCLUDE_PATTERNS: Final[frozenset[str]] = frozenset(
    [
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "*.pyc",
        "*.pyo",
        "*.egg-info",
        ".DS_Store",
        "Thumbs.db",
    ]
)

# File patterns
PYTHON_FILE_PATTERN: Final[str] = "*.py"
MARKDOWN_FILE_PATTERN: Final[str] = "*.md"
ALL_FILE_PATTERN: Final[str] = "*"

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_DEFAULT: Final[str] = "INFO"

# Report settings
REPORT_LINE_WIDTH: Final[int] = 80
REPORT_INDENT_SIZE: Final[int] = 4
MAX_PREVIEW_LENGTH: Final[int] = 100
DEFAULT_REPORT_ENCODING: Final[str] = "utf-8"

# Performance settings
DEFAULT_BATCH_SIZE: Final[int] = 32
MAX_CONCURRENT_OPERATIONS: Final[int] = 10
OPERATION_TIMEOUT_SECONDS: Final[int] = 30
CACHE_SIZE_LIMIT: Final[int] = 1000

# Security settings
ALLOWED_BASE_PATHS: Final[frozenset[Path]] = frozenset(
    [Path(), Path("docs"), Path("planning"), Path("scripts"), Path("tests")]
)

# Model settings (for embeddings)
DEFAULT_MODEL_NAME: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_MAX_LENGTH: Final[int] = 512
EMBEDDING_DIMENSION: Final[int] = 384

# Validation rules
VALIDATION_RULES: Final[dict[str, Any]] = {
    "max_file_size_bytes": MAX_FILE_SIZE_MB * 1024 * 1024,
    "allowed_encodings": ["utf-8", "utf-16", "ascii"],
    "max_path_depth": 10,
    "require_docstrings": True,
    "require_type_hints": True,
}

# Error messages
ERROR_MESSAGES: Final[dict[str, str]] = {
    "path_traversal": "Path traversal attempt detected: {path}",
    "file_too_large": "File exceeds maximum size of {max_size}MB: {path}",
    "invalid_encoding": "Invalid file encoding. Expected {expected}, got {actual}",
    "path_not_allowed": "Path outside allowed directories: {path}",
    "invalid_threshold": "Threshold must be between 0 and 1: {value}",
    "empty_input": "Input cannot be empty: {field}",
    "file_not_found": "File not found: {path}",
    "permission_denied": "Permission denied accessing: {path}",
}

# Success messages (no emojis per CLAUDE.md)
SUCCESS_MESSAGES: Final[dict[str, str]] = {
    "analysis_complete": "Analysis completed successfully",
    "report_generated": "Report generated: {path}",
    "validation_passed": "All validation checks passed",
    "files_processed": "Processed {count} files",
    "duplicates_found": "Found {count} duplicate groups",
}
