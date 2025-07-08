#!/usr/bin/env python3
"""Test suite for document_analyzer.validation module.

Comprehensive tests for input validation utilities ensuring security
and compliance with CLAUDE.md standards.
"""

import tempfile
from pathlib import Path
from typing import cast

import pytest

from src.validation.validation import (
    ValidationError,
    check_security_patterns,
    sanitize_filename,
    validate_directory_path,
    validate_encoding,
    validate_file_path,
    validate_file_size,
    validate_json_structure,
    validate_string_input,
)


class TestValidationError:
    """Test cases for ValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test ValidationError creation with message."""
        message = "Test validation error"
        error = ValidationError(message)

        assert str(error) == message
        assert isinstance(error, Exception)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from Exception."""
        error = ValidationError("Test")

        assert isinstance(error, Exception)
        assert isinstance(error, ValidationError)


class TestValidateStringInput:
    """Test cases for validate_string_input function."""

    def test_validate_string_input_happy_path(self) -> None:
        """Test validation of valid string input."""
        valid_input = "This is a valid string"

        result = validate_string_input(valid_input, "test_field")

        assert result == valid_input

    def test_validate_string_input_empty_string(self) -> None:
        """Test validation rejects empty string by default."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_input("", "test_field")

        assert "test_field cannot be empty" in str(exc_info.value)

    def test_validate_string_input_allow_empty(self) -> None:
        """Test validation allows empty string when specified."""
        result = validate_string_input("", "test_field", allow_empty=True)

        assert result == ""

    def test_validate_string_input_none_value(self) -> None:
        """Test validation rejects None value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_input(None, "test_field")

        assert "test_field must be a string" in str(exc_info.value)

    def test_validate_string_input_non_string(self) -> None:
        """Test validation rejects non-string types."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_input(123, "test_field")

        assert "test_field must be a string" in str(exc_info.value)

    def test_validate_string_input_max_length(self) -> None:
        """Test validation enforces maximum length."""
        long_string = "x" * 1001  # Over default 1000 limit

        with pytest.raises(ValidationError) as exc_info:
            validate_string_input(long_string, "test_field")

        assert "exceeds maximum length" in str(exc_info.value)

    def test_validate_string_input_custom_max_length(self) -> None:
        """Test validation with custom maximum length."""
        test_string = "short"

        result = validate_string_input(test_string, "test_field", max_length=10)

        assert result == test_string

    def test_validate_string_input_exactly_max_length(self) -> None:
        """Test validation with string exactly at max length."""
        test_string = "x" * 100

        result = validate_string_input(test_string, "test_field", max_length=100)

        assert result == test_string


class TestValidateFilePath:
    """Test cases for validate_file_path function."""

    def test_validate_file_path_happy_path(self) -> None:
        """Test validation of existing file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            result = validate_file_path(test_file)

            assert result == test_file
            assert isinstance(result, Path)

    def test_validate_file_path_string_input(self) -> None:
        """Test validation converts string to Path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            result = validate_file_path(str(test_file))

            assert result == test_file
            assert isinstance(result, Path)

    def test_validate_file_path_nonexistent_file(self) -> None:
        """Test validation rejects nonexistent file."""
        nonexistent_file = Path("/definitely/does/not/exist.txt")

        with pytest.raises(ValidationError) as exc_info:
            validate_file_path(nonexistent_file)

        assert "File does not exist" in str(exc_info.value)

    def test_validate_file_path_directory_not_file(self) -> None:
        """Test validation rejects directory instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValidationError) as exc_info:
                validate_file_path(temp_dir)

            assert "Path is not a file" in str(exc_info.value)

    def test_validate_file_path_allow_nonexistent(self) -> None:
        """Test validation allows nonexistent file when specified."""
        nonexistent_file = Path("/some/future/file.txt")

        result = validate_file_path(nonexistent_file, must_exist=False, check_readable=False)

        assert result == nonexistent_file

    def test_validate_file_path_unreadable_file(self) -> None:
        """Test validation of unreadable file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")
            # Make file unreadable
            test_file.chmod(0o000)

            try:
                with pytest.raises(ValidationError) as exc_info:
                    validate_file_path(test_file, check_readable=True)

                assert "File is not readable" in str(exc_info.value)
            finally:
                # Restore permissions for cleanup
                test_file.chmod(0o644)

    def test_validate_file_path_none_input(self) -> None:
        """Test validation rejects None input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file_path(cast("Path", None))

        assert "File path cannot be None" in str(exc_info.value)


class TestValidateDirectoryPath:
    """Test cases for validate_directory_path function."""

    def test_validate_directory_path_happy_path(self) -> None:
        """Test validation of existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory_path(temp_dir)

            assert result == Path(temp_dir)
            assert isinstance(result, Path)

    def test_validate_directory_path_nonexistent(self) -> None:
        """Test validation rejects nonexistent directory."""
        nonexistent_dir = Path("/definitely/does/not/exist")

        with pytest.raises(ValidationError) as exc_info:
            validate_directory_path(nonexistent_dir)

        assert "Directory does not exist" in str(exc_info.value)

    def test_validate_directory_path_file_not_directory(self) -> None:
        """Test validation rejects file instead of directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            with pytest.raises(ValidationError) as exc_info:
                validate_directory_path(test_file)

            assert "Path is not a directory" in str(exc_info.value)

    def test_validate_directory_path_allow_nonexistent(self) -> None:
        """Test validation allows nonexistent directory when specified."""
        nonexistent_dir = Path("/some/future/directory")

        result = validate_directory_path(nonexistent_dir, must_exist=False)

        assert result == nonexistent_dir


class TestValidateEncoding:
    """Test cases for validate_encoding function."""

    def test_validate_encoding_valid_encoding(self) -> None:
        """Test validation of valid encoding."""
        valid_encodings = ["utf-8", "ascii", "latin-1", "cp1252"]

        for encoding in valid_encodings:
            result = validate_encoding(encoding)
            assert result == encoding

    def test_validate_encoding_invalid_encoding(self) -> None:
        """Test validation rejects invalid encoding."""
        with pytest.raises(ValidationError) as exc_info:
            validate_encoding("invalid-encoding-name")

        assert "Invalid encoding" in str(exc_info.value)

    def test_validate_encoding_none_input(self) -> None:
        """Test validation rejects None input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_encoding(None)

        assert "Encoding cannot be None" in str(exc_info.value)


