"""Tests for reference_validator_merged module."""

from pathlib import Path

from src.reference_validator_merged import (
    DocumentParser,
    Reference,
    ReferenceGraph,
    ReferenceValidator,
    ValidationIssue,
    ValidationReport,
)


class TestReference:
    """Test Reference dataclass."""

    def test_reference_creation(self) -> None:
        """Test creating Reference instance."""
        ref = Reference(
            source_file=Path("source.md"),
            target_file=Path("target.md"),
            line_number=10,
            reference_text="[Link](target.md)",
            reference_type="markdown_link",
        )
        assert ref.source_file == Path("source.md")
        assert ref.target_file == Path("target.md")
        assert ref.line_number == 10
        assert ref.reference_type == "markdown_link"

    def test_reference_equality(self) -> None:
        """Test Reference equality comparison."""
        ref1 = Reference(Path("a.md"), Path("b.md"), 1, "[B](b.md)")
        ref2 = Reference(Path("a.md"), Path("b.md"), 1, "[B](b.md)")
        ref3 = Reference(Path("a.md"), Path("c.md"), 1, "[C](c.md)")

        assert ref1 == ref2
        assert ref1 != ref3


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_validation_issue_creation(self) -> None:
        """Test creating ValidationIssue instance."""
        issue = ValidationIssue(
            file_path=Path("test.md"),
            issue_type="broken_reference",
            message="Reference to missing.md not found",
            line_number=5,
            severity="error",
        )
        assert issue.file_path == Path("test.md")
        assert issue.issue_type == "broken_reference"
        assert issue.severity == "error"
        assert issue.line_number == 5


