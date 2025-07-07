#!/usr/bin/env python3
"""Structural Soundness Checker.

Verifies the structural integrity of the documentation system by checking:
1. Are docs/adr/ and docs/architecture/ entries properly cited in DOCUMENTS.md?
2. Do .md templates actually generate their target outputs?
3. Are template-to-output mappings complete and functional?
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .analyzers import find_active_documents

logger = logging.getLogger(__name__)


@dataclass
class TemplateMapping:
    """Represents a template and its expected outputs."""

    template_path: Path
    template_name: str
    expected_outputs: list[str]
    actual_outputs: list[str]
    instructions: list[str]
    generation_commands: list[str]


@dataclass
class CitationCheck:
    """Represents citation verification results."""

    document_path: Path
    cited_in_documents: list[str]
    expected_citations: list[str]
    missing_citations: list[str]


class StructuralSoundnessChecker:
    """Checks structural soundness of documentation system."""

    def __init__(self, root_dir: Path | None = None) -> None:
        """Initialize structural soundness checker.

        Args:
            root_dir: Root directory of the project. If None, uses current working directory.
        """
        self.root_dir = root_dir or Path.cwd()
        self.documents_md_path = self.root_dir / "planning" / "DOCUMENTS.md"

        # Template patterns that indicate file generation
        self.template_patterns = [
            r"(?:generates?|creates?|outputs?)\s*:?\s*`([^`]+)`",
            r"(?:creates?|generates?)\s+([^\s]+\.(yml|yaml|py|json|md|sh|txt))",
            r"(?:output|result|target).*?([^\s]+\.(yml|yaml|py|json|md|sh|txt))",
            r"→\s*([^\s]+\.(yml|yaml|py|json|md|sh|txt))",
            r"produces?\s+([^\s]+\.(yml|yaml|py|json|md|sh|txt))",
        ]

        # Command patterns that show generation instructions
        self.command_patterns = [
            r"```(?:bash|shell|sh)\n([^`]+)\n```",
            r"`([^`]*(?:generate|create|build|make)[^`]*)`",
            r"run\s+`([^`]+)`",
            r"execute\s+`([^`]+)`",
        ]

    def find_adr_and_architecture_files(self) -> tuple[list[Path], list[Path]]:
        """Find all ADR and architecture files."""
        adr_files: list[Path] = []
        arch_files: list[Path] = []

        # Find ADR files
        adr_dir = self.root_dir / "docs" / "adr"
        if adr_dir.exists():
            # Exclude template
            adr_files.extend(file for file in adr_dir.rglob("*.md") if file.name != "template.md")

        # Find architecture files
        arch_dir = self.root_dir / "docs" / "architecture"
        if arch_dir.exists():
            arch_files.extend(arch_dir.rglob("*.md"))

        return adr_files, arch_files

    def check_citations_in_documents_md(self, files_to_check: list[Path]) -> list[CitationCheck]:
        """Check if files are properly cited in DOCUMENTS.md."""
        if not self.documents_md_path.exists():
            return []

        documents_content = self.documents_md_path.read_text()
        citation_results = []

        for file_path in files_to_check:
            rel_path = file_path.relative_to(self.root_dir)
            file_name = file_path.name

            # Check various citation patterns
            citations_found = []

            # Direct file name mention
            if file_name in documents_content:
                citations_found.append(f"Direct mention: {file_name}")

            # Relative path mention
            if str(rel_path) in documents_content:
                citations_found.append(f"Path mention: {rel_path}")

            # Link pattern [text](path)
            link_pattern = rf"\[[^\]]*\]\([^)]*{re.escape(str(rel_path))}[^)]*\)"
            if re.search(link_pattern, documents_content):
                citations_found.append(f"Markdown link to {rel_path}")

            # Directory mention (for architecture/adr directories)
            dir_name = file_path.parent.name
            if dir_name in ["adr", "architecture"] and dir_name in documents_content:
                citations_found.append(f"Directory mention: {dir_name}")

            citation_check = CitationCheck(
                document_path=file_path,
                cited_in_documents=citations_found,
                expected_citations=[str(rel_path), file_name],
                missing_citations=[],
            )

            # Determine missing citations
            if not citations_found:
                citation_check.missing_citations = [str(rel_path)]

            citation_results.append(citation_check)

        return citation_results

    def extract_template_mappings(self, template_files: list[Path]) -> list[TemplateMapping]:
        """Extract expected outputs from template files."""
        mappings = []

        for template_path in template_files:
            if not template_path.exists():
                continue

            content = template_path.read_text()
            template_name = template_path.name

            # Extract expected outputs
            expected_outputs = []
            for pattern in self.template_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    output_file = match.group(1)
                    if output_file and not output_file.startswith("$"):
                        expected_outputs.append(output_file)

            # Extract generation commands
            generation_commands = []
            for pattern in self.command_patterns:
                for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                    command = match.group(1).strip()
                    if any(keyword in command.lower() for keyword in ["generate", "create", "build", "make"]):
                        generation_commands.append(command)

            # Extract general instructions
            instructions = []
            instruction_patterns = [
                r"(?:must|should|need to)\s+([^.]+)",
                r"(?:create|implement|build|generate)\s+([^.]+)",
                r"(?:step \d+|Step \d+):\s*([^.]+)",
            ]

            for pattern in instruction_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    instruction = match.group(1).strip()
                    if len(instruction) > 10:  # Filter out very short matches
                        instructions.append(instruction)

            # Check which outputs actually exist
            actual_outputs = []
            for expected in expected_outputs:
                # Try various paths where the output might exist
                search_paths = [
                    self.root_dir / expected,
                    self.root_dir / ".github" / expected,
                    self.root_dir / ".github" / "workflows" / expected,
                    self.root_dir / "scripts" / expected,
                    self.root_dir / "src" / expected,
                    self.root_dir / "docs" / expected,
                    self.root_dir / "planning" / expected,
                ]

                for search_path in search_paths:
                    if search_path.exists():
                        actual_outputs.append(str(search_path.relative_to(self.root_dir)))
                        break

            mapping = TemplateMapping(
                template_path=template_path,
                template_name=template_name,
                expected_outputs=list(set(expected_outputs)),  # Remove duplicates
                actual_outputs=actual_outputs,
                instructions=instructions[:10],  # Limit to first 10
                generation_commands=generation_commands,
            )

            mappings.append(mapping)

        return mappings

    def find_template_files(self) -> list[Path]:
        """Find all template files in the project."""
        all_docs = find_active_documents()
        template_files = []

        for doc in all_docs:
            if not doc.name.endswith(".md"):
                continue

            # Check if file is a template based on name or content
            is_template = False

            # Name-based detection
            if any(keyword in doc.name.lower() for keyword in ["template", "automation", "plan"]):
                is_template = True

            # Content-based detection
            if not is_template:
                try:
                    content = doc.read_text()
                    # Look for template indicators
                    template_indicators = [
                        "generates?.*:",
                        "creates?.*:",
                        "outputs?.*:",
                        "template",
                        "automation.*plan",
                        "generates?.*file",
                        r"\.github/workflows",
                        "creates?.*script",
                    ]

                    for indicator in template_indicators:
                        if re.search(indicator, content, re.IGNORECASE):
                            is_template = True
                            break
                except OSError as e:
                    logger.warning(f"Failed to check if {doc} is a template: {e}")
                    continue

            if is_template:
                template_files.append(doc)

        return template_files

    def generate_soundness_report(self) -> None:
        """Generate comprehensive structural soundness report."""
        logger.info("=" * 80)
        logger.info("🏗️  STRUCTURAL SOUNDNESS ANALYSIS")
        logger.info("=" * 80)
        logger.info("")

        # 1. Check ADR and Architecture citations
        logger.info("1️⃣ CHECKING ADR & ARCHITECTURE CITATIONS")
        logger.info("-" * 50)

        adr_files, arch_files = self.find_adr_and_architecture_files()
        all_structural_files = adr_files + arch_files

        if not all_structural_files:
            logger.info("❌ No ADR or architecture files found")
        else:
            logger.info(f"📁 Found {len(adr_files)} ADR files and {len(arch_files)} architecture files")

            # Check citations in DOCUMENTS.md
            if not self.documents_md_path.exists():
                logger.info("❌ DOCUMENTS.md not found - cannot verify citations")
            else:
                citation_results = self.check_citations_in_documents_md(all_structural_files)

                cited_count = sum(1 for result in citation_results if result.cited_in_documents)
                missing_count = len(citation_results) - cited_count

                logger.info(f"✅ Properly cited: {cited_count}/{len(citation_results)} files")
                logger.info(f"❌ Missing citations: {missing_count} files")

                if missing_count > 0:
                    logger.info("\nFiles missing citations in DOCUMENTS.md:")
                    for result in citation_results:
                        if not result.cited_in_documents:
                            rel_path = result.document_path.relative_to(self.root_dir)
                            logger.info(f"  📄 {rel_path}")

                if cited_count > 0:
                    logger.info("\nProperly cited files:")
                    for result in citation_results:
                        if result.cited_in_documents:
                            rel_path = result.document_path.relative_to(self.root_dir)
                            logger.info(f"  ✅ {rel_path}")
                            for citation in result.cited_in_documents[:2]:
                                logger.info(f"     - {citation}")
        logger.info("")

        # 2. Check template-to-output mappings
        logger.info("2️⃣ CHECKING TEMPLATE-TO-OUTPUT MAPPINGS")
        logger.info("-" * 50)

        template_files = self.find_template_files()
        logger.info(f"🔍 Found {len(template_files)} template files")

        if not template_files:
            logger.info("❌ No template files found")
        else:
            template_mappings = self.extract_template_mappings(template_files)

            total_expected = sum(len(mapping.expected_outputs) for mapping in template_mappings)
            total_actual = sum(len(mapping.actual_outputs) for mapping in template_mappings)

            if total_expected > 0:
                generation_rate = (total_actual / total_expected) * 100
                logger.info(f"📊 Generation rate: {total_actual}/{total_expected} ({generation_rate:.1f}%)")
            else:
                logger.info("⚠️  No expected outputs found in templates")

            logger.info(
                f"📝 Total generation instructions: {sum(len(mapping.instructions) for mapping in template_mappings)}"
            )
            logger.info(
                f"⚙️  Total generation commands: {sum(len(mapping.generation_commands) for mapping in template_mappings)}"
            )

            # Detail each template
            logger.info("\nTemplate Analysis:")
            for mapping in template_mappings:
                rel_path = mapping.template_path.relative_to(self.root_dir)
                logger.info(f"\n📄 {rel_path}")

                if mapping.expected_outputs:
                    logger.info(f"   Expected outputs: {len(mapping.expected_outputs)}")
                    logger.info(f"   Actual outputs: {len(mapping.actual_outputs)}")

                    if mapping.actual_outputs:
                        logger.info("   ✅ Generated files:")
                        for output in mapping.actual_outputs[:3]:
                            logger.info(f"      - {output}")
                        if len(mapping.actual_outputs) > 3:
                            logger.info(f"      ... and {len(mapping.actual_outputs) - 3} more")

                    missing_outputs = set(mapping.expected_outputs) - set(mapping.actual_outputs)
                    if missing_outputs:
                        logger.info("   ❌ Missing outputs:")
                        for missing in list(missing_outputs)[:3]:
                            logger.info(f"      - {missing}")
                        if len(missing_outputs) > 3:
                            logger.info(f"      ... and {len(missing_outputs) - 3} more")

                    if mapping.generation_commands:
                        logger.info("   🔧 Generation commands found:")
                        for cmd in mapping.generation_commands[:2]:
                            logger.info(f"      - {cmd[:60]}...")
                else:
                    logger.info("   ⚠️  No expected outputs identified")
        logger.info("")

        # 3. Summary and recommendations
        logger.info("=" * 80)
        logger.info("📊 STRUCTURAL SOUNDNESS SUMMARY")
        logger.info("=" * 80)

        # Calculate overall scores
        citation_score = 0
        if all_structural_files:
            citation_results = (
                self.check_citations_in_documents_md(all_structural_files) if self.documents_md_path.exists() else []
            )
            if citation_results:
                cited_count = sum(1 for result in citation_results if result.cited_in_documents)
                citation_score = int((cited_count / len(citation_results)) * 100)

        generation_score = 0
        if template_files:
            template_mappings = self.extract_template_mappings(template_files)
            total_expected = sum(len(mapping.expected_outputs) for mapping in template_mappings)
            total_actual = sum(len(mapping.actual_outputs) for mapping in template_mappings)
            if total_expected > 0:
                generation_score = int((total_actual / total_expected) * 100)

        logger.info(f"🏗️  Citation Coverage: {citation_score:.1f}%")
        logger.info(f"⚙️  Template Generation: {generation_score:.1f}%")
        logger.info(f"📁 ADR Files: {len(adr_files)}")
        logger.info(f"🏛️  Architecture Files: {len(arch_files)}")
        logger.info(f"📝 Template Files: {len(template_files)}")

        # Overall assessment
        overall_score = (citation_score + generation_score) / 2
        if overall_score >= 80:
            logger.info(f"\n✅ Overall Assessment: EXCELLENT ({overall_score:.1f}%)")
            logger.info("   Strong structural soundness with good documentation coverage")
        elif overall_score >= 60:
            logger.info(f"\n⚠️  Overall Assessment: GOOD ({overall_score:.1f}%)")
            logger.info("   Solid foundation with some areas for improvement")
        else:
            logger.info(f"\n❌ Overall Assessment: NEEDS ATTENTION ({overall_score:.1f}%)")
            logger.info("   Structural gaps need addressing")

        # Recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        if citation_score < 80:
            logger.info("   - Add missing ADR/architecture references to DOCUMENTS.md")
        if generation_score < 80:
            logger.info("   - Implement missing template outputs or update template specifications")
        if len(adr_files) == 0:
            logger.info("   - Create ADR files for major architectural decisions")
        if len(template_files) > 0 and generation_score > 0:
            logger.info("   - Consider automating template-to-output generation")


def main() -> None:
    """Run the structural soundness checker."""
    # Configure logging for CLI usage
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])

    checker = StructuralSoundnessChecker()
    checker.generate_soundness_report()


if __name__ == "__main__":
    main()
