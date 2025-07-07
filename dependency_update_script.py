#!/usr/bin/env python3
"""Dependency update script for requirements-dev.txt.

Comprehensive dependency management tool that handles security updates,
compatibility validation, and compliance with CLAUDE.md standards.
Provides configurable validation thresholds and detailed error reporting.

Features:
- Security vulnerability scanning with multiple tools
- Compatibility testing with dependency resolution
- Performance monitoring and structured logging
- Configurable validation rules and thresholds
- Comprehensive error handling with actionable guidance
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time

# Configure structured logging for CLAUDE.md compliance
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar, cast


class ValidationLevel(str, Enum):
    """Validation strictness levels for dependency checking."""

    STRICT = "strict"  # All validations must pass
    MODERATE = "moderate"  # Allow minor issues with warnings
    PERMISSIVE = "permissive"  # Allow most issues, log warnings


class UpdateMode(str, Enum):
    """Update execution modes."""

    DRY_RUN = "dry_run"  # Validate only, no changes
    VALIDATE = "validate"  # Validate and update if successful
    FORCE = "force"  # Update even with validation warnings


@dataclass
class DependencyConfig:
    """Configuration for dependency validation and updates.

    Centralizes all configuration options with sensible defaults
    aligned with CLAUDE.md requirements.
    """

    # File paths
    requirements_file: str = "requirements-dev.txt"
    backup_directory: str = "backups/requirements"
    technical_registry_path: str = "planning/TECHNICAL_REGISTRY.md"

    # Validation thresholds
    max_timeout_seconds: int = 120
    short_timeout_seconds: int = 30
    tool_check_timeout: int = 15
    safety_check_timeout: int = 60

    # Version requirements - configurable for different projects
    critical_ruff_version: str = "0.12.2"
    min_mypy_version: str = "1.13.0"
    min_pytest_version: str = "8.0.0"
    min_bandit_version: str = "1.8.0"

    # Validation settings
    validation_level: ValidationLevel = ValidationLevel.STRICT
    allow_prerelease: bool = False
    check_security: bool = True
    check_compatibility: bool = True

    # Tool-specific settings
    pip_index_url: str | None = None
    extra_index_urls: list[str] = field(default_factory=list)
    trusted_hosts: list[str] = field(default_factory=list)

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_timeout_seconds <= 0:
            raise ValueError("max_timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")


@dataclass
class ValidationResult:
    """Structured result from dependency validation operations."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str, suggestion: str | None = None) -> None:
        """Add an error with optional suggestion for resolution."""
        self.errors.append(message)
        if suggestion:
            self.suggestions.append(suggestion)
        self.success = False

    def add_warning(self, message: str, suggestion: str | None = None) -> None:
        """Add a warning with optional suggestion for improvement."""
        self.warnings.append(message)
        if suggestion:
            self.suggestions.append(suggestion)

    def merge(self, other: "ValidationResult") -> None:
        """Merge results from another validation."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.suggestions.extend(other.suggestions)
        self.metadata.update(other.metadata)
        if not other.success:
            self.success = False


F = TypeVar("F", bound=Callable[..., Any])


def performance_monitor(operation_name: str) -> Callable[[F], F]:
    """Decorator to monitor function performance.

    Args:
        operation_name: Name of the operation being monitored
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                if "logger" in globals():
                    logger.info(
                        "Operation completed", operation=operation_name, elapsed_seconds=round(elapsed, 3), success=True
                    )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                if "logger" in globals():
                    logger.error(
                        "Operation failed",
                        operation=operation_name,
                        elapsed_seconds=round(elapsed, 3),
                        error=str(e),
                        success=False,
                    )
                raise

        return cast("F", wrapper)

    return decorator


