#!/usr/bin/env python3
"""Generate FILES_REQUIRED.md by scanning project documentation files.

This script scans all markdown files in the project to find referenced files
and generates a comprehensive index organized by file type. Follows CLAUDE.md
standards for security, error handling, and code quality.
"""
import re
import sys
import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Pattern, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_PATH_LENGTH = 255
MAX_FILES_PER_TYPE = 1000
SUPPORTED_FILE_EXTENSIONS = ('.py', '.md', '.yml', '.yaml', '.json', '.toml', '.txt')

# File type groups for organization
FILE_TYPE_GROUPS = {
    ".md": "📄 Markdown Documentation",
    ".py": "🐍 Python Scripts",
    ".yml": "⚙️ CI/CD Workflows",
    ".yaml": "⚙️ CI/CD Workflows",
    ".json": "🧩 JSON Configurations",
    ".toml": "📦 Python Build Configs",
    ".txt": "📝 Plain Text Files",
}

# Regex to match file paths in markdown code or links
FILE_PATTERN: Pattern[str] = re.compile(
    r'(?:["\'`(]|\b)([\w./-]+\.(?:py|md|yml|yaml|json|toml|txt))(?:[)"\'`]|\b)'
)


class ValidationError(Exception):
    """Raised when file validation fails."""
    pass


@dataclass
class ScanResult:
    """Results from scanning markdown files.
    
    Attributes:
        found_files: Dictionary mapping file extensions to sets of file paths
        errors: List of error messages encountered during scanning
        warnings: List of warning messages
        scanned_count: Number of markdown files scanned
    """
    found_files: Dict[str, Set[str]]
    errors: List[str]
    warnings: List[str]
    scanned_count: int


class FileScanner:
    """Scans markdown files for file references with validation and error handling."""
    
    def __init__(self, docs_root: Optional[Path] = None) -> None:
        """Initialize file scanner.
        
        Args:
            docs_root: Root directory to scan. Defaults to parent of script location.
            
        Raises:
            ValueError: If docs_root is invalid
        """
        if docs_root is None:
            self.docs_root = Path(__file__).parent
        else:
            self.docs_root = docs_root
            
        if not self.docs_root.exists():
            raise ValueError(f"Directory does not exist: {self.docs_root}")
            
        if not self.docs_root.is_dir():
            raise ValueError(f"Path is not a directory: {self.docs_root}")
    
    def validate_file_path(self, file_path: str) -> bool:
        """Validate file path for security and format.
        
        Args:
            file_path: File path to validate
            
        Returns:
            True if path is valid, False otherwise
        """
        if not file_path or len(file_path) > MAX_FILE_PATH_LENGTH:
            return False
            
        # Security check: no parent directory traversal
        if '..' in file_path:
            logger.warning(f"Rejected path with parent directory traversal: {file_path}")
            return False
            
        # Security check: no absolute paths
        if file_path.startswith('/') or (len(file_path) > 2 and file_path[1] == ':'):
            logger.warning(f"Rejected absolute path: {file_path}")
            return False
            
        # Must have valid extension
        if not any(file_path.endswith(ext) for ext in SUPPORTED_FILE_EXTENSIONS):
            return False
            
        return True
    
    def scan_markdown_files(self) -> ScanResult:
        """Scan markdown files for file references with error handling.
        
        Returns:
            ScanResult containing found files and any errors/warnings
            
        Raises:
            IOError: If unable to access the docs root directory
        """
        found_files: Dict[str, Set[str]] = defaultdict(set)
        errors: List[str] = []
        warnings: List[str] = []
        scanned_count = 0
        
        try:
            # Find all markdown files
            md_files = list(self.docs_root.rglob("*.md"))
            
            if not md_files:
                warnings.append(f"No markdown files found in {self.docs_root}")
                logger.warning(f"No markdown files found in {self.docs_root}")
                return ScanResult(found_files, errors, warnings, 0)
            
            logger.info(f"Found {len(md_files)} markdown files to scan")
            
            # Process each markdown file
            for md_file in md_files:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    matches = FILE_PATTERN.findall(content)
                    scanned_count += 1
                    
                    for match in matches:
                        if self.validate_file_path(match):
                            ext = Path(match).suffix
                            if ext in SUPPORTED_FILE_EXTENSIONS:
                                found_files[ext].add(match)
                                
                                # Warn if too many files of one type
                                if len(found_files[ext]) > MAX_FILES_PER_TYPE:
                                    warning = f"Found over {MAX_FILES_PER_TYPE} {ext} files"
                                    if warning not in warnings:
                                        warnings.append(warning)
                                        
                except IOError as e:
                    error_msg = f"Failed to read {md_file}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                except Exception as e:
                    error_msg = f"Unexpected error processing {md_file}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                    
        except Exception as e:
            error_msg = f"Failed to scan markdown files: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            raise IOError(error_msg) from e
            
        logger.info(f"Scanned {scanned_count} files, found {sum(len(files) for files in found_files.values())} references")
        return ScanResult(found_files, errors, warnings, scanned_count)


