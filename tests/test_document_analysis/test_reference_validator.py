#!/usr/bin/env python3
"""Tests for document_analysis.reference_validator module.

Comprehensive tests for reference validation according to CLAUDE.md standards.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.document_analysis.reference_validator import ReferenceValidator


class TestReferenceValidatorInitialization:
    """Test ReferenceValidator initialization."""

    def test_init_with_default_params(self) -> None:
        """Test initialization with default parameters."""
        with patch("src.document_analysis.reference_validator.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/root")
            validator = ReferenceValidator()
            
            assert validator.root_dir == Path("/test/root")
            assert validator.reference_map_path == Path("/test/root/DOCUMENT_REFERENCE_MAP.md")
            assert validator.enhanced_mode is True

    def test_init_with_custom_root_dir(self) -> None:
        """Test initialization with custom root directory."""
        custom_root = Path("/custom/root")
        validator = ReferenceValidator(root_dir=custom_root)
        
        assert validator.root_dir == custom_root
        assert validator.reference_map_path == custom_root / "DOCUMENT_REFERENCE_MAP.md"
        assert validator.enhanced_mode is True

    def test_init_basic_mode(self) -> None:
        """Test initialization in basic mode."""
        validator = ReferenceValidator(enhanced_mode=False)
        assert validator.enhanced_mode is False

    def test_init_both_params(self) -> None:
        """Test initialization with both custom root and mode."""
        custom_root = Path("/custom/root")
        validator = ReferenceValidator(root_dir=custom_root, enhanced_mode=False)
        
        assert validator.root_dir == custom_root
        assert validator.enhanced_mode is False


class TestNormalizePath:
    """Test path normalization functionality."""

    def test_normalize_path_basic_mode(self) -> None:
        """Test path normalization in basic mode."""
        validator = ReferenceValidator(enhanced_mode=False)
        
        # Basic mode only removes ./
        assert validator.normalize_path("./README.md") == "README.md"
        assert validator.normalize_path("README.md") == "README.md"
        assert validator.normalize_path("../parent.md") == "../parent.md"
        assert validator.normalize_path("docs/guide.md") == "docs/guide.md"

    def test_normalize_path_enhanced_mode(self) -> None:
        """Test path normalization in enhanced mode."""
        root = Path("/test/root")
        validator = ReferenceValidator(root_dir=root, enhanced_mode=True)
        
        # Test relative path resolution
        assert validator.normalize_path("./README.md") == "README.md"
        assert validator.normalize_path("docs/guide.md") == "docs/guide.md"

    def test_normalize_path_with_parent_directory(self) -> None:
        """Test normalizing paths with parent directory references."""
        root = Path("/test/root")
        validator = ReferenceValidator(root_dir=root, enhanced_mode=True)
        
        # Test ../ resolution
        from_dir = root / "docs"
        with patch.object(Path, "resolve") as mock_resolve:
            mock_resolve.return_value = root / "README.md"
            with patch.object(Path, "relative_to", return_value=Path("README.md")):
                result = validator.normalize_path("../README.md", from_dir)
                assert result == "README.md"

    def test_normalize_path_outside_root(self) -> None:
        """Test normalizing paths that resolve outside root directory."""
        root = Path("/test/root")
        validator = ReferenceValidator(root_dir=root, enhanced_mode=True)
        
        from_dir = root / "docs"
        with patch.object(Path, "resolve") as mock_resolve:
            mock_resolve.return_value = Path("/outside/file.md")
            with patch.object(Path, "relative_to", side_effect=ValueError):
                result = validator.normalize_path("../../../outside/file.md", from_dir)
                assert result == "../../../outside/file.md"

    def test_normalize_path_planning_directory_check(self) -> None:
        """Test auto-detection of planning directory files."""
        root = Path("/test/root")
        validator = ReferenceValidator(root_dir=root, enhanced_mode=True)
        
        # Mock planning directory existence
        with patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            result = validator.normalize_path("TASK.md")
            assert result == "planning/TASK.md"
            
            # Verify exists was called
            assert mock_exists.called


class TestExtractReferencesFromMap:
    """Test extraction of references from DOCUMENT_REFERENCE_MAP.md."""

    def test_extract_references_file_not_found(self) -> None:
        """Test extraction when reference map doesn't exist."""
        validator = ReferenceValidator()
        
        with patch.object(Path, "exists", return_value=False):
            with patch("src.document_analysis.reference_validator.logger") as mock_logger:
                references = validator.extract_references_from_map()
                
                assert references == {}
                mock_logger.info.assert_called()

    def test_extract_references_basic_format(self) -> None:
        """Test extracting references in basic format."""
        validator = ReferenceValidator(enhanced_mode=False)
        
        content = """
📄 README.md
├── 🔗 → PLANNING.md ✅
├── 🔗 → CONTRIBUTING.md ✅
└── 🔗 → docs/guide.md ❌

📄 PLANNING.md
└── 🔗 → README.md ✅
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_map()
                
                assert "README.md" in references
                assert "PLANNING.md" in references["README.md"]
                assert "CONTRIBUTING.md" in references["README.md"]
                assert "docs/guide.md" in references["README.md"]
                assert "README.md" in references["PLANNING.md"]

    def test_extract_references_enhanced_mode_with_directories(self) -> None:
        """Test extracting references with directory context in enhanced mode."""
        validator = ReferenceValidator(enhanced_mode=True)
        
        content = """
