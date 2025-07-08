#!/usr/bin/env python3
"""Tests for document_analysis.config module.

Tests all configuration constants and settings according to CLAUDE.md standards.
Ensures all values are properly typed and within expected ranges.
"""

from pathlib import Path
from typing import Any

import pytest

from src.document_analysis.config import (
    ALLOWED_BASE_PATHS,
    ALL_FILE_PATTERN,
    CACHE_SIZE_LIMIT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_ENCODING,
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_MODEL_NAME,
    DEFAULT_REPORT_ENCODING,
    DUPLICATE_THRESHOLD,
    EMBEDDING_DIMENSION,
    ERROR_MESSAGES,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOG_LEVEL_DEFAULT,
    MARKDOWN_FILE_PATTERN,
    MARKDOWN_VALID_EXTENSIONS,
    MAX_CONCURRENT_OPERATIONS,
    MAX_FILE_PATH_LENGTH,
    MAX_FILE_SIZE_MB,
    MAX_HEADING_LEVEL,
    MAX_LINK_LENGTH,
    MAX_PREVIEW_LENGTH,
    MIN_CONTENT_LENGTH,
    MIN_HEADING_LEVEL,
    MODEL_MAX_LENGTH,
    OPERATION_TIMEOUT_SECONDS,
    PYTHON_FILE_PATTERN,
    REPORT_INDENT_SIZE,
    REPORT_LINE_WIDTH,
    SIMILARITY_THRESHOLD_HIGH,
    SIMILARITY_THRESHOLD_LOW,
    SIMILARITY_THRESHOLD_MEDIUM,
    SUCCESS_MESSAGES,
    VALIDATION_RULES,
)


class TestFileSystemLimits:
    """Test file system limit constants."""

    def test_max_file_path_length_valid_value(self) -> None:
        """Test MAX_FILE_PATH_LENGTH has reasonable value."""
        assert isinstance(MAX_FILE_PATH_LENGTH, int)
        assert MAX_FILE_PATH_LENGTH == 255
        assert MAX_FILE_PATH_LENGTH > 0
        assert MAX_FILE_PATH_LENGTH <= 4096  # Reasonable upper limit

    def test_max_file_size_mb_valid_range(self) -> None:
        """Test MAX_FILE_SIZE_MB is within reasonable range."""
        assert isinstance(MAX_FILE_SIZE_MB, int)
        assert MAX_FILE_SIZE_MB == 50
        assert 1 <= MAX_FILE_SIZE_MB <= 1000  # Between 1MB and 1GB

    def test_default_encoding_is_utf8(self) -> None:
        """Test DEFAULT_ENCODING is UTF-8."""
        assert isinstance(DEFAULT_ENCODING, str)
        assert DEFAULT_ENCODING == "utf-8"
        assert DEFAULT_ENCODING in ["utf-8", "utf-16", "ascii"]


class TestAnalysisThresholds:
    """Test analysis threshold constants."""

    def test_similarity_thresholds_valid_range(self) -> None:
        """Test similarity thresholds are in valid range and properly ordered."""
        assert isinstance(SIMILARITY_THRESHOLD_HIGH, float)
        assert isinstance(SIMILARITY_THRESHOLD_MEDIUM, float)
        assert isinstance(SIMILARITY_THRESHOLD_LOW, float)
        
        # Check valid range [0, 1]
        assert 0.0 <= SIMILARITY_THRESHOLD_LOW <= 1.0
        assert 0.0 <= SIMILARITY_THRESHOLD_MEDIUM <= 1.0
        assert 0.0 <= SIMILARITY_THRESHOLD_HIGH <= 1.0
        
        # Check proper ordering
        assert SIMILARITY_THRESHOLD_LOW < SIMILARITY_THRESHOLD_MEDIUM
        assert SIMILARITY_THRESHOLD_MEDIUM < SIMILARITY_THRESHOLD_HIGH

    def test_duplicate_threshold_percentage_range(self) -> None:
        """Test DUPLICATE_THRESHOLD is valid percentage."""
        assert isinstance(DUPLICATE_THRESHOLD, int)
        assert 0 <= DUPLICATE_THRESHOLD <= 100
        assert DUPLICATE_THRESHOLD == 85

    def test_min_content_length_positive(self) -> None:
        """Test MIN_CONTENT_LENGTH is positive."""
        assert isinstance(MIN_CONTENT_LENGTH, int)
        assert MIN_CONTENT_LENGTH > 0
        assert MIN_CONTENT_LENGTH == 20


