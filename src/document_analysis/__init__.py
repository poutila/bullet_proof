#!/usr/bin/env python3
"""Document matching and analysis utilities.

This module provides tools for:
- Finding and analyzing document similarities
- Semantic embedding-based comparison
- Fuzzy text matching and merging
- Content embedding verification
- Document deduplication workflows

Main modules:
- core: Core matching algorithms and utilities
- analyzers: Document discovery and content loading
- embeddings: Semantic similarity analysis
- merging: Document merging and deduplication
- reports: Analysis reporting and export
- config: Configuration constants and settings
- validation: Input validation and security
"""


from document_analysis.analyzers import find_active_documents, find_not_in_use_documents, load_markdown_files
from document_analysis.core import get_best_match_seq, is_similar, split_sections
from document_analysis.embeddings import analyze_active_document_similarities, analyze_semantic_similarity
from document_analysis.merging import merge_documents, merge_similar_documents
from document_analysis.reports import (
    check_content_embedding,
    export_similarity_report,
    generate_comprehensive_similarity_report,
)

__version__ = "1.0.0"

__all__: list[str] = [
    # Version
    "__version__",
    # Embeddings
    "analyze_active_document_similarities",
    "analyze_semantic_similarity",
    # Reports
    "check_content_embedding",
    "export_similarity_report",
    # Analyzers
    "find_active_documents",
    "find_not_in_use_documents",
    "generate_comprehensive_similarity_report",
    # Core
    "get_best_match_seq",
    "is_similar",
    "load_markdown_files",
    # Merging
    "merge_documents",
    "merge_similar_documents",
    "split_sections",
]