class ReportGenerator:
    """Generates the FILES_REQUIRED.md report."""
    
    def __init__(self, output_path: Path = Path("FILES_REQUIRED.md")) -> None:
        """Initialize report generator.
        
        Args:
            output_path: Path where the report will be written
        """
        self.output_path = output_path
    
    def generate_report(self, scan_result: ScanResult) -> None:
        """Generate FILES_REQUIRED.md from scan results.
        
        Args:
            scan_result: Results from file scanning
            
        Raises:
            IOError: If unable to write the output file
        """
        output_lines: List[str] = [
            "# 📁 FILES_REQUIRED.md",
            "",
            "This file is auto-generated by `generate_files_required.py`.",
            "",
            f"**Last Generated**: {Path(__file__).stat().st_mtime}",
            f"**Files Scanned**: {scan_result.scanned_count}",
            f"**Total References Found**: {sum(len(files) for files in scan_result.found_files.values())}",
            ""
        ]
        
        # Add any warnings
        if scan_result.warnings:
            output_lines.extend([
                "## ⚠️ Warnings",
                ""
            ])
            for warning in scan_result.warnings:
                output_lines.append(f"- {warning}")
            output_lines.append("")
        
        # Add any errors
        if scan_result.errors:
            output_lines.extend([
                "## ❌ Errors",
                ""
            ])
            for error in scan_result.errors:
                output_lines.append(f"- {error}")
            output_lines.append("")
        
        # Add file groups
        for ext in sorted(scan_result.found_files.keys()):
            group_title = FILE_TYPE_GROUPS.get(ext, f"Other ({ext})")
            files = sorted(scan_result.found_files[ext])
            
            output_lines.extend([
                f"## {group_title}",
                "",
                f"**Count**: {len(files)}",
                ""
            ])
            
            for file_path in files:
                output_lines.append(f"- `{file_path}`")
            output_lines.append("")
        
        # Write the report
        try:
            self.output_path.write_text("\n".join(output_lines), encoding="utf-8")
            logger.info(f"Report written to {self.output_path}")
        except IOError as e:
            error_msg = f"Failed to write report to {self.output_path}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg) from e


def main() -> None:
    """Main entry point for the script.
    
    Scans markdown files and generates FILES_REQUIRED.md report.
    """
    try:
        # Initialize scanner
        scanner = FileScanner()
        
        # Scan for file references
        logger.info("Starting markdown file scan...")
        scan_result = scanner.scan_markdown_files()
        
        # Generate report
        generator = ReportGenerator()
        generator.generate_report(scan_result)
        
        # Print summary
        total_files = sum(len(files) for files in scan_result.found_files.values())
        print(f"✅ FILES_REQUIRED.md generated successfully!")
        print(f"📊 Scanned {scan_result.scanned_count} markdown files")
        print(f"📁 Found {total_files} file references")
        
        if scan_result.warnings:
            print(f"⚠️  {len(scan_result.warnings)} warnings")
            
        if scan_result.errors:
            print(f"❌ {len(scan_result.errors)} errors")
            sys.exit(1)
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except IOError as e:
        logger.error(f"IO error: {e}")
        print(f"❌ IO error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()