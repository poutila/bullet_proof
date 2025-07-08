"""Result models for docpipe analysis."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field, computed_field

from .issues import Issue, Feedback, IssueGroup, Severity, ValidationResult
from .config import AnalysisConfig


class DocumentInfo(BaseModel):
    """Information about a single document."""
    
    path: Path = Field(..., description="Path to the document")
    size_bytes: int = Field(..., description="Size of the document in bytes")
    lines: int = Field(..., description="Number of lines in the document")
    type: str = Field(..., description="Document type (e.g., 'markdown', 'claude')")
    last_modified: datetime = Field(..., description="Last modification time")
    encoding: str = Field("utf-8", description="File encoding")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class SimilarDocumentPair(BaseModel):
    """Represents a pair of similar documents."""
    
    source: Path = Field(..., description="Source document path")
    target: Path = Field(..., description="Target document path")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    similarity_method: str = Field(..., description="Method used for similarity calculation")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @computed_field
    @property
    def is_duplicate(self) -> bool:
        """Check if documents are duplicates (>95% similar)."""
        return self.similarity_score >= 0.95
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class ReferenceInfo(BaseModel):
    """Information about a document reference."""
    
    source_file: Path = Field(..., description="File containing the reference")
    target_file: Path = Field(..., description="Referenced file")
    line_number: int = Field(..., description="Line number of the reference")
    reference_text: str = Field(..., description="Text of the reference")
    is_valid: bool = Field(..., description="Whether the reference is valid")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class ComplianceResults(BaseModel):
    """Results from compliance checking."""
    
    files_checked: int = Field(0, description="Number of files checked")
    files_compliant: int = Field(0, description="Number of compliant files")
    issues: List[Issue] = Field(default_factory=list)
    issue_groups: Dict[str, IssueGroup] = Field(default_factory=dict)
    coverage_percentage: Optional[float] = Field(None, description="Test coverage percentage")
    
    @computed_field
    @property
    def compliance_score(self) -> float:
        """Calculate compliance score as percentage."""
        if self.files_checked == 0:
            return 100.0
        return (self.files_compliant / self.files_checked) * 100.0
    
    @computed_field
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(i.severity == Severity.CRITICAL for i in self.issues)
    
    def add_issue(self, issue: Issue, group_name: Optional[str] = None) -> None:
        """Add an issue to the results."""
        self.issues.append(issue)
        if group_name:
            if group_name not in self.issue_groups:
                self.issue_groups[group_name] = IssueGroup(title=group_name)
            self.issue_groups[group_name].add_issue(issue)


class SimilarityResults(BaseModel):
    """Results from similarity analysis."""
    
    documents_analyzed: int = Field(0, description="Number of documents analyzed")
    similar_pairs: List[SimilarDocumentPair] = Field(default_factory=list)
    duplicate_groups: List[List[Path]] = Field(default_factory=list)
    similarity_matrix: Optional[Dict[str, Dict[str, float]]] = Field(None)
    
    @computed_field
    @property
    def duplicate_count(self) -> int:
        """Number of duplicate documents found."""
        return sum(1 for pair in self.similar_pairs if pair.is_duplicate)
    
    @computed_field
    @property
    def similar_count(self) -> int:
        """Number of similar (but not duplicate) documents found."""
        return len(self.similar_pairs) - self.duplicate_count
    
    def get_similar_to(self, document: Path, threshold: float = 0.0) -> List[SimilarDocumentPair]:
        """Get all documents similar to the given document."""
        results = []
        doc_str = str(document)
        for pair in self.similar_pairs:
            if str(pair.source) == doc_str or str(pair.target) == doc_str:
                if pair.similarity_score >= threshold:
                    results.append(pair)
        return sorted(results, key=lambda x: x.similarity_score, reverse=True)


class ReferenceResults(BaseModel):
    """Results from reference validation."""
    
    references_found: int = Field(0, description="Total references found")
    valid_references: int = Field(0, description="Number of valid references")
    broken_references: List[ReferenceInfo] = Field(default_factory=list)
    orphaned_documents: List[Path] = Field(default_factory=list)
    reference_graph: Optional[Dict[str, List[str]]] = Field(None)
    
    @computed_field
    @property
    def validation_score(self) -> float:
        """Calculate validation score as percentage."""
        if self.references_found == 0:
            return 100.0
        return (self.valid_references / self.references_found) * 100.0
    
    @computed_field
    @property
    def has_broken_references(self) -> bool:
        """Check if there are any broken references."""
        return len(self.broken_references) > 0


class InstructionResults(BaseModel):
    """Results from instruction path tracing."""
    
    documents_traced: int = Field(0, description="Number of documents traced")
    instruction_paths: Dict[str, List[str]] = Field(default_factory=dict)
    missing_files: List[str] = Field(default_factory=list)
    coverage_percentage: float = Field(0.0, description="Instruction coverage percentage")
    must_have_files: List[str] = Field(default_factory=list)
    
    def add_path(self, start: str, path: List[str]) -> None:
        """Add an instruction path."""
        self.instruction_paths[start] = path
    
    def get_all_referenced_files(self) -> Set[str]:
        """Get all files referenced in instruction paths."""
        files = set()
        for path in self.instruction_paths.values():
            files.update(path)
        return files


class AnalysisResults(BaseModel):
    """Combined results from all analyses."""
    
    # Metadata
    project_path: Path = Field(..., description="Path to analyzed project")
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_seconds: float = Field(0.0, description="Analysis duration in seconds")
    config: AnalysisConfig = Field(..., description="Configuration used for analysis")
    
    # Document information
    documents: List[DocumentInfo] = Field(default_factory=list)
    total_documents: int = Field(0, description="Total documents analyzed")
    
    # Analysis results
    compliance: Optional[ComplianceResults] = None
    similarity: Optional[SimilarityResults] = None
    references: Optional[ReferenceResults] = None
    instructions: Optional[InstructionResults] = None
    
    # Aggregated results
    all_issues: List[Issue] = Field(default_factory=list)
    feedback: List[Feedback] = Field(default_factory=list)
    validation_results: List[ValidationResult] = Field(default_factory=list)
    
    # Quick access properties
    @computed_field
    @property
    def missing_references(self) -> List[str]:
        """Get all missing references."""
        if not self.references:
            return []
        return [str(ref.target_file) for ref in self.references.broken_references]
    
    @computed_field
    @property
    def must_have_files(self) -> List[str]:
        """Get must-have files from instruction analysis."""
        if not self.instructions:
            return []
        return self.instructions.must_have_files
    
    @computed_field
    @property
    def similar_documents(self) -> List[SimilarDocumentPair]:
        """Get all similar document pairs."""
        if not self.similarity:
            return []
        return self.similarity.similar_pairs
    
    @computed_field
    @property
    def compliance_score(self) -> float:
        """Get overall compliance score."""
        if not self.compliance:
            return 100.0
        return self.compliance.compliance_score
    
    @computed_field
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(i.severity == Severity.CRITICAL for i in self.all_issues)
    
    @computed_field
    @property
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis results."""
        summary = {
            "project_path": str(self.project_path),
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "total_documents": self.total_documents,
            "critical_issues": sum(1 for i in self.all_issues if i.severity == Severity.CRITICAL),
            "errors": sum(1 for i in self.all_issues if i.severity == Severity.ERROR),
            "warnings": sum(1 for i in self.all_issues if i.severity == Severity.WARNING),
        }
        
        if self.compliance:
            summary["compliance_score"] = self.compliance_score
            summary["files_checked"] = self.compliance.files_checked
            
        if self.similarity:
            summary["duplicate_documents"] = self.similarity.duplicate_count
            summary["similar_documents"] = self.similarity.similar_count
            
        if self.references:
            summary["broken_references"] = len(self.references.broken_references)
            summary["orphaned_documents"] = len(self.references.orphaned_documents)
            
        if self.instructions:
            summary["instruction_coverage"] = self.instructions.coverage_percentage
            summary["missing_files"] = len(self.instructions.missing_files)
        
        return summary
    
    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the results."""
        self.all_issues.append(issue)
        
        # Also add to specific results if applicable
        if issue.category.value.startswith("missing_") or issue.category.value.startswith("forbidden_"):
            if self.compliance:
                self.compliance.issues.append(issue)
    
    def add_feedback(self, feedback: Feedback) -> None:
        """Add feedback to the results."""
        self.feedback.append(feedback)
    
    def export(self, path: Path, format: Optional[str] = None) -> None:
        """Export results to file."""
        format = format or self.config.output_format
        
        if format == "json":
            self._export_json(path)
        elif format == "csv":
            self._export_csv(path)
        elif format == "excel":
            self._export_excel(path)
        elif format == "markdown":
            self._export_markdown(path)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_json(self, path: Path) -> None:
        """Export to JSON format."""
        import json
        
        data = self.model_dump(exclude_none=True)
        # Convert Path objects to strings
        data = self._convert_paths_to_strings(data)
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _export_csv(self, path: Path) -> None:
        """Export to CSV format."""
        import csv
        
        # Export issues as CSV
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'severity', 'category', 'message', 'file_path', 
                'line_number', 'suggestion'
            ])
            writer.writeheader()
            for issue in self.all_issues:
                writer.writerow({
                    'severity': issue.severity.value,
                    'category': issue.category.value,
                    'message': issue.message,
                    'file_path': str(issue.file_path) if issue.file_path else '',
                    'line_number': issue.line_number or '',
                    'suggestion': issue.suggestion or ''
                })
    
    def _export_excel(self, path: Path) -> None:
        """Export to Excel format."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for Excel export: pip install docpipe[data]")
        
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([self.summary])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Issues sheet
            if self.all_issues:
                issues_data = []
                for issue in self.all_issues:
                    issues_data.append({
                        'Severity': issue.severity.value,
                        'Category': issue.category.value,
                        'Message': issue.message,
                        'File': str(issue.file_path) if issue.file_path else '',
                        'Line': issue.line_number or '',
                        'Suggestion': issue.suggestion or ''
                    })
                issues_df = pd.DataFrame(issues_data)
                issues_df.to_excel(writer, sheet_name='Issues', index=False)
            
            # Similar documents sheet
            if self.similarity and self.similarity.similar_pairs:
                sim_data = []
                for pair in self.similarity.similar_pairs:
                    sim_data.append({
                        'Source': str(pair.source),
                        'Target': str(pair.target),
                        'Similarity': pair.similarity_score,
                        'Method': pair.similarity_method,
                        'Is Duplicate': pair.is_duplicate
                    })
                sim_df = pd.DataFrame(sim_data)
                sim_df.to_excel(writer, sheet_name='Similar Documents', index=False)
    
    def _export_markdown(self, path: Path) -> None:
        """Export to Markdown format."""
        lines = [
            f"# Analysis Results",
            f"",
            f"**Project:** {self.project_path}",
            f"**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {self.duration_seconds:.2f} seconds",
            f"",
            f"## Summary",
            f"",
        ]
        
        for key, value in self.summary.items():
            lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        
        if self.all_issues:
            lines.extend([
                "",
                "## Issues",
                "",
            ])
            
            # Group issues by severity
            by_severity = {}
            for issue in self.all_issues:
                sev = issue.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(issue)
            
            for severity in [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]:
                if severity.value in by_severity:
                    lines.append(f"### {severity.value.title()}")
                    lines.append("")
                    for issue in by_severity[severity.value]:
                        location = ""
                        if issue.file_path:
                            location = f" (`{issue.file_path}`"
                            if issue.line_number:
                                location += f":{issue.line_number}"
                            location += ")"
                        lines.append(f"- {issue.message}{location}")
                    lines.append("")
        
        if self.feedback:
            lines.extend([
                "## Feedback",
                "",
            ])
            for fb in self.feedback:
                prefix = "⚠️ " if fb.action_required else ""
                lines.append(f"- {prefix}**{fb.severity.value.upper()}:** {fb.message}")
                if fb.details:
                    lines.append(f"  - {fb.details}")
            lines.append("")
        
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
    
    def _convert_paths_to_strings(self, data: Any) -> Any:
        """Recursively convert Path objects to strings."""
        if isinstance(data, Path):
            return str(data)
        elif isinstance(data, dict):
            return {k: self._convert_paths_to_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_paths_to_strings(item) for item in data]
        return data
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True