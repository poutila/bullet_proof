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
        logger.info(f"{prefix}📄 {rel_path}")

        if node.instructions:
            logger.info(f"{prefix}  📝 {len(node.instructions)} instructions found")

        if node.generates:
            logger.info(f"{prefix}  🔧 Generates: {', '.join(node.generates[:3])}")
            if len(node.generates) > 3:
                logger.info(f"{prefix}     ... and {len(node.generates) - 3} more")

        # Print children with proper tree formatting
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("  └─ " if is_last else "  ├─ ")
            prefix + ("     " if is_last else "  │  ")
            self.print_instruction_tree(child, child_prefix)

    def print_coverage_report(self, coverage: dict[str, list[str]]) -> None:
        """Print coverage analysis report.

        Args:
            coverage: Coverage data to report
        """
        logger.info("\n📈 COVERAGE ANALYSIS:")
        logger.info("-" * 40)

        for aspect, items in coverage.items():
            logger.info(f"\n{aspect.replace('_', ' ').title()}:")
            if items:
                for item in items[:5]:
                    logger.info(f"  ✅ {item}")
                if len(items) > 5:
                    logger.info(f"  ... and {len(items) - 5} more")
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

        logger.info(f"\n✅ Exists: {exists_count}/{total_count} files ({exists_count / total_count * 100:.1f}%)")

        missing = [f for f, exists in alignment.items() if not exists]
        if missing:
            logger.info(f"❌ Missing: {len(missing)} files")
            logger.info("\nMissing files:")
            for f in missing[:10]:
                logger.info(f"  - {f}")
            if len(missing) > 10:
                logger.info(f"  ... and {len(missing) - 10} more")

    def print_summary(self, total_docs: int, entry_points: int) -> None:
        """Print analysis summary.

        Args:
            total_docs: Total documents traced
            entry_points: Number of entry points analyzed
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 SUMMARY")
        logger.info("=" * 80)

        logger.info(f"📄 Documents traced: {total_docs}")
        logger.info(f"🔗 Entry points analyzed: {entry_points}")

        # Overall assessment
        if total_docs > 10:
            logger.info("\n✅ Overall: Good documentation connectivity")
        else:
            logger.info("\n⚠️  Overall: Limited documentation reach - consider adding more cross-references")
