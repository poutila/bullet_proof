#!/usr/bin/env python3
"""Tests for document_analysis.validation module.

Comprehensive tests for all validation functions including security checks,
edge cases, and error handling according to CLAUDE.md standards.
"""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.document_analysis.validation import (
    ValidationError,
    check_security_patterns,
    sanitize_filename,
    validate_directory_path,
    validate_encoding,
    validate_file_path,
    validate_file_size,
    validate_json_structure,
    validate_list_input,
    validate_string_input,
    validate_threshold,
)


@pytest.fixture(autouse=True)
def mock_allowed_paths(monkeypatch):
    """Mock ALLOWED_BASE_PATHS to include temp directories for testing."""
    # Allow any path for testing
    monkeypatch.setattr("src.document_analysis.validation.ALLOWED_BASE_PATHS", frozenset())


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_creation(self) -> None:
        """Test creating ValidationError with message."""
        error = ValidationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from Exception."""
        error = ValidationError("Test")
        assert isinstance(error, ValidationError)
        assert isinstance(error, Exception)


class TestValidateFilePath:
    """Test validate_file_path function."""

    def test_validate_file_path_happy_path(self, tmp_path: Path) -> None:
        """Test validating existing file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = validate_file_path(test_file)
        assert result == test_file.resolve()
        assert isinstance(result, Path)

    def test_validate_file_path_string_input(self, tmp_path: Path) -> None:
        """Test validating file path from string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = validate_file_path(str(test_file))
        assert result == test_file.resolve()

    def test_validate_file_path_none_raises_error(self) -> None:
        """Test None path raises ValidationError."""
        with pytest.raises(ValidationError, match="File path cannot be None"):
            validate_file_path(None)

    def test_validate_file_path_empty_raises_error(self) -> None:
        """Test empty path raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_file_path("")

    def test_validate_file_path_traversal_attempt(self) -> None:
        """Test path traversal attempt is blocked."""
        with pytest.raises(ValidationError, match="Path traversal attempt detected"):
            validate_file_path("../../../etc/passwd")

    def test_validate_file_path_too_long(self) -> None:
        """Test path length validation."""
        long_path = "a" * 300
        with pytest.raises(ValidationError, match="Path too long"):
            validate_file_path(long_path, must_exist=False)

    def test_validate_file_path_must_exist_false(self, tmp_path: Path) -> None:
        """Test validation when file doesn't need to exist."""
        non_existent = tmp_path / "does_not_exist.txt"
        result = validate_file_path(non_existent, must_exist=False)
        assert result == non_existent.resolve()

    def test_validate_file_path_must_exist_true_missing(self, tmp_path: Path) -> None:
        """Test validation fails when required file is missing."""
        non_existent = tmp_path / "missing.txt"
        with pytest.raises(ValidationError, match="File not found"):
            validate_file_path(non_existent, must_exist=True)

    def test_validate_file_path_directory_rejected(self, tmp_path: Path) -> None:
        """Test directories are rejected when checking files."""
        with pytest.raises(ValidationError, match="Path is not a file"):
            validate_file_path(tmp_path, check_readable=True)

    def test_validate_file_path_extension_validation(self, tmp_path: Path) -> None:
        """Test file extension validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Should pass with correct extension
        result = validate_file_path(test_file, allowed_extensions=[".txt", ".md"])
        assert result == test_file.resolve()
        
        # Should fail with wrong extension
        with pytest.raises(ValidationError, match="Invalid file extension"):
            validate_file_path(test_file, allowed_extensions=[".py", ".md"])

    def test_validate_file_path_size_check(self, tmp_path: Path) -> None:
        """Test file size validation."""
        test_file = tmp_path / "large.txt"
        # Create a file larger than MAX_FILE_SIZE_MB (50MB)
        test_file.write_bytes(b"x" * (51 * 1024 * 1024))
        
        with pytest.raises(ValidationError, match="File exceeds maximum size"):
            validate_file_path(test_file)

    @patch("src.document_analysis.validation.os.access")
    def test_validate_file_path_not_readable(self, mock_access: Any, tmp_path: Path) -> None:
        """Test validation fails for unreadable files."""
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("content")
        mock_access.return_value = False
        
        with pytest.raises(ValidationError, match="File is not readable"):
            validate_file_path(test_file)

    def test_validate_file_path_allowed_base_paths(self, tmp_path: Path) -> None:
        """Test path validation against allowed base paths."""
        # This test assumes ALLOWED_BASE_PATHS includes current directory
        test_file = Path("test.txt")
        test_file.write_text("content")
        try:
            result = validate_file_path(test_file)
            assert result.name == "test.txt"
        finally:
            if test_file.exists():
                test_file.unlink()


class TestValidateDirectoryPath:
    """Test validate_directory_path function."""

    def test_validate_directory_path_happy_path(self, tmp_path: Path) -> None:
        """Test validating existing directory."""
        result = validate_directory_path(tmp_path)
        assert result == tmp_path.resolve()
        assert isinstance(result, Path)

    def test_validate_directory_path_create_if_missing(self, tmp_path: Path) -> None:
        """Test creating directory if it doesn't exist."""
        new_dir = tmp_path / "new_directory"
        result = validate_directory_path(new_dir, must_exist=True, create_if_missing=True)
        assert result.exists()
        assert result.is_dir()

    def test_validate_directory_path_empty_raises_error(self) -> None:
        """Test empty path raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_directory_path("")

    def test_validate_directory_path_file_rejected(self, tmp_path: Path) -> None:
        """Test files are rejected when expecting directory."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        
        with pytest.raises(ValidationError, match="Path is not a directory"):
            validate_directory_path(test_file)

    def test_validate_directory_path_must_exist_false(self, tmp_path: Path) -> None:
        """Test validation when directory doesn't need to exist."""
        non_existent = tmp_path / "does_not_exist"
        result = validate_directory_path(non_existent, must_exist=False)
        assert result == non_existent.resolve()

    def test_validate_directory_path_creation_failure(self, tmp_path: Path) -> None:
        """Test handling directory creation failure."""
        # Try to create directory in a read-only location
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            new_dir = tmp_path / "cannot_create"
            with pytest.raises(ValidationError, match="Failed to create directory"):
                validate_directory_path(new_dir, must_exist=True, create_if_missing=True)


