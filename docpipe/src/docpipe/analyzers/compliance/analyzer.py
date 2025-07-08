"""Compliance analyzer for checking CLAUDE.md standards."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from ...models import (
    Issue,
    Severity,
    IssueCategory,
    ComplianceResults,
)
from ..base import BaseAnalyzer, FileAnalyzer


@dataclass
class ComplianceConfig:
    """Configuration for compliance checking."""
    
    # Thresholds
    min_type_hint_coverage: float = 80.0
    min_docstring_coverage: float = 70.0
    max_file_lines: int = 500
    max_function_lines: int = 50
    max_complexity: int = 10
    
    # Feature toggles
    check_type_hints: bool = True
    check_docstrings: bool = True
    check_error_handling: bool = True
    check_forbidden_patterns: bool = True
    check_security_issues: bool = True
    check_test_files: bool = True
    check_complexity: bool = True
    check_file_length: bool = True
    
    # Patterns
    forbidden_patterns: List[str] = field(default_factory=lambda: [
        r'\bprint\s*\(',
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\binput\s*\(',
        r'\b__import__\s*\(',
        r'#\s*type:\s*ignore',
        r'#\s*noqa',
        r'#\s*fmt:\s*off',
    ])
    
    security_patterns: List[str] = field(default_factory=lambda: [
        r'password\s*=\s*["\'][\w\d]+["\']',
        r'api_key\s*=\s*["\'][\w\d]+["\']',
        r'secret\s*=\s*["\'][\w\d]+["\']',
        r'shell\s*=\s*True',
        r'verify\s*=\s*False',
        r'\.format\s*\([^)]*\)\s*#.*SQL',
        r'%\s*\([^)]*\)\s*#.*SQL',
    ])


class ComplianceAnalyzer(FileAnalyzer):
    """Analyzer for checking Python code compliance with CLAUDE.md standards."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with configuration."""
        super().__init__(config)
        
        # Create ComplianceConfig from dict
        compliance_config = config.get("compliance", {}) if config else {}
        self.compliance_config = ComplianceConfig(**compliance_config)
    
    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "ComplianceAnalyzer"
    
    @property 
    def description(self) -> str:
        """Get analyzer description."""
        return "Checks Python code compliance with CLAUDE.md standards"
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Only process Python files."""
        return file_path.suffix == ".py"
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file for compliance."""
        issues: List[Issue] = []
        
        # Skip test files for certain checks
        is_test_file = "test_" in file_path.name or "_test.py" in file_path.name
        
        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception as e:
            issues.append(Issue(
                severity=Severity.ERROR,
                category=IssueCategory.PARSE_ERROR,
                message=f"Failed to parse Python file: {e}",
                file_path=file_path
            ))
            return {"compliant": False, "issues": issues}
        
        # Run individual checks
        if self.compliance_config.check_type_hints and not is_test_file:
            self._check_type_hints(file_path, tree, issues)
        
        if self.compliance_config.check_docstrings and not is_test_file:
            self._check_docstrings(file_path, tree, issues)
        
        if self.compliance_config.check_error_handling:
            self._check_error_handling(file_path, tree, content, issues)
        
        if self.compliance_config.check_forbidden_patterns:
            self._check_forbidden_patterns(file_path, content, issues)
        
        if self.compliance_config.check_security_issues:
            self._check_security_patterns(file_path, content, issues)
        
        if self.compliance_config.check_complexity and not is_test_file:
            self._check_complexity(file_path, tree, issues)
        
        if self.compliance_config.check_file_length:
            self._check_file_length(file_path, content, issues)
        
        # Check for test file if not a test file itself
        if self.compliance_config.check_test_files and not is_test_file:
            self._check_test_file_exists(file_path, issues)
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "metrics": self._calculate_metrics(tree, content)
        }
    
    def _check_type_hints(self, file_path: Path, tree: ast.AST, issues: List[Issue]) -> None:
        """Check type hint coverage."""
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        if not functions:
            return
        
        typed_functions = 0
        total_functions = 0
        
        for func in functions:
            # Skip dunder methods
            if func.name.startswith("__") and func.name.endswith("__"):
                continue
            
            total_functions += 1
            
            # Check return type annotation
            has_return_type = func.returns is not None
            
            # Check parameter type annotations (excluding self)
            params = [arg for arg in func.args.args if arg.arg != "self"]
            has_param_types = all(arg.annotation is not None for arg in params)
            
            if has_return_type and has_param_types:
                typed_functions += 1
            else:
                issues.append(Issue(
                    severity=Severity.WARNING,
                    category=IssueCategory.MISSING_TYPE_HINTS,
                    message=f"Function '{func.name}' missing type hints",
                    file_path=file_path,
                    line_number=func.lineno,
                    suggestion="Add type hints for all parameters and return value"
                ))
        
        # Check coverage
        if total_functions > 0:
            coverage = (typed_functions / total_functions) * 100
            if coverage < self.compliance_config.min_type_hint_coverage:
                issues.append(Issue(
                    severity=Severity.ERROR,
                    category=IssueCategory.MISSING_TYPE_HINTS,
                    message=f"Type hint coverage {coverage:.1f}% below required {self.compliance_config.min_type_hint_coverage}%",
                    file_path=file_path,
                    suggestion="Add type hints to more functions"
                ))
    
    def _check_docstrings(self, file_path: Path, tree: ast.AST, issues: List[Issue]) -> None:
        """Check docstring coverage."""
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        total_items = len(functions) + len(classes)
        if total_items == 0:
            return
        
        documented_items = 0
        
        for func in functions:
            if ast.get_docstring(func):
                documented_items += 1
            else:
                issues.append(Issue(
                    severity=Severity.WARNING,
                    category=IssueCategory.MISSING_DOCSTRING,
                    message=f"Function '{func.name}' missing docstring",
                    file_path=file_path,
                    line_number=func.lineno,
                    suggestion="Add a docstring describing the function"
                ))
        
        for cls in classes:
            if ast.get_docstring(cls):
                documented_items += 1
            else:
                issues.append(Issue(
                    severity=Severity.WARNING,
                    category=IssueCategory.MISSING_DOCSTRING,
                    message=f"Class '{cls.name}' missing docstring",
                    file_path=file_path,
                    line_number=cls.lineno,
                    suggestion="Add a docstring describing the class"
                ))
        
        # Check coverage
        coverage = (documented_items / total_items) * 100
        if coverage < self.compliance_config.min_docstring_coverage:
            issues.append(Issue(
                severity=Severity.WARNING,
                category=IssueCategory.MISSING_DOCSTRING,
                message=f"Docstring coverage {coverage:.1f}% below required {self.compliance_config.min_docstring_coverage}%",
                file_path=file_path,
                suggestion="Add docstrings to more functions and classes"
            ))
    
    def _check_error_handling(self, file_path: Path, tree: ast.AST, content: str, issues: List[Issue]) -> None:
        """Check for proper error handling."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Check for bare except
                if node.type is None:
                    issues.append(Issue(
                        severity=Severity.ERROR,
                        category=IssueCategory.FORBIDDEN_PATTERN,
                        message="Bare except clause found",
                        file_path=file_path,
                        line_number=node.lineno,
                        suggestion="Use specific exception types instead of bare except"
                    ))
    
    def _check_forbidden_patterns(self, file_path: Path, content: str, issues: List[Issue]) -> None:
        """Check for forbidden patterns."""
        lines = content.split('\n')
        
        for pattern in self.compliance_config.forbidden_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    # Determine appropriate message
                    if 'print' in pattern:
                        msg = "print() statement found"
                        suggestion = "Use logging instead of print()"
                    elif 'eval' in pattern or 'exec' in pattern:
                        msg = f"Dangerous function {pattern} found"
                        suggestion = "Avoid eval/exec for security reasons"
                    elif 'type:' in pattern:
                        msg = "Type ignore comment found"
                        suggestion = "Fix the type error instead of ignoring it"
                    else:
                        msg = f"Forbidden pattern found: {pattern}"
                        suggestion = "Remove or replace this pattern"
                    
                    issues.append(Issue(
                        severity=Severity.ERROR,
                        category=IssueCategory.FORBIDDEN_PATTERN,
                        message=msg,
                        file_path=file_path,
                        line_number=i,
                        suggestion=suggestion,
                        code_snippet=line.strip()
                    ))
    
    def _check_security_patterns(self, file_path: Path, content: str, issues: List[Issue]) -> None:
        """Check for security issues."""
        lines = content.split('\n')
        
        for pattern in self.compliance_config.security_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append(Issue(
                        severity=Severity.CRITICAL,
                        category=IssueCategory.SECURITY_PATTERN,
                        message=f"Potential security issue: {pattern}",
                        file_path=file_path,
                        line_number=i,
                        suggestion="Review and fix this security issue",
                        code_snippet=line.strip()
                    ))
    
    def _check_complexity(self, file_path: Path, tree: ast.AST, issues: List[Issue]) -> None:
        """Check cyclomatic complexity."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                if complexity > self.compliance_config.max_complexity:
                    issues.append(Issue(
                        severity=Severity.WARNING,
                        category=IssueCategory.HIGH_COMPLEXITY,
                        message=f"Function '{node.name}' has complexity {complexity} (max: {self.compliance_config.max_complexity})",
                        file_path=file_path,
                        line_number=node.lineno,
                        suggestion="Refactor to reduce complexity"
                    ))
    
    def _check_file_length(self, file_path: Path, content: str, issues: List[Issue]) -> None:
        """Check file length."""
        lines = len(content.split('\n'))
        if lines > self.compliance_config.max_file_lines:
            issues.append(Issue(
                severity=Severity.WARNING,
                category=IssueCategory.FILE_TOO_LONG,
                message=f"File has {lines} lines (max: {self.compliance_config.max_file_lines})",
                file_path=file_path,
                suggestion="Split into smaller modules"
            ))
    
    def _check_test_file_exists(self, file_path: Path, issues: List[Issue]) -> None:
        """Check if corresponding test file exists."""
        # Skip __init__.py files
        if file_path.name == "__init__.py":
            return
        
        # Look for test file
        test_name = f"test_{file_path.stem}.py"
        test_paths = [
            file_path.parent / test_name,
            file_path.parent / "tests" / test_name,
            file_path.parent.parent / "tests" / test_name,
        ]
        
        if not any(p.exists() for p in test_paths):
            issues.append(Issue(
                severity=Severity.ERROR,
                category=IssueCategory.MISSING_TESTS,
                message=f"No test file found for {file_path.name}",
                file_path=file_path,
                suggestion=f"Create {test_name} with tests"
            ))
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each 'and' or 'or' adds complexity
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_metrics(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Calculate various code metrics."""
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        
        return {
            "lines": len(content.split('\n')),
            "functions": len(functions),
            "classes": len(classes),
            "imports": len([n for n in ast.walk(tree) if isinstance(n, ast.Import)]),
        }
    
    def _analyze_impl(self, path: Path) -> ComplianceResults:
        """Aggregate results into ComplianceResults."""
        if path.is_file():
            # Single file analysis
            result = self._analyze_file(path)
            results = ComplianceResults(
                files_checked=1,
                files_compliant=1 if result["compliant"] else 0
            )
            for issue in result["issues"]:
                results.add_issue(issue)
            
        else:
            # Directory analysis
            results = ComplianceResults()
            file_results = super()._analyze_directory(path)
            
            for file_path, result in file_results.items():
                if isinstance(result, dict) and "issues" in result:
                    results.files_checked += 1
                    if result.get("compliant", False):
                        results.files_compliant += 1
                    
                    for issue in result["issues"]:
                        results.add_issue(issue)
        
        return results