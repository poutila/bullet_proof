#!/usr/bin/env python3
"""Comprehensive test suite for generate_files_required.py.

Tests all functionality including file scanning, validation, error handling,
and report generation following CLAUDE.md testing standards.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from generate_files_required import (
    FILE_PATTERN,
    MAX_FILE_PATH_LENGTH,
    SUPPORTED_FILE_EXTENSIONS,
    FileScanner,
    ReportGenerator,
    ScanResult,
)


class TestFilePattern:
    """Test the regex pattern for finding file references."""

    def test_pattern_matches_basic_files(self) -> None:
        """Test pattern matches basic file references."""
        test_content = 'Check out "config.py" and `README.md`'
        matches = FILE_PATTERN.findall(test_content)
        assert "config.py" in matches
        assert "README.md" in matches

    def test_pattern_matches_paths(self) -> None:
        """Test pattern matches file paths."""
        test_content = "See scripts/deploy.py and docs/api.md"
        matches = FILE_PATTERN.findall(test_content)
        assert "scripts/deploy.py" in matches
        assert "docs/api.md" in matches

    def test_pattern_matches_quoted_paths(self) -> None:
        """Test pattern matches quoted file paths."""
        test_content = """
        Files include:
        - "src/main.py"
        - 'tests/test_main.py'
        - `config.json`
        """
        matches = FILE_PATTERN.findall(test_content)
        assert "src/main.py" in matches
        assert "tests/test_main.py" in matches
        assert "config.json" in matches

    def test_pattern_excludes_invalid_extensions(self) -> None:
        """Test pattern excludes unsupported file extensions."""
        test_content = "Files: image.png, document.pdf, script.sh"
        matches = FILE_PATTERN.findall(test_content)
        assert len(matches) == 0


class TestFileScanner:
    """Test the FileScanner class."""

    def test_init_with_valid_directory(self, tmp_path: Path) -> None:
        """Test initialization with valid directory."""
        scanner = FileScanner(tmp_path)
        assert scanner.docs_root == tmp_path

    def test_init_with_invalid_directory(self) -> None:
        """Test initialization with non-existent directory."""
        with pytest.raises(ValueError, match="Directory does not exist"):
            FileScanner(Path("/nonexistent/directory"))

    def test_init_with_file_path(self, tmp_path: Path) -> None:
        """Test initialization with file instead of directory."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="Path is not a directory"):
            FileScanner(file_path)

    def test_validate_file_path_valid(self) -> None:
        """Test validation of valid file paths."""
        scanner = FileScanner()

        valid_paths = ["script.py", "docs/README.md", "src/module/file.py", "config.json", "requirements.txt"]

        for path in valid_paths:
            assert scanner.validate_file_path(path), f"Path {path} should be valid"

    def test_validate_file_path_invalid(self) -> None:
        """Test validation rejects invalid paths."""
        scanner = FileScanner()

        invalid_paths = [
            "",  # Empty path
            "../parent.py",  # Parent directory traversal
            "/absolute/path.py",  # Absolute path
            "C:\\windows\\file.py",  # Windows absolute path
            "file.exe",  # Unsupported extension
            "a" * 300 + ".py",  # Too long
        ]

        for path in invalid_paths:
            assert not scanner.validate_file_path(path), f"Path {path} should be invalid"

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """Test scanning empty directory."""
        scanner = FileScanner(tmp_path)
        result = scanner.scan_markdown_files()

        assert result.scanned_count == 0
        assert len(result.found_files) == 0
        assert len(result.warnings) == 1
        assert "No markdown files found" in result.warnings[0]

    def test_scan_markdown_files_success(self, tmp_path: Path) -> None:
        """Test successful scanning of markdown files."""
        # Create test markdown files
        (tmp_path / "doc1.md").write_text("""
        # Documentation
        See `main.py` and `config.json` for details.
        Also check scripts/deploy.py
        """)

        (tmp_path / "doc2.md").write_text("""
        ## Setup
        Run tests/test_main.py
        Configuration in settings.yaml
        """)

        scanner = FileScanner(tmp_path)
        result = scanner.scan_markdown_files()

        assert result.scanned_count == 2
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

        assert "main.py" in result.found_files[".py"]
        assert "scripts/deploy.py" in result.found_files[".py"]
        assert "tests/test_main.py" in result.found_files[".py"]
        assert "config.json" in result.found_files[".json"]
        assert "settings.yaml" in result.found_files[".yaml"]

    def test_scan_handles_read_errors(self, tmp_path: Path) -> None:
        """Test scanning handles file read errors gracefully."""
        # Create a markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("Check main.py")

        # Mock read_text to raise IOError
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            scanner = FileScanner(tmp_path)
            result = scanner.scan_markdown_files()

            assert result.scanned_count == 0
            assert len(result.errors) == 1
            assert "Failed to read" in result.errors[0]

    def test_scan_validates_file_paths(self, tmp_path: Path) -> None:
        """Test scanning validates and rejects invalid file paths."""
        (tmp_path / "doc.md").write_text("""
        Valid: main.py
        Invalid: ../parent.py
        Invalid: /absolute/path.py
        Invalid: file.exe
        """)

        scanner = FileScanner(tmp_path)
        result = scanner.scan_markdown_files()

        assert "main.py" in result.found_files[".py"]
        assert "../parent.py" not in result.found_files.get(".py", set())
        assert "/absolute/path.py" not in result.found_files.get(".py", set())