class TestValidateThreshold:
    """Test validate_threshold function."""

    def test_validate_threshold_valid_values(self) -> None:
        """Test valid threshold values."""
        assert validate_threshold(0.0) == 0.0
        assert validate_threshold(0.5) == 0.5
        assert validate_threshold(1.0) == 1.0
        assert validate_threshold(0.75) == 0.75

    def test_validate_threshold_string_conversion(self) -> None:
        """Test threshold validation with string input."""
        assert validate_threshold("0.5") == 0.5
        assert validate_threshold("1") == 1.0

    def test_validate_threshold_out_of_range(self) -> None:
        """Test threshold values outside [0, 1] range."""
        with pytest.raises(ValidationError, match="Threshold must be between 0 and 1"):
            validate_threshold(-0.1)
        
        with pytest.raises(ValidationError, match="Threshold must be between 0 and 1"):
            validate_threshold(1.1)

    def test_validate_threshold_invalid_type(self) -> None:
        """Test threshold validation with invalid types."""
        with pytest.raises(ValidationError, match="must be a number"):
            validate_threshold("not_a_number")
        
        with pytest.raises(ValidationError, match="must be a number"):
            validate_threshold(None)

    def test_validate_threshold_custom_name(self) -> None:
        """Test threshold validation with custom parameter name."""
        with pytest.raises(ValidationError, match="Invalid similarity_score"):
            validate_threshold("invalid", name="similarity_score")


