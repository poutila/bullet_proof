"""Common matrix utilities for similarity calculations.

This module provides shared utilities for working with similarity matrices
across different similarity calculation techniques.
"""

import logging
from typing import Any, TypeAlias

import numpy as np
import pandas as pd

from document_analysis.validation import ValidationError

logger = logging.getLogger(__name__)

# Type alias for matrix types
MatrixType: TypeAlias = list[list[float]] | np.ndarray | pd.DataFrame


def create_empty_matrix(size: int, fill_value: float = 0.0) -> list[list[float]]:
    """Create an empty similarity matrix of given size.

    Args:
        size: Size of the square matrix
        fill_value: Value to fill the matrix with

    Returns:
        Square matrix filled with fill_value

    Raises:
        ValidationError: If size is invalid

    Example:
        >>> matrix = create_empty_matrix(3, 0.0)
        >>> len(matrix) == 3 and len(matrix[0]) == 3
        True
    """
    if not isinstance(size, int) or size <= 0:
        raise ValidationError(f"Matrix size must be positive integer, got {size}")

    if not isinstance(fill_value, (int, float)):
        raise ValidationError(f"Fill value must be numeric, got {type(fill_value)}")

    matrix = [[fill_value for _ in range(size)] for _ in range(size)]

    # Set diagonal to 1.0 for similarity matrices (self-similarity)
    if fill_value != 1.0:
        for i in range(size):
            matrix[i][i] = 1.0

    logger.debug(f"Created {size}x{size} matrix with fill_value={fill_value}")
    return matrix


def normalize_matrix(matrix: MatrixType, method: str = "minmax") -> MatrixType:
    """Normalize similarity matrix using specified method.

    Args:
        matrix: Input similarity matrix
        method: Normalization method ('minmax', 'zscore', 'none')

    Returns:
        Normalized matrix of same type as input

    Raises:
        ValidationError: If matrix or method is invalid

    Example:
        >>> matrix = [[1.0, 0.5], [0.5, 1.0]]
        >>> normalized = normalize_matrix(matrix, 'minmax')
        >>> isinstance(normalized, list)
        True
    """
    if method not in ["minmax", "zscore", "none"]:
        raise ValidationError(f"Unsupported normalization method: {method}")

    if method == "none":
        return matrix

    # Validate and convert matrix
    if isinstance(matrix, list):
        # Convert to numpy for processing
        try:
            np_matrix = np.array(matrix, dtype=float)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid matrix format: {e}") from e

        if np_matrix.ndim != 2 or np_matrix.shape[0] != np_matrix.shape[1]:
            raise ValidationError("Matrix must be square 2D array")

    elif isinstance(matrix, pd.DataFrame):
        if matrix.shape[0] != matrix.shape[1]:
            raise ValidationError("DataFrame must be square")
        np_matrix = matrix.values

    elif isinstance(matrix, np.ndarray):
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValidationError("Array must be square 2D array")
        np_matrix = matrix

    else:
        raise ValidationError(f"Unsupported matrix type: {type(matrix)}")

    # Apply normalization
    if method == "minmax":
        # Min-max normalization: (x - min) / (max - min)
        min_val = np_matrix.min()
        max_val = np_matrix.max()

        if max_val == min_val:
            logger.warning("Matrix has constant values, cannot normalize")
            normalized = np_matrix
        else:
            normalized = (np_matrix - min_val) / (max_val - min_val)

    elif method == "zscore":
        # Z-score normalization: (x - mean) / std
        mean_val = np_matrix.mean()
        std_val = np_matrix.std()

        if std_val == 0:
            logger.warning("Matrix has zero standard deviation, cannot normalize")
            normalized = np_matrix
        else:
            normalized = (np_matrix - mean_val) / std_val

    # Convert back to original type
    if isinstance(matrix, list):
        return normalized.tolist()
    if isinstance(matrix, pd.DataFrame):
        return pd.DataFrame(normalized, index=matrix.index, columns=matrix.columns)
    return normalized


