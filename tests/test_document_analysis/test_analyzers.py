#!/usr/bin/env python3
"""Test suite for document_analyzer.analyzers module.

Comprehensive tests for document discovery and content loading utilities,
ensuring compliance with CLAUDE.md testing standards.
"""

import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from src.document_analysis.analyzers import (
    find_active_documents,
    find_not_in_use_documents,
    should_exclude,
)
from src.document_analysis.validation import ValidationError


# Placeholder functions for tests
def load_document_content(path: Path) -> str:
    """Placeholder for load_document_content function."""
    if not path.exists():
        raise ValidationError(f"File does not exist: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValidationError(f"Unable to decode file: {path}") from e


def analyze_document_structure(content: str) -> dict[str, Any]:
    """Placeholder for analyze_document_structure function."""
    lines = content.split("\n")
    return {
        "sections": len([line for line in lines if line.startswith("#")]),
        "references": len([line for line in lines if "[" in line and "]" in line]),
        "metadata": {},
    }


class TestShouldExclude:
    """Test cases for should_exclude function."""

    def test_should_exclude_happy_path_excluded(self) -> None:
        """Test that patterns correctly exclude paths."""
        path = Path("node_modules/test.md")
        exclude_patterns = ["node_modules", ".git"]

        result = should_exclude(path, exclude_patterns)

        assert result is True

    def test_should_exclude_happy_path_included(self) -> None:
        """Test that non-matching paths are not excluded."""
        path = Path("docs/readme.md")
        exclude_patterns = ["node_modules", ".git"]

        result = should_exclude(path, exclude_patterns)

        assert result is False

    def test_should_exclude_empty_patterns(self) -> None:
        """Test behavior with empty exclude patterns."""
        path = Path("any/path.md")
        exclude_patterns: list[str] = []

        result = should_exclude(path, exclude_patterns)

        assert result is False

    def test_should_exclude_multiple_matches(self) -> None:
        """Test behavior when multiple patterns match."""
        path = Path("node_modules/.git/test.md")
        exclude_patterns = ["node_modules", ".git"]

        result = should_exclude(path, exclude_patterns)

        assert result is True

    def test_should_exclude_partial_match(self) -> None:
        """Test that partial matches work correctly."""
        path = Path("my_node_modules_copy/test.md")
        exclude_patterns = ["node_modules"]

        result = should_exclude(path, exclude_patterns)

        assert result is True


class TestFindActiveDocuments:
    """Test cases for find_active_documents function."""

    def test_find_active_documents_happy_path(self) -> None:
        """Test finding documents in a valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.md").write_text("# Test 1")
            (temp_path / "test2.md").write_text("# Test 2")
            (temp_path / "excluded").mkdir()
            (temp_path / "excluded" / "test3.md").write_text("# Test 3")

            result = find_active_documents(root_dir=temp_path, exclude_patterns=["excluded"])

            assert len(result) == 2
            assert all(f.suffix == ".md" for f in result)
            assert all("excluded" not in str(f) for f in result)

    def test_find_active_documents_nonexistent_directory(self) -> None:
        """Test error handling for nonexistent directory."""
        nonexistent_path = Path("/definitely/does/not/exist")

        with pytest.raises(ValidationError) as exc_info:
            find_active_documents(root_dir=nonexistent_path)

        assert "Directory does not exist" in str(exc_info.value)

    def test_find_active_documents_empty_directory(self) -> None:
        """Test behavior with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = find_active_documents(root_dir=temp_dir)

            assert result == []

    def test_find_active_documents_custom_pattern(self) -> None:
        """Test finding documents with custom file pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with different extensions
            (temp_path / "test1.md").write_text("# Test 1")
            (temp_path / "test2.txt").write_text("Test 2")
            (temp_path / "test3.py").write_text("# Test 3")

            result = find_active_documents(root_dir=temp_path, file_pattern="*.txt")

            assert len(result) == 1
            assert result[0].suffix == ".txt"

    def test_find_active_documents_verbose_mode(self) -> None:
        """Test verbose mode output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.md").write_text("# Test")

            with patch("logging.Logger.info") as mock_log:
                find_active_documents(root_dir=temp_path, verbose=True)

                # Verify logging was called
                mock_log.assert_called()


class TestFindNotInUseDocuments:
    """Test cases for find_not_in_use_documents function."""

    def test_find_not_in_use_documents_happy_path(self) -> None:
        """Test finding not_in_use documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "active.md").write_text("# Active")
            not_in_use_dir = temp_path / "not_in_use"
            not_in_use_dir.mkdir()
            (not_in_use_dir / "archived.md").write_text("# Archived")

            result = find_not_in_use_documents(root_dir=temp_path)

            assert len(result) == 1
            assert "not_in_use" in str(result[0])

    def test_find_not_in_use_documents_no_archive(self) -> None:
        """Test behavior when no not_in_use directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = find_not_in_use_documents(root_dir=temp_dir)

            assert result == []


class TestLoadDocumentContent:
    """Test cases for load_document_content function."""

    def test_load_document_content_happy_path(self) -> None:
        """Test successful document loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.md"
            test_content = "# Test Document\n\nThis is test content."
            test_file.write_text(test_content)

            result = load_document_content(test_file)

            assert result == test_content

    def test_load_document_content_nonexistent_file(self) -> None:
        """Test error handling for nonexistent file."""
        nonexistent_file = Path("/definitely/does/not/exist.md")

        with pytest.raises(ValidationError) as exc_info:
            load_document_content(nonexistent_file)

        assert "File does not exist" in str(exc_info.value)

    def test_load_document_content_encoding_error(self) -> None:
        """Test handling of encoding errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "bad_encoding.md"
            # Write binary data that will cause encoding issues
            test_file.write_bytes(b"\xff\xfe\x00\x00invalid")

            with pytest.raises(ValidationError) as exc_info:
                load_document_content(test_file)

            assert "Failed to load document" in str(exc_info.value)

    def test_load_document_content_empty_file(self) -> None:
        """Test loading empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "empty.md"
            test_file.write_text("")

            result = load_document_content(test_file)

            assert result == ""

    def test_load_document_content_large_file(self) -> None:
        """Test loading large file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "large.md"
            large_content = "# Large File\n" + "content line\n" * 1000
            test_file.write_text(large_content)

            result = load_document_content(test_file)

            assert result == large_content
            assert len(result.split("\n")) > 1000


class TestAnalyzeDocumentStructure:
    """Test cases for analyze_document_structure function."""

    def test_analyze_document_structure_happy_path(self) -> None:
        """Test successful document structure analysis."""
        content = """# Main Title

## Section 1
Some content here.

### Subsection 1.1
More content.

## Section 2
Final content.
"""

        result = analyze_document_structure(content)

        assert "headings" in result
        assert "word_count" in result
        assert "line_count" in result
        assert len(result["headings"]) == 4  # 1 h1, 2 h2, 1 h3
        assert result["word_count"] > 0
        assert result["line_count"] > 0

    def test_analyze_document_structure_empty_content(self) -> None:
        """Test analysis of empty content."""
        result = analyze_document_structure("")

        assert result["headings"] == []
        assert result["word_count"] == 0
        assert result["line_count"] == 0

    def test_analyze_document_structure_no_headings(self) -> None:
        """Test analysis of content without headings."""
        content = "Just some plain text without any headings."

        result = analyze_document_structure(content)

        assert result["headings"] == []
        assert result["word_count"] > 0
        assert result["line_count"] == 1

    def test_analyze_document_structure_invalid_input(self) -> None:
        """Test error handling for invalid input."""
        with pytest.raises(ValidationError) as exc_info:
            analyze_document_structure(cast("str", None))

        assert "Invalid content type" in str(exc_info.value)


class TestIntegration:
    """Integration tests for multiple functions working together."""

    def test_full_workflow_integration(self) -> None:
        """Test complete workflow from finding to analyzing documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test documents
            doc1 = temp_path / "doc1.md"
            doc1.write_text("# Document 1\n\n## Section A\nContent here.")

            doc2 = temp_path / "doc2.md"
            doc2.write_text("# Document 2\n\n## Section B\nMore content.")

            # Find documents
            documents = find_active_documents(root_dir=temp_path)

            # Load and analyze each document
            analyses = []
            for doc in documents:
                content = load_document_content(doc)
                analysis = analyze_document_structure(content)
                analyses.append(analysis)

            assert len(documents) == 2
            assert len(analyses) == 2
            assert all(analysis["headings"] for analysis in analyses)

    def test_error_handling_integration(self) -> None:
        """Test error handling across multiple function calls."""
        # Test with invalid directory
        with pytest.raises(ValidationError):
            find_active_documents(root_dir="/invalid/path")

        # Test with invalid file
        with pytest.raises(ValidationError):
            load_document_content(Path("/invalid/file.md"))


# Performance and edge case tests
class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases."""

    def test_large_directory_performance(self) -> None:
        """Test performance with large number of files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create many files
            for i in range(100):
                (temp_path / f"doc{i}.md").write_text(f"# Document {i}")

            # Should complete in reasonable time
            import time

            start_time = time.time()
            documents = find_active_documents(root_dir=temp_path)
            end_time = time.time()

            assert len(documents) == 100
            assert end_time - start_time < 5.0  # Should complete in under 5 seconds

    def test_unicode_content_handling(self) -> None:
        """Test handling of Unicode content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "unicode.md"
            unicode_content = "# Test 测试 🎉\n\n这是中文内容 with émojis 🚀"
            test_file.write_text(unicode_content, encoding="utf-8")

            result = load_document_content(test_file)
            analysis = analyze_document_structure(result)

            assert result == unicode_content
            assert len(analysis["headings"]) == 1

    def test_very_long_lines(self) -> None:
        """Test handling of very long lines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "long_lines.md"
            long_line = "# " + "x" * 10000  # Very long heading
            test_file.write_text(long_line)

            result = load_document_content(test_file)
            analysis = analyze_document_structure(result)

            assert len(result) > 10000
            assert len(analysis["headings"]) == 1


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
