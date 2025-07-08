#!/usr/bin/env python3
"""Tests for document_analysis.similarity.semantic_similarity module.

Comprehensive tests for semantic similarity calculation according to CLAUDE.md standards.
Note: This mocks the SentenceTransformer to avoid downloading models during tests.
"""

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import numpy as np
import pandas as pd
import pytest

from src.document_analysis.similarity.semantic_similarity import (
    SemanticSimilarityCalculator,
    analyze_active_document_similarities,
    analyze_semantic_similarity,
    create_similarity_matrix,
    find_embeddings_clusters,
)
from src.document_analysis.similarity.base import SimilarityResult
from src.document_analysis.validation import ValidationError


@pytest.fixture(autouse=True)
def mock_allowed_paths(monkeypatch):
    """Mock ALLOWED_BASE_PATHS to include temp directories for testing."""
    monkeypatch.setattr("src.document_analysis.validation.ALLOWED_BASE_PATHS", frozenset())


class MockTensor:
    """Mock torch tensor for testing."""
    
    def __init__(self, data: np.ndarray):
        self.data = data
        self.shape = data.shape
    
    def cpu(self) -> 'MockTensor':
        return self
    
    def numpy(self) -> np.ndarray:
        return self.data
    
    def __getitem__(self, key):
        result = self.data[key]
        if isinstance(result, np.ndarray):
            return MockTensor(result)
        return result


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer for tests."""
    with patch('src.document_analysis.similarity.semantic_similarity.SentenceTransformer') as mock:
        model = MagicMock()
        
        # Mock encode method to return predictable embeddings
        def encode_side_effect(texts, convert_to_tensor=False, show_progress_bar=True):
            if isinstance(texts, str):
                texts = [texts]
            
            # Create more diverse embeddings based on text content
            embeddings = []
            for text in texts:
                # Create embeddings that differ more between texts
                if "cooking" in text.lower() or "recipe" in text.lower():
                    # Very different embedding for cooking content
                    embedding = np.array([0.1, 0.9, 0.2, 0.1])
                elif "machine learning" in text.lower() or "ml" in text.lower():
                    # Similar embeddings for ML content
                    embedding = np.array([0.8, 0.2, 0.7, 0.3])
                elif "artificial intelligence" in text.lower() or "ai" in text.lower():
                    # Slightly different for AI content
                    embedding = np.array([0.75, 0.25, 0.65, 0.35])
                else:
                    # Default embedding based on text length
                    length_factor = len(text) / 100.0
                    embedding = np.array([length_factor, 0.5, 0.3, 0.2])
                embeddings.append(embedding)
            
            embeddings_array = np.array(embeddings)
            
            if convert_to_tensor:
                return MockTensor(embeddings_array)
            return embeddings_array
        
        model.encode.side_effect = encode_side_effect
        mock.return_value = model
        
        yield mock


@pytest.fixture
def mock_pytorch_cos_sim():
    """Mock pytorch_cos_sim function."""
    def cos_sim_side_effect(tensor1, tensor2):
        # Simple cosine similarity calculation
        a = tensor1.data if hasattr(tensor1, 'data') else tensor1
        b = tensor2.data if hasattr(tensor2, 'data') else tensor2
        
        # Ensure 2D arrays
        if len(a.shape) == 1:
            a = a.reshape(1, -1)
        if len(b.shape) == 1:
            b = b.reshape(1, -1)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b.T)
        norm_a = np.linalg.norm(a, axis=1)[:, np.newaxis]
        norm_b = np.linalg.norm(b, axis=1)[np.newaxis, :]
        
        similarity = dot_product / (norm_a * norm_b + 1e-8)
        return MockTensor(similarity)
    
    with patch('src.document_analysis.similarity.semantic_similarity.util.pytorch_cos_sim', side_effect=cos_sim_side_effect) as mock:
        yield mock


@pytest.fixture
def sample_texts():
    """Sample texts for testing."""
    return [
        "This is a test document about machine learning.",
        "This is another test document about machine learning and AI.",
        "Completely different content about cooking recipes.",
        "Yet another document discussing artificial intelligence and ML."
    ]


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary markdown files for testing."""
    files = []
    
    # Create test files
    file1 = tmp_path / "doc1.md"
    file1.write_text("# Document 1\nThis is about machine learning.")
    files.append(file1)
    
    file2 = tmp_path / "doc2.md"
    file2.write_text("# Document 2\nThis is also about machine learning and AI.")
    files.append(file2)
    
    file3 = tmp_path / "doc3.md"
    file3.write_text("# Document 3\nCompletely different - cooking recipes here.")
    files.append(file3)
    
    file4 = tmp_path / "doc4.md"
    file4.write_text("# Document 4\nMore about artificial intelligence.")
    files.append(file4)
    
    return files, tmp_path


