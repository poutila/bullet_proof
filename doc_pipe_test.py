from pathlib import Path

from docpipe import analyze_project

docs_path = Path('collected_docs')
results = analyze_project(docs_path)
print(f"Documents analyzed: {results.total_documents}")
print(f"Compliance score: {results.compliance_score}%")
print(f"Issues found: {len(results.all_issues)}")