"""Integration tests for the main API."""

import pytest
from pathlib import Path
import json
import tempfile

from docpipe import analyze_project, DocPipe, AnalysisConfig, FEATURES
from docpipe.models import Severity


class TestAnalyzeProject:
    """Test the analyze_project function."""
    
    def test_analyze_sample_project(self, sample_project):
        """Test analyzing a complete sample project."""
        results = analyze_project(sample_project)
        
        assert results.project_path == sample_project
        assert results.total_documents > 0
        assert results.compliance is not None
        assert results.similarity is not None
        assert results.references is not None
        
        # Check summary
        summary = results.summary
        assert "total_documents" in summary
        assert "compliance_score" in summary
        
    def test_analyze_with_config(self, sample_project):
        """Test analyzing with custom configuration."""
        config = AnalysisConfig(
            check_compliance=True,
            analyze_similarity=True,
            validate_references=False,  # Skip references
            trace_instructions=False,
            similarity_threshold=0.8
        )
        
        results = analyze_project(sample_project, config)
        
        assert results.compliance is not None
        assert results.similarity is not None
        assert results.references is None  # Skipped
        
    def test_analyze_with_progress(self, sample_project):
        """Test analyzing with progress callback."""
        progress_calls = []
        
        def track_progress(percentage, message):
            progress_calls.append((percentage, message))
        
        results = analyze_project(sample_project, progress_callback=track_progress)
        
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100.0  # Final progress
        assert "complete" in progress_calls[-1][1].lower()
        
    def test_analyze_nonexistent_path(self):
        """Test analyzing nonexistent path."""
        with pytest.raises(Exception, match="does not exist"):
            analyze_project("/nonexistent/path")
            
    def test_analyze_file_instead_of_directory(self, temp_dir):
        """Test analyzing a file instead of directory."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test")
        
        with pytest.raises(Exception, match="not a directory"):
            analyze_project(test_file)


class TestDocPipe:
    """Test the DocPipe class."""
    
    def test_docpipe_initialization(self):
        """Test DocPipe initialization."""
        config = AnalysisConfig(similarity_threshold=0.85)
        pipeline = DocPipe(config)
        
        assert pipeline.config.similarity_threshold == 0.85
        
    def test_validate_config(self):
        """Test configuration validation."""
        # Test with semantic similarity but no NLP
        config = AnalysisConfig(similarity_method="semantic")
        pipeline = DocPipe(config)
        
        warnings = pipeline.validate_config()
        
        if not FEATURES.get('semantic_similarity', False):
            assert len(warnings) > 0
            assert "sentence-transformers not installed" in warnings[0]
            
    def test_individual_analyzers(self, sample_project):
        """Test running individual analyzers."""
        pipeline = DocPipe()
        
        # Test each analyzer separately
        compliance_results = pipeline.analyze_compliance(sample_project)
        assert compliance_results.files_checked > 0
        
        similarity_results = pipeline.analyze_similarity(sample_project)
        assert similarity_results.documents_analyzed > 0
        
        reference_results = pipeline.analyze_references(sample_project)
        assert reference_results.references_found >= 0
        
    def test_get_features(self):
        """Test feature detection."""
        pipeline = DocPipe()
        features = pipeline.get_features()
        
        assert isinstance(features, dict)
        assert 'semantic_similarity' in features
        assert 'excel_export' in features
        
    def test_full_analysis(self, sample_project):
        """Test full analysis with DocPipe."""
        pipeline = DocPipe(AnalysisConfig(
            check_compliance=True,
            analyze_similarity=True,
            validate_references=True,
            similarity_threshold=0.7
        ))
        
        results = pipeline.analyze(sample_project)
        
        assert results.compliance is not None
        assert results.similarity is not None
        assert results.references is not None
        assert len(results.feedback) > 0
        
        # Check feedback generation
        feedback_severities = {f.severity for f in results.feedback}
        assert Severity.INFO in feedback_severities  # Should have at least info


class TestResultsExport:
    """Test exporting analysis results."""
    
    def test_export_json(self, sample_project, temp_dir):
        """Test exporting results to JSON."""
        results = analyze_project(sample_project)
        
        export_path = temp_dir / "results.json"
        results.export(export_path, format="json")
        
        assert export_path.exists()
        
        # Load and verify JSON
        with open(export_path) as f:
            data = json.load(f)
        
        assert data["project_path"] == str(sample_project)
        assert "summary" in data
        assert "all_issues" in data
        
    def test_export_csv(self, sample_project, temp_dir):
        """Test exporting results to CSV."""
        results = analyze_project(sample_project)
        
        export_path = temp_dir / "results.csv"
        results.export(export_path, format="csv")
        
        assert export_path.exists()
        
        # Verify CSV has content
        content = export_path.read_text()
        assert "severity" in content
        assert "category" in content
        
    def test_export_markdown(self, sample_project, temp_dir):
        """Test exporting results to Markdown."""
        results = analyze_project(sample_project)
        
        export_path = temp_dir / "results.md"
        results.export(export_path, format="markdown")
        
        assert export_path.exists()
        
        content = export_path.read_text()
        assert "# Analysis Results" in content
        assert "## Summary" in content
        assert str(sample_project) in content
        
    def test_export_excel_without_pandas(self, sample_project, temp_dir):
        """Test Excel export fails gracefully without pandas."""
        results = analyze_project(sample_project)
        
        # Temporarily disable pandas
        import sys
        pandas_module = sys.modules.get('pandas')
        if pandas_module:
            sys.modules['pandas'] = None
        
        try:
            export_path = temp_dir / "results.xlsx"
            with pytest.raises(ImportError, match="pandas required"):
                results.export(export_path, format="excel")
        finally:
            # Restore pandas
            if pandas_module:
                sys.modules['pandas'] = pandas_module


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_directory(self, temp_dir):
        """Test analyzing empty directory."""
        results = analyze_project(temp_dir)
        
        assert results.total_documents == 0
        assert results.compliance.files_checked == 0
        assert results.similarity.documents_analyzed == 0
        
    def test_directory_with_only_python(self, temp_dir):
        """Test directory with only Python files."""
        (temp_dir / "module.py").write_text("def func(): pass")
        
        results = analyze_project(temp_dir)
        
        assert results.total_documents == 0  # No markdown
        assert results.compliance.files_checked == 1  # Python file checked
        
    def test_large_file_handling(self, temp_dir):
        """Test handling of large files."""
        # Create a large file (over max size)
        large_content = "x" * (11 * 1024 * 1024)  # 11MB
        (temp_dir / "large.md").write_text(large_content)
        (temp_dir / "normal.md").write_text("# Normal")
        
        config = AnalysisConfig(max_file_size_mb=10.0)
        results = analyze_project(temp_dir, config)
        
        # Should skip the large file
        assert results.total_documents == 1  # Only normal.md
        
    def test_unicode_handling(self, temp_dir):
        """Test handling of unicode in documents."""
        content = """
        # Unicode Test 🚀
        
        This contains émojis and spëcial characters.
        日本語 and 中文 text.
        """
        
        (temp_dir / "unicode.md").write_text(content, encoding='utf-8')
        
        results = analyze_project(temp_dir)
        assert results.total_documents == 1
        
    def test_concurrent_analysis(self, sample_project):
        """Test running multiple analyses concurrently."""
        # This tests that the analyzer instances don't interfere
        pipeline1 = DocPipe(AnalysisConfig(similarity_threshold=0.7))
        pipeline2 = DocPipe(AnalysisConfig(similarity_threshold=0.9))
        
        results1 = pipeline1.analyze(sample_project)
        results2 = pipeline2.analyze(sample_project)
        
        # Different thresholds should potentially give different results
        assert results1.config.similarity_threshold == 0.7
        assert results2.config.similarity_threshold == 0.9