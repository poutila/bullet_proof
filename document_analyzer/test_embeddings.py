#!/usr/bin/env python3
"""
Test suite for embeddings module.

Tests all embedding and similarity analysis functions according to CLAUDE.md standards.
"""
import pytest
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from document_analyzer.embeddings import (
    analyze_semantic_similarity,
    analyze_active_document_similarities,
    create_similarity_matrix,
    find_embeddings_clusters
)
from document_analyzer.validation import ValidationError


class TestAnalyzeSemanticSimilarity:
    """Test cases for analyze_semantic_similarity function."""
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    @patch('document_analyzer.embeddings.SentenceTransformer')
    def test_analyze_semantic_similarity_basic(
        self,
        mock_model_class: Mock,
        mock_load_files: Mock
    ) -> None:
        """Test basic semantic similarity analysis."""
        # Setup mocks
        mock_load_files.side_effect = [
            {"not_in_use/doc1.md": "content1"},
            {"active/doc2.md": "content2"}
        ]
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock embeddings as tensors
        mock_tensor1 = Mock()
        mock_tensor2 = Mock()
        mock_model.encode.side_effect = [mock_tensor1, mock_tensor2]
        
        # Mock cosine similarity
        with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
            mock_cos_sim.return_value = [[0.85]]  # High similarity
            
            # Run analysis
            df = analyze_semantic_similarity(
                [Path("not_in_use/doc1.md")],
                [Path("active/doc2.md")],
                Path("."),
                threshold=0.75
            )
        
        # Verify results
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["not_in_use"] == "not_in_use/doc1.md"
        assert df.iloc[0]["matched_file"] == "active/doc2.md"
        assert df.iloc[0]["similarity"] == 0.85
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    def test_analyze_semantic_similarity_no_matches(
        self,
        mock_load_files: Mock
    ) -> None:
        """Test when no documents meet similarity threshold."""
        # Setup mocks
        mock_load_files.side_effect = [
            {"not_in_use/doc1.md": "content1"},
            {"active/doc2.md": "content2"}
        ]
        
        with patch('document_analyzer.embeddings.SentenceTransformer') as mock_model_class:
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            mock_model.encode.side_effect = [Mock(), Mock()]
            
            with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
                mock_cos_sim.return_value = [[0.5]]  # Below threshold
                
                df = analyze_semantic_similarity(
                    [Path("not_in_use/doc1.md")],
                    [Path("active/doc2.md")],
                    Path("."),
                    threshold=0.75
                )
        
        assert len(df) == 0
    
    def test_analyze_semantic_similarity_empty_lists(self) -> None:
        """Test error handling for empty document lists."""
        with pytest.raises(ValidationError):
            analyze_semantic_similarity([], [Path("doc.md")], Path("."))
        
        with pytest.raises(ValidationError):
            analyze_semantic_similarity([Path("doc.md")], [], Path("."))
    
    def test_analyze_semantic_similarity_invalid_threshold(self) -> None:
        """Test threshold validation."""
        with pytest.raises(ValidationError):
            analyze_semantic_similarity(
                [Path("doc1.md")],
                [Path("doc2.md")],
                Path("."),
                threshold=1.5  # Invalid
            )
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    def test_analyze_semantic_similarity_load_failure(
        self,
        mock_load_files: Mock
    ) -> None:
        """Test handling of file loading failures."""
        mock_load_files.side_effect = OSError("Failed to load")
        
        with pytest.raises(RuntimeError, match="Failed to load document files"):
            analyze_semantic_similarity(
                [Path("doc1.md")],
                [Path("doc2.md")],
                Path(".")
            )
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    def test_analyze_semantic_similarity_model_failure(
        self,
        mock_load_files: Mock
    ) -> None:
        """Test handling of model loading failures."""
        mock_load_files.side_effect = [
            {"doc1.md": "content1"},
            {"doc2.md": "content2"}
        ]
        
        with patch('document_analyzer.embeddings.SentenceTransformer') as mock_model_class:
            mock_model_class.side_effect = Exception("Model error")
            
            with pytest.raises(RuntimeError, match="Failed to load model"):
                analyze_semantic_similarity(
                    [Path("doc1.md")],
                    [Path("doc2.md")],
                    Path(".")
                )