class TestReportGenerator:
    """Test the ReportGenerator class."""

    def test_generate_empty_report(self, tmp_path: Path) -> None:
        """Test generating report with no files found."""
        output_path = tmp_path / "test_output.md"
        generator = ReportGenerator(output_path)

        scan_result = ScanResult(found_files={}, errors=[], warnings=[], scanned_count=5)

        generator.generate_report(scan_result)

        assert output_path.exists()
        content = output_path.read_text()
        assert "FILES_REQUIRED.md" in content
        assert "Files Scanned: 5" in content
        assert "Total References Found: 0" in content

    def test_generate_report_with_files(self, tmp_path: Path) -> None:
        """Test generating report with found files."""
        output_path = tmp_path / "test_output.md"
        generator = ReportGenerator(output_path)

        scan_result = ScanResult(
            found_files={".py": {"main.py", "test.py"}, ".md": {"README.md", "docs/guide.md"}, ".json": {"config.json"}},
            errors=[],
            warnings=[],
            scanned_count=10,
        )

        generator.generate_report(scan_result)

        content = output_path.read_text()
        assert "🐍 Python Scripts" in content
        assert "📄 Markdown Documentation" in content
        assert "🧩 JSON Configurations" in content
        assert "- `main.py`" in content
        assert "- `README.md`" in content
        assert "- `config.json`" in content
        assert "Count: 2" in content  # Python files count

    def test_generate_report_with_errors_and_warnings(self, tmp_path: Path) -> None:
        """Test generating report with errors and warnings."""
        output_path = tmp_path / "test_output.md"
        generator = ReportGenerator(output_path)

        scan_result = ScanResult(
            found_files={".py": {"main.py"}},
            errors=["Failed to read file1.md", "Permission denied: file2.md"],
            warnings=["No markdown files in subdirectory"],
            scanned_count=3,
        )

        generator.generate_report(scan_result)

        content = output_path.read_text()
        assert "## ⚠️ Warnings" in content
        assert "## ❌ Errors" in content
        assert "Failed to read file1.md" in content
        assert "Permission denied: file2.md" in content
        assert "No markdown files in subdirectory" in content

    def test_generate_report_write_error(self, tmp_path: Path) -> None:
        """Test handling write errors when generating report."""
        # Use a path that can't be written to
        output_path = tmp_path / "nonexistent" / "output.md"
        generator = ReportGenerator(output_path)

        scan_result = ScanResult(found_files={}, errors=[], warnings=[], scanned_count=0)

        with pytest.raises(IOError, match="Failed to write report"):
            generator.generate_report(scan_result)


class TestIntegration:
    """Integration tests for the complete workflow."""

    def test_end_to_end_scanning_and_reporting(self, tmp_path: Path) -> None:
        """Test complete workflow from scanning to report generation."""
        # Create test structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (tmp_path / "README.md").write_text("""
        # Project
        Main script: src/main.py
        Config: config.json
        Tests: tests/test_main.py
        """)

        (docs_dir / "guide.md").write_text("""
        ## Guide
        See utils/helper.py and data.yaml
        """)

        # Scan files
        scanner = FileScanner(tmp_path)
        scan_result = scanner.scan_markdown_files()

        # Generate report
        output_path = tmp_path / "FILES_REQUIRED.md"
        generator = ReportGenerator(output_path)
        generator.generate_report(scan_result)

        # Verify results
        assert output_path.exists()
        content = output_path.read_text()

        # Check all files were found and categorized
        assert "src/main.py" in content
        assert "tests/test_main.py" in content
        assert "utils/helper.py" in content
        assert "config.json" in content
        assert "data.yaml" in content

        # Check proper organization
        assert content.index("🐍 Python Scripts") < content.index("src/main.py")
        assert content.index("🧩 JSON Configurations") < content.index("config.json")

    def test_main_function_success(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Test main function executes successfully."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create test file
        (tmp_path / "test.md").write_text("See main.py")

        # Import and run main
        from generate_files_required import main

        # Should not raise any exceptions
        main()

        # Verify output file created
        assert (tmp_path / "FILES_REQUIRED.md").exists()


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    def test_large_number_of_files_warning(self, tmp_path: Path) -> None:
        """Test warning when too many files of one type found."""
        # Create markdown with many file references
        content = "\n".join([f"File: script{i}.py" for i in range(1100)])
        (tmp_path / "large.md").write_text(content)

        scanner = FileScanner(tmp_path)
        result = scanner.scan_markdown_files()

        assert len(result.warnings) > 0
        assert any("Found over" in w for w in result.warnings)

    def test_malformed_markdown_handling(self, tmp_path: Path) -> None:
        """Test handling of malformed markdown content."""
        # Create markdown with potential parsing issues
        (tmp_path / "malformed.md").write_text("""
        Unclosed quote: "main.py
        Special chars: <script>alert()</script>
        Unicode: 文件.py
        Null bytes: \x00
        """)

        scanner = FileScanner(tmp_path)
        # Should not raise exceptions
        result = scanner.scan_markdown_files()
        assert result.scanned_count == 1


# Test constants and configuration
def test_constants_are_reasonable() -> None:
    """Test that constants have reasonable values."""
    assert MAX_FILE_PATH_LENGTH > 50
    assert MAX_FILE_PATH_LENGTH <= 260  # Windows path limit
    assert len(SUPPORTED_FILE_EXTENSIONS) > 0
    assert all(ext.startswith(".") for ext in SUPPORTED_FILE_EXTENSIONS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
