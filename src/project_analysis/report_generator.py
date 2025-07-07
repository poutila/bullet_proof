"""Report generation functionality for instruction path tracer."""

import logging
from pathlib import Path

from .instruction_node import InstructionNode

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports for instruction path tracing."""

    def __init__(self, root_dir: Path):
        """Initialize report generator.

        Args:
            root_dir: Root directory for relative path calculation
        """
        self.root_dir = root_dir

    def print_instruction_tree(self, node: InstructionNode | None, prefix: str = "") -> None:
        """Print the instruction tree.

        Args:
            node: Node to print from
            prefix: Prefix for tree formatting
        """
        if not node:
            return

        # Print current node
        rel_path = node.path.relative_to(self.root_dir)
        logger.info("%s📄 %s", prefix, rel_path)

        if node.instructions:
            logger.info("%s  📝 %d instructions found", prefix, len(node.instructions))

        if node.generates:
            logger.info("%s  🔧 Generates: %s", prefix, ", ".join(node.generates[:3]))
            if len(node.generates) > 3:
                logger.info("%s     ... and %d more", prefix, len(node.generates) - 3)

        # Print children with proper tree formatting
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("  └─ " if is_last else "  ├─ ")
            self.print_instruction_tree(child, child_prefix)

    def print_coverage_report(self, coverage: dict[str, list[str]]) -> None:
        """Print coverage analysis report.

        Args:
            coverage: Coverage data to report
        """
        logger.info("\n📈 COVERAGE ANALYSIS:")
        logger.info("-" * 40)

        for aspect, items in coverage.items():
            logger.info("\n%s:", aspect.replace("_", " ").title())
            if items:
                for item in items[:5]:
                    logger.info("  ✅ %s", item)
                if len(items) > 5:
                    logger.info("  ... and %d more", len(items) - 5)
            else:
                logger.info("  ❌ No coverage found")

    def print_alignment_report(self, alignment: dict[str, bool]) -> None:
        """Print FILES_REQUIRED.md alignment report.

        Args:
            alignment: Alignment data to report
        """
        if not alignment:
            logger.info("❌ FILES_REQUIRED.md not found or empty")
            return

        exists_count = sum(1 for exists in alignment.values() if exists)
        total_count = len(alignment)

        logger.info("\n✅ Exists: %d/%d files (%.1f%%)", exists_count, total_count, exists_count / total_count * 100)

        missing = [f for f, exists in alignment.items() if not exists]
        if missing:
            logger.info("❌ Missing: %d files", len(missing))
            logger.info("\nMissing files:")
            for f in missing[:10]:
                logger.info("  - %s", f)
            if len(missing) > 10:
                logger.info("  ... and %d more", len(missing) - 10)

    def print_summary(self, total_docs: int, entry_points: int) -> None:
        """Print analysis summary.

        Args:
            total_docs: Total documents traced
            entry_points: Number of entry points analyzed
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 SUMMARY")
        logger.info("%s", "=" * 80)

        logger.info("📄 Documents traced: %d", total_docs)
        logger.info("🔗 Entry points analyzed: %d", entry_points)

        # Overall assessment
        if total_docs > 10:
            logger.info("\n✅ Overall: Good documentation connectivity")
        else:
            logger.info("\n⚠️  Overall: Limited documentation reach - consider adding more cross-references")
