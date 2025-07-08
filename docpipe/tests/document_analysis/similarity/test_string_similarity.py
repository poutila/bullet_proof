"""Tests for string similarity module."""


import pytest

from src.document_analysis.similarity.string_similarity import (
    StringSimilarityCalculator,
    find_best_match,
    get_best_match_seq,
    is_similar,
    split_sections,
)
from src.document_analysis.validation import ValidationError


class TestStringSimilarityCalculator:
    """Test StringSimilarityCalculator class."""

    def test_init_default_algorithm(self) -> None:
        """Test initialization with default algorithm."""
        calc = StringSimilarityCalculator()
        assert calc.algorithm == "token_set_ratio"

    def test_init_custom_algorithm(self) -> None:
        """Test initialization with custom algorithm."""
        calc = StringSimilarityCalculator(algorithm="ratio")
        assert calc.algorithm == "ratio"

    def test_init_invalid_algorithm(self) -> None:
        """Test initialization with invalid algorithm."""
        with pytest.raises(ValidationError):
            StringSimilarityCalculator(algorithm="invalid")

    def test_calculate_pairwise(self) -> None:
        """Test pairwise similarity calculation."""
        calc = StringSimilarityCalculator()
        score = calc.calculate_pairwise("Hello world", "Hello World!")
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Should be very similar

    def test_calculate_pairwise_identical(self) -> None:
        """Test pairwise similarity for identical strings."""
        calc = StringSimilarityCalculator()
        score = calc.calculate_pairwise("test", "test")
        assert score == 1.0

    def test_calculate_pairwise_different(self) -> None:
        """Test pairwise similarity for different strings."""
        calc = StringSimilarityCalculator()
        score = calc.calculate_pairwise("apple", "orange")
        assert score < 0.5  # Should be quite different


class TestSplitSections:
    """Test split_sections function."""

    def test_split_basic(self) -> None:
        """Test basic section splitting."""
        text = "This is the first section with enough content\n\nThis is the second section with enough content\n\nThis is the third section with enough content"
        sections = split_sections(text)
        assert len(sections) == 3
        assert "first section" in sections[0]
        assert "second section" in sections[1]
        assert "third section" in sections[2]

    def test_split_with_min_length(self) -> None:
        """Test splitting with minimum length."""
        text = "Long section\n\nShort\n\nAnother long section"
        sections = split_sections(text, min_len=10)
        assert len(sections) == 2
        assert "Short" not in sections

    def test_split_empty_text(self) -> None:
        """Test splitting empty text."""
        with pytest.raises(ValidationError):
            split_sections("")  # Empty text raises validation error

    def test_split_invalid_input(self) -> None:
        """Test splitting with invalid input."""
        with pytest.raises(ValidationError):
            split_sections(None)  # type: ignore


class TestIsSimilar:
    """Test is_similar function."""

    def test_similar_texts(self) -> None:
        """Test similar texts."""
        assert is_similar("Hello world", "Hello World!", threshold=80)

    def test_different_texts(self) -> None:
        """Test different texts."""
        assert not is_similar("apple", "orange", threshold=80)

    def test_custom_threshold(self) -> None:
        """Test with custom threshold."""
        text1 = "The quick brown fox"
        text2 = "The fast brown fox"
        assert is_similar(text1, text2, threshold=60)
        assert not is_similar(text1, text2, threshold=95)


class TestFindBestMatch:
    """Test find_best_match function."""

    def test_find_match(self) -> None:
        """Test finding best match."""
        section = "Hello world"
        targets = ["Hi there", "Hello World!", "Goodbye"]
        match, score = find_best_match(section, targets)
        assert match == "Hello World!"
        assert score > 0.8

    def test_no_match_above_threshold(self) -> None:
        """Test when no match is above threshold."""
        section = "Apple"
        targets = ["Orange", "Banana", "Grape"]
        match, score = find_best_match(section, targets, threshold=0.8)
        assert match is None
        assert score == 0.0

    def test_empty_targets(self) -> None:
        """Test with empty targets list."""
        match, score = find_best_match("test", [])
        assert match is None
        assert score == 0.0


class TestGetBestMatchSeq:
    """Test get_best_match_seq function."""

    def test_sequence_matching(self) -> None:
        """Test sequence-based matching."""
        section = "Hello world"
        targets = ["Hi world", "Hello World", "Goodbye"]
        match, score = get_best_match_seq(section, targets)
        assert match == "Hello World"
        assert score > 0.8

    def test_empty_targets_error(self) -> None:
        """Test error with empty targets."""
        with pytest.raises(ValueError, match="Targets list cannot be empty"):
            get_best_match_seq("test", [])
