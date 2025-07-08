"""Tests for compliance analyzer."""

import pytest
from pathlib import Path

from docpipe.analyzers import ComplianceAnalyzer, ComplianceConfig
from docpipe.models import Severity, IssueCategory


class TestComplianceConfig:
    """Test ComplianceConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ComplianceConfig()
        
        assert config.min_type_hint_coverage == 80.0
        assert config.min_docstring_coverage == 70.0
        assert config.max_file_lines == 500
        assert config.max_complexity == 10
        assert config.check_type_hints is True
        assert config.check_forbidden_patterns is True
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = ComplianceConfig(
            min_type_hint_coverage=90.0,
            check_docstrings=False,
            max_complexity=5
        )
        
        assert config.min_type_hint_coverage == 90.0
        assert config.check_docstrings is False
        assert config.max_complexity == 5


class TestComplianceAnalyzer:
    """Test ComplianceAnalyzer functionality."""
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = ComplianceAnalyzer()
        assert analyzer.name == "ComplianceAnalyzer"
        assert analyzer.description == "Checks Python code compliance with CLAUDE.md standards"
        
    def test_analyze_good_file(self, python_files):
        """Test analyzing a compliant Python file."""
        analyzer = ComplianceAnalyzer()
        result = analyzer.analyze(python_files['good'])
        
        assert result.success is True
        assert result.analyzer_name == "ComplianceAnalyzer"
        assert isinstance(result.duration_seconds, float)
        
        # Check compliance results
        compliance_results = result.data
        assert compliance_results.files_checked == 1
        assert compliance_results.files_compliant == 1
        assert len(compliance_results.issues) == 0
        assert compliance_results.compliance_score == 100.0
        
    def test_analyze_bad_file(self, python_files):
        """Test analyzing a non-compliant Python file."""
        analyzer = ComplianceAnalyzer()
        result = analyzer.analyze(python_files['bad'])
        
        assert result.success is True
        
        # Check compliance results
        compliance_results = result.data
        assert compliance_results.files_checked == 1
        assert compliance_results.files_compliant == 0
        assert len(compliance_results.issues) > 0
        assert compliance_results.compliance_score == 0.0
        
        # Check specific issues
        issue_categories = {issue.category for issue in compliance_results.issues}
        assert IssueCategory.MISSING_TYPE_HINTS in issue_categories
        assert IssueCategory.MISSING_DOCSTRING in issue_categories
        assert IssueCategory.FORBIDDEN_PATTERN in issue_categories
        assert IssueCategory.SECURITY_PATTERN in issue_categories
        
        # Check for specific forbidden patterns
        issue_messages = [issue.message for issue in compliance_results.issues]
        assert any("print() statement found" in msg for msg in issue_messages)
        assert any("Bare except clause" in msg for msg in issue_messages)
        assert any("eval" in msg for msg in issue_messages)
        assert any("password" in msg for msg in issue_messages)
        
    def test_analyze_directory(self, python_files):
        """Test analyzing a directory with multiple Python files."""
        analyzer = ComplianceAnalyzer()
        result = analyzer.analyze(python_files['good'].parent)
        
        assert result.success is True
        
        compliance_results = result.data
        assert compliance_results.files_checked >= 2  # At least good and bad files
        assert compliance_results.files_compliant >= 1  # At least the good file
        assert compliance_results.compliance_score > 0
        assert compliance_results.compliance_score < 100  # Due to bad file
        
    def test_type_hint_coverage(self, temp_dir):
        """Test type hint coverage calculation."""
        # Create file with partial type hints
        content = '''
        def func1(x: int) -> int:
            return x
        
        def func2(x, y):  # Missing type hints
            return x + y
        
        def func3(x: str) -> str:
            return x.upper()
        '''
        
        test_file = temp_dir / "partial_hints.py"
        test_file.write_text(content)
        
        analyzer = ComplianceAnalyzer({
            "compliance": {"min_type_hint_coverage": 80.0}
        })
        result = analyzer.analyze(test_file)
        
        compliance_results = result.data
        # 2 out of 3 functions have type hints = 66.7% < 80%
        assert any(
            "Type hint coverage" in issue.message and "below required" in issue.message
            for issue in compliance_results.issues
        )
        
    def test_complexity_check(self, temp_dir):
        """Test cyclomatic complexity checking."""
        # Create file with complex function
        content = '''
        def complex_func(a, b, c, d):
            """Very complex function."""
            if a:
                if b:
                    for i in range(10):
                        if c:
                            while d:
                                if i > 5:
                                    return 1
                                d -= 1
                        else:
                            return 2
                else:
                    return 3
            return 0
        '''
        
        test_file = temp_dir / "complex.py"
        test_file.write_text(content)
        
        analyzer = ComplianceAnalyzer({
            "compliance": {"max_complexity": 5}
        })
        result = analyzer.analyze(test_file)
        
        compliance_results = result.data
        assert any(
            issue.category == IssueCategory.HIGH_COMPLEXITY
            for issue in compliance_results.issues
        )
        
    def test_file_length_check(self, temp_dir):
        """Test file length checking."""
        # Create long file
        lines = ['# Line {}'.format(i) for i in range(600)]
        content = '\n'.join(lines)
        
        test_file = temp_dir / "long_file.py"
        test_file.write_text(content)
        
        analyzer = ComplianceAnalyzer({
            "compliance": {"max_file_lines": 500}
        })
        result = analyzer.analyze(test_file)
        
        compliance_results = result.data
        assert any(
            issue.category == IssueCategory.FILE_TOO_LONG
            for issue in compliance_results.issues
        )
        
    def test_test_file_check(self, temp_dir):
        """Test checking for corresponding test files."""
        # Create module without test
        module_file = temp_dir / "my_module.py"
        module_file.write_text('def func(): pass')
        
        analyzer = ComplianceAnalyzer()
        result = analyzer.analyze(module_file)
        
        compliance_results = result.data
        assert any(
            issue.category == IssueCategory.MISSING_TESTS
            for issue in compliance_results.issues
        )
        
    def test_skip_test_files(self, temp_dir):
        """Test that test files are skipped for certain checks."""
        # Create test file with missing type hints
        content = '''
        def test_something():
            # No type hints needed in tests
            x = 1
            y = 2
            assert x + y == 3
        '''
        
        test_file = temp_dir / "test_module.py"
        test_file.write_text(content)
        
        analyzer = ComplianceAnalyzer()
        result = analyzer.analyze(test_file)
        
        compliance_results = result.data
        # Should not complain about missing type hints in test files
        assert not any(
            issue.category == IssueCategory.MISSING_TYPE_HINTS
            for issue in compliance_results.issues
        )
        
    def test_custom_forbidden_patterns(self, temp_dir):
        """Test custom forbidden patterns."""
        content = '''
        def func():
            # Custom forbidden pattern
            TODO: Fix this
            return None
        '''
        
        test_file = temp_dir / "custom.py"
        test_file.write_text(content)
        
        analyzer = ComplianceAnalyzer({
            "compliance": {
                "forbidden_patterns": [r'TODO:']
            }
        })
        result = analyzer.analyze(test_file)
        
        compliance_results = result.data
        assert any(
            issue.category == IssueCategory.FORBIDDEN_PATTERN
            for issue in compliance_results.issues
        )