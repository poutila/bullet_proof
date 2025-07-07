#!/usr/bin/env python3
"""
Reference Map Validator

Validates document references in DOCUMENT_REFERENCE_MAP.md to ensure:
1. All referenced documents exist (Present ✅)
2. All links are valid (Correctly linked ✅)
3. Documents are internally coherent (Internally coherent 🔍)
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from document_analyzer.analyzers import find_active_documents


class ReferenceValidator:
    """Validates document references and links."""
    
    def __init__(self, root_dir: Path = None):
        self.root_dir = root_dir or Path.cwd()
        self.reference_map_path = self.root_dir / "DOCUMENT_REFERENCE_MAP.md"
        
    def extract_references_from_map(self) -> Dict[str, List[str]]:
        """Extract all document references from DOCUMENT_REFERENCE_MAP.md."""
        references = defaultdict(list)
        
        if not self.reference_map_path.exists():
            print(f"❌ DOCUMENT_REFERENCE_MAP.md not found at {self.reference_map_path}")
            return references
            
        content = self.reference_map_path.read_text()
        
        # Pattern to match document references in the map
        # Matches lines like: │   ├── 🔗 → PLANNING.md ✅
        ref_pattern = r'🔗 → ([^\s]+\.md)\s*([✅❌])?'
        
        current_doc = None
        for line in content.split('\n'):
            # Detect document being analyzed
            if '📄' in line and '.md' in line:
                # Extract document name
                doc_match = re.search(r'📄\s+(\S+\.md)', line)
                if doc_match:
                    current_doc = doc_match.group(1)
            
            # Find references from current document
            if current_doc and '🔗' in line:
                ref_match = re.search(ref_pattern, line)
                if ref_match:
                    referenced_doc = ref_match.group(1)
                    references[current_doc].append(referenced_doc)
                    
        return dict(references)
    
    def extract_references_from_document(self, doc_path: Path) -> Set[str]:
        """Extract markdown links from a document."""
        if not doc_path.exists():
            return set()
            
        content = doc_path.read_text()
        
        # Pattern to match markdown links: [text](path)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        references = set()
        for match in re.finditer(link_pattern, content):
            link_path = match.group(2)
            # Only consider .md files
            if link_path.endswith('.md'):
                # Normalize path
                if link_path.startswith('./'):
                    link_path = link_path[2:]
                references.add(link_path)
                
        return references
    
    def validate_document_presence(self, references: Dict[str, List[str]]) -> Dict[str, bool]:
        """Check if all referenced documents exist."""
        all_docs = find_active_documents()
        doc_paths = {str(doc.relative_to(self.root_dir)): doc for doc in all_docs}
        
        presence_status = {}
        
        for doc, refs in references.items():
            for ref in refs:
                # Handle different path formats
                normalized_ref = ref
                if ref.startswith('./'):
                    normalized_ref = ref[2:]
                    
                # Check if file exists
                full_path = self.root_dir / normalized_ref
                exists = full_path.exists() and full_path.is_file()
                
                presence_status[ref] = exists
                
        return presence_status
    
    def validate_link_correctness(self) -> Dict[str, Dict[str, str]]:
        """Validate that links in documents match the reference map."""
        all_docs = find_active_documents()
        link_status = {}
        
        for doc_path in all_docs:
            doc_name = doc_path.name
            
            # Skip non-markdown files
            if not doc_name.endswith('.md'):
                continue
                
            # Extract actual links from document
            actual_refs = self.extract_references_from_document(doc_path)
            
            link_status[doc_name] = {
                'path': str(doc_path.relative_to(self.root_dir)),
                'references': list(actual_refs),
                'reference_count': len(actual_refs)
            }
            
        return link_status
    
    def check_internal_coherence(self) -> Dict[str, List[str]]:
        """Check for internal coherence issues in documents."""
        issues = defaultdict(list)
        all_docs = find_active_documents()
        
        for doc_path in all_docs:
            doc_name = doc_path.name
            
            if not doc_name.endswith('.md'):
                continue
                
            content = doc_path.read_text()
            
            # Check for broken section references
            section_refs = re.findall(r'\[([^\]]+)\]\(#([^)]+)\)', content)
            headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            
            # Normalize headings to anchor format
            heading_anchors = set()
            for heading in headings:
                # Convert to lowercase and replace spaces with hyphens
                anchor = heading.lower().replace(' ', '-')
                # Remove special characters
                anchor = re.sub(r'[^\w\-]', '', anchor)
                heading_anchors.add(anchor)
            
            # Check section references
            for ref_text, anchor in section_refs:
                if anchor not in heading_anchors:
                    issues[doc_name].append(f"Broken section reference: #{anchor}")
            
            # Check for TODO/FIXME items
            todos = re.findall(r'(TODO|FIXME|XXX):\s*(.+)', content)
            for marker, desc in todos:
                issues[doc_name].append(f"{marker}: {desc.strip()}")
                
            # Check for placeholder content
            placeholders = re.findall(r'\[([^\]]*(?:PLACEHOLDER|TBD|WIP)[^\]]*)\]', content, re.IGNORECASE)
            for placeholder in placeholders:
                issues[doc_name].append(f"Placeholder content: [{placeholder}]")
                
        return dict(issues)
    
    def generate_validation_report(self):
        """Generate a comprehensive validation report."""
        print("=" * 80)
        print("📊 DOCUMENT REFERENCE VALIDATION REPORT")
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
        
        # 3. Validate link correctness
        print("3️⃣ VALIDATING LINK CORRECTNESS")
        print("-" * 50)
        link_status = self.validate_link_correctness()
        
        docs_with_refs = sum(1 for info in link_status.values() if info['reference_count'] > 0)
        total_links = sum(info['reference_count'] for info in link_status.values())
        
        print(f"📄 Analyzed {len(link_status)} documents")
        print(f"🔗 Found {total_links} total links in {docs_with_refs} documents")
        
        # Compare with reference map
        print("\nCross-validation with reference map:")
        for doc, refs in references.items():
            if doc in link_status:
                actual_refs = set(link_status[doc]['references'])
                expected_refs = set(refs)
                
                missing_in_doc = expected_refs - actual_refs
                extra_in_doc = actual_refs - expected_refs
                
                if missing_in_doc or extra_in_doc:
                    print(f"\n📄 {doc}:")
                    if missing_in_doc:
                        print(f"  ⚠️  Missing links: {', '.join(missing_in_doc)}")
                    if extra_in_doc:
                        print(f"  ➕ Extra links: {', '.join(extra_in_doc)}")
        print()
        
        # 4. Check internal coherence
        print("4️⃣ CHECKING INTERNAL COHERENCE")
        print("-" * 50)
        coherence_issues = self.check_internal_coherence()
        
        if not coherence_issues:
            print("✅ No internal coherence issues found!")
        else:
            print(f"⚠️  Found issues in {len(coherence_issues)} documents:")
            for doc, issues in sorted(coherence_issues.items()):
                print(f"\n📄 {doc}:")
                for issue in issues[:5]:  # Limit to first 5 issues
                    print(f"  - {issue}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more issues")
        print()
        
        # 5. Summary
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        
        # Calculate scores
        presence_score = (present_count / len(presence_status) * 100) if presence_status else 0
        
        print(f"✅ Document Presence: {presence_score:.1f}% ({present_count}/{len(presence_status)})")
        print(f"🔗 Total Document Links: {total_links}")
        print(f"⚠️  Documents with Issues: {len(coherence_issues)}")
        
        # Overall health
        if presence_score >= 90 and len(coherence_issues) <= 2:
            print("\n✅ Overall: EXCELLENT - Documentation is well-maintained")
        elif presence_score >= 70 and len(coherence_issues) <= 5:
            print("\n⚠️  Overall: GOOD - Minor improvements needed")
        else:
            print("\n❌ Overall: NEEDS ATTENTION - Significant issues found")


def main():
    """Run the reference validation."""
    validator = ReferenceValidator()
    validator.generate_validation_report()


if __name__ == "__main__":
    main()