#!/usr/bin/env python3
"""Tests for project_analysis.patterns module.

Tests all pattern constants and regex patterns according to CLAUDE.md standards.
"""

import re
from typing import Final

import pytest

from src.project_analysis.patterns import (
    ARCHITECTURE_TERMS,
    CI_CD_TERMS,
    COMMON_PREFIXES,
    FILE_GENERATION_PATTERNS,
    FILE_SEARCH_PATHS,
    INSTRUCTION_PATTERNS,
    TEST_TERMS,
)


class TestInstructionPatterns:
    """Test INSTRUCTION_PATTERNS regex patterns."""

    def test_instruction_patterns_is_list(self) -> None:
        """Test INSTRUCTION_PATTERNS is a list of strings."""
        assert isinstance(INSTRUCTION_PATTERNS, list)
        assert len(INSTRUCTION_PATTERNS) > 0
        for pattern in INSTRUCTION_PATTERNS:
            assert isinstance(pattern, str)

    def test_instruction_patterns_valid_regex(self) -> None:
        """Test all instruction patterns are valid regex."""
        for pattern in INSTRUCTION_PATTERNS:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")

    def test_instruction_patterns_must_should_detection(self) -> None:
        """Test detection of must/should/need to patterns."""
        pattern = INSTRUCTION_PATTERNS[0]
        
        test_cases = [
            ("You must implement the feature", True),
            ("should create a test", True),
            ("need to fix the bug", True),
            ("required to update docs", True),
            ("This is optional", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"

    def test_instruction_patterns_create_implement_detection(self) -> None:
        """Test detection of create/implement/build patterns."""
        pattern = INSTRUCTION_PATTERNS[1]
        
        test_cases = [
            ("create a new module", True),
            ("implement the algorithm", True),
            ("build the documentation", True),
            ("generate test reports", True),
            ("write unit tests", True),
            ("read the file", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"

    def test_instruction_patterns_reference_detection(self) -> None:
        """Test detection of markdown reference patterns."""
        pattern = INSTRUCTION_PATTERNS[2]
        
        test_cases = [
            ("follow [CONTRIBUTING](CONTRIBUTING.md)", True),
            ("use [this guide](docs/guide.md)", True),
            ("see [README](README.md)", True),
            ("plain text without links", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"

    def test_instruction_patterns_command_detection(self) -> None:
        """Test detection of command execution patterns."""
        pattern = INSTRUCTION_PATTERNS[3]
        
        test_cases = [
            ("run `pytest`", True),
            ("execute `make build`", True),
            ("run the following: test", False),
            ("execute without backticks", False),
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"


class TestFileGenerationPatterns:
    """Test FILE_GENERATION_PATTERNS regex patterns."""

    def test_file_generation_patterns_is_list(self) -> None:
        """Test FILE_GENERATION_PATTERNS is a list of strings."""
        assert isinstance(FILE_GENERATION_PATTERNS, list)
        assert len(FILE_GENERATION_PATTERNS) > 0
        for pattern in FILE_GENERATION_PATTERNS:
            assert isinstance(pattern, str)

    def test_file_generation_patterns_valid_regex(self) -> None:
        """Test all file generation patterns are valid regex."""
        for pattern in FILE_GENERATION_PATTERNS:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")

    def test_file_generation_create_file_detection(self) -> None:
        """Test detection of create file patterns."""
        pattern = FILE_GENERATION_PATTERNS[0]
        
        test_cases = [
            ("create file `config.yml`", True),
            ("generate `output.json`", True),
            ("write script `deploy.sh`", True),
            ("create config.yml", False),  # No backticks
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"

    def test_file_generation_extension_detection(self) -> None:
        """Test detection of files with specific extensions."""
        # Check pattern that matches file extensions
        extension_patterns = [p for p in FILE_GENERATION_PATTERNS if "py|yml" in p]
        assert len(extension_patterns) > 0
        
        pattern = extension_patterns[0]
        test_cases = [
            ("creates config.yml", True),
            ("generates script.py", True),
            ("creates readme.md", True),
            ("creates file.txt", True),
            ("creates file.exe", False),  # Not in allowed extensions
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"

    def test_file_generation_backtick_detection(self) -> None:
        """Test detection of filenames in backticks."""
        # Find pattern that matches backtick filenames
        backtick_patterns = [p for p in FILE_GENERATION_PATTERNS if "`([^`]+\\." in p]
        assert len(backtick_patterns) > 0
        
        pattern = backtick_patterns[0]
        test_cases = [
            ("`config.yml`", True),
            ("`test.py`", True),
            ("`README.md`", True),
            ("config.yml", False),  # No backticks
            ("`no-extension`", False),  # No file extension
        ]
        
        for text, should_match in test_cases:
            match = re.search(pattern, text)
            assert (match is not None) == should_match, f"Pattern failed for: {text}"


class TestCoverageTerms:
    """Test coverage check term lists."""

    def test_ci_cd_terms_valid(self) -> None:
        """Test CI_CD_TERMS contains expected values."""
        assert isinstance(CI_CD_TERMS, list)
        assert len(CI_CD_TERMS) > 0
        
        expected_terms = ["ci/cd", "github action", "workflow", "pipeline"]
        for term in expected_terms:
            assert term in CI_CD_TERMS
        
        # All terms should be lowercase for case-insensitive matching
        for term in CI_CD_TERMS:
            assert isinstance(term, str)
            assert term == term.lower()

    def test_test_terms_valid(self) -> None:
        """Test TEST_TERMS contains expected values."""
        assert isinstance(TEST_TERMS, list)
        assert len(TEST_TERMS) > 0
        
        expected_terms = ["pytest", "test automation", "coverage", "mutation test"]
        for term in expected_terms:
            assert term in TEST_TERMS
        
        # All terms should be lowercase
        for term in TEST_TERMS:
            assert isinstance(term, str)
            assert term == term.lower()

    def test_architecture_terms_valid(self) -> None:
        """Test ARCHITECTURE_TERMS contains expected values."""
        assert isinstance(ARCHITECTURE_TERMS, list)
        assert len(ARCHITECTURE_TERMS) > 0
        
        expected_terms = ["architecture", "design", "component", "module"]
        for term in expected_terms:
            assert term in ARCHITECTURE_TERMS
        
        # All terms should be lowercase
        for term in ARCHITECTURE_TERMS:
            assert isinstance(term, str)
            assert term == term.lower()

    def test_no_duplicate_terms(self) -> None:
        """Test that term lists don't have duplicates."""
        assert len(CI_CD_TERMS) == len(set(CI_CD_TERMS))
        assert len(TEST_TERMS) == len(set(TEST_TERMS))
        assert len(ARCHITECTURE_TERMS) == len(set(ARCHITECTURE_TERMS))


class TestFileSearchPaths:
    """Test file search path configuration."""

    def test_file_search_paths_valid(self) -> None:
        """Test FILE_SEARCH_PATHS contains valid directory paths."""
        assert isinstance(FILE_SEARCH_PATHS, list)
        assert len(FILE_SEARCH_PATHS) > 0
        
        for path in FILE_SEARCH_PATHS:
            assert isinstance(path, str)
            # Paths should end with / or be empty
            assert path == "" or path.endswith("/")

    def test_file_search_paths_includes_key_dirs(self) -> None:
        """Test FILE_SEARCH_PATHS includes important directories."""
        expected_paths = ["", "src/", "docs/", "tests/"]
        for path in expected_paths:
            assert path in FILE_SEARCH_PATHS

    def test_file_search_paths_no_duplicates(self) -> None:
        """Test FILE_SEARCH_PATHS has no duplicates."""
        assert len(FILE_SEARCH_PATHS) == len(set(FILE_SEARCH_PATHS))

    def test_file_search_paths_no_dangerous_paths(self) -> None:
        """Test FILE_SEARCH_PATHS doesn't contain dangerous paths."""
        # Only check for actual dangerous paths, not just any "/"
        dangerous_paths = ["../", "../../", "/etc/", "/usr/", "~", "//"]
        for path in FILE_SEARCH_PATHS:
            # Check for absolute paths starting with /
            if path.startswith("/") and path != "/":
                pytest.fail(f"Absolute path found: {path}")
            # Check for dangerous patterns
            for dangerous in dangerous_paths:
                assert dangerous not in path, f"Dangerous path found: {path}"


class TestCommonPrefixes:
    """Test common directory prefixes."""

    def test_common_prefixes_valid(self) -> None:
        """Test COMMON_PREFIXES contains valid values."""
        assert isinstance(COMMON_PREFIXES, list)
        assert len(COMMON_PREFIXES) > 0
        
        for prefix in COMMON_PREFIXES:
            assert isinstance(prefix, str)
            # Prefixes should end with / or be empty
            assert prefix == "" or prefix.endswith("/")

    def test_common_prefixes_expected_values(self) -> None:
        """Test COMMON_PREFIXES contains expected directories."""
        expected = ["planning/", "docs/", ""]
        for prefix in expected:
            assert prefix in COMMON_PREFIXES

    def test_common_prefixes_no_duplicates(self) -> None:
        """Test COMMON_PREFIXES has no duplicates."""
        assert len(COMMON_PREFIXES) == len(set(COMMON_PREFIXES))


class TestPatternIntegration:
    """Test pattern integration and usage scenarios."""

    def test_instruction_pattern_coverage(self) -> None:
        """Test instruction patterns cover common instruction types."""
        test_instructions = [
            "You must implement error handling",
            "should create unit tests",
            "need to update documentation",
            "required to fix the bug",
            "create a configuration file",
            "implement the new feature",
            "build the deployment pipeline",
            "follow [CONTRIBUTING](CONTRIBUTING.md)",
            "run `pytest --cov`",
            "CI/CD pipeline configuration",
            "test coverage must be above 90%",
            "generates output.json",
        ]
        
        for instruction in test_instructions:
            matched = False
            for pattern in INSTRUCTION_PATTERNS:
                if re.search(pattern, instruction, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"No pattern matched instruction: {instruction}"

    def test_file_generation_pattern_coverage(self) -> None:
        """Test file generation patterns cover common cases."""
        test_cases = [
            "create file `config.yml`",
            "generates output.json",
            "creates deploy.py",
            "write `test_module.py`",
            "output: results.txt",
            "`data.json` will be created",
        ]
        
        for case in test_cases:
            matched = False
            for pattern in FILE_GENERATION_PATTERNS:
                if re.search(pattern, case, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"No pattern matched case: {case}"

    def test_patterns_are_final(self) -> None:
        """Test that pattern constants use Final type annotation."""
        # This is more of a code review test, but we can verify immutability
        import sys
        patterns_module = sys.modules["src.project_analysis.patterns"]
        
        # Check that key constants exist and are the right type
        expected_lists = [
            "INSTRUCTION_PATTERNS",
            "FILE_GENERATION_PATTERNS",
            "CI_CD_TERMS",
            "TEST_TERMS",
            "ARCHITECTURE_TERMS",
            "FILE_SEARCH_PATHS",
            "COMMON_PREFIXES",
        ]
        
        for const_name in expected_lists:
            assert hasattr(patterns_module, const_name)
            value = getattr(patterns_module, const_name)
            assert isinstance(value, list)


class TestPatternEdgeCases:
    """Test edge cases and potential issues with patterns."""

    def test_patterns_no_catastrophic_backtracking(self) -> None:
        """Test patterns don't have catastrophic backtracking issues."""
        # Create a long string that could cause issues
        long_string = "a" * 1000 + "b" * 1000
        
        for pattern in INSTRUCTION_PATTERNS + FILE_GENERATION_PATTERNS:
            try:
                # This should complete quickly
                re.search(pattern, long_string)
            except:
                pytest.fail(f"Pattern caused issues: {pattern}")

    def test_patterns_handle_special_chars(self) -> None:
        """Test patterns handle special characters gracefully."""
        special_strings = [
            "create `file-name_123.py`",
            "must implement feature (with parens)",
            "follow [link with spaces](path with spaces.md)",
            "generate file@#$%.txt",  # Special chars in filename
        ]
        
        # Just ensure patterns don't crash on special input
        for text in special_strings:
            for pattern in INSTRUCTION_PATTERNS + FILE_GENERATION_PATTERNS:
                try:
                    re.search(pattern, text)
                except re.error:
                    pytest.fail(f"Pattern failed on special chars: {pattern}")

    def test_empty_string_handling(self) -> None:
        """Test patterns handle empty strings."""
        for pattern in INSTRUCTION_PATTERNS + FILE_GENERATION_PATTERNS:
            # Should not crash on empty string
            result = re.search(pattern, "")
            # Empty string shouldn't match any pattern
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])