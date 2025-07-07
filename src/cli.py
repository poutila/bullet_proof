#!/usr/bin/env python3
"""Command Line Interface for Bullet Proof project.

This CLI provides a unified interface to run all functionality in the project:
- Compliance checking
- Document analysis
- Similarity analysis
- Project structure analysis
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.compliance.claude_compliance_checker_simple import ClaudeComplianceChecker
from src.document_analysis.reference_validator import ReferenceValidator
from src.document_analysis.structural_soundness_checker import StructuralSoundnessChecker
from src.project_analysis.instruction_path_tracer import InstructionPathTracer
from src.document_analysis.similarity import StringSimilarityCalculator, SemanticSimilarityCalculator
from src.document_analysis import find_active_documents, load_markdown_files, merge_similar_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def run_compliance_check(args: argparse.Namespace) -> None:
    """Run CLAUDE.md compliance checker."""
    logger.info("🔍 Running CLAUDE.md Compliance Check...")
    logger.info("=" * 80)
    
    checker = ClaudeComplianceChecker(args.path)
    
    if args.file:
        # Check specific file
        file_path = Path(args.file)
        if file_path.exists():
            compliance = checker.check_file_compliance(file_path)
            checker.print_file_compliance(compliance)
        else:
            logger.error(f"File not found: {args.file}")
    else:
        # Check entire project
        checker.check_project_compliance()


def run_reference_check(args: argparse.Namespace) -> None:
    """Run reference validator."""
    logger.info("🔗 Running Reference Validator...")
    logger.info("=" * 80)
    
    validator = ReferenceValidator(
        root_dir=args.path,
        enhanced_mode=not args.basic
    )
    validator.generate_validation_report()


def run_structural_check(args: argparse.Namespace) -> None:
    """Run structural soundness checker."""
    logger.info("🏗️  Running Structural Soundness Check...")
    logger.info("=" * 80)
    
    checker = StructuralSoundnessChecker(root_dir=args.path)
    checker.generate_soundness_report()


def run_instruction_trace(args: argparse.Namespace) -> None:
    """Run instruction path tracer."""
    logger.info("📍 Running Instruction Path Tracer...")
    logger.info("=" * 80)
    
    tracer = InstructionPathTracer(root_dir=args.path)
    tracer.trace_all_paths()


def run_similarity_analysis(args: argparse.Namespace) -> None:
    """Run similarity analysis on documents."""
    logger.info("🔄 Running Similarity Analysis...")
    logger.info("=" * 80)
    
    # Find documents
    docs = find_active_documents(root_dir=args.path)
    logger.info(f"Found {len(docs)} documents")
    
    if len(docs) < 2:
        logger.warning("Need at least 2 documents for similarity analysis")
        return
    
    # Filter by pattern if provided
    if args.pattern:
        docs = [d for d in docs if args.pattern in str(d)]
        logger.info(f"Filtered to {len(docs)} documents matching '{args.pattern}'")
    
    # Limit number of documents
    if args.limit and len(docs) > args.limit:
        docs = docs[:args.limit]
        logger.info(f"Limited to {args.limit} documents")
    
    # Load documents
    loaded = load_markdown_files(docs, args.path)
    
    if args.semantic:
        logger.info("Using semantic similarity (requires sentence-transformers)")
        try:
            calculator = SemanticSimilarityCalculator()
            logger.info(f"Loaded model: {calculator.model_name}")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            logger.info("Falling back to string similarity")
            calculator = StringSimilarityCalculator()
    else:
        logger.info("Using string-based similarity")
        calculator = StringSimilarityCalculator()
    
    # Calculate similarity matrix
    texts = list(loaded.values())
    paths = list(loaded.keys())
    
    logger.info(f"\nCalculating similarity matrix for {len(texts)} documents...")
    matrix = calculator.calculate_matrix(texts, threshold=args.threshold)
    
    # Display results
    logger.info(f"\nSimilarity Results (threshold: {args.threshold}):")
    logger.info("-" * 50)
    
    # Find high similarity pairs
    high_similarity_pairs = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            score = matrix[i][j] if isinstance(matrix, list) else matrix.iloc[i, j]
            if score >= args.threshold:
                high_similarity_pairs.append((paths[i], paths[j], score))
    
    # Sort by score
    high_similarity_pairs.sort(key=lambda x: x[2], reverse=True)
    
    # Display top pairs
    if high_similarity_pairs:
        logger.info(f"\nFound {len(high_similarity_pairs)} document pairs above threshold:")
        for i, (doc1, doc2, score) in enumerate(high_similarity_pairs[:10]):
            logger.info(f"\n{i+1}. Similarity: {score:.3f}")
            logger.info(f"   - {doc1.name}")
            logger.info(f"   - {doc2.name}")
    else:
        logger.info("No document pairs found above threshold")


def run_merge_similar(args: argparse.Namespace) -> None:
    """Find and merge similar documents."""
    logger.info("🔀 Running Document Merge Analysis...")
    logger.info("=" * 80)
    
    # Find documents
    docs = find_active_documents(root_dir=args.path)
    
    if args.pattern:
        docs = [d for d in docs if args.pattern in str(d)]
    
    logger.info(f"Analyzing {len(docs)} documents for potential merges...")
    
    # Run merge analysis
    merge_report = merge_similar_documents(
        documents=docs,
        similarity_threshold=args.threshold,
        actually_merge=args.execute,
        output_dir=Path(args.output) if args.output else None,
        dry_run=not args.execute
    )
    
    if not args.execute:
        logger.info("\n💡 This was a dry run. Use --execute to actually merge files.")


def run_all_checks(args: argparse.Namespace) -> None:
    """Run all checks in sequence."""
    logger.info("🧪 Running ALL Checks...")
    logger.info("=" * 80)
    
    # Compliance check
    logger.info("\n" + "="*80)
    run_compliance_check(args)
    
    # Reference validation
    logger.info("\n" + "="*80)
    run_reference_check(args)
    
    # Structural soundness
    logger.info("\n" + "="*80)
    run_structural_check(args)
    
    # Instruction tracing
    logger.info("\n" + "="*80)
    run_instruction_trace(args)
    
    logger.info("\n" + "="*80)
    logger.info("✅ All checks completed!")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bullet Proof CLI - Run various code and documentation analysis tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all checks
  python -m src.cli all

  # Check CLAUDE.md compliance
  python -m src.cli compliance
  python -m src.cli compliance --file src/module.py

  # Validate references
  python -m src.cli references
  python -m src.cli references --basic

  # Check structural soundness
  python -m src.cli structure

  # Trace instruction paths
  python -m src.cli trace

  # Analyze document similarity
  python -m src.cli similarity
  python -m src.cli similarity --semantic --threshold 0.8
  python -m src.cli similarity --pattern "README" --limit 10

  # Find and merge similar documents
  python -m src.cli merge --threshold 0.9
  python -m src.cli merge --execute --output merged/
"""
    )
    
    # Global options
    parser.add_argument(
        '--path', '-p',
        type=Path,
        default=Path.cwd(),
        help='Root directory to analyze (default: current directory)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # All checks
    parser_all = subparsers.add_parser('all', help='Run all checks')
    
    # Compliance checker
    parser_compliance = subparsers.add_parser('compliance', help='Check CLAUDE.md compliance')
    parser_compliance.add_argument('--file', '-f', help='Check specific file')
    
    # Reference validator
    parser_refs = subparsers.add_parser('references', help='Validate document references')
    parser_refs.add_argument('--basic', action='store_true', help='Use basic mode without enhanced path resolution')
    
    # Structural soundness
    parser_struct = subparsers.add_parser('structure', help='Check structural soundness')
    
    # Instruction tracer
    parser_trace = subparsers.add_parser('trace', help='Trace instruction paths')
    
    # Similarity analysis
    parser_sim = subparsers.add_parser('similarity', help='Analyze document similarity')
    parser_sim.add_argument('--semantic', action='store_true', help='Use semantic similarity (requires models)')
    parser_sim.add_argument('--threshold', type=float, default=0.7, help='Similarity threshold (0-1)')
    parser_sim.add_argument('--pattern', help='Filter documents by pattern')
    parser_sim.add_argument('--limit', type=int, help='Limit number of documents')
    
    # Merge similar documents
    parser_merge = subparsers.add_parser('merge', help='Find and merge similar documents')
    parser_merge.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold for merging')
    parser_merge.add_argument('--execute', action='store_true', help='Actually perform merges (default: dry run)')
    parser_merge.add_argument('--output', help='Output directory for merged files')
    parser_merge.add_argument('--pattern', help='Filter documents by pattern')
    
    args = parser.parse_args()
    
    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Execute command
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    command_map = {
        'all': run_all_checks,
        'compliance': run_compliance_check,
        'references': run_reference_check,
        'structure': run_structural_check,
        'trace': run_instruction_trace,
        'similarity': run_similarity_analysis,
        'merge': run_merge_similar,
    }
    
    try:
        command_func = command_map[args.command]
        command_func(args)
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()