"""Path resolution functionality for instruction path tracer."""

import logging
from pathlib import Path

from .patterns import COMMON_PREFIXES

logger = logging.getLogger(__name__)


class PathResolver:
    """Resolves and normalizes document paths."""

    def __init__(self, root_dir: Path):
        """Initialize path resolver.

        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = root_dir

    def normalize_path(self, path: str, from_dir: Path) -> Path | None:
        """Normalize a relative path to absolute.

        Args:
            path: Path string to normalize
            from_dir: Directory to resolve relative paths from

        Returns:
            Normalized absolute path or None if not found
        """
        # Skip URLs
        if path.startswith("http"):
            return None

        # Clean up relative path markers
        if path.startswith("./"):
            path = path[2:]

        # Try resolving from the given directory
        if path.startswith("../"):
            resolved = (from_dir / path).resolve()
        else:
            resolved = from_dir / path

        # Check if file exists at resolved path
        if resolved.exists():
            return resolved

        # Try from root
        root_resolved = self.root_dir / path
        if root_resolved.exists():
            return root_resolved

        # Try common directory prefixes
        for prefix in COMMON_PREFIXES:
            test_path = self.root_dir / prefix / path
            if test_path.exists():
                return test_path

        return None

    def find_file_in_project(self, filename: str, search_paths: list[str]) -> Path | None:
        """Find a file in the project using search paths.

        Args:
            filename: Name of the file to find
            search_paths: List of paths to search in

        Returns:
            Path to the found file or None
        """
        # Clean up the filename
        clean_file = filename.lstrip("./")

        for search_path in search_paths:
            test_path = self.root_dir / search_path / clean_file
            if test_path.exists():
                return test_path

        return None