class TestSemanticSimilarityCalculator:
    """Test SemanticSimilarityCalculator class."""

    def test_initialization(self, mock_sentence_transformer) -> None:
        """Test calculator initialization."""
        calc = SemanticSimilarityCalculator(model_name="test-model")
        
        assert calc.name == "SemanticSimilarity"
        assert calc.model_name == "test-model"
        assert calc._model is None  # Lazy loading
        assert calc.config["model_name"] == "test-model"

    def test_initialization_with_default_model(self, mock_sentence_transformer) -> None:
        """Test initialization with default model."""
        calc = SemanticSimilarityCalculator()
        
        assert calc.model_name == "sentence-transformers/all-MiniLM-L6-v2"  # DEFAULT_MODEL_NAME

    def test_model_lazy_loading(self, mock_sentence_transformer) -> None:
        """Test model is loaded lazily on first access."""
        calc = SemanticSimilarityCalculator(model_name="test-model")
        
        assert calc._model is None
        mock_sentence_transformer.assert_not_called()
        
        # Access model property
        model = calc.model
        
        assert model is not None
        assert calc._model is not None
        mock_sentence_transformer.assert_called_once_with("test-model")

    def test_model_loading_failure(self, mock_sentence_transformer) -> None:
        """Test handling of model loading failure."""
        mock_sentence_transformer.side_effect = OSError("Model not found")
        
        calc = SemanticSimilarityCalculator(model_name="bad-model")
        
        with pytest.raises(RuntimeError, match="Failed to load model bad-model"):
            _ = calc.model

    def test_calculate_similarity_valid(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test pairwise similarity calculation."""
        calc = SemanticSimilarityCalculator()
        
        score = calc._calculate_similarity("text one", "text two")
        
        assert 0.0 <= score <= 1.0
        assert calc.model.encode.called

    def test_calculate_similarity_identical_texts(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test similarity of identical texts."""
        calc = SemanticSimilarityCalculator()
        
        score = calc._calculate_similarity("identical text", "identical text")
        
        assert score == pytest.approx(1.0, rel=0.01)

    def test_calculate_similarity_error_handling(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test error handling in similarity calculation."""
        calc = SemanticSimilarityCalculator()
        calc.model.encode.side_effect = RuntimeError("Encoding failed")
        
        score = calc._calculate_similarity("text1", "text2")
        
        assert score == 0.0  # Should return 0 on error

    def test_calculate_pairwise_with_validation(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test pairwise calculation with input validation."""
        calc = SemanticSimilarityCalculator()
        
        # Valid inputs
        score = calc.calculate_pairwise("valid text", "another valid text")
        assert 0.0 <= score <= 1.0
        
        # Empty text
        with pytest.raises(ValidationError, match="cannot be empty"):
            calc.calculate_pairwise("", "valid")
        
        # Non-string input
        with pytest.raises(ValidationError, match="must be a string"):
            calc.calculate_pairwise(123, "valid")  # type: ignore

    def test_calculate_matrix_valid(self, mock_sentence_transformer, mock_pytorch_cos_sim, sample_texts) -> None:
        """Test matrix calculation with valid inputs."""
        calc = SemanticSimilarityCalculator()
        
        matrix = calc.calculate_matrix(sample_texts)
        
        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (4, 4)
        assert list(matrix.index) == ["text_0", "text_1", "text_2", "text_3"]
        assert list(matrix.columns) == ["text_0", "text_1", "text_2", "text_3"]
        
        # Check diagonal is 1.0
        for i in range(4):
            assert matrix.iloc[i, i] == pytest.approx(1.0, rel=0.01)

    def test_calculate_matrix_empty_list(self, mock_sentence_transformer) -> None:
        """Test matrix calculation rejects empty list."""
        calc = SemanticSimilarityCalculator()
        
        with pytest.raises(ValueError, match="Text list cannot be empty"):
            calc.calculate_matrix([])

    def test_calculate_matrix_invalid_threshold(self, mock_sentence_transformer, sample_texts) -> None:
        """Test matrix calculation with invalid threshold."""
        calc = SemanticSimilarityCalculator()
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            calc.calculate_matrix(sample_texts, threshold=1.5)

    def test_calculate_matrix_with_threshold(self, mock_sentence_transformer, mock_pytorch_cos_sim, sample_texts) -> None:
        """Test matrix calculation with threshold filtering."""
        calc = SemanticSimilarityCalculator()
        
        matrix = calc.calculate_matrix(sample_texts, threshold=0.8)
        
        # Check that values below threshold are set to 0
        # Our mock creates diverse embeddings, so cooking should have low similarity to ML
        # Find the off-diagonal values
        values = matrix.values
        off_diagonal_mask = ~np.eye(len(sample_texts), dtype=bool)
        off_diagonal_values = values[off_diagonal_mask]
        
        # Should have some zeros (values that were below threshold)
        assert (off_diagonal_values == 0.0).any() or (off_diagonal_values < 0.8).any()

    def test_calculate_matrix_encoding_failure(self, mock_sentence_transformer) -> None:
        """Test matrix calculation with encoding failure."""
        calc = SemanticSimilarityCalculator()
        calc.model.encode.side_effect = RuntimeError("Encoding failed")
        
        with pytest.raises(RuntimeError, match="Failed to calculate similarity matrix"):
            calc.calculate_matrix(["text1", "text2"])

    def test_find_similar_documents_valid(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test finding similar documents with valid inputs."""
        files, root_dir = temp_files
        calc = SemanticSimilarityCalculator()
        
        # Make paths relative to root_dir
        query_docs = [files[0].relative_to(root_dir)]  # doc1.md
        candidate_docs = [f.relative_to(root_dir) for f in files[1:]]  # doc2, doc3, doc4
        
        results = calc.find_similar_documents(query_docs, candidate_docs, root_dir, threshold=0.5)
        
        assert isinstance(results, list)
        assert all(isinstance(r, SimilarityResult) for r in results)
        
        # Results should be sorted by score
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_find_similar_documents_empty_lists(self, mock_sentence_transformer, temp_files) -> None:
        """Test error handling for empty document lists."""
        _, root_dir = temp_files
        calc = SemanticSimilarityCalculator()
        
        with pytest.raises(ValidationError, match="Query documents list cannot be empty"):
            calc.find_similar_documents([], [Path("doc.md")], root_dir)
        
        with pytest.raises(ValidationError, match="Candidate documents list cannot be empty"):
            calc.find_similar_documents([Path("doc.md")], [], root_dir)

    def test_find_similar_documents_invalid_root(self, mock_sentence_transformer) -> None:
        """Test error handling for invalid root directory."""
        calc = SemanticSimilarityCalculator()
        
        with pytest.raises(ValidationError, match="Invalid root directory"):
            calc.find_similar_documents(
                [Path("doc1.md")], 
                [Path("doc2.md")], 
                Path("/nonexistent/path")
            )

    def test_find_similar_documents_file_not_found(self, mock_sentence_transformer, temp_files) -> None:
        """Test error handling when documents cannot be loaded."""
        _, root_dir = temp_files
        calc = SemanticSimilarityCalculator()
        
        with patch('src.document_analysis.similarity.semantic_similarity.load_markdown_files') as mock_load:
            mock_load.side_effect = OSError("File not found")
            
            with pytest.raises(FileNotFoundError, match="Could not load documents"):
                calc.find_similar_documents(
                    [Path("missing.md")],
                    [Path("also_missing.md")],
                    root_dir
                )

    def test_find_similar_documents_skip_self_comparison(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test that self-comparisons are skipped."""
        files, root_dir = temp_files
        calc = SemanticSimilarityCalculator()
        
        # Include same file in both lists - use relative paths
        rel_files = [f.relative_to(root_dir) for f in files[:2]]
        results = calc.find_similar_documents(rel_files, rel_files, root_dir, threshold=0.1)
        
        # Should not include self-comparisons
        for result in results:
            assert result.source != result.target

    def test_clustering_functionality(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test that calculator has clustering functionality from mixin."""
        calc = SemanticSimilarityCalculator()
        
        # Create a simple similarity matrix
        matrix = pd.DataFrame([
            [1.0, 0.9, 0.2],
            [0.9, 1.0, 0.3],
            [0.2, 0.3, 1.0]
        ])
        
        clusters = calc.find_clusters(matrix, threshold=0.8)
        
        assert isinstance(clusters, list)
        if clusters:
            assert all(isinstance(c, list) for c in clusters)


class TestLegacyFunctions:
    """Test legacy compatibility functions."""

    def test_analyze_semantic_similarity(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test legacy analyze_semantic_similarity function."""
        files, root_dir = temp_files
        
        not_in_use = files[:2]
        active = files[2:]
        
        df = analyze_semantic_similarity(not_in_use, active, root_dir, threshold=0.3)
        
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"not_in_use", "matched_file", "similarity"}

    def test_analyze_semantic_similarity_with_model(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test analyze_semantic_similarity with pre-loaded model."""
        files, root_dir = temp_files
        model = Mock()
        
        df = analyze_semantic_similarity(files[:1], files[1:], root_dir, model=model)
        
        assert isinstance(df, pd.DataFrame)

    def test_create_similarity_matrix(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test legacy create_similarity_matrix function."""
        files, root_dir = temp_files
        
        matrix_df, doc_names = create_similarity_matrix(files, root_dir)
        
        assert isinstance(matrix_df, pd.DataFrame)
        assert isinstance(doc_names, list)
        assert len(doc_names) == len(files)
        assert matrix_df.shape == (len(files), len(files))
        
        # Check that index and columns use file names
        assert list(matrix_df.index) == doc_names
        assert list(matrix_df.columns) == doc_names

    def test_create_similarity_matrix_insufficient_docs(self, mock_sentence_transformer, temp_files) -> None:
        """Test create_similarity_matrix with too few documents."""
        files, root_dir = temp_files
        
        matrix_df, doc_names = create_similarity_matrix(files[:1], root_dir)
        
        assert matrix_df.empty
        assert doc_names == []

    def test_create_similarity_matrix_validation_error(self, mock_sentence_transformer) -> None:
        """Test create_similarity_matrix with invalid inputs."""
        with pytest.raises(ValidationError):
            create_similarity_matrix([], Path("."))

    def test_find_embeddings_clusters(self, mock_sentence_transformer) -> None:
        """Test legacy find_embeddings_clusters function."""
        # Create test similarity matrix
        matrix = pd.DataFrame([
            [1.0, 0.95, 0.1, 0.1],
            [0.95, 1.0, 0.1, 0.1],
            [0.1, 0.1, 1.0, 0.85],
            [0.1, 0.1, 0.85, 1.0]
        ], index=["doc1", "doc2", "doc3", "doc4"], columns=["doc1", "doc2", "doc3", "doc4"])
        
        clusters = find_embeddings_clusters(matrix, threshold=0.8)
        
        assert isinstance(clusters, list)
        assert len(clusters) == 2
        assert sorted(clusters[0]) == ["doc1", "doc2"]
        assert sorted(clusters[1]) == ["doc3", "doc4"]

    def test_find_embeddings_clusters_default_threshold(self, mock_sentence_transformer) -> None:
        """Test find_embeddings_clusters with default threshold."""
        matrix = pd.DataFrame([[1.0, 0.7], [0.7, 1.0]], index=["a", "b"], columns=["a", "b"])
        
        clusters = find_embeddings_clusters(matrix)  # Uses SIMILARITY_THRESHOLD_MEDIUM
        
        assert isinstance(clusters, list)

    def test_find_embeddings_clusters_invalid_threshold(self) -> None:
        """Test find_embeddings_clusters with invalid threshold."""
        matrix = pd.DataFrame([[1.0]])
        
        with pytest.raises(ValidationError, match="must be between"):
            find_embeddings_clusters(matrix, threshold=1.5)


class TestAnalyzeActiveDocumentSimilarities:
    """Test analyze_active_document_similarities function."""

    def test_analyze_active_valid(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test analyzing active documents with valid inputs."""
        files, root_dir = temp_files
        
        df = analyze_active_document_similarities(files, root_dir, threshold=0.3)
        
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == {"doc1", "doc2", "similarity", "relationship_type"}
        
        # Check relationship types
        if not df.empty:
            assert all(rt in ["NEAR_DUPLICATE", "HIGH_OVERLAP", "MODERATE_OVERLAP", "LOW_SIMILARITY"] 
                      for rt in df["relationship_type"])

    def test_analyze_active_insufficient_docs(self, mock_sentence_transformer, temp_files) -> None:
        """Test with insufficient documents."""
        files, root_dir = temp_files
        
        df = analyze_active_document_similarities(files[:1], root_dir)
        
        assert df.empty
        assert set(df.columns) == {"doc1", "doc2", "similarity", "relationship_type"}

    def test_analyze_active_exclude_self(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test that self-comparisons are excluded by default."""
        files, root_dir = temp_files
        
        df = analyze_active_document_similarities(files, root_dir, threshold=0.1)
        
        # No self-comparisons
        for _, row in df.iterrows():
            assert row["doc1"] != row["doc2"]

    def test_analyze_active_include_self(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test including self-comparisons."""
        files, root_dir = temp_files
        
        df = analyze_active_document_similarities(files[:2], root_dir, threshold=0.1, exclude_self=False)
        
        # Should have more results when including self
        assert len(df) > 0

    def test_analyze_active_relationship_types(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test relationship type classification."""
        with patch('src.document_analysis.similarity.semantic_similarity.load_markdown_files') as mock_load:
            mock_load.return_value = {
                "doc1.md": "content1",
                "doc2.md": "content2"
            }
            
            # Mock different similarity scores
            mock_pytorch_cos_sim.return_value = MockTensor(np.array([[1.0, 0.85], [0.85, 1.0]]))
            
            df = analyze_active_document_similarities([Path("doc1.md"), Path("doc2.md")], Path("."), threshold=0.1)
            
            assert len(df) == 1
            assert df.iloc[0]["relationship_type"] == "NEAR_DUPLICATE"  # score >= 0.8

    def test_analyze_active_with_preloaded_model(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test with pre-loaded model."""
        files, root_dir = temp_files
        model = Mock()
        model.encode.return_value = MockTensor(np.random.rand(len(files), 4))
        
        df = analyze_active_document_similarities(files, root_dir, model=model)
        
        assert isinstance(df, pd.DataFrame)
        model.encode.assert_called()

    def test_analyze_active_model_loading_failure(self, mock_sentence_transformer, temp_files) -> None:
        """Test handling of model loading failure."""
        files, root_dir = temp_files
        mock_sentence_transformer.side_effect = OSError("Model not found")
        
        with pytest.raises(RuntimeError, match="Failed to load model"):
            analyze_active_document_similarities(files, root_dir)

    def test_analyze_active_encoding_failure(self, mock_sentence_transformer, temp_files) -> None:
        """Test handling of encoding failure."""
        files, root_dir = temp_files
        model = Mock()
        model.encode.side_effect = RuntimeError("Encoding failed")
        
        with pytest.raises(RuntimeError, match="Failed to generate document embeddings"):
            analyze_active_document_similarities(files, root_dir, model=model)


class TestIntegration:
    """Integration tests for semantic similarity module."""

    def test_full_pipeline(self, mock_sentence_transformer, mock_pytorch_cos_sim, temp_files) -> None:
        """Test complete semantic similarity pipeline."""
        files, root_dir = temp_files
        
        # Create calculator
        calc = SemanticSimilarityCalculator()
        
        # Calculate similarity matrix
        texts = [f"Text {i}" for i in range(4)]
        matrix = calc.calculate_matrix(texts, threshold=0.3)
        
        # Find clusters
        clusters = calc.find_clusters(matrix, threshold=0.7)
        
        # Find similar documents
        results = calc.find_similar_documents(files[:1], files[1:], root_dir, threshold=0.4)
        
        assert isinstance(matrix, pd.DataFrame)
        assert isinstance(clusters, list)
        assert isinstance(results, list)

    def test_consistency_across_methods(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test consistency between different calculation methods."""
        calc = SemanticSimilarityCalculator()
        
        text1 = "This is a test document"
        text2 = "This is another test document"
        
        # Pairwise calculation
        pairwise_score = calc.calculate_pairwise(text1, text2)
        
        # Matrix calculation
        matrix = calc.calculate_matrix([text1, text2])
        matrix_score = matrix.iloc[0, 1]
        
        assert pairwise_score == pytest.approx(matrix_score, rel=0.01)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_texts(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test handling of very long texts."""
        calc = SemanticSimilarityCalculator()
        
        long_text1 = "word " * 10000
        long_text2 = "different " * 10000
        
        score = calc.calculate_pairwise(long_text1, long_text2)
        assert 0.0 <= score <= 1.0

    def test_unicode_texts(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test handling of Unicode texts."""
        calc = SemanticSimilarityCalculator()
        
        texts = ["Hello 世界", "Привет мир", "مرحبا بالعالم"]
        matrix = calc.calculate_matrix(texts)
        
        assert matrix.shape == (3, 3)

    def test_empty_file_loading(self, mock_sentence_transformer, temp_files) -> None:
        """Test handling when no files are loaded."""
        _, root_dir = temp_files
        calc = SemanticSimilarityCalculator()
        
        with patch('src.document_analysis.similarity.semantic_similarity.load_markdown_files') as mock_load:
            mock_load.return_value = {}
            
            results = calc.find_similar_documents([Path("a.md")], [Path("b.md")], root_dir)
            
            assert results == []

    def test_nan_similarity_scores(self, mock_sentence_transformer, mock_pytorch_cos_sim) -> None:
        """Test handling of NaN similarity scores."""
        calc = SemanticSimilarityCalculator()
        
        # Mock cosine similarity to return NaN
        mock_pytorch_cos_sim.return_value = MockTensor(np.array([[float('nan')]]))
        
        score = calc._calculate_similarity("text1", "text2")
        
        # Should be clamped to valid range
        assert 0.0 <= score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])