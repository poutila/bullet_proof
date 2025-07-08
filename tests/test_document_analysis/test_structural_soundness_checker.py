#!/usr/bin/env python3
"""Tests for document_analysis.structural_soundness_checker module.

Comprehensive tests for structural soundness checking according to CLAUDE.md standards.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.document_analysis.structural_soundness_checker import (
    CitationCheck,
    StructuralSoundnessChecker,
    TemplateMapping,
)


class TestDataClasses:
    """Test data classes used by the structural soundness checker."""

    def test_template_mapping_creation(self) -> None:
        """Test creating a TemplateMapping dataclass."""
        template_path = Path("/test/template.md")
        mapping = TemplateMapping(
            template_path=template_path,
            template_name="template.md",
            expected_outputs=["output1.yml", "output2.json"],
            actual_outputs=["output1.yml"],
            instructions=["Create a workflow", "Generate config"],
            generation_commands=["generate-workflow", "make config"]
        )
        
        assert mapping.template_path == template_path
        assert mapping.template_name == "template.md"
        assert len(mapping.expected_outputs) == 2
        assert len(mapping.actual_outputs) == 1
        assert len(mapping.instructions) == 2
        assert len(mapping.generation_commands) == 2

    def test_citation_check_creation(self) -> None:
        """Test creating a CitationCheck dataclass."""
        doc_path = Path("/test/docs/adr/001-decision.md")
        check = CitationCheck(
            document_path=doc_path,
            cited_in_documents=["Direct mention: 001-decision.md"],
            expected_citations=["docs/adr/001-decision.md", "001-decision.md"],
            missing_citations=[]
        )
        
        assert check.document_path == doc_path
        assert len(check.cited_in_documents) == 1
        assert len(check.expected_citations) == 2
        assert len(check.missing_citations) == 0


class TestStructuralSoundnessCheckerInitialization:
    """Test initialization of StructuralSoundnessChecker."""

    def test_init_with_default_params(self) -> None:
        """Test initialization with default parameters."""
        with patch("src.document_analysis.structural_soundness_checker.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/root")
            checker = StructuralSoundnessChecker()
            
            assert checker.root_dir == Path("/test/root")
            assert checker.documents_md_path == Path("/test/root/planning/DOCUMENTS.md")
            assert len(checker.template_patterns) > 0
            assert len(checker.command_patterns) > 0

    def test_init_with_custom_root(self) -> None:
        """Test initialization with custom root directory."""
        custom_root = Path("/custom/root")
        checker = StructuralSoundnessChecker(root_dir=custom_root)
        
        assert checker.root_dir == custom_root
        assert checker.documents_md_path == custom_root / "planning" / "DOCUMENTS.md"

    def test_pattern_compilation(self) -> None:
        """Test that regex patterns compile successfully."""
        checker = StructuralSoundnessChecker()
        
        # Test template patterns
        for pattern in checker.template_patterns:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")
        
        # Test command patterns
        for pattern in checker.command_patterns:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")


class TestFindAdrAndArchitectureFiles:
    """Test finding ADR and architecture files."""

    def test_find_files_both_directories_exist(self) -> None:
        """Test finding files when both ADR and architecture directories exist."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        # Mock directory structure
        mock_adr_files = [
            Path("/test/docs/adr/001-decision.md"),
            Path("/test/docs/adr/002-another.md"),
            Path("/test/docs/adr/template.md")  # Should be excluded
        ]
        
        mock_arch_files = [
            Path("/test/docs/architecture/system-design.md"),
            Path("/test/docs/architecture/components.md")
        ]
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "rglob") as mock_rglob:
                # Setup exists to return True for both directories
                mock_exists.side_effect = lambda: True
                
                # Setup rglob to return appropriate files
                def rglob_side_effect(pattern):
                    # Get the path from the calling context
                    if mock_rglob.call_count == 1:  # First call is for ADR
                        # Filter out template.md
                        return [f for f in mock_adr_files if f.name != "template.md"]
                    else:  # Second call is for architecture
                        return mock_arch_files
                
                mock_rglob.side_effect = rglob_side_effect
                
                adr_files, arch_files = checker.find_adr_and_architecture_files()
                
                # Template should be excluded from ADR files
                assert len(adr_files) == 2
                assert all(f.name != "template.md" for f in adr_files)
                assert len(arch_files) == 2

    def test_find_files_no_directories(self) -> None:
        """Test finding files when directories don't exist."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        with patch.object(Path, "exists", return_value=False):
            adr_files, arch_files = checker.find_adr_and_architecture_files()
            
            assert adr_files == []
            assert arch_files == []

    def test_find_files_only_adr_exists(self) -> None:
        """Test finding files when only ADR directory exists."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        mock_adr_files = [Path("/test/docs/adr/001-decision.md")]
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "rglob") as mock_rglob:
                mock_exists.side_effect = lambda: "adr" in str(mock_exists.call_args[0][0]) if mock_exists.call_args else False
                mock_rglob.return_value = mock_adr_files
                
                adr_files, arch_files = checker.find_adr_and_architecture_files()
                
                assert len(adr_files) == 1
                assert arch_files == []


