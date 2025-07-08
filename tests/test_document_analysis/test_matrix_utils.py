#!/usr/bin/env python3
"""Tests for document_analysis.similarity.matrix_utils module.

Comprehensive tests for matrix utility functions according to CLAUDE.md standards.
"""

import logging
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.document_analysis.similarity.matrix_utils import (
    convert_matrix_format,
    create_empty_matrix,
    filter_matrix_by_threshold,
    find_clusters_in_matrix,
    get_matrix_stats,
    normalize_matrix,
)
from src.document_analysis.validation import ValidationError


class TestCreateEmptyMatrix:
    """Test create_empty_matrix function."""

    def test_create_matrix_default_fill(self) -> None:
        """Test creating matrix with default fill value."""
        matrix = create_empty_matrix(3)
        
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        
        # Check diagonal is 1.0
        for i in range(3):
            assert matrix[i][i] == 1.0
        
        # Check off-diagonal is 0.0
        assert matrix[0][1] == 0.0
        assert matrix[1][2] == 0.0

    def test_create_matrix_custom_fill(self) -> None:
        """Test creating matrix with custom fill value."""
        matrix = create_empty_matrix(2, fill_value=0.5)
        
        assert len(matrix) == 2
        assert matrix[0][1] == 0.5
        assert matrix[1][0] == 0.5
        
        # Diagonal should still be 1.0
        assert matrix[0][0] == 1.0
        assert matrix[1][1] == 1.0

    def test_create_matrix_fill_one(self) -> None:
        """Test creating matrix filled with 1.0."""
        matrix = create_empty_matrix(2, fill_value=1.0)
        
        # All values should be 1.0
        assert all(all(val == 1.0 for val in row) for row in matrix)

    def test_create_matrix_invalid_size(self) -> None:
        """Test error handling for invalid size."""
        with pytest.raises(ValidationError, match="Matrix size must be positive integer"):
            create_empty_matrix(0)
        
        with pytest.raises(ValidationError, match="Matrix size must be positive integer"):
            create_empty_matrix(-1)
        
        with pytest.raises(ValidationError, match="Matrix size must be positive integer"):
            create_empty_matrix(2.5)  # type: ignore

    def test_create_matrix_invalid_fill_value(self) -> None:
        """Test error handling for invalid fill value."""
        with pytest.raises(ValidationError, match="Fill value must be numeric"):
            create_empty_matrix(3, fill_value="invalid")  # type: ignore

    def test_create_matrix_large_size(self) -> None:
        """Test creating large matrix."""
        matrix = create_empty_matrix(100)
        assert len(matrix) == 100
        assert len(matrix[0]) == 100

    def test_create_matrix_logging(self) -> None:
        """Test that matrix creation logs debug info."""
        with patch("src.document_analysis.similarity.matrix_utils.logger") as mock_logger:
            matrix = create_empty_matrix(3, fill_value=0.2)
            
            mock_logger.debug.assert_called_with("Created 3x3 matrix with fill_value=0.2")


