"""Issue and feedback models for docpipe analysis results."""

from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for issues and feedback."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"
    
    def __lt__(self, other: "Severity") -> bool:
        """Compare severity levels for sorting."""
        order = [self.HINT, self.INFO, self.WARNING, self.ERROR, self.CRITICAL]
        return order.index(self) < order.index(other)


class IssueCategory(str, Enum):
    """Categories for different types of issues."""
    # Compliance issues
    MISSING_TYPE_HINTS = "missing_type_hints"
    MISSING_DOCSTRING = "missing_docstring"
    MISSING_TESTS = "missing_tests"
    HIGH_COMPLEXITY = "high_complexity"
    SECURITY_PATTERN = "security_pattern"
    FORBIDDEN_PATTERN = "forbidden_pattern"
    FILE_TOO_LONG = "file_too_long"
    
    # Reference issues
    BROKEN_REFERENCE = "broken_reference"
    MISSING_FILE = "missing_file"
    CIRCULAR_REFERENCE = "circular_reference"
    ORPHANED_DOCUMENT = "orphaned_document"
    
    # Similarity issues
    DUPLICATE_CONTENT = "duplicate_content"
    NEAR_DUPLICATE = "near_duplicate"
    REDUNDANT_DOCUMENTATION = "redundant_documentation"
    
    # Structure issues
    INVALID_STRUCTURE = "invalid_structure"
    MISSING_SECTION = "missing_section"
    INCONSISTENT_FORMAT = "inconsistent_format"
    
    # General issues
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"


class Issue(BaseModel):
    """Represents a single issue found during analysis."""
    
    severity: Severity = Field(
        ...,
        description="Severity level of the issue"
    )
    category: IssueCategory = Field(
        ...,
        description="Category of the issue"
    )
    message: str = Field(
        ...,
        description="Human-readable description of the issue"
    )
    file_path: Optional[Path] = Field(
        None,
        description="Path to the file where the issue was found"
    )
    line_number: Optional[int] = Field(
        None,
        description="Line number where the issue occurs"
    )
    column_number: Optional[int] = Field(
        None,
        description="Column number where the issue occurs"
    )
    suggestion: Optional[str] = Field(
        None,
        description="Suggested fix for the issue"
    )
    code_snippet: Optional[str] = Field(
        None,
        description="Relevant code snippet"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the issue"
    )
    
    def __str__(self) -> str:
        """String representation of the issue."""
        location = ""
        if self.file_path:
            location = f" in {self.file_path}"
            if self.line_number:
                location += f":{self.line_number}"
                if self.column_number:
                    location += f":{self.column_number}"
        
        return f"[{self.severity.value.upper()}] {self.message}{location}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = self.model_dump(exclude_none=True)
        if self.file_path:
            data['file_path'] = str(self.file_path)
        return data
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        arbitrary_types_allowed = True


class Feedback(BaseModel):
    """User-friendly feedback message."""
    
    severity: Severity = Field(
        ...,
        description="Severity level of the feedback"
    )
    message: str = Field(
        ...,
        description="User-friendly feedback message"
    )
    details: Optional[str] = Field(
        None,
        description="Additional details or context"
    )
    action_required: bool = Field(
        False,
        description="Whether user action is required"
    )
    related_issues: List[Issue] = Field(
        default_factory=list,
        description="Related issues that contribute to this feedback"
    )
    
    def __str__(self) -> str:
        """String representation of feedback."""
        prefix = "!" if self.action_required else ""
        return f"{prefix}[{self.severity.value.upper()}] {self.message}"
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class IssueGroup(BaseModel):
    """Groups related issues together."""
    
    title: str = Field(..., description="Title of the issue group")
    description: Optional[str] = Field(None, description="Description of the group")
    issues: List[Issue] = Field(default_factory=list, description="Issues in this group")
    severity: Optional[Severity] = Field(None, description="Overall severity of the group")
    
    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the group."""
        self.issues.append(issue)
        # Update group severity to highest issue severity
        if not self.severity or issue.severity > self.severity:
            self.severity = issue.severity
    
    @property
    def count(self) -> int:
        """Number of issues in the group."""
        return len(self.issues)
    
    @property
    def count_by_severity(self) -> Dict[Severity, int]:
        """Count issues by severity."""
        counts = {s: 0 for s in Severity}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts
    
    def filter_by_severity(self, min_severity: Severity) -> List[Issue]:
        """Get issues with at least the specified severity."""
        return [i for i in self.issues if i.severity >= min_severity]
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of a validation check."""
    
    passed: bool = Field(..., description="Whether the validation passed")
    message: str = Field(..., description="Validation message")
    timestamp: datetime = Field(default_factory=datetime.now)
    validator_name: str = Field(..., description="Name of the validator")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True