class TestCheckCitationsInDocumentsMd:
    """Test checking citations in DOCUMENTS.md."""

    def test_check_citations_no_documents_md(self) -> None:
        """Test checking citations when DOCUMENTS.md doesn't exist."""
        checker = StructuralSoundnessChecker()
        
        with patch.object(Path, "exists", return_value=False):
            results = checker.check_citations_in_documents_md([Path("/test/file.md")])
            assert results == []

    def test_check_citations_direct_mention(self) -> None:
        """Test detecting direct file name mentions."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        documents_content = """
# Documents

Here we mention 001-decision.md directly.
Also see system-design.md for details.
"""
        
        files_to_check = [
            Path("/test/docs/adr/001-decision.md"),
            Path("/test/docs/architecture/system-design.md"),
            Path("/test/docs/missing.md")
        ]
        
        with patch.object(checker.documents_md_path, "exists", return_value=True):
            with patch.object(checker.documents_md_path, "read_text", return_value=documents_content):
                results = checker.check_citations_in_documents_md(files_to_check)
                
                assert len(results) == 3
                
                # Check first file (should be found)
                assert results[0].document_path == files_to_check[0]
                assert any("Direct mention" in citation for citation in results[0].cited_in_documents)
                assert results[0].missing_citations == []
                
                # Check second file (should be found)
                assert results[1].document_path == files_to_check[1]
                assert any("Direct mention" in citation for citation in results[1].cited_in_documents)
                
                # Check third file (should not be found)
                assert results[2].document_path == files_to_check[2]
                assert results[2].cited_in_documents == []
                assert len(results[2].missing_citations) > 0

    def test_check_citations_markdown_links(self) -> None:
        """Test detecting markdown link citations."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        documents_content = """
# Documents

See [ADR 001](docs/adr/001-decision.md) for details.
Check [Architecture](docs/architecture/system-design.md).
"""
        
        files_to_check = [
            Path("/test/docs/adr/001-decision.md"),
            Path("/test/docs/architecture/system-design.md")
        ]
        
        with patch.object(checker.documents_md_path, "exists", return_value=True):
            with patch.object(checker.documents_md_path, "read_text", return_value=documents_content):
                results = checker.check_citations_in_documents_md(files_to_check)
                
                assert len(results) == 2
                assert all(any("Markdown link" in c for c in r.cited_in_documents) for r in results)

    def test_check_citations_directory_mention(self) -> None:
        """Test detecting directory mentions."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        documents_content = """
# Documents