def find_clusters_in_matrix(matrix: MatrixType, threshold: float = 0.7) -> list[list[int]]:
    """Find clusters of similar items in similarity matrix.

    Uses a simple greedy clustering algorithm to group items with
    similarity above the threshold.

    Args:
        matrix: Similarity matrix (square, symmetric)
        threshold: Minimum similarity for clustering

    Returns:
        List of clusters, where each cluster is a list of indices

    Raises:
        ValidationError: If matrix or threshold is invalid

    Example:
        >>> matrix = [[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]]
        >>> clusters = find_clusters_in_matrix(matrix, 0.8)
        >>> len(clusters) >= 1
        True
    """
    # Validate threshold
    if not 0.0 <= threshold <= 1.0:
        raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

    # Validate and get matrix size
    if isinstance(matrix, list):
        n = len(matrix)
        if n == 0 or any(len(row) != n for row in matrix):
            raise ValidationError("Matrix must be square and non-empty")

    elif isinstance(matrix, (np.ndarray, pd.DataFrame)):
        if matrix.shape[0] != matrix.shape[1]:
            raise ValidationError("Matrix must be square")
        n = matrix.shape[0]

    else:
        raise ValidationError(f"Unsupported matrix type: {type(matrix)}")

    if n == 0:
        return []

    # Simple greedy clustering algorithm
    visited = [False] * n
    clusters = []

    for i in range(n):
        if visited[i]:
            continue

        cluster = [i]
        visited[i] = True

        # Find all items similar to item i
        for j in range(i + 1, n):
            if visited[j]:
                continue

            # Get similarity score
            if isinstance(matrix, list):
                score = matrix[i][j]
            elif isinstance(matrix, pd.DataFrame):
                score = matrix.iloc[i, j]
            else:  # numpy array
                score = matrix[i, j]

            if score >= threshold:
                cluster.append(j)
                visited[j] = True

        # Only include clusters with multiple items
        if len(cluster) > 1:
            clusters.append(cluster)

    logger.debug(f"Found {len(clusters)} clusters with threshold {threshold}")
    return clusters


def get_matrix_stats(matrix: MatrixType) -> dict[str, Any]:
    """Get statistical information about similarity matrix.

    Args:
        matrix: Similarity matrix

    Returns:
        Dictionary with matrix statistics

    Raises:
        ValidationError: If matrix is invalid

    Example:
        >>> matrix = [[1.0, 0.5], [0.5, 1.0]]
        >>> stats = get_matrix_stats(matrix)
        >>> 'mean' in stats and 'std' in stats
        True
    """
    # Convert to numpy for consistent processing
    if isinstance(matrix, list):
        try:
            np_matrix = np.array(matrix, dtype=float)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid matrix format: {e}") from e

    elif isinstance(matrix, pd.DataFrame):
        np_matrix = matrix.values

    elif isinstance(matrix, np.ndarray):
        np_matrix = matrix

    else:
        raise ValidationError(f"Unsupported matrix type: {type(matrix)}")

    if np_matrix.ndim != 2:
        raise ValidationError("Matrix must be 2D")

    # Calculate statistics (excluding diagonal)
    n = np_matrix.shape[0]
    if n != np_matrix.shape[1]:
        raise ValidationError("Matrix must be square")

    # Get upper triangle (excluding diagonal) for symmetric matrices
    upper_triangle = np_matrix[np.triu_indices(n, k=1)]

    if len(upper_triangle) == 0:
        # Single item matrix
        stats = {"size": n, "total_pairs": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}
    else:
        stats = {
            "size": n,
            "total_pairs": len(upper_triangle),
            "mean": float(np.mean(upper_triangle)),
            "std": float(np.std(upper_triangle)),
            "min": float(np.min(upper_triangle)),
            "max": float(np.max(upper_triangle)),
            "median": float(np.median(upper_triangle)),
        }

    # Add distribution information
    if len(upper_triangle) > 0:
        stats["percentile_25"] = float(np.percentile(upper_triangle, 25))
        stats["percentile_75"] = float(np.percentile(upper_triangle, 75))

        # Count values in different ranges
        stats["high_similarity"] = int(np.sum(upper_triangle >= 0.8))
        stats["medium_similarity"] = int(np.sum((upper_triangle >= 0.5) & (upper_triangle < 0.8)))
        stats["low_similarity"] = int(np.sum(upper_triangle < 0.5))
    else:
        stats["percentile_25"] = 0.0
        stats["percentile_75"] = 0.0
        stats["high_similarity"] = 0
        stats["medium_similarity"] = 0
        stats["low_similarity"] = 0

    logger.debug(f"Matrix stats: {stats['total_pairs']} pairs, mean={stats['mean']:.3f}")
    return stats