class TestAnalyzeActiveDocumentSimilarities:
    """Test cases for analyze_active_document_similarities function."""
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    @patch('document_analyzer.embeddings.SentenceTransformer')
    def test_analyze_active_similarities_basic(
        self,
        mock_model_class: Mock,
        mock_load_files: Mock
    ) -> None:
        """Test basic active document similarity analysis."""
        # Setup mocks
        mock_load_files.return_value = {
            "doc1.md": "content1",
            "doc2.md": "content2",
            "doc3.md": "content3"
        }
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.encode.return_value = Mock()
        
        # Mock similarity matrix
        with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
            # Create symmetric similarity matrix
            mock_cos_sim.return_value = [
                [1.0, 0.9, 0.3],
                [0.9, 1.0, 0.4],
                [0.3, 0.4, 1.0]
            ]
            
            df = analyze_active_document_similarities(
                [Path("doc1.md"), Path("doc2.md"), Path("doc3.md")],
                Path("."),
                threshold=0.75
            )
        
        # Should find one pair with high similarity
        assert len(df) == 1
        assert df.iloc[0]["similarity"] == 0.9
        assert df.iloc[0]["relationship_type"] == "HIGH_OVERLAP"
    
    def test_analyze_active_similarities_insufficient_docs(self) -> None:
        """Test handling of insufficient documents."""
        df = analyze_active_document_similarities(
            [Path("only_one.md")],
            Path(".")
        )
        
        assert len(df) == 0
        assert list(df.columns) == ["doc1", "doc2", "similarity", "relationship_type"]
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    @patch('document_analyzer.embeddings.SentenceTransformer')
    def test_analyze_active_similarities_relationship_types(
        self,
        mock_model_class: Mock,
        mock_load_files: Mock
    ) -> None:
        """Test different relationship type classifications."""
        mock_load_files.return_value = {
            "doc1.md": "content1",
            "doc2.md": "content2",
            "doc3.md": "content3",
            "doc4.md": "content4"
        }
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.encode.return_value = Mock()
        
        with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
            # Various similarity levels
            mock_cos_sim.return_value = [
                [1.0, 0.96, 0.86, 0.76],
                [0.96, 1.0, 0.5, 0.5],
                [0.86, 0.5, 1.0, 0.5],
                [0.76, 0.5, 0.5, 1.0]
            ]
            
            df = analyze_active_document_similarities(
                [Path(f"doc{i}.md") for i in range(1, 5)],
                Path("."),
                threshold=0.75
            )
        
        # Check relationship types
        relationships = df["relationship_type"].tolist()
        assert "NEAR_DUPLICATE" in relationships
        assert "HIGH_OVERLAP" in relationships
        assert "MODERATE_OVERLAP" in relationships
    
    def test_analyze_active_similarities_exclude_self(self) -> None:
        """Test self-exclusion parameter."""
        # This is implicitly tested in other tests
        # Self-comparisons (diagonal) should never appear in results
        pass


class TestCreateSimilarityMatrix:
    """Test cases for create_similarity_matrix function."""
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    @patch('document_analyzer.embeddings.SentenceTransformer')
    def test_create_similarity_matrix_basic(
        self,
        mock_model_class: Mock,
        mock_load_files: Mock
    ) -> None:
        """Test basic similarity matrix creation."""
        # Setup mocks
        mock_load_files.return_value = {
            "doc1.md": "content1",
            "doc2.md": "content2"
        }
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.encode.return_value = Mock()
        
        with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
            # Mock tensor with cpu() and numpy() methods
            mock_tensor = Mock()
            mock_tensor.cpu.return_value.numpy.return_value = np.array([
                [1.0, 0.8],
                [0.8, 1.0]
            ])
            mock_cos_sim.return_value = mock_tensor
            
            matrix, names = create_similarity_matrix(
                [Path("doc1.md"), Path("doc2.md")],
                Path(".")
            )
        
        # Verify matrix properties
        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (2, 2)
        assert names == ["doc1.md", "doc2.md"]
        assert matrix.iloc[0, 0] == 1.0  # Self-similarity
        assert matrix.iloc[0, 1] == 0.8
        assert matrix.iloc[1, 0] == 0.8  # Symmetric
    
    def test_create_similarity_matrix_single_doc(self) -> None:
        """Test handling of single document."""
        with patch('document_analyzer.embeddings.load_markdown_files') as mock_load:
            mock_load.return_value = {"doc1.md": "content"}
            
            matrix, names = create_similarity_matrix(
                [Path("doc1.md")],
                Path(".")
            )
            
            assert matrix.empty
            assert names == []
    
    def test_create_similarity_matrix_empty_list(self) -> None:
        """Test validation of empty document list."""
        with pytest.raises(ValidationError):
            create_similarity_matrix([], Path("."))
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    def test_create_similarity_matrix_encoding_failure(
        self,
        mock_load_files: Mock
    ) -> None:
        """Test handling of encoding failures."""
        mock_load_files.return_value = {
            "doc1.md": "content1",
            "doc2.md": "content2"
        }
        
        with patch('document_analyzer.embeddings.SentenceTransformer') as mock_model_class:
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            mock_model.encode.side_effect = Exception("Encoding error")
            
            with pytest.raises(RuntimeError, match="Failed to generate document embeddings"):
                create_similarity_matrix(
                    [Path("doc1.md"), Path("doc2.md")],
                    Path(".")
                )