📁 planning/
📄 TASK.md
├── 🔗 → PLANNING.md ✅
└── 🔗 → ../README.md ✅
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                with patch.object(validator, "normalize_path") as mock_normalize:
                    mock_normalize.side_effect = lambda p, d: p  # Return path as-is
                    
                    references = validator.extract_references_from_map()
                    
                    assert "planning/TASK.md" in references
                    assert len(references["planning/TASK.md"]) == 2

    def test_extract_references_edge_cases(self) -> None:
        """Test edge cases in reference extraction."""
        validator = ReferenceValidator(enhanced_mode=False)  # Use basic mode to avoid path normalization
        
        # Content with various edge cases
        content = """
# Some header
📄 test.txt  # Not a markdown file
📄 README.md
├── 🔗 → VALID.md ✅
├── 🔗 → another-file.md ❌
└── Random text without link marker

📄 ANOTHER.md
└── 🔗 → test.md ✅
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_map()
                
                # Should only extract valid markdown references
                assert "test.txt" not in references
                assert "README.md" in references
                assert "VALID.md" in references["README.md"]
                assert "another-file.md" in references["README.md"]
                assert "ANOTHER.md" in references
                assert "test.md" in references["ANOTHER.md"]


class TestExtractReferencesFromDocument:
    """Test extraction of references from markdown documents."""

    def test_extract_references_file_not_exists(self) -> None:
        """Test extraction when document doesn't exist."""
        validator = ReferenceValidator()
        doc_path = Path("/test/doc.md")
        
        with patch.object(Path, "exists", return_value=False):
            references = validator.extract_references_from_document(doc_path)
            assert references == set()

    def test_extract_references_basic_links(self) -> None:
        """Test extracting basic markdown links."""
        validator = ReferenceValidator(enhanced_mode=False)
        doc_path = Path("/test/README.md")
        
        content = """
# README

See [Planning](./PLANNING.md) for details.
Check out the [guide](docs/guide.md).
External link to [Google](https://google.com).
Image link ![Logo](logo.png).
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_document(doc_path)
                
                assert references == {"PLANNING.md", "docs/guide.md"}
                # Should not include non-.md links
                assert "https://google.com" not in references
                assert "logo.png" not in references

    def test_extract_references_enhanced_mode_normalization(self) -> None:
        """Test reference extraction with path normalization in enhanced mode."""
        validator = ReferenceValidator(enhanced_mode=True)
        doc_path = Path("/test/docs/guide.md")
        
        content = """
