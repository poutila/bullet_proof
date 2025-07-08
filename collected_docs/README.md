# 📦 Docpipe

[![Python Version](https://img.shields.io/pypi/pyversions/docpipe)](https://pypi.org/project/docpipe/)
[![License](https://img.shields.io/github/license/username/docpipe)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/username/docpipe/tests.yml?branch=main)](https://github.com/username/docpipe/actions)
[![Coverage](https://img.shields.io/codecov/c/github/username/docpipe)](https://codecov.io/gh/username/docpipe)

A comprehensive tool for analyzing AI coding instructions in markdown documentation.

## 🚀 Features

- **Document Similarity Analysis**: Find duplicate or similar documentation using string matching and semantic analysis
- **Reference Validation**: Ensure all document references and links are valid
- **Compliance Checking**: Verify adherence to coding standards (e.g., CLAUDE.md)
- **Instruction Path Tracing**: Track instruction flow through documentation
- **Structural Soundness**: Validate document structure and organization
- **Multiple Export Formats**: JSON, CSV, Excel, and markdown reports

## 📥 Installation

### Basic Installation
```bash
pip install docpipe
```

### With NLP Features (Semantic Similarity)
```bash
pip install docpipe[nlp]
```

### With Data Export Features
```bash
pip install docpipe[data]
```

### Full Installation
```bash
pip install docpipe[all]
```

## 🎯 Quick Start

### Simple Usage
```python
from docpipe import analyze_project

# Analyze a project
results = analyze_project("/path/to/project")

# Access results
print(f"Found {len(results.missing_references)} missing references")
print(f"Found {len(results.similar_documents)} similar documents")
print(f"Compliance score: {results.compliance_score}%")

# Get feedback
for feedback in results.feedback:
    print(f"{feedback.severity}: {feedback.message}")
```

### Advanced Usage
```python
from docpipe import DocPipe, AnalysisConfig

# Configure analysis
config = AnalysisConfig(
    check_compliance=True,
    compliance_rules="CLAUDE.md",
    similarity_threshold=0.8,
    analyze_similarity=True,
    trace_instructions=True,
    validate_references=True,
)

# Create pipeline
pipeline = DocPipe(config)

# Run analysis with progress callback
def progress(percent, message):
    print(f"[{percent}%] {message}")

results = pipeline.analyze("/path/to/project", progress_callback=progress)

# Export results
results.export("analysis_report.json", format="json")
results.export("analysis_report.xlsx", format="excel")
```

## 🔧 CLI Usage

Docpipe also provides a command-line interface:

```bash
# Run all analyses
docpipe analyze /path/to/project

# Run specific analysis
docpipe analyze /path/to/project --only similarity

# Export results
docpipe analyze /path/to/project --output report.json --format json

# Show available features
docpipe features
```

## 📚 Documentation

For detailed documentation, visit [https://docpipe.readthedocs.io](https://docpipe.readthedocs.io)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) first.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with ❤️ by the Docpipe Contributors