All files in the adr directory are important.
The architecture folder contains system designs.
"""
        
        files_to_check = [
            Path("/test/docs/adr/001-decision.md"),
            Path("/test/docs/architecture/system-design.md")
        ]
        
        with patch.object(checker.documents_md_path, "exists", return_value=True):
            with patch.object(checker.documents_md_path, "read_text", return_value=documents_content):
                results = checker.check_citations_in_documents_md(files_to_check)
                
                # Files in adr and architecture directories should be considered cited
                assert all(any("Directory mention" in c for c in r.cited_in_documents) for r in results)


class TestExtractTemplateMappings:
    """Test extracting template mappings from files."""

    def test_extract_mappings_empty_list(self) -> None:
        """Test extracting mappings from empty file list."""
        checker = StructuralSoundnessChecker()
        mappings = checker.extract_template_mappings([])
        assert mappings == []

    def test_extract_mappings_basic_template(self) -> None:
        """Test extracting mappings from a basic template."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        template_content = """
# Workflow Template

This template generates: `workflow.yml`
It also creates: build.json

## Instructions
- You must create the workflow file
- You should implement the build configuration

## Commands
```bash
generate-workflow --output workflow.yml
```
"""
        
        template_path = Path("/test/templates/workflow-template.md")
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "read_text", return_value=template_content):
                # Mock existence checks for expected outputs
                # First call checks template existence, rest check output paths
                mock_exists.side_effect = [True] + ["workflow.yml" in str(path) and ".github" in str(path) for path in [
                    checker.root_dir / "workflow.yml",
                    checker.root_dir / ".github" / "workflow.yml",
                    checker.root_dir / ".github" / "workflows" / "workflow.yml",
                    checker.root_dir / "scripts" / "workflow.yml",
                    checker.root_dir / "src" / "workflow.yml",
                    checker.root_dir / "docs" / "workflow.yml",
                    checker.root_dir / "planning" / "workflow.yml",
                ]] * 2  # For both expected outputs
                
                mappings = checker.extract_template_mappings([template_path])
                
                assert len(mappings) == 1
                mapping = mappings[0]
                
                assert mapping.template_path == template_path
                assert "workflow.yml" in mapping.expected_outputs
                assert "build.json" in mapping.expected_outputs
                assert len(mapping.instructions) > 0
                assert len(mapping.generation_commands) > 0
                assert any("workflow" in cmd for cmd in mapping.generation_commands)

    def test_extract_mappings_multiple_patterns(self) -> None:
        """Test extracting outputs using various patterns."""
        checker = StructuralSoundnessChecker()
        
        template_content = """
Creates: config.yml
Outputs: script.sh
Produces data.json
→ report.txt
Target file: test.py
"""
        
        template_path = Path("/test/template.md")
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=template_content):
                mappings = checker.extract_template_mappings([template_path])
                
                assert len(mappings) == 1
                expected = {"config.yml", "script.sh", "data.json", "report.txt", "test.py"}
                assert set(mappings[0].expected_outputs) == expected

    def test_extract_mappings_file_not_exists(self) -> None:
        """Test handling non-existent template files."""
        checker = StructuralSoundnessChecker()
        
        template_path = Path("/test/nonexistent.md")
        
        with patch.object(Path, "exists", return_value=False):
            mappings = checker.extract_template_mappings([template_path])
            assert mappings == []

    def test_extract_mappings_with_actual_outputs(self) -> None:
        """Test detecting actual outputs that exist."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        template_content = "Creates: workflow.yml"
        template_path = Path("/test/template.md")
        
        with patch.object(Path, "exists") as mock_exists:
            with patch.object(Path, "read_text", return_value=template_content):
                # First call is for template existence, subsequent calls check output paths
                mock_exists.side_effect = [True, False, True, False, False, False, False, False]
                
                mappings = checker.extract_template_mappings([template_path])
                
                assert len(mappings) == 1
                assert "workflow.yml" in mappings[0].expected_outputs
                assert len(mappings[0].actual_outputs) == 1