class TestDocumentParser:
    """Test DocumentParser class."""

    def test_extract_markdown_links(self) -> None:
        """Test extracting markdown links from content."""
        parser = DocumentParser()
        content = """# Document

Here's a [link to README](README.md).
And an [external link](https://example.com).
Also a [reference link][ref].

[ref]: ./reference.md
"""
        links = parser.extract_markdown_links(content)

        assert len(links) == 2  # Only internal links
        assert ("README.md", 3) in links
        assert ("./reference.md", 7) in links

    def test_extract_image_references(self) -> None:
        """Test extracting image references."""
        parser = DocumentParser()
        content = """# Document

![Alt text](images/diagram.png)
![Another image](../assets/logo.jpg)
![External](https://example.com/image.png)
"""
        images = parser.extract_image_references(content)

        assert len(images) == 2  # Only local images
        assert ("images/diagram.png", 3) in images
        assert ("../assets/logo.jpg", 4) in images

    def test_extract_include_directives(self) -> None:
        """Test extracting include directives."""
        parser = DocumentParser()
        content = """# Document

<!-- include: header.md -->
Some content
<!-- include: ../shared/footer.md -->
"""
        includes = parser.extract_include_directives(content)

        assert len(includes) == 2
        assert ("header.md", 3) in includes
        assert ("../shared/footer.md", 5) in includes

    def test_parse_document(self, tmp_path: Path) -> None:
        """Test parsing complete document."""
        content = """# Test Document

[Link 1](doc1.md)
![Image](img.png)
<!-- include: inc.md -->
[Link 2](doc2.md)
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        parser = DocumentParser()
        references = parser.parse_document(doc_path)

        assert len(references) == 4
        ref_targets = [r.target_file.name for r in references]
        assert "doc1.md" in ref_targets
        assert "doc2.md" in ref_targets
        assert "img.png" in ref_targets
        assert "inc.md" in ref_targets


class TestReferenceGraph:
    """Test ReferenceGraph class."""

    def test_add_reference(self) -> None:
        """Test adding references to graph."""
        graph = ReferenceGraph()

        ref1 = Reference(Path("a.md"), Path("b.md"), 1, "[B](b.md)")
        ref2 = Reference(Path("a.md"), Path("c.md"), 2, "[C](c.md)")
        ref3 = Reference(Path("b.md"), Path("c.md"), 1, "[C](c.md)")

        graph.add_reference(ref1)
        graph.add_reference(ref2)
        graph.add_reference(ref3)

        assert len(graph.get_outgoing_references(Path("a.md"))) == 2
        assert len(graph.get_outgoing_references(Path("b.md"))) == 1
        assert len(graph.get_incoming_references(Path("c.md"))) == 2

    def test_get_all_files(self) -> None:
        """Test getting all files in graph."""
        graph = ReferenceGraph()

        ref1 = Reference(Path("a.md"), Path("b.md"), 1, "")
        ref2 = Reference(Path("b.md"), Path("c.md"), 1, "")

        graph.add_reference(ref1)
        graph.add_reference(ref2)

        all_files = graph.get_all_files()
        assert len(all_files) == 3
        assert Path("a.md") in all_files
        assert Path("b.md") in all_files
        assert Path("c.md") in all_files

    def test_find_circular_dependencies(self) -> None:
        """Test finding circular dependencies."""
        graph = ReferenceGraph()

        # Create circular dependency: a -> b -> c -> a
        graph.add_reference(Reference(Path("a.md"), Path("b.md"), 1, ""))
        graph.add_reference(Reference(Path("b.md"), Path("c.md"), 1, ""))
        graph.add_reference(Reference(Path("c.md"), Path("a.md"), 1, ""))

        cycles = graph.find_circular_dependencies()
        assert len(cycles) > 0

        # Should find the cycle
        cycle_files = set()
        for cycle in cycles:
            cycle_files.update(cycle)

        assert Path("a.md") in cycle_files
        assert Path("b.md") in cycle_files
        assert Path("c.md") in cycle_files

    def test_find_orphaned_files(self, tmp_path: Path) -> None:
        """Test finding orphaned files."""
        # Create files
        (tmp_path / "referenced.md").write_text("# Referenced")
        (tmp_path / "orphaned.md").write_text("# Orphaned")
        (tmp_path / "index.md").write_text("[Link](referenced.md)")

        graph = ReferenceGraph()
        graph.add_reference(Reference(Path("index.md"), Path("referenced.md"), 1, ""))

        orphaned = graph.find_orphaned_files(tmp_path)

        assert len(orphaned) == 1
        assert Path("orphaned.md") in orphaned


class TestReferenceValidator:
    """Test ReferenceValidator class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test validator initialization."""
        validator = ReferenceValidator(tmp_path)
        assert validator.project_root == tmp_path
        assert isinstance(validator.parser, DocumentParser)
        assert isinstance(validator.graph, ReferenceGraph)
        assert validator.issues == []

    def test_validate_file_exists(self, tmp_path: Path) -> None:
        """Test validating file existence."""
        (tmp_path / "exists.md").write_text("# Exists")

        validator = ReferenceValidator(tmp_path)

        # Existing file
        assert validator.validate_file_exists(Path("exists.md")) is True

        # Non-existing file
        assert validator.validate_file_exists(Path("missing.md")) is False

    def test_resolve_reference(self, tmp_path: Path) -> None:
        """Test resolving relative references."""
        validator = ReferenceValidator(tmp_path)

        source = Path("docs/guide.md")

        # Same directory
        assert validator.resolve_reference("./intro.md", source) == Path("docs/intro.md")

        # Parent directory
        assert validator.resolve_reference("../README.md", source) == Path("README.md")

        # Absolute path from root
        assert validator.resolve_reference("docs/api.md", source) == Path("docs/api.md")

    def test_validate_single_reference(self, tmp_path: Path) -> None:
        """Test validating single reference."""
        (tmp_path / "target.md").write_text("# Target")

        validator = ReferenceValidator(tmp_path)

        # Valid reference
        ref_valid = Reference(Path("source.md"), Path("target.md"), 1, "[Target](target.md)")
        validator.validate_reference(ref_valid)
        assert len(validator.issues) == 0

        # Invalid reference
        ref_invalid = Reference(Path("source.md"), Path("missing.md"), 2, "[Missing](missing.md)")
        validator.validate_reference(ref_invalid)
        assert len(validator.issues) == 1
        assert validator.issues[0].issue_type == "broken_reference"

    def test_check_circular_dependencies(self) -> None:
        """Test checking for circular dependencies."""
        validator = ReferenceValidator(Path("/tmp"))

        # Create circular dependency
        validator.graph.add_reference(Reference(Path("a.md"), Path("b.md"), 1, ""))
        validator.graph.add_reference(Reference(Path("b.md"), Path("c.md"), 1, ""))
        validator.graph.add_reference(Reference(Path("c.md"), Path("a.md"), 1, ""))

        validator.check_circular_dependencies()

        circular_issues = [i for i in validator.issues if i.issue_type == "circular_dependency"]
        assert len(circular_issues) > 0

    def test_check_orphaned_files(self, tmp_path: Path) -> None:
        """Test checking for orphaned files."""
        # Create files
        (tmp_path / "index.md").write_text("[Used](used.md)")
        (tmp_path / "used.md").write_text("# Used")
        (tmp_path / "orphaned.md").write_text("# Orphaned")

        validator = ReferenceValidator(tmp_path)
        validator.scan_project()
        validator.check_orphaned_files()

        orphan_issues = [i for i in validator.issues if i.issue_type == "orphaned_file"]
        assert len(orphan_issues) > 0
        assert any("orphaned.md" in str(i.file_path) for i in orphan_issues)

    def test_full_validation(self, tmp_path: Path) -> None:
        """Test full project validation."""
        # Create test project structure
        (tmp_path / "README.md").write_text("""# Project

