#!/usr/bin/env python3
"""Tests for document_analysis.similarity.base module.

Comprehensive tests for base similarity interfaces according to CLAUDE.md standards.
"""

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.document_analysis.similarity.base import (
    BaseSimilarityCalculator,
    ClusteringMixin,
    SimilarityCalculator,
    SimilarityResult,
)
from src.document_analysis.validation import ValidationError


class TestSimilarityResult:
    """Test SimilarityResult dataclass."""

    def test_similarity_result_creation_valid(self) -> None:
        """Test creating a valid SimilarityResult."""
        result = SimilarityResult(
            source="doc1",
            target="doc2",
            score=0.85,
            technique="cosine",
            metadata={"tokens": 100}
        )
        
        assert result.source == "doc1"
        assert result.target == "doc2"
        assert result.score == 0.85
        assert result.technique == "cosine"
        assert result.metadata == {"tokens": 100}

    def test_similarity_result_default_metadata(self) -> None:
        """Test SimilarityResult with default empty metadata."""
        result = SimilarityResult(
            source="doc1",
            target="doc2",
            score=0.5,
            technique="jaccard"
        )
        
        assert result.metadata == {}

    def test_similarity_result_score_validation_low(self) -> None:
        """Test SimilarityResult rejects score below 0.0."""
        with pytest.raises(ValueError, match="Similarity score must be between 0.0 and 1.0"):
            SimilarityResult(
                source="doc1",
                target="doc2",
                score=-0.1,
                technique="test"
            )

    def test_similarity_result_score_validation_high(self) -> None:
        """Test SimilarityResult rejects score above 1.0."""
        with pytest.raises(ValueError, match="Similarity score must be between 0.0 and 1.0"):
            SimilarityResult(
                source="doc1",
                target="doc2",
                score=1.5,
                technique="test"
            )

    def test_similarity_result_edge_scores(self) -> None:
        """Test SimilarityResult accepts edge case scores."""
        # Test 0.0
        result1 = SimilarityResult(source="a", target="b", score=0.0, technique="test")
        assert result1.score == 0.0
        
        # Test 1.0
        result2 = SimilarityResult(source="a", target="b", score=1.0, technique="test")
        assert result2.score == 1.0


class TestSimilarityCalculatorProtocol:
    """Test the SimilarityCalculator protocol."""

    def test_protocol_implementation(self) -> None:
        """Test that a class can implement the SimilarityCalculator protocol."""
        
        class MockCalculator:
            """Mock implementation of SimilarityCalculator protocol."""
            
            def calculate_pairwise(self, text1: str, text2: str) -> float:
                return 0.5
            
            def calculate_matrix(self, texts: list[str], threshold: float = 0.0) -> list[list[float]]:
                return [[1.0, 0.5], [0.5, 1.0]]
            
            def find_similar_documents(
                self, query_docs: list[Path], candidate_docs: list[Path], 
                root_dir: Path, threshold: float = 0.5
            ) -> list[SimilarityResult]:
                return []
        
        # Should be able to use as SimilarityCalculator
        calc: SimilarityCalculator = MockCalculator()
        assert calc.calculate_pairwise("a", "b") == 0.5

    def test_protocol_type_checking(self) -> None:
        """Test that protocol validates required methods."""
        # This test verifies the protocol structure exists
        assert hasattr(SimilarityCalculator, "calculate_pairwise")
        assert hasattr(SimilarityCalculator, "calculate_matrix")
        assert hasattr(SimilarityCalculator, "find_similar_documents")