class TestNormalizeMatrix:
    """Test normalize_matrix function."""

    def test_normalize_list_matrix_minmax(self) -> None:
        """Test min-max normalization of list matrix."""
        matrix = [[1.0, 0.2], [0.2, 1.0]]
        normalized = normalize_matrix(matrix, method="minmax")
        
        assert isinstance(normalized, list)
        assert normalized[0][0] == 1.0  # Max value
        assert normalized[0][1] == 0.0  # Min value
        assert normalized[1][0] == 0.0  # Min value
        assert normalized[1][1] == 1.0  # Max value

    def test_normalize_numpy_matrix_minmax(self) -> None:
        """Test min-max normalization of numpy array."""
        matrix = np.array([[1.0, 0.5], [0.5, 1.0]])
        normalized = normalize_matrix(matrix, method="minmax")
        
        assert isinstance(normalized, np.ndarray)
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0

    def test_normalize_dataframe_matrix_minmax(self) -> None:
        """Test min-max normalization of pandas DataFrame."""
        matrix = pd.DataFrame([[1.0, 0.3], [0.3, 1.0]], 
                            index=['A', 'B'], 
                            columns=['A', 'B'])
        normalized = normalize_matrix(matrix, method="minmax")
        
        assert isinstance(normalized, pd.DataFrame)
        assert list(normalized.index) == ['A', 'B']
        assert list(normalized.columns) == ['A', 'B']
        assert normalized.min().min() == 0.0
        assert normalized.max().max() == 1.0

    def test_normalize_zscore(self) -> None:
        """Test z-score normalization."""
        matrix = [[1.0, 0.2, 0.8], [0.2, 1.0, 0.5], [0.8, 0.5, 1.0]]
        normalized = normalize_matrix(matrix, method="zscore")
        
        assert isinstance(normalized, list)
        # Check that mean is approximately 0
        flat = [val for row in normalized for val in row]
        assert abs(np.mean(flat)) < 0.001
        # Check that std is approximately 1
        assert abs(np.std(flat) - 1.0) < 0.001

    def test_normalize_none_method(self) -> None:
        """Test no normalization."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        normalized = normalize_matrix(matrix, method="none")
        
        assert normalized == matrix

    def test_normalize_constant_matrix(self) -> None:
        """Test normalization of matrix with constant values."""
        matrix = [[0.5, 0.5], [0.5, 0.5]]
        
        with patch("src.document_analysis.similarity.matrix_utils.logger") as mock_logger:
            normalized = normalize_matrix(matrix, method="minmax")
            # Should return unchanged matrix and log warning
            assert normalized == matrix
            mock_logger.warning.assert_called()

    def test_normalize_zero_std_matrix(self) -> None:
        """Test z-score normalization with zero standard deviation."""
        matrix = [[0.7, 0.7], [0.7, 0.7]]
        
        with patch("src.document_analysis.similarity.matrix_utils.logger") as mock_logger:
            normalized = normalize_matrix(matrix, method="zscore")
            # Should return unchanged matrix and log warning
            mock_logger.warning.assert_called()

    def test_normalize_invalid_method(self) -> None:
        """Test error handling for invalid normalization method."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with pytest.raises(ValidationError, match="Unsupported normalization method"):
            normalize_matrix(matrix, method="invalid")

    def test_normalize_invalid_matrix_format(self) -> None:
        """Test error handling for invalid matrix format."""
        # Non-numeric values
        with pytest.raises(ValidationError, match="Invalid matrix format"):
            normalize_matrix([["a", "b"], ["c", "d"]], method="minmax")  # type: ignore
        
        # Non-square matrix
        with pytest.raises(ValidationError, match="Matrix must be square"):
            normalize_matrix([[1.0, 0.5]], method="minmax")

    def test_normalize_unsupported_type(self) -> None:
        """Test error handling for unsupported matrix type."""
        with pytest.raises(ValidationError, match="Unsupported matrix type"):
            normalize_matrix("not a matrix", method="minmax")  # type: ignore

    def test_normalize_3d_array(self) -> None:
        """Test error handling for 3D array."""
        matrix = np.array([[[1.0]]])
        
        with pytest.raises(ValidationError, match="must be square 2D array"):
            normalize_matrix(matrix, method="minmax")


