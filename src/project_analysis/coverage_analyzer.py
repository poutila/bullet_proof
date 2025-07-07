"""Coverage analysis functionality for instruction path tracer."""

import logging
import re
from pathlib import Path

from .instruction_node import InstructionNode
from .path_resolver import PathResolver
from .patterns import ARCHITECTURE_TERMS, CI_CD_TERMS, FILE_SEARCH_PATHS, TEST_TERMS

logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """Analyzes coverage of various aspects in documentation."""

    def __init__(self, root_dir: Path):
        """Initialize coverage analyzer.

        Args:
            root_dir: Root directory of the project
        """
        self.root_dir = root_dir
        self.path_resolver = PathResolver(root_dir)

    def check_coverage(self, root_node: InstructionNode) -> dict[str, list[str]]:
        """Check coverage of various aspects.

        Args:
            root_node: Root node of the instruction tree

        Returns:
            Dictionary mapping coverage aspects to found items
        """
        coverage: dict[str, list[str]] = {
            "file_generation": [],
            "ci_cd": [],
            "test_automation": [],
            "architecture": [],
            "implementation": [],
        }

        self._traverse_for_coverage(root_node, coverage)
        return coverage

    def _traverse_for_coverage(self, node: InstructionNode, coverage: dict[str, list[str]]) -> None:
        """Traverse tree and collect coverage information.

        Args:
            node: Current node to analyze
            coverage: Coverage dictionary to update
        """
        # Check for file generation
        for gen_file in node.generates:
            coverage["file_generation"].append(f"{node.path.name}: {gen_file}")

        # Check document content for various aspects
        try:
            content = node.path.read_text().lower()

            # Check for CI/CD mentions
            if any(term in content for term in CI_CD_TERMS):
                coverage["ci_cd"].append(node.path.name)

            # Check for test automation
            if any(term in content for term in TEST_TERMS):
                coverage["test_automation"].append(node.path.name)

            # Check for architecture
            if any(term in content for term in ARCHITECTURE_TERMS):
                coverage["architecture"].append(node.path.name)

        except Exception as e:
            logger.warning(f"Failed to read {node.path}: {e}")

        # Check for implementation instructions
        if node.instructions:
            coverage["implementation"].append(f"{node.path.name}: {len(node.instructions)} instructions")

        # Traverse children
        for child in node.children:
            self._traverse_for_coverage(child, coverage)

    def check_files_required_alignment(self) -> dict[str, bool]:
        """Check alignment with FILES_REQUIRED.md.

        Returns:
            Dictionary mapping required files to existence status
        """
        files_required_path = self.root_dir / "FILES_REQUIRED.md"
        if not files_required_path.exists():
            return {}

        content = files_required_path.read_text()
        required_files = self._extract_required_files(content)

        # Check which files exist
        alignment = {}
        for req_file in required_files:
            exists = self._check_file_exists(req_file)
            alignment[req_file] = exists

        return alignment

    def _extract_required_files(self, content: str) -> set[str]:
        """Extract required files from FILES_REQUIRED.md content.

        Args:
            content: Content of FILES_REQUIRED.md

        Returns:
            Set of required file names
        """
        required_files = set()

        # Pattern for bullet point files: - `filename`
        bullet_pattern = r"-\s+`([^`]+\.(py|yml|yaml|md|json|toml|txt|sh|cfg|ini))`"
        for match in re.finditer(bullet_pattern, content):
            required_files.add(match.group(1))

        # Pattern for tree structure files
        tree_pattern = r"[│├└]\s*([^\s]+\.(py|yml|yaml|md|json|toml|txt|sh|cfg|ini))"
        for match in re.finditer(tree_pattern, content):
            required_files.add(match.group(1))

        # Pattern for direct filenames in text
        direct_pattern = r"`([^`]+\.(py|yml|yaml|md|json|toml|txt|sh|cfg|ini))`"
        for match in re.finditer(direct_pattern, content):
            filename = match.group(1)
            # Skip if it's part of a path or code example
            if not any(skip in filename for skip in ["/", "test_", "example"]):
                required_files.add(filename)

        return required_files

    def _check_file_exists(self, filename: str) -> bool:
        """Check if a required file exists in the project.

        Args:
            filename: Name of the file to check

        Returns:
            True if file exists, False otherwise
        """
        result = self.path_resolver.find_file_in_project(filename, FILE_SEARCH_PATHS)
        return result is not None