class TestFindTemplateFiles:
    """Test finding template files in the project."""

    def test_find_template_files_by_name(self) -> None:
        """Test finding templates by filename."""
        checker = StructuralSoundnessChecker()
        
        mock_docs = [
            Path("/test/template.md"),
            Path("/test/workflow-template.md"),
            Path("/test/automation-plan.md"),
            Path("/test/regular-doc.md"),
            Path("/test/readme.txt")  # Non-markdown
        ]
        
        with patch("src.document_analysis.structural_soundness_checker.find_active_documents", return_value=mock_docs):
            templates = checker.find_template_files()
            
            # Should find files with template/automation/plan in name
            assert len(templates) == 3
            assert all(doc.name.endswith(".md") for doc in templates)
            assert Path("/test/regular-doc.md") not in templates
            assert Path("/test/readme.txt") not in templates

    def test_find_template_files_by_content(self) -> None:
        """Test finding templates by content indicators."""
        checker = StructuralSoundnessChecker()
        
        mock_docs = [
            Path("/test/doc1.md"),
            Path("/test/doc2.md"),
            Path("/test/doc3.md")
        ]
        
        contents = {
            "/test/doc1.md": "This document generates: workflow.yml",
            "/test/doc2.md": "Regular documentation without template indicators",
            "/test/doc3.md": "Creates a .github/workflows file"
        }
        
        with patch("src.document_analysis.structural_soundness_checker.find_active_documents", return_value=mock_docs):
            with patch.object(Path, "read_text") as mock_read:
                mock_read.side_effect = lambda self: contents.get(str(self), "")
                
                templates = checker.find_template_files()
                
                # Should find doc1 and doc3 based on content
                assert len(templates) == 2
                assert Path("/test/doc1.md") in templates
                assert Path("/test/doc3.md") in templates
                assert Path("/test/doc2.md") not in templates

    def test_find_template_files_read_error(self) -> None:
        """Test handling read errors when checking template content."""
        checker = StructuralSoundnessChecker()
        
        mock_docs = [Path("/test/unreadable.md")]
        
        with patch("src.document_analysis.structural_soundness_checker.find_active_documents", return_value=mock_docs):
            with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
                with patch("src.document_analysis.structural_soundness_checker.logger") as mock_logger:
                    templates = checker.find_template_files()
                    
                    assert templates == []
                    mock_logger.warning.assert_called()