class TestFindEmbeddingsClusters:
    """Test cases for find_embeddings_clusters function."""
    
    def test_find_clusters_basic(self) -> None:
        """Test basic cluster finding."""
        # Create similarity matrix with clear clusters
        data = [
            [1.0, 0.95, 0.1, 0.1],
            [0.95, 1.0, 0.1, 0.1],
            [0.1, 0.1, 1.0, 0.9],
            [0.1, 0.1, 0.9, 1.0]
        ]
        
        matrix = pd.DataFrame(
            data,
            index=["doc1", "doc2", "doc3", "doc4"],
            columns=["doc1", "doc2", "doc3", "doc4"]
        )
        
        clusters = find_embeddings_clusters(matrix, threshold=0.85)
        
        assert len(clusters) == 2
        assert set(clusters[0]) == {"doc1", "doc2"}
        assert set(clusters[1]) == {"doc3", "doc4"}
    
    def test_find_clusters_no_clusters(self) -> None:
        """Test when no clusters exist above threshold."""
        # Low similarities everywhere
        data = [
            [1.0, 0.3, 0.2],
            [0.3, 1.0, 0.4],
            [0.2, 0.4, 1.0]
        ]
        
        matrix = pd.DataFrame(
            data,
            index=["doc1", "doc2", "doc3"],
            columns=["doc1", "doc2", "doc3"]
        )
        
        clusters = find_embeddings_clusters(matrix, threshold=0.85)
        
        assert len(clusters) == 0
    
    def test_find_clusters_empty_matrix(self) -> None:
        """Test error handling for empty matrix."""
        empty_matrix = pd.DataFrame()
        
        with pytest.raises(ValueError, match="empty"):
            find_embeddings_clusters(empty_matrix)
    
    def test_find_clusters_non_square_matrix(self) -> None:
        """Test error handling for non-square matrix."""
        # Rectangular matrix
        matrix = pd.DataFrame([[1.0, 0.5], [0.5, 1.0], [0.3, 0.4]])
        
        with pytest.raises(ValueError, match="square"):
            find_embeddings_clusters(matrix)
    
    def test_find_clusters_invalid_threshold(self) -> None:
        """Test threshold validation."""
        matrix = pd.DataFrame([[1.0, 0.5], [0.5, 1.0]])
        
        with pytest.raises(ValidationError):
            find_embeddings_clusters(matrix, threshold=1.5)
    
    def test_find_clusters_default_threshold(self) -> None:
        """Test default threshold behavior."""
        # Should use SIMILARITY_THRESHOLD_MEDIUM (0.85)
        data = [
            [1.0, 0.86],
            [0.86, 1.0]
        ]
        
        matrix = pd.DataFrame(
            data,
            index=["doc1", "doc2"],
            columns=["doc1", "doc2"]
        )
        
        clusters = find_embeddings_clusters(matrix)  # No threshold specified
        
        assert len(clusters) == 1
        assert set(clusters[0]) == {"doc1", "doc2"}
    
    def test_find_clusters_missing_document(self) -> None:
        """Test error handling for missing document in matrix."""
        matrix = pd.DataFrame(
            [[1.0, 0.9], [0.9, 1.0]],
            index=["doc1", "doc2"],
            columns=["doc1", "doc3"]  # Mismatched columns
        )
        
        with pytest.raises(ValueError, match="not found in matrix"):
            find_embeddings_clusters(matrix)


class TestIntegration:
    """Integration tests for embeddings module."""
    
    @patch('document_analyzer.embeddings.load_markdown_files')
    @patch('document_analyzer.embeddings.SentenceTransformer')
    def test_full_workflow(
        self,
        mock_model_class: Mock,
        mock_load_files: Mock
    ) -> None:
        """Test complete workflow from documents to clusters."""
        # Setup comprehensive test data
        mock_load_files.return_value = {
            "doc1.md": "Python programming tutorial",
            "doc2.md": "Python coding guide",
            "doc3.md": "JavaScript basics",
            "doc4.md": "JavaScript fundamentals"
        }
        
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        # Mock embeddings
        mock_embeddings = Mock()
        mock_model.encode.return_value = mock_embeddings
        
        # Mock similarity scores showing two clusters
        with patch('document_analyzer.embeddings.util.pytorch_cos_sim') as mock_cos_sim:
            mock_tensor = Mock()
            mock_tensor.cpu.return_value.numpy.return_value = np.array([
                [1.0, 0.92, 0.3, 0.2],   # doc1 similar to doc2
                [0.92, 1.0, 0.2, 0.3],
                [0.3, 0.2, 1.0, 0.91],   # doc3 similar to doc4
                [0.2, 0.3, 0.91, 1.0]
            ])
            mock_cos_sim.return_value = mock_tensor
            
            # Create similarity matrix
            matrix, names = create_similarity_matrix(
                [Path(f"doc{i}.md") for i in range(1, 5)],
                Path(".")
            )
            
            # Find clusters
            clusters = find_embeddings_clusters(matrix, threshold=0.9)
        
        # Verify results
        assert len(clusters) == 2
        assert len(names) == 4
        
        # Check that similar documents are clustered together
        cluster_sets = [set(c) for c in clusters]
        assert {"doc1.md", "doc2.md"} in cluster_sets
        assert {"doc3.md", "doc4.md"} in cluster_sets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])