class TestFindClustersInMatrix:
    """Test find_clusters_in_matrix function."""

    def test_find_clusters_list_matrix(self) -> None:
        """Test finding clusters in list matrix."""
        matrix = [
            [1.0, 0.9, 0.1, 0.1],
            [0.9, 1.0, 0.1, 0.1],
            [0.1, 0.1, 1.0, 0.85],
            [0.1, 0.1, 0.85, 1.0]
        ]
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.8)
        
        assert len(clusters) == 2
        assert sorted(clusters[0]) == [0, 1]
        assert sorted(clusters[1]) == [2, 3]

    def test_find_clusters_numpy_matrix(self) -> None:
        """Test finding clusters in numpy array."""
        matrix = np.array([
            [1.0, 0.6, 0.7],
            [0.6, 1.0, 0.8],
            [0.7, 0.8, 1.0]
        ])
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.75)
        
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [1, 2]  # Items 1 and 2 have similarity 0.8

    def test_find_clusters_dataframe_matrix(self) -> None:
        """Test finding clusters in pandas DataFrame."""
        matrix = pd.DataFrame([
            [1.0, 0.9, 0.2],
            [0.9, 1.0, 0.3],
            [0.2, 0.3, 1.0]
        ])
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.85)
        
        assert len(clusters) == 1
        assert sorted(clusters[0]) == [0, 1]

    def test_find_clusters_no_clusters(self) -> None:
        """Test when no clusters exist above threshold."""
        matrix = [
            [1.0, 0.3, 0.2],
            [0.3, 1.0, 0.4],
            [0.2, 0.4, 1.0]
        ]
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.8)
        assert clusters == []

    def test_find_clusters_single_element(self) -> None:
        """Test with single element matrix."""
        matrix = [[1.0]]
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.5)
        assert clusters == []  # No multi-item clusters

    def test_find_clusters_invalid_threshold(self) -> None:
        """Test error handling for invalid threshold."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            find_clusters_in_matrix(matrix, threshold=-0.1)
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            find_clusters_in_matrix(matrix, threshold=1.5)

    def test_find_clusters_invalid_matrix(self) -> None:
        """Test error handling for invalid matrix."""
        # Empty list
        with pytest.raises(ValidationError, match="Matrix must be square and non-empty"):
            find_clusters_in_matrix([])
        
        # Non-square list
        with pytest.raises(ValidationError, match="Matrix must be square and non-empty"):
            find_clusters_in_matrix([[1.0, 0.5]])
        
        # Non-square array
        with pytest.raises(ValidationError, match="Matrix must be square"):
            find_clusters_in_matrix(np.array([[1.0, 0.5]]))

    def test_find_clusters_unsupported_type(self) -> None:
        """Test error handling for unsupported matrix type."""
        with pytest.raises(ValidationError, match="Unsupported matrix type"):
            find_clusters_in_matrix("not a matrix")  # type: ignore

    def test_find_clusters_logging(self) -> None:
        """Test that clustering logs debug info."""
        matrix = [[1.0, 0.8], [0.8, 1.0]]
        
        with patch("src.document_analysis.similarity.matrix_utils.logger") as mock_logger:
            clusters = find_clusters_in_matrix(matrix, threshold=0.7)
            
            mock_logger.debug.assert_called_with("Found 1 clusters with threshold 0.7")


class TestGetMatrixStats:
    """Test get_matrix_stats function."""

    def test_get_stats_list_matrix(self) -> None:
        """Test getting stats for list matrix."""
        matrix = [
            [1.0, 0.8, 0.2],
            [0.8, 1.0, 0.5],
            [0.2, 0.5, 1.0]
        ]
        
        stats = get_matrix_stats(matrix)
        
        assert stats["size"] == 3
        assert stats["total_pairs"] == 3  # Upper triangle
        assert stats["mean"] == pytest.approx(0.5, rel=0.01)
        assert stats["min"] == 0.2
        assert stats["max"] == 0.8
        assert stats["high_similarity"] == 1  # One value >= 0.8
        assert stats["medium_similarity"] == 1  # One value in [0.5, 0.8)
        assert stats["low_similarity"] == 1  # One value < 0.5

    def test_get_stats_numpy_matrix(self) -> None:
        """Test getting stats for numpy array."""
        matrix = np.array([
            [1.0, 0.9],
            [0.9, 1.0]
        ])
        
        stats = get_matrix_stats(matrix)
        
        assert stats["size"] == 2
        assert stats["total_pairs"] == 1
        assert stats["mean"] == 0.9
        assert stats["std"] == 0.0
        assert stats["high_similarity"] == 1

    def test_get_stats_dataframe_matrix(self) -> None:
        """Test getting stats for pandas DataFrame."""
        matrix = pd.DataFrame([
            [1.0, 0.3, 0.7],
            [0.3, 1.0, 0.6],
            [0.7, 0.6, 1.0]
        ])
        
        stats = get_matrix_stats(matrix)
        
        assert stats["size"] == 3
        assert stats["total_pairs"] == 3
        assert "percentile_25" in stats
        assert "percentile_75" in stats

    def test_get_stats_single_element(self) -> None:
        """Test getting stats for single element matrix."""
        matrix = [[1.0]]
        
        stats = get_matrix_stats(matrix)
        
        assert stats["size"] == 1
        assert stats["total_pairs"] == 0
        assert stats["mean"] == 0.0
        assert stats["std"] == 0.0

    def test_get_stats_invalid_matrix(self) -> None:
        """Test error handling for invalid matrix."""
        # Non-numeric matrix
        with pytest.raises(ValidationError, match="Invalid matrix format"):
            get_matrix_stats([["a", "b"], ["c", "d"]])  # type: ignore
        
        # Non-square matrix
        with pytest.raises(ValidationError, match="Matrix must be square"):
            get_matrix_stats([[1.0, 0.5]])
        
        # 1D array
        with pytest.raises(ValidationError, match="Matrix must be 2D"):
            get_matrix_stats(np.array([1.0, 0.5]))

    def test_get_stats_unsupported_type(self) -> None:
        """Test error handling for unsupported matrix type."""
        with pytest.raises(ValidationError, match="Unsupported matrix type"):
            get_matrix_stats("not a matrix")  # type: ignore

    def test_get_stats_logging(self) -> None:
        """Test that stats calculation logs debug info."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with patch("src.document_analysis.similarity.matrix_utils.logger") as mock_logger:
            stats = get_matrix_stats(matrix)
            
            mock_logger.debug.assert_called()
            assert "1 pairs" in mock_logger.debug.call_args[0][0]


