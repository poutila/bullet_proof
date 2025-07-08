"""Data models for docpipe."""

from .config import AnalysisConfig
from .issues import (
    Issue,
    Feedback,
    IssueGroup,
    Severity,
    IssueCategory,
    ValidationResult,
)
from .results import (
    AnalysisResults,
    ComplianceResults,
    SimilarityResults,
    ReferenceResults,
    InstructionResults,
    DocumentInfo,
    SimilarDocumentPair,
    ReferenceInfo,
)

__all__ = [
    # Configuration
    "AnalysisConfig",
    
    # Issues and feedback
    "Issue",
    "Feedback", 
    "IssueGroup",
    "Severity",
    "IssueCategory",
    "ValidationResult",
    
    # Results
    "AnalysisResults",
    "ComplianceResults",
    "SimilarityResults",
    "ReferenceResults",
    "InstructionResults",
    
    # Data structures
    "DocumentInfo",
    "SimilarDocumentPair",
    "ReferenceInfo",
]