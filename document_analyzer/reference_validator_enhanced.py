#!/usr/bin/env python3
"""
Enhanced Reference Map Validator

Improved version that properly resolves relative paths and provides
more accurate validation results.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from document_analyzer.analyzers import find_active_documents


class EnhancedReferenceValidator:
    """Enhanced validator with better path resolution."""
    
    def __init__(self, root_dir: Path = None):
        self.root_dir = root_dir or Path.cwd()
        self.reference_map_path = self.root_dir / "DOCUMENT_REFERENCE_MAP.md"
        
    def normalize_path(self, path: str, from_dir: Path = None) -> str:
        """Normalize a path to be relative to root directory."""
        if from_dir is None:
            from_dir = self.root_dir
            
        # Handle relative paths
        if path.startswith('../'):
            # Resolve relative to the from_dir
            resolved = (from_dir / path).resolve()
            try:
                return str(resolved.relative_to(self.root_dir))
            except ValueError:
                return path
        elif path.startswith('./'):
            path = path[2:]
            
        # If path doesn't start with planning/ or docs/, check if it should
        if not path.startswith(('planning/', 'docs/', '../')):
            # Check if file exists in planning directory
            if (self.root_dir / 'planning' / path).exists():
                return f'planning/{path}'
                
        return path
    
    def extract_references_from_map(self) -> Dict[str, List[str]]:
        """Extract all document references from DOCUMENT_REFERENCE_MAP.md."""
        references = defaultdict(list)
        
        if not self.reference_map_path.exists():
            print(f"❌ DOCUMENT_REFERENCE_MAP.md not found at {self.reference_map_path}")
            return references
            
        content = self.reference_map_path.read_text()
        
        # Pattern to match document references in the map
        ref_pattern = r'🔗 → ([^\s]+\.md)\s*([✅❌])?'
        
        current_doc = None
        current_dir = self.root_dir
        
        for line in content.split('\n'):
            # Detect directory context
            if '📁' in line and '/' in line:
                dir_match = re.search(r'📁\s+(\S+/)', line)
                if dir_match:
                    current_dir = self.root_dir / dir_match.group(1).rstrip('/')
            
            # Detect document being analyzed
            if '📄' in line and '.md' in line:
                doc_match = re.search(r'📄\s+(\S+\.md)', line)
                if doc_match:
                    current_doc = doc_match.group(1)
                    # Normalize based on current directory context
                    if current_dir != self.root_dir:
                        rel_path = current_dir.relative_to(self.root_dir)
                        current_doc = str(rel_path / current_doc)
            
            # Find references from current document
            if current_doc and '🔗' in line:
                ref_match = re.search(ref_pattern, line)
                if ref_match:
                    referenced_doc = ref_match.group(1)
                    # Normalize the referenced document path
                    normalized_ref = self.normalize_path(referenced_doc, current_dir)
                    references[current_doc].append(normalized_ref)
                    
        return dict(references)
    
    def validate_document_presence(self, references: Dict[str, List[str]]) -> Dict[str, bool]:
        """Check if all referenced documents exist."""
        presence_status = {}
        
        for doc, refs in references.items():
            for ref in refs:
                # Normalize and check existence
                full_path = self.root_dir / ref
                exists = full_path.exists() and full_path.is_file()
                presence_status[ref] = exists
                
        return presence_status
    
    def extract_references_from_document(self, doc_path: Path) -> Set[str]:
        """Extract markdown links from a document with proper path resolution."""
        if not doc_path.exists():
            return set()
            
        content = doc_path.read_text()
        doc_dir = doc_path.parent
        
        # Pattern to match markdown links: [text](path)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        references = set()
        for match in re.finditer(link_pattern, content):
            link_path = match.group(2)
            
            # Only consider .md files
            if link_path.endswith('.md'):
                # Normalize path relative to document location
                normalized = self.normalize_path(link_path, doc_dir)
                references.add(normalized)
                
        return references
    
    def generate_validation_report(self):
        """Generate an enhanced validation report."""
        print("=" * 80)
        print("📊 ENHANCED DOCUMENT REFERENCE VALIDATION REPORT")
        print("=" * 80)
        print()
        
        # 1. Extract references from map
        print("1️⃣ EXTRACTING REFERENCES FROM DOCUMENT_REFERENCE_MAP.md")
        print("-" * 50)
        references = self.extract_references_from_map()
        
        if not references:
            print("❌ No references found or file missing")
            return
            
        total_refs = sum(len(refs) for refs in references.values())
        print(f"✅ Found {len(references)} documents with {total_refs} total references")
        print()
        
        # 2. Validate document presence
        print("2️⃣ VALIDATING DOCUMENT PRESENCE")
        print("-" * 50)
        presence_status = self.validate_document_presence(references)
        
        missing_count = sum(1 for exists in presence_status.values() if not exists)
        present_count = len(presence_status) - missing_count
        
        print(f"✅ Present: {present_count} documents")
        print(f"❌ Missing: {missing_count} documents")
        
        if missing_count > 0:
            print("\nMissing documents:")
            for doc, exists in sorted(presence_status.items()):
                if not exists:
                    print(f"  ❌ {doc}")
        print()
        
        # 3. Path resolution analysis
        print("3️⃣ PATH RESOLUTION ANALYSIS")
        print("-" * 50)
        
        # Show how paths are resolved
        print("Path mappings:")
        path_examples = [
            ("CLAUDE.md", "From root", "CLAUDE.md"),
            ("../CLAUDE.md", "From planning/", "CLAUDE.md"),
            ("PLANNING.md", "From root", "planning/PLANNING.md"),
            ("./TASK.md", "From planning/", "planning/TASK.md"),
        ]
        
        for original, context, resolved in path_examples:
            print(f"  {original:20} ({context:15}) → {resolved}")
        print()
        
        # 4. Cross-reference validation
        print("4️⃣ CROSS-REFERENCE VALIDATION")
        print("-" * 50)
        
        all_docs = find_active_documents()
        issues_found = False
        
        for doc_path in all_docs:
            if not doc_path.name.endswith('.md'):
                continue
                
            doc_refs = self.extract_references_from_document(doc_path)
            doc_name = str(doc_path.relative_to(self.root_dir))
            
            # Check each reference
            invalid_refs = []
            for ref in doc_refs:
                ref_path = self.root_dir / ref
                if not ref_path.exists():
                    invalid_refs.append(ref)
                    
            if invalid_refs:
                if not issues_found:
                    print("Documents with invalid references:")
                    issues_found = True
                print(f"\n📄 {doc_name}:")
                for ref in invalid_refs:
                    print(f"  ❌ {ref}")
                    
        if not issues_found:
            print("✅ All document references are valid!")
        print()
        
        # 5. Summary
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        
        # Calculate scores
        presence_score = (present_count / len(presence_status) * 100) if presence_status else 0
        
        print(f"✅ Document Presence: {presence_score:.1f}% ({present_count}/{len(presence_status)})")
        print(f"📄 Total Documents Analyzed: {len(all_docs)}")
        print(f"🔗 Reference Map Entries: {len(references)}")
        
        # Overall health
        if presence_score >= 90 and not issues_found:
            print("\n✅ Overall: EXCELLENT - Documentation references are well-maintained")
        elif presence_score >= 70:
            print("\n⚠️  Overall: GOOD - Minor improvements needed")
        else:
            print("\n📍 Overall: ATTENTION - Some references need updating")
            
        print("\n💡 Note: This enhanced validator properly resolves relative paths")


def main():
    """Run the enhanced reference validation."""
    validator = EnhancedReferenceValidator()
    validator.generate_validation_report()


if __name__ == "__main__":
    main()