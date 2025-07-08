"""Tests for similarity analyzers."""

import pytest
from pathlib import Path
import numpy as np

from docpipe.analyzers import (
    StringSimilarityAnalyzer,
    SemanticSimilarityAnalyzer,
    CombinedSimilarityAnalyzer,
    create_similarity_analyzer,
    SimilarityConfig,
)
from docpipe.models import SimilarityResults


class TestSimilarityConfig:
    """Test SimilarityConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SimilarityConfig()
        
        assert config.method == "string"
        assert config.similarity_threshold == 0.75
        assert config.duplicate_threshold == 0.95
        assert config.string_algorithm == "token_sort"
        assert config.enable_clustering is True
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = SimilarityConfig(
            method="semantic",
            similarity_threshold=0.8,
            string_algorithm="partial"
        )
        
        assert config.method == "semantic"
        assert config.similarity_threshold == 0.8
        assert config.string_algorithm == "partial"


class TestStringSimilarityAnalyzer:
    """Test StringSimilarityAnalyzer functionality."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = StringSimilarityAnalyzer()
        assert analyzer.name == "StringSimilarityAnalyzer"
        assert "string matching" in analyzer.description
        
    def test_analyze_similar_documents(self, markdown_files):
        """Test analyzing similar markdown documents."""
        analyzer = StringSimilarityAnalyzer({
            "similarity": {"similarity_threshold": 0.7}
        })
        
        # Analyze directory with similar docs
        result = analyzer.analyze(markdown_files['doc1'].parent)
        
        assert result.success is True
        assert isinstance(result.data, SimilarityResults)
        
        similarity_results = result.data
        assert similarity_results.documents_analyzed == 3  # doc1, doc2, doc3
        
        # doc1 and doc2 should be similar
        assert len(similarity_results.similar_pairs) > 0
        
        # Check that doc1 and doc2 are identified as similar
        similar_paths = set()
        for pair in similarity_results.similar_pairs:
            similar_paths.add(str(pair.source.name))
            similar_paths.add(str(pair.target.name))
        
        assert "doc1.md" in similar_paths
        assert "doc2.md" in similar_paths
        
    def test_analyze_single_document(self, markdown_files):
        """Test analyzing a single document."""
        analyzer = StringSimilarityAnalyzer()
        result = analyzer.analyze(markdown_files['doc1'])
        
        assert result.success is True
        similarity_results = result.data
        assert similarity_results.documents_analyzed == 1
        assert len(similarity_results.similar_pairs) == 0  # No pairs for single doc
        
    def test_similarity_threshold(self, markdown_files):
        """Test similarity threshold filtering."""
        # High threshold
        analyzer_high = StringSimilarityAnalyzer({
            "similarity": {"similarity_threshold": 0.95}
        })
        result_high = analyzer_high.analyze(markdown_files['doc1'].parent)
        
        # Low threshold
        analyzer_low = StringSimilarityAnalyzer({
            "similarity": {"similarity_threshold": 0.3}
        })
        result_low = analyzer_low.analyze(markdown_files['doc1'].parent)
        
        # Should find more pairs with lower threshold
        assert len(result_low.data.similar_pairs) >= len(result_high.data.similar_pairs)
        
    def test_duplicate_detection(self, temp_dir):
        """Test duplicate document detection."""
        # Create identical documents
        content = "# Test Document\n\nThis is a test document."
        
        (temp_dir / "dup1.md").write_text(content)
        (temp_dir / "dup2.md").write_text(content)
        (temp_dir / "dup3.md").write_text(content)
        (temp_dir / "different.md").write_text("# Different\n\nCompletely different.")
        
        analyzer = StringSimilarityAnalyzer({
            "similarity": {
                "similarity_threshold": 0.7,
                "duplicate_threshold": 0.95,
                "enable_clustering": True
            }
        })
        
        result = analyzer.analyze(temp_dir)
        similarity_results = result.data
        
        # Should find duplicate groups
        assert len(similarity_results.duplicate_groups) > 0
        
        # Check that all duplicates are in the same group
        dup_group = None
        for group in similarity_results.duplicate_groups:
            names = [p.name for p in group]
            if "dup1.md" in names:
                dup_group = group
                break
        
        assert dup_group is not None
        assert len(dup_group) == 3
        assert all(p.name.startswith("dup") for p in dup_group)
        
    def test_exclude_patterns(self, temp_dir):
        """Test excluding files based on patterns."""
        (temp_dir / "include.md").write_text("# Include")
        (temp_dir / "exclude.tmp.md").write_text("# Exclude")
        (temp_dir / ".hidden.md").write_text("# Hidden")
        
        analyzer = StringSimilarityAnalyzer({
            "exclude_patterns": ["*.tmp.*", ".*"]
        })
        
        result = analyzer.analyze(temp_dir)
        similarity_results = result.data
        
        # Should only analyze include.md
        assert similarity_results.documents_analyzed == 1