class TestFilterMatrixByThreshold:
    """Test filter_matrix_by_threshold function."""

    def test_filter_list_matrix(self) -> None:
        """Test filtering list matrix."""
        matrix = [
            [1.0, 0.3, 0.8],
            [0.3, 1.0, 0.4],
            [0.8, 0.4, 1.0]
        ]
        
        filtered = filter_matrix_by_threshold(matrix, threshold=0.5)
        
        assert isinstance(filtered, list)
        # Values below 0.5 should be 0
        assert filtered[0][1] == 0.0
        assert filtered[1][0] == 0.0
        assert filtered[1][2] == 0.0
        assert filtered[2][1] == 0.0
        # Values >= 0.5 should be preserved
        assert filtered[0][2] == 0.8
        assert filtered[2][0] == 0.8
        # Diagonal should be preserved
        assert all(filtered[i][i] == 1.0 for i in range(3))

    def test_filter_numpy_matrix(self) -> None:
        """Test filtering numpy array."""
        matrix = np.array([
            [1.0, 0.2, 0.7],
            [0.2, 1.0, 0.6],
            [0.7, 0.6, 1.0]
        ])
        
        filtered = filter_matrix_by_threshold(matrix, threshold=0.6)
        
        assert isinstance(filtered, np.ndarray)
        assert filtered[0][1] == 0.0  # 0.2 < 0.6
        assert filtered[0][2] == 0.7  # 0.7 >= 0.6
        assert np.all(np.diag(filtered) == 1.0)

    def test_filter_dataframe_matrix(self) -> None:
        """Test filtering pandas DataFrame."""
        matrix = pd.DataFrame([
            [1.0, 0.4, 0.9],
            [0.4, 1.0, 0.3],
            [0.9, 0.3, 1.0]
        ], index=['A', 'B', 'C'], columns=['A', 'B', 'C'])
        
        filtered = filter_matrix_by_threshold(matrix, threshold=0.5)
        
        assert isinstance(filtered, pd.DataFrame)
        assert list(filtered.index) == ['A', 'B', 'C']
        assert filtered.loc['A', 'B'] == 0.0
        assert filtered.loc['A', 'C'] == 0.9

    def test_filter_threshold_zero(self) -> None:
        """Test filtering with threshold 0.0."""
        matrix = [[1.0, 0.1], [0.1, 1.0]]
        
        filtered = filter_matrix_by_threshold(matrix, threshold=0.0)
        
        # All values should be preserved
        assert filtered == matrix

    def test_filter_threshold_one(self) -> None:
        """Test filtering with threshold 1.0."""
        matrix = [[1.0, 0.9], [0.9, 1.0]]
        
        filtered = filter_matrix_by_threshold(matrix, threshold=1.0)
        
        # Only diagonal should remain
        assert filtered[0][1] == 0.0
        assert filtered[1][0] == 0.0
        assert filtered[0][0] == 1.0
        assert filtered[1][1] == 1.0

    def test_filter_invalid_threshold(self) -> None:
        """Test error handling for invalid threshold."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            filter_matrix_by_threshold(matrix, threshold=-0.1)
        
        with pytest.raises(ValidationError, match="Threshold must be between"):
            filter_matrix_by_threshold(matrix, threshold=1.1)

    def test_filter_unsupported_type(self) -> None:
        """Test error handling for unsupported matrix type."""
        with pytest.raises(ValidationError, match="Unsupported matrix type"):
            filter_matrix_by_threshold("not a matrix", threshold=0.5)  # type: ignore


class TestConvertMatrixFormat:
    """Test convert_matrix_format function."""

    def test_convert_list_to_numpy(self) -> None:
        """Test converting list to numpy array."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        converted = convert_matrix_format(matrix, "numpy")
        
        assert isinstance(converted, np.ndarray)
        assert converted.shape == (2, 2)
        assert np.array_equal(converted, np.array(matrix))

    def test_convert_numpy_to_list(self) -> None:
        """Test converting numpy array to list."""
        matrix = np.array([[1.0, 0.8], [0.8, 1.0]])
        
        converted = convert_matrix_format(matrix, "list")
        
        assert isinstance(converted, list)
        assert converted == [[1.0, 0.8], [0.8, 1.0]]

    def test_convert_list_to_dataframe(self) -> None:
        """Test converting list to DataFrame with labels."""
        matrix = [[1.0, 0.7], [0.7, 1.0]]
        
        converted = convert_matrix_format(matrix, "dataframe", labels=['A', 'B'])
        
        assert isinstance(converted, pd.DataFrame)
        assert list(converted.index) == ['A', 'B']
        assert list(converted.columns) == ['A', 'B']
        assert converted.loc['A', 'B'] == 0.7

    def test_convert_dataframe_to_numpy(self) -> None:
        """Test converting DataFrame to numpy array."""
        matrix = pd.DataFrame([[1.0, 0.5], [0.5, 1.0]], 
                            index=['X', 'Y'], 
                            columns=['X', 'Y'])
        
        converted = convert_matrix_format(matrix, "numpy")
        
        assert isinstance(converted, np.ndarray)
        assert converted[0][1] == 0.5

    def test_convert_with_default_labels(self) -> None:
        """Test converting to DataFrame with default labels."""
        matrix = [[1.0, 0.3, 0.6], [0.3, 1.0, 0.4], [0.6, 0.4, 1.0]]
        
        converted = convert_matrix_format(matrix, "dataframe")
        
        assert isinstance(converted, pd.DataFrame)
        assert list(converted.index) == ['item_0', 'item_1', 'item_2']
        assert list(converted.columns) == ['item_0', 'item_1', 'item_2']

    def test_convert_same_format(self) -> None:
        """Test converting to same format."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        converted = convert_matrix_format(matrix, "list")
        
        assert converted == matrix

    def test_convert_invalid_target_format(self) -> None:
        """Test error handling for invalid target format."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with pytest.raises(ValidationError, match="Unsupported target format"):
            convert_matrix_format(matrix, "invalid")

    def test_convert_invalid_input_type(self) -> None:
        """Test error handling for invalid input type."""
        with pytest.raises(ValidationError, match="Unsupported input matrix type"):
            convert_matrix_format("not a matrix", "numpy")  # type: ignore

    def test_convert_mismatched_labels(self) -> None:
        """Test error handling for mismatched labels."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        
        with pytest.raises(ValidationError, match="Labels length .* doesn't match"):
            convert_matrix_format(matrix, "dataframe", labels=['A', 'B', 'C'])

    def test_convert_preserves_values(self) -> None:
        """Test that conversion preserves all values."""
        matrix = [[1.0, 0.123, 0.789], [0.123, 1.0, 0.456], [0.789, 0.456, 1.0]]
        
        # Convert through all formats
        as_numpy = convert_matrix_format(matrix, "numpy")
        as_df = convert_matrix_format(as_numpy, "dataframe")
        back_to_list = convert_matrix_format(as_df, "list")
        
        # Values should be preserved
        for i in range(3):
            for j in range(3):
                assert abs(back_to_list[i][j] - matrix[i][j]) < 1e-10


class TestIntegration:
    """Integration tests for matrix utilities."""

    def test_full_matrix_pipeline(self) -> None:
        """Test complete matrix processing pipeline."""
        # Create matrix
        matrix = create_empty_matrix(4, fill_value=0.0)
        
        # Add some similarity values
        matrix[0][1] = matrix[1][0] = 0.9
        matrix[0][2] = matrix[2][0] = 0.3
        matrix[1][3] = matrix[3][1] = 0.8
        matrix[2][3] = matrix[3][2] = 0.2
        
        # Normalize
        normalized = normalize_matrix(matrix, method="minmax")
        
        # Get stats
        stats = get_matrix_stats(normalized)
        assert stats["total_pairs"] == 6
        
        # Filter
        filtered = filter_matrix_by_threshold(normalized, threshold=0.5)
        
        # Find clusters
        clusters = find_clusters_in_matrix(filtered, threshold=0.7)
        assert len(clusters) >= 1
        
        # Convert format
        df = convert_matrix_format(filtered, "dataframe", 
                                 labels=['A', 'B', 'C', 'D'])
        assert isinstance(df, pd.DataFrame)

    def test_matrix_utilities_consistency(self) -> None:
        """Test consistency across different matrix types."""
        # Create identical matrices in different formats
        list_matrix = [[1.0, 0.7, 0.3], [0.7, 1.0, 0.5], [0.3, 0.5, 1.0]]
        numpy_matrix = np.array(list_matrix)
        df_matrix = pd.DataFrame(list_matrix)
        
        # Get stats should be identical
        list_stats = get_matrix_stats(list_matrix)
        numpy_stats = get_matrix_stats(numpy_matrix)
        df_stats = get_matrix_stats(df_matrix)
        
        assert list_stats["mean"] == numpy_stats["mean"]
        assert numpy_stats["mean"] == df_stats["mean"]
        
        # Find clusters should be identical
        list_clusters = find_clusters_in_matrix(list_matrix, threshold=0.6)
        numpy_clusters = find_clusters_in_matrix(numpy_matrix, threshold=0.6)
        df_clusters = find_clusters_in_matrix(df_matrix, threshold=0.6)
        
        assert list_clusters == numpy_clusters
        assert numpy_clusters == df_clusters


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_large_matrix(self) -> None:
        """Test utilities with very large matrix."""
        # Create 100x100 matrix
        matrix = create_empty_matrix(100, fill_value=0.5)
        
        # Should handle large matrices efficiently
        stats = get_matrix_stats(matrix)
        assert stats["size"] == 100
        assert stats["total_pairs"] == 4950  # 100*99/2

    def test_matrix_with_nan_values(self) -> None:
        """Test handling of NaN values."""
        matrix = [[1.0, float('nan')], [float('nan'), 1.0]]
        
        # normalize_matrix should handle NaN
        with pytest.raises(ValidationError):
            normalize_matrix(matrix, method="minmax")

    def test_matrix_with_inf_values(self) -> None:
        """Test handling of infinite values."""
        matrix = [[1.0, float('inf')], [float('inf'), 1.0]]
        
        # Should raise validation error
        with pytest.raises(ValidationError):
            get_matrix_stats(matrix)

    def test_unicode_labels(self) -> None:
        """Test DataFrame conversion with Unicode labels."""
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        labels = ['测试A', 'テストB']
        
        df = convert_matrix_format(matrix, "dataframe", labels=labels)
        
        assert list(df.index) == labels
        assert list(df.columns) == labels

    def test_empty_cluster_edge_case(self) -> None:
        """Test clustering when all similarities are below threshold."""
        matrix = [[1.0, 0.1, 0.1], [0.1, 1.0, 0.1], [0.1, 0.1, 1.0]]
        
        clusters = find_clusters_in_matrix(matrix, threshold=0.9)
        
        assert clusters == []  # No clusters above threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])