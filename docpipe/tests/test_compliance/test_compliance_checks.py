#!/usr/bin/env python3
"""Test suite for document_analyzer.compliance_checks module.

Tests for CLAUDE.md compliance checking utilities.
"""

import tempfile
from pathlib import Path

import pytest

from src.compliance.compliance_checks import (
    ComplianceIssue,
    calculate_complexity,
    check_docstrings,
    check_error_handling,
    check_file_length,
    check_forbidden_patterns,
    check_security_issues,
    check_test_coverage,
    check_type_hints,
)


class TestComplianceIssue:
    """Test cases for ComplianceIssue dataclass."""

    def test_compliance_issue_creation(self) -> None:
        """Test ComplianceIssue creation."""
        issue = ComplianceIssue(file_path=Path("test.py"), issue_type="test", severity="high", description="Test issue")

        assert issue.file_path == Path("test.py")
        assert issue.issue_type == "test"
        assert issue.severity == "high"
        assert issue.description == "Test issue"


class TestCheckTypeHints:
    """Test cases for check_type_hints function."""

    def test_check_type_hints_typed_function(self) -> None:
        """Test detection of properly typed functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def typed_function(x: int, y: str) -> bool:
    return True
""")

            has_hints, issues = check_type_hints(test_file)

            assert has_hints is True
            assert len(issues) == 0

    def test_check_type_hints_untyped_function(self) -> None:
        """Test detection of untyped functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def untyped_function(x, y):
    return True
""")

            has_hints, issues = check_type_hints(test_file)

            assert has_hints is False
            assert len(issues) > 0
            assert any("missing type hints" in issue.description.lower() for issue in issues)

    def test_check_type_hints_syntax_error(self) -> None:
        """Test handling of syntax errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("invalid python syntax !!!")

            has_hints, issues = check_type_hints(test_file)

            assert has_hints is False
            assert len(issues) > 0
            assert any("Failed to parse" in issue.description for issue in issues)


class TestCheckErrorHandling:
    """Test cases for check_error_handling function."""

    def test_check_error_handling_with_try_except(self) -> None:
        """Test detection of error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def function_with_error_handling():
    try:
        risky_operation()
    except ValueError as e:
        handle_error(e)
""")

            has_handling, _issues = check_error_handling(test_file)

            assert has_handling is True

    def test_check_error_handling_bare_except(self) -> None:
        """Test detection of bare except clauses."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def function_with_bare_except():
    try:
        risky_operation()
    except:
        pass
""")

            _has_handling, issues = check_error_handling(test_file)

            assert len(issues) > 0
            assert any("bare except" in issue.description.lower() for issue in issues)


class TestCheckForbiddenPatterns:
    """Test cases for check_forbidden_patterns function."""

    def test_check_forbidden_patterns_print_statement(self) -> None:
        """Test detection of print statements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def bad_function():
    print("This is forbidden")
""")

            issues = check_forbidden_patterns(test_file)

            assert len(issues) > 0
            assert any("print" in issue.description.lower() for issue in issues)

    def test_check_forbidden_patterns_eval(self) -> None:
        """Test detection of eval usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def bad_function():
    result = eval("1 + 1")
""")

            issues = check_forbidden_patterns(test_file)

            assert len(issues) > 0
            assert any("eval" in issue.description.lower() for issue in issues)

    def test_check_forbidden_patterns_clean_code(self) -> None:
        """Test that clean code passes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
import logging

logger = logging.getLogger(__name__)

def good_function():
    logger.info("This is good")
""")

            issues = check_forbidden_patterns(test_file)

            assert len(issues) == 0


class TestCheckSecurityIssues:
    """Test cases for check_security_issues function."""

    def test_check_security_issues_shell_true(self) -> None:
        """Test detection of shell=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
import subprocess
subprocess.run("ls", shell=True)
""")

            has_issues, issues = check_security_issues(test_file)

            assert has_issues is True
            assert len(issues) > 0
            assert any("shell=true" in issue.description.lower() for issue in issues)

    def test_check_security_issues_hardcoded_password(self) -> None:
        """Test detection of hardcoded passwords."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
password = "secret123"
""")

            has_issues, issues = check_security_issues(test_file)

            assert has_issues is True
            assert len(issues) > 0
            assert any("password" in issue.description.lower() for issue in issues)

    def test_check_security_issues_clean_code(self) -> None:
        """Test that secure code passes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
