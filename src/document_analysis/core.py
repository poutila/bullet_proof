#!/usr/bin/env python3
"""Core text matching algorithms and utilities.

This module provides text comparison, fuzzy matching, and similarity analysis
functions following CLAUDE.md security and quality standards.
"""

import logging
import re
from difflib import SequenceMatcher

from rapidfuzz import fuzz

from src.document_analysis.config import (
    DUPLICATE_THRESHOLD,
    MIN_CONTENT_LENGTH,
    SIMILARITY_THRESHOLD_HIGH,
    SIMILARITY_THRESHOLD_LOW,
)
from src.validation.validation import ValidationError, validate_string_input, validate_threshold

logger = logging.getLogger(__name__)


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

    except Exception as e:
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


def get_similarity_matrix(texts: list[str], threshold: float | None = None) -> list[list[float]]:
    """Calculate pairwise similarity matrix for a list of texts.

    Creates a symmetric matrix of similarity scores between all pairs of texts,
    only including scores that meet the threshold requirement.

    Args:
        texts: List of text documents
        threshold: Minimum similarity to include in results (defaults to SIMILARITY_THRESHOLD_LOW)

    Returns:
        Square matrix of similarity scores

    Raises:
        ValidationError: If input validation fails
        ValueError: If texts list is empty

    Example:
        >>> matrix = get_similarity_matrix(["hello", "hello world", "goodbye"])
        >>> len(matrix) == 3
        True
    """
    if not texts:
        raise ValueError("Text list cannot be empty")

    # Validate threshold
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_LOW
    else:
        try:
            threshold = validate_threshold(threshold, "similarity_threshold")
        except ValidationError as e:
            logger.error(f"Invalid threshold: {e}")
            raise

    # Validate all texts
    validated_texts: list[str] = []
    for i, text in enumerate(texts):
        try:
            validated = validate_string_input(text, f"text[{i}]", max_length=100_000)
            validated_texts.append(validated)
        except ValidationError as e:
            logger.error(f"Invalid text at index {i}: {e}")
            raise

    n = len(validated_texts)
    matrix: list[list[float]] = [[0.0 for _ in range(n)] for _ in range(n)]

    # Calculate pairwise similarities
    for i in range(n):
        # Diagonal is always 1.0 (self-similarity)
        matrix[i][i] = 1.0

        for j in range(i + 1, n):
            try:
                # Calculate semantic similarity
                score = fuzz.token_set_ratio(validated_texts[i], validated_texts[j]) / 100.0

                # Only store if above threshold
                if score >= threshold:
                    matrix[i][j] = score
                    matrix[j][i] = score  # Symmetric matrix

            except Exception as e:
                logger.warning(f"Error calculating similarity for texts {i} and {j}: {e}")
                # Leave as 0.0 on error

    logger.info(f"Generated {n}x{n} similarity matrix with threshold {threshold:.2f}")

    return matrix


def find_duplicate_groups(similarity_matrix: list[list[float]], threshold: float | None = None) -> list[list[int]]:
    """Find groups of highly similar documents from similarity matrix.

    Uses a greedy clustering approach to identify groups of documents
    with similarity scores above the threshold.

    Args:
        similarity_matrix: Square similarity matrix
        threshold: Minimum similarity to consider as duplicates (defaults to SIMILARITY_THRESHOLD_HIGH)

    Returns:
        List of document index groups that are similar

    Raises:
        ValidationError: If threshold validation fails
        ValueError: If matrix is invalid

    Example:
        >>> matrix = [[1.0, 0.95], [0.95, 1.0]]
        >>> groups = find_duplicate_groups(matrix, threshold=0.9)
        >>> len(groups) == 1
        True
    """
    if not similarity_matrix:
        raise ValueError("Similarity matrix cannot be empty")

    n = len(similarity_matrix)

    # Validate matrix is square
    for i, row in enumerate(similarity_matrix):
        if len(row) != n:
            raise ValueError(f"Matrix must be square. Row {i} has {len(row)} elements, expected {n}")

    # Validate threshold
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD_HIGH
    else:
        try:
            threshold = validate_threshold(threshold, "duplicate_threshold")
        except ValidationError as e:
            logger.error(f"Invalid threshold: {e}")
            raise

    visited: list[bool] = [False] * n
    groups: list[list[int]] = []

    for i in range(n):
        if visited[i]:
            continue

        # Start a new group with document i
        group: list[int] = [i]
        visited[i] = True

        # Find all documents similar to document i
        for j in range(i + 1, n):
            if not visited[j] and similarity_matrix[i][j] >= threshold:
                group.append(j)
                visited[j] = True

        # Only include groups with multiple documents
        if len(group) > 1:
            groups.append(group)
            logger.debug(f"Found duplicate group with {len(group)} documents: {group[:5]}...")

    logger.info(f"Found {len(groups)} duplicate groups with threshold {threshold:.2f}")

    return groups
