# Contributing to Docpipe

We welcome contributions to Docpipe! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

1. **Check existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, dependencies)
   - Error messages and stack traces

### Suggesting Features

1. **Open a discussion** first for major features
2. **Explain the use case** and why it would be valuable
3. **Consider alternatives** and trade-offs
4. **Be prepared to contribute** the implementation

### Contributing Code

#### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/docpipe.git
   cd docpipe
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install in development mode:
   ```bash
   pip install -e .[dev]
   ```

5. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

#### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Run quality checks**:
   ```bash
   # Run tests with coverage
   pytest --cov=docpipe --cov-report=term-missing

   # Type checking
   mypy docpipe

   # Linting
   ruff check docpipe tests

   # Formatting
   black docpipe tests
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `style:` Code style changes
   - `refactor:` Code refactoring
   - `test:` Test changes
   - `chore:` Build/tooling changes

5. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Coding Standards

#### Python Code Style

We follow PEP 8 with these specific requirements:

1. **Type hints required** for all functions:
   ```python
   def process_data(items: List[str], prefix: str = "") -> List[str]:
       """Process data with optional prefix."""
       return [f"{prefix}{item}" for item in items]
   ```

2. **Docstrings required** for all public functions and classes:
   ```python
   def analyze_document(path: Path) -> AnalysisResult:
       """
       Analyze a document for compliance.
       
       Args:
           path: Path to the document to analyze
           
       Returns:
           Analysis results containing issues and metrics
           
       Raises:
           FileNotFoundError: If the document doesn't exist
       """
   ```

3. **Maximum line length**: 100 characters
4. **Maximum file length**: 500 lines
5. **Maximum function complexity**: 10 (cyclomatic complexity)

#### Test Requirements

1. **Test coverage minimum**: 90%
2. **Test file naming**: `test_<module_name>.py`
3. **Test function naming**: `test_<function>_<condition>_<expected_result>`
   ```python
   def test_analyze_document_missing_file_raises_error():
       """Test that analyzing missing file raises FileNotFoundError."""
   ```

4. **Required test types**:
   - Unit tests for individual functions
   - Integration tests for workflows
   - Edge case tests
   - Error condition tests

#### Security Requirements

1. **No hardcoded secrets** or credentials
2. **No use of `eval()` or `exec()`**
3. **Input validation** for all user inputs
4. **No bare `except:` clauses**
5. **Use `logging` instead of `print()`**

### Pull Request Process

1. **Ensure all checks pass**:
   - All tests pass
   - Coverage meets minimum (90%)
   - No linting errors
   - Type checking passes

2. **Update documentation**:
   - Add/update docstrings
   - Update user guide if needed
   - Update CHANGELOG.md

3. **Write a clear PR description**:
   - What changes were made
   - Why they were needed
   - Any breaking changes
   - Related issues

4. **Be responsive to feedback**:
   - Address review comments
   - Ask for clarification if needed
   - Be open to suggestions

### Release Process

Releases are managed by maintainers:

1. **Version bumping** follows [Semantic Versioning](https://semver.org/)
2. **CHANGELOG.md** is updated with all changes
3. **Tags** are created for releases
4. **PyPI deployment** is automated via GitHub Actions

## Getting Help

- **Documentation**: Check the [User Guide](docs/user_guide.md) and [API Reference](docs/api_reference.md)
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions

## Recognition

Contributors are recognized in:
- The CHANGELOG.md file
- The project's contributor list
- Release notes

Thank you for contributing to Docpipe! 🎉