"""Tests for issue and feedback models."""

import pytest
from pathlib import Path

from docpipe.models import (
    Issue,
    Feedback,
    IssueGroup,
    Severity,
    IssueCategory,
    ValidationResult,
)


class TestSeverity:
    """Test Severity enum."""
    
    def test_severity_ordering(self):
        """Test severity comparison."""
        assert Severity.HINT < Severity.INFO
        assert Severity.INFO < Severity.WARNING
        assert Severity.WARNING < Severity.ERROR
        assert Severity.ERROR < Severity.CRITICAL
        
    def test_severity_values(self):
        """Test severity string values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"
        assert Severity.HINT.value == "hint"


class TestIssue:
    """Test Issue model."""
    
    def test_create_issue(self):
        """Test creating an issue."""
        issue = Issue(
            severity=Severity.ERROR,
            category=IssueCategory.MISSING_TYPE_HINTS,
            message="Function missing type hints",
            file_path=Path("test.py"),
            line_number=10,
            suggestion="Add type hints"
        )
        
        assert issue.severity == Severity.ERROR
        assert issue.category == IssueCategory.MISSING_TYPE_HINTS
        assert issue.message == "Function missing type hints"
        assert issue.file_path == Path("test.py")
        assert issue.line_number == 10
        assert issue.suggestion == "Add type hints"
        
    def test_issue_string_representation(self):
        """Test issue string representation."""
        issue = Issue(
            severity=Severity.WARNING,
            category=IssueCategory.BROKEN_REFERENCE,
            message="Broken link found",
            file_path=Path("docs/README.md"),
            line_number=25
        )
        
        str_repr = str(issue)
        assert "[WARNING]" in str_repr
        assert "Broken link found" in str_repr
        assert "docs/README.md:25" in str_repr
        
    def test_issue_without_location(self):
        """Test issue without file location."""
        issue = Issue(
            severity=Severity.INFO,
            category=IssueCategory.VALIDATION_ERROR,
            message="General validation error"
        )
        
        str_repr = str(issue)
        assert "[INFO]" in str_repr
        assert "General validation error" in str_repr
        assert ".py" not in str_repr  # No file path
        
    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = Issue(
            severity=Severity.ERROR,
            category=IssueCategory.SECURITY_PATTERN,
            message="Security issue found",
            file_path=Path("/test/file.py"),
            line_number=42,
            metadata={"pattern": "password=.*"}
        )
        
        data = issue.to_dict()
        assert data["severity"] == "error"
        assert data["category"] == "security_pattern"
        assert data["message"] == "Security issue found"
        assert data["file_path"] == "/test/file.py"
        assert data["line_number"] == 42
        assert data["metadata"]["pattern"] == "password=.*"


class TestFeedback:
    """Test Feedback model."""
    
    def test_create_feedback(self):
        """Test creating feedback."""
        feedback = Feedback(
            severity=Severity.WARNING,
            message="Consider refactoring",
            details="This module is getting complex",
            action_required=True
        )
        
        assert feedback.severity == Severity.WARNING
        assert feedback.message == "Consider refactoring"
        assert feedback.details == "This module is getting complex"
        assert feedback.action_required is True
        
    def test_feedback_string_representation(self):
        """Test feedback string representation."""
        feedback = Feedback(
            severity=Severity.ERROR,
            message="Critical issues found",
            action_required=True
        )
        
        str_repr = str(feedback)
        assert "!" in str_repr  # Action required indicator
        assert "[ERROR]" in str_repr
        assert "Critical issues found" in str_repr
        
    def test_feedback_with_related_issues(self):
        """Test feedback with related issues."""
        issue1 = Issue(
            severity=Severity.ERROR,
            category=IssueCategory.MISSING_TESTS,
            message="No tests found"
        )
        issue2 = Issue(
            severity=Severity.WARNING,
            category=IssueCategory.MISSING_DOCSTRING,
            message="Missing docstring"
        )
        
        feedback = Feedback(
            severity=Severity.ERROR,
            message="Quality issues found",
            related_issues=[issue1, issue2]
        )
        
        assert len(feedback.related_issues) == 2
        assert feedback.related_issues[0] == issue1
        assert feedback.related_issues[1] == issue2


class TestIssueGroup:
    """Test IssueGroup model."""
    
    def test_create_issue_group(self):
        """Test creating an issue group."""
        group = IssueGroup(
            title="Type Hint Issues",
            description="Issues related to missing type hints"
        )
        
        assert group.title == "Type Hint Issues"
        assert group.description == "Issues related to missing type hints"
        assert group.count == 0
        assert group.severity is None
        
    def test_add_issues_to_group(self):
        """Test adding issues to group."""
        group = IssueGroup(title="Compliance Issues")
        
        issue1 = Issue(
            severity=Severity.WARNING,
            category=IssueCategory.MISSING_TYPE_HINTS,
            message="Missing type hints"
        )
        issue2 = Issue(
            severity=Severity.ERROR,
            category=IssueCategory.MISSING_TESTS,
            message="No test file"
        )
        
        group.add_issue(issue1)
        group.add_issue(issue2)
        
        assert group.count == 2
        assert group.severity == Severity.ERROR  # Highest severity
        
    def test_count_by_severity(self):
        """Test counting issues by severity."""
        group = IssueGroup(title="All Issues")
        
        # Add issues of different severities
        for _ in range(3):
            group.add_issue(Issue(
                severity=Severity.WARNING,
                category=IssueCategory.MISSING_DOCSTRING,
                message="Missing docstring"
            ))
        
        for _ in range(2):
            group.add_issue(Issue(
                severity=Severity.ERROR,
                category=IssueCategory.MISSING_TESTS,
                message="Missing tests"
            ))
        
        group.add_issue(Issue(
            severity=Severity.CRITICAL,
            category=IssueCategory.SECURITY_PATTERN,
            message="Security issue"
        ))
        
        counts = group.count_by_severity
        assert counts[Severity.WARNING] == 3
        assert counts[Severity.ERROR] == 2
        assert counts[Severity.CRITICAL] == 1
        assert counts[Severity.INFO] == 0
        
    def test_filter_by_severity(self):
        """Test filtering issues by minimum severity."""
        group = IssueGroup(title="Mixed Issues")
        
        group.add_issue(Issue(
            severity=Severity.INFO,
            category=IssueCategory.MISSING_DOCSTRING,
            message="Info"
        ))
        group.add_issue(Issue(
            severity=Severity.WARNING,
            category=IssueCategory.MISSING_TYPE_HINTS,
            message="Warning"
        ))
        group.add_issue(Issue(
            severity=Severity.ERROR,
            category=IssueCategory.BROKEN_REFERENCE,
            message="Error"
        ))
        
        # Filter for warnings and above
        filtered = group.filter_by_severity(Severity.WARNING)
        assert len(filtered) == 2
        
        # Filter for errors and above
        filtered = group.filter_by_severity(Severity.ERROR)
        assert len(filtered) == 1


class TestValidationResult:
    """Test ValidationResult model."""
    
    def test_create_validation_result(self):
        """Test creating a validation result."""
        result = ValidationResult(
            passed=True,
            message="All checks passed",
            validator_name="ComplianceValidator"
        )
        
        assert result.passed is True
        assert result.message == "All checks passed"
        assert result.validator_name == "ComplianceValidator"
        assert result.timestamp is not None
        
    def test_validation_with_metadata(self):
        """Test validation result with metadata."""
        result = ValidationResult(
            passed=False,
            message="Validation failed",
            validator_name="ReferenceValidator",
            metadata={
                "broken_links": 5,
                "total_links": 20
            }
        )
        
        assert result.passed is False
        assert result.metadata["broken_links"] == 5
        assert result.metadata["total_links"] == 20