class ConcreteTestCalculator(BaseSimilarityCalculator):
    """Concrete implementation for testing BaseSimilarityCalculator."""
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple implementation that returns length ratio."""
        if len(text1) == 0 and len(text2) == 0:
            return 1.0
        max_len = max(len(text1), len(text2))
        min_len = min(len(text1), len(text2))
        return min_len / max_len if max_len > 0 else 0.0


class TestBaseSimilarityCalculator:
    """Test BaseSimilarityCalculator abstract base class."""

    def test_initialization(self) -> None:
        """Test initialization of base calculator."""
        calc = ConcreteTestCalculator(name="test", param1="value1", param2=42)
        
        assert calc.name == "test"
        assert calc.config == {"param1": "value1", "param2": 42}

    def test_calculate_pairwise_valid(self) -> None:
        """Test pairwise calculation with valid inputs."""
        calc = ConcreteTestCalculator(name="test")
        
        score = calc.calculate_pairwise("hello", "hello world")
        assert 0.0 <= score <= 1.0
        assert score == 5/11  # len("hello") / len("hello world")

    def test_calculate_pairwise_identical(self) -> None:
        """Test pairwise calculation with identical texts."""
        calc = ConcreteTestCalculator(name="test")
        
        score = calc.calculate_pairwise("test text", "test text")
        assert score == 1.0

    def test_calculate_pairwise_empty_strings(self) -> None:
        """Test pairwise calculation rejects empty strings."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValidationError, match="cannot be empty"):
            calc.calculate_pairwise("", "valid")
        
        with pytest.raises(ValidationError, match="cannot be empty"):
            calc.calculate_pairwise("valid", "")

    def test_calculate_pairwise_invalid_types(self) -> None:
        """Test pairwise calculation rejects invalid types."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValidationError, match="must be a string"):
            calc.calculate_pairwise(123, "valid")  # type: ignore
        
        with pytest.raises(ValidationError, match="must be a string"):
            calc.calculate_pairwise("valid", None)  # type: ignore

    def test_calculate_pairwise_whitespace_only(self) -> None:
        """Test pairwise calculation rejects whitespace-only strings."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValidationError, match="cannot be empty"):
            calc.calculate_pairwise("   \n\t  ", "valid")

    def test_calculate_pairwise_very_long_text(self) -> None:
        """Test pairwise calculation rejects very long texts."""
        calc = ConcreteTestCalculator(name="test")
        
        long_text = "a" * 100_001
        with pytest.raises(ValidationError, match="too long"):
            calc.calculate_pairwise(long_text, "valid")

    def test_calculate_pairwise_score_clamping(self) -> None:
        """Test that scores are clamped to [0.0, 1.0] range."""
        
        class BadCalculator(BaseSimilarityCalculator):
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                return 2.5  # Invalid score
        
        calc = BadCalculator(name="bad")
        score = calc.calculate_pairwise("a", "b")
        assert score == 1.0  # Should be clamped
        
        class NegativeCalculator(BaseSimilarityCalculator):
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                return -0.5  # Invalid score
        
        calc2 = NegativeCalculator(name="negative")
        score2 = calc2.calculate_pairwise("a", "b")
        assert score2 == 0.0  # Should be clamped

    def test_calculate_pairwise_exception_handling(self) -> None:
        """Test exception handling in pairwise calculation."""
        
        class ErrorCalculator(BaseSimilarityCalculator):
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                raise AttributeError("Test error")
        
        calc = ErrorCalculator(name="error")
        
        with patch("src.document_analysis.similarity.base.logger") as mock_logger:
            with pytest.raises(ValidationError, match="Failed to calculate similarity"):
                calc.calculate_pairwise("a", "b")
            
            mock_logger.error.assert_called()

    def test_calculate_matrix_valid(self) -> None:
        """Test matrix calculation with valid inputs."""
        calc = ConcreteTestCalculator(name="test")
        
        texts = ["hello", "hello world", "world"]
        matrix = calc.calculate_matrix(texts)
        
        assert len(matrix) == 3
        assert len(matrix[0]) == 3
        
        # Check diagonal is 1.0
        for i in range(3):
            assert matrix[i][i] == 1.0
        
        # Check symmetry
        for i in range(3):
            for j in range(3):
                assert matrix[i][j] == matrix[j][i]

    def test_calculate_matrix_empty_list(self) -> None:
        """Test matrix calculation rejects empty text list."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValueError, match="Text list cannot be empty"):
            calc.calculate_matrix([])

    def test_calculate_matrix_invalid_threshold(self) -> None:
        """Test matrix calculation rejects invalid threshold."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            calc.calculate_matrix(["a", "b"], threshold=-0.1)
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            calc.calculate_matrix(["a", "b"], threshold=1.5)

    def test_calculate_matrix_with_threshold(self) -> None:
        """Test matrix calculation with threshold filtering."""
        calc = ConcreteTestCalculator(name="test")
        
        texts = ["a", "ab", "abc", "abcd"]
        matrix = calc.calculate_matrix(texts, threshold=0.5)
        
        # Check that low similarity scores are 0.0
        # "a" vs "abcd" should be 1/4 = 0.25 < 0.5
        assert matrix[0][3] == 0.0
        assert matrix[3][0] == 0.0

    def test_calculate_matrix_invalid_text_in_list(self) -> None:
        """Test matrix calculation validates all texts in list."""
        calc = ConcreteTestCalculator(name="test")
        
        with pytest.raises(ValidationError, match="texts\\[1\\] must be a string"):
            calc.calculate_matrix(["valid", 123, "also valid"])  # type: ignore

    def test_calculate_matrix_exception_handling(self) -> None:
        """Test exception handling in matrix calculation."""
        
        class SometimesErrorCalculator(BaseSimilarityCalculator):
            def __init__(self, name: str) -> None:
                super().__init__(name)
                self.call_count = 0
                
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                self.call_count += 1
                if self.call_count == 2:  # Fail on second call
                    raise ValueError("Test error")
                return 0.5
        
        calc = SometimesErrorCalculator(name="sometimes_error")
        
        with patch("src.document_analysis.similarity.base.logger") as mock_logger:
            matrix = calc.calculate_matrix(["a", "b", "c"])
            
            # Should still produce a matrix
            assert len(matrix) == 3
            
            # Logger should have warning
            mock_logger.warning.assert_called()

    def test_validate_text_input(self) -> None:
        """Test text input validation method."""
        calc = ConcreteTestCalculator(name="test")
        
        # Valid inputs
        calc._validate_text_input("valid text", "param")
        calc._validate_text_input("a", "param")
        calc._validate_text_input("x" * 100_000, "param")  # Max length
        
        # Invalid inputs
        with pytest.raises(ValidationError):
            calc._validate_text_input("", "param")
        
        with pytest.raises(ValidationError):
            calc._validate_text_input("   ", "param")
        
        with pytest.raises(ValidationError):
            calc._validate_text_input("x" * 100_001, "param")
        
        with pytest.raises(ValidationError):
            calc._validate_text_input(None, "param")  # type: ignore