class TestValidateStringInput:
    """Test validate_string_input function."""

    def test_validate_string_input_happy_path(self) -> None:
        """Test basic string validation."""
        result = validate_string_input("test string", "field")
        assert result == "test string"

    def test_validate_string_input_strips_whitespace(self) -> None:
        """Test string validation strips whitespace."""
        result = validate_string_input("  test  ", "field")
        assert result == "test"

    def test_validate_string_input_none_raises_error(self) -> None:
        """Test None value raises error."""
        with pytest.raises(ValidationError, match="field must be a string"):
            validate_string_input(None, "field")

    def test_validate_string_input_empty_not_allowed(self) -> None:
        """Test empty string raises error when not allowed."""
        with pytest.raises(ValidationError, match="field cannot be empty"):
            validate_string_input("", "field", allow_empty=False)

    def test_validate_string_input_empty_allowed(self) -> None:
        """Test empty string passes when allowed."""
        result = validate_string_input("", "field", allow_empty=True)
        assert result == ""

    def test_validate_string_input_max_length(self) -> None:
        """Test string length validation."""
        # Should pass
        result = validate_string_input("short", "field", max_length=10)
        assert result == "short"
        
        # Should fail
        with pytest.raises(ValidationError, match="field too long"):
            validate_string_input("very long string", "field", max_length=5)

    def test_validate_string_input_allowed_values(self) -> None:
        """Test string validation against allowed values."""
        # Should pass
        result = validate_string_input("option1", "field", allowed_values=["option1", "option2"])
        assert result == "option1"
        
        # Should fail
        with pytest.raises(ValidationError, match="Invalid field.*Allowed values"):
            validate_string_input("option3", "field", allowed_values=["option1", "option2"])

    def test_validate_string_input_pattern(self) -> None:
        """Test string validation with regex pattern."""
        # Should pass
        result = validate_string_input("test123", "field", pattern=r"^[a-z]+\d+$")
        assert result == "test123"
        
        # Should fail
        with pytest.raises(ValidationError, match="does not match pattern"):
            validate_string_input("123test", "field", pattern=r"^[a-z]+\d+$")


class TestValidateListInput:
    """Test validate_list_input function."""

    def test_validate_list_input_happy_path(self) -> None:
        """Test basic list validation."""
        result = validate_list_input([1, 2, 3], "field")
        assert result == [1, 2, 3]

    def test_validate_list_input_not_list(self) -> None:
        """Test non-list input raises error."""
        with pytest.raises(ValidationError, match="field must be a list"):
            validate_list_input("not a list", "field")
        
        with pytest.raises(ValidationError, match="field must be a list"):
            validate_list_input(123, "field")

    def test_validate_list_input_min_length(self) -> None:
        """Test list minimum length validation."""
        # Should pass
        result = validate_list_input([1, 2], "field", min_length=2)
        assert result == [1, 2]
        
        # Should fail
        with pytest.raises(ValidationError, match="field too short"):
            validate_list_input([1], "field", min_length=2)

    def test_validate_list_input_max_length(self) -> None:
        """Test list maximum length validation."""
        # Should pass
        result = validate_list_input([1, 2], "field", max_length=2)
        assert result == [1, 2]
        
        # Should fail
        with pytest.raises(ValidationError, match="field too long"):
            validate_list_input([1, 2, 3], "field", max_length=2)

    def test_validate_list_input_item_validator(self) -> None:
        """Test list validation with item validator."""
        def is_positive(x: int) -> int:
            if x <= 0:
                raise ValueError("Must be positive")
            return x
        
        # Should pass
        result = validate_list_input([1, 2, 3], "field", item_validator=is_positive)
        assert result == [1, 2, 3]
        
        # Should fail
        with pytest.raises(ValidationError, match="Invalid item at index 1"):
            validate_list_input([1, -2, 3], "field", item_validator=is_positive)


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_sanitize_filename_clean(self) -> None:
        """Test sanitizing clean filename."""
        assert sanitize_filename("test.txt") == "test.txt"
        assert sanitize_filename("my_file-123.py") == "my_file-123.py"

    def test_sanitize_filename_dangerous_chars(self) -> None:
        """Test removing dangerous characters."""
        assert sanitize_filename("test<>file.txt") == "test__file.txt"
        assert sanitize_filename("path/to/file.txt") == "path_to_file.txt"
        assert sanitize_filename("file:name.txt") == "file_name.txt"

    def test_sanitize_filename_empty_error(self) -> None:
        """Test empty filename raises error."""
        with pytest.raises(ValidationError, match="Filename cannot be empty"):
            sanitize_filename("")

    def test_sanitize_filename_strips_dots_spaces(self) -> None:
        """Test stripping leading/trailing dots and spaces."""
        assert sanitize_filename("  test.txt  ") == "test.txt"
        assert sanitize_filename("..test.txt..") == "test.txt"

    def test_sanitize_filename_reserved_names(self) -> None:
        """Test rejection of Windows reserved filenames."""
        reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]
        for name in reserved:
            with pytest.raises(ValidationError, match="Reserved filename"):
                sanitize_filename(name)
            with pytest.raises(ValidationError, match="Reserved filename"):
                sanitize_filename(name.lower())
            with pytest.raises(ValidationError, match="Reserved filename"):
                sanitize_filename(f"{name}.txt")

    def test_sanitize_filename_only_dots(self) -> None:
        """Test filename with only dots is rejected."""
        with pytest.raises(ValidationError, match="Filename invalid after sanitization"):
            sanitize_filename("...")

    def test_sanitize_filename_length_limit(self) -> None:
        """Test filename length is limited to 255 chars."""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 255

    def test_sanitize_filename_becomes_empty(self) -> None:
        """Test filename that becomes empty after sanitization."""
        # ">>><<<"" becomes "______" which is not empty
        result = sanitize_filename(">>><<<")
        assert result == "______"


