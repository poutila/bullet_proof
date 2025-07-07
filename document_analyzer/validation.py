#!/usr/bin/env python3
"""
Input validation and sanitization module.

Provides comprehensive validation functions to ensure security and data integrity
according to CLAUDE.md requirements.
"""
import re
from pathlib import Path
from typing import Optional, List, Union, Any
import logging

from document_analyzer.config import (
    MAX_FILE_PATH_LENGTH,
    MAX_FILE_SIZE_MB,
    ALLOWED_BASE_PATHS,
    ERROR_MESSAGES,
    VALIDATION_RULES
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


def validate_file_path(
    path: Union[str, Path],
    must_exist: bool = True,
    allowed_extensions: Optional[List[str]] = None
) -> Path:
    """
    Validate and sanitize file path to prevent security issues.
    
    Args:
        path: File path to validate
        must_exist: Whether the file must exist
        allowed_extensions: List of allowed file extensions (e.g., ['.md', '.py'])
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path validation fails
        
    Example:
        >>> validate_file_path("/home/user/doc.md", must_exist=True)
        Path('/home/user/doc.md')
    """
    if not path:
        raise ValidationError(ERROR_MESSAGES["empty_input"].format(field="path"))
    
    # Convert to Path object
    try:
        path_obj = Path(str(path)).resolve()
    except (ValueError, RuntimeError) as e:
        raise ValidationError(f"Invalid path format: {path}") from e
    
    # Check for path traversal attempts
    if ".." in str(path):
        raise ValidationError(ERROR_MESSAGES["path_traversal"].format(path=path))
    
    # Check path length
    if len(str(path_obj)) > MAX_FILE_PATH_LENGTH:
        raise ValidationError(f"Path too long: {len(str(path_obj))} > {MAX_FILE_PATH_LENGTH}")
    
    # Validate against allowed base paths
    if ALLOWED_BASE_PATHS:
        allowed = any(
            path_obj.is_relative_to(base.resolve()) or 
            path_obj == base.resolve()
            for base in ALLOWED_BASE_PATHS
        )
        if not allowed:
            raise ValidationError(ERROR_MESSAGES["path_not_allowed"].format(path=path_obj))
    
    # Check file existence if required
    if must_exist and not path_obj.exists():
        raise ValidationError(ERROR_MESSAGES["file_not_found"].format(path=path_obj))
    
    # Validate extension if specified
    if allowed_extensions and path_obj.suffix not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension: {path_obj.suffix}. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size if it exists
    if path_obj.exists() and path_obj.is_file():
        size_mb = path_obj.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise ValidationError(
                ERROR_MESSAGES["file_too_large"].format(
                    max_size=MAX_FILE_SIZE_MB,
                    path=path_obj
                )
            )
    
    logger.debug(f"Validated path: {path_obj}")
    return path_obj


def validate_directory_path(
    path: Union[str, Path],
    must_exist: bool = True,
    create_if_missing: bool = False
) -> Path:
    """
    Validate directory path with security checks.
    
    Args:
        path: Directory path to validate
        must_exist: Whether directory must exist
        create_if_missing: Create directory if it doesn't exist
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    path_obj = validate_file_path(path, must_exist=False)
    
    if must_exist and not path_obj.exists():
        if create_if_missing:
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {path_obj}")
            except OSError as e:
                raise ValidationError(f"Failed to create directory: {path_obj}") from e
        else:
            raise ValidationError(f"Directory not found: {path_obj}")
    
    if path_obj.exists() and not path_obj.is_dir():
        raise ValidationError(f"Path is not a directory: {path_obj}")
    
    return path_obj


def validate_threshold(value: float, name: str = "threshold") -> float:
    """
    Validate threshold values (must be between 0 and 1).
    
    Args:
        value: Threshold value to validate
        name: Name of the threshold for error messages
        
    Returns:
        Validated threshold value
        
    Raises:
        ValidationError: If threshold is invalid
    """
    try:
        float_value = float(value)
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Invalid {name}: must be a number") from e
    
    if not 0 <= float_value <= 1:
        raise ValidationError(
            ERROR_MESSAGES["invalid_threshold"].format(value=float_value)
        )
    
    return float_value


def validate_string_input(
    value: Any,
    field_name: str,
    max_length: Optional[int] = None,
    allowed_values: Optional[List[str]] = None,
    pattern: Optional[str] = None
) -> str:
    """
    Validate and sanitize string input.
    
    Args:
        value: Value to validate
        field_name: Field name for error messages
        max_length: Maximum allowed length
        allowed_values: List of allowed values
        pattern: Regex pattern to match
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If validation fails
    """
    if value is None or str(value).strip() == "":
        raise ValidationError(ERROR_MESSAGES["empty_input"].format(field=field_name))
    
    str_value = str(value).strip()
    
    if max_length and len(str_value) > max_length:
        raise ValidationError(
            f"{field_name} too long: {len(str_value)} > {max_length}"
        )
    
    if allowed_values and str_value not in allowed_values:
        raise ValidationError(
            f"Invalid {field_name}: '{str_value}'. "
            f"Allowed values: {', '.join(allowed_values)}"
        )
    
    if pattern and not re.match(pattern, str_value):
        raise ValidationError(
            f"Invalid {field_name} format: '{str_value}' "
            f"does not match pattern: {pattern}"
        )
    
    return str_value


def validate_list_input(
    value: Any,
    field_name: str,
    min_length: int = 0,
    max_length: Optional[int] = None,
    item_validator: Optional[callable] = None
) -> List[Any]:
    """
    Validate list input with optional item validation.
    
    Args:
        value: List to validate
        field_name: Field name for error messages
        min_length: Minimum list length
        max_length: Maximum list length
        item_validator: Function to validate each item
        
    Returns:
        Validated list
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")
    
    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} too short: {len(value)} < {min_length}"
        )
    
    if max_length and len(value) > max_length:
        raise ValidationError(
            f"{field_name} too long: {len(value)} > {max_length}"
        )
    
    if item_validator:
        validated_items = []
        for i, item in enumerate(value):
            try:
                validated_item = item_validator(item)
                validated_items.append(validated_item)
            except Exception as e:
                raise ValidationError(
                    f"Invalid item at index {i} in {field_name}: {e}"
                ) from e
        return validated_items
    
    return value


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
        
    Raises:
        ValidationError: If filename is invalid
    """
    if not filename:
        raise ValidationError("Filename cannot be empty")
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure filename is not empty after sanitization
    if not sanitized:
        raise ValidationError("Filename invalid after sanitization")
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized
