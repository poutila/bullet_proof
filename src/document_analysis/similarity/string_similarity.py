"""String-based similarity calculation using fuzzy matching.

This module implements similarity calculation using rapidfuzz library
for fast string-based similarity analysis.
"""

import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from ..analyzers import load_markdown_files
from ..config import (
    DUPLICATE_THRESHOLD,
    MIN_CONTENT_LENGTH,
    SIMILARITY_THRESHOLD_HIGH,
    SIMILARITY_THRESHOLD_LOW,
)
from ..validation import ValidationError, validate_file_path, validate_string_input, validate_threshold

from .base import BaseSimilarityCalculator, ClusteringMixin, SimilarityResult

logger = logging.getLogger(__name__)


class StringSimilarityCalculator(BaseSimilarityCalculator, ClusteringMixin):
    """String-based similarity calculator using fuzzy matching.

    Uses rapidfuzz.fuzz.token_set_ratio for calculating string similarity
    based on tokenized text comparison.
    """

    def __init__(self, algorithm: str = "token_set_ratio", **kwargs: Any) -> None:
        """Initialize string similarity calculator.

        Args:
            algorithm: Fuzzy matching algorithm to use
            **kwargs: Additional configuration parameters
        """
        super().__init__("StringSimilarity", algorithm=algorithm, **kwargs)
        self.algorithm = algorithm

        # Validate algorithm choice
        if algorithm not in ["ratio", "partial_ratio", "token_sort_ratio", "token_set_ratio"]:
            raise ValidationError(f"Unsupported algorithm: {algorithm}")

        self._fuzz_func = getattr(fuzz, algorithm)
        logger.debug(f"Using rapidfuzz.{algorithm} for string similarity")

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using fuzzy matching.

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # rapidfuzz returns score 0-100, normalize to 0-1
            score = self._fuzz_func(text1, text2) / 100.0
            return float(score)
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(f"Fuzzy matching failed: {e}")
            return 0.0

    def find_similar_documents(
        self, query_docs: list[Path], candidate_docs: list[Path], root_dir: Path, threshold: float = 0.5
    ) -> list[SimilarityResult]:
        """Find documents similar to query documents using string matching.

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
        # Validate inputs
        if not query_docs:
            raise ValidationError("Query documents list cannot be empty")
        if not candidate_docs:
            raise ValidationError("Candidate documents list cannot be empty")

        try:
            root_dir = validate_file_path(root_dir, must_exist=True)
        except ValidationError as e:
            raise ValidationError(f"Invalid root directory: {e}") from e

        if not 0.0 <= threshold <= 1.0:
            raise ValidationError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        # Load documents
        try:
            query_files = load_markdown_files(query_docs, root_dir)
            candidate_files = load_markdown_files(candidate_docs, root_dir)
        except (OSError, ValueError) as e:
            logger.error(f"Failed to load documents: {e}")
            raise FileNotFoundError("Could not load documents") from e

        results = []

        # Compare each query document against all candidates
        for query_path, query_content in query_files.items():
            for candidate_path, candidate_content in candidate_files.items():
                # Skip self-comparison
                if query_path == candidate_path:
                    continue

                try:
                    score = self._calculate_similarity(query_content, candidate_content)

                    if score >= threshold:
                        result = SimilarityResult(
                            source=query_path,
                            target=candidate_path,
                            score=score,
                            technique="string_fuzzy",
                            metadata={
                                "algorithm": self.algorithm,
                                "query_length": len(query_content),
                                "candidate_length": len(candidate_content),
                            },
                        )
                        results.append(result)

                except (AttributeError, TypeError, ValueError) as e:
                    logger.warning(f"Failed to compare {query_path} vs {candidate_path}: {e}")
                    continue

        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(results)} similar document pairs above threshold {threshold}")
        return results


def get_similarity_matrix(texts: list[str], threshold: float | None = None) -> list[list[float]]:
    """Calculate pairwise similarity matrix for a list of texts.

    Legacy function for backward compatibility. Consider using
    StringSimilarityCalculator.calculate_matrix() instead.

    Args:
        texts: List of text documents
        threshold: Minimum similarity to include in results

    Returns:
        Square matrix of similarity scores

    Raises:
        ValidationError: If input validation fails
        ValueError: If texts list is empty
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_LOW

    calculator = StringSimilarityCalculator()
    matrix = calculator.calculate_matrix(texts, threshold)

    # Convert to list format if needed
    if isinstance(matrix, list):
        return matrix
    if isinstance(matrix, pd.DataFrame):
        df_result: list[list[float]] = matrix.values.tolist()
        return df_result
    # numpy array
    np_result: list[list[float]] = matrix.tolist()
    return np_result


def find_duplicate_groups(similarity_matrix: list[list[float]], threshold: float | None = None) -> list[list[int]]:
    """Find groups of highly similar documents from similarity matrix.

    Legacy function for backward compatibility. Consider using
    StringSimilarityCalculator with ClusteringMixin instead.

    Args:
        similarity_matrix: Square similarity matrix
        threshold: Minimum similarity to consider as duplicates

    Returns:
        List of document index groups that are similar

    Raises:
        ValidationError: If threshold validation fails
        ValueError: If matrix is invalid
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_HIGH

    # Validate threshold
    try:
        threshold = validate_threshold(threshold, "duplicate_threshold")
    except ValidationError as e:
        logger.error(f"Invalid threshold: {e}")
        raise

    # Validate matrix
    if not similarity_matrix:
        raise ValueError("Similarity matrix cannot be empty")

    n = len(similarity_matrix)
    if not all(len(row) == n for row in similarity_matrix):
        raise ValueError("Similarity matrix must be square")

    # Use clustering mixin functionality
    calculator = StringSimilarityCalculator()
    return calculator.find_clusters(similarity_matrix, threshold)


def find_best_match(section: str, targets: list[str], threshold: float | None = None) -> tuple[str | None, float]:
    """Find best matching target for a given section.

    Args:
        section: Text section to find matches for
        targets: List of target texts to compare against
        threshold: Minimum similarity threshold

    Returns:
        Tuple of (best_match_text, similarity_score) or (None, 0.0) if no match above threshold

    Raises:
        ValidationError: If input validation fails
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_LOW

    # Validate inputs
    try:
        section = validate_string_input(section, "section", max_length=100_000)
        threshold = validate_threshold(threshold, "match_threshold")
    except ValidationError as e:
        logger.error(f"Input validation failed: {e}")
        raise

    if not targets:
        logger.debug("No targets provided for matching")
        return None, 0.0

    calculator = StringSimilarityCalculator()
    best_match = None
    best_score = 0.0

    for i, target in enumerate(targets):
        try:
            validated_target = validate_string_input(target, f"target[{i}]", max_length=100_000)
            score = calculator._calculate_similarity(section, validated_target)

            if score > best_score and score >= threshold:
                best_match = validated_target
                best_score = score

        except ValidationError as e:
            logger.warning(f"Skipping invalid target at index {i}: {e}")
            continue

    logger.debug(f"Best match found with score {best_score:.3f} for section of length {len(section)}")
    return best_match, best_score


