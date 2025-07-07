"""Tests for claude_compliance_checker_simple module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.claude_compliance_checker_simple import (
    ClaudeComplianceChecker,
    FileCompliance,
    main,
)
from src.compliance_checks import ComplianceIssue


class TestFileCompliance:
    """Test FileCompliance dataclass."""

    def test_file_compliance_creation(self) -> None:
        """Test creating a FileCompliance instance."""
        compliance = FileCompliance(
            file_path=Path("test.py"),
            has_type_hints=True,
            has_error_handling=True,
            has_tests=True,
            has_docstrings=True,
            has_security_issues=False,
            complexity_score=5,
            line_count=100,
            issues=[],
        )
        assert compliance.file_path == Path("test.py")
        assert compliance.has_type_hints is True
        assert len(compliance.issues) == 0

    def test_file_compliance_with_issues(self) -> None:
        """Test FileCompliance with issues."""
        issue = ComplianceIssue(file_path=Path("test.py"), issue_type="test-rule", severity="high", description="Test issue")
        compliance = FileCompliance(file_path=Path("test.py"), has_type_hints=False, issues=[issue])
        assert compliance.has_type_hints is False
        assert len(compliance.issues) == 1


class TestClaudeComplianceChecker:
    """Test ClaudeComplianceChecker class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test checker initialization."""
        checker = ClaudeComplianceChecker(tmp_path)
        assert checker.project_root == tmp_path
        assert checker.ignore_dirs == {".venv", "__pycache__", ".git", "node_modules"}

    def test_find_python_files(self, tmp_path: Path) -> None:
        """Test finding Python files."""
        # Create test structure
        (tmp_path / "module1.py").write_text("# Python file")
        (tmp_path / "module2.py").write_text("# Another file")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "module3.py").write_text("# Subdir file")
        (tmp_path / ".venv" / "ignored.py").mkdir(parents=True)
        (tmp_path / ".venv" / "ignored.py").write_text("# Should be ignored")

        checker = ClaudeComplianceChecker(tmp_path)
        files = checker.find_python_files()

        assert len(files) == 3
        assert Path("module1.py") in [f.name for f in files]
        assert Path("module2.py") in [f.name for f in files]
        assert Path("module3.py") in [f.name for f in files]

    @patch("compliance.compliance_checks.check_type_hints")
    @patch("compliance.compliance_checks.check_test_coverage")
    @patch("compliance.compliance_checks.check_docstrings")
    @patch("compliance.compliance_checks.check_file_length")
    @patch("compliance.compliance_checks.check_forbidden_patterns")
    @patch("compliance.compliance_checks.check_security_issues")
    @patch("compliance.compliance_checks.check_error_handling")
    @patch("compliance.compliance_checks.calculate_complexity")
    def test_check_file_compliance_all_pass(
        self,
        mock_complexity,
        mock_error,
        mock_security,
        mock_forbidden,
        mock_length,
        mock_docstrings,
        mock_coverage,
        mock_hints,
        tmp_path: Path,
    ) -> None:
        """Test checking file compliance when all checks pass."""
        # Setup mocks
        mock_hints.return_value = (True, [])
        mock_coverage.return_value = (True, [])
        mock_docstrings.return_value = (True, [])
        mock_length.return_value = (True, [])
        mock_forbidden.return_value = (True, [])
        mock_security.return_value = (True, [])
        mock_error.return_value = (True, [])
        mock_complexity.return_value = []

        file_path = tmp_path / "test.py"
        file_path.write_text("def test(): pass")

        checker = ClaudeComplianceChecker(tmp_path)
        compliance = checker.check_file_compliance(file_path)

        assert compliance.is_compliant is True
        assert len(compliance.issues) == 0
        assert compliance.type_hints_ok is True
        assert compliance.test_coverage_ok is True

    @patch("compliance.compliance_checks.check_type_hints")
    @patch("compliance.compliance_checks.check_test_coverage")
    def test_check_file_compliance_with_issues(self, mock_coverage, mock_hints, tmp_path: Path) -> None:
        """Test checking file compliance with issues."""
        # Setup mocks to return issues
        hint_issue = ComplianceIssue(
            file_path=file_path, issue_type="type-hints", severity="high", description="Missing type hints"
        )
        coverage_issue = ComplianceIssue(
            file_path=file_path, issue_type="test-coverage", severity="high", description="No test file"
        )

        mock_hints.return_value = (False, [hint_issue])
        mock_coverage.return_value = (False, [coverage_issue])

        # Mock other checks to pass
        with (
            patch("compliance.compliance_checks.check_docstrings", return_value=(True, [])),
            patch("compliance.compliance_checks.check_file_length", return_value=(True, [])),
            patch("compliance.compliance_checks.check_forbidden_patterns", return_value=(True, [])),
            patch("compliance.compliance_checks.check_security_issues", return_value=(True, [])),
            patch("compliance.compliance_checks.check_error_handling", return_value=(True, [])),
            patch("compliance.compliance_checks.calculate_complexity", return_value=[]),
        ):
            file_path = tmp_path / "test.py"
            file_path.write_text("def test(): pass")

            checker = ClaudeComplianceChecker(tmp_path)
            compliance = checker.check_file_compliance(file_path)

            assert compliance.is_compliant is False
            assert len(compliance.issues) == 2
            assert compliance.type_hints_ok is False
            assert compliance.test_coverage_ok is False

    def test_check_project_compliance(self, tmp_path: Path) -> None:
        """Test checking entire project compliance."""
        # Create test files
        (tmp_path / "good.py").write_text('''
"""Good module."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
''')

        (tmp_path / "test_good.py").write_text('''
