#!/usr/bin/env python3
"""Instruction Path Tracer.

Traces instruction paths from entry point documents (README.md, PLANNING.md)
to ensure they lead to complete implementation coverage including:
- File generation
- Architectural coverage
- CI/CD and test automation
- FILES_REQUIRED.md alignment
"""

import logging
from collections import deque
from pathlib import Path

from .coverage_analyzer import CoverageAnalyzer
from .document_parser import DocumentParser
from .instruction_node import InstructionNode
from .path_resolver import PathResolver
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class InstructionPathTracer:
    """Traces instruction paths through documentation.

    This class coordinates the tracing of instruction paths by delegating
    specific responsibilities to specialized components.
    """

    def __init__(self, root_dir: Path | None = None, max_depth: int = 5):
        """Initialize instruction path tracer.

        Args:
            root_dir: Root directory of the project. If None, uses current working directory.
            max_depth: Maximum depth to trace in the document tree
        """
        self.root_dir = root_dir or Path.cwd()
        self.max_depth = max_depth
        self.visited: set[str] = set()

        # Initialize components
        self.parser = DocumentParser()
        self.path_resolver = PathResolver(self.root_dir)
        self.coverage_analyzer = CoverageAnalyzer(self.root_dir)
        self.report_generator = ReportGenerator(self.root_dir)

    def trace_from_document(self, start_path: Path) -> InstructionNode | None:
        """Trace instruction paths starting from a document.

        Args:
            start_path: Path to start tracing from

        Returns:
            Root node of the instruction tree
        """
        queue: deque[tuple[Path, int, InstructionNode | None]] = deque([(start_path, 0, None)])
        root_node = None
        nodes_by_path: dict[str, InstructionNode] = {}

        while queue:
            current_path, depth, parent_node = queue.popleft()

            if depth > self.max_depth:
                continue

            if str(current_path) in self.visited:
                continue

            self.visited.add(str(current_path))

            # Extract information from current document
            node = self.parser.extract_document_info(current_path)
            if not node:
                continue

            node.depth = depth
            node.parent = parent_node

            if parent_node:
                parent_node.children.append(node)
            else:
                root_node = node

            nodes_by_path[str(current_path)] = node

            # Follow references
            for ref in node.references:
                ref_path = self.path_resolver.normalize_path(ref, current_path.parent)
                if ref_path and str(ref_path) not in self.visited:
                    queue.append((ref_path, depth + 1, node))

        return root_node

    def generate_trace_report(self) -> None:
        """Generate comprehensive instruction path trace report."""
        logger.info("=" * 80)
        logger.info("📊 INSTRUCTION PATH TRACE REPORT")
        logger.info("=" * 80)
        logger.info("")

        # Find entry points
        entry_points = self._find_entry_points()

        if not entry_points:
            logger.info("❌ No entry points found (README.md or PLANNING.md)")
            return

        # Trace from each entry point
        for name, path in entry_points:
            self._trace_entry_point(name, path)

        # Check FILES_REQUIRED.md alignment
        self._check_files_required_alignment()

        # Print summary
        self.report_generator.print_summary(total_docs=len(self.visited), entry_points=len(entry_points))

    def _find_entry_points(self) -> list[tuple[str, Path]]:
        """Find documentation entry points.

        Returns:
            List of (name, path) tuples for entry points
        """
        entry_points = []

        readme_path = self.root_dir / "README.md"
        if readme_path.exists():
            entry_points.append(("README.md", readme_path))

        planning_path = self.root_dir / "planning" / "PLANNING.md"
        if planning_path.exists():
            entry_points.append(("PLANNING.md", planning_path))

        return entry_points

    def _trace_entry_point(self, name: str, path: Path) -> None:
        """Trace from a single entry point.

        Args:
            name: Name of the entry point
            path: Path to the entry point document
        """
        logger.info(f"\n{'=' * 40}")
        logger.info(f"🚀 TRACING FROM: {name}")
        logger.info(f"{'=' * 40}")

        self.visited.clear()
        root_node = self.trace_from_document(path)

        if root_node:
            logger.info("\n📊 INSTRUCTION TREE:")
            logger.info("-" * 40)
            self.report_generator.print_instruction_tree(root_node)

            # Check coverage
            coverage = self.coverage_analyzer.check_coverage(root_node)
            self.report_generator.print_coverage_report(coverage)

    def _check_files_required_alignment(self) -> None:
        """Check and report FILES_REQUIRED.md alignment."""
        logger.info("\n" + "=" * 80)
        logger.info("📁 FILES_REQUIRED.md ALIGNMENT CHECK")
        logger.info("=" * 80)

        alignment = self.coverage_analyzer.check_files_required_alignment()
        self.report_generator.print_alignment_report(alignment)


def main() -> None:
    """Run the instruction path tracer."""
    tracer = InstructionPathTracer()
    tracer.generate_trace_report()


if __name__ == "__main__":
    main()
