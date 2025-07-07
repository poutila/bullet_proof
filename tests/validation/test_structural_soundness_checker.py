"""Tests for structural_soundness_checker module."""

import logging
from pathlib import Path
from unittest.mock import patch

from src.structural_soundness_checker import (
    CrossReferenceChecker,
    DocumentHierarchyAnalyzer,
    DocumentStructure,
    StructuralIssue,
    StructuralSoundnessChecker,
    TemplateValidator,
)


class TestStructuralIssue:
    """Test StructuralIssue dataclass."""

    def test_structural_issue_creation(self) -> None:
        """Test creating StructuralIssue instance."""
        issue = StructuralIssue(
            category="missing_citation",
            severity="warning",
            location="docs/architecture/design.md",
            message="Document not cited in DOCUMENTS.md",
            suggestion="Add reference to DOCUMENTS.md",
        )
        assert issue.category == "missing_citation"
        assert issue.severity == "warning"
        assert issue.location == "docs/architecture/design.md"
        assert issue.suggestion == "Add reference to DOCUMENTS.md"


class TestDocumentStructure:
    """Test DocumentStructure dataclass."""

    def test_document_structure_creation(self) -> None:
        """Test creating DocumentStructure instance."""
        structure = DocumentStructure(
            path=Path("docs/README.md"),
            title="Documentation",
            headers=["Introduction", "Usage", "API"],
            internal_links=["guide.md", "api.md"],
            external_links=["https://example.com"],
            citations=["DOCUMENTS.md"],
            is_template=False,
            template_markers=[],
        )
        assert structure.path == Path("docs/README.md")
        assert structure.title == "Documentation"
        assert len(structure.headers) == 3
        assert len(structure.internal_links) == 2
        assert structure.is_template is False


class TestTemplateValidator:
    """Test TemplateValidator class."""

    def test_identify_template(self) -> None:
        """Test identifying template files."""
        validator = TemplateValidator()

        template_content = """# [PROJECT_NAME] Template

[DESCRIPTION]

## [SECTION_NAME]

TODO: Fill in details
"""
        regular_content = """# Regular Document

This is a normal document without placeholders.
"""

        assert validator.is_template(template_content) is True
        assert validator.is_template(regular_content) is False

    def test_extract_template_markers(self) -> None:
        """Test extracting template markers."""
        validator = TemplateValidator()

        content = """# [PROJECT_NAME] Guide

Author: [AUTHOR_NAME]
Date: [DATE]

## [FEATURE_1]
[FEATURE_1_DESCRIPTION]

## Configuration
Set [CONFIG_VALUE] in config file.
"""
        markers = validator.extract_markers(content)

        assert len(markers) == 6
        assert "[PROJECT_NAME]" in markers
        assert "[AUTHOR_NAME]" in markers
        assert "[FEATURE_1]" in markers
        assert markers["[PROJECT_NAME]"] == 1  # Line 1
        assert markers["[FEATURE_1]"] == 6  # Line 6

    def test_validate_template_completeness(self) -> None:
        """Test validating template has all required markers."""
        validator = TemplateValidator()

        complete_template = """# [PROJECT_NAME] Template

[DESCRIPTION]

## Features
- [FEATURE_1]
- [FEATURE_2]

## Installation
[INSTALLATION_STEPS]
"""

        incomplete_template = """# Project Template

[DESCRIPTION]

## Features
- Feature 1
- Feature 2
"""

        complete_issues = validator.validate_template(complete_template, Path("template.md"))
        assert len(complete_issues) == 0

        incomplete_issues = validator.validate_template(incomplete_template, Path("template.md"))
        assert len(incomplete_issues) > 0
        assert any("PROJECT_NAME" in issue.message for issue in incomplete_issues)

    def test_check_template_outputs(self, tmp_path: Path) -> None:
        """Test checking if templates have corresponding outputs."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        outputs_dir = tmp_path / "generated"
        outputs_dir.mkdir()

        # Create template
        template = templates_dir / "project_template.md"
        template.write_text("# [PROJECT_NAME] Template")

        # Create output
        output = outputs_dir / "my_project.md"
        output.write_text("# My Project")

        validator = TemplateValidator()
        issues = validator.check_template_outputs(templates_dir, outputs_dir)

        # Should pass if output exists
        assert len(issues) == 0

        # Test missing output
        orphan_template = templates_dir / "orphan_template.md"
        orphan_template.write_text("# [NAME] Template")

        issues = validator.check_template_outputs(templates_dir, outputs_dir)
        assert len(issues) > 0
        assert any("orphan_template.md" in issue.location for issue in issues)


class TestDocumentHierarchyAnalyzer:
    """Test DocumentHierarchyAnalyzer class."""

    def test_analyze_document_structure(self, tmp_path: Path) -> None:
        """Test analyzing document structure."""
        content = """# Main Document

