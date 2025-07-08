"""Tests for claude_compliance_checker module."""

from pathlib import Path

from src.compliance.claude_compliance_checker import (
    ClaudeComplianceChecker,
)


class TestClaudeComplianceCheckerIntegration:
    """Integration tests for the full compliance checker."""

    def test_check_type_hints_integration(self, tmp_path: Path) -> None:
        """Test type hints checking integration."""
        code_with_hints = """
def add(a: int, b: int) -> int:
    return a + b
"""
        code_without_hints = """
def add(a, b):
    return a + b
"""

        file_with = tmp_path / "with_hints.py"
        file_with.write_text(code_with_hints)

        file_without = tmp_path / "without_hints.py"
        file_without.write_text(code_without_hints)

        checker = ClaudeComplianceChecker(tmp_path)

        # File with hints should pass
        compliance_with = checker.analyze_file(file_with)
        assert compliance_with.has_type_hints is True

        # File without hints should fail
        compliance_without = checker.analyze_file(file_without)
        assert compliance_without.has_type_hints is False

    def test_check_test_coverage_integration(self, tmp_path: Path) -> None:
        """Test test coverage checking integration."""
        src_file = tmp_path / "module.py"
        src_file.write_text("def func(): pass")

        test_file = tmp_path / "test_module.py"
        test_file.write_text("def test_func(): pass")

        checker = ClaudeComplianceChecker(tmp_path)

        # Should pass since test file exists
        compliance = checker.analyze_file(src_file)
        assert compliance.has_tests is True

        # Remove test file
        test_file.unlink()

        # Should fail now
        compliance = checker.analyze_file(src_file)
        assert compliance.has_tests is False

    def test_check_file_length_integration(self, tmp_path: Path) -> None:
        """Test file length checking integration."""
        short_file = tmp_path / "short.py"
        short_file.write_text("\n".join(["# Line"] * 100))

        long_file = tmp_path / "long.py"
        long_file.write_text("\n".join(["# Line"] * 600))

        checker = ClaudeComplianceChecker(tmp_path)

        # Short file should pass
        compliance_short = checker.analyze_file(short_file)
        assert compliance_short.line_count < 500

        # Long file should fail
        compliance_long = checker.analyze_file(long_file)
        assert compliance_long.line_count > 500

    def test_check_forbidden_patterns_integration(self, tmp_path: Path) -> None:
        """Test forbidden patterns checking integration."""
        clean_code = """
import logging
logger = logging.getLogger(__name__)

def process():
    logger.info("Processing")
"""

        dirty_code = """
def process():
    print("Processing")
    eval("1 + 1")
"""

        clean_file = tmp_path / "clean.py"
        clean_file.write_text(clean_code)

        dirty_file = tmp_path / "dirty.py"
        dirty_file.write_text(dirty_code)

        checker = ClaudeComplianceChecker(tmp_path)

        # Clean file should pass
        compliance_clean = checker.analyze_file(clean_file)
        assert len([i for i in compliance_clean.issues if i.issue_type == 'forbidden-pattern']) == 0

        # Dirty file should fail
        compliance_dirty = checker.analyze_file(dirty_file)
        assert len([i for i in compliance_dirty.issues if i.issue_type == 'forbidden-pattern']) > 0

    def test_check_security_issues_integration(self, tmp_path: Path) -> None:
        """Test security issues checking integration."""
        secure_code = """
import os
from pathlib import Path

def read_config():
    config_path = Path("config.json")
    return config_path.read_text()
"""

        insecure_code = """
password = "admin123"
api_key = "sk-1234567890"

def run_command(cmd):
    os.system(cmd)
"""

        secure_file = tmp_path / "secure.py"
        secure_file.write_text(secure_code)

        insecure_file = tmp_path / "insecure.py"
        insecure_file.write_text(insecure_code)

        checker = ClaudeComplianceChecker(tmp_path)

        # Secure file should pass
        compliance_secure = checker.analyze_file(secure_file)
        assert compliance_secure.has_security_issues is False

        # Insecure file should fail
        compliance_insecure = checker.analyze_file(insecure_file)
        assert compliance_insecure.has_security_issues is True

    def test_check_error_handling_integration(self, tmp_path: Path) -> None:
        """Test error handling checking integration."""
        good_handling = """
def process():
    try:
        risky_operation()
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise ProcessingError() from e
"""

        bad_handling = """
def process():
    try:
        risky_operation()
    except:
        pass
"""

        good_file = tmp_path / "good_handling.py"
        good_file.write_text(good_handling)

        bad_file = tmp_path / "bad_handling.py"
        bad_file.write_text(bad_handling)

        checker = ClaudeComplianceChecker(tmp_path)

        # Good error handling should pass
        compliance_good = checker.analyze_file(good_file)
        assert compliance_good.has_error_handling is True

        # Bad error handling should fail
        compliance_bad = checker.analyze_file(bad_file)
        assert compliance_bad.has_error_handling is False

    def test_check_complexity_integration(self, tmp_path: Path) -> None:
        """Test complexity checking integration."""
        simple_code = """
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b
"""

        complex_code = """
def complex_func(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            if x > 60:
                                if x > 70:
                                    if x > 80:
                                        if x > 90:
                                            return "very high"
                                        return "high"
                                    return "medium-high"
                                return "medium"
                            return "medium-low"
                        return "low"
                    return "very low"
                return "minimal"
            return "tiny"
        return "small"
    return "negative"
"""

        simple_file = tmp_path / "simple.py"
        simple_file.write_text(simple_code)

        complex_file = tmp_path / "complex.py"
        complex_file.write_text(complex_code)

        checker = ClaudeComplianceChecker(tmp_path)

        # Simple code should pass
        compliance_simple = checker.analyze_file(simple_file)
        assert compliance_simple.complexity_score < 10

        # Complex code should fail
        compliance_complex = checker.analyze_file(complex_file)
        assert compliance_complex.complexity_score >= 10

    def test_full_project_compliance(self, tmp_path: Path) -> None:
        """Test full project compliance checking."""
        # Create a compliant module
        compliant_module = tmp_path / "compliant.py"
        compliant_module.write_text('''
"""A compliant module."""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def process_items(items: List[str]) -> Optional[str]:
    """Process a list of items.
    
    Args:
        items: List of items to process
        
    Returns:
        First item or None if empty
    """
    try:
        if not items:
            return None
        return items[0]
    except Exception as e:
        logger.error(f"Error processing items: {e}")
        raise
''')

        # Create test for compliant module
        test_module = tmp_path / "test_compliant.py"
        test_module.write_text('''
"""Tests for compliant module."""

from compliant import process_items


def test_process_items_with_items() -> None:
    """Test processing non-empty list."""
    result = process_items(["a", "b", "c"])
    assert result == "a"


def test_process_items_empty() -> None:
    """Test processing empty list."""
    result = process_items([])
    assert result is None
''')

        # Create a non-compliant module
        non_compliant = tmp_path / "non_compliant.py"
        non_compliant.write_text("""
def bad_function(x, y):
    print("This uses print")
    try:
        result = x / y
    except:
        pass
    return result
""")

        checker = ClaudeComplianceChecker(tmp_path)
        overall_compliant = checker.check_project_compliance()

        # Project should not be fully compliant due to non_compliant.py
        assert overall_compliant is False

    def test_ignore_directories(self, tmp_path: Path) -> None:
        """Test that certain directories are ignored."""
        # Create files in ignored directories
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "ignored.py").write_text("print('should be ignored')")

        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "cached.pyc").write_text("compiled bytecode")

        # Create a regular Python file
        (tmp_path / "checked.py").write_text("def func(): pass")

        checker = ClaudeComplianceChecker(tmp_path)
        files = checker.find_python_files()

        # Should only find the regular file
        assert len(files) == 1
        assert files[0].name == "checked.py"

    def test_summary_statistics(self, tmp_path: Path, capsys) -> None:
        """Test summary statistics in report."""
        # Create mixed compliance files
        for i in range(3):
            good_file = tmp_path / f"good{i}.py"
            good_file.write_text(f'''
"""Good module {i}."""

def func{i}(x: int) -> int:
    """Function {i}."""
    return x + {i}
''')

            test_file = tmp_path / f"test_good{i}.py"
            test_file.write_text(f"def test_func{i}(): pass")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def bad(): print('bad')")

        checker = ClaudeComplianceChecker(tmp_path)
        checker.check_project_compliance()

        captured = capsys.readouterr()
        assert "Total files checked: 4" in captured.out
        assert "Compliant files: 3" in captured.out
        assert "Non-compliant files: 1" in captured.out
        assert "Overall compliance: 75.0%" in captured.out
