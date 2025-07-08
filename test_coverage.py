#!/usr/bin/env python3
"""Test coverage analysis tool.

Maps Python source files to their test files and vice versa,
generating a coverage report to identify missing tests.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple


def find_python_files(directory: Path, exclude_dirs: set[str] | None = None) -> List[Path]:
    """Find all Python files in a directory, excluding specified subdirectories.
    
    Args:
        directory: Directory to search
        exclude_dirs: Set of directory names to exclude
        
    Returns:
        List of Python file paths
    """
    if exclude_dirs is None:
        exclude_dirs = {"__pycache__", ".venv", "venv", ".git"}
    
    python_files = []
    
    for file_path in directory.rglob("*.py"):
        # Skip if in excluded directory
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue
        # Skip __init__.py files
        if file_path.name == "__init__.py":
            continue
        python_files.append(file_path)
    
    return sorted(python_files)


def get_test_file_name(src_file: Path) -> str:
    """Get the expected test file name for a source file.
    
    Args:
        src_file: Source file path
        
    Returns:
        Expected test file name
    """
    if src_file.name.startswith("test_"):
        return src_file.name
    return f"test_{src_file.name}"


def find_test_file(src_file: Path, test_files: List[Path]) -> Path | None:
    """Find the test file for a given source file.
    
    Args:
        src_file: Source file path
        test_files: List of all test files
        
    Returns:
        Test file path if found, None otherwise
    """
    expected_name = get_test_file_name(src_file)
    
    # Try to find test file with matching name
    for test_file in test_files:
        if test_file.name == expected_name:
            return test_file
    
    # Try to find test file in a subdirectory with similar structure
    src_parts = src_file.relative_to(Path("src")).parts
    for test_file in test_files:
        test_parts = test_file.relative_to(Path("tests")).parts
        if len(test_parts) > 1 and test_parts[-1] == expected_name:
            # Check if directory structure matches
            if len(src_parts) == len(test_parts):
                if all(sp == tp for sp, tp in zip(src_parts[:-1], test_parts[:-1])):
                    return test_file
    
    return None


def find_source_file(test_file: Path, src_files: List[Path]) -> Path | None:
    """Find the source file for a given test file.
    
    Args:
        test_file: Test file path
        src_files: List of all source files
        
    Returns:
        Source file path if found, None otherwise
    """
    # Remove test_ prefix if present
    if test_file.name.startswith("test_"):
        expected_name = test_file.name[5:]
    else:
        return None
    
    # Try to find source file with matching name
    for src_file in src_files:
        if src_file.name == expected_name:
            return src_file
    
    # Try to find source file in a subdirectory with similar structure
    test_parts = test_file.relative_to(Path("tests")).parts
    for src_file in src_files:
        src_parts = src_file.relative_to(Path("src")).parts
        if src_parts[-1] == expected_name:
            # Check if directory structure matches
            if len(src_parts) == len(test_parts):
                if all(sp == tp for sp, tp in zip(src_parts[:-1], test_parts[:-1])):
                    return src_file
    
    return None


def analyze_test_coverage() -> Tuple[Dict[str, str | None], Dict[str, str | None]]:
    """Analyze test coverage by mapping source files to test files.
    
    Returns:
        Tuple of (src_to_test, test_to_src) dictionaries
    """
    src_dir = Path("src")
    tests_dir = Path("tests")
    
    # Find all Python files
    src_files = find_python_files(src_dir)
    test_files = find_python_files(tests_dir)
    
    # Map source files to test files
    src_to_test: Dict[str, str | None] = {}
    for src_file in src_files:
        test_file = find_test_file(src_file, test_files)
        src_to_test[str(src_file)] = str(test_file) if test_file else None
    
    # Map test files to source files
    test_to_src: Dict[str, str | None] = {}
    for test_file in test_files:
        src_file = find_source_file(test_file, src_files)
        test_to_src[str(test_file)] = str(src_file) if src_file else None
    
    return src_to_test, test_to_src


def generate_coverage_report(src_to_test: Dict[str, str | None], test_to_src: Dict[str, str | None]) -> str:
    """Generate a markdown report of test coverage.
    
    Args:
        src_to_test: Dictionary mapping source files to test files
        test_to_src: Dictionary mapping test files to source files
        
    Returns:
        Markdown formatted report
    """
    from datetime import datetime
    
    report = "# Test Coverage Report\n\n"
    report += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Summary statistics
    total_src_files = len(src_to_test)
    src_with_tests = sum(1 for v in src_to_test.values() if v is not None)
    src_without_tests = total_src_files - src_with_tests
    coverage_percentage = (src_with_tests / total_src_files * 100) if total_src_files > 0 else 0
    
    total_test_files = len(test_to_src)
    orphan_tests = sum(1 for v in test_to_src.values() if v is None)
    
    report += "## Summary\n\n"
    report += f"- Total source files: {total_src_files}\n"
    report += f"- Source files with tests: {src_with_tests} ({coverage_percentage:.1f}%)\n"
    report += f"- Source files without tests: {src_without_tests}\n"
    report += f"- Total test files: {total_test_files}\n"
    report += f"- Orphan test files: {orphan_tests}\n\n"
    
    # Coverage assessment
    report += "## Coverage Assessment\n\n"
    if coverage_percentage >= 90:
        report += "✅ **Excellent**: Test coverage is above 90%\n"
    elif coverage_percentage >= 80:
        report += "✅ **Good**: Test coverage is above 80%\n"
    elif coverage_percentage >= 70:
        report += "⚠️ **Adequate**: Test coverage is above 70% but could be improved\n"
    elif coverage_percentage >= 50:
        report += "⚠️ **Poor**: Test coverage is below 70% and needs improvement\n"
    else:
        report += "❌ **Critical**: Test coverage is below 50% and requires immediate attention\n"
    
    report += "\n"
    
    # Source files without tests
    if src_without_tests > 0:
        report += "## Source Files Without Tests\n\n"
        report += "The following source files do not have corresponding test files:\n\n"
        for src_file, test_file in sorted(src_to_test.items()):
            if test_file is None:
                report += f"- `{src_file}`\n"
        report += "\n"
    
    # Orphan test files
    if orphan_tests > 0:
        report += "## Orphan Test Files\n\n"
        report += "The following test files do not have corresponding source files:\n\n"
        for test_file, src_file in sorted(test_to_src.items()):
            if src_file is None:
                report += f"- `{test_file}`\n"
        report += "\n"
    
    # Detailed mapping
    report += "## Source to Test Mapping\n\n"
    report += "| Source File | Test File | Status |\n"
    report += "|-------------|-----------|--------|\n"
    
    for src_file, test_file in sorted(src_to_test.items()):
        status = "✅" if test_file else "❌"
        test_display = test_file if test_file else "**Missing**"
        report += f"| `{src_file}` | `{test_display}` | {status} |\n"
    
    report += "\n"
    
    # Test to source mapping (only for files with mappings)
    mapped_tests = {k: v for k, v in test_to_src.items() if v is not None}
    if mapped_tests:
        report += "## Test to Source Mapping\n\n"
        report += "| Test File | Source File |\n"
        report += "|-----------|-------------|\n"
        
        for test_file, src_file in sorted(mapped_tests.items()):
            report += f"| `{test_file}` | `{src_file}` |\n"
    
    return report


def main():
    """Main function to analyze test coverage and generate report."""
    print("Analyzing test coverage...")
    
    # Analyze coverage
    src_to_test, test_to_src = analyze_test_coverage()
    
    # Generate report
    report = generate_coverage_report(src_to_test, test_to_src)
    
    # Write report to file
    report_path = Path("TEST_COVERAGE.md")
    report_path.write_text(report)
    print(f"Test coverage report written to {report_path}")
    
    # Also save raw data as JSON for potential future use
    data = {
        "src_to_test": src_to_test,
        "test_to_src": test_to_src
    }
    
    json_path = Path("test_coverage.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Raw coverage data written to {json_path}")
    
    # Print summary
    total_src = len(src_to_test)
    with_tests = sum(1 for v in src_to_test.values() if v is not None)
    coverage = (with_tests / total_src * 100) if total_src > 0 else 0
    
    print(f"\nSummary:")
    print(f"  Source files: {total_src}")
    print(f"  With tests: {with_tests}")
    print(f"  Coverage: {coverage:.1f}%")


if __name__ == "__main__":
    main()