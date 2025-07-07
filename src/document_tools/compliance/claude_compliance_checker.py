#!/usr/bin/env python3
"""CLAUDE.md Compliance Checker.

Analyzes all Python files in document_analyzer/ folder to ensure they comply
with the standards defined in CLAUDE.md including:
- Type hints for everything
- Proper error handling
- Test coverage requirements
- Code quality standards
- Security requirements
- Documentation standards
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ComplianceIssue:
    """Represents a compliance issue."""

    file_path: Path
    issue_type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    line_number: int | None = None
    suggestion: str | None = None


@dataclass
class FileCompliance:
    """Represents compliance status for a file."""

    file_path: Path
    has_type_hints: bool = False
    has_error_handling: bool = False
    has_tests: bool = False
    has_docstrings: bool = False
    has_security_issues: bool = False
    complexity_score: int = 0
    line_count: int = 0
    issues: list[ComplianceIssue] = field(default_factory=list)


class ClaudeComplianceChecker:
    """Checks compliance with CLAUDE.md standards."""

    def __init__(self, root_dir: Path | None = None):
        """Initialize compliance checker.

        Args:
            root_dir: Root directory of the project. If None, uses current working directory.
        """
        self.root_dir = root_dir or Path.cwd()
        self.document_analyzer_dir = self.root_dir / "document_analyzer"

        # CLAUDE.md forbidden patterns
        self.forbidden_patterns = [
            (r"print\s*\(", "Use logging instead of print statements"),
            (r"eval\s*\(", "eval() is a security risk"),
            (r"exec\s*\(", "exec() is a security risk"),
            (r"input\s*\(", "Use proper input validation instead of input()"),
            (r"__import__\s*\(", "Use standard imports instead of __import__"),
            (r"#\s*type:\s*ignore", "Fix typing errors instead of ignoring them"),
            (r"#\s*noqa", "Fix linting errors instead of ignoring them"),
            (r"#\s*fmt:\s*off", "Fix formatting errors instead of disabling formatter"),
        ]

        # Security patterns to check
        self.security_patterns = [
            (r"shell\s*=\s*True", "Avoid shell=True in subprocess calls"),
            (r"pickle\.loads?", "pickle can be unsafe with untrusted data"),
            (r"yaml\.load\s*\((?!.*Loader)", "Use yaml.safe_load() instead of yaml.load()"),
            (r"sql.*%.*%", "Potential SQL injection - use parameterized queries"),
            (r'password.*=.*["\'][^"\']*["\']', "Hardcoded password detected"),
            (r'api[_-]?key.*=.*["\'][^"\']*["\']', "Hardcoded API key detected"),
        ]

    def find_python_files(self) -> list[Path]:
        """Find all Python files in document_analyzer directory."""
        if not self.document_analyzer_dir.exists():
            return []

        return [file_path for file_path in self.document_analyzer_dir.rglob("*.py") if file_path.name != "__pycache__"]

    def check_type_hints(self, file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
        """Check if file has proper type hints."""
        issues = []
        has_type_hints = False

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

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

    def check_error_handling(self, file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
        """Check for proper error handling."""
        issues = []
        has_error_handling = False

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Look for try-except blocks
            try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]

            # Look for functions that might need error handling
            [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

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

            # Check for file operations without context managers
            [node for node in ast.walk(tree) if isinstance(node, ast.Call) and (
                    (isinstance(node.func, ast.Name) and node.func.id == "open") or
                    (isinstance(node.func, ast.Attribute) and node.func.attr in ["read_text", "write_text"])
                )]

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

    def check_forbidden_patterns(self, file_path: Path) -> list[ComplianceIssue]:
        """Check for forbidden patterns from CLAUDE.md."""
        issues = []

        try:
            content = file_path.read_text()
            lines = content.split("\n")

            for pattern, message in self.forbidden_patterns:
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
                    file_path=file_path,
                    issue_type="parsing",
                    severity="critical",
                    description=f"Failed to check patterns: {e}",
                )
            )

        return issues

    def check_security_issues(self, file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
        """Check for security issues."""
        issues = []
        has_security_issues = False

        try:
            content = file_path.read_text()
            lines = content.split("\n")

            for pattern, message in self.security_patterns:
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
                    file_path=file_path,
                    issue_type="parsing",
                    severity="critical",
                    description=f"Failed to check security: {e}",
                )
            )

        return has_security_issues, issues

    def check_docstrings(self, file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
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

    def check_test_coverage(self, file_path: Path) -> tuple[bool, list[ComplianceIssue]]:
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

    def calculate_complexity(self, file_path: Path) -> tuple[int, list[ComplianceIssue]]:
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

    def analyze_file(self, file_path: Path) -> FileCompliance:
        """Analyze a single file for CLAUDE.md compliance."""
        compliance = FileCompliance(file_path=file_path)

        try:
            content = file_path.read_text()
            compliance.line_count = len(content.split("\n"))

            # Check if file is too long (CLAUDE.md: max 500 lines)
            if compliance.line_count > 500:
                compliance.issues.append(
                    ComplianceIssue(
                        file_path=file_path,
                        issue_type="file_length",
                        severity="high",
                        description=f"File has {compliance.line_count} lines (max 500)",
                        suggestion="Split into smaller modules",
                    )
                )

        except Exception as e:
            compliance.issues.append(
                ComplianceIssue(
                    file_path=file_path, issue_type="parsing", severity="critical", description=f"Failed to read file: {e}"
                )
            )
            return compliance

        # Run all checks
        compliance.has_type_hints, type_issues = self.check_type_hints(file_path)
        compliance.issues.extend(type_issues)

        compliance.has_error_handling, error_issues = self.check_error_handling(file_path)
        compliance.issues.extend(error_issues)

        compliance.has_tests, test_issues = self.check_test_coverage(file_path)
        compliance.issues.extend(test_issues)

        compliance.has_docstrings, doc_issues = self.check_docstrings(file_path)
        compliance.issues.extend(doc_issues)

        compliance.has_security_issues, security_issues = self.check_security_issues(file_path)
        compliance.issues.extend(security_issues)

        compliance.complexity_score, complexity_issues = self.calculate_complexity(file_path)
        compliance.issues.extend(complexity_issues)

        # Check forbidden patterns
        forbidden_issues = self.check_forbidden_patterns(file_path)
        compliance.issues.extend(forbidden_issues)

        return compliance

    def generate_compliance_report(self) -> None:
        """Generate comprehensive CLAUDE.md compliance report."""
        logger.info("=" * 80)
        logger.info("🔍 CLAUDE.md COMPLIANCE ANALYSIS")
        logger.info("=" * 80)
        logger.info("")

        python_files = self.find_python_files()

        if not python_files:
            logger.error("❌ No Python files found in document_analyzer/ directory")
            return

        logger.info(f"📁 Analyzing {len(python_files)} Python files in document_analyzer/")
        logger.info("")

        # Analyze each file
        compliance_results = []
        for file_path in python_files:
            compliance = self.analyze_file(file_path)
            compliance_results.append(compliance)

        # Summary statistics
        total_files = len(compliance_results)
        files_with_tests = sum(1 for c in compliance_results if c.has_tests)
        files_with_type_hints = sum(1 for c in compliance_results if c.has_type_hints)
        files_with_docstrings = sum(1 for c in compliance_results if c.has_docstrings)
        files_with_security_issues = sum(1 for c in compliance_results if c.has_security_issues)

        critical_issues = sum(len([i for i in c.issues if i.severity == "critical"]) for c in compliance_results)
        high_issues = sum(len([i for i in c.issues if i.severity == "high"]) for c in compliance_results)
        medium_issues = sum(len([i for i in c.issues if i.severity == "medium"]) for c in compliance_results)

        logger.info("📊 COMPLIANCE SUMMARY")
        logger.info("-" * 50)
        logger.info(
            f"✅ Type Hints: {files_with_type_hints}/{total_files} files ({files_with_type_hints / total_files * 100:.1f}%)"
        )
        logger.info(f"🧪 Test Coverage: {files_with_tests}/{total_files} files ({files_with_tests / total_files * 100:.1f}%)")
        logger.info(
            f"📚 Documentation: {files_with_docstrings}/{total_files} files ({files_with_docstrings / total_files * 100:.1f}%)"
        )
        logger.info(f"🔒 Security Issues: {files_with_security_issues} files")
        logger.info("")
        logger.info(f"🚨 Critical Issues: {critical_issues}")
        logger.info(f"⚠️  High Issues: {high_issues}")
        logger.info(f"💡 Medium Issues: {medium_issues}")
        logger.info("")

        # Detailed file analysis
        logger.info("📋 DETAILED FILE ANALYSIS")
        logger.info("-" * 50)

        for compliance in compliance_results:
            rel_path = compliance.file_path.relative_to(self.root_dir)
            logger.info(f"\n📄 {rel_path}")
            logger.info(f"   Lines: {compliance.line_count}")

            # Status indicators
            status_icons = []
            if compliance.has_type_hints:
                status_icons.append("🔤")
            if compliance.has_tests:
                status_icons.append("🧪")
            if compliance.has_docstrings:
                status_icons.append("📚")
            if not compliance.has_security_issues:
                status_icons.append("🔒")

            if status_icons:
                logger.info(f"   Status: {' '.join(status_icons)}")

            # Issues by severity
            critical = [i for i in compliance.issues if i.severity == "critical"]
            high = [i for i in compliance.issues if i.severity == "high"]
            medium = [i for i in compliance.issues if i.severity == "medium"]

            if critical:
                logger.info(f"   🚨 Critical: {len(critical)} issues")
                for issue in critical[:2]:
                    logger.info(f"      - {issue.description}")
                if len(critical) > 2:
                    logger.info(f"      ... and {len(critical) - 2} more")

            if high:
                logger.info(f"   ⚠️  High: {len(high)} issues")
                for issue in high[:2]:
                    logger.info(f"      - {issue.description}")
                if len(high) > 2:
                    logger.info(f"      ... and {len(high) - 2} more")

            if medium:
                logger.info(f"   💡 Medium: {len(medium)} issues")

        # Overall assessment
        logger.info("\n" + "=" * 80)
        logger.info("📊 OVERALL CLAUDE.md COMPLIANCE")
        logger.info("=" * 80)

        # Calculate compliance score
        type_score = (files_with_type_hints / total_files) * 100
        test_score = (files_with_tests / total_files) * 100
        doc_score = (files_with_docstrings / total_files) * 100
        security_score = ((total_files - files_with_security_issues) / total_files) * 100

        overall_score = (type_score + test_score + doc_score + security_score) / 4

        logger.info(f"🔤 Type Hints: {type_score:.1f}%")
        logger.info(f"🧪 Test Coverage: {test_score:.1f}%")
        logger.info(f"📚 Documentation: {doc_score:.1f}%")
        logger.info(f"🔒 Security: {security_score:.1f}%")
        logger.info(f"\n📈 Overall Score: {overall_score:.1f}%")

        if overall_score >= 90:
            logger.info("✅ EXCELLENT - Fully CLAUDE.md compliant")
        elif overall_score >= 75:
            logger.info("⚠️  GOOD - Mostly compliant, minor improvements needed")
        elif overall_score >= 50:
            logger.info("❌ NEEDS WORK - Significant compliance gaps")
        else:
            logger.info("🚨 CRITICAL - Major compliance issues need immediate attention")

        # Recommendations
        logger.info("\n💡 TOP RECOMMENDATIONS:")
        if test_score < 80:
            logger.info("   - Create missing test files (CLAUDE.md requirement)")
        if type_score < 80:
            logger.info("   - Add type hints to all functions and variables")
        if doc_score < 70:
            logger.info("   - Add Google-style docstrings to public functions")
        if critical_issues > 0:
            logger.info(f"   - Fix {critical_issues} critical issues immediately")


def main() -> None:
    """Run the CLAUDE.md compliance checker."""
    checker = ClaudeComplianceChecker()
    checker.generate_compliance_report()


if __name__ == "__main__":
    main()