import os
password = os.environ.get("PASSWORD")
""")

            has_issues, issues = check_security_issues(test_file)

            assert has_issues is False
            assert len(issues) == 0


class TestCheckDocstrings:
    """Test cases for check_docstrings function."""

    def test_check_docstrings_documented_function(self) -> None:
        """Test detection of properly documented functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text('''
"""Module with good documentation."""

def documented_function():
    """This function has a docstring."""
    pass
''')

            has_docs, issues = check_docstrings(test_file)

            assert has_docs is True
            assert len(issues) == 0

    def test_check_docstrings_undocumented_function(self) -> None:
        """Test detection of undocumented functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def undocumented_function():
    pass
""")

            has_docs, issues = check_docstrings(test_file)

            assert has_docs is False
            assert len(issues) > 0
            assert any("missing docstring" in issue.description.lower() for issue in issues)


class TestCheckTestCoverage:
    """Test cases for check_test_coverage function."""

    def test_check_test_coverage_existing_test(self) -> None:
        """Test detection of existing test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source file
            source_file = Path(temp_dir) / "module.py"
            source_file.write_text("def function(): pass")

            # Create corresponding test file
            test_file = Path(temp_dir) / "test_module.py"
            test_file.write_text("def test_function(): pass")

            has_tests, issues = check_test_coverage(source_file)

            assert has_tests is True
            assert len(issues) == 0

    def test_check_test_coverage_missing_test(self) -> None:
        """Test detection of missing test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source file without test
            source_file = Path(temp_dir) / "module.py"
            source_file.write_text("def function(): pass")

            has_tests, issues = check_test_coverage(source_file)

            assert has_tests is False
            assert len(issues) > 0
            assert any("no corresponding test file" in issue.description.lower() for issue in issues)

    def test_check_test_coverage_test_file_itself(self) -> None:
        """Test that test files themselves pass coverage check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_module.py"
            test_file.write_text("def test_function(): pass")

            has_tests, issues = check_test_coverage(test_file)

            assert has_tests is True
            assert len(issues) == 0


class TestCalculateComplexity:
    """Test cases for calculate_complexity function."""

    def test_calculate_complexity_simple_function(self) -> None:
        """Test complexity calculation for simple function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def simple_function():
    return True
""")

            complexity, issues = calculate_complexity(test_file)

            assert complexity == 1  # Base complexity
            assert len(issues) == 0

    def test_calculate_complexity_complex_function(self) -> None:
        """Test complexity calculation for complex function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                while i > 0:
                    if i > 5:
                        try:
                            result = i / 2
                        except ZeroDivisionError:
                            result = 0
                        if result > 1:
                            return result
                    i -= 1
    return 0
""")

            complexity, issues = calculate_complexity(test_file)

            assert complexity > 10  # Should exceed threshold
            assert len(issues) > 0
            assert any("complexity" in issue.description.lower() for issue in issues)


class TestCheckFileLength:
    """Test cases for check_file_length function."""

    def test_check_file_length_short_file(self) -> None:
        """Test that short files pass length check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def function(): pass\n")

            issues = check_file_length(test_file)

            assert len(issues) == 0

    def test_check_file_length_long_file(self) -> None:
        """Test detection of overly long files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            # Create file with > 500 lines
            long_content = "\n".join([f"# Line {i}" for i in range(501)])
            test_file.write_text(long_content)

            issues = check_file_length(test_file)

            assert len(issues) > 0
            assert any("file has" in issue.description.lower() and "lines" in issue.description.lower() for issue in issues)


class TestIntegration:
    """Integration tests for compliance checks."""

    def test_multiple_checks_on_good_file(self) -> None:
        """Test multiple compliance checks on a well-written file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a good Python file
            good_file = Path(temp_dir) / "good_module.py"
            good_file.write_text('''
"""Well-written module with good practices."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GoodClass:
    """A well-documented class."""

    def __init__(self, value: int) -> None:
        """Initialize with a value."""
        self.value = value

    def process(self, data: Optional[str] = None) -> bool:
        """Process data safely."""
        try:
            if data is not None:
                logger.info(f"Processing: {data}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error processing: {e}")
            return False
''')

            # Create corresponding test file
            test_file = Path(temp_dir) / "test_good_module.py"
            test_file.write_text("def test_good_class(): pass")

            # Run all checks
            has_hints, _hint_issues = check_type_hints(good_file)
            has_handling, _handling_issues = check_error_handling(good_file)
            forbidden_issues = check_forbidden_patterns(good_file)
            has_security, _security_issues = check_security_issues(good_file)
            has_docs, _doc_issues = check_docstrings(good_file)
            has_tests, _test_issues = check_test_coverage(good_file)
            _complexity, complexity_issues = calculate_complexity(good_file)
            length_issues = check_file_length(good_file)

            # All checks should pass
            assert has_hints is True
            assert has_handling is True
            assert len(forbidden_issues) == 0
            assert has_security is False  # No security issues
            assert has_docs is True
            assert has_tests is True
            assert len(complexity_issues) == 0
            assert len(length_issues) == 0


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
