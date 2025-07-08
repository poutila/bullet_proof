"""Tests for compliance_checks module."""

from pathlib import Path

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
    """Test ComplianceIssue dataclass."""

    def test_compliance_issue_creation(self) -> None:
        """Test creating a ComplianceIssue instance."""
        issue = ComplianceIssue(
            file_path=Path("test.py"), issue_type="test-rule", severity="high", description="Test message", line_number=10
        )
        assert issue.file_path == Path("test.py")
        assert issue.issue_type == "test-rule"
        assert issue.severity == "high"
        assert issue.description == "Test message"
        assert issue.line_number == 10


class TestCheckTypeHints:
    """Test check_type_hints function."""

    def test_check_type_hints_all_present(self, tmp_path: Path) -> None:
        """Test when all type hints are present."""
        code = """
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return f"Hello, {name}"
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_type_hints(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_type_hints_missing(self, tmp_path: Path) -> None:
        """Test when type hints are missing."""
        code = """
def add(a, b):
    return a + b

def greet(name: str):
    return f"Hello, {name}"
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_type_hints(file_path)
        assert result is False
        assert len(issues) > 0
        assert any("add" in issue.description for issue in issues)

    def test_check_type_hints_invalid_syntax(self, tmp_path: Path) -> None:
        """Test handling of invalid Python syntax."""
        code = """
def invalid syntax here
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_type_hints(file_path)
        assert result is False
        assert len(issues) == 1
        assert "Failed to parse" in issues[0].description


class TestCheckTestCoverage:
    """Test check_test_coverage function."""

    def test_check_test_coverage_test_exists(self, tmp_path: Path) -> None:
        """Test when corresponding test file exists."""
        src_file = tmp_path / "module.py"
        src_file.write_text("def func(): pass")

        test_file = tmp_path / "test_module.py"
        test_file.write_text("def test_func(): pass")

        result, issues = check_test_coverage(src_file)
        assert result is True
        assert len(issues) == 0

    def test_check_test_coverage_no_test_file(self, tmp_path: Path) -> None:
        """Test when no test file exists."""
        src_file = tmp_path / "module.py"
        src_file.write_text("def func(): pass")

        result, issues = check_test_coverage(src_file)
        assert result is False
        assert len(issues) == 1
        assert "No test file found" in issues[0].description

    def test_check_test_coverage_skip_init(self, tmp_path: Path) -> None:
        """Test that __init__.py files are skipped."""
        init_file = tmp_path / "__init__.py"
        init_file.write_text("")

        result, issues = check_test_coverage(init_file)
        assert result is True
        assert len(issues) == 0


class TestCheckDocstrings:
    """Test check_docstrings function."""

    def test_check_docstrings_present(self, tmp_path: Path) -> None:
        """Test when all docstrings are present."""
        code = '''
"""Module docstring."""

def func():
    """Function docstring."""
    pass

class MyClass:
    """Class docstring."""
    
    def method(self):
        """Method docstring."""
        pass
'''
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_docstrings(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_docstrings_missing(self, tmp_path: Path) -> None:
        """Test when docstrings are missing."""
        code = """
def func():
    pass

class MyClass:
    def method(self):
        pass
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_docstrings(file_path)
        assert result is False
        assert len(issues) > 0
        assert any("func" in issue.description for issue in issues)
        assert any("MyClass" in issue.description for issue in issues)


class TestCheckFileLength:
    """Test check_file_length function."""

    def test_check_file_length_under_limit(self, tmp_path: Path) -> None:
        """Test file under 500 lines."""
        code = "\n".join(["# Line"] * 400)
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_file_length(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_file_length_over_limit(self, tmp_path: Path) -> None:
        """Test file over 500 lines."""
        code = "\n".join(["# Line"] * 600)
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_file_length(file_path)
        assert result is False
        assert len(issues) == 1
        assert "600 lines" in issues[0].description


class TestCheckForbiddenPatterns:
    """Test check_forbidden_patterns function."""

    def test_check_forbidden_patterns_clean(self, tmp_path: Path) -> None:
        """Test when no forbidden patterns exist."""
        code = """
import logging

logger = logging.getLogger(__name__)

def process():
    logger.info("Processing")
    return True
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_forbidden_patterns(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_forbidden_patterns_found(self, tmp_path: Path) -> None:
        """Test when forbidden patterns are found."""
        code = """
def process():
    print("Processing")
    eval("1 + 1")
    exec("x = 1")
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_forbidden_patterns(file_path)
        assert result is False
        assert len(issues) >= 3
        assert any("print(" in issue.description for issue in issues)
        assert any("eval(" in issue.description for issue in issues)
        assert any("exec(" in issue.description for issue in issues)


class TestCheckSecurityIssues:
    """Test check_security_issues function."""

    def test_check_security_issues_clean(self, tmp_path: Path) -> None:
        """Test when no security issues exist."""
        code = """
import os
from pathlib import Path

def read_file(filename: str) -> str:
    path = Path(filename)
    return path.read_text()
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_security_issues(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_security_issues_found(self, tmp_path: Path) -> None:
        """Test when security issues are found."""
        code = """
def run_command(cmd):
    os.system(cmd)

password = "secret123"
api_key = "sk-1234567890"
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_security_issues(file_path)
        assert result is False
        assert len(issues) > 0
        assert any("hardcoded" in issue.description.lower() for issue in issues)


class TestCheckErrorHandling:
    """Test check_error_handling function."""

    def test_check_error_handling_proper(self, tmp_path: Path) -> None:
        """Test proper error handling."""
        code = """
def process():
    try:
        result = risky_operation()
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ProcessingError() from e
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_error_handling(file_path)
        assert result is True
        assert len(issues) == 0

    def test_check_error_handling_bare_except(self, tmp_path: Path) -> None:
        """Test bare except clause detection."""
        code = """
def process():
    try:
        result = risky_operation()
    except:
        pass
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        result, issues = check_error_handling(file_path)
        assert result is False
        assert len(issues) == 1
        assert "bare except" in issues[0].description


class TestCalculateComplexity:
    """Test calculate_complexity function."""

    def test_calculate_complexity_simple(self, tmp_path: Path) -> None:
        """Test complexity calculation for simple function."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        complexities = calculate_complexity(file_path)
        assert len(complexities) == 1
        assert complexities[0][0] == "add"
        assert complexities[0][1] == 1  # Simple function has complexity 1

    def test_calculate_complexity_high(self, tmp_path: Path) -> None:
        """Test complexity calculation for complex function."""
        code = """
def complex_func(x):
    if x > 0:
        if x > 10:
            if x > 20:
                return "high"
            else:
                return "medium"
        else:
            for i in range(x):
                if i % 2 == 0:
                    print(i)
    else:
        while x < 0:
            x += 1
            if x == -5:
                break
    return x
"""
        file_path = tmp_path / "test.py"
        file_path.write_text(code)

        complexities = calculate_complexity(file_path)
        assert len(complexities) == 1
        assert complexities[0][0] == "complex_func"
        assert complexities[0][1] > 5  # High complexity