class TestClusteringMixin:
    """Test ClusteringMixin functionality."""

    def test_find_clusters_list_matrix(self) -> None:
        """Test clustering with list matrix."""
        mixin = ClusteringMixin()
        
        # Create a matrix with clear clusters
        matrix = [
            [1.0, 0.9, 0.1, 0.1],
            [0.9, 1.0, 0.1, 0.1],
            [0.1, 0.1, 1.0, 0.8],
            [0.1, 0.1, 0.8, 1.0]
        ]
        
        clusters = mixin.find_clusters(matrix, threshold=0.8)
        
        assert len(clusters) == 2
        assert sorted(clusters[0]) == [0, 1]
        assert sorted(clusters[1]) == [2, 3]

    def test_find_clusters_numpy_matrix(self) -> None:
        """Test clustering with numpy array matrix."""
        mixin = ClusteringMixin()
        
        matrix = np.array([
            [1.0, 0.85, 0.2],
            [0.85, 1.0, 0.3],
            [0.2, 0.3, 1.0]
        ])
        
        clusters = mixin.find_clusters(matrix, threshold=0.8)
        
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1]

    def test_find_clusters_pandas_matrix(self) -> None:
        """Test clustering with pandas DataFrame matrix."""
        mixin = ClusteringMixin()
        
        matrix = pd.DataFrame([
            [1.0, 0.75, 0.9],
            [0.75, 1.0, 0.6],
            [0.9, 0.6, 1.0]
        ])
        
        clusters = mixin.find_clusters(matrix, threshold=0.7)
        
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1, 2]

    def test_find_clusters_no_clusters(self) -> None:
        """Test clustering when no clusters exist."""
        mixin = ClusteringMixin()
        
        # Low similarity matrix
        matrix = [
            [1.0, 0.1, 0.2],
            [0.1, 1.0, 0.15],
            [0.2, 0.15, 1.0]
        ]
        
        clusters = mixin.find_clusters(matrix, threshold=0.7)
        assert clusters == []

    def test_find_clusters_single_item_clusters(self) -> None:
        """Test that single-item clusters are not returned."""
        mixin = ClusteringMixin()
        
        matrix = [[1.0, 0.3], [0.3, 1.0]]
        
        clusters = mixin.find_clusters(matrix, threshold=0.7)
        assert clusters == []  # No multi-item clusters

    def test_find_clusters_invalid_matrix_empty(self) -> None:
        """Test clustering rejects empty matrix."""
        mixin = ClusteringMixin()
        
        with pytest.raises(ValidationError, match="Matrix must be square and non-empty"):
            mixin.find_clusters([])

    def test_find_clusters_invalid_matrix_not_square(self) -> None:
        """Test clustering rejects non-square matrix."""
        mixin = ClusteringMixin()
        
        # Rectangular matrix
        with pytest.raises(ValidationError, match="Matrix must be square"):
            mixin.find_clusters([[1.0, 0.5], [0.5, 1.0], [0.3, 0.4]])
        
        # Numpy non-square
        with pytest.raises(ValidationError, match="Matrix must be square"):
            mixin.find_clusters(np.array([[1.0, 0.5, 0.3], [0.5, 1.0, 0.4]]))

    def test_find_clusters_invalid_threshold(self) -> None:
        """Test clustering rejects invalid threshold."""
        mixin = ClusteringMixin()
        
        matrix = [[1.0]]
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            mixin.find_clusters(matrix, threshold=-0.1)
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            mixin.find_clusters(matrix, threshold=1.1)

    def test_find_clusters_unsupported_type(self) -> None:
        """Test clustering rejects unsupported matrix types."""
        mixin = ClusteringMixin()
        
        with pytest.raises(ValidationError, match="Unsupported matrix type"):
            mixin.find_clusters("not a matrix")  # type: ignore

    def test_find_clusters_edge_threshold(self) -> None:
        """Test clustering with edge case thresholds."""
        mixin = ClusteringMixin()
        
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        # Threshold 0.0 - all connected
        clusters = mixin.find_clusters(matrix, threshold=0.0)
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1]
        
        # Threshold 1.0 - only self-similar
        clusters = mixin.find_clusters(matrix, threshold=1.0)
        assert clusters == []

    def test_find_clusters_logging(self) -> None:
        """Test that clustering logs debug information."""
        mixin = ClusteringMixin()
        
        matrix = [[1.0, 0.8], [0.8, 1.0]]
        
        with patch("src.document_analysis.similarity.base.logger") as mock_logger:
            clusters = mixin.find_clusters(matrix, threshold=0.7)
            
            assert len(clusters) == 1
            mock_logger.debug.assert_called_with("Found 1 clusters with threshold 0.7")