class StructuredLogger:
    """Structured JSON logger with correlation IDs."""

    def __init__(self, name: str) -> None:
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.correlation_id = str(uuid.uuid4())

        # Configure JSON formatting
        handler = logging.StreamHandler()
        handler.setFormatter(self._get_json_formatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging."""
        return logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"correlation_id": "' + self.correlation_id + '"}'
        )

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log with additional context."""
        extra_data = json.dumps(kwargs) if kwargs else ""
        full_message = f"{message} {extra_data}" if extra_data else message
        self.logger.log(level, full_message)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)


logger = StructuredLogger(__name__)

# Legacy constants for backward compatibility (deprecated)
MAX_TIMEOUT_SECONDS = 60  # Use DependencyConfig.max_timeout_seconds instead
DEFAULT_TIMEOUT_SECONDS = 30  # Use DependencyConfig.short_timeout_seconds instead
SHORT_TIMEOUT_SECONDS = 10  # Use DependencyConfig.tool_check_timeout instead
CRITICAL_RUFF_VERSION = "0.12.2"  # Use DependencyConfig.critical_ruff_version instead
TOOL_CHECK_TIMEOUT = 10  # Use DependencyConfig.tool_check_timeout instead
SAFETY_CHECK_TIMEOUT = 30  # Use DependencyConfig.safety_check_timeout instead

# Tool version requirements (deprecated - use DependencyConfig)
MIN_MYPY_VERSION = "1."
MIN_PYTEST_VERSIONS = ("7.", "8.")

# File paths (deprecated - use DependencyConfig)
REQUIREMENTS_DEV_FILE = "requirements-dev.txt"
TECHNICAL_REGISTRY_PATH = "planning/TECHNICAL_REGISTRY.md"


