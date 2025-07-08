"""Custom exceptions for docpipe."""


class DocPipeError(Exception):
    """Base exception for all docpipe errors."""
    pass


class ConfigurationError(DocPipeError):
    """Raised when configuration is invalid."""
    pass


class AnalysisError(DocPipeError):
    """Raised when analysis fails."""
    pass


class ValidationError(DocPipeError):
    """Raised when validation fails."""
    pass


class FileNotFoundError(DocPipeError):
    """Raised when a required file is not found."""
    pass


class DependencyError(DocPipeError):
    """Raised when a required dependency is missing."""
    pass


class ExportError(DocPipeError):
    """Raised when export operation fails."""
    pass