def filter_matrix_by_threshold(matrix: MatrixType, threshold: float) -> MatrixType:
    """Filter similarity matrix by setting values below threshold to 0.

    Args:
        matrix: Input similarity matrix
        threshold: Minimum value to keep

    Returns:
        Filtered matrix of same type as input

    Raises:
        ValidationError: If threshold is invalid

    Example:
        >>> matrix = [[1.0, 0.3], [0.3, 1.0]]
        >>> filtered = filter_matrix_by_threshold(matrix, 0.5)
        >>> filtered[0][1] == 0.0
        True
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

    if isinstance(matrix, list):
        filtered: list[list[float]] = []
        for row in matrix:
            filtered_row = [val if val >= threshold else 0.0 for val in row]
            filtered.append(filtered_row)
        # Preserve diagonal
        n = len(filtered)
        for i in range(n):
            filtered[i][i] = 1.0
        return filtered

    if isinstance(matrix, pd.DataFrame):
        filtered_df = matrix.copy()
        filtered_df[filtered_df < threshold] = 0.0
        # Preserve diagonal
        for i in range(len(filtered_df)):
            filtered_df.iloc[i, i] = 1.0
        return filtered_df

    if isinstance(matrix, np.ndarray):
        filtered_arr = matrix.copy()
        filtered_arr[filtered_arr < threshold] = 0.0
        # Preserve diagonal
        np.fill_diagonal(filtered_arr, 1.0)
        return filtered_arr

    raise ValidationError(f"Unsupported matrix type: {type(matrix)}")


def convert_matrix_format(matrix: MatrixType, target_format: str, labels: list[str] | None = None) -> MatrixType:
    """Convert similarity matrix between different formats.

    Args:
        matrix: Input matrix
        target_format: Target format ('list', 'numpy', 'dataframe')
        labels: Labels for DataFrame format (optional)

    Returns:
        Matrix in target format

    Raises:
        ValidationError: If format is invalid

    Example:
        >>> matrix = [[1.0, 0.5], [0.5, 1.0]]
        >>> df = convert_matrix_format(matrix, 'dataframe', ['A', 'B'])
        >>> isinstance(df, pd.DataFrame)
        True
    """
    if target_format not in ["list", "numpy", "dataframe"]:
        raise ValidationError(f"Unsupported target format: {target_format}")

    # Convert input to numpy first
    if isinstance(matrix, list):
        np_matrix = np.array(matrix, dtype=float)
    elif isinstance(matrix, pd.DataFrame):
        np_matrix = matrix.values
    elif isinstance(matrix, np.ndarray):
        np_matrix = matrix
    else:
        raise ValidationError(f"Unsupported input matrix type: {type(matrix)}")

    # Convert to target format
    if target_format == "list":
        return np_matrix.tolist()

    if target_format == "numpy":
        return np_matrix

    if target_format == "dataframe":
        if labels is None:
            labels = [f"item_{i}" for i in range(np_matrix.shape[0])]
        elif len(labels) != np_matrix.shape[0]:
            raise ValidationError(f"Labels length {len(labels)} doesn't match matrix size {np_matrix.shape[0]}")

        return pd.DataFrame(np_matrix, index=labels, columns=labels)

    # Should not reach here due to validation above
    raise ValidationError(f"Unknown target format: {target_format}")
