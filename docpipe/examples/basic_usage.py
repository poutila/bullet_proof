"""Basic usage example for docpipe."""

from pathlib import Path
from docpipe import analyze_project, AnalysisConfig


def main():
    """Demonstrate basic docpipe usage."""
    
    # Example 1: Simple analysis with defaults
    print("Example 1: Basic analysis")
    print("-" * 40)
    
    results = analyze_project(".")
    print(f"Documents analyzed: {results.total_documents}")
    print(f"Compliance score: {results.compliance_score:.1f}%")
    print(f"Issues found: {len(results.all_issues)}")
    
    # Show feedback
    print("\nFeedback:")
    for feedback in results.feedback:
        print(f"  [{feedback.severity.value}] {feedback.message}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Custom configuration
    print("Example 2: Custom configuration")
    print("-" * 40)
    
    config = AnalysisConfig(
        similarity_threshold=0.8,
        check_compliance=True,
        analyze_similarity=True,
        validate_references=False,  # Skip reference validation
        trace_instructions=False,   # Skip instruction tracing
        verbose=True
    )
    
    # Progress callback
    def show_progress(percentage: float, message: str):
        print(f"  [{percentage:3.0f}%] {message}")
    
    results = analyze_project(".", config, progress_callback=show_progress)
    
    # Access specific results
    if results.similarity:
        print(f"\nSimilar documents found: {len(results.similar_documents)}")
        for pair in results.similar_documents[:3]:  # Show first 3
            print(f"  - {pair.source.name} <-> {pair.target.name} "
                  f"(similarity: {pair.similarity_score:.2f})")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Export results
    print("Example 3: Export results")
    print("-" * 40)
    
    # Export to different formats
    results.export("analysis_report.json", format="json")
    print("Exported to: analysis_report.json")
    
    results.export("analysis_report.md", format="markdown")
    print("Exported to: analysis_report.md")
    
    # Export to Excel if pandas is available
    try:
        results.export("analysis_report.xlsx", format="excel")
        print("Exported to: analysis_report.xlsx")
    except ImportError:
        print("Excel export not available (install with: pip install docpipe[data])")


if __name__ == "__main__":
    main()