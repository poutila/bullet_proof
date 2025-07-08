"""Command-line interface for docpipe."""

import sys
from pathlib import Path
from typing import Optional
import click
import logging

from .. import __version__, analyze_project, DocPipe, AnalysisConfig, FEATURES
from ..models import Severity


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="docpipe")
def cli():
    """Docpipe - Analyze AI coding instructions in markdown documentation."""
    pass


@cli.command()
@click.argument('path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', '-f', 
              type=click.Choice(['json', 'csv', 'excel', 'markdown']), 
              default='json',
              help='Output format')
@click.option('--only', 
              type=click.Choice(['compliance', 'similarity', 'references', 'instructions', 'structure']),
              help='Run only specific analysis')
@click.option('--similarity-threshold', type=float, help='Similarity threshold (0-1)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
def analyze(
    path: str,
    config: Optional[str],
    output: Optional[str],
    format: str,
    only: Optional[str],
    similarity_threshold: Optional[float],
    verbose: bool,
    quiet: bool
):
    """Analyze a project for documentation quality."""
    
    # Set up logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Load configuration
        if config:
            analysis_config = AnalysisConfig.from_file(Path(config))
        else:
            analysis_config = AnalysisConfig()
        
        # Override config with command-line options
        if only:
            # Disable all analyses except the specified one
            analysis_config.check_compliance = (only == 'compliance')
            analysis_config.analyze_similarity = (only == 'similarity')
            analysis_config.validate_references = (only == 'references')
            analysis_config.trace_instructions = (only == 'instructions')
            analysis_config.check_structure = (only == 'structure')
        
        if similarity_threshold is not None:
            analysis_config.similarity_threshold = similarity_threshold
        
        analysis_config.output_format = format
        analysis_config.verbose = verbose
        
        # Progress callback
        def show_progress(percentage: float, message: str) -> None:
            if not quiet:
                click.echo(f"[{percentage:3.0f}%] {message}")
        
        # Run analysis
        click.echo(f"Analyzing project: {path}")
        results = analyze_project(path, analysis_config, show_progress)
        
        # Display summary
        if not quiet:
            click.echo("\n" + "="*60)
            click.echo("ANALYSIS SUMMARY")
            click.echo("="*60)
            
            summary = results.summary
            for key, value in summary.items():
                click.echo(f"{key.replace('_', ' ').title()}: {value}")
            
            # Show feedback
            if results.feedback:
                click.echo("\n" + "="*60)
                click.echo("FEEDBACK")
                click.echo("="*60)
                
                for fb in results.feedback:
                    severity_color = {
                        Severity.CRITICAL: 'red',
                        Severity.ERROR: 'red',
                        Severity.WARNING: 'yellow',
                        Severity.INFO: 'green',
                        Severity.HINT: 'blue',
                    }
                    
                    prefix = "⚠️ " if fb.action_required else ""
                    click.echo(
                        click.style(
                            f"{prefix}[{fb.severity.value.upper()}] {fb.message}",
                            fg=severity_color.get(fb.severity, 'white')
                        )
                    )
                    if fb.details:
                        click.echo(f"  → {fb.details}")
        
        # Export results if requested
        if output:
            output_path = Path(output)
            results.export(output_path, format)
            click.echo(f"\nResults exported to: {output_path}")
        
        # Exit with appropriate code
        if results.has_critical_issues:
            sys.exit(2)
        elif len(results.all_issues) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


@cli.command()
def features():
    """Show available features based on installed dependencies."""
    click.echo("Docpipe Features:")
    click.echo("="*40)
    
    for feature, available in FEATURES.items():
        status = "✓ Available" if available else "✗ Not available"
        color = 'green' if available else 'red'
        click.echo(
            f"{feature.replace('_', ' ').title():.<30} "
            f"{click.style(status, fg=color)}"
        )
    
    click.echo("\nTo enable missing features:")
    if not FEATURES.get('semantic_similarity'):
        click.echo("  - Semantic similarity: pip install docpipe[ml]")
    if not FEATURES.get('excel_export'):
        click.echo("  - Excel export: pip install docpipe[data]")


@cli.command()
@click.argument('config_path', type=click.Path())
@click.option('--similarity-threshold', type=float, default=0.75)
@click.option('--compliance-rules', default='CLAUDE.md')
@click.option('--max-file-lines', type=int, default=500)
@click.option('--min-test-coverage', type=float, default=90.0)
def init_config(
    config_path: str,
    similarity_threshold: float,
    compliance_rules: str,
    max_file_lines: int,
    min_test_coverage: float
):
    """Initialize a configuration file with defaults."""
    
    config = AnalysisConfig(
        similarity_threshold=similarity_threshold,
        compliance_rules=compliance_rules,
        max_file_lines=max_file_lines,
        min_test_coverage=min_test_coverage,
    )
    
    config_file = Path(config_path)
    config.save(config_file)
    
    click.echo(f"Configuration file created: {config_file}")
    click.echo("You can now edit this file to customize your analysis.")


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def validate_config(path: str):
    """Validate a configuration file."""
    
    try:
        config = AnalysisConfig.from_file(Path(path))
        pipeline = DocPipe(config)
        warnings = pipeline.validate_config()
        
        if warnings:
            click.echo("Configuration warnings:")
            for warning in warnings:
                click.echo(f"  - {warning}")
        else:
            click.echo("Configuration is valid!")
    
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()