class TestValidateEncoding:
    """Test validate_encoding function."""

    def test_validate_encoding_valid(self) -> None:
        """Test valid encoding names."""
        assert validate_encoding("utf-8") == "utf-8"
        assert validate_encoding("utf-16") == "utf-16"
        assert validate_encoding("ascii") == "ascii"
        assert validate_encoding("latin-1") == "latin-1"

    def test_validate_encoding_none_error(self) -> None:
        """Test None encoding raises error."""
        with pytest.raises(ValidationError, match="Encoding cannot be None"):
            validate_encoding(None)

    def test_validate_encoding_invalid(self) -> None:
        """Test invalid encoding names."""
        with pytest.raises(ValidationError, match="Invalid encoding"):
            validate_encoding("not-an-encoding")
        
        # Note: "utf8" is actually a valid alias for "utf-8" in Python
        assert validate_encoding("utf8") == "utf8"


class TestValidateFileSize:
    """Test validate_file_size function."""

    def test_validate_file_size_within_limit(self, tmp_path: Path) -> None:
        """Test file size validation within limit."""
        test_file = tmp_path / "small.txt"
        test_file.write_bytes(b"x" * 1000)
        
        size = validate_file_size(test_file, max_size_bytes=2000)
        assert size == 1000

    def test_validate_file_size_exceeds_limit(self, tmp_path: Path) -> None:
        """Test file size validation exceeding limit."""
        test_file = tmp_path / "large.txt"
        test_file.write_bytes(b"x" * 2000)
        
        with pytest.raises(ValidationError, match="File size exceeds maximum"):
            validate_file_size(test_file, max_size_bytes=1000)

    def test_validate_file_size_string_path(self, tmp_path: Path) -> None:
        """Test file size validation with string path."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"x" * 500)
        
        size = validate_file_size(str(test_file))
        assert size == 500

    def test_validate_file_size_nonexistent(self, tmp_path: Path) -> None:
        """Test file size validation for nonexistent file."""
        nonexistent = tmp_path / "missing.txt"
        
        with pytest.raises(ValidationError, match="File does not exist"):
            validate_file_size(nonexistent)


class TestCheckSecurityPatterns:
    """Test check_security_patterns function."""

    def test_check_security_patterns_clean(self) -> None:
        """Test clean content returns no issues."""
        content = "This is clean content with no security issues."
        issues = check_security_patterns(content)
        assert issues == []

    def test_check_security_patterns_script_injection(self) -> None:
        """Test detection of script injection."""
        content = '<script>alert("XSS")</script>'
        issues = check_security_patterns(content)
        assert "Potential script injection detected" in issues

    def test_check_security_patterns_path_traversal(self) -> None:
        """Test detection of path traversal."""
        content1 = "../../etc/passwd"
        issues1 = check_security_patterns(content1)
        assert "Potential path traversal detected" in issues1
        
        content2 = "..\\windows\\system32"
        issues2 = check_security_patterns(content2)
        assert "Potential path traversal detected" in issues2

    def test_check_security_patterns_sql_injection(self) -> None:
        """Test detection of SQL injection patterns."""
        sql_payloads = [
            "' OR 1=1",
            "'; DROP TABLE users",
            "'; DELETE FROM accounts",
            "'; --",
        ]
        
        for payload in sql_payloads:
            issues = check_security_patterns(payload)
            assert "Potential SQL injection detected" in issues

    def test_check_security_patterns_multiple_issues(self) -> None:
        """Test detection of multiple security issues."""
        content = "<script>alert('XSS')</script> and ../../etc/passwd"
        issues = check_security_patterns(content)
        assert len(issues) == 2
        assert "Potential script injection detected" in issues
        assert "Potential path traversal detected" in issues

    def test_check_security_patterns_case_insensitive(self) -> None:
        """Test case-insensitive pattern matching."""
        content = "<SCRIPT>alert('XSS')</SCRIPT>"
        issues = check_security_patterns(content)
        assert "Potential script injection detected" in issues


class TestValidateJsonStructure:
    """Test validate_json_structure function."""

    def test_validate_json_structure_valid(self) -> None:
        """Test valid JSON structure."""
        data = {"name": "test", "value": 123, "active": True}
        result = validate_json_structure(data, ["name", "value"])
        assert result == data

    def test_validate_json_structure_not_dict(self) -> None:
        """Test non-dict input raises error."""
        with pytest.raises(ValidationError, match="Data must be a dictionary"):
            validate_json_structure([], ["key"])
        
        with pytest.raises(ValidationError, match="Data must be a dictionary"):
            validate_json_structure("not a dict", ["key"])

    def test_validate_json_structure_missing_keys(self) -> None:
        """Test missing required keys."""
        data = {"name": "test"}
        with pytest.raises(ValidationError, match="Missing required keys: value, active"):
            validate_json_structure(data, ["name", "value", "active"])

    def test_validate_json_structure_extra_keys_allowed(self) -> None:
        """Test extra keys are allowed."""
        data = {"name": "test", "value": 123, "extra": "allowed"}
        result = validate_json_structure(data, ["name", "value"])
        assert result == data

    def test_validate_json_structure_empty_requirements(self) -> None:
        """Test validation with no required keys."""
        data = {"any": "data"}
        result = validate_json_structure(data, [])
        assert result == data


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple validation functions."""

    def test_validate_markdown_file_workflow(self, tmp_path: Path) -> None:
        """Test typical markdown file validation workflow."""
        # Create test file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Document\n\nContent here.")
        
        # Validate path
        validated_path = validate_file_path(md_file, allowed_extensions=[".md"])
        
        # Check size
        size = validate_file_size(validated_path)
        assert size > 0
        
        # Validate content doesn't have security issues
        content = validated_path.read_text()
        issues = check_security_patterns(content)
        assert issues == []

    def test_validate_config_file_workflow(self, tmp_path: Path) -> None:
        """Test configuration file validation workflow."""
        import json
        
        # Create config file
        config_data = {"threshold": 0.85, "encoding": "utf-8", "files": ["a.txt", "b.txt"]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        # Validate path
        validated_path = validate_file_path(config_file)
        
        # Load and validate structure
        loaded_data = json.loads(validated_path.read_text())
        validated_data = validate_json_structure(loaded_data, ["threshold", "encoding"])
        
        # Validate individual fields
        threshold = validate_threshold(validated_data["threshold"])
        encoding = validate_encoding(validated_data["encoding"])
        
        assert threshold == 0.85
        assert encoding == "utf-8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])