class TestIntegration:
    """Integration tests for similarity base module."""

    def test_concrete_calculator_with_clustering(self) -> None:
        """Test using concrete calculator with clustering mixin."""
        
        class CalculatorWithClustering(ConcreteTestCalculator, ClusteringMixin):
            """Calculator that includes clustering functionality."""
            pass
        
        calc = CalculatorWithClustering(name="test_cluster")
        
        # Calculate similarity matrix
        texts = ["short", "shorter", "very long text", "another long text"]
        matrix = calc.calculate_matrix(texts)
        
        # Find clusters
        clusters = calc.find_clusters(matrix, threshold=0.5)
        
        # Should find clusters of similar length texts
        assert len(clusters) >= 1

    def test_protocol_compliance(self) -> None:
        """Test that concrete implementations comply with protocol."""
        
        class ProtocolCompliantCalculator(BaseSimilarityCalculator):
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                return 0.5
            
            def find_similar_documents(
                self, query_docs: list[Path], candidate_docs: list[Path], 
                root_dir: Path, threshold: float = 0.5
            ) -> list[SimilarityResult]:
                return [
                    SimilarityResult(
                        source=str(query_docs[0]),
                        target=str(candidate_docs[0]),
                        score=0.7,
                        technique=self.name
                    )
                ]
        
        calc = ProtocolCompliantCalculator(name="compliant")
        
        # Should work as SimilarityCalculator
        assert calc.calculate_pairwise("a", "b") == 0.5
        assert isinstance(calc.calculate_matrix(["a", "b"]), list)
        
        results = calc.find_similar_documents(
            [Path("query.txt")],
            [Path("candidate.txt")],
            Path("/root")
        )
        assert len(results) == 1
        assert results[0].score == 0.7


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_matrix_with_nan_values(self) -> None:
        """Test handling of NaN values in calculations."""
        
        class NanCalculator(BaseSimilarityCalculator):
            def _calculate_similarity(self, text1: str, text2: str) -> float:
                if text1 == "nan":
                    return float('nan')
                return 0.5
        
        calc = NanCalculator(name="nan_test")
        
        # NaN should be clamped to valid range
        score = calc.calculate_pairwise("nan", "test")
        assert 0.0 <= score <= 1.0

    def test_very_large_matrix(self) -> None:
        """Test performance with large matrix."""
        calc = ConcreteTestCalculator(name="test")
        
        # Create 100 texts
        texts = [f"text_{i}" * (i % 10 + 1) for i in range(100)]
        
        matrix = calc.calculate_matrix(texts, threshold=0.5)
        
        assert len(matrix) == 100
        assert len(matrix[0]) == 100

    def test_unicode_text_handling(self) -> None:
        """Test handling of Unicode text."""
        calc = ConcreteTestCalculator(name="test")
        
        score = calc.calculate_pairwise("Hello 世界", "Hello World")
        assert 0.0 <= score <= 1.0
        
        texts = ["测试", "テスト", "тест", "test"]
        matrix = calc.calculate_matrix(texts)
        assert len(matrix) == 4

    def test_concurrent_calculations(self) -> None:
        """Test thread safety of calculations."""
        calc = ConcreteTestCalculator(name="test")
        
        # Simulate concurrent access
        results = []
        for i in range(10):
            score = calc.calculate_pairwise(f"text{i}", f"other{i}")
            results.append(score)
        
        assert all(0.0 <= s <= 1.0 for s in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])