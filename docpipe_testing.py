from pathlib import Path
from docpipe import analyze_project

# Test all three directories with detailed output
for dir_name in ['collected_docs', 'collected_docs_broken', 'collected_docs_missing_docs']:
    print(f"\n{'='*60}")
    print(f"Testing: {dir_name}")
    print('='*60)
    
    docs_path = Path(dir_name)
    results = analyze_project(docs_path)
    
    print(f"Documents analyzed: {results.total_documents}")
    print(f"Compliance score: {results.compliance_score}%")
    print(f"Total issues found: {len(results.all_issues)}")
    
    # Show compliance details if available
    if results.compliance:
        print(f"\nCompliance Details:")
        print(f"  - Issues: {len(results.compliance.issues)}")
        print(f"  - Critical issues: {results.compliance.has_critical_issues}")
        print(f"  - Score: {results.compliance.compliance_score}%")
        
        if results.compliance.issues:
            print("\n  Issues found:")
            for issue in results.compliance.issues[:5]:  # Show first 5 issues
                print(f"    - [{issue.severity}] {issue.type}: {issue.message}")
                print(f"      File: {issue.file_path}")
    
    # Show reference validation details
    if results.references:
        print(f"\nReference Validation:")
        print(f"  - Broken references: {len(results.references.broken_references)}")
        print(f"  - Orphaned documents: {len(results.references.orphaned_documents)}")
        print(f"  - Has broken refs: {results.references.has_broken_references}")
        
        if results.references.broken_references:
            print("\n  Broken references found:")
            for ref in list(results.references.broken_references)[:5]:
                print(f"    - {ref}")
    
    # Show similarity details
    if results.similarity:
        print(f"\nSimilarity Analysis:")
        print(f"  - Duplicate count: {results.similarity.duplicate_count}")
        print(f"  - Similar count: {results.similarity.similar_count}")
    
    # Show instruction tracing details
    if results.instructions:
        print(f"\nInstruction Tracing:")
        print(f"  - Coverage: {results.instructions.coverage_percentage:.1f}%")
        print(f"  - Missing files: {len(results.instructions.missing_files)}")
    
    # Show feedback
    if results.feedback:
        print(f"\nFeedback ({len(results.feedback)} items):")
        for fb in results.feedback:
            print(f"  - [{fb.severity}] {fb.message}")
            if fb.details:
                print(f"    Details: {fb.details}")