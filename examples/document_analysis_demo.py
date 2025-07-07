#!/usr/bin/env python3
"""Example usage of the document matching analyzers module."""

from pathlib import Path

from src.document_analysis.analyzers import find_active_documents, find_not_in_use_documents
from src.document_analysis.config import DEFAULT_EXCLUDE_PATTERNS


def demo_document_finders() -> None:
    """Demonstrate the document finder functions."""
    print("=== TESTING DOCUMENT FINDER FUNCTIONS ===\n")

    # Test 1: Find all active markdown documents
    print("1. Finding all active markdown documents...")
    active_docs = find_active_documents()
    print(f"   Found {len(active_docs)} active documents")

    # Show first 5 as examples
    print("   Examples:")
    for doc in active_docs[:5]:
        print(f"     - {doc.relative_to(Path.cwd())}")

    # Test 2: Find with custom patterns
    print("\n2. Finding Python files (excluding tests)...")
    custom_exclude = [*DEFAULT_EXCLUDE_PATTERNS, "tests", "test_"]
    py_files = find_active_documents(file_pattern="*.py", exclude_patterns=custom_exclude, verbose=True)
    print(f"   Found {len(py_files)} Python files")

    # Test 3: Find not_in_use documents
    print("\n3. Finding not_in_use documents...")
    not_in_use_docs = find_not_in_use_documents()
    print(f"   Found {len(not_in_use_docs)} not_in_use documents")
    for doc in not_in_use_docs:
        print(f"     - {doc.relative_to(Path.cwd())}")

    # Test 4: Different file types
    print("\n4. Finding all YAML/TOML config files...")
    yaml_files = find_active_documents(file_pattern="*.yaml", verbose=False)
    yml_files = find_active_documents(file_pattern="*.yml", verbose=False)
    toml_files = find_active_documents(file_pattern="*.toml", verbose=False)

    print(f"   YAML files: {len(yaml_files + yml_files)}")
    print(f"   TOML files: {len(toml_files)}")

    # Test 5: Count by directory
    print("\n5. Document distribution by directory...")
    dir_counts: dict[str, int] = {}
    for doc in active_docs:
        parent = doc.parent.relative_to(Path.cwd())
        dir_counts[str(parent)] = dir_counts.get(str(parent), 0) + 1

    # Sort by count
    sorted_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)
    print("   Top directories with markdown files:")
    for dir_name, count in sorted_dirs[:5]:
        print(f"     {dir_name}: {count} files")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"📄 Total active documents: {len(active_docs)}")
    print(f"🗂️ Total not_in_use documents: {len(not_in_use_docs)}")
    print(f"📊 Directories scanned: {len(dir_counts)}")


if __name__ == "__main__":
    demo_document_finders()