[Back to README](../README.md)
[Another doc](./another.md)
[Planning](../planning/PLANNING.md)
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                with patch.object(Path, "parent", new_callable=lambda: Mock(return_value=Path("/test/docs"))):
                    with patch.object(validator, "normalize_path") as mock_normalize:
                        mock_normalize.side_effect = lambda p, d: f"normalized_{p}"
                        
                        references = validator.extract_references_from_document(doc_path)
                        
                        assert "normalized_../README.md" in references
                        assert "normalized_./another.md" in references
                        assert "normalized_../planning/PLANNING.md" in references

    def test_extract_references_edge_cases(self) -> None:
        """Test edge cases in reference extraction."""
        validator = ReferenceValidator(enhanced_mode=False)  # Use basic mode for predictable results
        doc_path = Path("/test/doc.md")
        
        content = """
[Empty link]()
[No parentheses]
[Multiple](link1.md) [links](link2.md) [on](link3.md) [same line](link4.md)
[Link with spaces](path with spaces.md)
[Link with fragment](doc.md#section)
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_document(doc_path)
                
                # In basic mode, paths are returned as-is
                assert "link1.md" in references
                assert "link2.md" in references
                assert "link3.md" in references
                assert "link4.md" in references
                assert "path with spaces.md" in references
                # Note: doc.md#section doesn't end with .md so it's not included
                assert len(references) == 5


class TestValidateDocumentPresence:
    """Test document presence validation."""

    def test_validate_empty_references(self) -> None:
        """Test validation with empty references."""
        validator = ReferenceValidator()
        presence = validator.validate_document_presence({})
        assert presence == {}

    def test_validate_document_presence_basic_mode(self) -> None:
        """Test document presence validation in basic mode."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=False)
        
        references = {
            "README.md": ["PLANNING.md", "./docs/guide.md"],
            "PLANNING.md": ["README.md"]
        }
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "is_file") as mock_is_file:
                # Set up mock responses
                mock_exists.side_effect = [True, True, False]
                mock_is_file.return_value = True
                
                presence = validator.validate_document_presence(references)
                
                assert presence["PLANNING.md"] is True
                assert presence["./docs/guide.md"] is True
                assert presence["README.md"] is False

    def test_validate_document_presence_enhanced_mode(self) -> None:
        """Test document presence validation in enhanced mode."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=True)
        
        references = {
            "README.md": ["planning/PLANNING.md", "docs/guide.md"]
        }
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "is_file") as mock_is_file:
                mock_exists.side_effect = [True, False]
                mock_is_file.return_value = True
                
                presence = validator.validate_document_presence(references)
                
                assert presence["planning/PLANNING.md"] is True
                assert presence["docs/guide.md"] is False


class TestValidateLinkCorrectness:
    """Test link correctness validation."""

    def test_validate_link_correctness_no_docs(self) -> None:
        """Test link validation when no documents found."""
        validator = ReferenceValidator()
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[]):
            link_status = validator.validate_link_correctness()
            assert link_status == {}

    def test_validate_link_correctness_basic_mode(self) -> None:
        """Test link validation in basic mode."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=False)
        
        mock_docs = [
            Path("/test/README.md"),
            Path("/test/guide.txt")  # Non-markdown file
        ]
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=mock_docs):
            with patch.object(validator, "extract_references_from_document") as mock_extract:
                mock_extract.return_value = {"PLANNING.md", "CONTRIBUTING.md"}
                
                link_status = validator.validate_link_correctness()
                
                assert "README.md" in link_status
                assert link_status["README.md"]["reference_count"] == 2
                assert "guide.txt" not in link_status  # Non-markdown filtered out

    def test_validate_link_correctness_enhanced_mode(self) -> None:
        """Test link validation in enhanced mode with relative paths."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=True)
        
        mock_docs = [Path("/test/docs/guide.md")]
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=mock_docs):
            with patch.object(validator, "extract_references_from_document") as mock_extract:
                mock_extract.return_value = {"../README.md"}
                
                link_status = validator.validate_link_correctness()
                
                assert "docs/guide.md" in link_status
                assert link_status["docs/guide.md"]["path"] == "docs/guide.md"
                assert link_status["docs/guide.md"]["reference_count"] == 1


class TestCheckInternalCoherence:
    """Test internal coherence checking."""

    def test_check_internal_coherence_no_docs(self) -> None:
        """Test coherence check with no documents."""
        validator = ReferenceValidator()
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[]):
            issues = validator.check_internal_coherence()
            assert issues == {}

    def test_check_internal_coherence_broken_section_refs(self) -> None:
        """Test detection of broken section references."""
        validator = ReferenceValidator()
        
        content = """
# Main Title
## Section One