class TestMarkdownConfiguration:
    """Test markdown-related configuration."""

    def test_markdown_extensions_immutable_set(self) -> None:
        """Test MARKDOWN_VALID_EXTENSIONS is immutable frozenset."""
        assert isinstance(MARKDOWN_VALID_EXTENSIONS, frozenset)
        assert ".md" in MARKDOWN_VALID_EXTENSIONS
        assert ".markdown" in MARKDOWN_VALID_EXTENSIONS
        assert len(MARKDOWN_VALID_EXTENSIONS) == 2

    def test_heading_levels_valid_range(self) -> None:
        """Test heading levels are in valid markdown range."""
        assert isinstance(MIN_HEADING_LEVEL, int)
        assert isinstance(MAX_HEADING_LEVEL, int)
        assert MIN_HEADING_LEVEL == 1
        assert MAX_HEADING_LEVEL == 6
        assert MIN_HEADING_LEVEL < MAX_HEADING_LEVEL

    def test_max_link_length_reasonable(self) -> None:
        """Test MAX_LINK_LENGTH is reasonable for URLs."""
        assert isinstance(MAX_LINK_LENGTH, int)
        assert MAX_LINK_LENGTH == 2048
        assert MAX_LINK_LENGTH >= 255  # Minimum for most URLs


class TestPatternConfiguration:
    """Test pattern matching configuration."""

    def test_exclude_patterns_immutable_set(self) -> None:
        """Test DEFAULT_EXCLUDE_PATTERNS is immutable frozenset."""
        assert isinstance(DEFAULT_EXCLUDE_PATTERNS, frozenset)
        assert "__pycache__" in DEFAULT_EXCLUDE_PATTERNS
        assert ".git" in DEFAULT_EXCLUDE_PATTERNS
        assert len(DEFAULT_EXCLUDE_PATTERNS) > 10

    def test_file_patterns_valid_globs(self) -> None:
        """Test file patterns are valid glob patterns."""
        assert isinstance(PYTHON_FILE_PATTERN, str)
        assert isinstance(MARKDOWN_FILE_PATTERN, str)
        assert isinstance(ALL_FILE_PATTERN, str)
        
        assert PYTHON_FILE_PATTERN == "*.py"
        assert MARKDOWN_FILE_PATTERN == "*.md"
        assert ALL_FILE_PATTERN == "*"

    def test_exclude_patterns_no_dangerous_entries(self) -> None:
        """Test exclude patterns don't contain dangerous entries."""
        # Should not exclude important directories
        assert "src" not in DEFAULT_EXCLUDE_PATTERNS
        assert "tests" not in DEFAULT_EXCLUDE_PATTERNS
        assert "" not in DEFAULT_EXCLUDE_PATTERNS  # Empty string


class TestLoggingConfiguration:
    """Test logging configuration constants."""

    def test_log_format_contains_required_fields(self) -> None:
        """Test LOG_FORMAT contains all required fields."""
        assert isinstance(LOG_FORMAT, str)
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(name)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(message)s" in LOG_FORMAT

    def test_log_date_format_valid(self) -> None:
        """Test LOG_DATE_FORMAT is valid strftime format."""
        assert isinstance(LOG_DATE_FORMAT, str)
        assert LOG_DATE_FORMAT == "%Y-%m-%d %H:%M:%S"
        
        # Test it's a valid format by trying to use it
        from datetime import datetime
        try:
            datetime.now().strftime(LOG_DATE_FORMAT)
        except ValueError:
            pytest.fail("Invalid date format")

    def test_log_level_default_valid(self) -> None:
        """Test LOG_LEVEL_DEFAULT is valid Python log level."""
        assert isinstance(LOG_LEVEL_DEFAULT, str)
        assert LOG_LEVEL_DEFAULT in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert LOG_LEVEL_DEFAULT == "INFO"


class TestReportSettings:
    """Test report generation settings."""

    def test_report_dimensions_reasonable(self) -> None:
        """Test report dimensions are reasonable."""
        assert isinstance(REPORT_LINE_WIDTH, int)
        assert isinstance(REPORT_INDENT_SIZE, int)
        assert isinstance(MAX_PREVIEW_LENGTH, int)
        
        assert 40 <= REPORT_LINE_WIDTH <= 120
        assert 2 <= REPORT_INDENT_SIZE <= 8
        assert 50 <= MAX_PREVIEW_LENGTH <= 500

    def test_report_encoding_valid(self) -> None:
        """Test DEFAULT_REPORT_ENCODING is valid."""
        assert isinstance(DEFAULT_REPORT_ENCODING, str)
        assert DEFAULT_REPORT_ENCODING == "utf-8"


