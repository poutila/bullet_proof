#!/usr/bin/env python3
"""Instruction Path Tracer.

Traces instruction paths from entry point documents (README.md, PLANNING.md)
to ensure they lead to complete implementation coverage including:
- File generation
- Architectural coverage
- CI/CD and test automation
- FILES_REQUIRED.md alignment
"""

import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class InstructionNode:
    """Represents a node in the instruction path."""

    path: Path
    title: str
    depth: int
    parent: Optional["InstructionNode"] = None
    children: list["InstructionNode"] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    generates: list[str] = field(default_factory=list)


class InstructionPathTracer:
    """Traces instruction paths through documentation."""

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = root_dir or Path.cwd()
        self.visited: set[str] = set()
        self.instruction_graph: dict[str, Any] = {}

        # Key patterns to identify instructions
        self.instruction_patterns = [
            r"(?:must|should|need to|required to)\s+(\w+)",
            r"(?:create|implement|build|generate|write)\s+([^.]+)",
            r"(?:follow|use|see)\s+\[([^\]]+)\]\(([^)]+)\)",
            r"(?:run|execute)\s+`([^`]+)`",
            r"CI/CD.*(?:pipeline|workflow|action)",
            r"test.*(?:coverage|automation|framework)",
            r"(?:generates?|creates?|outputs?)\s*:?\s*([^.]+)",
        ]

        # File generation patterns
        self.file_gen_patterns = [
            r"(?:create|generate|write)\s+(?:file|script)?\s*`([^`]+)`",
            r"(?:creates?|generates?)\s+([^\s]+\.(py|yml|yaml|md|json|toml|txt))",
            r"(?:output|result).*?([^\s]+\.(py|yml|yaml|md|json|toml|txt))",
            r"`([^`]+\.(py|yml|yaml|md|json|toml|txt))`",
        ]

    def extract_document_info(self, doc_path: Path) -> InstructionNode | None:
        """Extract instructions and references from a document."""
        if not doc_path.exists():
            return None

        content = doc_path.read_text()
        lines = content.split("\n")

        # Extract title
        title = doc_path.name
        for line in lines[:10]:  # Check first 10 lines for title
            if line.startswith("# "):
                title = line[2:].strip()
                break

        node = InstructionNode(path=doc_path, title=title, depth=0)

        # Extract references (markdown links)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(link_pattern, content):
            match.group(1)
            link_path = match.group(2)
            if link_path.endswith(".md"):
                node.references.append(link_path)

        # Extract instructions
        for pattern in self.instruction_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                instruction = match.group(0)
                node.instructions.append(instruction)

        # Extract file generation mentions
        for pattern in self.file_gen_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                file_mention = match.group(1)
                if file_mention and not file_mention.startswith("$"):
                    node.generates.append(file_mention)

        return node

    def normalize_path(self, path: str, from_dir: Path) -> Path | None:
        """Normalize a relative path to absolute."""
        if path.startswith("http"):
            return None

        if path.startswith("./"):
            path = path[2:]

        resolved = (from_dir / path).resolve() if path.startswith("../") else from_dir / path

        # Check if file exists
        if resolved.exists():
            return resolved

        # Try from root
        root_resolved = self.root_dir / path
        if root_resolved.exists():
            return root_resolved

        # Try common directories
        for prefix in ["planning/", "docs/", ""]:
            test_path = self.root_dir / prefix / path
            if test_path.exists():
                return test_path

        return None

    def trace_from_document(self, start_path: Path, max_depth: int = 5) -> InstructionNode | None:
        """Trace instruction paths starting from a document."""
        queue: deque[tuple[Path, int, InstructionNode | None]] = deque([(start_path, 0, None)])
        root_node = None
        nodes_by_path = {}

        while queue:
            current_path, depth, parent_node = queue.popleft()

            if depth > max_depth:
                continue

            if str(current_path) in self.visited:
                continue

            self.visited.add(str(current_path))

            # Extract information from current document
            node = self.extract_document_info(current_path)
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
                ref_path = self.normalize_path(ref, current_path.parent)
                if ref_path and str(ref_path) not in self.visited:
                    queue.append((ref_path, depth + 1, node))

        return root_node

    def check_coverage(self, root_node: InstructionNode) -> dict[str, list[str]]:
        """Check coverage of various aspects."""
        coverage: dict[str, list[str]] = {
            "file_generation": [],
            "ci_cd": [],
            "test_automation": [],
            "architecture": [],
            "implementation": [],
        }

        def traverse(node: InstructionNode) -> None:
            # Check for file generation
            for gen_file in node.generates:
                coverage["file_generation"].append(f"{node.path.name}: {gen_file}")

            # Check for CI/CD mentions
            content = node.path.read_text().lower()
            if any(term in content for term in ["ci/cd", "github action", "workflow", "pipeline"]):
                coverage["ci_cd"].append(node.path.name)

            # Check for test automation
            if any(term in content for term in ["pytest", "test automation", "coverage", "mutation test"]):
                coverage["test_automation"].append(node.path.name)

            # Check for architecture
            if any(term in content for term in ["architecture", "design", "component", "module"]):
                coverage["architecture"].append(node.path.name)

            # Check for implementation instructions
            if node.instructions:
                coverage["implementation"].append(f"{node.path.name}: {len(node.instructions)} instructions")

            # Traverse children
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return coverage

    def check_files_required_alignment(self) -> dict[str, bool]:
        """Check alignment with FILES_REQUIRED.md."""
        files_required_path = self.root_dir / "FILES_REQUIRED.md"
        if not files_required_path.exists():
            return {}

        content = files_required_path.read_text()

        # Extract required files - improved pattern for FILES_REQUIRED.md format
        required_files = set()

        # Pattern for bullet point files: - `filename`
        bullet_pattern = r"-\s+`([^`]+\.(py|yml|yaml|md|json|toml|txt|sh|cfg|ini))`"
        for match in re.finditer(bullet_pattern, content):
            required_files.add(match.group(1))

        # Pattern for tree structure files: │├└ and filenames
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

        # Check which exist
        alignment = {}
        for req_file in required_files:
            # Clean up the filename
            clean_file = req_file.lstrip("./")

            # Try various paths
            exists = False
            search_paths = [
                clean_file,
                f"src/{clean_file}",
                f"docs/{clean_file}",
                f"planning/{clean_file}",
                f".github/{clean_file}",
                f".github/workflows/{clean_file}",
                f"scripts/{clean_file}",
                f"tests/{clean_file}",
            ]

            for search_path in search_paths:
                test_path = self.root_dir / search_path
                if test_path.exists():
                    exists = True
                    break

            alignment[req_file] = exists

        return alignment

    def print_instruction_tree(self, node: InstructionNode | None, prefix: str = "") -> None:
        """Print the instruction tree."""
        if not node:
            return

        # Print current node
        rel_path = node.path.relative_to(self.root_dir)
        print(f"{prefix}📄 {rel_path}")

        if node.instructions:
            print(f"{prefix}  📝 {len(node.instructions)} instructions found")

        if node.generates:
            print(f"{prefix}  🔧 Generates: {', '.join(node.generates[:3])}")
            if len(node.generates) > 3:
                print(f"{prefix}     ... and {len(node.generates) - 3} more")

        # Print children
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1
            child_prefix = prefix + ("  └─ " if is_last else "  ├─ ")
            prefix + ("     " if is_last else "  │  ")
            self.print_instruction_tree(child, child_prefix)

    def generate_trace_report(self) -> None:
        """Generate comprehensive instruction path trace report."""
        print("=" * 80)
        print("📊 INSTRUCTION PATH TRACE REPORT")
        print("=" * 80)
        print()

        # Check if entry points exist
        readme_path = self.root_dir / "README.md"
        planning_path = self.root_dir / "planning" / "PLANNING.md"

        entry_points = []
        if readme_path.exists():
            entry_points.append(("README.md", readme_path))
        if planning_path.exists():
            entry_points.append(("PLANNING.md", planning_path))

        if not entry_points:
            print("❌ No entry points found (README.md or PLANNING.md)")
            return

        # Trace from each entry point
        for name, path in entry_points:
            print(f"\n{'=' * 40}")
            print(f"🚀 TRACING FROM: {name}")
            print(f"{'=' * 40}")

            self.visited.clear()
            root_node = self.trace_from_document(path)

            if root_node:
                print("\n📊 INSTRUCTION TREE:")
                print("-" * 40)
                self.print_instruction_tree(root_node)

                # Check coverage
                print("\n📈 COVERAGE ANALYSIS:")
                print("-" * 40)
                coverage = self.check_coverage(root_node)

                for aspect, items in coverage.items():
                    print(f"\n{aspect.replace('_', ' ').title()}:")
                    if items:
                        for item in items[:5]:
                            print(f"  ✅ {item}")
                        if len(items) > 5:
                            print(f"  ... and {len(items) - 5} more")
                    else:
                        print("  ❌ No coverage found")

        # Check FILES_REQUIRED.md alignment
        print("\n" + "=" * 80)
        print("📁 FILES_REQUIRED.md ALIGNMENT CHECK")
        print("=" * 80)

        alignment = self.check_files_required_alignment()
        if not alignment:
            print("❌ FILES_REQUIRED.md not found or empty")
        else:
            exists_count = sum(1 for exists in alignment.values() if exists)
            total_count = len(alignment)

            print(f"\n✅ Exists: {exists_count}/{total_count} files ({exists_count / total_count * 100:.1f}%)")

            missing = [f for f, exists in alignment.items() if not exists]
            if missing:
                print(f"❌ Missing: {len(missing)} files")
                print("\nMissing files:")
                for f in missing[:10]:
                    print(f"  - {f}")
                if len(missing) > 10:
                    print(f"  ... and {len(missing) - 10} more")

        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)

        total_docs = len(self.visited)
        print(f"📄 Documents traced: {total_docs}")
        print(f"🔗 Entry points analyzed: {len(entry_points)}")

        # Overall assessment
        if total_docs > 10:
            print("\n✅ Overall: Good documentation connectivity")
        else:
            print("\n⚠️  Overall: Limited documentation reach - consider adding more cross-references")


def main() -> None:
    """Run the instruction path tracer."""
    tracer = InstructionPathTracer()
    tracer.generate_trace_report()


if __name__ == "__main__":
    main()
