# Contributing to Bullet Proof

Thank you for your interest in contributing to the Bullet Proof project! This document provides guidelines and standards for contributing.

## 📚 Related Documentation
- **Development Standards**: [CLAUDE.md](./CLAUDE.md) - MUST READ before contributing
- **Task Management**: [TASK.md](./planning/TASK.md) - Current tasks and priorities
- **Architecture**: [PLANNING.md](./planning/PLANNING.md) - System design and phases
- **Terminology**: [GLOSSARY.md](./GLOSSARY.md) - Project-specific terms

## 🚀 Getting Started

### Prerequisites
1. Read [CLAUDE.md](./CLAUDE.md) completely - it contains all development standards
2. Review current tasks in [TASK.md](./planning/TASK.md)
3. Set up your development environment as per [README.md](./README.md)

### Development Environment
```bash
# Install uv for fast package management
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv venv_local
source venv_local/bin/activate

# Install development dependencies
uv pip install -r requirements-dev.txt
```

## 🔒 Security Requirements

**CRITICAL**: All contributions must follow these security rules:

1. **NEVER commit secrets, API keys, or passwords**
2. **ALWAYS validate and sanitize inputs**
3. **USE parameterized queries** - no SQL concatenation
4. **ESCAPE user input** before rendering
5. **IMPLEMENT rate limiting** for APIs
6. **ENCRYPT sensitive data** at rest

See [CLAUDE.md](./CLAUDE.md#critical---security--data-integrity-zero-tolerance) for complete security requirements.

## 📋 Contribution Process

### 1. Find or Create a Task
- Check [TASK.md](./planning/TASK.md) for open tasks
- For new features, create a task using the Fibonacci scoring system
- Ensure task aligns with current sprint goals

### 2. Create a Branch
```bash
# Branch naming convention: type/scope-description
git checkout -b feat/user-auth
git checkout -b fix/database-connection
git checkout -b docs/api-endpoints
```

### 3. Write Tests FIRST
**MANDATORY**: Test-Driven Development is required
- Write tests before implementation
- Minimum 90% code coverage
- Include edge cases and failure scenarios

```python
# Test naming convention
def test_calculate_risk_score_valid_input_returns_float()
def test_calculate_risk_score_missing_data_raises_validation_error()
```

### 4. Implement Your Changes
Follow these standards from [CLAUDE.md](./CLAUDE.md):
- **Type hints for EVERYTHING**
- **No functions > 500 lines**
- **No more than 7 parameters per function**
- **Cyclomatic complexity ≤ 10**
- **Use async/await for I/O operations**

### 5. Run Quality Checks
```bash
# Required checks before committing
nox -s lint          # Type checking and linting
nox -s tests         # Unit tests with coverage
nox -s format        # Code formatting
nox -s security      # Security scanning
```

### 6. Update Documentation
- Update relevant .md files
- Add/update docstrings (Google style required)
- Update CHANGELOG.md for notable changes

### 7. Commit Your Changes
Use Conventional Commits format:
```bash
feat(api): add user authentication endpoint
fix(database): resolve connection pool exhaustion
docs(readme): update installation instructions
```

### 8. Create Pull Request
- Reference the task from TASK.md
- Include test results
- Describe changes clearly
- Ensure all CI checks pass

## 🧪 Testing Standards

### Required Tests
1. **Happy path test** (minimum 1)
2. **Edge cases** (minimum 2)
3. **Failure scenarios** (minimum 1)
4. **Integration test** (if applicable)

### Coverage Requirements
- **90% minimum code coverage**
- Use `pytest --cov=. --cov-fail-under=90`
- No `# type: ignore` or `# noqa` comments

## 🎨 Code Style

### Python Style
- **Black** for formatting (required)
- **Ruff** for linting (required)
- **MyPy** for type checking (strict mode)
- **Google-style docstrings**

### Forbidden Patterns
These will cause CI to fail:
```python
print()          # Use logging instead
eval()           # Security risk
exec()           # Security risk
# type: ignore   # Fix typing errors properly
# noqa           # Fix linting errors properly
```

## 📐 Architecture Guidelines

### SOLID Principles (Mandatory)
- **S**ingle Responsibility Principle
- **O**pen/Closed Principle
- **L**iskov Substitution Principle
- **I**nterface Segregation Principle
- **D**ependency Inversion Principle

### File Organization
```
src/
├── domain/         # Core business logic
├── services/       # Application services
├── api/           # API routes and schemas
├── database/      # Database models
└── utils/         # Utility functions

tests/             # Mirror src/ structure
```

## 🚨 Pull Request Checklist

Before submitting your PR, ensure:

- [ ] All tests pass with ≥90% coverage
- [ ] Type checking passes (`mypy`)
- [ ] Code formatting applied (`black`, `ruff`)
- [ ] Security scan clean (`bandit`, `safety`)
- [ ] No circular imports
- [ ] No global variables
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Task marked complete in TASK.md
- [ ] Regression tests added for bug fixes

## 🤝 Code Review Process

### Review Criteria
1. **Security**: No vulnerabilities or sensitive data exposure
2. **Tests**: Comprehensive coverage including edge cases
3. **Performance**: Efficient algorithms and queries
4. **Standards**: Follows CLAUDE.md requirements
5. **Documentation**: Clear and complete

### Response Times
- **Critical security fixes**: < 2 hours
- **Bug fixes**: < 24 hours
- **Features**: < 48 hours
- **Documentation**: < 72 hours

## 🐛 Reporting Issues

### Security Vulnerabilities
**DO NOT** create public issues for security vulnerabilities.
Contact the security team directly: [security contact to be added]

### Bug Reports
Include:
1. Clear description of the issue
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Environment details
6. Error messages/logs

### Feature Requests
1. Check [TASK.md](./planning/TASK.md) for existing requests
2. Provide use case and benefits
3. Consider implementation approach
4. Align with project architecture

## 📞 Getting Help

- **Standards Questions**: Refer to [CLAUDE.md](./CLAUDE.md)
- **Architecture Questions**: See [PLANNING.md](./planning/PLANNING.md)
- **Task Questions**: Check [TASK.md](./planning/TASK.md)
- **General Questions**: Create a discussion issue

## 🙏 Recognition

Contributors are recognized in:
- Git commit history
- CHANGELOG.md entries
- Project documentation

Thank you for helping make Bullet Proof more robust and secure!

---

> **Remember**: Quality over quantity. A well-tested, secure feature is better than multiple rushed implementations.