def split_sections(text: str, min_len: int | None = None) -> list[str]:
    r"""Split markdown text into sections by paragraph.

    Splits text on double newlines and filters out sections shorter than
    the minimum length requirement.

    Args:
        text: Text to split into sections
        min_len: Minimum section length to include (defaults to MIN_CONTENT_LENGTH)

    Returns:
        List of text sections meeting minimum length requirement

    Raises:
        ValidationError: If text validation fails

    Example:
        >>> sections = split_sections("Hello\n\nWorld\n\nShort", min_len=5)
        >>> len(sections)
        2
    """
    # Validate input
    try:
        validated_text = validate_string_input(
            text,
            "text",
            max_length=1_000_000,  # 1MB text limit
        )
    except ValidationError as e:
        logger.error(f"Invalid text input: {e}")
        raise

    # Set default minimum length
    if min_len is None:
        min_len = MIN_CONTENT_LENGTH
    elif min_len < 0:
        raise ValidationError(f"Minimum length must be non-negative: {min_len}")

    # Split by double newlines
    sections = re.split(r"\n\s*\n", validated_text)

    # Filter and clean sections
    valid_sections: list[str] = []
    for section in sections:
        cleaned = section.strip()
        if len(cleaned) >= min_len:
            valid_sections.append(cleaned)

    logger.debug(f"Split text into {len(valid_sections)} sections")
    return valid_sections


def is_similar(a: str, b: str, threshold: int | None = None) -> bool:
    """Check if two text blocks are semantically similar using fuzzy matching.

    Uses token-based fuzzy matching to determine semantic similarity,
    checking both token set ratio and token sort ratio.

    Args:
        a: First text block
        b: Second text block
        threshold: Similarity threshold (0-100, defaults to DUPLICATE_THRESHOLD)

    Returns:
        True if texts are similar above threshold

    Raises:
        ValidationError: If input validation fails

    Example:
        >>> is_similar("Hello world", "world Hello", threshold=80)
        True
    """
    # Validate inputs
    try:
        validated_a = validate_string_input(a, "text_a", max_length=100_000)
        validated_b = validate_string_input(b, "text_b", max_length=100_000)
    except ValidationError as e:
        logger.error(f"Text validation failed: {e}")
        raise

    # Set default threshold
    if threshold is None:
        threshold = DUPLICATE_THRESHOLD
    elif not 0 <= threshold <= 100:
        raise ValidationError(f"Threshold must be between 0 and 100: {threshold}")

    try:
        # Calculate similarity using both token methods
        token_set_score = fuzz.token_set_ratio(validated_a, validated_b)
        token_sort_score = fuzz.token_sort_ratio(validated_a, validated_b)

        # Return true if either method exceeds threshold
        result = bool(token_set_score >= threshold or token_sort_score >= threshold)

        logger.debug(
            f"Similarity check - set: {token_set_score}, sort: {token_sort_score}, threshold: {threshold}, result: {result}"
        )

        return result

    except (AttributeError, TypeError, ValueError) as e:
        logger.error(f"Error calculating similarity: {e}")
        raise


def get_best_match_seq(section: str, targets: list[str]) -> tuple[str, float]:
    """Get best match using SequenceMatcher for debugging fallback matching.

    This provides character-level similarity comparison as a fallback
    to catch similarities that token-based fuzzy matching might miss.

    Args:
        section: Source section to match
        targets: List of target sections to compare against

    Returns:
        Tuple of (best_match_text, similarity_ratio)

    Raises:
        ValidationError: If input validation fails
        ValueError: If targets list is empty

    Example:
        >>> match, score = get_best_match_seq("hello", ["hello world", "hi"])
        >>> score > 0.5
        True
    """
    # Validate inputs
    try:
        validated_section = validate_string_input(section, "section", max_length=100_000)
    except ValidationError as e:
        logger.error(f"Invalid section: {e}")
        raise

    if not targets:
        raise ValueError("Targets list cannot be empty")

    best_match: str = ""
    best_score: float = 0.0

    for i, target in enumerate(targets):
        try:
            # Validate each target
            validated_target = validate_string_input(target, f"target[{i}]", max_length=100_000)

            # Calculate similarity ratio
            matcher = SequenceMatcher(None, validated_section, validated_target)
            score = matcher.ratio()

            if score > best_score:
                best_score = score
                best_match = validated_target

        except ValidationError as e:
            logger.warning(f"Skipping invalid target at index {i}: {e}")
            continue

    logger.debug(f"Best match found with score {best_score:.3f} for section of length {len(section)}")

    return best_match, best_score