"""Test for good module."""

def test_add() -> None:
    """Test add function."""
    assert add(1, 2) == 3
''')

        checker = ClaudeComplianceChecker(tmp_path)
        with patch.object(checker, "print_report") as mock_print:
            overall_compliant = checker.check_project_compliance()

            # Should have checked both files
            assert mock_print.called

    def test_calculate_overall_compliance(self, tmp_path: Path) -> None:
        """Test calculating overall compliance percentage."""
        compliant_file = FileCompliance(file_path=Path("compliant.py"), is_compliant=True, issues=[])

        non_compliant_file = FileCompliance(
            file_path=Path("non_compliant.py"), is_compliant=False, issues=[ComplianceIssue("test", "error", "issue")]
        )

        checker = ClaudeComplianceChecker(tmp_path)
        percentage = checker.calculate_overall_compliance([compliant_file, non_compliant_file])

        assert percentage == 50.0

    def test_calculate_overall_compliance_empty(self, tmp_path: Path) -> None:
        """Test calculating compliance with no files."""
        checker = ClaudeComplianceChecker(tmp_path)
        percentage = checker.calculate_overall_compliance([])

        assert percentage == 100.0

    def test_print_report(self, tmp_path: Path, capsys) -> None:
        """Test printing compliance report."""
        compliant_file = FileCompliance(
            file_path=Path("compliant.py"),
            is_compliant=True,
            issues=[],
            type_hints_ok=True,
            test_coverage_ok=True,
            docstrings_ok=True,
            file_length_ok=True,
            no_forbidden_patterns=True,
            security_ok=True,
            error_handling_ok=True,
            complexity_ok=True,
        )

        non_compliant_file = FileCompliance(
            file_path=Path("non_compliant.py"),
            is_compliant=False,
            issues=[ComplianceIssue(Path("non_compliant.py"), "type-hints", "high", "Missing type hints", line_number=10)],
            type_hints_ok=False,
            test_coverage_ok=True,
            docstrings_ok=True,
            file_length_ok=True,
            no_forbidden_patterns=True,
            security_ok=True,
            error_handling_ok=True,
            complexity_ok=True,
        )

        checker = ClaudeComplianceChecker(tmp_path)
        checker.print_report([compliant_file, non_compliant_file])

        captured = capsys.readouterr()
        assert "CLAUDE.md COMPLIANCE ANALYSIS" in captured.out
        assert "✅ compliant.py" in captured.out
        assert "❌ non_compliant.py" in captured.out
        assert "Missing type hints" in captured.out
        assert "50.0%" in captured.out


class TestMain:
    """Test main function."""

    @patch("src.compliance.claude_compliance_checker_simple.ClaudeComplianceChecker")
    def test_main_with_path(self, mock_checker_class, tmp_path: Path) -> None:
        """Test main function with custom path."""
        mock_checker = MagicMock()
        mock_checker.check_project_compliance.return_value = True
        mock_checker_class.return_value = mock_checker

        with patch("sys.argv", ["checker.py", str(tmp_path)]):
            main()

        mock_checker_class.assert_called_once_with(tmp_path)
        mock_checker.check_project_compliance.assert_called_once()

    @patch("src.compliance.claude_compliance_checker_simple.ClaudeComplianceChecker")
    def test_main_no_args(self, mock_checker_class) -> None:
        """Test main function with no arguments."""
        mock_checker = MagicMock()
        mock_checker.check_project_compliance.return_value = False
        mock_checker_class.return_value = mock_checker

        with patch("sys.argv", ["checker.py"]):
            main()

        # Should use current directory
        mock_checker_class.assert_called_once()
        mock_checker.check_project_compliance.assert_called_once()

    @patch("src.compliance.claude_compliance_checker_simple.ClaudeComplianceChecker")
    def test_main_exit_codes(self, mock_checker_class) -> None:
        """Test main function exit codes."""
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker

        # Test successful compliance
        mock_checker.check_project_compliance.return_value = True
        with patch("sys.argv", ["checker.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        # Test failed compliance
        mock_checker.check_project_compliance.return_value = False
        with patch("sys.argv", ["checker.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