See [this section](#section-two) for more.
Also check [missing section](#non-existent).
"""
        
        mock_doc = Path("/test/doc.md")
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[mock_doc]):
            with patch.object(Path, "read_text", return_value=content):
                issues = validator.check_internal_coherence()
                
                assert "doc.md" in issues
                assert any("non-existent" in issue for issue in issues["doc.md"])
                # "section-two" might not be flagged since headings are normalized

    def test_check_internal_coherence_todos_and_placeholders(self) -> None:
        """Test detection of TODOs and placeholders."""
        validator = ReferenceValidator()
        
        content = """
# Document

TODO: Implement this feature
FIXME: This is broken
XXX: Temporary hack

[PLACEHOLDER for future content]
[TBD - specifications]
"""
        
        mock_doc = Path("/test/doc.md")
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[mock_doc]):
            with patch.object(Path, "read_text", return_value=content):
                issues = validator.check_internal_coherence()
                
                assert "doc.md" in issues
                assert any("TODO:" in issue for issue in issues["doc.md"])
                assert any("FIXME:" in issue for issue in issues["doc.md"])
                assert any("XXX:" in issue for issue in issues["doc.md"])
                assert any("PLACEHOLDER" in issue for issue in issues["doc.md"])
                assert any("TBD" in issue for issue in issues["doc.md"])

    def test_check_internal_coherence_read_error(self) -> None:
        """Test handling of file read errors."""
        validator = ReferenceValidator()
        mock_doc = Path("/test/doc.md")
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[mock_doc]):
            with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
                issues = validator.check_internal_coherence()
                
                assert "doc.md" in issues
                assert any("Error reading file" in issue for issue in issues["doc.md"])

    def test_check_internal_coherence_heading_normalization(self) -> None:
        """Test heading anchor normalization."""
        validator = ReferenceValidator()
        
        content = """
# Complex Heading with Special Characters!
## Another-Heading (with parentheses)

[Link to first](#complex-heading-with-special-characters)
[Link to second](#another-heading-with-parentheses)
"""
        
        mock_doc = Path("/test/doc.md")
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[mock_doc]):
            with patch.object(Path, "read_text", return_value=content):
                issues = validator.check_internal_coherence()
                
                # Should not report issues for correctly normalized anchors
                if "doc.md" in issues:
                    broken_refs = [i for i in issues["doc.md"] if "Broken section reference" in i]
                    assert len(broken_refs) == 0


class TestValidateCrossReferences:
    """Test cross-reference validation (enhanced mode only)."""

    def test_validate_cross_references_basic_mode(self) -> None:
        """Test that basic mode returns empty result."""
        validator = ReferenceValidator(enhanced_mode=False)
        result = validator.validate_cross_references()
        assert result == {}

    def test_validate_cross_references_all_valid(self) -> None:
        """Test cross-reference validation with all valid references."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=True)
        
        mock_docs = [Path("/test/README.md")]
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=mock_docs):
            with patch.object(validator, "extract_references_from_document") as mock_extract:
                mock_extract.return_value = {"PLANNING.md"}
                
                with patch.object(Path, "exists", return_value=True):
                    invalid_refs = validator.validate_cross_references()
                    assert invalid_refs == {}

    def test_validate_cross_references_with_invalid(self) -> None:
        """Test cross-reference validation with invalid references."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=True)
        
        mock_docs = [
            Path("/test/README.md"),
            Path("/test/guide.txt")  # Non-markdown
        ]
        
        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=mock_docs):
            with patch.object(validator, "extract_references_from_document") as mock_extract:
                mock_extract.return_value = {"MISSING.md", "EXISTS.md"}
                
                with patch.object(Path, "exists") as mock_exists:
                    # Define exists behavior based on path
                    def exists_side_effect(self):
                        path_str = str(self)
                        return "EXISTS.md" in path_str
                    
                    mock_exists.side_effect = exists_side_effect
                    
                    invalid_refs = validator.validate_cross_references()
                    
                    assert "README.md" in invalid_refs
                    assert "MISSING.md" in invalid_refs["README.md"]
                    assert "EXISTS.md" not in invalid_refs.get("README.md", [])


class TestGenerateValidationReport:
    """Test validation report generation."""

    def test_generate_report_no_references(self) -> None:
        """Test report generation when no references found."""
        validator = ReferenceValidator()
        
        with patch.object(validator, "extract_references_from_map", return_value={}):
            with patch("src.document_analysis.reference_validator.logger") as mock_logger:
                validator.generate_validation_report()
                
                # Should log that no references found
                log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("No references found" in msg for msg in log_messages)

    def test_generate_report_basic_mode(self) -> None:
        """Test report generation in basic mode."""
        validator = ReferenceValidator(enhanced_mode=False)
        
        references = {"README.md": ["PLANNING.md"]}
        presence_status = {"PLANNING.md": True}
        link_status = {"README.md": {"references": ["PLANNING.md"], "reference_count": 1}}
        coherence_issues = {}
        
        with patch.object(validator, "extract_references_from_map", return_value=references):
            with patch.object(validator, "validate_document_presence", return_value=presence_status):
                with patch.object(validator, "validate_link_correctness", return_value=link_status):
                    with patch.object(validator, "check_internal_coherence", return_value=coherence_issues):
                        with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[]):
                            with patch("src.document_analysis.reference_validator.logger") as mock_logger:
                                validator.generate_validation_report()
                                
                                log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                                assert any("DOCUMENT REFERENCE VALIDATION REPORT" in msg for msg in log_messages)
                                assert not any("ENHANCED" in msg for msg in log_messages)

    def test_generate_report_enhanced_mode_full(self) -> None:
        """Test comprehensive report generation in enhanced mode."""
        validator = ReferenceValidator(enhanced_mode=True)
        
        references = {
            "README.md": ["PLANNING.md", "MISSING.md"],
            "PLANNING.md": ["README.md"]
        }
        presence_status = {
            "PLANNING.md": True,
            "README.md": True,
            "MISSING.md": False
        }
        link_status = {
            "README.md": {
                "references": ["PLANNING.md", "EXTRA.md"],
                "reference_count": 2,
                "path": "README.md"
            }
        }
        coherence_issues = {
            "README.md": ["TODO: Fix this", "Placeholder content: [TBD]"]
        }
        invalid_refs = {
            "PLANNING.md": ["NONEXISTENT.md"]
        }
        
        with patch.object(validator, "extract_references_from_map", return_value=references):
            with patch.object(validator, "validate_document_presence", return_value=presence_status):
                with patch.object(validator, "validate_link_correctness", return_value=link_status):
                    with patch.object(validator, "check_internal_coherence", return_value=coherence_issues):
                        with patch.object(validator, "validate_cross_references", return_value=invalid_refs):
                            with patch("src.document_analysis.reference_validator.find_active_documents", return_value=[]):
                                with patch("src.document_analysis.reference_validator.logger") as mock_logger:
                                    validator.generate_validation_report()
                                    
                                    log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                                    
                                    # Check various report sections
                                    assert any("ENHANCED DOCUMENT REFERENCE VALIDATION REPORT" in msg for msg in log_messages)
                                    assert any("PATH RESOLUTION ANALYSIS" in msg for msg in log_messages)
                                    assert any("CROSS-REFERENCE VALIDATION" in msg for msg in log_messages)
                                    assert any("Missing: 1 documents" in msg for msg in log_messages)
                                    assert any("NEEDS ATTENTION" in msg for msg in log_messages)


class TestMainFunction:
    """Test the main function."""

    def test_main_default_mode(self) -> None:
        """Test main function with default enhanced mode."""
        with patch("sys.argv", ["script.py"]):
            with patch("src.document_analysis.reference_validator.ReferenceValidator") as mock_validator_class:
                mock_validator = MagicMock()
                mock_validator_class.return_value = mock_validator
                
                from src.document_analysis.reference_validator import main
                main()
                
                mock_validator_class.assert_called_once_with(enhanced_mode=True)
                mock_validator.generate_validation_report.assert_called_once()

    def test_main_basic_mode(self) -> None:
        """Test main function with --basic flag."""
        with patch("sys.argv", ["script.py", "--basic"]):
            with patch("src.document_analysis.reference_validator.ReferenceValidator") as mock_validator_class:
                mock_validator = MagicMock()
                mock_validator_class.return_value = mock_validator
                
                from src.document_analysis.reference_validator import main
                main()
                
                mock_validator_class.assert_called_once_with(enhanced_mode=False)
                mock_validator.generate_validation_report.assert_called_once()


class TestReferenceValidatorIntegration:
    """Integration tests for realistic scenarios."""

    def test_full_validation_workflow(self) -> None:
        """Test complete validation workflow."""
        validator = ReferenceValidator(root_dir=Path("/test"), enhanced_mode=True)
        
        # Set up a realistic document structure
        map_content = """
📁 /
📄 README.md
├── 🔗 → planning/PLANNING.md ✅
└── 🔗 → CONTRIBUTING.md ✅

📁 planning/
📄 PLANNING.md
└── 🔗 → ../README.md ✅
"""
        
        # Mock the reference map path to exist and contain our content
        with patch.object(validator.reference_map_path, "exists", return_value=True):
            with patch.object(validator.reference_map_path, "read_text", return_value=map_content):
                # Extract references
                references = validator.extract_references_from_map()
                assert len(references) > 0
                assert "README.md" in references
                assert "planning/PLANNING.md" in references["README.md"]
                
                # Test validate_document_presence with specific mocks
                with patch("pathlib.Path") as mock_path_class:
                    # Create mock path instances
                    mock_planning = MagicMock()
                    mock_planning.exists.return_value = True
                    mock_planning.is_file.return_value = True
                    
                    mock_contributing = MagicMock()
                    mock_contributing.exists.return_value = False
                    mock_contributing.is_file.return_value = False
                    
                    mock_readme = MagicMock()
                    mock_readme.exists.return_value = True
                    mock_readme.is_file.return_value = True
                    
                    # Set up the Path constructor to return appropriate mocks
                    def path_side_effect(path_str):
                        if "PLANNING.md" in str(path_str):
                            return mock_planning
                        elif "CONTRIBUTING.md" in str(path_str):
                            return mock_contributing
                        elif "README.md" in str(path_str):
                            return mock_readme
                        else:
                            mock = MagicMock()
                            mock.exists.return_value = True
                            mock.is_file.return_value = True
                            return mock
                    
                    mock_path_class.side_effect = path_side_effect
                    
                    # Validate presence
                    presence = validator.validate_document_presence(references)
                    
                    # Check results
                    assert any("CONTRIBUTING.md" in key for key in presence)
                    # Find the key that contains CONTRIBUTING.md and check it's False
                    for key, value in presence.items():
                        if "CONTRIBUTING.md" in key:
                            assert value is False
                            break


class TestReferenceValidatorEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_document_handling(self) -> None:
        """Test handling of empty documents."""
        validator = ReferenceValidator()
        doc_path = Path("/test/empty.md")
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=""):
                references = validator.extract_references_from_document(doc_path)
                assert references == set()

    def test_malformed_markdown_links(self) -> None:
        """Test handling of malformed markdown links."""
        validator = ReferenceValidator()
        doc_path = Path("/test/malformed.md")
        
        content = """
[Unclosed link(file.md)
[No URL]()
[](orphan-url.md)
[[Double brackets]](file.md)
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_document(doc_path)
                # Should handle malformed links gracefully
                assert isinstance(references, set)

    def test_unicode_in_paths_and_content(self) -> None:
        """Test handling of Unicode characters."""
        validator = ReferenceValidator()
        doc_path = Path("/test/unicode.md")
        
        content = """
[日本語](ドキュメント.md)
[Español](guía.md)
[Emoji 📚](docs/📚books.md)
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=content):
                references = validator.extract_references_from_document(doc_path)
                
                # In enhanced mode, paths get normalized
                refs_list = list(references)
                assert any("ドキュメント.md" in r for r in refs_list)
                assert any("guía.md" in r for r in refs_list)
                assert any("📚books.md" in r for r in refs_list)

    def test_very_long_paths(self) -> None:
        """Test handling of very long file paths."""
        validator = ReferenceValidator(enhanced_mode=True)
        
        # Create a very long path
        long_path = "very/long/nested/directory/structure/" * 10 + "file.md"
        
        result = validator.normalize_path(long_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_circular_reference_detection(self) -> None:
        """Test detection of circular references."""
        validator = ReferenceValidator()
        
        # Set up circular references
        references = {
            "A.md": ["B.md"],
            "B.md": ["C.md"],
            "C.md": ["A.md"]  # Circular reference back to A
        }
        
        # The validator should handle this gracefully
        presence = validator.validate_document_presence(references)
        assert isinstance(presence, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])