class TestGenerateSoundnessReport:
    """Test report generation."""

    def test_generate_report_no_files(self) -> None:
        """Test report generation when no relevant files found."""
        checker = StructuralSoundnessChecker()
        
        with patch.object(checker, "find_adr_and_architecture_files", return_value=([], [])):
            with patch.object(checker, "find_template_files", return_value=[]):
                with patch("src.document_analysis.structural_soundness_checker.logger") as mock_logger:
                    checker.generate_soundness_report()
                    
                    log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                    assert any("No ADR or architecture files found" in msg for msg in log_messages)
                    assert any("No template files found" in msg for msg in log_messages)

    def test_generate_report_with_citations(self) -> None:
        """Test report generation with citation checking."""
        checker = StructuralSoundnessChecker()
        
        mock_adr_files = [Path("/test/docs/adr/001.md")]
        mock_arch_files = [Path("/test/docs/architecture/design.md")]
        
        mock_citation_results = [
            CitationCheck(
                document_path=mock_adr_files[0],
                cited_in_documents=["Direct mention"],
                expected_citations=[],
                missing_citations=[]
            ),
            CitationCheck(
                document_path=mock_arch_files[0],
                cited_in_documents=[],
                expected_citations=["docs/architecture/design.md"],
                missing_citations=["docs/architecture/design.md"]
            )
        ]
        
        with patch.object(checker, "find_adr_and_architecture_files", return_value=(mock_adr_files, mock_arch_files)):
            with patch.object(checker.documents_md_path, "exists", return_value=True):
                with patch.object(checker, "check_citations_in_documents_md", return_value=mock_citation_results):
                    with patch.object(checker, "find_template_files", return_value=[]):
                        with patch("src.document_analysis.structural_soundness_checker.logger") as mock_logger:
                            checker.generate_soundness_report()
                            
                            log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                            assert any("Properly cited: 1/2" in msg for msg in log_messages)
                            assert any("Missing citations: 1" in msg for msg in log_messages)

    def test_generate_report_with_templates(self) -> None:
        """Test report generation with template analysis."""
        checker = StructuralSoundnessChecker()
        
        mock_templates = [Path("/test/template.md")]
        mock_mappings = [
            TemplateMapping(
                template_path=mock_templates[0],
                template_name="template.md",
                expected_outputs=["output1.yml", "output2.json"],
                actual_outputs=["output1.yml"],
                instructions=["Create workflow"],
                generation_commands=["generate-workflow"]
            )
        ]
        
        with patch.object(checker, "find_adr_and_architecture_files", return_value=([], [])):
            with patch.object(checker, "find_template_files", return_value=mock_templates):
                with patch.object(checker, "extract_template_mappings", return_value=mock_mappings):
                    with patch("src.document_analysis.structural_soundness_checker.logger") as mock_logger:
                        checker.generate_soundness_report()
                        
                        log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                        assert any("Generation rate: 1/2 (50.0%)" in msg for msg in log_messages)
                        assert any("Total generation instructions: 1" in msg for msg in log_messages)

    def test_generate_report_overall_assessment(self) -> None:
        """Test overall assessment calculation in report."""
        checker = StructuralSoundnessChecker()
        
        # Set up high scores
        mock_adr_files = [Path("/test/docs/adr/001.md")]
        mock_citation_results = [
            CitationCheck(
                document_path=mock_adr_files[0],
                cited_in_documents=["Direct mention"],
                expected_citations=[],
                missing_citations=[]
            )
        ]
        
        mock_templates = [Path("/test/template.md")]
        mock_mappings = [
            TemplateMapping(
                template_path=mock_templates[0],
                template_name="template.md",
                expected_outputs=["output.yml"],
                actual_outputs=["output.yml"],
                instructions=[],
                generation_commands=[]
            )
        ]
        
        with patch.object(checker, "find_adr_and_architecture_files", return_value=(mock_adr_files, [])):
            with patch.object(checker.documents_md_path, "exists", return_value=True):
                with patch.object(checker, "check_citations_in_documents_md", return_value=mock_citation_results):
                    with patch.object(checker, "find_template_files", return_value=mock_templates):
                        with patch.object(checker, "extract_template_mappings", return_value=mock_mappings):
                            with patch("src.document_analysis.structural_soundness_checker.logger") as mock_logger:
                                checker.generate_soundness_report()
                                
                                log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
                                assert any("Overall Assessment: EXCELLENT" in msg for msg in log_messages)


