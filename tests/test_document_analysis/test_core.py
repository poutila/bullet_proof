#!/usr/bin/env python3
"""Test suite for core text matching algorithms.

Tests all functions in core.py including edge cases, error handling,
and performance considerations according to CLAUDE.md standards.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_analysis.core import (
    find_duplicate_groups,
    get_best_match_seq,
    get_similarity_matrix,
    is_similar,
    split_sections,
)
from src.validation.validation import ValidationError


class TestSplitSections:
    """Test cases for split_sections function."""

    def test_split_sections_basic(self) -> None:
        """Test basic section splitting functionality."""
        text = "First section\n\nSecond section\n\nThird section"
        sections = split_sections(text)

        assert len(sections) == 3
        assert sections[0] == "First section"
        assert sections[1] == "Second section"
        assert sections[2] == "Third section"

    def test_split_sections_with_min_length(self) -> None:
        """Test section filtering by minimum length."""
        text = "Long section here\n\nShort\n\nAnother long section"
        sections = split_sections(text, min_len=10)

        assert len(sections) == 2
        assert "Short" not in sections
        assert "Long section here" in sections
        assert "Another long section" in sections

    def test_split_sections_empty_text(self) -> None:
        """Test handling of empty text input."""
        with pytest.raises(ValidationError, match="empty"):
            split_sections("")

    def test_split_sections_whitespace_only(self) -> None:
        """Test handling of whitespace-only input."""
        with pytest.raises(ValidationError, match="empty"):
            split_sections("   \n  \n  ")

    def test_split_sections_single_section(self) -> None:
        """Test text with no section breaks."""
        text = "This is a single long section without any breaks"
        sections = split_sections(text)

        assert len(sections) == 1
        assert sections[0] == text

    def test_split_sections_multiple_newlines(self) -> None:
        """Test handling of multiple consecutive newlines."""
        text = "First\n\n\n\nSecond\n\n\n\n\nThird"
        sections = split_sections(text)

        assert len(sections) == 3
        assert sections[0] == "First"
        assert sections[1] == "Second"
        assert sections[2] == "Third"

    def test_split_sections_negative_min_length(self) -> None:
        """Test that negative min_length raises error."""
        with pytest.raises(ValidationError, match="non-negative"):
            split_sections("test", min_len=-1)

    def test_split_sections_very_long_text(self) -> None:
        """Test handling of very long text input."""
        # Test within allowed limit
        long_text = "Section " + "x" * 100_000
        sections = split_sections(long_text)
        assert len(sections) == 1

        # Test exceeding limit
        too_long = "x" * 1_000_001
        with pytest.raises(ValidationError):
            split_sections(too_long)


class TestIsSimilar:
    """Test cases for is_similar function."""

    def test_is_similar_identical_text(self) -> None:
        """Test that identical texts are similar."""
        text = "This is a test sentence"
        assert is_similar(text, text) is True

    def test_is_similar_different_order(self) -> None:
        """Test token-based similarity ignores order."""
        text1 = "hello world python"
        text2 = "python world hello"
        assert is_similar(text1, text2, threshold=80) is True

    def test_is_similar_partial_overlap(self) -> None:
        """Test partial text overlap detection."""
        text1 = "The quick brown fox jumps"
        text2 = "The quick brown fox runs"
        assert is_similar(text1, text2, threshold=75) is True

    def test_is_similar_completely_different(self) -> None:
        """Test completely different texts are not similar."""
        text1 = "Apple orange banana"
        text2 = "Car truck motorcycle"
        assert is_similar(text1, text2, threshold=85) is False

    def test_is_similar_empty_text_validation(self) -> None:
        """Test that empty texts raise validation error."""
        with pytest.raises(ValidationError):
            is_similar("", "test")

        with pytest.raises(ValidationError):
            is_similar("test", "")

    def test_is_similar_threshold_validation(self) -> None:
        """Test threshold value validation."""
        # Valid thresholds
        assert is_similar("test", "test", threshold=0) is True
        assert is_similar("test", "test", threshold=100) is True

        # Invalid thresholds
        with pytest.raises(ValidationError, match="between 0 and 100"):
            is_similar("test", "test", threshold=-1)

        with pytest.raises(ValidationError, match="between 0 and 100"):
            is_similar("test", "test", threshold=101)

    def test_is_similar_case_insensitive(self) -> None:
        """Test case sensitivity in similarity matching."""
        text1 = "Hello World"
        text2 = "hello world"
        # Token-based matching should handle case differences
        assert is_similar(text1, text2, threshold=90) is True

    def test_is_similar_punctuation_handling(self) -> None:
        """Test handling of punctuation in similarity."""
        text1 = "Hello, world!"
        text2 = "Hello world"
        assert is_similar(text1, text2, threshold=85) is True


class TestGetBestMatchSeq:
    """Test cases for get_best_match_seq function."""

    def test_get_best_match_seq_exact_match(self) -> None:
        """Test finding exact match in targets."""
        section = "test section"
        targets = ["other", "test section", "another"]

        match, score = get_best_match_seq(section, targets)
        assert match == "test section"
        assert score == 1.0

    def test_get_best_match_seq_partial_match(self) -> None:
        """Test finding best partial match."""
        section = "hello world"
        targets = ["hi world", "hello there", "goodbye world"]

        match, score = get_best_match_seq(section, targets)
        assert "hello" in match or "world" in match
        assert 0 < score < 1

    def test_get_best_match_seq_empty_targets(self) -> None:
        """Test error handling for empty targets list."""
        with pytest.raises(ValueError, match="empty"):
            get_best_match_seq("test", [])

    def test_get_best_match_seq_invalid_section(self) -> None:
        """Test validation of section parameter."""
        with pytest.raises(ValidationError):
            get_best_match_seq("", ["target"])

    def test_get_best_match_seq_invalid_targets(self) -> None:
        """Test handling of invalid targets."""
        section = "test"
        targets = ["valid", "", "another valid"]

        # Should skip invalid target and still work
        match, _score = get_best_match_seq(section, targets)
        assert match in ["valid", "another valid"]

    def test_get_best_match_seq_case_sensitivity(self) -> None:
        """Test case-sensitive matching behavior."""
        section = "Hello World"
        targets = ["hello world", "HELLO WORLD", "Hello World"]

        match, score = get_best_match_seq(section, targets)
        assert match == "Hello World"
        assert score == 1.0

    def test_get_best_match_seq_long_texts(self) -> None:
        """Test handling of long text sections."""
        section = "x" * 50_000
        targets = [section, "y" * 50_000]

        match, score = get_best_match_seq(section, targets)
        assert match == section
        assert score == 1.0


class TestGetSimilarityMatrix:
    """Test cases for get_similarity_matrix function."""

    def test_get_similarity_matrix_basic(self) -> None:
        """Test basic similarity matrix generation."""
        texts = ["hello world", "hello there", "goodbye world"]
        matrix = get_similarity_matrix(texts, threshold=0.0)

        assert len(matrix) == 3
        assert len(matrix[0]) == 3

        # Check diagonal is 1.0
        for i in range(3):
            assert matrix[i][i] == 1.0

        # Check symmetry
        for i in range(3):
            for j in range(3):
                assert matrix[i][j] == matrix[j][i]

    def test_get_similarity_matrix_threshold_filtering(self) -> None:
        """Test that threshold properly filters results."""
        texts = ["cat", "dog", "cat"]
        matrix = get_similarity_matrix(texts, threshold=0.9)

        # Only identical texts should have high similarity
        assert matrix[0][2] > 0.9  # "cat" vs "cat"
        assert matrix[0][1] == 0.0  # "cat" vs "dog" below threshold

    def test_get_similarity_matrix_empty_list(self) -> None:
        """Test error handling for empty text list."""
        with pytest.raises(ValueError, match="empty"):
            get_similarity_matrix([])

    def test_get_similarity_matrix_single_text(self) -> None:
        """Test matrix for single text."""
        texts = ["only one"]
        matrix = get_similarity_matrix(texts)

        assert len(matrix) == 1
        assert matrix[0][0] == 1.0

    def test_get_similarity_matrix_invalid_texts(self) -> None:
        """Test validation of text inputs."""
        with pytest.raises(ValidationError):
            get_similarity_matrix(["valid", "", "also valid"])

    def test_get_similarity_matrix_threshold_validation(self) -> None:
        """Test threshold parameter validation."""
        texts = ["a", "b"]

        # Valid thresholds
        matrix = get_similarity_matrix(texts, threshold=0.0)
        assert matrix is not None

        matrix = get_similarity_matrix(texts, threshold=1.0)
        assert matrix is not None

        # Invalid thresholds
        with pytest.raises(ValidationError):
            get_similarity_matrix(texts, threshold=1.5)

        with pytest.raises(ValidationError):
            get_similarity_matrix(texts, threshold=-0.1)


class TestFindDuplicateGroups:
    """Test cases for find_duplicate_groups function."""

    def test_find_duplicate_groups_identical_texts(self) -> None:
        """Test grouping of identical texts."""
        # Create matrix with perfect matches
        matrix = [[1.0, 0.95, 0.1], [0.95, 1.0, 0.1], [0.1, 0.1, 1.0]]

        groups = find_duplicate_groups(matrix, threshold=0.9)
        assert len(groups) == 1
        assert set(groups[0]) == {0, 1}

    def test_find_duplicate_groups_no_duplicates(self) -> None:
        """Test when no duplicates exist."""
        # Create matrix with low similarities
        matrix = [[1.0, 0.3, 0.2], [0.3, 1.0, 0.4], [0.2, 0.4, 1.0]]

        groups = find_duplicate_groups(matrix, threshold=0.9)
        assert len(groups) == 0

    def test_find_duplicate_groups_multiple_groups(self) -> None:
        """Test multiple separate duplicate groups."""
        # Create matrix with two separate groups
        matrix = [[1.0, 0.95, 0.1, 0.1], [0.95, 1.0, 0.1, 0.1], [0.1, 0.1, 1.0, 0.92], [0.1, 0.1, 0.92, 1.0]]

        groups = find_duplicate_groups(matrix, threshold=0.9)
        assert len(groups) == 2
        assert {0, 1} in [set(g) for g in groups]
        assert {2, 3} in [set(g) for g in groups]

    def test_find_duplicate_groups_empty_matrix(self) -> None:
        """Test error handling for empty matrix."""
        with pytest.raises(ValueError, match="empty"):
            find_duplicate_groups([])

    def test_find_duplicate_groups_non_square_matrix(self) -> None:
        """Test error handling for non-square matrix."""
        matrix = [
            [1.0, 0.5],
            [0.5, 1.0, 0.3],  # Extra element
        ]

        with pytest.raises(ValueError, match="square"):
            find_duplicate_groups(matrix)

    def test_find_duplicate_groups_threshold_validation(self) -> None:
        """Test threshold parameter validation."""
        matrix = [[1.0]]

        # Valid thresholds
        groups = find_duplicate_groups(matrix, threshold=0.0)
        assert groups is not None

        groups = find_duplicate_groups(matrix, threshold=1.0)
        assert groups is not None

        # Invalid thresholds
        with pytest.raises(ValidationError):
            find_duplicate_groups(matrix, threshold=1.1)

        with pytest.raises(ValidationError):
            find_duplicate_groups(matrix, threshold=-0.1)

    def test_find_duplicate_groups_default_threshold(self) -> None:
        """Test default threshold behavior."""
        matrix = [[1.0, 0.96], [0.96, 1.0]]

        # Should use high threshold by default (likely 0.95)
        groups = find_duplicate_groups(matrix)
        assert len(groups) == 1


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_unicode_handling(self) -> None:
        """Test handling of Unicode text."""
        text1 = "Hello 世界 🌍"
        text2 = "Hello 世界 🌍"

        assert is_similar(text1, text2) is True

        sections = split_sections(f"{text1}\n\n{text2}")
        assert len(sections) == 2

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        text = "Test with @#$%^&*() special chars!"
        sections = split_sections(text)
        assert sections[0] == text

        assert is_similar(text, text) is True

    def test_performance_large_matrix(self) -> None:
        """Test performance with larger similarity matrix."""
        # Create 50x50 matrix
        n = 50
        matrix = [[1.0 if i == j else 0.5 for j in range(n)] for i in range(n)]

        # Should complete without timeout
        groups = find_duplicate_groups(matrix, threshold=0.9)
        assert len(groups) == 0  # No duplicates with threshold 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
