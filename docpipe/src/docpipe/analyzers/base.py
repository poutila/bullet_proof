"""Base classes and protocols for docpipe analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, TypeVar

from ..models import Issue, ValidationResult

T = TypeVar('T')


@dataclass
class AnalyzerResult(Generic[T]):
    """Base result class for all analyzers."""

    analyzer_name: str
    success: bool
    duration_seconds: float
    data: T
    issues: List[Issue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        from ..models import Severity
        return any(issue.severity == Severity.CRITICAL for issue in self.issues)


class Analyzer(Protocol):
    """Protocol defining the analyzer interface."""

    @property
    def name(self) -> str:
        """Get the analyzer name."""
        ...

    @property
    def description(self) -> str:
        """Get the analyzer description."""
        ...

    def analyze(self, path: Path) -> AnalyzerResult:
        """
        Run analysis on the given path.

        Args:
            path: Path to analyze (file or directory)

        Returns:
            AnalyzerResult with analysis data
        """
        ...

    def validate_config(self) -> List[str]:
        """
        Validate analyzer configuration.

        Returns:
            List of validation warnings (empty if valid)
        """
        ...


class BaseAnalyzer(ABC):
    """Abstract base class for analyzers with common functionality."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize analyzer with optional configuration.

        Args:
            config: Analyzer-specific configuration
        """
        self.config = config or {}
        self._start_time: Optional[float] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the analyzer name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the analyzer description."""
        pass

    @abstractmethod
    def _analyze_impl(self, path: Path) -> Any:
        """
        Implement the actual analysis logic.

        Args:
            path: Path to analyze

        Returns:
            Analysis-specific data
        """
        pass

    def analyze(self, path: Path) -> AnalyzerResult:
        """
        Run analysis with timing and error handling.

        Args:
            path: Path to analyze

        Returns:
            AnalyzerResult with analysis data
        """
        import time

        self._start_time = time.time()
        issues: List[Issue] = []

        try:
            # Validate path
            if not path.exists():
                raise FileNotFoundError(f"Path does not exist: {path}")

            # Run implementation
            data = self._analyze_impl(path)

            # Create result
            duration = time.time() - self._start_time
            return AnalyzerResult(
                analyzer_name=self.name,
                success=True,
                duration_seconds=duration,
                data=data,
                issues=issues
            )

        except Exception as e:
            # Handle errors gracefully
            duration = time.time() - self._start_time
            from ..models import IssueCategory, Severity

            issues.append(Issue(
                severity=Severity.ERROR,
                category=IssueCategory.VALIDATION_ERROR,
                message=f"Analysis failed: {str(e)}",
                file_path=path if path.is_file() else None
            ))

            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                duration_seconds=duration,
                data=None,
                issues=issues,
                metadata={"error": str(e)}
            )

    def validate_config(self) -> List[str]:
        """
        Validate analyzer configuration.

        Returns:
            List of validation warnings
        """
        # Base implementation - can be overridden
        return []

    def _should_exclude(self, path: Path, exclude_patterns: List[str]) -> bool:
        """Check if path should be excluded based on patterns."""
        import fnmatch

        path_str = str(path)
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also check individual path components
            for part in path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False


class CompositeAnalyzer(BaseAnalyzer):
    """Analyzer that runs multiple sub-analyzers."""

    def __init__(self, analyzers: List[Analyzer], config: Optional[Dict[str, Any]] = None):
        """
        Initialize with a list of analyzers.

        Args:
            analyzers: List of analyzers to run
            config: Optional configuration
        """
        super().__init__(config)
        self.analyzers = analyzers

    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "CompositeAnalyzer"

    @property
    def description(self) -> str:
        """Get analyzer description."""
        analyzer_names = [a.name for a in self.analyzers]
        return f"Runs multiple analyzers: {', '.join(analyzer_names)}"

    def _analyze_impl(self, path: Path) -> Dict[str, AnalyzerResult]:
        """
        Run all sub-analyzers.

        Args:
            path: Path to analyze

        Returns:
            Dictionary of analyzer name to result
        """
        results = {}

        for analyzer in self.analyzers:
            if self._should_run_analyzer(analyzer):
                result = analyzer.analyze(path)
                results[analyzer.name] = result

        return results

    def _should_run_analyzer(self, analyzer: Analyzer) -> bool:
        """Check if analyzer should run based on configuration."""
        # Can be overridden to add conditional logic
        if "enabled_analyzers" in self.config:
            return analyzer.name in self.config["enabled_analyzers"]
        if "disabled_analyzers" in self.config:
            return analyzer.name not in self.config["disabled_analyzers"]
        return True

    def validate_config(self) -> List[str]:
        """Validate configuration for all analyzers."""
        warnings = []

        for analyzer in self.analyzers:
            analyzer_warnings = analyzer.validate_config()
            for warning in analyzer_warnings:
                warnings.append(f"{analyzer.name}: {warning}")

        return warnings


class FileAnalyzer(BaseAnalyzer):
    """Base class for analyzers that process individual files."""

    @abstractmethod
    def _analyze_file(self, file_path: Path) -> Any:
        """
        Analyze a single file.

        Args:
            file_path: Path to the file

        Returns:
            File-specific analysis data
        """
        pass

    def _analyze_impl(self, path: Path) -> Any:
        """
        Implement analysis for files and directories.

        Args:
            path: Path to analyze

        Returns:
            Analysis data
        """
        if path.is_file():
            return self._analyze_file(path)
        elif path.is_dir():
            return self._analyze_directory(path)
        else:
            raise ValueError(f"Path is neither file nor directory: {path}")

    def _analyze_directory(self, dir_path: Path) -> Dict[str, Any]:
        """
        Analyze all files in a directory.

        Args:
            dir_path: Directory path

        Returns:
            Dictionary with file results
        """
        results = {}
        exclude_patterns = self.config.get("exclude_patterns", [])

        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and not self._should_exclude(file_path, exclude_patterns):
                if self._should_process_file(file_path):
                    try:
                        results[str(file_path)] = self._analyze_file(file_path)
                    except Exception as e:
                        # Log error but continue processing
                        results[str(file_path)] = {"error": str(e)}

        return results

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Check if file should be processed.

        Can be overridden by subclasses to add file type filtering.

        Args:
            file_path: File path to check

        Returns:
            True if file should be processed
        """
        return True


# Type aliases for convenience
AnalyzerFactory = Callable[[Dict[str, Any]], Analyzer]
AnalyzerRegistry = Dict[str, AnalyzerFactory]