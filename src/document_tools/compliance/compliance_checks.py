#!/usr/bin/env python3
"""CLAUDE.md Compliance Checking Utilities.

Individual compliance check functions separated from the main checker
for better maintainability and testability.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComplianceIssue:
    """Represents a compliance issue."""

    file_path: Path
    issue_type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    line_number: int | None = None
    suggestion: str | None = None


def check_type_hints(file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
    """Check if file has proper type hints."""
    issues = []
    has_type_hints = False

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        typed_functions = 0
        total_functions = len(functions)

        for func in functions:
            # Skip dunder methods and simple getters/setters
            if func.name.startswith("_") and func.name.endswith("_"):
                total_functions -= 1
                continue

            # Check return type annotation
            has_return_type = func.returns is not None

            # Check parameter type annotations
            has_param_types = all(arg.annotation is not None for arg in func.args.args if arg.arg != "self")

            if has_return_type and has_param_types:
                typed_functions += 1
            else:
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="type_hints",
                        severity="high",
                        description=f"Function '{func.name}' missing type hints",
                        line_number=func.lineno,
                        suggestion="Add type hints for all parameters and return type",
                    )
                )

        if total_functions > 0:
            type_coverage = typed_functions / total_functions
            has_type_hints = type_coverage >= 0.8  # 80% threshold

            if type_coverage < 0.8:
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="type_hints",
                        severity="medium",
                        description=f"Type hint coverage: {type_coverage:.1%} (should be ≥80%)",
                        suggestion="Add type hints to more functions",
                    )
                )
        else:
            has_type_hints = True  # No functions to type

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path,
                issue_type="parsing",
                severity="critical",
                description=f"Failed to parse file: {e}",
                suggestion="Fix syntax errors",
            )
        )

    return has_type_hints, issues


def check_error_handling(file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
    """Check for proper error handling."""
    issues = []
    has_error_handling = False

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Look for try-except blocks
        try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]

        # Check for bare except clauses
        for try_block in try_blocks:
            # bare except:
            issues.extend(ComplianceIssue(
                            file_path=file_path,
                            issue_type="error_handling",
                            severity="high",
                            description="Bare except clause found",
                            line_number=handler.lineno,
                            suggestion="Use specific exception types instead of bare except:",
                        ) for handler in try_block.handlers if handler.type is None)

        # Simple heuristic: if we have try blocks or path operations, assume error handling
        if try_blocks or any("Path" in str(type(node)) for node in ast.walk(tree)):
            has_error_handling = True

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path,
                issue_type="parsing",
                severity="critical",
                description=f"Failed to analyze error handling: {e}",
            )
        )

    return has_error_handling, issues


def check_forbidden_patterns(file_path: Path) -> list[ComplianceIssue]:
    """Check for forbidden patterns from CLAUDE.md."""
    # CLAUDE.md forbidden patterns
    forbidden_patterns = [
        (r"print\s*\(", "Use logging instead of print statements"),
        (r"eval\s*\(", "eval() is a security risk"),
        (r"exec\s*\(", "exec() is a security risk"),
        (r"input\s*\(", "Use proper input validation instead of input()"),
        (r"__import__\s*\(", "Use standard imports instead of __import__"),
        (r"#\s*type:\s*ignore", "Fix typing errors instead of ignoring them"),
        (r"#\s*noqa", "Fix linting errors instead of ignoring them"),
        (r"#\s*fmt:\s*off", "Fix formatting errors instead of disabling formatter"),
    ]

    issues = []

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for pattern, message in forbidden_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append(
                        ComplianceIssue(
                            file_path=file_path,
                            issue_type="forbidden_pattern",
                            severity="critical",
                            description=f"Forbidden pattern: {message}",
                            line_number=line_num,
                            suggestion=f"Remove or replace: {line.strip()}",
                        )
                    )

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path, issue_type="parsing", severity="critical", description=f"Failed to check patterns: {e}"
            )
        )

    return issues


def check_security_issues(file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
    """Check for security issues."""
    # Security patterns to check
    security_patterns = [
        (r"shell\s*=\s*True", "Avoid shell=True in subprocess calls"),
        (r"pickle\.loads?", "pickle can be unsafe with untrusted data"),
        (r"yaml\.load\s*\((?!.*Loader)", "Use yaml.safe_load() instead of yaml.load()"),
        (r"sql.*%.*%", "Potential SQL injection - use parameterized queries"),
        (r'password.*=.*["\'][^"\']*["\']', "Hardcoded password detected"),
        (r'api[_-]?key.*=.*["\'][^"\']*["\']', "Hardcoded API key detected"),
    ]

    issues = []
    has_security_issues = False

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for pattern, message in security_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        ComplianceIssue(
                            file_path=file_path,
                            issue_type="security",
                            severity="critical",
                            description=f"Security issue: {message}",
                            line_number=line_num,
                            suggestion="Review and fix security vulnerability",
                        )
                    )
                    has_security_issues = True

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path, issue_type="parsing", severity="critical", description=f"Failed to check security: {e}"
            )
        )

    return has_security_issues, issues


def check_docstrings(file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
    """Check for proper docstrings."""
    issues = []
    has_docstrings = False

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Check module docstring
        module_has_docstring = ast.get_docstring(tree) is not None

        # Check function docstrings
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        public_functions = [f for f in functions if not f.name.startswith("_")]

        documented_functions = 0
        for func in public_functions:
            if ast.get_docstring(func):
                documented_functions += 1
            else:
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="documentation",
                        severity="medium",
                        description=f"Function '{func.name}' missing docstring",
                        line_number=func.lineno,
                        suggestion="Add Google-style docstring",
                    )
                )

        # Check class docstrings
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        documented_classes = 0
        for cls in classes:
            if ast.get_docstring(cls):
                documented_classes += 1
            else:
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="documentation",
                        severity="medium",
                        description=f"Class '{cls.name}' missing docstring",
                        line_number=cls.lineno,
                        suggestion="Add class docstring",
                    )
                )

        # Calculate overall documentation score
        total_items = len(public_functions) + len(classes) + (1 if content.strip() else 0)
        documented_items = documented_functions + documented_classes + (1 if module_has_docstring else 0)

        if total_items > 0:
            doc_coverage = documented_items / total_items
            has_docstrings = doc_coverage >= 0.7  # 70% threshold

            if not module_has_docstring and content.strip():
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="documentation",
                        severity="medium",
                        description="Module missing docstring",
                        line_number=1,
                        suggestion="Add module-level docstring",
                    )
                )

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path,
                issue_type="parsing",
                severity="critical",
                description=f"Failed to check docstrings: {e}",
            )
        )

    return has_docstrings, issues


def check_test_coverage(file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
    """Check if corresponding test file exists."""
    issues: list[ComplianceIssue] = []

    # Skip test files themselves
    if file_path.name.startswith("test_"):
        return True, issues

    # Look for corresponding test file
    test_file_name = f"test_{file_path.name}"
    test_file_path = file_path.parent / test_file_name

    has_tests = test_file_path.exists()

    if not has_tests:
        issues.append(
            ComplianceIssue(
                file_path=file_path,
                issue_type="testing",
                severity="critical",
                description="No corresponding test file found",
                suggestion=f"Create {test_file_name} with proper test coverage",
            )
        )

    return has_tests, issues


def calculate_complexity(file_path: Path) -> tuple[int, list[ComplianceIssue]]:
    """Calculate cyclomatic complexity."""
    issues = []
    total_complexity = 0

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            complexity = 1  # Base complexity

            # Count decision points
            for node in ast.walk(func):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1

            total_complexity += complexity

            if complexity > 10:  # CLAUDE.md threshold
                issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="complexity",
                        severity="high",
                        description=f"Function '{func.name}' has complexity {complexity} (max 10)",
                        line_number=func.lineno,
                        suggestion="Break down into smaller functions",
                    )
                )

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path,
                issue_type="parsing",
                severity="critical",
                description=f"Failed to calculate complexity: {e}",
            )
        )

    return total_complexity, issues


def check_file_length(file_path: Path) -> list[ComplianceIssue]:
    """Check if file exceeds maximum length (500 lines)."""
    issues = []

    try:
        content = file_path.read_text()
        line_count = len(content.split("\n"))

        if line_count > 500:
            issues.append(
                ComplianceIssue(
                    file_path=file_path,
                    issue_type="file_length",
                    severity="high",
                    description=f"File has {line_count} lines (max 500)",
                    suggestion="Split into smaller modules",
                )
            )

    except Exception as e:
        issues.append(
            ComplianceIssue(
                file_path=file_path, issue_type="parsing", severity="critical", description=f"Failed to read file: {e}"
            )
        )

    return issues