## Introduction
See [guide](guide.md) for details.

## Architecture
Refer to [design](docs/architecture/design.md).

## External Resources
- [Website](https://example.com)
- [Documentation](https://docs.example.com)
"""
        doc_path = tmp_path / "README.md"
        doc_path.write_text(content)

        analyzer = DocumentHierarchyAnalyzer(tmp_path)
        structure = analyzer.analyze_document(doc_path)

        assert structure.title == "Main Document"
        assert len(structure.headers) == 3
        assert "Introduction" in structure.headers
        assert len(structure.internal_links) == 2
        assert "guide.md" in structure.internal_links
        assert len(structure.external_links) == 2

    def test_build_hierarchy_tree(self, tmp_path: Path) -> None:
        """Test building document hierarchy tree."""
        # Create document structure
        (tmp_path / "README.md").write_text("""# Project
[Planning](planning/PLANNING.md)
[Docs](docs/index.md)
""")

        planning_dir = tmp_path / "planning"
        planning_dir.mkdir()
        (planning_dir / "PLANNING.md").write_text("""# Planning
[Tasks](TASKS.md)
""")
        (planning_dir / "TASKS.md").write_text("# Tasks")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("""# Documentation
[API](api.md)
""")
        (docs_dir / "api.md").write_text("# API")

        analyzer = DocumentHierarchyAnalyzer(tmp_path)
        hierarchy = analyzer.build_hierarchy()

        # Check README is at root
        assert "README.md" in hierarchy
        assert "planning/PLANNING.md" in hierarchy["README.md"]["children"]
        assert "docs/index.md" in hierarchy["README.md"]["children"]

        # Check nested structure
        assert "planning/TASKS.md" in hierarchy["planning/PLANNING.md"]["children"]
        assert "docs/api.md" in hierarchy["docs/index.md"]["children"]

    def test_find_orphaned_documents(self, tmp_path: Path) -> None:
        """Test finding orphaned documents."""
        # Create connected documents
        (tmp_path / "index.md").write_text("[Connected](connected.md)")
        (tmp_path / "connected.md").write_text("# Connected")

        # Create orphaned document
        (tmp_path / "orphaned.md").write_text("# Orphaned")

        analyzer = DocumentHierarchyAnalyzer(tmp_path)
        analyzer.build_hierarchy()
        orphaned = analyzer.find_orphaned_documents()

        assert len(orphaned) >= 1
        assert any("orphaned.md" in str(path) for path in orphaned)
        assert not any("connected.md" in str(path) for path in orphaned)


class TestCrossReferenceChecker:
    """Test CrossReferenceChecker class."""

    def test_check_architecture_citations(self, tmp_path: Path) -> None:
        """Test checking if architecture docs are cited."""
        # Create architecture docs
        arch_dir = tmp_path / "docs" / "architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "overview.md").write_text("# Architecture Overview")
        (arch_dir / "design.md").write_text("# System Design")

        # Create DOCUMENTS.md with citations
        documents_content = """# Project Documents

## Architecture
- [Overview](docs/architecture/overview.md)
"""
        (tmp_path / "DOCUMENTS.md").write_text(documents_content)

        checker = CrossReferenceChecker(tmp_path)
        issues = checker.check_architecture_citations()

        # Should have issue for uncited design.md
        assert len(issues) > 0
        assert any("design.md" in issue.location for issue in issues)
        assert not any("overview.md" in issue.location for issue in issues)

    def test_check_adr_citations(self, tmp_path: Path) -> None:
        """Test checking if ADRs are cited."""
        # Create ADR docs
        adr_dir = tmp_path / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "0001-use-python.md").write_text("# ADR-0001: Use Python")
        (adr_dir / "0002-use-pytest.md").write_text("# ADR-0002: Use Pytest")

        # Create DOCUMENTS.md without ADR citations
        (tmp_path / "DOCUMENTS.md").write_text("# Documents\n\nNo ADRs listed.")

        checker = CrossReferenceChecker(tmp_path)
        issues = checker.check_adr_citations()

        # Should have issues for both uncited ADRs
        assert len(issues) >= 2
        assert any("0001-use-python.md" in issue.location for issue in issues)
        assert any("0002-use-pytest.md" in issue.location for issue in issues)

    def test_validate_cross_references(self, tmp_path: Path) -> None:
        """Test validating cross-references between documents."""
        # Create documents with cross-references
        (tmp_path / "README.md").write_text("[Planning](PLANNING.md)")
        (tmp_path / "PLANNING.md").write_text("[Tasks](TASKS.md)")
        (tmp_path / "TASKS.md").write_text("[Missing](MISSING.md)")

        checker = CrossReferenceChecker(tmp_path)
        issues = checker.validate_cross_references()

        # Should find broken reference to MISSING.md
        assert len(issues) > 0
        assert any("MISSING.md" in issue.message for issue in issues)


class TestStructuralSoundnessChecker:
    """Test main StructuralSoundnessChecker class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test checker initialization."""
        checker = StructuralSoundnessChecker(tmp_path)
        assert checker.project_root == tmp_path
        assert isinstance(checker.template_validator, TemplateValidator)
        assert isinstance(checker.hierarchy_analyzer, DocumentHierarchyAnalyzer)
        assert isinstance(checker.cross_ref_checker, CrossReferenceChecker)

    def test_check_all(self, tmp_path: Path, caplog) -> None:
        """Test running all structural checks."""
        # Set up minimal project structure
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / "DOCUMENTS.md").write_text("# Documents")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create architecture doc
        arch_dir = docs_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "design.md").write_text("# Design")

        # Create ADR
        adr_dir = docs_dir / "adr"
        adr_dir.mkdir()
        (adr_dir / "0001-decision.md").write_text("# Decision")

        # Create template
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "template.md").write_text("# [NAME] Template")

        with caplog.at_level(logging.INFO):
            checker = StructuralSoundnessChecker(tmp_path)
            all_issues = checker.check_all()

        # Should find various issues
        assert len(all_issues) > 0

        # Check that all check types ran
        assert "STRUCTURAL SOUNDNESS ANALYSIS" in caplog.text
        assert "Checking Architecture Citations" in caplog.text
        assert "Checking ADR Citations" in caplog.text
        assert "Checking Templates" in caplog.text

    def test_generate_report(self, tmp_path: Path) -> None:
        """Test generating structural soundness report."""
        checker = StructuralSoundnessChecker(tmp_path)

        # Add some mock issues
        issues = [
            StructuralIssue("missing_citation", "warning", "test.md", "Not cited"),
            StructuralIssue("broken_reference", "error", "doc.md", "Broken ref"),
            StructuralIssue("template_issue", "info", "template.md", "Missing marker"),
        ]

        report = checker.generate_report(issues)

        assert "Total Issues: 3" in report
        assert "Errors: 1" in report
        assert "Warnings: 1" in report
        assert "Info: 1" in report
        assert "missing_citation" in report
        assert "broken_reference" in report
        assert "template_issue" in report

    def test_main_function(self, tmp_path: Path) -> None:
        """Test main function execution."""
        # Create minimal structure
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "DOCUMENTS.md").write_text("# Documents")

        with patch("sys.argv", ["checker", str(tmp_path)]):
            from validation.structural_soundness_checker import main

            # Should run without errors
            try:
                main()
            except SystemExit as e:
                # Check exit code (0 = success, 1 = issues found)
                assert e.code in [0, 1]
