"""Tests for validation module."""

from pathlib import Path

from src.validation import (
    ContentValidator,
    DocumentValidator,
    MetadataValidator,
    ReferenceValidator,
    StructureValidator,
    ValidationResult,
    ValidationRule,
    Validator,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_success(self) -> None:
        """Test creating successful validation result."""
        result = ValidationResult(
            passed=True, rule="test-rule", message="Validation passed", details={"checked": 10, "passed": 10}
        )
        assert result.passed is True
        assert result.rule == "test-rule"
        assert result.message == "Validation passed"
        assert result.details["checked"] == 10

    def test_validation_result_failure(self) -> None:
        """Test creating failed validation result."""
        result = ValidationResult(
            passed=False,
            rule="test-rule",
            message="Validation failed",
            details={"errors": ["Error 1", "Error 2"]},
            severity="error",
        )
        assert result.passed is False
        assert result.severity == "error"
        assert len(result.details["errors"]) == 2


class TestValidationRule:
    """Test ValidationRule class."""

    def test_validation_rule_creation(self) -> None:
        """Test creating validation rule."""

        def test_validator(content: str) -> bool:
            return len(content) > 0

        rule = ValidationRule(
            name="non-empty", description="Content must not be empty", validator=test_validator, severity="error"
        )

        assert rule.name == "non-empty"
        assert rule.description == "Content must not be empty"
        assert rule.severity == "error"
        assert rule.validator("test") is True
        assert rule.validator("") is False

    def test_validation_rule_with_custom_message(self) -> None:
        """Test validation rule with custom message function."""

        def validator(content: str) -> bool:
            return len(content) <= 100

        def message_func(content: str) -> str:
            return f"Content too long: {len(content)} characters"

        rule = ValidationRule(
            name="max-length", description="Content must be <= 100 chars", validator=validator, message_func=message_func
        )

        long_content = "x" * 150
        assert rule.validator(long_content) is False
        assert rule.message_func(long_content) == "Content too long: 150 characters"


class TestValidator:
    """Test base Validator class."""

    def test_validator_add_rule(self) -> None:
        """Test adding rules to validator."""
        validator = Validator()

        rule1 = ValidationRule("rule1", "Test rule 1", lambda x: True)
        rule2 = ValidationRule("rule2", "Test rule 2", lambda x: False)

        validator.add_rule(rule1)
        validator.add_rule(rule2)

        assert len(validator.rules) == 2
        assert validator.rules[0].name == "rule1"
        assert validator.rules[1].name == "rule2"

    def test_validator_validate_all_pass(self) -> None:
        """Test validation when all rules pass."""
        validator = Validator()

        rule1 = ValidationRule("rule1", "Test 1", lambda x: True)
        rule2 = ValidationRule("rule2", "Test 2", lambda x: True)

        validator.add_rule(rule1)
        validator.add_rule(rule2)

        results = validator.validate("test content")

        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_validator_validate_with_failures(self) -> None:
        """Test validation with some failures."""
        validator = Validator()

        rule1 = ValidationRule("pass", "Should pass", lambda x: True)
        rule2 = ValidationRule("fail", "Should fail", lambda x: False)

        validator.add_rule(rule1)
        validator.add_rule(rule2)

        results = validator.validate("test content")

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False


class TestDocumentValidator:
    """Test DocumentValidator class."""

    def test_document_validator_initialization(self) -> None:
        """Test document validator initialization."""
        validator = DocumentValidator()

        # Should have default rules
        assert len(validator.rules) > 0
        rule_names = [r.name for r in validator.rules]
        assert "has-title" in rule_names
        assert "valid-markdown" in rule_names

    def test_validate_document_with_title(self, tmp_path: Path) -> None:
        """Test validating document with title."""
        content = "# Document Title\n\nContent here."
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = DocumentValidator()
        results = validator.validate_file(doc_path)

        title_result = next((r for r in results if r.rule == "has-title"), None)
        assert title_result is not None
        assert title_result.passed is True

    def test_validate_document_no_title(self, tmp_path: Path) -> None:
        """Test validating document without title."""
        content = "Just some content without a header."
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = DocumentValidator()
        results = validator.validate_file(doc_path)

        title_result = next((r for r in results if r.rule == "has-title"), None)
        assert title_result is not None
        assert title_result.passed is False

    def test_validate_markdown_syntax(self, tmp_path: Path) -> None:
        """Test markdown syntax validation."""
        valid_md = """# Title

## Section

- List item
- Another item

[Link](url.md)
"""
        doc_path = tmp_path / "valid.md"
        doc_path.write_text(valid_md)

        validator = DocumentValidator()
        results = validator.validate_file(doc_path)

        md_result = next((r for r in results if r.rule == "valid-markdown"), None)
        assert md_result is not None
        assert md_result.passed is True


class TestReferenceValidator:
    """Test ReferenceValidator class."""

    def test_validate_internal_references(self, tmp_path: Path) -> None:
        """Test validating internal document references."""
        # Create documents
        (tmp_path / "index.md").write_text("[Valid](other.md)")
        (tmp_path / "other.md").write_text("# Other")

        content_with_refs = """
[Valid Link](other.md)
[Invalid Link](missing.md)
[External](https://example.com)
"""
        doc_path = tmp_path / "doc.md"
        doc_path.write_text(content_with_refs)

        validator = ReferenceValidator(tmp_path)
        results = validator.validate_file(doc_path)

        ref_result = next((r for r in results if r.rule == "valid-references"), None)
        assert ref_result is not None
        assert ref_result.passed is False  # Has invalid reference
        assert "missing.md" in ref_result.message

    def test_validate_no_broken_references(self, tmp_path: Path) -> None:
        """Test when all references are valid."""
        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")

        content = "[Link 1](doc1.md) and [Link 2](doc2.md)"
        doc_path = tmp_path / "index.md"
        doc_path.write_text(content)

        validator = ReferenceValidator(tmp_path)
        results = validator.validate_file(doc_path)

        ref_result = next((r for r in results if r.rule == "valid-references"), None)
        assert ref_result.passed is True

    def test_validate_circular_references(self, tmp_path: Path) -> None:
        """Test detecting circular references."""
        (tmp_path / "a.md").write_text("[Link to B](b.md)")
        (tmp_path / "b.md").write_text("[Link to C](c.md)")
        (tmp_path / "c.md").write_text("[Link to A](a.md)")

        validator = ReferenceValidator(tmp_path)
        validator.add_rule(
            ValidationRule(
                "no-circular-refs",
                "No circular references",
                lambda x: True,  # Simplified for test
            )
        )

        # Would need to implement circular reference detection
        # This is a placeholder to show the test structure


class TestStructureValidator:
    """Test StructureValidator class."""

    def test_validate_heading_hierarchy(self, tmp_path: Path) -> None:
        """Test validating heading hierarchy."""
        valid_structure = """# Main Title

## Section 1
### Subsection 1.1
### Subsection 1.2

## Section 2
### Subsection 2.1
"""
        doc_path = tmp_path / "valid.md"
        doc_path.write_text(valid_structure)

        validator = StructureValidator()
        results = validator.validate_file(doc_path)

        hierarchy_result = next((r for r in results if r.rule == "heading-hierarchy"), None)
        assert hierarchy_result is not None
        assert hierarchy_result.passed is True

    def test_validate_invalid_hierarchy(self, tmp_path: Path) -> None:
        """Test invalid heading hierarchy."""
        invalid_structure = """# Title

### Skipped H2!

## Back to H2
"""
        doc_path = tmp_path / "invalid.md"
        doc_path.write_text(invalid_structure)

        validator = StructureValidator()
        results = validator.validate_file(doc_path)

        hierarchy_result = next((r for r in results if r.rule == "heading-hierarchy"), None)
        assert hierarchy_result.passed is False

    def test_validate_consistent_formatting(self, tmp_path: Path) -> None:
        """Test consistent formatting validation."""
        inconsistent = """# Title

- item 1
* item 2  # Different bullet style
- item 3
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(inconsistent)

        validator = StructureValidator()
        results = validator.validate_file(doc_path)

        # Check for formatting consistency
        assert any(not r.passed for r in results)


class TestContentValidator:
    """Test ContentValidator class."""

    def test_validate_no_empty_sections(self, tmp_path: Path) -> None:
        """Test detecting empty sections."""
        content = """# Title

## Section 1
Content here.

## Section 2

## Section 3
More content.
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = ContentValidator()
        results = validator.validate_file(doc_path)

        empty_result = next((r for r in results if r.rule == "no-empty-sections"), None)
        assert empty_result is not None
        assert empty_result.passed is False
        assert "Section 2" in empty_result.message

    def test_validate_no_todos(self, tmp_path: Path) -> None:
        """Test detecting TODO items."""
        content = """# Document

This is done.

TODO: Fix this section

More content here.
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = ContentValidator()
        results = validator.validate_file(doc_path)

        todo_result = next((r for r in results if r.rule == "no-todos"), None)
        assert todo_result is not None
        assert todo_result.passed is False

    def test_validate_spell_check(self, tmp_path: Path) -> None:
        """Test spell checking validation."""
        content = """# Document

This is a correcty spelled document.
No problms here at all.
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = ContentValidator()
        # Would need spell checker integration
        # This shows the test structure


class TestMetadataValidator:
    """Test MetadataValidator class."""

    def test_validate_required_metadata(self, tmp_path: Path) -> None:
        """Test validating required metadata fields."""
        content = """---
title: Test Document
author: Test Author
date: 2024-01-01
---

# Content
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = MetadataValidator(required_fields=["title", "author", "date"])
        results = validator.validate_file(doc_path)

        metadata_result = next((r for r in results if r.rule == "required-metadata"), None)
        assert metadata_result is not None
        assert metadata_result.passed is True

    def test_validate_missing_metadata(self, tmp_path: Path) -> None:
        """Test detecting missing metadata."""
        content = """---
title: Test Document
---

# Content
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        validator = MetadataValidator(required_fields=["title", "author", "date"])
        results = validator.validate_file(doc_path)

        metadata_result = next((r for r in results if r.rule == "required-metadata"), None)
        assert metadata_result.passed is False
        assert "author" in metadata_result.message
        assert "date" in metadata_result.message

    def test_validate_metadata_schema(self, tmp_path: Path) -> None:
        """Test validating metadata against schema."""
        content = """---
title: Test
version: "not-a-number"
tags: "should-be-list"
---

# Content
"""
        doc_path = tmp_path / "test.md"
        doc_path.write_text(content)

        schema = {"version": {"type": "number"}, "tags": {"type": "list"}}

        validator = MetadataValidator(schema=schema)
        results = validator.validate_file(doc_path)

        # Would validate against schema
        assert len(results) > 0