class TestMainFunction:
    """Test the main function."""

    def test_main_execution(self) -> None:
        """Test main function execution."""
        with patch("src.document_analysis.structural_soundness_checker.StructuralSoundnessChecker") as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker_class.return_value = mock_checker
            
            from src.document_analysis.structural_soundness_checker import main
            main()
            
            mock_checker_class.assert_called_once_with()
            mock_checker.generate_soundness_report.assert_called_once()


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_full_structural_analysis(self) -> None:
        """Test complete structural analysis workflow."""
        checker = StructuralSoundnessChecker(root_dir=Path("/test"))
        
        # Set up realistic file structure
        adr_files = [
            Path("/test/docs/adr/001-use-python.md"),
            Path("/test/docs/adr/002-testing-strategy.md")
        ]
        
        arch_files = [
            Path("/test/docs/architecture/system-overview.md")
        ]
        
        template_files = [
            Path("/test/templates/github-workflow-template.md")
        ]
        
        documents_content = """
# Project Documents

## Architecture Decisions
- [Use Python](docs/adr/001-use-python.md)
- See docs/adr directory for all decisions

## Architecture
- [System Overview](docs/architecture/system-overview.md)
"""
        
        template_content = """
# GitHub Workflow Template

This template generates: `ci.yml`

```bash
generate-workflow --name ci --output .github/workflows/ci.yml
```
"""
        
        with patch.object(checker, "find_adr_and_architecture_files", return_value=(adr_files, arch_files)):
            with patch.object(checker.documents_md_path, "exists", return_value=True):
                with patch.object(checker.documents_md_path, "read_text", return_value=documents_content):
                    with patch.object(checker, "find_template_files", return_value=template_files):
                        with patch.object(Path, "exists", return_value=True):
                            with patch.object(Path, "read_text", return_value=template_content):
                                # Run full analysis
                                citation_results = checker.check_citations_in_documents_md(adr_files + arch_files)
                                template_mappings = checker.extract_template_mappings(template_files)
                                
                                # Verify results
                                assert len(citation_results) == 3
                                
                                # 001 should be found via direct link
                                adr001_result = next(r for r in citation_results if "001" in str(r.document_path))
                                assert len(adr001_result.cited_in_documents) > 0
                                
                                # 002 should be found via directory mention
                                adr002_result = next(r for r in citation_results if "002" in str(r.document_path))
                                assert any("Directory mention" in c for c in adr002_result.cited_in_documents)
                                
                                # Template analysis
                                assert len(template_mappings) == 1
                                assert "ci.yml" in template_mappings[0].expected_outputs


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_template_patterns(self) -> None:
        """Test behavior with empty pattern lists."""
        checker = StructuralSoundnessChecker()
        
        # Temporarily clear patterns
        original_patterns = checker.template_patterns
        checker.template_patterns = []
        
        template_content = "Creates: output.yml"
        mappings = checker.extract_template_mappings([Path("/test/template.md")])
        
        # Should return empty mappings without patterns
        assert all(len(m.expected_outputs) == 0 for m in mappings)
        
        # Restore patterns
        checker.template_patterns = original_patterns

    def test_malformed_regex_in_content(self) -> None:
        """Test handling malformed content that might break regex."""
        checker = StructuralSoundnessChecker()
        
        documents_content = "[[[Broken markdown]]](((invalid)))"
        files = [Path("/test/file.md")]
        
        with patch.object(checker.documents_md_path, "exists", return_value=True):
            with patch.object(checker.documents_md_path, "read_text", return_value=documents_content):
                # Should handle gracefully without raising exceptions
                results = checker.check_citations_in_documents_md(files)
                assert isinstance(results, list)

    def test_unicode_in_filenames_and_content(self) -> None:
        """Test handling Unicode characters."""
        checker = StructuralSoundnessChecker()
        
        template_content = """
# Template 模板

Creates: 输出文件.yml
Generates: café-config.json
"""
        
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=template_content):
                mappings = checker.extract_template_mappings([Path("/test/模板.md")])
                
                assert len(mappings) == 1
                assert "输出文件.yml" in mappings[0].expected_outputs
                assert "café-config.json" in mappings[0].expected_outputs

    def test_very_large_documents_md(self) -> None:
        """Test performance with very large DOCUMENTS.md file."""
        checker = StructuralSoundnessChecker()
        
        # Create a large document content
        large_content = "# Documents\n" + "\n".join([f"File {i}.md" for i in range(1000)])
        
        files_to_check = [Path(f"/test/File {i}.md") for i in range(10)]
        
        with patch.object(checker.documents_md_path, "exists", return_value=True):
            with patch.object(checker.documents_md_path, "read_text", return_value=large_content):
                results = checker.check_citations_in_documents_md(files_to_check)
                
                # Should complete without performance issues
                assert len(results) == 10
                assert all(len(r.cited_in_documents) > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])