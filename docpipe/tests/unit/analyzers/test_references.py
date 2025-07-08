"""Tests for reference validator analyzer."""

import pytest
from pathlib import Path

from docpipe.analyzers import ReferenceValidator
from docpipe.models import ReferenceResults, IssueCategory


class TestReferenceValidator:
    """Test ReferenceValidator functionality."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = ReferenceValidator()
        assert analyzer.name == "ReferenceValidator"
        assert "references and links" in analyzer.description
        
    def test_analyze_valid_references(self, sample_project):
        """Test analyzing project with valid references."""
        analyzer = ReferenceValidator()
        result = analyzer.analyze(sample_project)
        
        assert result.success is True
        assert isinstance(result.data, ReferenceResults)
        
        ref_results = result.data
        assert ref_results.references_found > 0
        assert ref_results.valid_references > 0
        
        # README.md has valid references to CONTRIBUTING.md and PLANNING.md
        assert ref_results.validation_score > 0
        
    def test_analyze_broken_references(self, temp_dir):
        """Test analyzing documents with broken references."""
        # Create document with broken references
        content = """
        # Test Document
        
        See [Valid Link](existing.md) for details.
        See [Broken Link](nonexistent.md) for more info.
        Check [Another Broken](missing/file.md) reference.
        """
        
        (temp_dir / "test.md").write_text(content)
        (temp_dir / "existing.md").write_text("# Existing")
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        assert ref_results.references_found == 3
        assert ref_results.valid_references == 1
        assert len(ref_results.broken_references) == 2
        assert ref_results.has_broken_references is True
        
        # Check broken reference details
        broken_targets = [str(ref.target_file.name) for ref in ref_results.broken_references]
        assert "nonexistent.md" in broken_targets
        assert "file.md" in broken_targets
        
    def test_orphaned_documents(self, temp_dir):
        """Test detection of orphaned documents."""
        # Create documents where one is not referenced
        (temp_dir / "index.md").write_text("# Index\n\nSee [Doc A](doc_a.md)")
        (temp_dir / "doc_a.md").write_text("# Doc A\n\nBack to [Index](index.md)")
        (temp_dir / "orphaned.md").write_text("# Orphaned\n\nNobody links here")
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        assert len(ref_results.orphaned_documents) == 1
        assert ref_results.orphaned_documents[0].name == "orphaned.md"
        
    def test_external_links(self, temp_dir):
        """Test handling of external links."""
        content = """
        # External Links
        
        Visit [Google](https://www.google.com)
        See [GitHub](https://github.com/user/repo)
        """
        
        (temp_dir / "external.md").write_text(content)
        
        # Test with external link checking disabled (default)
        analyzer = ReferenceValidator({"check_external_links": False})
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        assert ref_results.references_found == 2
        assert ref_results.valid_references == 2  # External links assumed valid
        
    def test_anchor_links(self, temp_dir):
        """Test handling of anchor links."""
        content = """
        # Document
        
        ## Section One
        
        See [Section Two](#section-two)
        
        ## Section Two
        
        Back to [top](#)
        """
        
        (temp_dir / "anchors.md").write_text(content)
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        # Anchor links should be considered valid for now
        assert ref_results.broken_references == []
        
    def test_image_references(self, temp_dir):
        """Test handling of image references."""
        content = """
        # Images
        
        ![Valid Image](images/logo.png)
        ![Missing Image](images/missing.png)
        """
        
        (temp_dir / "images.md").write_text(content)
        (temp_dir / "images").mkdir()
        (temp_dir / "images" / "logo.png").write_text("fake image")
        
        analyzer = ReferenceValidator({"check_images": True})
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        assert ref_results.references_found == 2
        assert ref_results.valid_references == 1
        assert len(ref_results.broken_references) == 1
        
    def test_relative_paths(self, temp_dir):
        """Test handling of relative path references."""
        # Create nested structure
        (temp_dir / "docs").mkdir()
        (temp_dir / "docs" / "guide").mkdir()
        
        content = """
        # Guide
        
        See [Parent](../index.md)
        See [Sibling](./other.md)
        See [Root](../../README.md)
        """
        
        (temp_dir / "docs" / "guide" / "main.md").write_text(content)
        (temp_dir / "docs" / "index.md").write_text("# Index")
        (temp_dir / "docs" / "guide" / "other.md").write_text("# Other")
        (temp_dir / "README.md").write_text("# README")
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        # All relative paths should resolve correctly
        assert ref_results.validation_score == 100.0
        
    def test_single_file_analysis(self, temp_dir):
        """Test analyzing a single file."""
        content = """
        # Single File
        
        [Link 1](other.md)
        [Link 2](another.md)
        """
        
        test_file = temp_dir / "single.md"
        test_file.write_text(content)
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(test_file)
        
        ref_results = result.data
        assert ref_results.references_found == 2
        assert ref_results.valid_references == 0  # Both links broken
        assert len(ref_results.broken_references) == 2
        
    def test_markdown_only(self, temp_dir):
        """Test that only markdown files are processed."""
        # Create various file types
        (temp_dir / "doc.md").write_text("# Doc\n[Link](other.txt)")
        (temp_dir / "script.py").write_text("# Python file")
        (temp_dir / "other.txt").write_text("Text file")
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        # Should only process the .md file
        assert ref_results.references_found == 1
        
    def test_case_sensitivity(self, temp_dir):
        """Test case sensitivity in references."""
        (temp_dir / "Main.md").write_text("# Main\n[Link](sub.md)")
        (temp_dir / "Sub.MD").write_text("# Sub")  # Different case
        
        analyzer = ReferenceValidator()
        result = analyzer.analyze(temp_dir)
        
        ref_results = result.data
        # On case-sensitive systems, this should be broken
        # On case-insensitive systems, it might work
        # Just verify the analyzer runs without error
        assert result.success is True