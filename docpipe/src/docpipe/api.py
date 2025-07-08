"""Main API for docpipe package."""

import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import logging

from .models import (
    AnalysisConfig,
    AnalysisResults,
    ComplianceResults,
    SimilarityResults,
    ReferenceResults,
    InstructionResults,
    DocumentInfo,
    Issue,
    Feedback,
    Severity,
)
from .core.engine import AnalysisEngine
from .core.exceptions import DocPipeError, ConfigurationError

# Set up logging
logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[float, str], None]


def analyze_project(
    path: str | Path,
    config: Optional[AnalysisConfig] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> AnalysisResults:
    """
    Analyze a project for documentation quality, compliance, and consistency.
    
    This is the main entry point for docpipe analysis. It runs all configured
    analyses and returns a comprehensive result object.
    
    Args:
        path: Path to the project directory to analyze
        config: Configuration for the analysis (uses defaults if not provided)
        progress_callback: Optional callback function for progress updates.
                          Called with (percentage, message) parameters.
    
    Returns:
        AnalysisResults object containing all analysis results
        
    Raises:
        DocPipeError: If analysis fails
        ConfigurationError: If configuration is invalid
        
    Example:
        >>> results = analyze_project("/path/to/project")
        >>> print(f"Compliance score: {results.compliance_score}%")
        >>> print(f"Found {len(results.missing_references)} missing references")
        
    Example with progress:
        >>> def show_progress(pct, msg):
        ...     print(f"[{pct:3.0f}%] {msg}")
        >>> results = analyze_project("/path/to/project", progress_callback=show_progress)
    """
    # Convert to Path object
    project_path = Path(path).resolve()
    
    # Validate path exists
    if not project_path.exists():
        raise DocPipeError(f"Project path does not exist: {project_path}")
    
    if not project_path.is_dir():
        raise DocPipeError(f"Project path is not a directory: {project_path}")
    
    # Use default config if not provided
    if config is None:
        config = AnalysisConfig()
    
    # Set root path if not specified
    if config.root_path is None:
        config.root_path = project_path
    
    # Create DocPipe instance and run analysis
    pipeline = DocPipe(config)
    return pipeline.analyze(project_path, progress_callback)


class DocPipe:
    """
    Main class for document analysis pipeline.
    
    This class provides a flexible interface for running document analyses
    with full control over configuration and execution.
    
    Attributes:
        config: Analysis configuration
        engine: Internal analysis engine
        
    Example:
        >>> config = AnalysisConfig(similarity_threshold=0.8)
        >>> pipeline = DocPipe(config)
        >>> results = pipeline.analyze("/path/to/project")
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        Initialize DocPipe with configuration.
        
        Args:
            config: Analysis configuration (uses defaults if not provided)
        """
        self.config = config or AnalysisConfig()
        self.engine = AnalysisEngine(self.config)
        self._start_time: Optional[float] = None
        
    def analyze(
        self,
        path: Path | str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> AnalysisResults:
        """
        Run complete analysis pipeline on a project.
        
        Args:
            path: Path to analyze
            progress_callback: Optional progress callback
            
        Returns:
            Complete analysis results
            
        Raises:
            DocPipeError: If analysis fails
        """
        self._start_time = time.time()
        project_path = Path(path).resolve()
        
        # Initialize results
        results = AnalysisResults(
            project_path=project_path,
            timestamp=datetime.now(),
            config=self.config
        )
        
        try:
            # Progress tracking
            total_steps = sum([
                self.config.check_compliance,
                self.config.analyze_similarity,
                self.config.validate_references,
                self.config.trace_instructions,
                self.config.check_structure,
            ])
            current_step = 0
            
            def update_progress(message: str) -> None:
                nonlocal current_step
                if progress_callback:
                    percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0
                    progress_callback(percentage, message)
                current_step += 1
            
            # Discover documents
            update_progress("Discovering documents...")
            documents = self.engine.discover_documents(project_path)
            results.documents = documents
            results.total_documents = len(documents)
            
            # Run compliance checks
            if self.config.check_compliance:
                update_progress("Checking compliance...")
                results.compliance = self.analyze_compliance(project_path)
                results.all_issues.extend(results.compliance.issues)
            
            # Run similarity analysis
            if self.config.analyze_similarity:
                update_progress("Analyzing document similarity...")
                results.similarity = self.analyze_similarity(project_path)
            
            # Validate references
            if self.config.validate_references:
                update_progress("Validating references...")
                results.references = self.analyze_references(project_path)
            
            # Trace instructions
            if self.config.trace_instructions:
                update_progress("Tracing instruction paths...")
                results.instructions = self.analyze_instructions(project_path)
            
            # Check structure
            if self.config.check_structure:
                update_progress("Checking structural soundness...")
                structure_issues = self.engine.check_structure(project_path)
                results.all_issues.extend(structure_issues)
            
            # Generate feedback
            update_progress("Generating feedback...")
            results.feedback = self._generate_feedback(results)
            
            # Final progress update
            if progress_callback:
                progress_callback(100.0, "Analysis complete!")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise DocPipeError(f"Analysis failed: {e}") from e
        
        finally:
            # Record duration
            if self._start_time:
                results.duration_seconds = time.time() - self._start_time
        
        return results
    
    def analyze_compliance(self, path: Path) -> ComplianceResults:
        """
        Run compliance analysis only.
        
        Args:
            path: Path to analyze
            
        Returns:
            Compliance analysis results
        """
        return self.engine.analyze_compliance(path)
    
    def analyze_similarity(self, path: Path) -> SimilarityResults:
        """
        Run similarity analysis only.
        
        Args:
            path: Path to analyze
            
        Returns:
            Similarity analysis results
        """
        return self.engine.analyze_similarity(path)
    
    def analyze_references(self, path: Path) -> ReferenceResults:
        """
        Run reference validation only.
        
        Args:
            path: Path to analyze
            
        Returns:
            Reference validation results
        """
        return self.engine.analyze_references(path)
    
    def analyze_instructions(self, path: Path) -> InstructionResults:
        """
        Run instruction path tracing only.
        
        Args:
            path: Path to analyze
            
        Returns:
            Instruction tracing results
        """
        return self.engine.analyze_instructions(path)
    
    def _generate_feedback(self, results: AnalysisResults) -> List[Feedback]:
        """Generate user-friendly feedback based on results."""
        feedback = []
        
        # Compliance feedback
        if results.compliance:
            if results.compliance.has_critical_issues:
                feedback.append(Feedback(
                    severity=Severity.CRITICAL,
                    message="Critical compliance issues found that must be fixed",
                    action_required=True
                ))
            elif results.compliance.compliance_score < 80:
                feedback.append(Feedback(
                    severity=Severity.WARNING,
                    message=f"Compliance score is {results.compliance.compliance_score:.1f}% (below 80% threshold)",
                    details="Review and fix compliance issues to improve code quality",
                    action_required=True
                ))
            else:
                feedback.append(Feedback(
                    severity=Severity.INFO,
                    message=f"Good compliance score: {results.compliance.compliance_score:.1f}%"
                ))
        
        # Similarity feedback
        if results.similarity:
            if results.similarity.duplicate_count > 0:
                feedback.append(Feedback(
                    severity=Severity.WARNING,
                    message=f"Found {results.similarity.duplicate_count} duplicate documents",
                    details="Consider consolidating duplicate content",
                    action_required=True
                ))
            if results.similarity.similar_count > 5:
                feedback.append(Feedback(
                    severity=Severity.INFO,
                    message=f"Found {results.similarity.similar_count} similar documents",
                    details="Review for potential consolidation opportunities"
                ))
        
        # Reference feedback
        if results.references:
            if results.references.has_broken_references:
                feedback.append(Feedback(
                    severity=Severity.ERROR,
                    message=f"Found {len(results.references.broken_references)} broken references",
                    details="Fix broken links to ensure documentation integrity",
                    action_required=True
                ))
            if results.references.orphaned_documents:
                feedback.append(Feedback(
                    severity=Severity.WARNING,
                    message=f"Found {len(results.references.orphaned_documents)} orphaned documents",
                    details="These documents are not referenced anywhere"
                ))
        
        # Instruction feedback
        if results.instructions:
            if results.instructions.missing_files:
                feedback.append(Feedback(
                    severity=Severity.ERROR,
                    message=f"Found {len(results.instructions.missing_files)} missing required files",
                    details="Create these files to complete the documentation",
                    action_required=True
                ))
            if results.instructions.coverage_percentage < 80:
                feedback.append(Feedback(
                    severity=Severity.WARNING,
                    message=f"Instruction coverage is {results.instructions.coverage_percentage:.1f}% (below 80% threshold)",
                    details="Improve documentation coverage"
                ))
        
        # Overall feedback
        if not results.has_critical_issues and len(results.all_issues) == 0:
            feedback.append(Feedback(
                severity=Severity.INFO,
                message="Excellent! No issues found in the documentation.",
                details="Your documentation is well-structured and compliant"
            ))
        
        return feedback
    
    def get_features(self) -> Dict[str, bool]:
        """
        Get available features based on installed dependencies.
        
        Returns:
            Dictionary of feature names and their availability
        """
        from . import FEATURES
        return FEATURES.copy()
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []
        
        # Check semantic similarity availability
        if self.config.similarity_method in ["semantic", "both"]:
            from . import HAS_SEMANTIC_SIMILARITY
            if not HAS_SEMANTIC_SIMILARITY:
                warnings.append(
                    "Semantic similarity requested but sentence-transformers not installed. "
                    "Install with: pip install docpipe[ml]"
                )
        
        # Check export format availability
        if self.config.output_format == "excel":
            from . import HAS_PANDAS
            if not HAS_PANDAS:
                warnings.append(
                    "Excel export requested but pandas not installed. "
                    "Install with: pip install docpipe[data]"
                )
        
        # Check path validity
        if self.config.root_path and not self.config.root_path.exists():
            warnings.append(f"Configured root path does not exist: {self.config.root_path}")
        
        return warnings


# Re-export key classes for convenience
__all__ = [
    "analyze_project",
    "DocPipe",
    "AnalysisConfig",
    "AnalysisResults",
    "ProgressCallback",
]