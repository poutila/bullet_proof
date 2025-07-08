"""Configuration models for docpipe analysis."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class AnalysisConfig(BaseModel):
    """Configuration for document analysis pipeline.
    
    This class defines all configuration options for the docpipe analysis engine.
    It provides sensible defaults while allowing full customization.
    """
    
    # General settings
    root_path: Optional[Path] = Field(
        None,
        description="Root path for analysis. If not provided, current directory is used."
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [
            "*.venv*", 
            "*__pycache__*", 
            "*.git*",
            "*node_modules*",
            "*.pytest_cache*",
            "*.mypy_cache*",
            "*dist*",
            "*build*",
            "*.egg-info*",
        ],
        description="Glob patterns for paths to exclude from analysis"
    )
    include_not_in_use: bool = Field(
        False,
        description="Include documents in 'not_in_use' directories"
    )
    
    # Analysis toggles
    check_compliance: bool = Field(True, description="Run compliance checks")
    analyze_similarity: bool = Field(True, description="Run similarity analysis")
    validate_references: bool = Field(True, description="Validate document references")
    trace_instructions: bool = Field(True, description="Trace instruction paths")
    check_structure: bool = Field(True, description="Check structural soundness")
    
    # Compliance settings
    compliance_rules: str = Field(
        "CLAUDE.md",
        description="Name of the file containing compliance rules"
    )
    max_file_lines: int = Field(
        500,
        description="Maximum allowed lines in a Python file"
    )
    min_test_coverage: float = Field(
        90.0,
        description="Minimum required test coverage percentage"
    )
    max_complexity: int = Field(
        10,
        description="Maximum allowed cyclomatic complexity"
    )
    min_type_hint_coverage: float = Field(
        80.0,
        description="Minimum required type hint coverage percentage"
    )
    
    # Similarity settings
    similarity_method: str = Field(
        "semantic",
        description="Similarity calculation method: 'string', 'semantic', or 'both'"
    )
    similarity_threshold: float = Field(
        0.75,
        description="Minimum similarity score to consider documents similar"
    )
    similarity_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        description="Model to use for semantic similarity (if available)"
    )
    enable_clustering: bool = Field(
        True,
        description="Enable clustering of similar documents"
    )
    
    # Reference validation settings
    check_external_links: bool = Field(
        False,
        description="Validate external HTTP/HTTPS links"
    )
    check_images: bool = Field(
        True,
        description="Validate image references"
    )
    check_anchors: bool = Field(
        True,
        description="Validate internal anchor links"
    )
    
    # Output settings
    output_format: str = Field(
        "json",
        description="Default output format: json, csv, excel, markdown"
    )
    verbose: bool = Field(
        False,
        description="Enable verbose output"
    )
    include_file_contents: bool = Field(
        False,
        description="Include file contents in results (increases output size)"
    )
    
    # Performance settings
    max_file_size_mb: float = Field(
        10.0,
        description="Maximum file size to process in megabytes"
    )
    parallel_processing: bool = Field(
        True,
        description="Enable parallel processing for better performance"
    )
    batch_size: int = Field(
        50,
        description="Number of files to process in each batch"
    )
    
    @validator("similarity_method")
    def validate_similarity_method(cls, v: str) -> str:
        """Validate similarity method."""
        valid_methods = {"string", "semantic", "both"}
        if v not in valid_methods:
            raise ValueError(f"similarity_method must be one of {valid_methods}")
        return v
    
    @validator("output_format")
    def validate_output_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = {"json", "csv", "excel", "markdown"}
        if v not in valid_formats:
            raise ValueError(f"output_format must be one of {valid_formats}")
        return v
    
    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v: float) -> float:
        """Validate similarity threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v
    
    @validator("min_test_coverage")
    def validate_test_coverage(cls, v: float) -> float:
        """Validate test coverage is between 0 and 100."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("min_test_coverage must be between 0.0 and 100.0")
        return v
    
    @validator("min_type_hint_coverage")
    def validate_type_hint_coverage(cls, v: float) -> float:
        """Validate type hint coverage is between 0 and 100."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("min_type_hint_coverage must be between 0.0 and 100.0")
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Disallow extra fields
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump(exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisConfig":
        """Create config from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_file(cls, path: Path) -> "AnalysisConfig":
        """Load config from JSON or YAML file."""
        import json
        
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML config files: pip install pyyaml")
            else:
                data = json.load(f)
        
        return cls.from_dict(data)
    
    def save(self, path: Path) -> None:
        """Save config to file."""
        import json
        
        with open(path, 'w') as f:
            if path.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    yaml.safe_dump(self.to_dict(), f, default_flow_style=False)
                except ImportError:
                    raise ImportError("PyYAML required for YAML config files: pip install pyyaml")
            else:
                json.dump(self.to_dict(), f, indent=2)