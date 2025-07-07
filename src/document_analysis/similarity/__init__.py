"""Similarity analysis module.

Provides unified interface for different similarity calculation techniques:
- String-based similarity using fuzzy matching
- Semantic similarity using embeddings

This module follows the Interface Segregation Principle by providing
specialized interfaces for different similarity techniques while maintaining
a common base interface.
"""

from .base import SimilarityCalculator, SimilarityMatrix, SimilarityResult
from .matrix_utils import create_empty_matrix, find_clusters_in_matrix, normalize_matrix
from .semantic_similarity import SemanticSimilarityCalculator
from .string_similarity import StringSimilarityCalculator

__all__ = [
    # Base interfaces
    "SimilarityCalculator",
    "SimilarityMatrix",
    "SimilarityResult",
    # Implementations
    "StringSimilarityCalculator",
    "SemanticSimilarityCalculator",
    # Utilities
    "create_empty_matrix",
    "find_clusters_in_matrix",
    "normalize_matrix",
]
