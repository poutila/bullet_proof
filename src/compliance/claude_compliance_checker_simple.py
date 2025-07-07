#!/usr/bin/env python3
"""CLAUDE.md Compliance Checker.

Simplified main checker that orchestrates compliance checks using
the separated compliance_checks module.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from compliance.compliance_checks import (
    ComplianceIssue,
    calculate_complexity,
    check_docstrings,
    check_error_handling,
    check_file_length,
    check_forbidden_patterns,
    check_security_issues,
    check_test_coverage,
    check_type_hints,
)

logger = logging.getLogger(__name__)


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

    def __init__(self, root_dir: Path | None = None) -> None:
        """Initialize compliance checker.

        Args:
            root_dir: Root directory of the project. If None, uses current working directory.
        """
        self.root_dir = root_dir or Path.cwd()
        self.document_analyzer_dir = self.root_dir / "document_analyzer"

    def find_python_files(self) -> list[Path]:
        """Find all Python files in document_analyzer directory."""
        if not self.document_analyzer_dir.exists():
            return []

        return [file_path for file_path in self.document_analyzer_dir.rglob("*.py") if file_path.name != "__pycache__"]

    def analyze_file(self, file_path: Path) -> FileCompliance:
        """Analyze a single file for CLAUDE.md compliance."""
        compliance = FileCompliance(file_path=file_path)

        try:
            content = file_path.read_text()
            compliance.line_count = len(content.split("\n"))
        except Exception as e:
            compliance.issues.append(
                ComplianceIssue(
                    file_path=file_path, issue_type="parsing", severity="critical", description=f"Failed to read file: {e}"
                )
            )
            return compliance

        # Run all checks
        compliance.has_type_hints, type_issues = check_type_hints(file_path)
        compliance.issues.extend(type_issues)

        compliance.has_error_handling, error_issues = check_error_handling(file_path)
        compliance.issues.extend(error_issues)

        compliance.has_tests, test_issues = check_test_coverage(file_path)
        compliance.issues.extend(test_issues)

        compliance.has_docstrings, doc_issues = check_docstrings(file_path)
        compliance.issues.extend(doc_issues)

        compliance.has_security_issues, security_issues = check_security_issues(file_path)
        compliance.issues.extend(security_issues)

        compliance.complexity_score, complexity_issues = calculate_complexity(file_path)
        compliance.issues.extend(complexity_issues)

        # Check forbidden patterns
        forbidden_issues = check_forbidden_patterns(file_path)
        compliance.issues.extend(forbidden_issues)

        # Check file length
        length_issues = check_file_length(file_path)
        compliance.issues.extend(length_issues)

        return compliance

    def generate_compliance_report(self) -> None:
        """Generate comprehensive CLAUDE.md compliance report."""
        logger.info("=" * 80)
        logger.info("🔍 CLAUDE.md COMPLIANCE ANALYSIS")
        logger.info("=" * 80)
        logger.info("")

        python_files = self.find_python_files()

        if not python_files:
            logger.error("No Python files found in document_analyzer/ directory")
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
        logger.info(
            f"🧪 Test Coverage: {files_with_tests}/{total_files} files ({files_with_tests / total_files * 100:.1f}%)"
        )
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
    # Configure logging for CLI usage
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])

    checker = ClaudeComplianceChecker()
    checker.generate_compliance_report()


if __name__ == "__main__":
    main()
