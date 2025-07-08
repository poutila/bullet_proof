"""Advanced usage example for docpipe."""

from pathlib import Path
from docpipe import DocPipe, AnalysisConfig, FEATURES
from docpipe.models import Severity


def main():
    """Demonstrate advanced docpipe usage."""
    
    # Check available features
    print("Available Features:")
    print("-" * 40)
    for feature, available in FEATURES.items():
        status = "✓" if available else "✗"
        print(f"{status} {feature}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 1: Using DocPipe class directly
    print("Example 1: Using DocPipe class")
    print("-" * 40)
    
    # Create custom configuration
    config = AnalysisConfig(
        # Only analyze specific types
        check_compliance=True,
        analyze_similarity=True,
        validate_references=False,
        trace_instructions=False,
        check_structure=False,
        
        # Similarity settings
        similarity_method="both" if FEATURES['semantic_similarity'] else "string",
        similarity_threshold=0.85,
        enable_clustering=True,
        
        # Compliance settings
        max_file_lines=500,
        min_test_coverage=90.0,
        max_complexity=10,
        
        # Performance settings
        parallel_processing=True,
        batch_size=100,
    )
    
    # Create pipeline
    pipeline = DocPipe(config)
    
    # Validate configuration
    warnings = pipeline.validate_config()
    if warnings:
        print("Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Run specific analyses
    project_path = Path(".")
    
    print("\nRunning compliance analysis...")
    compliance_results = pipeline.analyze_compliance(project_path)
    print(f"  Files checked: {compliance_results.files_checked}")
    print(f"  Compliance score: {compliance_results.compliance_score:.1f}%")
    
    print("\nRunning similarity analysis...")
    similarity_results = pipeline.analyze_similarity(project_path)
    print(f"  Documents analyzed: {similarity_results.documents_analyzed}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Custom analysis workflow
    print("Example 2: Custom analysis workflow")
    print("-" * 40)
    
    # Run full analysis with custom handling
    def custom_progress(percentage: float, message: str):
        # Custom progress handling (e.g., update UI, send to logging system)
        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r[{bar}] {percentage:3.0f}% - {message}", end="", flush=True)
    
    results = pipeline.analyze(project_path, progress_callback=custom_progress)
    print()  # New line after progress
    
    # Process results programmatically
    critical_issues = [i for i in results.all_issues if i.severity == Severity.CRITICAL]
    if critical_issues:
        print(f"\n⚠️  Found {len(critical_issues)} CRITICAL issues:")
        for issue in critical_issues[:5]:  # Show first 5
            print(f"  - {issue.message}")
            if issue.file_path:
                print(f"    File: {issue.file_path}:{issue.line_number or ''}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Integration with CI/CD
    print("Example 3: CI/CD Integration")
    print("-" * 40)
    
    # Create strict configuration for CI
    ci_config = AnalysisConfig(
        # Strict thresholds
        similarity_threshold=0.95,  # Flag near-duplicates
        min_test_coverage=95.0,     # Higher coverage requirement
        max_file_lines=300,         # Stricter file size limit
        
        # Output settings for CI
        output_format="json",
        verbose=False,
        include_file_contents=False,  # Keep output small
    )
    
    ci_pipeline = DocPipe(ci_config)
    ci_results = ci_pipeline.analyze(project_path)
    
    # Determine exit code for CI
    if ci_results.has_critical_issues:
        print("❌ Build FAILED - Critical issues found")
        exit_code = 2
    elif ci_results.compliance_score < 90:
        print("❌ Build FAILED - Compliance score too low")
        exit_code = 1
    elif len(ci_results.missing_references) > 0:
        print("⚠️  Build WARNING - Missing references found")
        exit_code = 0
    else:
        print("✅ Build PASSED - All checks passed")
        exit_code = 0
    
    # Export results for CI artifacts
    ci_results.export("ci_results.json")
    print(f"CI results exported to: ci_results.json")
    print(f"Exit code: {exit_code}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 4: Custom analyzer (plugin system preview)
    print("Example 4: Plugin System (Future Feature)")
    print("-" * 40)
    print("In future versions, you'll be able to add custom analyzers:")
    print("""
    from docpipe.analyzers import BaseAnalyzer
    
    class CustomAnalyzer(BaseAnalyzer):
        def analyze(self, path: Path) -> AnalyzerResult:
            # Your custom analysis logic here
            pass
    
    pipeline.register_analyzer('custom', CustomAnalyzer())
    """)


if __name__ == "__main__":
    main()