# Docpipe API Reference

## Main Functions

### `analyze_project`

```python
analyze_project(
    path: str | Path,
    config: Optional[AnalysisConfig] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> AnalysisResults
```

Main entry point for project analysis.

**Parameters:**
- `path`: Path to the project directory to analyze
- `config`: Optional configuration (uses defaults if not provided)
- `progress_callback`: Optional callback for progress updates `(percentage: float, message: str) -> None`

**Returns:**
- `AnalysisResults` object containing all analysis results

**Raises:**
- `DocPipeError`: If analysis fails
- `ConfigurationError`: If configuration is invalid

## Classes

### `DocPipe`

Main class for document analysis pipeline.

```python
class DocPipe:
    def __init__(self, config: Optional[AnalysisConfig] = None)
    def analyze(self, path: Path | str, progress_callback: Optional[ProgressCallback] = None) -> AnalysisResults
    def analyze_compliance(self, path: Path) -> ComplianceResults
    def analyze_similarity(self, path: Path) -> SimilarityResults
    def analyze_references(self, path: Path) -> ReferenceResults
    def analyze_instructions(self, path: Path) -> InstructionResults
    def get_features(self) -> Dict[str, bool]
    def validate_config(self) -> List[str]
```

### `AnalysisConfig`

Configuration for analysis pipeline.

```python
@dataclass
class AnalysisConfig:
    # General settings
    root_path: Optional[Path] = None
    exclude_patterns: List[str] = field(default_factory=list)
    include_not_in_use: bool = False
    
    # Analysis toggles
    check_compliance: bool = True
    analyze_similarity: bool = True
    validate_references: bool = True
    trace_instructions: bool = True
    check_structure: bool = True
    
    # Compliance settings
    compliance_rules: str = "CLAUDE.md"
    max_file_lines: int = 500
    min_test_coverage: float = 90.0
    max_complexity: int = 10
    
    # Similarity settings
    similarity_method: str = "semantic"  # "string", "semantic", or "both"
    similarity_threshold: float = 0.75
    similarity_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_clustering: bool = True
    
    # Reference settings
    check_external_links: bool = False
    check_images: bool = True
    check_anchors: bool = True
    
    # Output settings
    output_format: str = "json"  # "json", "csv", "excel", "markdown"
    verbose: bool = False
    include_file_contents: bool = False
    
    # Performance settings
    max_file_size_mb: float = 10.0
    parallel_processing: bool = True
    batch_size: int = 50
```

## Result Models

### `AnalysisResults`

Combined results from all analyses.

```python
@dataclass
class AnalysisResults:
    # Metadata
    project_path: Path
    timestamp: datetime
    duration_seconds: float
    config: AnalysisConfig
    
    # Document information
    documents: List[DocumentInfo]
    total_documents: int
    
    # Analysis results
    compliance: Optional[ComplianceResults]
    similarity: Optional[SimilarityResults]
    references: Optional[ReferenceResults]
    instructions: Optional[InstructionResults]
    
    # Aggregated results
    all_issues: List[Issue]
    feedback: List[Feedback]
    
    # Properties
    @property
    def missing_references(self) -> List[str]
    @property
    def must_have_files(self) -> List[str]
    @property
    def similar_documents(self) -> List[SimilarDocumentPair]
    @property
    def compliance_score(self) -> float
    @property
    def has_critical_issues(self) -> bool
    @property
    def summary(self) -> Dict[str, Any]
    
    # Methods
    def export(self, path: Path, format: Optional[str] = None) -> None
```

### `ComplianceResults`

Results from compliance checking.

```python
@dataclass
class ComplianceResults:
    files_checked: int
    files_compliant: int
    issues: List[Issue]
    issue_groups: Dict[str, IssueGroup]
    coverage_percentage: Optional[float]
    
    @property
    def compliance_score(self) -> float
    @property
    def has_critical_issues(self) -> bool
```

### `SimilarityResults`

Results from similarity analysis.

```python
@dataclass
class SimilarityResults:
    documents_analyzed: int
    similar_pairs: List[SimilarDocumentPair]
    duplicate_groups: List[List[Path]]
    similarity_matrix: Optional[Dict[str, Dict[str, float]]]
    
    @property
    def duplicate_count(self) -> int
    @property
    def similar_count(self) -> int
```

### `ReferenceResults`

Results from reference validation.

```python
@dataclass
class ReferenceResults:
    references_found: int
    valid_references: int
    broken_references: List[ReferenceInfo]
    orphaned_documents: List[Path]
    reference_graph: Optional[Dict[str, List[str]]]
    
    @property
    def validation_score(self) -> float
    @property
    def has_broken_references(self) -> bool
```

## Issue and Feedback Models

### `Issue`

Represents a single issue found during analysis.

```python
@dataclass
class Issue:
    severity: Severity
    category: IssueCategory
    message: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### `Feedback`

User-friendly feedback message.

```python
@dataclass
class Feedback:
    severity: Severity
    message: str
    details: Optional[str] = None
    action_required: bool = False
    related_issues: List[Issue] = field(default_factory=list)
```

### `Severity`

Issue severity levels.

```python
class Severity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"
```

### `IssueCategory`

Categories for different types of issues.

```python
class IssueCategory(str, Enum):
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
```

## Analyzer Classes

### `ComplianceAnalyzer`

Checks Python code compliance with standards.

```python
class ComplianceAnalyzer(FileAnalyzer):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

### `StringSimilarityAnalyzer`

Analyzes document similarity using string matching.

```python
class StringSimilarityAnalyzer(BaseAnalyzer):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

### `SemanticSimilarityAnalyzer`

Analyzes document similarity using semantic embeddings (requires [nlp] extra).

```python
class SemanticSimilarityAnalyzer(BaseAnalyzer):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

### `ReferenceValidator`

Validates references and links in markdown documents.

```python
class ReferenceValidator(FileAnalyzer):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
```

## Exceptions

### `DocPipeError`

Base exception for all docpipe errors.

### `ConfigurationError`

Raised when configuration is invalid.

### `AnalysisError`

Raised when analysis fails.

### `ValidationError`

Raised when validation fails.

### `DependencyError`

Raised when a required dependency is missing.

## Constants

### `FEATURES`

Dictionary of available features based on installed dependencies.

```python
FEATURES = {
    'semantic_similarity': bool,  # True if sentence-transformers installed
    'excel_export': bool,         # True if pandas installed
    'dataframe_reports': bool,    # True if pandas installed
}
```

## Type Aliases

```python
ProgressCallback = Callable[[float, str], None]
```

## Usage Examples

### Basic Analysis

```python
from docpipe import analyze_project

results = analyze_project("/path/to/project")
print(results.summary)
```

### Custom Configuration

```python
from docpipe import DocPipe, AnalysisConfig

config = AnalysisConfig(
    similarity_threshold=0.8,
    check_compliance=True,
    exclude_patterns=["*test*", "*.tmp"]
)

pipeline = DocPipe(config)
results = pipeline.analyze("/path/to/project")
```

### Exporting Results

```python
# Export to different formats
results.export("report.json")  # Uses config.output_format
results.export("report.csv", format="csv")
results.export("report.xlsx", format="excel")
```

### Error Handling

```python
from docpipe import analyze_project, DocPipeError

try:
    results = analyze_project("/path/to/project")
except DocPipeError as e:
    print(f"Analysis failed: {e}")
```