class TestSemanticSimilarityAnalyzer:
    """Test SemanticSimilarityAnalyzer functionality."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = SemanticSimilarityAnalyzer()
        assert analyzer.name == "SemanticSimilarityAnalyzer"
        assert "semantic embeddings" in analyzer.description
        
    def test_validate_config_without_dependency(self):
        """Test configuration validation without sentence-transformers."""
        analyzer = SemanticSimilarityAnalyzer()
        
        # If sentence-transformers is not installed, should get warning
        warnings = analyzer.validate_config()
        if not analyzer.sentence_transformers:
            assert len(warnings) > 0
            assert "sentence-transformers not installed" in warnings[0]
            
    def test_analyze_without_dependency(self, markdown_files):
        """Test analyzing without sentence-transformers returns empty results."""
        analyzer = SemanticSimilarityAnalyzer()
        
        # Temporarily set sentence_transformers to None
        original_st = analyzer.sentence_transformers
        analyzer.sentence_transformers = None
        
        result = analyzer.analyze(markdown_files['doc1'].parent)
        
        assert result.success is True
        assert result.data.documents_analyzed == 0  # No analysis performed
        
        # Restore
        analyzer.sentence_transformers = original_st
        
    def test_analyze_with_mock_dependency(self, markdown_files, mock_sentence_transformers):
        """Test analyzing with mocked sentence-transformers."""
        analyzer = SemanticSimilarityAnalyzer()
        analyzer.sentence_transformers = mock_sentence_transformers
        
        result = analyzer.analyze(markdown_files['doc1'].parent)
        
        assert result.success is True
        similarity_results = result.data
        assert similarity_results.documents_analyzed == 3
        
        # Check that model was called
        assert mock_sentence_transformers.SentenceTransformer.called
        assert analyzer.model.encode.called


class TestCombinedSimilarityAnalyzer:
    """Test CombinedSimilarityAnalyzer functionality."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = CombinedSimilarityAnalyzer()
        assert analyzer.name == "CombinedSimilarityAnalyzer"
        assert "both string and semantic" in analyzer.description
        
    def test_analyze_combined(self, markdown_files):
        """Test combined analysis."""
        analyzer = CombinedSimilarityAnalyzer({
            "similarity": {"similarity_threshold": 0.7}
        })
        
        result = analyzer.analyze(markdown_files['doc1'].parent)
        
        assert result.success is True
        similarity_results = result.data
        
        # Should have results from string analysis at least
        assert similarity_results.documents_analyzed > 0
        
    def test_merge_duplicate_groups(self):
        """Test merging overlapping duplicate groups."""
        analyzer = CombinedSimilarityAnalyzer()
        
        # Create overlapping groups
        groups = [
            [Path("a.md"), Path("b.md")],
            [Path("b.md"), Path("c.md")],
            [Path("d.md"), Path("e.md")],
        ]
        
        merged = analyzer._merge_duplicate_groups(groups)
        
        assert len(merged) == 2  # Two separate groups
        
        # Find the merged group containing a, b, c
        large_group = None
        for group in merged:
            if Path("a.md") in group:
                large_group = group
                break
                
        assert large_group is not None
        assert len(large_group) == 3
        assert Path("a.md") in large_group
        assert Path("b.md") in large_group
        assert Path("c.md") in large_group


class TestSimilarityFactory:
    """Test create_similarity_analyzer factory function."""
    
    def test_create_string_analyzer(self):
        """Test creating string analyzer."""
        analyzer = create_similarity_analyzer({
            "similarity": {"method": "string"}
        })
        
        assert isinstance(analyzer, StringSimilarityAnalyzer)
        
    def test_create_semantic_analyzer(self):
        """Test creating semantic analyzer."""
        analyzer = create_similarity_analyzer({
            "similarity": {"method": "semantic"}
        })
        
        # Should be semantic if available, otherwise string
        assert isinstance(analyzer, (SemanticSimilarityAnalyzer, StringSimilarityAnalyzer))
        
    def test_create_combined_analyzer(self):
        """Test creating combined analyzer."""
        analyzer = create_similarity_analyzer({
            "similarity": {"method": "both"}
        })
        
        assert isinstance(analyzer, CombinedSimilarityAnalyzer)
        
    def test_invalid_method(self):
        """Test invalid similarity method."""
        with pytest.raises(ValueError, match="Unknown similarity method"):
            create_similarity_analyzer({
                "similarity": {"method": "invalid"}
            })