class TestPerformanceSettings:
    """Test performance-related settings."""

    def test_batch_size_reasonable(self) -> None:
        """Test DEFAULT_BATCH_SIZE is reasonable."""
        assert isinstance(DEFAULT_BATCH_SIZE, int)
        assert 1 <= DEFAULT_BATCH_SIZE <= 1000
        assert DEFAULT_BATCH_SIZE == 32

    def test_concurrent_operations_limit(self) -> None:
        """Test MAX_CONCURRENT_OPERATIONS is reasonable."""
        assert isinstance(MAX_CONCURRENT_OPERATIONS, int)
        assert 1 <= MAX_CONCURRENT_OPERATIONS <= 100
        assert MAX_CONCURRENT_OPERATIONS == 10

    def test_operation_timeout_reasonable(self) -> None:
        """Test OPERATION_TIMEOUT_SECONDS is reasonable."""
        assert isinstance(OPERATION_TIMEOUT_SECONDS, int)
        assert 1 <= OPERATION_TIMEOUT_SECONDS <= 300
        assert OPERATION_TIMEOUT_SECONDS == 30

    def test_cache_size_limit_reasonable(self) -> None:
        """Test CACHE_SIZE_LIMIT is reasonable."""
        assert isinstance(CACHE_SIZE_LIMIT, int)
        assert 10 <= CACHE_SIZE_LIMIT <= 10000
        assert CACHE_SIZE_LIMIT == 1000


class TestSecuritySettings:
    """Test security-related settings."""

    def test_allowed_base_paths_immutable(self) -> None:
        """Test ALLOWED_BASE_PATHS is immutable frozenset."""
        assert isinstance(ALLOWED_BASE_PATHS, frozenset)
        assert all(isinstance(p, Path) for p in ALLOWED_BASE_PATHS)

    def test_allowed_base_paths_safe(self) -> None:
        """Test ALLOWED_BASE_PATHS contains only safe paths."""
        allowed_names = {str(p) for p in ALLOWED_BASE_PATHS}
        
        # Should not contain system directories
        dangerous_paths = ["/", "/etc", "/usr", "/bin", "/tmp", "~", ".."]
        for dangerous in dangerous_paths:
            assert dangerous not in allowed_names

    def test_allowed_base_paths_includes_project_dirs(self) -> None:
        """Test ALLOWED_BASE_PATHS includes necessary project directories."""
        path_strings = {str(p) for p in ALLOWED_BASE_PATHS}
        assert "." in path_strings or "" in path_strings  # Current dir
        assert "docs" in path_strings
        assert "tests" in path_strings


class TestModelSettings:
    """Test ML model-related settings."""

    def test_model_name_valid(self) -> None:
        """Test DEFAULT_MODEL_NAME is valid."""
        assert isinstance(DEFAULT_MODEL_NAME, str)
        assert len(DEFAULT_MODEL_NAME) > 0
        assert "/" in DEFAULT_MODEL_NAME  # HuggingFace format

    def test_model_dimensions_valid(self) -> None:
        """Test model dimension settings are valid."""
        assert isinstance(MODEL_MAX_LENGTH, int)
        assert isinstance(EMBEDDING_DIMENSION, int)
        
        assert MODEL_MAX_LENGTH > 0
        assert MODEL_MAX_LENGTH == 512
        
        assert EMBEDDING_DIMENSION > 0
        assert EMBEDDING_DIMENSION == 384


class TestValidationRules:
    """Test validation rules configuration."""

    def test_validation_rules_structure(self) -> None:
        """Test VALIDATION_RULES has expected structure."""
        assert isinstance(VALIDATION_RULES, dict)
        assert "max_file_size_bytes" in VALIDATION_RULES
        assert "allowed_encodings" in VALIDATION_RULES
        assert "max_path_depth" in VALIDATION_RULES

    def test_validation_rules_values_valid(self) -> None:
        """Test validation rule values are valid."""
        assert VALIDATION_RULES["max_file_size_bytes"] == MAX_FILE_SIZE_MB * 1024 * 1024
        assert isinstance(VALIDATION_RULES["allowed_encodings"], list)
        assert "utf-8" in VALIDATION_RULES["allowed_encodings"]
        assert VALIDATION_RULES["max_path_depth"] > 0

    def test_validation_flags_boolean(self) -> None:
        """Test validation flags are boolean."""
        assert isinstance(VALIDATION_RULES["require_docstrings"], bool)
        assert isinstance(VALIDATION_RULES["require_type_hints"], bool)


