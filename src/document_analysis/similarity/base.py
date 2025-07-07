"""Base interfaces for similarity calculation.

This module defines the abstract interfaces that all similarity calculators
must implement, following the Dependency Inversion Principle from CLAUDE.md.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Union

import numpy as np
import pandas as pd

from ..validation import ValidationError

logger = logging.getLogger(__name__)

# Type aliases for better readability
SimilarityMatrix = Union[list[list[float]], np.ndarray, pd.DataFrame]
TextList = list[str]
PathList = list[Path]


@dataclass
class SimilarityResult:
    """Result of similarity calculation between documents.

    Attributes:
        source: Source document identifier
        target: Target document identifier
        score: Similarity score (0.0 to 1.0)
        technique: Similarity calculation technique used
        metadata: Additional information about the calculation
    """

    source: str
    target: str
    score: float
    technique: str
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Validate similarity result after initialization."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {self.score}")
        if self.metadata is None:
            self.metadata = {}


class SimilarityCalculator(Protocol):
    """Protocol defining the interface for similarity calculators.

    This follows the Interface Segregation Principle by defining
    minimal, focused interface that clients can depend on.
    """

    def calculate_pairwise(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0

        Raises:
            ValidationError: If input validation fails
        """
        ...

    def calculate_matrix(self, texts: TextList, threshold: float = 0.0) -> SimilarityMatrix:
        """Calculate pairwise similarity matrix for list of texts.

        Args:
            texts: List of texts to compare
            threshold: Minimum similarity score to include in results

        Returns:
            Similarity matrix with scores >= threshold

        Raises:
            ValidationError: If input validation fails
            ValueError: If texts list is empty
        """
        ...

    def find_similar_documents(
        self, query_docs: PathList, candidate_docs: PathList, root_dir: Path, threshold: float = 0.5
    ) -> list[SimilarityResult]:
        """Find documents similar to query documents.

        Args:
            query_docs: Documents to find similarities for
            candidate_docs: Documents to search within
            root_dir: Root directory for file loading
            threshold: Minimum similarity score to include

        Returns:
            List of similarity results above threshold

        Raises:
            ValidationError: If input validation fails
            FileNotFoundError: If documents cannot be loaded
        """
        ...


class BaseSimilarityCalculator(ABC):
    """Abstract base class for similarity calculators.

    Provides common functionality and enforces the template method pattern
    for similarity calculation implementations.
    """

    def __init__(self, name: str, **kwargs: Any) -> None:
        """Initialize base similarity calculator.

        Args:
            name: Name of the similarity technique
            **kwargs: Additional configuration parameters
        """
        self.name = name
        self.config = kwargs
        logger.debug(f"Initialized {name} similarity calculator")

    @abstractmethod
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (implementation-specific).

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """

    def calculate_pairwise(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts with validation.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0

        Raises:
            ValidationError: If input validation fails
        """
        # Validate inputs
        self._validate_text_input(text1, "text1")
        self._validate_text_input(text2, "text2")

        try:
            score = self._calculate_similarity(text1, text2)
            return max(0.0, min(1.0, score))  # Clamp to [0.0, 1.0]
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            raise ValidationError(f"Failed to calculate similarity: {e}") from e

    def calculate_matrix(self, texts: TextList, threshold: float = 0.0) -> SimilarityMatrix:
        """Calculate pairwise similarity matrix for list of texts.

        Args:
            texts: List of texts to compare
            threshold: Minimum similarity score to include in results

        Returns:
            Similarity matrix with scores >= threshold

        Raises:
            ValidationError: If input validation fails
            ValueError: If texts list is empty
        """
        # Validate inputs
        if not texts:
            raise ValueError("Text list cannot be empty")

        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        for i, text in enumerate(texts):
            self._validate_text_input(text, f"texts[{i}]")

        n = len(texts)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        # Calculate pairwise similarities
        for i in range(n):
            matrix[i][i] = 1.0  # Self-similarity is always 1.0

            for j in range(i + 1, n):
                try:
                    score = self._calculate_similarity(texts[i], texts[j])
                    if score >= threshold:
                        matrix[i][j] = score
                        matrix[j][i] = score  # Symmetric matrix
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity for texts {i}, {j}: {e}")
                    continue

        return matrix

    def _validate_text_input(self, text: str, param_name: str) -> None:
        """Validate text input parameter.

        Args:
            text: Text to validate
            param_name: Parameter name for error messages

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(text, str):
            raise ValidationError(f"{param_name} must be a string, got {type(text)}")

        if len(text.strip()) == 0:
            raise ValidationError(f"{param_name} cannot be empty or whitespace-only")

        if len(text) > 100_000:  # Reasonable limit
            raise ValidationError(f"{param_name} too long: {len(text)} characters (max 100,000)")


class ClusteringMixin:
    """Mixin providing clustering functionality for similarity matrices."""

    def find_clusters(self, matrix: SimilarityMatrix, threshold: float = 0.7) -> list[list[int]]:
        """Find clusters of similar items in similarity matrix.

        Args:
            matrix: Similarity matrix (square, symmetric)
            threshold: Minimum similarity for clustering

        Returns:
            List of clusters, where each cluster is a list of indices

        Raises:
            ValidationError: If matrix validation fails
        """
        # Validate matrix
        if isinstance(matrix, list):
            n = len(matrix)
            if n == 0 or len(matrix[0]) != n:
                raise ValidationError("Matrix must be square and non-empty")
        elif isinstance(matrix, (np.ndarray, pd.DataFrame)):
            if matrix.shape[0] != matrix.shape[1]:
                raise ValidationError("Matrix must be square")
            n = matrix.shape[0]
        else:
            raise ValidationError(f"Unsupported matrix type: {type(matrix)}")

        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        # Simple clustering: group items with similarity >= threshold
        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            cluster = [i]
            visited[i] = True

            for j in range(i + 1, n):
                if visited[j]:
                    continue

                # Get similarity score
                if isinstance(matrix, list):
                    score = matrix[i][j]
                else:
                    score = matrix.iloc[i, j] if isinstance(matrix, pd.DataFrame) else matrix[i, j]

                if score >= threshold:
                    cluster.append(j)
                    visited[j] = True

            if len(cluster) > 1:  # Only include clusters with multiple items
                clusters.append(cluster)

        logger.debug(f"Found {len(clusters)} clusters with threshold {threshold}")
        return clusters
