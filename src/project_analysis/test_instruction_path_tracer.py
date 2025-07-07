#!/usr/bin/env python3
"""Tests for instruction path tracer modules."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from .coverage_analyzer import CoverageAnalyzer
from .document_parser import DocumentParser
from .instruction_node import InstructionNode
from .instruction_path_tracer import InstructionPathTracer
from .path_resolver import PathResolver
from .report_generator import ReportGenerator


class TestDocumentParser:
    """Test cases for DocumentParser."""

    def test_extract_document_info_file_not_exists(self):
        """Test extraction from non-existent file returns None."""
        parser = DocumentParser()
        result = parser.extract_document_info(Path("/non/existent/file.md"))
        assert result is None

    def test_extract_title_from_markdown(self, tmp_path):
        """Test title extraction from markdown header."""
        parser = DocumentParser()
        doc_path = tmp_path / "test.md"
        doc_path.write_text("# Test Title\n\nContent here")
        
        node = parser.extract_document_info(doc_path)
        assert node is not None
        assert node.title == "Test Title"

    def test_extract_title_fallback_to_filename(self, tmp_path):
        """Test title falls back to filename when no header."""
        parser = DocumentParser()
        doc_path = tmp_path / "test.md"
        doc_path.write_text("No header here\n\nContent")
        
        node = parser.extract_document_info(doc_path)
        assert node is not None
        assert node.title == "test.md"

    def test_extract_references(self, tmp_path):
        """Test markdown reference extraction."""
        parser = DocumentParser()
        doc_path = tmp_path / "test.md"
        doc_path.write_text(
            "See [Planning](../planning/PLANNING.md) and "
            "[README](README.md) for more."
        )
        
        node = parser.extract_document_info(doc_path)
        assert node is not None
        assert "../planning/PLANNING.md" in node.references
        assert "README.md" in node.references

    def test_extract_instructions(self, tmp_path):
        """Test instruction pattern extraction."""
        parser = DocumentParser()
        doc_path = tmp_path / "test.md"
        doc_path.write_text(
            "You must implement the feature.\n"
            "Need to create configuration files.\n"
            "Should write tests."
        )
        
        node = parser.extract_document_info(doc_path)
        assert node is not None
        assert len(node.instructions) >= 3

    def test_extract_file_generations(self, tmp_path):
        """Test file generation pattern extraction."""
        parser = DocumentParser()
        doc_path = tmp_path / "test.md"
        doc_path.write_text(
            "This creates `config.yml`.\n"
            "Generates output.json file."
        )
        
        node = parser.extract_document_info(doc_path)
        assert node is not None
        assert "config.yml" in node.generates
        assert "output.json" in node.generates


class TestPathResolver:
    """Test cases for PathResolver."""

    def test_normalize_path_skips_urls(self, tmp_path):
        """Test that URLs are skipped."""
        resolver = PathResolver(tmp_path)
        result = resolver.normalize_path("https://example.com", tmp_path)
        assert result is None

    def test_normalize_path_relative(self, tmp_path):
        """Test relative path normalization."""
        resolver = PathResolver(tmp_path)
        
        # Create a file
        (tmp_path / "test.md").touch()
        
        # Test ./ prefix removal
        result = resolver.normalize_path("./test.md", tmp_path)
        assert result == tmp_path / "test.md"

    def test_normalize_path_parent_directory(self, tmp_path):
        """Test parent directory path resolution."""
        resolver = PathResolver(tmp_path)
        
        # Create subdirectory and file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "test.md").touch()
        
        # Test ../ resolution
        result = resolver.normalize_path("../test.md", subdir)
        assert result == tmp_path / "test.md"

    def test_find_file_in_project(self, tmp_path):
        """Test finding files in project."""
        resolver = PathResolver(tmp_path)
        
        # Create src directory and file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").touch()
        
        result = resolver.find_file_in_project("test.py", ["src/", "docs/"])
        assert result == src_dir / "test.py"


class TestCoverageAnalyzer:
    """Test cases for CoverageAnalyzer."""

    def test_check_coverage_empty_tree(self, tmp_path):
        """Test coverage check with empty tree."""
        analyzer = CoverageAnalyzer(tmp_path)
        node = InstructionNode(path=tmp_path / "test.md", title="Test", depth=0)
        
        coverage = analyzer.check_coverage(node)
        
        assert all(len(items) == 0 for items in coverage.values())

    def test_check_coverage_with_file_generation(self, tmp_path):
        """Test coverage check detects file generation."""
        analyzer = CoverageAnalyzer(tmp_path)
        doc_path = tmp_path / "test.md"
        doc_path.write_text("Content")
        
        node = InstructionNode(
            path=doc_path,
            title="Test",
            depth=0,
            generates=["config.yml", "setup.py"]
        )
        
        coverage = analyzer.check_coverage(node)
        
        assert len(coverage["file_generation"]) == 2
        assert "test.md: config.yml" in coverage["file_generation"]

    def test_extract_required_files(self, tmp_path):
        """Test extracting required files from content."""
        analyzer = CoverageAnalyzer(tmp_path)
        
        content = """
        - `config.yml`
        - `setup.py`
        ├── test.md
        Direct mention: `script.sh`
        """
        
        files = analyzer._extract_required_files(content)
        
        assert "config.yml" in files
        assert "setup.py" in files
        assert "test.md" in files
        assert "script.sh" in files


class TestReportGenerator:
    """Test cases for ReportGenerator."""

    def test_print_instruction_tree_empty_node(self, tmp_path):
        """Test printing empty tree."""
        generator = ReportGenerator(tmp_path)
        
        # Should not raise exception
        generator.print_instruction_tree(None)

    def test_print_coverage_report(self, tmp_path):
        """Test printing coverage report."""
        generator = ReportGenerator(tmp_path)
        
        coverage = {
            "file_generation": ["test.py", "config.yml"],
            "ci_cd": ["workflow.yml"],
            "test_automation": [],
        }
        
        # Should not raise exception
        generator.print_coverage_report(coverage)

    def test_print_alignment_report_empty(self, tmp_path):
        """Test printing empty alignment report."""
        generator = ReportGenerator(tmp_path)
        
        # Should not raise exception
        generator.print_alignment_report({})

    def test_print_summary(self, tmp_path):
        """Test printing summary."""
        generator = ReportGenerator(tmp_path)
        
        # Should not raise exception
        generator.print_summary(total_docs=15, entry_points=2)


class TestInstructionPathTracer:
    """Test cases for InstructionPathTracer."""

    def test_initialization(self, tmp_path):
        """Test tracer initialization."""
        tracer = InstructionPathTracer(root_dir=tmp_path, max_depth=3)
        
        assert tracer.root_dir == tmp_path
        assert tracer.max_depth == 3
        assert len(tracer.visited) == 0

    def test_find_entry_points_none_exist(self, tmp_path):
        """Test finding entry points when none exist."""
        tracer = InstructionPathTracer(root_dir=tmp_path)
        
        entry_points = tracer._find_entry_points()
        
        assert len(entry_points) == 0

    def test_find_entry_points_readme_exists(self, tmp_path):
        """Test finding README.md entry point."""
        tracer = InstructionPathTracer(root_dir=tmp_path)
        
        # Create README.md
        readme = tmp_path / "README.md"
        readme.touch()
        
        entry_points = tracer._find_entry_points()
        
        assert len(entry_points) == 1
        assert entry_points[0] == ("README.md", readme)

    def test_trace_from_document_single_file(self, tmp_path):
        """Test tracing from a single document."""
        tracer = InstructionPathTracer(root_dir=tmp_path)
        
        # Create a document
        doc = tmp_path / "test.md"
        doc.write_text("# Test Document\n\nNo references here.")
        
        root_node = tracer.trace_from_document(doc)
        
        assert root_node is not None
        assert root_node.title == "Test Document"
        assert len(root_node.children) == 0

    def test_trace_from_document_with_references(self, tmp_path):
        """Test tracing with document references."""
        tracer = InstructionPathTracer(root_dir=tmp_path)
        
        # Create main document with reference
        doc1 = tmp_path / "doc1.md"
        doc1.write_text("# Doc 1\n\nSee [Doc 2](doc2.md)")
        
        # Create referenced document
        doc2 = tmp_path / "doc2.md"
        doc2.write_text("# Doc 2\n\nContent")
        
        root_node = tracer.trace_from_document(doc1)
        
        assert root_node is not None
        assert len(root_node.children) == 1
        assert root_node.children[0].title == "Doc 2"

    def test_max_depth_limit(self, tmp_path):
        """Test that max depth is respected."""
        tracer = InstructionPathTracer(root_dir=tmp_path, max_depth=1)
        
        # Create chain of documents
        doc1 = tmp_path / "doc1.md"
        doc1.write_text("# Doc 1\n\nSee [Doc 2](doc2.md)")
        
        doc2 = tmp_path / "doc2.md"
        doc2.write_text("# Doc 2\n\nSee [Doc 3](doc3.md)")
        
        doc3 = tmp_path / "doc3.md"
        doc3.write_text("# Doc 3\n\nEnd")
        
        root_node = tracer.trace_from_document(doc1)
        
        # Should only trace to depth 1
        assert root_node is not None
        assert len(root_node.children) == 1
        assert len(root_node.children[0].children) == 0  # Doc3 not traced


if __name__ == "__main__":
    pytest.main([__file__])