class TestMessages:
    """Test message constants."""

    def test_error_messages_complete(self) -> None:
        """Test ERROR_MESSAGES contains all required keys."""
        assert isinstance(ERROR_MESSAGES, dict)
        required_keys = [
            "path_traversal",
            "file_too_large",
            "invalid_encoding",
            "path_not_allowed",
            "invalid_threshold",
            "empty_input",
            "file_not_found",
            "permission_denied",
        ]
        for key in required_keys:
            assert key in ERROR_MESSAGES
            assert isinstance(ERROR_MESSAGES[key], str)
            assert len(ERROR_MESSAGES[key]) > 0

    def test_error_messages_have_placeholders(self) -> None:
        """Test error messages have proper placeholders."""
        for key, message in ERROR_MESSAGES.items():
            assert "{" in message, f"Error message '{key}' should have placeholders"
            assert "}" in message, f"Error message '{key}' should have placeholders"

    def test_success_messages_complete(self) -> None:
        """Test SUCCESS_MESSAGES contains expected keys."""
        assert isinstance(SUCCESS_MESSAGES, dict)
        assert len(SUCCESS_MESSAGES) > 0
        
        for key, message in SUCCESS_MESSAGES.items():
            assert isinstance(message, str)
            assert len(message) > 0

    def test_messages_no_emojis(self) -> None:
        """Test messages don't contain emojis (per CLAUDE.md)."""
        import re
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]"
        )
        
        for message in ERROR_MESSAGES.values():
            assert not emoji_pattern.search(message), "Error messages should not contain emojis"
        
        for message in SUCCESS_MESSAGES.values():
            assert not emoji_pattern.search(message), "Success messages should not contain emojis"


class TestConfigurationIntegrity:
    """Test overall configuration integrity."""

    def test_all_constants_are_final(self) -> None:
        """Test that constants use Final type annotation."""
        # This is more of a code review test, but we can check immutability
        import sys
        config_module = sys.modules["src.document_analysis.config"]
        
        # Check that key constants exist and have expected types
        expected_constants = [
            ("MAX_FILE_SIZE_MB", int),
            ("SIMILARITY_THRESHOLD_HIGH", float),
            ("DEFAULT_EXCLUDE_PATTERNS", frozenset),
            ("ERROR_MESSAGES", dict),
        ]
        
        for const_name, expected_type in expected_constants:
            assert hasattr(config_module, const_name)
            value = getattr(config_module, const_name)
            assert isinstance(value, expected_type)

    def test_no_mutable_defaults(self) -> None:
        """Test configuration doesn't use mutable defaults."""
        # Frozensets and tuples for collections
        assert isinstance(DEFAULT_EXCLUDE_PATTERNS, frozenset)
        assert isinstance(MARKDOWN_VALID_EXTENSIONS, frozenset)
        assert isinstance(ALLOWED_BASE_PATHS, frozenset)

    def test_consistent_naming_convention(self) -> None:
        """Test all constants follow UPPER_CASE naming convention."""
        import sys
        config_module = sys.modules["src.document_analysis.config"]
        
        for attr_name in dir(config_module):
            if not attr_name.startswith("_"):  # Skip private attributes
                attr_value = getattr(config_module, attr_name)
                # Check if it's a constant (not a module or function)
                if not callable(attr_value) and not hasattr(attr_value, "__module__"):
                    if attr_name != "Final" and attr_name != "Path" and attr_name != "Any":
                        assert attr_name.isupper(), f"Constant {attr_name} should be UPPER_CASE"

    def test_paths_are_pathlib_objects(self) -> None:
        """Test path-related settings use pathlib.Path."""
        assert all(isinstance(p, Path) for p in ALLOWED_BASE_PATHS)

    def test_encoding_consistency(self) -> None:
        """Test encoding settings are consistent."""
        assert DEFAULT_ENCODING == DEFAULT_REPORT_ENCODING
        assert DEFAULT_ENCODING in VALIDATION_RULES["allowed_encodings"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])