See [docs](docs/guide.md) for more info.
""")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("""# Guide

Check the [API docs](api.md).
Missing link: [broken](missing.md)
""")

        (docs_dir / "api.md").write_text("# API Documentation")
        (tmp_path / "orphaned.md").write_text("# Orphaned Document")

        validator = ReferenceValidator(tmp_path)
        report = validator.validate()

        assert report.total_files >= 4
        assert report.total_references >= 3
        assert len(report.issues) >= 2  # At least broken ref and orphaned file

        issue_types = {issue.issue_type for issue in report.issues}
        assert "broken_reference" in issue_types
        assert "orphaned_file" in issue_types


class TestValidationReport:
    """Test ValidationReport class."""

    def test_report_creation(self) -> None:
        """Test creating validation report."""
        issues = [
            ValidationIssue(Path("a.md"), "broken_reference", "Bad ref"),
            ValidationIssue(Path("b.md"), "orphaned_file", "Orphaned"),
        ]

        report = ValidationReport(
            total_files=10, total_references=25, issues=issues, circular_dependencies=[], orphaned_files=[Path("b.md")]
        )

        assert report.total_files == 10
        assert report.total_references == 25
        assert len(report.issues) == 2
        assert report.is_valid is False

    def test_report_summary(self) -> None:
        """Test generating report summary."""
        report = ValidationReport(
            total_files=5,
            total_references=10,
            issues=[
                ValidationIssue(Path("a.md"), "broken_reference", "Bad ref", severity="error"),
                ValidationIssue(Path("b.md"), "orphaned_file", "Orphaned", severity="warning"),
            ],
        )

        summary = report.get_summary()

        assert summary["total_files"] == 5
        assert summary["total_references"] == 10
        assert summary["total_issues"] == 2
        assert summary["errors"] == 1
        assert summary["warnings"] == 1

    def test_report_to_dict(self) -> None:
        """Test converting report to dictionary."""
        report = ValidationReport(
            total_files=3, total_references=5, issues=[ValidationIssue(Path("test.md"), "test", "Test issue")]
        )

        report_dict = report.to_dict()

        assert report_dict["total_files"] == 3
        assert report_dict["total_references"] == 5
        assert len(report_dict["issues"]) == 1
        assert report_dict["is_valid"] is False
