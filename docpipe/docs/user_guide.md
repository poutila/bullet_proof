# Docpipe User Guide

## Introduction

Docpipe is a comprehensive tool for analyzing AI coding instructions in markdown documentation. It helps ensure documentation quality, consistency, and compliance with coding standards.

## Installation

### Basic Installation

```bash
pip install docpipe
```

### Optional Features

For semantic similarity analysis using NLP:
```bash
pip install docpipe[nlp]
```

For data export features (Excel, advanced reporting):
```bash
pip install docpipe[data]
```

For development tools:
```bash
pip install docpipe[dev]
```

Install everything:
```bash
pip install docpipe[all]
```

## Quick Start

### Simple Usage

```python
from docpipe import analyze_project

# Analyze a project
results = analyze_project("/path/to/project")

# Print summary
print(f"Documents analyzed: {results.total_documents}")
print(f"Compliance score: {results.compliance_score}%")
print(f"Issues found: {len(results.all_issues)}")

# Check for critical issues
if results.has_critical_issues:
    print("⚠️ Critical issues found!")
```

### Using Configuration

```python
from docpipe import analyze_project, AnalysisConfig

# Create custom configuration
config = AnalysisConfig(
    # Toggle analyses
    check_compliance=True,
    analyze_similarity=True,
    validate_references=True,
    
    # Set thresholds
    similarity_threshold=0.8,
    min_test_coverage=90.0,
    max_file_lines=500,
    
    # Configure output
    output_format="json",
    verbose=True
)

# Run analysis
results = analyze_project("/path/to/project", config)
```

### Progress Tracking

```python
def show_progress(percentage, message):
    print(f"[{percentage:3.0f}%] {message}")

results = analyze_project(
    "/path/to/project",
    progress_callback=show_progress
)
```

## Advanced Usage

### Using DocPipe Class

For more control over the analysis process:

```python
from docpipe import DocPipe, AnalysisConfig

# Create pipeline
pipeline = DocPipe(AnalysisConfig(
    similarity_method="both",  # Use both string and semantic
    enable_clustering=True,
    parallel_processing=True
))

# Run specific analyses
compliance_results = pipeline.analyze_compliance("/path/to/project")
similarity_results = pipeline.analyze_similarity("/path/to/project")

# Or run full analysis
results = pipeline.analyze("/path/to/project")
```

### Exporting Results

```python
# Export to different formats
results.export("report.json", format="json")
results.export("report.csv", format="csv")
results.export("report.md", format="markdown")
results.export("report.xlsx", format="excel")  # Requires [data] extra
```

### Configuration Files

Save and load configurations:

```python
# Save configuration
config = AnalysisConfig(similarity_threshold=0.85)
config.save("myconfig.json")

# Load configuration
loaded_config = AnalysisConfig.from_file("myconfig.json")
```

## Analysis Types

### 1. Compliance Analysis

Checks Python code against CLAUDE.md standards:
- Type hint coverage (default: 80% required)
- Docstring coverage (default: 70% required)
- Forbidden patterns (print, eval, exec, etc.)
- Security vulnerabilities
- Cyclomatic complexity
- File length limits
- Test file existence

### 2. Similarity Analysis

Finds similar or duplicate documents:
- **String similarity**: Uses fuzzy matching algorithms
- **Semantic similarity**: Uses NLP embeddings (requires [nlp] extra)
- **Combined**: Uses both methods for best results

### 3. Reference Validation

Validates links and references in markdown:
- Internal document links
- Image references
- Anchor links
- External URLs (optional)
- Detects orphaned documents

### 4. Instruction Path Tracing

Traces instruction flow through documentation (when implemented).

## Configuration Options

### Key Configuration Parameters

```python
config = AnalysisConfig(
    # Analysis toggles
    check_compliance=True,
    analyze_similarity=True,
    validate_references=True,
    trace_instructions=False,
    check_structure=False,
    
    # Compliance settings
    min_type_hint_coverage=80.0,
    min_docstring_coverage=70.0,
    max_file_lines=500,
    max_complexity=10,
    
    # Similarity settings
    similarity_method="string",  # "string", "semantic", or "both"
    similarity_threshold=0.75,
    enable_clustering=True,
    
    # Reference settings
    check_external_links=False,
    check_images=True,
    check_anchors=True,
    
    # Output settings
    output_format="json",
    verbose=False,
    
    # Performance settings
    max_file_size_mb=10.0,
    parallel_processing=True,
    
    # Exclusions
    exclude_patterns=[
        "*.venv*",
        "*__pycache__*",
        "*.git*",
        "*node_modules*",
    ]
)
```

## Understanding Results

### Analysis Results Structure

```python
results = analyze_project("/path/to/project")

# Access different result types
results.compliance      # ComplianceResults
results.similarity      # SimilarityResults  
results.references      # ReferenceResults
results.instructions    # InstructionResults

# Aggregated data
results.all_issues      # List of all issues found
results.feedback        # User-friendly feedback messages
results.summary         # Dictionary summary of results
```

### Issue Severity Levels

- **CRITICAL**: Must be fixed immediately
- **ERROR**: Should be fixed
- **WARNING**: Should be reviewed
- **INFO**: Informational
- **HINT**: Suggestions for improvement

### Feedback Messages

Feedback provides actionable insights:

```python
for feedback in results.feedback:
    if feedback.action_required:
        print(f"⚠️ {feedback.message}")
        if feedback.details:
            print(f"   {feedback.details}")
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Docpipe Analysis
  run: |
    pip install docpipe
    python -c "
    from docpipe import analyze_project
    results = analyze_project('.')
    if results.has_critical_issues:
        exit(2)
    elif results.compliance_score < 80:
        exit(1)
    "
```

### Pre-commit Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: docpipe
        name: Docpipe Analysis
        entry: docpipe analyze
        language: python
        additional_dependencies: [docpipe]
        files: \.(py|md)$
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure docpipe is installed
   ```bash
   pip install docpipe
   ```

2. **Semantic similarity not working**: Install NLP dependencies
   ```bash
   pip install docpipe[nlp]
   ```

3. **Excel export failing**: Install data dependencies
   ```bash
   pip install docpipe[data]
   ```

4. **Large files skipped**: Adjust max file size
   ```python
   config = AnalysisConfig(max_file_size_mb=20.0)
   ```

### Performance Tips

1. **Exclude unnecessary paths**:
   ```python
   config = AnalysisConfig(
       exclude_patterns=["*.venv*", "build/*", "dist/*"]
   )
   ```

2. **Use string similarity for faster analysis**:
   ```python
   config = AnalysisConfig(similarity_method="string")
   ```

3. **Disable expensive checks**:
   ```python
   config = AnalysisConfig(
       check_external_links=False,
       trace_instructions=False
   )
   ```

## Examples

See the `examples/` directory for complete examples:
- `basic_usage.py`: Simple analysis examples
- `advanced_usage.py`: Advanced features and configuration
- More examples coming soon!

## API Reference

For detailed API documentation, see the [API Reference](api_reference.md).