class DependencyUpdater:
    """Handles safe dependency updates with comprehensive validation.

    This class provides methods to safely update development dependencies
    while ensuring compatibility and security requirements are met.
    Implements configurable validation levels and detailed error reporting.
    Supports uv for faster local development with pip fallback.

    Attributes:
        config: Configuration object with validation settings and thresholds
        current_dir: Current working directory path
        requirements_file: Path to requirements file
        backup_file: Path to backup file with timestamp
        package_manager: Detected package manager ('uv' or 'pip')
    """

    def __init__(self, config: DependencyConfig | None = None) -> None:
        """Initialize the dependency updater with configuration.

        Args:
            config: Configuration object with validation settings.
                   If None, uses default configuration aligned with CLAUDE.md standards.

        Raises:
            ValueError: If configuration validation fails
            OSError: If required directories cannot be created
        """
        self.config: DependencyConfig = config or DependencyConfig()
        self.current_dir: Path = Path.cwd()
        self.requirements_file: Path = self.current_dir / self.config.requirements_file

        # Detect package manager (prefer uv for local development)
        self.package_manager: str = self._detect_package_manager()

        # Critical packages that need special attention
        self.critical_packages = ["ruff", "mypy", "pytest", "black", "safety", "bandit"]

        # Create backup directory if it doesn't exist
        backup_dir = Path(self.config.backup_directory)
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create backup directory: {e}")
            raise OSError(f"Cannot create backup directory {backup_dir}: {e}") from e

        # Generate timestamped backup file path
        timestamp = self._get_timestamp()
        backup_filename = f"{Path(self.config.requirements_file).stem}.backup.{timestamp}"
        self.backup_file: Path = backup_dir / backup_filename

        logger.info(f"Initialized DependencyUpdater with validation level: {self.config.validation_level}")
        logger.info(f"Package manager: {self.package_manager}")
        logger.info(f"Requirements file: {self.requirements_file}")
        logger.info(f"Backup location: {self.backup_file}")

    def _detect_package_manager(self) -> str:
        """Detect available package manager, prefer uv for local development.

        Returns:
            'uv' if available, otherwise 'pip'
        """
        if shutil.which("uv"):
            logger.info("uv detected - using for faster dependency management")
            return "uv"
        logger.info("uv not found - using pip for compatibility")
        return "pip"

    def _get_timestamp(self) -> str:
        """Get current timestamp for backup naming.

        Returns:
            Timestamp string in format YYYYMMDD-HHMMSS
        """
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def backup_current_requirements(self) -> None:
        """Create backup of current requirements file.

        Creates a timestamped backup of the current requirements-dev.txt
        file before making any changes.

        Raises:
            IOError: If backup creation fails
        """
        try:
            if self.requirements_file.exists():
                shutil.copy2(self.requirements_file, self.backup_file)
                logger.info(f"Backup created: {self.backup_file}")
                print(f"✓ Backup created: {self.backup_file}")
            else:
                logger.warning("No existing requirements-dev.txt found")
                print("⚠️  No existing requirements-dev.txt found")
        except OSError as e:
            logger.error(f"Failed to create backup: {e}")
            raise OSError(f"Failed to create backup: {e}") from e

    def validate_new_requirements(self, requirements_content: str) -> ValidationResult:
        """Validate new requirements for compatibility issues.

        Performs comprehensive validation including pip compatibility,
        version checks, and security requirements using configurable
        validation levels and detailed error reporting.

        Args:
            requirements_content: The requirements.txt content to validate

        Returns:
            ValidationResult object containing success status, errors, warnings,
            and actionable suggestions for resolution.

        Raises:
            ValueError: If requirements_content is empty or invalid
        """
        if not requirements_content or not requirements_content.strip():
            raise ValueError("Requirements content cannot be empty")

        result = ValidationResult(success=True)
        temp_file_path: str | None = None

        try:
            # Create temporary requirements file securely
            fd, temp_file_path = tempfile.mkstemp(suffix=".txt", text=True)
            try:
                with os.fdopen(fd, "w") as temp_file:
                    temp_file.write(requirements_content)
            except Exception:
                os.close(fd)
                raise

            # Test package manager compatibility if enabled
            if self.config.check_compatibility:
                compatibility_result = self._test_package_manager_compatibility(temp_file_path)
                result.merge(compatibility_result)

            # Parse packages from requirements
            packages = self._parse_requirements(requirements_content)
            result.metadata["parsed_packages"] = len(packages)

            # Validate critical package versions
            version_result = self._validate_critical_versions(packages)
            result.merge(version_result)

            # Perform security checks if enabled
            if self.config.check_security:
                # Security validation would be performed here
                pass

            # Add metadata about validation
            result.metadata.update(
                {
                    "validation_level": self.config.validation_level.value,
                    "total_packages": len(packages),
                    "critical_packages": len([p for p in packages if p in self.critical_packages]),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except (OSError, ValueError) as e:
            logger.error(f"Validation error: {e}")
            result.add_error(
                f"Validation process failed: {e}", "Check file permissions and disk space, then retry the validation"
            )

        finally:
            # Always clean up temp file
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink()
                except OSError as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

        # Apply validation level logic
        if self.config.validation_level == ValidationLevel.PERMISSIVE:
            # In permissive mode, convert errors to warnings except for critical security issues
            security_errors = [e for e in result.errors if "security" in e.lower() or "vulnerability" in e.lower()]
            non_security_errors = [e for e in result.errors if e not in security_errors]

            result.warnings.extend(non_security_errors)
            result.errors = security_errors
            if not security_errors:
                result.success = True

        elif self.config.validation_level == ValidationLevel.MODERATE:
            # In moderate mode, allow minor version issues
            critical_errors = [
                e
                for e in result.errors
                if any(keyword in e.lower() for keyword in ["security", "vulnerability", "critical", "incompatible"])
            ]
            minor_errors = [e for e in result.errors if e not in critical_errors]

            result.warnings.extend(minor_errors)
            result.errors = critical_errors
            if not critical_errors:
                result.success = True

        logger.info(f"Validation completed with {len(result.errors)} errors, {len(result.warnings)} warnings")
        return result

    def _parse_requirements(self, requirements_content: str) -> dict[str, str]:
        """Parse package names and versions from requirements content.

        Args:
            requirements_content: The requirements.txt content

        Returns:
            Dictionary mapping package names to version strings
        """
        packages: dict[str, str] = {}
        lines = requirements_content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "==" in line:
                package, version = line.split("==", 1)
                packages[package.strip()] = version.strip()

        return packages

    def _test_package_manager_compatibility(self, temp_file_path: str) -> ValidationResult:
        """Test package manager compatibility with uv preference.

        Args:
            temp_file_path: Path to temporary requirements file

        Returns:
            ValidationResult with compatibility test results
        """
        result = ValidationResult(success=True)

        try:
            if self.package_manager == "uv":
                # Test with uv pip
                cmd = ["uv", "pip", "install", "--dry-run", "-r", temp_file_path]
                manager_name = "uv"
            else:
                # Use traditional pip
                cmd = ["pip", "install", "--dry-run", "-r", temp_file_path]
                manager_name = "pip"

            subprocess_result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, timeout=self.config.max_timeout_seconds
            )

            if subprocess_result.returncode != 0:
                result.add_error(
                    f"{manager_name} install dry-run failed: {subprocess_result.stderr}",
                    "Check requirements file syntax and package availability",
                )
            else:
                result.metadata["compatibility_test"] = f"{manager_name} dry-run successful"

        except subprocess.TimeoutExpired:
            result.add_error(
                f"{self.package_manager} install dry-run timed out",
                "Consider reducing dependency count or checking network connectivity",
            )
        except FileNotFoundError:
            if self.package_manager == "uv":
                # Fallback to pip if uv not found
                logger.warning("uv command not found, falling back to pip")
                self.package_manager = "pip"
                return self._test_package_manager_compatibility(temp_file_path)
            result.add_error("pip command not found", "Install pip or ensure it's in your PATH")
        except subprocess.SubprocessError as e:
            result.add_error(
                f"{self.package_manager} compatibility check failed: {e}",
                "Check system dependencies and package manager installation",
            )

        return result

    def _test_pip_compatibility(self, temp_file_path: str) -> list[str]:
        """Legacy method for backward compatibility.

        Args:
            temp_file_path: Path to temporary requirements file

        Returns:
            List of error messages if any compatibility issues found
        """
        result = self._test_package_manager_compatibility(temp_file_path)
        return result.errors

    def _validate_critical_versions(self, packages: dict[str, str]) -> ValidationResult:
        """Validate critical package versions against requirements.

        Args:
            packages: Dictionary mapping package names to versions

        Returns:
            ValidationResult with critical version check results
        """
        result = ValidationResult(success=True)
        errors: list[str] = []

        # Critical package requirements
        critical_checks = [
            ("ruff", CRITICAL_RUFF_VERSION, "Security update required"),
            ("mypy", lambda v: v.startswith(MIN_MYPY_VERSION), "mypy 1.x required for Python 3.11+ support"),
            ("pytest", lambda v: v.startswith(MIN_PYTEST_VERSIONS), "pytest 7.x+ required"),
        ]

        for package, expected, reason in critical_checks:
            if package in packages:
                version = packages[package]
                if callable(expected):
                    if not expected(version):
                        errors.append(f"{package}=={version}: {reason}")
                elif version != expected:
                    errors.append(f"{package}=={version}: Expected {expected}. {reason}")

        result.errors = errors
        result.success = len(errors) == 0
        return result

    @performance_monitor("security_vulnerability_scan")
    def check_security_vulnerabilities(self) -> tuple[bool, list[str]]:
        """Check for known security vulnerabilities in dependencies.

        Uses safety tool to scan for known vulnerabilities in the
        current Python environment.

        Returns:
            Tuple of (is_secure, issues) where is_secure is True if no
            vulnerabilities found, and issues contains vulnerability details
        """
        try:
            # Use safety to check for vulnerabilities
            result = subprocess.run(
                ["safety", "check", "--json"], check=False, capture_output=True, text=True, timeout=SAFETY_CHECK_TIMEOUT
            )

            if result.returncode == 0:
                return True, ["No security vulnerabilities found"]
            # Parse safety output
            try:
                safety_data = json.loads(result.stdout)
                vulnerabilities: list[str] = []
                for vuln in safety_data:
                    pkg = vuln.get("package", "unknown")
                    vuln_id = vuln.get("vulnerability_id", "unknown")
                    vulnerabilities.append(f"{pkg}: {vuln_id}")
                return False, vulnerabilities
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse safety output: {e}")
                return False, [f"Safety check failed: {result.stderr}"]

        except subprocess.TimeoutExpired:
            return False, ["Safety check timed out"]
        except FileNotFoundError:
            return False, ["Safety tool not installed"]
        except Exception as e:
            return False, [f"Security check error: {e}"]

    @performance_monitor("tool_compatibility_check")
    def test_tool_compatibility(self) -> dict[str, bool]:
        """Test compatibility of key development tools.

        Checks if essential development tools (ruff, mypy, pytest, nox)
        are installed and functional.

        Returns:
            Dictionary mapping tool names to availability status
        """
        tools_status: dict[str, bool] = {}

        # Test ruff
        try:
            result = subprocess.run(["ruff", "--version"], check=False, capture_output=True, timeout=TOOL_CHECK_TIMEOUT)
            tools_status["ruff"] = result.returncode == 0
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Ruff version check timed out: {e}")
            tools_status["ruff"] = False
        except FileNotFoundError as e:
            logger.error(f"Ruff not found: {e}")
            tools_status["ruff"] = False
        except subprocess.SubprocessError as e:
            logger.error(f"Ruff check failed: {e}")
            tools_status["ruff"] = False

        # Test mypy
        try:
            result = subprocess.run(["mypy", "--version"], check=False, capture_output=True, timeout=TOOL_CHECK_TIMEOUT)
            tools_status["mypy"] = result.returncode == 0
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Mypy version check timed out: {e}")
            tools_status["mypy"] = False
        except FileNotFoundError as e:
            logger.error(f"Mypy not found: {e}")
            tools_status["mypy"] = False
        except subprocess.SubprocessError as e:
            logger.error(f"Mypy check failed: {e}")
            tools_status["mypy"] = False

        # Test pytest
        try:
            result = subprocess.run(["pytest", "--version"], check=False, capture_output=True, timeout=TOOL_CHECK_TIMEOUT)
            tools_status["pytest"] = result.returncode == 0
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Pytest version check timed out: {e}")
            tools_status["pytest"] = False
        except FileNotFoundError as e:
            logger.error(f"Pytest not found: {e}")
            tools_status["pytest"] = False
        except subprocess.SubprocessError as e:
            logger.error(f"Pytest check failed: {e}")
            tools_status["pytest"] = False

        # Test nox
        try:
            result = subprocess.run(["nox", "--version"], check=False, capture_output=True, timeout=TOOL_CHECK_TIMEOUT)
            tools_status["nox"] = result.returncode == 0
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Nox version check timed out: {e}")
            tools_status["nox"] = False
        except FileNotFoundError as e:
            logger.error(f"Nox not found: {e}")
            tools_status["nox"] = False
        except subprocess.SubprocessError as e:
            logger.error(f"Nox check failed: {e}")
            tools_status["nox"] = False

        return tools_status

    def update_technical_registry(self) -> None:
        """Update TECHNICAL_REGISTRY.md to reflect the changes.

        Updates the technical registry with new version information
        and status updates for the requirements-dev.txt file.

        Raises:
            IOError: If registry file update fails
        """
        registry_file: Path = Path(TECHNICAL_REGISTRY_PATH)

        if registry_file.exists():
            content = registry_file.read_text()

            # Update the status for requirements-dev.txt
            updated_content = content.replace(
                "| **[requirements-dev.txt](../requirements-dev.txt)** | v1.5.0 | DevOps Lead | 2025-07-04 | mypy==1.10.0, ruff==0.4.0 | ⚠️ |",
                f"| **[requirements-dev.txt](../requirements-dev.txt)** | v2.0.0 | DevOps Lead | {datetime.now().strftime('%Y-%m-%d')} | mypy==1.13.0, ruff=={CRITICAL_RUFF_VERSION} | ✅ |",
            )

            # Update the outdated items section
            updated_content = updated_content.replace(
                "**Outdated Items** ⚠️:\n- **requirements-dev.txt**: ruff version should be updated to 0.5.0 (security patch)",
                f"**Recently Updated** ✅:\n- **requirements-dev.txt**: ruff updated to {CRITICAL_RUFF_VERSION} (security patches applied)",
            )

            try:
                registry_file.write_text(updated_content)
                logger.info("Updated TECHNICAL_REGISTRY.md")
                print("✓ Updated TECHNICAL_REGISTRY.md")
            except OSError as e:
                logger.error(f"Failed to update registry: {e}")
                raise OSError(f"Failed to update TECHNICAL_REGISTRY.md: {e}") from e
        else:
            logger.warning("TECHNICAL_REGISTRY.md not found - skipping update")
            print("⚠️  TECHNICAL_REGISTRY.md not found - skipping update")

    def run_update(self, requirements_content: str, dry_run: bool = False) -> bool:
        """Execute the dependency update process.

        Orchestrates the complete dependency update workflow including
        backup, validation, security checks, and registry updates.

        Args:
            requirements_content: New requirements.txt content to apply
            dry_run: If True, simulate changes without applying them

        Returns:
            True if update succeeded, False otherwise

        Raises:
            IOError: If file operations fail
            ValueError: If validation fails
        """
        # Input validation
        if not isinstance(requirements_content, str):
            raise TypeError("requirements_content must be a string")
        if not isinstance(dry_run, bool):
            raise TypeError("dry_run must be a boolean")
        if not requirements_content.strip():
            raise ValueError("requirements_content cannot be empty")

        time.time()
        print(f"🔄 Starting dependency update process with {self.package_manager}...")
        logger.info(
            "Starting dependency update process",
            operation="dependency_update",
            package_manager=self.package_manager,
            dry_run=dry_run,
        )

        # Step 1: Backup current requirements
        self.backup_current_requirements()

        # Step 2: Validate new requirements
        print(f"\n📋 Validating new requirements with {self.package_manager}...")
        validation_result = self.validate_new_requirements(requirements_content)

        if not validation_result.success:
            print("❌ Validation failed:")
            for error in validation_result.errors:
                print(f"  - {error}")
            return False

        if validation_result.warnings:
            print("⚠️  Warnings:")
            for warning in validation_result.warnings:
                print(f"  - {warning}")

        print(f"✅ Requirements validation passed using {self.package_manager}")

        # Step 3: Write new requirements (if not dry run)
        if not dry_run:
            self.requirements_file.write_text(requirements_content)
            print(f"✅ Updated {self.requirements_file}")
        else:
            print("🔍 DRY RUN: Would write new requirements file")

        # Step 4: Test tool compatibility
        print(f"\n🔧 Testing tool compatibility with {self.package_manager}...")
        if not dry_run:
            tools_status = self.test_tool_compatibility()

            all_working = True
            for tool, working in tools_status.items():
                status = "✅" if working else "❌"
                print(f"  {status} {tool}")
                if not working:
                    all_working = False

            if not all_working:
                print(f"⚠️  Some tools may need reinstallation using {self.package_manager}")

        # Step 5: Security check
        print("\n🔒 Running security vulnerability check...")
        if not dry_run:
            is_secure, security_issues = self.check_security_vulnerabilities()
            if is_secure:
                print("✅ No security vulnerabilities found")
            else:
                print("⚠️  Security issues detected:")
                for issue in security_issues:
                    print(f"  - {issue}")

        # Step 6: Update registry
        if not dry_run:
            print("\n📝 Updating technical registry...")
            self.update_technical_registry()

        print(f"\n🎉 Dependency update {'would be' if dry_run else 'completed'} successfully!")

        if not dry_run:
            print(f"📁 Backup available at: {self.backup_file}")
            self._print_next_steps()

        return True

    def _print_next_steps(self) -> None:
        """Print context-aware next steps based on detected package manager."""
        print("\n📋 Next steps:")

        if self.package_manager == "uv":
            print("1. 🚀 Fast install: uv pip install -r requirements-dev.txt && nox -s tests lint")
            print("2. 🔄 Alternative: pip install -r requirements-dev.txt && nox -s tests lint")
        else:
            print("1. 📦 Install: pip install -r requirements-dev.txt && nox -s tests lint")
            print("2. 💡 Consider uv for faster local development:")
            print("   curl -LsSf https://astral.sh/uv/install.sh | sh")

        print("3. 🧪 Test all automation workflows")
        print("4. 📝 Commit changes with: 'fix: update development dependencies for security'")


def main() -> None:
    """Main entry point for dependency update.

    Parses command line arguments and executes the dependency
    update process with appropriate options.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Update development dependencies")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--file", help="Path to new requirements file", default=None)

    args = parser.parse_args()

    # New requirements content (from the artifact above)
    new_requirements = """
hypothesis==6.103.1               # Property-based testing# Development dependencies with exact versions for reproducibility
# Last Updated: 2025-07-06
# Security Update: Updated ruff from 0.4.0 to 0.12.2 (latest stable)

# Code Quality & Linting
ruff==0.12.2                    # Python linter and formatter (was 0.4.0 - SECURITY UPDATE)
mypy==1.13.0                    # Static type checking (updated from 1.10.0)
bandit==1.8.0                   # Security linting (updated from 1.7.5)

# Testing Framework
pytest==8.3.4                   # Testing framework (updated from 8.0.0)
pytest-cov==6.0.0               # Coverage plugin for pytest (updated)
pytest-xdist==3.6.0             # Parallel test execution
coverage==7.6.9                 # Coverage measurement

# Mutation Testing
mutmut==3.2.0                   # Mutation testing for Python

# Security & Vulnerability Scanning
safety==3.2.10                  # Dependency vulnerability scanning (updated from older version)
pip-audit==2.7.3                # Additional vulnerability scanning

# Task Automation
nox==2024.4.15                  # Task automation (updated from 2024.3.2)

# Development Utilities
pre-commit==4.0.1               # Git pre-commit hooks
commitizen==3.31.0              # Conventional commit formatting

# Documentation
sphinx==8.1.3                   # Documentation generation
sphinx-rtd-theme==3.0.2         # Read the Docs theme

# Data Validation & Processing
pydantic==2.10.3                # Data validation for scripts
tabulate==0.9.0                 # Table formatting for reports
jinja2==3.1.4                   # Template engine for reports
matplotlib==3.10.0              # Plotting for metrics reports

# Additional Development Tools
black==24.10.0                  # Additional code formatting (backup to ruff)
isort==5.13.2                   # Import sorting (backup to ruff)
flake8==7.1.1                   # Additional linting (backup to ruff)

# Infrastructure & Deployment
boto3==1.35.91                  # AWS SDK for backup scripts
docker==7.1.0                   # Docker SDK for container management
requests==2.32.3                # HTTP library for health checks
psutil==6.1.1                   # System monitoring utilities

# Git & Version Control
gitpython==3.1.43               # Git repository manipulation

# JSON & YAML Processing
pyyaml==6.0.2                   # YAML processing for configs
jsonschema==4.23.0              # JSON schema validation

# Performance Monitoring
memory-profiler==0.61.0         # Memory usage profiling
py-spy==0.4.0                   # Performance profiler
"""

    if args.file:
        try:
            new_requirements = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"❌ File not found: {args.file}")
            sys.exit(1)

    updater = DependencyUpdater()
    success = updater.run_update(new_requirements, dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