class TestValidateFileSize:
    """Test cases for validate_file_size function."""

    def test_validate_file_size_happy_path(self) -> None:
        """Test validation of normal file size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Small file content")

            result = validate_file_size(test_file)

            assert result > 0

    def test_validate_file_size_large_file(self) -> None:
        """Test validation rejects overly large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "large.txt"
            # Create a file larger than default 100MB limit
            large_content = "x" * (101 * 1024 * 1024)  # 101MB
            test_file.write_text(large_content)

            with pytest.raises(ValidationError) as exc_info:
                validate_file_size(test_file)

            assert "File size exceeds maximum" in str(exc_info.value)

    def test_validate_file_size_custom_limit(self) -> None:
        """Test validation with custom size limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Small content")

            result = validate_file_size(test_file, max_size_bytes=1000)

            assert result > 0

    def test_validate_file_size_empty_file(self) -> None:
        """Test validation of empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "empty.txt"
            test_file.write_text("")

            result = validate_file_size(test_file)

            assert result == 0


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    def test_sanitize_filename_happy_path(self) -> None:
        """Test sanitization of clean filename."""
        clean_filename = "normal_file.txt"

        result = sanitize_filename(clean_filename)

        assert result == clean_filename

    def test_sanitize_filename_dangerous_characters(self) -> None:
        """Test sanitization removes dangerous characters."""
        dangerous_filename = "file../with\\dangerous:characters?.txt"

        result = sanitize_filename(dangerous_filename)

        # Should remove or replace dangerous characters
        assert ".." not in result
        assert "\\" not in result
        assert ":" not in result
        assert "?" not in result

    def test_sanitize_filename_empty_input(self) -> None:
        """Test sanitization of empty input."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename("")

        assert "Filename cannot be empty" in str(exc_info.value)

    def test_sanitize_filename_only_dots(self) -> None:
        """Test sanitization rejects filename with only dots."""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename("...")

        assert "Invalid filename" in str(exc_info.value)

    def test_sanitize_filename_reserved_names(self) -> None:
        """Test sanitization handles reserved names."""
        reserved_names = ["CON", "PRN", "AUX", "NUL"]

        for name in reserved_names:
            with pytest.raises(ValidationError) as exc_info:
                sanitize_filename(name)

            assert "Reserved filename" in str(exc_info.value)


class TestCheckSecurityPatterns:
    """Test cases for check_security_patterns function."""

    def test_check_security_patterns_safe_content(self) -> None:
        """Test that safe content passes security check."""
        safe_content = "This is normal, safe content without issues."

        result = check_security_patterns(safe_content)

        assert result == []  # No issues found

    def test_check_security_patterns_script_injection(self) -> None:
        """Test detection of script injection patterns."""
        malicious_content = "<script>alert('xss')</script>"

        result = check_security_patterns(malicious_content)

        assert len(result) > 0
        assert any("script" in issue.lower() for issue in result)

    def test_check_security_patterns_path_traversal(self) -> None:
        """Test detection of path traversal patterns."""
        malicious_content = "../../../etc/passwd"

        result = check_security_patterns(malicious_content)

        assert len(result) > 0
        assert any("path" in issue.lower() or "traversal" in issue.lower() for issue in result)

    def test_check_security_patterns_sql_injection(self) -> None:
        """Test detection of SQL injection patterns."""
        malicious_content = "'; DROP TABLE users; --"

        result = check_security_patterns(malicious_content)

        assert len(result) > 0
        assert any("sql" in issue.lower() or "injection" in issue.lower() for issue in result)

    def test_check_security_patterns_multiple_issues(self) -> None:
        """Test detection of multiple security issues."""
        malicious_content = "<script>alert('xss')</script>'; DROP TABLE users; --"

        result = check_security_patterns(malicious_content)

        assert len(result) > 1  # Multiple issues detected


class TestValidateJsonStructure:
    """Test cases for validate_json_structure function."""

    def test_validate_json_structure_happy_path(self) -> None:
        """Test validation of valid JSON structure."""
        valid_data = {"key1": "value1", "key2": 123, "key3": [1, 2, 3]}
        required_keys = ["key1", "key2"]

        result = validate_json_structure(valid_data, required_keys)

        assert result == valid_data

    def test_validate_json_structure_missing_keys(self) -> None:
        """Test validation rejects missing required keys."""
        incomplete_data = {"key1": "value1"}
        required_keys = ["key1", "key2", "key3"]

        with pytest.raises(ValidationError) as exc_info:
            validate_json_structure(incomplete_data, required_keys)

        assert "Missing required keys" in str(exc_info.value)

    def test_validate_json_structure_wrong_type(self) -> None:
        """Test validation rejects non-dict input."""
        invalid_data = ["not", "a", "dict"]
        required_keys = ["key1"]

        with pytest.raises(ValidationError) as exc_info:
            validate_json_structure(invalid_data, required_keys)

        assert "must be a dictionary" in str(exc_info.value)

    def test_validate_json_structure_empty_requirements(self) -> None:
        """Test validation with no required keys."""
        data = {"any": "data"}

        result = validate_json_structure(data, [])

        assert result == data

    def test_validate_json_structure_extra_keys_allowed(self) -> None:
        """Test validation allows extra keys by default."""
        data = {"required": "value", "extra": "allowed"}
        required_keys = ["required"]

        result = validate_json_structure(data, required_keys)

        assert result == data


class TestIntegrationValidation:
    """Integration tests for validation functions working together."""

    def test_full_file_validation_workflow(self) -> None:
        """Test complete file validation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test_document.md"
            content = "# Test Document\n\nSafe content here."
            test_file.write_text(content)

            # Validate file path
            validated_path = validate_file_path(test_file)

            # Validate file size
            file_size = validate_file_size(validated_path)

            # Validate filename
            safe_filename = sanitize_filename(validated_path.name)

            # Check content security
            security_issues = check_security_patterns(content)

            assert validated_path == test_file
            assert file_size > 0
            assert safe_filename == "test_document.md"
            assert security_issues == []

    def test_validation_error_propagation(self) -> None:
        """Test that validation errors propagate correctly."""
        # Test chain of validation that should fail
        with pytest.raises(ValidationError):
            # This should fail at the first validation step
            nonexistent_file = Path("/definitely/does/not/exist.txt")
            validated_path = validate_file_path(nonexistent_file)
            validate_file_size(validated_path)  # Should not reach here


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unicode_filename_validation(self) -> None:
        """Test validation of Unicode filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file with Unicode name
            unicode_filename = "测试文件_🎉.md"
            test_file = Path(temp_dir) / unicode_filename
            test_file.write_text("Unicode content")

            result = validate_file_path(test_file)
            sanitized = sanitize_filename(unicode_filename)

            assert result == test_file
            assert len(sanitized) > 0

    def test_very_long_paths(self) -> None:
        """Test handling of very long file paths."""
        # Create a very long path (within tempdir to ensure it's valid)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Build a long path by nesting directories
            long_path = Path(temp_dir)
            for i in range(10):
                long_path /= f"very_long_directory_name_{i}"

            long_path.mkdir(parents=True, exist_ok=True)
            test_file = long_path / "test.md"
            test_file.write_text("Content")

            result = validate_file_path(test_file)
            assert result == test_file

    def test_symbolic_link_handling(self) -> None:
        """Test handling of symbolic links."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create original file
            original_file = Path(temp_dir) / "original.md"
            original_file.write_text("Original content")

            # Create symbolic link
            link_file = Path(temp_dir) / "link.md"
            try:
                link_file.symlink_to(original_file)

                # Should be able to validate the link
                result = validate_file_path(link_file)
                assert result == link_file

            except OSError:
                # Skip if symlinks not supported on this system
                pytest.skip("Symbolic links not supported")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
